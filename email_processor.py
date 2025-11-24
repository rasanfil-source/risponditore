"""
Email processor module - Orchestrates the email processing pipeline
Coordinates filtering, classification, and response generation
✅ CLEANED VERSION: Removed duplications and deprecated methods
✅ FIXED: Better territory validation logging
✅ FIXED: Uses only ResponseValidator (removed legacy validation)
"""

import logging
from typing import Dict, Optional, List
from gmail_service import GmailManager
from sheets_service import SheetsManager
from gemini_service import GeminiService
from nlp_classifier import EmailClassifier
from response_validator import ResponseValidator
from utils import (
    should_ignore_email,
    apply_replacements,
    generate_dynamic_knowledge_base
)
from config import FORCE_REPLY_KEYWORDS
import config

logger = logging.getLogger(__name__)


class EmailProcessor:
    """
    Orchestrates the email processing pipeline
    
    ✅ IMPROVEMENTS:
    - Removed deprecated _validate_response method
    - Added territory validation logging
    - Uses only ResponseValidator for all validation
    - Smart KB truncation preserving structure
    - Better error handling with error labels
    """

    def __init__(self):
        """Initialize processor with all required services"""
        logger.info("🔧 Initializing EmailProcessor...")
        
        try:
            self.gmail = GmailManager()
            logger.info("✓ Gmail service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gmail service: {e}")
            raise
        
        try:
            self.sheets = SheetsManager()
            logger.info("✓ Sheets service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Sheets service: {e}")
            raise
        
        try:
            self.gemini = GeminiService()
            logger.info("✓ Gemini service initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini service: {e}")
            raise
        
        self.classifier = EmailClassifier()
        logger.info("✓ Classifier initialized")
        
        self.validator = ResponseValidator()
        logger.info("✓ Response validator initialized")
        
        # Load resources
        self._load_resources()
        
        logger.info("✅ EmailProcessor ready")

    def _load_resources(self):
        """Load knowledge base and configuration from Sheets"""
        logger.info("\n📚 Loading resources from Google Sheets...")
        
        try:
            # Load knowledge base
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

            # Verify required keys
            required_keys = ['knowledge_base_string', 'ignore_keywords', 'ignore_domains']
            missing_keys = [key for key in required_keys if key not in knowledge_data]
            
            if missing_keys:
                raise ValueError(
                    f"Knowledge base data is incomplete.\n"
                    f"   Missing keys: {missing_keys}\n"
                    f"   Expected keys: {required_keys}"
                )

            # Assign data
            self.knowledge_base = knowledge_data['knowledge_base_string']
            self.ignore_keywords = knowledge_data['ignore_keywords']
            self.ignore_domains = knowledge_data['ignore_domains']

            # Load replacements (optional)
            try:
                self.replacements = self.sheets.load_replacements()
            except Exception as e:
                logger.warning(f"⚠️  Could not load replacements sheet (non-critical): {e}")
                self.replacements = {}
            
            # Print statistics
            logger.info(f"\n✓ Resources loaded successfully:")
            logger.info(f"   📖 Knowledge base: {len(self.knowledge_base)} characters")
            logger.info(f"   🚫 Ignore keywords: {len(self.ignore_keywords)} entries")
            logger.info(f"   🚫 Ignore domains: {len(self.ignore_domains)} entries")
            logger.info(f"   🔄 Replacements: {len(self.replacements)} entries")
            
            # Show KB preview
            if self.knowledge_base:
                lines = self.knowledge_base.split('\n')
                preview_lines = min(3, len(lines))
                logger.info(f"   📋 Knowledge base preview (first {preview_lines} lines):")
                for line in lines[:preview_lines]:
                    if line.strip():
                        logger.info(f"      {line[:80]}...")
            
        except Exception as e:
            logger.error(f"\n❌ CRITICAL ERROR loading resources:")
            logger.error(f"   Error: {e}")
            logger.error(f"   Spreadsheet ID: {config.SPREADSHEET_ID}")
            logger.error(f"   Sheet Name: {config.SHEET_NAME}")
            logger.error(f"   Replacements Sheet: {config.REPLACEMENTS_SHEET}")
            logger.error(f"\n   Troubleshooting:")
            logger.error(f"   1. Verify SPREADSHEET_ID environment variable")
            logger.error(f"   2. Check service account has 'Viewer' access to spreadsheet")
            logger.error(f"   3. Verify sheet names match exactly (case-sensitive)")
            logger.error(f"   4. Check spreadsheet has data in columns A, B, C")
            raise

    def process_new_messages(self) -> Dict:
        """
        Process new unread messages

        Returns:
            Processing result dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 Starting email processing run")
        logger.info(f"{'='*60}\n")
        
        try:
            # Get or create label
            label_name = config.LABEL_NAME
            
            # Get unread threads
            logger.info(f"📨 Fetching unread threads (max: {config.MAX_EMAILS_PER_RUN})...")
            threads = self.gmail.get_unread_threads(
                exclude_label=label_name,
                max_results=config.MAX_EMAILS_PER_RUN
            )
            
            if not threads:
                logger.info("✓ No new messages to process")
                return {
                    'status': 'success',
                    'processed': 0,
                    'message': 'No new messages'
                }

            logger.info(f"📬 Found {len(threads)} thread(s) to process\n")

            # Process each thread
            results = {
                'processed': 0,
                'replied': 0,
                'filtered': 0,
                'errors': 0,
                'dry_run_count': 0,
                'validation_failed': 0
            }

            for i, thread in enumerate(threads, 1):
                logger.info(f"\n{'─'*60}")
                logger.info(f"📧 Processing thread {i}/{len(threads)}")
                logger.info(f"   Thread ID: {thread['id']}")
                
                try:
                    result = self._process_thread(thread, label_name)

                    if result['status'] == 'replied':
                        results['replied'] += 1
                        if result.get('dry_run'):
                            results['dry_run_count'] += 1
                        logger.info(f"✓ Thread {i}: Response sent{' (DRY RUN)' if result.get('dry_run') else ''}")
                    elif result['status'] == 'filtered':
                        results['filtered'] += 1
                        logger.info(f"⊘ Thread {i}: Filtered ({result.get('reason', 'unknown')})")
                    elif result['status'] == 'validation_failed':
                        results['validation_failed'] += 1
                        logger.warning(f"❌ Thread {i}: Validation failed (score: {result.get('validation_score', 0):.2f})")
                    elif result['status'] == 'skipped':
                        logger.info(f"⊘ Thread {i}: Skipped ({result.get('reason', 'unknown')})")
                    
                    results['processed'] += 1

                except Exception as e:
                    logger.error(f"❌ Error processing thread {i} ({thread['id']}): {e}", exc_info=True)
                    results['errors'] += 1
                    
                    # Add error label instead of processing label on failures
                    try:
                        error_label = config.ERROR_LABEL_NAME
                        self.gmail.add_label_to_thread(thread['id'], error_label)
                        logger.warning(f"   Marked thread with error label: {error_label}")
                    except Exception as label_error:
                        logger.error(f"   Could not add error label: {label_error}")

            # Print summary
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 PROCESSING SUMMARY")
            logger.info(f"{'='*60}")
            logger.info(f"   Total processed: {results['processed']}")
            logger.info(f"   ✓ Replied: {results['replied']}")
            if results['dry_run_count'] > 0:
                logger.info(f"   🔴 Dry run: {results['dry_run_count']}")
            logger.info(f"   ⊘ Filtered: {results['filtered']}")
            if results['validation_failed'] > 0:
                logger.info(f"   ❌ Validation failed: {results['validation_failed']}")
            logger.info(f"   ❌ Errors: {results['errors']}")
            logger.info(f"{'='*60}\n")

            return {
                'status': 'success',
                'processed': results['processed'],
                'replied': results['replied'],
                'filtered': results['filtered'],
                'validation_failed': results['validation_failed'],
                'errors': results['errors'],
                'dry_run': config.DRY_RUN,
                'dry_run_count': results['dry_run_count']
            }

        except Exception as e:
            logger.error(f"\n❌ CRITICAL ERROR in process_new_messages: {e}", exc_info=True)
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
        5. Advanced response validation
        6. Post-processing and sending

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

            logger.info(f"   From: {message_details['sender_email']}")
            logger.info(f"   Subject: {message_details['subject'][:60]}...")

            # Skip if from ourselves
            if self.gmail.user_email.lower() in message_details['sender_email'].lower():
                logger.info(f"   ⊘ Skipping: Self-sent message")
                return {'status': 'skipped', 'reason': 'self_sent'}

            # === STAGE 1: Fast Filters (Domain/Keyword) ===
            logger.info(f"   🔍 Stage 1: Fast filters...")
            if should_ignore_email(
                message_details['subject'],
                message_details['body'],
                message_details['sender_email'],
                self.ignore_keywords,
                self.ignore_domains
            ):
                logger.info(f"   ⊘ Filtered by domain/keyword")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': 'domain_keyword'}

            # === STAGE 2: NLP Classification ===
            logger.info(f"   🧠 Stage 2: NLP classification...")
            is_reply = message_details['subject'].lower().startswith(('re:', 'r:'))

            classification = self.classifier.classify_email(
                message_details['subject'],
                message_details['body'],
                is_reply=is_reply
            )

            logger.info(f"      Decision: {'REPLY' if classification['should_reply'] else 'NO REPLY'}")
            logger.info(f"      Reason: {classification['reason']}")
            if classification.get('category'):
                logger.info(f"      Category: {classification['category']}")

            # === STAGE 2b: Force Reply Check ===
            text_to_check = f"{message_details['subject']} {message_details['body']}".lower()
            if any(kw in text_to_check for kw in FORCE_REPLY_KEYWORDS):
                logger.info(f"   ⚠️  Force reply triggered by keyword")
                classification['should_reply'] = True
                classification['reason'] = 'force_reply'

            # === STAGE 2c: Gemini Lightweight Decision Check ===
            # Only if NLP classifier said "should reply", double-check with Gemini
            if classification['should_reply']:
                logger.info(f"   🤔 Stage 2c: Gemini decision check...")
                
                gemini_should_respond = self.gemini.should_respond_to_email(
                    email_content=message_details['body'],
                    email_subject=message_details['subject'],
                    sender_email=message_details['sender_email']
                )
                
                if not gemini_should_respond:
                    logger.info(f"   ⊘ Gemini decided: no response needed")
                    self.gmail.add_label_to_thread(thread['id'], label_name)
                    return {
                        'status': 'filtered',
                        'reason': 'gemini_no_response_needed'
                    }
                
                logger.info(f"   ✓ Gemini confirmed: response needed")

            # Final check after all filters
            if not classification['should_reply']:
                logger.info(f"   ⊘ Filtered by classifier")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': classification['reason']}

            # === STAGE 3: Build Context ===
            logger.info(f"   📚 Stage 3: Building context...")
            conversation_messages = []
            for msg in messages:
                msg_details = self.gmail.extract_message_details(msg)
                conversation_messages.append(msg_details)

            conversation_history = self.gmail.build_conversation_history(conversation_messages)
            logger.info(f"      Conversation: {len(conversation_messages)} message(s)")

            # Limit conversation history size
            if len(conversation_history) > config.MAX_CONVERSATION_CHARS:
                logger.info(f"      Summarizing long conversation ({len(conversation_history)} chars)...")
                summarized_history = self.gemini.summarize_conversation(conversation_history)
            else:
                summarized_history = conversation_history

            # Generate dynamic knowledge base with temporal context
            final_knowledge_base = generate_dynamic_knowledge_base(self.knowledge_base)
            
            logger.info(f"      Knowledge base with temporal context: {len(final_knowledge_base)} chars")
            
            # Smart truncation preserving structure
            if len(final_knowledge_base) > config.MAX_KNOWLEDGE_BASE_CHARS:
                final_knowledge_base = self._smart_truncate_kb(final_knowledge_base)

            # === STAGE 4: Gemini Response Generation ===
            logger.info(f"   🤖 Stage 4: Generating AI response...")
            ai_response = self.gemini.generate_response(
                message_details['body'],
                message_details['subject'],
                final_knowledge_base,
                message_details['sender_name'],
                message_details['sender_email'],
                summarized_history,
                category=classification.get('category')
            )

            # Check if response was generated
            if not ai_response:
                logger.warning(f"   ❌ No response generated by Gemini")
                self.gmail.add_label_to_thread(thread['id'], f"{config.ERROR_LABEL_NAME}_NO_RESPONSE")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'error', 'reason': 'no_response_generated'}

            # Check for NO_REPLY directive
            if 'NO_REPLY' in ai_response.upper():
                logger.info(f"   ⊘ Gemini decided NO_REPLY")
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {'status': 'filtered', 'reason': 'gemini_no_reply'}

            # === STAGE 5: ADVANCED RESPONSE VALIDATION ===
            logger.info(f"   🔍 Stage 5: Advanced response validation...")
            
            # Detect language for validation
            detected_language = self.gemini._detect_email_language(
                message_details['body'], 
                message_details['subject']
            )
            
            # Perform comprehensive validation
            validation_result = self.validator.validate_response(
                response=ai_response,
                detected_language=detected_language,
                knowledge_base=final_knowledge_base,
                email_content=message_details['body'],
                email_subject=message_details['subject']
            )
            
            # Log validation details
            logger.info(f"      Validation score: {validation_result.score:.2f}")
            logger.info(f"      Errors: {len(validation_result.errors)}")
            logger.info(f"      Warnings: {len(validation_result.warnings)}")
            
            # Check if validation passed
            if not validation_result.is_valid:
                logger.warning(f"   ❌ Response FAILED validation!")
                logger.warning(f"      Overall score: {validation_result.score:.2f} (threshold: {self.validator.min_valid_score})")
                
                # Log errors
                for i, error in enumerate(validation_result.errors, 1):
                    logger.warning(f"      Error {i}: {error}")
                
                # Log first 3 warnings
                for i, warning in enumerate(validation_result.warnings[:3], 1):
                    logger.warning(f"      Warning {i}: {warning}")
                
                if len(validation_result.warnings) > 3:
                    logger.warning(f"      ... and {len(validation_result.warnings) - 3} more warnings")
                
                # Add specific error label
                error_label = f"{config.ERROR_LABEL_NAME}_VALIDATION_FAILED"
                self.gmail.add_label_to_thread(thread['id'], error_label)
                self.gmail.add_label_to_thread(thread['id'], label_name)
                
                return {
                    'status': 'validation_failed',
                    'reason': 'response_quality_too_low',
                    'validation_score': validation_result.score,
                    'errors': validation_result.errors[:3],
                    'warnings': validation_result.warnings[:3]
                }
            
            # Validation passed!
            logger.info(f"   ✓ Validation PASSED (score: {validation_result.score:.2f})")
            
            if validation_result.warnings:
                logger.info(f"      ⚠️  {len(validation_result.warnings)} non-blocking warning(s):")
                for i, warning in enumerate(validation_result.warnings[:3], 1):
                    logger.info(f"         {i}. {warning}")
                if len(validation_result.warnings) > 3:
                    logger.info(f"         ... and {len(validation_result.warnings) - 3} more")

            # === STAGE 6: Post-processing and Sending ===
            logger.info(f"   ✏️  Stage 6: Post-processing...")
            
            # Apply text replacements
            if self.replacements:
                ai_response = apply_replacements(ai_response, self.replacements)
                logger.info(f"      Applied {len(self.replacements)} replacement rules")

            # DRY-RUN mode check
            if config.DRY_RUN:
                logger.warning(f"   🔴 DRY_RUN MODE: Skipping email send")
                logger.info(f"   📝 Would have sent response ({len(ai_response)} chars):")
                logger.info(f"      {ai_response[:200]}...")
                # Still mark as processed in dry-run
                self.gmail.add_label_to_thread(thread['id'], label_name)
                return {
                    'status': 'replied',
                    'dry_run': True,
                    'validation_score': validation_result.score
                }
            
            # Send reply (only if not DRY_RUN)
            logger.info(f"   📤 Sending reply...")
            self.gmail.send_reply(message_details, ai_response)
            logger.info(f"   ✓ Reply sent successfully")

            # Mark as processed
            self.gmail.add_label_to_thread(thread['id'], label_name)
            
            return {
                'status': 'replied',
                'validation_score': validation_result.score,
                'warnings_count': len(validation_result.warnings)
            }

        except Exception as e:
            logger.error(f"   ❌ Error in thread processing: {e}", exc_info=True)
            raise

    def _smart_truncate_kb(self, kb_text: str) -> str:
        """
        Smart truncation that preserves entry structure
        
        Args:
            kb_text: Full knowledge base text
            
        Returns:
            Truncated KB preserving structure
        """
        logger.warning(f"      KB too large ({len(kb_text)} chars), smart truncating...")
        
        # Split temporal context from KB content
        split_marker = "📋 DATE RILEVATE NELLA KNOWLEDGE BASE:"
        
        if split_marker in kb_text:
            parts = kb_text.split(split_marker)
            temporal_part = parts[0] + split_marker
            
            # Find end of date section
            if len(parts) > 1:
                date_section_parts = parts[1].split("\n\n", 1)
                if len(date_section_parts) > 1:
                    temporal_part += date_section_parts[0]
                    kb_content = date_section_parts[1]
                else:
                    temporal_part += parts[1]
                    kb_content = ""
            else:
                kb_content = ""
        else:
            # Fallback: assume first 2000 chars are temporal
            temporal_part = kb_text[:2000]
            kb_content = kb_text[2000:]
        
        remaining_space = config.MAX_KNOWLEDGE_BASE_CHARS - len(temporal_part)
        
        if len(kb_content) > remaining_space:
            # Truncate at entry boundaries
            entry_marker = "--- Informazione ---"
            entries = kb_content.split(entry_marker)
            
            truncated_entries = [entries[0]]  # Keep any preamble
            current_size = len(entries[0])
            entries_kept = 0
            
            for entry in entries[1:]:
                entry_with_marker = entry_marker + entry
                if current_size + len(entry_with_marker) < remaining_space - 200:  # Leave space for note
                    truncated_entries.append(entry_with_marker)
                    current_size += len(entry_with_marker)
                    entries_kept += 1
                else:
                    break
            
            kb_content = "".join(truncated_entries)
            kb_content += f"\n\n[... {len(entries) - entries_kept - 1} informazioni omesse per limiti di spazio ...]"
            
            logger.info(f"      Kept {entries_kept}/{len(entries)-1} KB entries")
        
        result = temporal_part + "\n\n" + kb_content
        logger.info(f"      Final KB size: {len(result)} chars")
        
        return result
    
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
        logger.info("\n🔄 Reloading resources from Google Sheets...")
        try:
            # Clear sheets cache
            self.sheets.clear_cache()
            
            # Reload resources
            self._load_resources()
            
            logger.info("✓ Resources reloaded successfully")
        except Exception as e:
            logger.error(f"❌ Error reloading resources: {e}")
            raise
