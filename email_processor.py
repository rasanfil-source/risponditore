"""
Email processor module - Orchestrates the email processing pipeline
Coordinates filtering, classification, and response generation
"""

from typing import Dict, Optional, List
from gmail_service import GmailManager
from sheets_service import SheetsManager
from gemini_service import GeminiService
from nlp_classifier import EmailClassifier
from utils import (
    should_ignore_email,
    apply_replacements,
    generate_dynamic_knowledge_base
)
from config import FORCE_REPLY_KEYWORDS
import config

class EmailProcessor:
    """
    Orchestrates the email processing pipeline:
    Gmail → Fast Filters → NLP Classification → Knowledge Base → Gemini → Response
    """

    def __init__(self):
        """Initialize processor with all required services"""
        self.gmail = GmailManager()
        self.sheets = SheetsManager()
        self.gemini = GeminiService()
        self.classifier = EmailClassifier()
        # Load resources
        self._load_resources()

    def _load_resources(self):
        """Load knowledge base and configuration from Sheets"""
        try:
            knowledge_data = self.sheets.load_knowledge_base()
            if not knowledge_data:
                raise ValueError("Failed to load knowledge base")

            self.knowledge_base = knowledge_data['knowledge_base_string']
            self.ignore_keywords = knowledge_data['ignore_keywords']
            self.ignore_domains = knowledge_data['ignore_domains']

            self.replacements = self.sheets.load_replacements()
            print("Resources loaded successfully")
        except Exception as e:
            print(f"Error loading resources: {e}")
            raise

    def process_new_messages(self) -> Dict:
        """
        Process new unread messages

        Returns:
            Processing result dictionary
        """
        try:
            # Get or create label
            label_name = config.LABEL_NAME
            # Get unread threads
            threads = self.gmail.get_unread_threads(
                exclude_label=label_name,
                max_results=config.MAX_EMAILS_PER_RUN
            )
            if not threads:
                return {
                    'status': 'success',
                    'processed': 0,
                    'message': 'No new messages'
                }

            # Process each thread
            results = {
                'processed': 0,
                'replied': 0,
                'filtered': 0,
                'errors': 0
            }

            for thread in threads:
                try:
                    result = self._process_thread(thread, label_name)

                    if result['status'] == 'replied':
                        results['replied'] += 1
                    elif result['status'] == 'filtered':
                        results['filtered'] += 1

                    results['processed'] += 1

                except Exception as e:
                    print(f"Error processing thread {thread['id']}: {e}")
                    results['errors'] += 1
                    # Mark as processed to avoid retry loops
                    try:
                        self.gmail.add_label_to_thread(thread['id'], label_name)
                    except:
                        pass

            return {
                'status': 'success',
                'processed': results['processed'],
                'replied': results['replied'],
                'filtered': results['filtered'],
                'errors': results['errors']
            }

        except Exception as e:
            print(f"Error in process_new_messages: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def _process_thread(self, thread: Dict, label_name: str) -> Dict:
        """
        Process a single email thread through the pipeline

        Pipeline stages:
        1. Extract messages
        2. Fast domain/keyword filters
        3. NLP classification
        4. Gemini response generation
        5. Post-processing and sending

        Args:
            thread: Gmail thread object
            label_name: Label to apply when processed

        Returns:
            Result dictionary
        """
        try:
            # Extract messages
            messages = thread.get('messages', [])
            if not messages:
                return {'status': 'skipped', 'reason': 'no_messages'}

            # Get last message
            last_message = messages[-1]
            message_details = self.gmail.extract_message_details(last_message)

            # Skip if from ourselves
            if self.gmail.user_email.lower() in message_details['sender_email'].lower():
                print(f"Skipping self-sent: {message_details['sender_email']}")
                return {'status': 'skipped', 'reason': 'self_sent'}

            # === STAGE 1: Fast Filters (Domain/Keyword) ===
            if should_ignore_email(
                message_details['subject'],
                message_details['body'],
                message_details['sender_email'],
                self.ignore_keywords,
                self.ignore_domains
            ):
                print(f"Filtered by domain/keyword: {message_details['sender_email']}")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': 'domain_keyword'}

            # === STAGE 2: NLP Classification ===
            is_reply = message_details['subject'].lower().startswith(('re:', 'r:'))

            classification = self.classifier.classify_email(
                message_details['subject'],
                message_details['body'],
                is_reply=is_reply
            )

            print(f"Classification: {classification}")

            # === STAGE 2b: Force Reply Check ===
            text_to_check = f"{message_details['subject']} {message_details['body']}".lower()
            if any(kw in text_to_check for kw in FORCE_REPLY_KEYWORDS):
                print("Force reply triggered by keyword")
                classification['should_reply'] = True
                classification['reason'] = 'force_reply'

            if not classification['should_reply']:
                print(f"Filtered by classifier: {classification['reason']}")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': classification['reason']}

            # === STAGE 3: Build Context ===
            conversation_messages = []
            for msg in messages:
                msg_details = self.gmail.extract_message_details(msg)
                conversation_messages.append(msg_details)

            conversation_history = self.gmail.build_conversation_history(conversation_messages)

            # Summarize if long
            summarized_history = self.gemini.summarize_conversation(conversation_history)

            # Generate dynamic knowledge base
            final_knowledge_base = generate_dynamic_knowledge_base(self.knowledge_base)

            # === STAGE 4: Gemini Response Generation ===
            ai_response = self.gemini.generate_response(
                message_details['body'],
                message_details['subject'],
                final_knowledge_base,
                message_details['sender_name'],
                message_details['sender_email'],
                summarized_history,
                category=classification.get('category')
            )

            # === STAGE 5: Post-processing and Sending ===
            if ai_response and 'NO_REPLY' not in ai_response.upper():
                # Apply text replacements
                ai_response = apply_replacements(ai_response, self.replacements)

                # Quality checks
                if not self._validate_response(ai_response, message_details):
                    print("Response failed validation")
                    self.gmail.add_label_to_thread(thread['id'], label_name)
                    return {'status': 'filtered', 'reason': 'invalid_response'}

                # Send reply
                self.gmail.send_reply(message_details, ai_response)
                print(f"✓ Replied to: {message_details['sender_email']}")

                # Mark as processed
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'replied'}

            elif ai_response and 'NO_REPLY' in ai_response.upper():
                print(f"Gemini decided NO_REPLY: {message_details['sender_email']}")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': 'gemini_no_reply'}

            else:
                print(f"Empty response from Gemini")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'error', 'reason': 'empty_response'}

        except Exception as e:
            print(f"Error in _process_thread: {e}")
            raise

    def _validate_response(self, response: str, message_details: Dict) -> bool:
        # Check minimum length
        if len(response.strip()) < 50:
            print("Response too short")
            return False

        # Check maximum length (avoid overly long responses)
        if len(response.strip()) > 3000:
            print("Response too long")
            return False

        required_greetings = ['buongiorno', 'buonasera', 'buon pomeriggio', 'gentile', 'buona']
        has_greeting = any(greet in response.lower()[:100] for greet in required_greetings)

        if not has_greeting:
            print("Response missing proper greeting (warning only)")

        if 'cordiali saluti' not in response.lower():
            print("Response missing proper closing (warning only)")

        return True
