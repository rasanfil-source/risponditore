"""
Gmail service module for email operations
Handles reading, sending, and labeling emails with improved HTML handling
"""

import base64
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
import re
from auth import get_gmail_service
from html2text import HTML2Text
import config

logger = logging.getLogger(__name__)


# ============ Helper Functions ============

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
    Convert HTML to plain text using html2text
    
    Args:
        html: HTML string
        
    Returns:
        Plain text representation
    """
    try:
        h = HTML2Text()
        h.ignore_links = False  # Mantiene i link come [text](url)
        h.ignore_images = True
        h.body_width = 0  # No line wrapping
        h.ignore_emphasis = False  # Mantiene *bold* e _italic_
        return h.handle(html).strip()
    except Exception as e:
        logger.warning(f"⚠️  HTML to text conversion error: {e}")
        return html  # Fallback: ritorna HTML grezzo


# ============ GmailManager Class ============

class GmailManager:
    def __init__(self, user_email: str = None):
        """Initialize Gmail manager with impersonated credentials"""
        self.service = get_gmail_service(user_email)
        self.user_email = user_email or config.IMPERSONATE_EMAIL
        
        # CRITICAL FIX: Add label cache to avoid repeated API calls
        self._label_cache: Dict[str, str] = {}
        logger.info("✓ Gmail label cache initialized")
        
    def get_or_create_label(self, label_name: str) -> str:
        """
        Get or create a Gmail label with caching
        
        Args:
            label_name: Name of the label
            
        Returns:
            Label ID
        """
        # CRITICAL FIX: Check cache first
        if label_name in self._label_cache:
            logger.debug(f"📦 Label '{label_name}' found in cache: {self._label_cache[label_name]}")
            return self._label_cache[label_name]
        
        try:
            # List all labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    # Cache the result
                    self._label_cache[label_name] = label['id']
                    logger.info(f"✓ Label '{label_name}' found: {label['id']}")
                    return label['id']
            
            # Create new label
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
            logger.info(f"Created new label: {label_name} ({created_label['id']})")
            return created_label['id']
            
        except Exception as e:
            logger.error(f"Error managing label: {e}")
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
            logger.error(f"Error fetching threads: {e}")
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
            
            logger.debug(f"Added label '{label_name}' to thread {thread_id}")
            
        except Exception as e:
            logger.error(f"Error adding label to thread: {e}")
            raise
    
    def extract_message_details(self, message: Dict) -> Dict:
        """
        Extract relevant details from a Gmail message
        
        Args:
            message: Gmail message object
            
        Returns:
            Dictionary with extracted details
        """
        headers = message['payload'].get('headers', [])
        
        # Extract header values
        subject = ''
        sender = ''
        date = ''
        message_id = ''
        
        for header in headers:
            name = header['name'].lower()
            value = header['value']
            
            if name == 'subject':
                subject = value
            elif name == 'from':
                sender = value
            elif name == 'date':
                date = value
            elif name == 'message-id':
                message_id = value
        
        # Extract body
        body = self._extract_body(message['payload'])
        
        # Extract sender name
        sender_name = self._extract_sender_name(sender)
        
        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'subject': subject,
            'sender': sender,
            'sender_name': sender_name,
            'sender_email': self._extract_email_address(sender),
            'date': date,
            'body': body,
            'message_id': message_id
        }
    
    def _extract_body(self, payload: Dict, max_length: int = 50000) -> str:
        """
        Extract body text from message payload with improved HTML handling
        
        Strategy:
        1. Recursively walk through multipart structures
        2. Prefer text/plain over text/html
        3. Convert HTML to readable text if needed
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
                        # Se troviamo text/plain in nested, ritorna subito
                        if body_text == '':
                            body_text = nested
                        if not mime.endswith('alternative'):
                            # Per multipart/mixed, ritorna subito
                            return nested
                
                # text/plain - PRIORITÀ MASSIMA
                elif mime == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        try:
                            body_text = _b64url_decode(data).decode('utf-8', errors='ignore')
                            return body_text  # Ritorna subito se troviamo text/plain
                        except Exception as e:
                            logger.warning(f"⚠️  Error decoding text/plain: {e}")
                
                # text/html - FALLBACK
                elif mime == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data and not html_fallback:  # Salva solo il primo HTML trovato
                        try:
                            html = _b64url_decode(data).decode('utf-8', errors='ignore')
                            html_fallback = _html_to_text(html)
                        except Exception as e:
                            logger.warning(f"⚠️  Error decoding text/html: {e}")
            
            # Se non abbiamo trovato text/plain, usa HTML convertito
            body_text = body_text if body_text else html_fallback
        
        # Case 2: Single part message (no 'parts')
        else:
            data = payload.get('body', {}).get('data', '')
            mime = payload.get('mimeType', '')
            
            if data:
                try:
                    decoded = _b64url_decode(data).decode('utf-8', errors='ignore')
                    
                    # Se è HTML, convertilo
                    if mime == 'text/html':
                        body_text = _html_to_text(decoded)
                    else:
                        # Altrimenti ritorna come plain text
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
        Send a reply to a message
        
        Args:
            original_message: Original message dictionary
            reply_text: Reply text content
        """
        try:
            # Create reply message
            message = MIMEMultipart('alternative')
            
            # Set headers
            message['To'] = original_message['sender']
            message['Subject'] = f"Re: {original_message['subject']}"
            message['In-Reply-To'] = original_message['message_id']
            message['References'] = original_message['message_id']
            
            # Create plain text part
            text_part = MIMEText(reply_text, 'plain', 'utf-8')
            
            # Create HTML part with quoted original message
            html_body = self._create_html_reply(reply_text, original_message['body'])
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            message.attach(text_part)
            message.attach(html_part)
            
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
            
            logger.info(f"Reply sent successfully to {original_message['sender']}")
            return send_result
            
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            raise
    
    def _create_html_reply(self, reply_text: str, original_body: str) -> str:
        """
        Create HTML formatted reply with quoted original message
        
        Args:
            reply_text: Reply text
            original_body: Original message body
            
        Returns:
            HTML formatted reply
        """
        # Convert plain text to HTML
        reply_html = reply_text.replace('\n', '<br>')
        original_html = original_body.replace('\n', '<br>')
        
        # MEDIUM PRIORITY FIX: Reduced font-size 20px for better compatibility
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
    
    def build_conversation_history(self, messages: List[Dict], max_messages: int = 10) -> str:
        """
        Build conversation history from messages
        
        Args:
            messages: List of message dictionaries
            max_messages: Maximum number of messages to include (default: 10)
            
        Returns:
            Formatted conversation history string
        """
        # Limita il numero di messaggi per evitare contesti troppo lunghi
        if len(messages) > max_messages:
            logger.warning(f"⚠️  Thread con {len(messages)} messaggi, limitando a ultimi {max_messages}")
            messages = messages[-max_messages:]
        
        history = []
        
        for msg in messages:
            if msg['sender_email'].lower() == self.user_email.lower():
                prefix = "Segreteria"
            else:
                prefix = f"Utente ({msg['sender']})"
            
            # Tronca messaggi molto lunghi
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
