"""
Gmail service module for email operations
Handles reading, sending, and labeling emails with improved HTML handling
✅ FIXED: Reply-To header support for web forms
✅ FIXED: Robust HTML parsing with multiple fallbacks, better error handling
✅ NEW: Intelligent Markdown to HTML conversion for Gemini responses
"""

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import re
from auth import get_gmail_service
from html2text import HTML2Text
from markdown_formatter import MarkdownFormatter  # ✅ NUOVO
import config

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _b64url_decode(data: str) -> bytes:
    """
    Decode base64 URL-safe string with automatic padding correction
    
    Args:
        data: Base64 URL-safe encoded string
        
    Returns:
        Decoded bytes
    """
    if not data:
        return b''
    
    # Add missing padding for urlsafe base64
    padding_needed = (-len(data)) % 4
    if padding_needed:
        data += '=' * padding_needed
    
    try:
        return base64.urlsafe_b64decode(data)
    except Exception as e:
        logger.warning(f"⚠️  Base64 decode error: {e}")
        return b''


def _html_to_text(html: str) -> str:
    """
    🔧 FIX: Convert HTML to plain text with robust fallback chain
    
    Tries:
    1. html2text (preferred, maintains structure)
    2. BeautifulSoup (fallback for complex HTML)
    3. Regex strip (last resort)
    
    Args:
        html: HTML string
        
    Returns:
        Plain text representation
    """
    if not html or not html.strip():
        return ''
    
    # Primary: html2text
    try:
        h = HTML2Text()
        h.ignore_links = False  # Keep links as [text](url)
        h.ignore_images = True
        h.body_width = 0  # No line wrapping
        h.ignore_emphasis = False  # Keep *bold* and _italic_
        result = h.handle(html).strip()
        
        # 🔧 FIX: Validate result quality
        if len(result) < 10 and len(html) > 100:
            logger.warning(f"⚠️  HTML2Text output suspiciously short ({len(result)} chars from {len(html)} chars HTML)")
            raise ValueError("Output too short, trying fallback")
        
        return result
        
    except Exception as e:
        logger.warning(f"⚠️  html2text failed: {e}, trying BeautifulSoup")
        
        # Secondary: BeautifulSoup
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            
            if text and len(text) > 10:
                logger.info("✓ Used BeautifulSoup fallback successfully")
                return text
            
            logger.warning("⚠️  BeautifulSoup also produced short output")
            
        except Exception as bs_error:
            logger.warning(f"⚠️  BeautifulSoup also failed: {bs_error}")
        
        # Tertiary: Regex strip (last resort)
        logger.warning("⚠️  Using regex fallback for HTML stripping")
        text = re.sub('<[^<]+?>', '', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


# ============================================================================
# GMAILMANAGER CLASS
# ============================================================================

class GmailManager:
    """
    Manager for Gmail API operations
    
    ✅ IMPROVEMENTS:
    - Reply-To header support for web forms
    - Race condition handling for label creation
    - Robust HTML parsing with fallbacks
    - Better error handling and logging
    - ✅ NEW: Intelligent Markdown to HTML conversion
    """
    
    def __init__(self, user_email: str = None):
        """Initialize Gmail manager with impersonated credentials"""
        self.service = get_gmail_service(user_email)
        self.user_email = user_email or config.IMPERSONATE_EMAIL
        
        # Label cache to avoid repeated API calls
        self._label_cache: Dict[str, str] = {}
        
        # ✅ NUOVO: Initialize Markdown formatter
        self.markdown_formatter = MarkdownFormatter()
        
        logger.info("✓ Gmail service initialized with label cache and Markdown formatter")
        
    def get_or_create_label(self, label_name: str) -> str:
        """
        🔧 FIX: Get or create a Gmail label with race condition handling
        
        Handles concurrent instances trying to create the same label
        
        Args:
            label_name: Name of the label
            
        Returns:
            Label ID
        """
        # Check cache first
        if label_name in self._label_cache:
            logger.debug(f"📦 Label '{label_name}' found in cache: {self._label_cache[label_name]}")
            return self._label_cache[label_name]
        
        try:
            # 🔧 FIX: Always fetch fresh labels to avoid race conditions
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    # Cache the result
                    self._label_cache[label_name] = label['id']
                    logger.info(f"✓ Label '{label_name}' found: {label['id']}")
                    return label['id']
            
            # Label doesn't exist, try to create it
            try:
                label_object = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                
                created_label = self.service.users().labels().create(
                    userId='me',
                    body=label_object
                ).execute()
                
                # Cache the new label
                self._label_cache[label_name] = created_label['id']
                logger.info(f"✓ Created new label: {label_name} ({created_label['id']})")
                return created_label['id']
                
            except Exception as create_error:
                # 🔧 FIX: Handle race condition - another process created it
                error_msg = str(create_error).lower()
                if 'already exists' in error_msg or 'duplicate' in error_msg:
                    logger.warning(f"⚠️  Label '{label_name}' created by another process, refetching...")
                    
                    # Refetch labels and find the newly created one
                    results = self.service.users().labels().list(userId='me').execute()
                    for label in results.get('labels', []):
                        if label['name'] == label_name:
                            self._label_cache[label_name] = label['id']
                            logger.info(f"✓ Found label created by another process: {label['id']}")
                            return label['id']
                    
                    # If still not found, something is wrong
                    logger.error(f"❌ Label '{label_name}' should exist but not found after refetch")
                    raise ValueError(f"Label '{label_name}' inconsistency after concurrent creation")
                else:
                    # Other error, re-raise
                    raise
            
        except Exception as e:
            logger.error(f"❌ Error managing label '{label_name}': {e}")
            raise
    
    def clear_label_cache(self):
        """Clear the label cache (useful for testing or after label changes)"""
        self._label_cache.clear()
        logger.info("🗑️  Label cache cleared")
    
    def get_unread_threads(self, exclude_label: str = None, max_results: int = 10) -> List[Dict]:
        """
        Get unread email threads
        
        Args:
            exclude_label: Label to exclude from search
            max_results: Maximum number of threads to return
            
        Returns:
            List of thread objects
        """
        try:
            query = 'is:unread'
            if exclude_label:
                # Note: Gmail query uses label name, not ID
                query += f' -label:{exclude_label}'
            
            results = self.service.users().threads().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            threads = results.get('threads', [])
            
            # Get full thread details
            full_threads = []
            for thread in threads:
                thread_detail = self.service.users().threads().get(
                    userId='me',
                    id=thread['id']
                ).execute()
                full_threads.append(thread_detail)
            
            return full_threads
            
        except Exception as e:
            logger.error(f"❌ Error fetching threads: {e}")
            raise
    
    def add_label_to_thread(self, thread_id: str, label_name: str):
        """
        Add a label to a thread
        
        Args:
            thread_id: Thread ID
            label_name: Name of the label to add
        """
        try:
            label_id = self.get_or_create_label(label_name)
            
            self.service.users().threads().modify(
                userId='me',
                id=thread_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            logger.debug(f"✓ Added label '{label_name}' to thread {thread_id}")
            
        except Exception as e:
            logger.error(f"❌ Error adding label to thread: {e}")
            raise
    
    def extract_message_details(self, message: Dict) -> Dict:
        """
        ✅ FIXED: Extract relevant details from a Gmail message with Reply-To support
        
        Now handles Reply-To header for web forms correctly
        
        Args:
            message: Gmail message object
            
        Returns:
            Dictionary with extracted details including Reply-To handling
        """
        headers = message['payload'].get('headers', [])
        
        # Extract header values
        subject = ''
        sender = ''
        reply_to = ''  # ✅ NEW: Reply-To header
        date = ''
        message_id = ''
        
        for header in headers:
            name = header['name'].lower()
            value = header['value']
            
            if name == 'subject':
                subject = value
            elif name == 'from':
                sender = value
            elif name == 'reply-to':  # ✅ NEW: Capture Reply-To
                reply_to = value
            elif name == 'date':
                date = value
            elif name == 'message-id':
                message_id = value
        
        # Extract body
        body = self._extract_body(message['payload'])
        
        # ═══════════════════════════════════════════════════════════════
        # ✅ NEW: Reply-To Logic - Use Reply-To if present and valid
        # ═══════════════════════════════════════════════════════════════
        
        # Use Reply-To if present and valid (contains @)
        if reply_to and '@' in reply_to:
            effective_sender = reply_to
            logger.info(f"   📧 Using Reply-To: {reply_to} (Original From: {sender})")
        else:
            effective_sender = sender
            if reply_to:
                logger.warning(f"   ⚠️  Invalid Reply-To ignored: {reply_to}")
        
        # Extract sender name and email from effective sender
        sender_name = self._extract_sender_name(effective_sender)
        sender_email = self._extract_email_address(effective_sender)
        
        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': subject,
            'sender': effective_sender,  # ✅ FIXED: This is now Reply-To when present
            'sender_name': sender_name,
            'sender_email': sender_email,
            'date': date,
            'body': body,
            'message_id': message_id,
            'original_from': sender,  # ✅ NEW: Keep original From for reference
            'has_reply_to': bool(reply_to)  # ✅ NEW: Flag to know if Reply-To was used
        }
    
    def _extract_body(self, payload: Dict, max_length: int = 50000) -> str:
        """
        🔧 IMPROVED: Extract body text from message payload with robust HTML handling
        
        Strategy:
        1. Recursively walk through multipart structures
        2. Prefer text/plain over text/html
        3. Convert HTML to readable text with fallback chain
        4. Handle base64 decoding errors gracefully
        
        Args:
            payload: Message payload dictionary
            max_length: Maximum body length (default: 50KB)
            
        Returns:
            Plain text body (truncated if too long)
        """
        body_text = ''
        html_fallback = ''
        
        # Skip attachments
        filename = payload.get('filename', '')
        if filename:
            return ''
        
        # Case 1: Multipart message (has 'parts')
        if 'parts' in payload:
            for part in payload['parts']:
                mime = part.get('mimeType', '')
                
                # Recursive case: nested multipart
                if mime.startswith('multipart/'):
                    nested = self._extract_body(part, max_length)
                    if nested:
                        # If we find text/plain in nested, return immediately
                        if body_text == '':
                            body_text = nested
                        if not mime.endswith('alternative'):
                            # For multipart/mixed, return immediately
                            return nested
                
                # text/plain - HIGHEST PRIORITY
                elif mime == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        try:
                            body_text = _b64url_decode(data).decode('utf-8', errors='ignore')
                            return body_text  # Return immediately if we find text/plain
                        except Exception as e:
                            logger.warning(f"⚠️  Error decoding text/plain: {e}")
                
                # text/html - FALLBACK
                elif mime == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data and not html_fallback:  # Save only the first HTML found
                        try:
                            html = _b64url_decode(data).decode('utf-8', errors='ignore')
                            html_fallback = _html_to_text(html)
                        except Exception as e:
                            logger.warning(f"⚠️  Error decoding text/html: {e}")
            
            # If we didn't find text/plain, use converted HTML
            body_text = body_text if body_text else html_fallback
        
        # Case 2: Single part message (no 'parts')
        else:
            data = payload.get('body', {}).get('data', '')
            mime = payload.get('mimeType', '')
            
            if data:
                try:
                    decoded = _b64url_decode(data).decode('utf-8', errors='ignore')
                    
                    # If it's HTML, convert it
                    if mime == 'text/html':
                        body_text = _html_to_text(decoded)
                    else:
                        # Otherwise return as plain text
                        body_text = decoded
                        
                except Exception as e:
                    logger.warning(f"⚠️  Error decoding single part body: {e}")
                    return ''
        
        # Truncate if too long
        if body_text and len(body_text) > max_length:
            logger.warning(f"⚠️  Body too long ({len(body_text)} chars), truncating to {max_length}")
            return body_text[:max_length] + "\n\n[... corpo messaggio troncato ...]"
        
        return body_text
    
    def _extract_sender_name(self, from_field: str) -> str:
        """
        Extract sender name from From field
        
        Args:
            from_field: From header value
            
        Returns:
            Sender name
        """
        match = re.match(r'^"?(.+?)"?\s*<', from_field)
        if match:
            return match.group(1).strip()
        
        # If no name found, use email prefix
        email = self._extract_email_address(from_field)
        if email:
            return email.split('@')[0]
        
        return 'Utente'
    
    def _extract_email_address(self, from_field: str) -> str:
        """
        Extract email address from From field
        
        Args:
            from_field: From header value
            
        Returns:
            Email address
        """
        match = re.search(r'<(.+?)>', from_field)
        if match:
            return match.group(1)
        
        # If no brackets, assume the whole field is the email
        if '@' in from_field:
            return from_field.strip()
        
        return ''
    
    def send_reply(self, original_message: Dict, reply_text: str):
        """
        Send a reply to a message with intelligent Markdown formatting
        
        ✅ NEW: Automatically detects and converts Markdown to HTML
        ✅ Compatible with Reply-To headers
        
        Args:
            original_message: Original message dictionary
            reply_text: Reply text content (may contain Markdown)
        """
        try:
            # ═══════════════════════════════════════════════════════════════
            # ✅ STEP 1: Intelligent Markdown Detection & Conversion
            # ═══════════════════════════════════════════════════════════════
            
            plain_text, html_text, was_converted = self.markdown_formatter.format_email_response(reply_text)
            
            if was_converted:
                logger.info("   ✨ Markdown formatting applied")
            
            # ═══════════════════════════════════════════════════════════════
            # ✅ STEP 2: Create MIME message with appropriate parts
            # ═══════════════════════════════════════════════════════════════
            
            message = MIMEMultipart('alternative')
            
            # Set headers
            message['To'] = original_message['sender']  # ✅ This uses Reply-To when present!
            message['Subject'] = f"Re: {original_message['subject']}"
            message['In-Reply-To'] = original_message['message_id']
            message['References'] = original_message['message_id']
            
            # ═══════════════════════════════════════════════════════════════
            # ✅ STEP 3: Attach plain text part
            # ═══════════════════════════════════════════════════════════════
            
            text_part = MIMEText(plain_text, 'plain', 'utf-8')
            message.attach(text_part)
            
            # ═══════════════════════════════════════════════════════════════
            # ✅ STEP 4: Attach HTML part (with or without Markdown conversion)
            # ═══════════════════════════════════════════════════════════════
            
            if html_text:
                # Markdown was detected and converted
                html_body = self._create_html_reply_with_formatting(
                    html_text,
                    original_message['body']
                )
            else:
                # No Markdown, use standard plain HTML
                html_body = self._create_html_reply(
                    plain_text,
                    original_message['body']
                )
            
            html_part = MIMEText(html_body, 'html', 'utf-8')
            message.attach(html_part)
            
            # ═══════════════════════════════════════════════════════════════
            # ✅ STEP 5: Send the message
            # ═══════════════════════════════════════════════════════════════
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            # Send the message
            send_result = self.service.users().messages().send(
                userId='me',
                body={
                    'raw': raw_message,
                    'threadId': original_message['thread_id']
                }
            ).execute()
            
            logger.info(f"✓ Reply sent successfully to {original_message['sender']}")
            
            # Log if Reply-To was used
            if original_message.get('has_reply_to'):
                logger.info(f"   📧 Reply sent to Reply-To address (not original From)")
            
            # Log if Markdown was used
            if was_converted:
                logger.info(f"   ✨ Email sent with formatted HTML (Markdown → HTML)")
            
            return send_result
            
        except Exception as e:
            logger.error(f"❌ Error sending reply: {e}")
            raise
    
    def _create_html_reply(self, reply_text: str, original_body: str) -> str:
        """
        Create HTML formatted reply with quoted original message
        (Used when NO Markdown is detected)
        
        Args:
            reply_text: Reply text
            original_body: Original message body
            
        Returns:
            HTML formatted reply
        """
        # Convert plain text to HTML
        reply_html = reply_text.replace('\n', '<br>')
        original_html = original_body.replace('\n', '<br>')
        
        html = f'''
        <div style="font-family: Arial, Helvetica, sans-serif; font-size: 20px; color: #351c75;">
            {reply_html}
            <br><br>
            <hr>
            <blockquote style="border-left:2px solid #ccc; margin:0; padding-left:8px; color:#555;">
                {original_html}
            </blockquote>
            <br>
            <span style="font-size: 12px; color: #555;">
                ---<br>
                Messaggio generato con l'assistenza dell'IA.
            </span>
        </div>
        '''
        
        return html
    
    def _create_html_reply_with_formatting(self, formatted_html: str, original_body: str) -> str:
        """
        ✅ NEW: Create HTML formatted reply with properly converted Markdown
        
        This preserves the Markdown-converted HTML structure while adding
        the original quoted message below.
        
        Args:
            formatted_html: HTML text with converted Markdown formatting
            original_body: Original message body
            
        Returns:
            Complete HTML formatted reply
        """
        # Convert original body to HTML (escape special chars)
        original_html = original_body.replace('&', '&amp;')
        original_html = original_html.replace('<', '&lt;')
        original_html = original_html.replace('>', '&gt;')
        original_html = original_html.replace('\n', '<br>')
        
        html = f'''
        <div style="font-family: Arial, Helvetica, sans-serif; font-size: 20px; color: #351c75;">
            {formatted_html}
            <br><br>
            <hr style="border: none; border-top: 1px solid #ccc; margin: 20px 0;">
            <blockquote style="border-left: 2px solid #ccc; margin: 0; padding-left: 12px; color: #555; font-size: 13px;">
                {original_html}
            </blockquote>
            <br>
            <span style="font-size: 11px; color: #999;">
                ---<br>
                Messaggio generato con l'assistenza dell'IA.
            </span>
        </div>
        '''
        
        return html
    
    def build_conversation_history(self, messages: List[Dict], max_messages: int = 10) -> str:
        """
        Build conversation history from messages
        
        Args:
            messages: List of message dictionaries
            max_messages: Maximum number of messages to include (default: 10)
            
        Returns:
            Formatted conversation history string
        """
        # Limit number of messages to avoid overly long contexts
        if len(messages) > max_messages:
            logger.warning(f"⚠️  Thread with {len(messages)} messages, limiting to last {max_messages}")
            messages = messages[-max_messages:]
        
        history = []
        
        for msg in messages:
            if msg['sender_email'].lower() == self.user_email.lower():
                prefix = "Segreteria"
            else:
                prefix = f"Utente ({msg['sender']})"
            
            # Truncate very long messages
            body = msg['body']
            if len(body) > 2000:
                body = body[:2000] + "\n[... messaggio troncato ...]"
            
            history.append(f"{prefix}: {body}\n---")
        
        return '\n'.join(history)
    
    def extract_main_reply(self, content: str) -> str:
        """
        Extract main reply content, removing quoted text
        
        Args:
            content: Email content
            
        Returns:
            Main reply without quoted text
        """
        markers = [
            r'^>',  # Standard quote marker
            r'^On .* wrote:',  # English quote header
            r'^Il giorno .* ha scritto:',  # Italian quote header
            r'^-{3,}.*Original Message',  # Original message separator
            r'^_{3,}',  # Underscore separator
        ]
        
        lines = content.split('\n')
        result_lines = []
        
        for line in lines:
            # Check if this line starts a quoted section
            is_quote = False
            for marker in markers:
                if re.match(marker, line, re.IGNORECASE):
                    is_quote = True
                    break
            
            if is_quote:
                break  # Stop at first quote marker
                
            result_lines.append(line)
        
        return '\n'.join(result_lines).strip()
    
    # ========================================================================
    # HEALTH CHECK AND DIAGNOSTICS
    # ========================================================================
    
    def test_connection(self) -> Dict:
        """
        Test Gmail API connection and permissions
        
        Returns:
            Dictionary with test results
        """
        results = {
            'connection_ok': False,
            'profile_accessible': False,
            'can_list_messages': False,
            'can_create_labels': False,
            'errors': []
        }
        
        try:
            # Test basic connection
            profile = self.service.users().getProfile(userId='me').execute()
            results['connection_ok'] = True
            results['profile_accessible'] = True
            results['email_address'] = profile.get('emailAddress')
            results['messages_total'] = profile.get('messagesTotal')
            
            # Test listing messages
            messages_result = self.service.users().messages().list(
                userId='me',
                maxResults=1
            ).execute()
            results['can_list_messages'] = True
            
            # Test label creation (try to get or create test label)
            try:
                test_label_id = self.get_or_create_label('_TEST_LABEL_')
                results['can_create_labels'] = True
                
                # Clean up test label
                try:
                    self.service.users().labels().delete(
                        userId='me',
                        id=test_label_id
                    ).execute()
                except:
                    pass  # Ignore cleanup errors
                    
            except Exception as e:
                results['errors'].append(f"Cannot create labels: {str(e)}")
            
        except Exception as e:
            results['errors'].append(f"Connection error: {str(e)}")
        
        results['is_healthy'] = (
            results['connection_ok'] and 
            results['profile_accessible'] and 
            results['can_list_messages']
        )
        
        return results