"""
Gmail service module for email operations
Handles reading, sending, and labeling emails
"""

import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Tuple
import re
from auth import get_gmail_service
from html2text import HTML2Text
import config

class GmailManager:
    def __init__(self, user_email: str = None):
        """Initialize Gmail manager with impersonated credentials"""
        self.service = get_gmail_service(user_email)
        self.user_email = user_email or config.IMPERSONATE_EMAIL
        
    def get_or_create_label(self, label_name: str) -> str:
        """
        Get or create a Gmail label
        
        Args:
            label_name: Name of the label
            
        Returns:
            Label ID
        """
        try:
            # List all labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
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
            
            print(f"Created new label: {label_name}")
            return created_label['id']
            
        except Exception as e:
            print(f"Error managing label: {e}")
            raise
    
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
                label_id = self.get_or_create_label(exclude_label)
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
            print(f"Error fetching threads: {e}")
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
            
        except Exception as e:
            print(f"Error adding label to thread: {e}")
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
    
    def _extract_body(self, payload: Dict) -> str:
        """
        Extract body text from message payload
        
        Args:
            payload: Message payload
            
        Returns:
            Plain text body
        """
        def _b64url_decode(data: str) -> bytes:
            if not data:
                return b''
            # Add missing padding for urlsafe base64
            padding_needed = (-len(data)) % 4
            if padding_needed:
                data += '=' * padding_needed
            return base64.urlsafe_b64decode(data)

        def _html_to_text(html: str) -> str:
            try:
                h = HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0
                return h.handle(html).strip()
            except Exception:
                return html

        body_text = ''

        # Recursively walk parts to find best candidate: prefer text/plain, fallback to text/html
        if 'parts' in payload:
            for part in payload['parts']:
                mime = part.get('mimeType', '')
                if mime.startswith('multipart/'):
                    nested = self._extract_body(part)
                    if nested:
                        return nested
                elif mime == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    try:
                        body_text = _b64url_decode(data).decode('utf-8', errors='ignore')
                        return body_text
                    except Exception:
                        pass
                elif mime == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    try:
                        html = _b64url_decode(data).decode('utf-8', errors='ignore')
                        body_text = _html_to_text(html)
                        # Keep looking in case a text/plain appears later, but remember this fallback
                    except Exception:
                        pass
            return body_text
        else:
            data = payload.get('body', {}).get('data', '')
            mime = payload.get('mimeType', '')
            if data:
                try:
                    decoded = _b64url_decode(data).decode('utf-8', errors='ignore')
                    if mime == 'text/html':
                        return _html_to_text(decoded)
                    return decoded
                except Exception:
                    return ''
        return ''
    
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
            
            print(f"Reply sent successfully to {original_message['sender']}")
            return send_result
            
        except Exception as e:
            print(f"Error sending reply: {e}")
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
        
        html = f'''
        <div style="font-family: Arial, Helvetica, sans-serif; font-size: 20px; color: #351c75;">
            {reply_html}
            <br><br>
            <hr>
            <blockquote style="border-left:2px solid #ccc; margin:0; padding-left:8px; color:#555;">
                {original_html}
            </blockquote>
            <br>
            <span style="font-size: 14px; color: #555;">
                ---<br>
                Messaggio generato con l'assistenza dell'IA.
            </span>
        </div>
        '''
        
        return html
    
    def build_conversation_history(self, messages: List[Dict]) -> str:
        """
        Build conversation history from messages
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Formatted conversation history string
        """
        history = []
        
        for msg in messages:
            if msg['sender_email'].lower() == self.user_email.lower():
                prefix = "Segreteria"
            else:
                prefix = f"Utente ({msg['sender']})"
            
            history.append(f"{prefix}: {msg['body']}\n---")
        
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
