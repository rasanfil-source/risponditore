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
        print("🔧 Initializing EmailProcessor...")
        
        try:
            self.gmail = GmailManager()
            print("✓ Gmail service initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Gmail service: {e}")
            raise
        
        try:
            self.sheets = SheetsManager()
            print("✓ Sheets service initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Sheets service: {e}")
            raise
        
        try:
            self.gemini = GeminiService()
            print("✓ Gemini service initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini service: {e}")
            raise
        
        self.classifier = EmailClassifier()
        print("✓ Classifier initialized")
        
        # Load resources
        self._load_resources()
        
        print("✅ EmailProcessor ready")

    def _load_resources(self):
        """Load knowledge base and configuration from Sheets"""
        print("\n📚 Loading resources from Google Sheets...")
        
        try:
            # Carica knowledge base
            knowledge_data = self.sheets.load_knowledge_base()
            
            if not knowledge_data:
                raise ValueError(
                    f"Failed to load knowledge base from Spreadsheet.\n"
                    f"   Spreadsheet ID: {config.SPREADSHEET_ID}\n"
                    f"   Sheet Name: {config.SHEET_NAME}\n"
                    f"   Please verify:\n"
                    f"   1. Spreadsheet ID is correct\n"
                    f"   2. Sheet name exists\n"
                    f"   3. Service account has access"
                )

            # Verifica che le chiavi necessarie siano presenti
            required_keys = ['knowledge_base_string', 'ignore_keywords', 'ignore_domains']
            missing_keys = [key for key in required_keys if key not in knowledge_data]
            
            if missing_keys:
                raise ValueError(
                    f"Knowledge base data is incomplete.\n"
                    f"   Missing keys: {missing_keys}\n"
                    f"   Expected keys: {required_keys}"
                )

            # Assegna dati
            self.knowledge_base = knowledge_data['knowledge_base_string']
            self.ignore_keywords = knowledge_data['ignore_keywords']
            self.ignore_domains = knowledge_data['ignore_domains']

            # Carica sostituzioni (opzionale)
            try:
                self.replacements = self.sheets.load_replacements()
            except Exception as e:
                print(f"⚠️  Could not load replacements sheet (non-critical): {e}")
                self.replacements = {}
            
            # Stampa statistiche
            print(f"\n✓ Resources loaded successfully:")
            print(f"   📖 Knowledge base: {len(self.knowledge_base)} characters")
            print(f"   🚫 Ignore keywords: {len(self.ignore_keywords)} entries")
            print(f"   🚫 Ignore domains: {len(self.ignore_domains)} entries")
            print(f"   🔄 Replacements: {len(self.replacements)} entries")
            
            # Mostra sample della knowledge base
            if self.knowledge_base:
                lines = self.knowledge_base.split('\n')
                preview_lines = min(3, len(lines))
                print(f"   📋 Knowledge base preview (first {preview_lines} lines):")
                for line in lines[:preview_lines]:
                    if line.strip():
                        print(f"      {line[:80]}...")
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR loading resources:")
            print(f"   Error: {e}")
            print(f"   Spreadsheet ID: {config.SPREADSHEET_ID}")
            print(f"   Sheet Name: {config.SHEET_NAME}")
            print(f"   Replacements Sheet: {config.REPLACEMENTS_SHEET}")
            print(f"\n   Troubleshooting:")
            print(f"   1. Verify SPREADSHEET_ID environment variable")
            print(f"   2. Check service account has 'Viewer' access to spreadsheet")
            print(f"   3. Verify sheet names match exactly (case-sensitive)")
            print(f"   4. Check spreadsheet has data in columns A, B, C")
            raise

    def process_new_messages(self) -> Dict:
        """
        Process new unread messages

        Returns:
            Processing result dictionary
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting email processing run")
        print(f"{'='*60}\n")
        
        try:
            # Get or create label
            label_name = config.LABEL_NAME
            
            # Get unread threads
            print(f"📨 Fetching unread threads (max: {config.MAX_EMAILS_PER_RUN})...")
            threads = self.gmail.get_unread_threads(
                exclude_label=label_name,
                max_results=config.MAX_EMAILS_PER_RUN
            )
            
            if not threads:
                print("✓ No new messages to process")
                return {
                    'status': 'success',
                    'processed': 0,
                    'message': 'No new messages'
                }

            print(f"📬 Found {len(threads)} thread(s) to process\n")

            # Process each thread
            results = {
                'processed': 0,
                'replied': 0,
                'filtered': 0,
                'errors': 0
            }

            for i, thread in enumerate(threads, 1):
                print(f"\n{'─'*60}")
                print(f"📧 Processing thread {i}/{len(threads)}")
                print(f"   Thread ID: {thread['id']}")
                
                try:
                    result = self._process_thread(thread, label_name)

                    if result['status'] == 'replied':
                        results['replied'] += 1
                        print(f"✓ Thread {i}: Response sent")
                    elif result['status'] == 'filtered':
                        results['filtered'] += 1
                        print(f"⊘ Thread {i}: Filtered ({result.get('reason', 'unknown')})")
                    elif result['status'] == 'skipped':
                        print(f"⊘ Thread {i}: Skipped ({result.get('reason', 'unknown')})")
                    
                    results['processed'] += 1

                except Exception as e:
                    print(f"❌ Error processing thread {i} ({thread['id']}): {e}")
                    results['errors'] += 1
                    
                    # Mark as processed to avoid retry loops
                    try:
                        self.gmail.add_label_to_thread(thread['id'], label_name)
                        print(f"   Marked thread as processed despite error")
                    except Exception as label_error:
                        print(f"   Could not add label: {label_error}")

            # Print summary
            print(f"\n{'='*60}")
            print(f"📊 PROCESSING SUMMARY")
            print(f"{'='*60}")
            print(f"   Total processed: {results['processed']}")
            print(f"   ✓ Replied: {results['replied']}")
            print(f"   ⊘ Filtered: {results['filtered']}")
            print(f"   ❌ Errors: {results['errors']}")
            print(f"{'='*60}\n")

            return {
                'status': 'success',
                'processed': results['processed'],
                'replied': results['replied'],
                'filtered': results['filtered'],
                'errors': results['errors']
            }

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in process_new_messages: {e}")
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

            print(f"   From: {message_details['sender_email']}")
            print(f"   Subject: {message_details['subject'][:60]}...")

            # Skip if from ourselves
            if self.gmail.user_email.lower() in message_details['sender_email'].lower():
                print(f"   ⊘ Skipping: Self-sent message")
                return {'status': 'skipped', 'reason': 'self_sent'}

            # === STAGE 1: Fast Filters (Domain/Keyword) ===
            print(f"   🔍 Stage 1: Fast filters...")
            if should_ignore_email(
                message_details['subject'],
                message_details['body'],
                message_details['sender_email'],
                self.ignore_keywords,
                self.ignore_domains
            ):
                print(f"   ⊘ Filtered by domain/keyword")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': 'domain_keyword'}

            # === STAGE 2: NLP Classification ===
            print(f"   🧠 Stage 2: NLP classification...")
            is_reply = message_details['subject'].lower().startswith(('re:', 'r:'))

            classification = self.classifier.classify_email(
                message_details['subject'],
                message_details['body'],
                is_reply=is_reply
            )

            print(f"      Decision: {'REPLY' if classification['should_reply'] else 'NO REPLY'}")
            print(f"      Reason: {classification['reason']}")
            if classification.get('category'):
                print(f"      Category: {classification['category']}")

            # === STAGE 2b: Force Reply Check ===
            text_to_check = f"{message_details['subject']} {message_details['body']}".lower()
            if any(kw in text_to_check for kw in FORCE_REPLY_KEYWORDS):
                print(f"   ⚠️  Force reply triggered by keyword")
                classification['should_reply'] = True
                classification['reason'] = 'force_reply'

            if not classification['should_reply']:
                print(f"   ⊘ Filtered by classifier")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': classification['reason']}

            # === STAGE 3: Build Context ===
            print(f"   📚 Stage 3: Building context...")
            conversation_messages = []
            for msg in messages:
                msg_details = self.gmail.extract_message_details(msg)
                conversation_messages.append(msg_details)

            conversation_history = self.gmail.build_conversation_history(conversation_messages)
            print(f"      Conversation: {len(conversation_messages)} message(s)")

            # Summarize if long
            if len(conversation_history) > 500:
                print(f"      Summarizing conversation...")
                summarized_history = self.gemini.summarize_conversation(conversation_history)
            else:
                summarized_history = conversation_history

            # Generate dynamic knowledge base
            final_knowledge_base = generate_dynamic_knowledge_base(self.knowledge_base)

            # === STAGE 4: Gemini Response Generation ===
            print(f"   🤖 Stage 4: Generating AI response...")
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
                print(f"   ✏️  Stage 5: Post-processing...")
                
                # Apply text replacements
                if self.replacements:
                    ai_response = apply_replacements(ai_response, self.replacements)
                    print(f"      Applied {len(self.replacements)} replacement rules")

                # Quality checks
                print(f"   ✓ Stage 6: Validation...")
                if not self._validate_response(ai_response, message_details):
                    print(f"   ⊘ Response failed validation")
                    self.gmail.add_label_to_thread(thread['id'], label_name)
                    return {'status': 'filtered', 'reason': 'invalid_response'}

                # Send reply
                print(f"   📤 Sending reply...")
                self.gmail.send_reply(message_details, ai_response)
                print(f"   ✓ Reply sent successfully")

                # Mark as processed
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'replied'}

            elif ai_response and 'NO_REPLY' in ai_response.upper():
                print(f"   ⊘ Gemini decided NO_REPLY")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': 'gemini_no_reply'}

            else:
                print(f"   ❌ Empty response from Gemini")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'error', 'reason': 'empty_response'}

        except Exception as e:
            print(f"   ❌ Error in thread processing: {e}")
            raise

    def _validate_response(self, response: str, message_details: Dict) -> bool:
        """
        Validate AI response quality
        
        Args:
            response: Generated response text
            message_details: Original message details
            
        Returns:
            True if response is valid
        """
        # Check minimum length
        if len(response.strip()) < 50:
            print(f"      ✗ Response too short ({len(response)} chars)")
            return False

        # Check maximum length
        if len(response.strip()) > 3000:
            print(f"      ⚠️  Response very long ({len(response)} chars)")
            # Non blocchiamo, ma avvisiamo

        # Check for greeting (warning only)
        required_greetings = ['buongiorno', 'buonasera', 'buon pomeriggio', 'gentile', 'buona', 
                             'good morning', 'good afternoon', 'good evening', 'dear',
                             'buenos días', 'buenas tardes', 'buenas noches']
        has_greeting = any(greet in response.lower()[:150] for greet in required_greetings)

        if not has_greeting:
            print(f"      ⚠️  Response missing greeting (non-blocking)")

        # Check for closing (warning only)
        closing_phrases = ['cordiali saluti', 'distinti saluti', 'kind regards', 
                          'best regards', 'cordiales saludos']
        has_closing = any(closing in response.lower() for closing in closing_phrases)
        
        if not has_closing:
            print(f"      ⚠️  Response missing closing (non-blocking)")

        # Check for "NO_REPLY" leaking through
        if 'NO_REPLY' in response.upper() and len(response) > 20:
            print(f"      ✗ Response contains NO_REPLY instruction (should be filtered)")
            return False

        print(f"      ✓ Validation passed ({len(response)} chars)")
        return True
    
    def get_statistics(self) -> Dict:
        """
        Get processor statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            'knowledge_base_size': len(self.knowledge_base) if hasattr(self, 'knowledge_base') else 0,
            'ignore_keywords_count': len(self.ignore_keywords) if hasattr(self, 'ignore_keywords') else 0,
            'ignore_domains_count': len(self.ignore_domains) if hasattr(self, 'ignore_domains') else 0,
            'replacements_count': len(self.replacements) if hasattr(self, 'replacements') else 0,
        }
    
    def reload_resources(self):
        """
        Reload resources from Google Sheets (clear cache and reload)
        """
        print("\n🔄 Reloading resources from Google Sheets...")
        try:
            # Clear sheets cache
            self.sheets.clear_cache()
            
            # Reload resources
            self._load_resources()
            
            print("✓ Resources reloaded successfully")
        except Exception as e:
            print(f"❌ Error reloading resources: {e}")
            raise
