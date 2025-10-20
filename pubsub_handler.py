"""
Pub/Sub handler module for Gmail notifications
Processes Gmail push notifications and extracts message data
"""

import base64
import json
from typing import Dict, Optional
import config

class PubSubHandler:
    """
    Handler for Gmail Pub/Sub notifications
    """
    
    def __init__(self):
        """Initialize Pub/Sub handler"""
        pass
    
    def parse_pubsub_message(self, event: Dict) -> Optional[Dict]:
        """
        Parse Pub/Sub message from Gmail notification
        
        Args:
            event: Cloud Function event dictionary (CloudEvent format)
            
        Returns:
            Parsed message data or None if invalid
        """
        try:
            # CloudEvents Gen2 format: event.data.message.data
            if 'message' not in event:
                print("No 'message' in Pub/Sub event")
                return None
            
            if 'data' not in event['message']:
                print("No 'data' in message")
                return None
            
            # Decode base64 data
            message_data = base64.b64decode(event['message']['data']).decode('utf-8')
            notification = json.loads(message_data)
            
            # Gmail notification structure:
            # {
            #   "emailAddress": "user@domain.com",
            #   "historyId": "12345"
            # }
            
            if 'emailAddress' not in notification:
                print("Invalid Gmail notification format")
                return None
            
            return {
                'email_address': notification['emailAddress'],
                'history_id': notification.get('historyId'),
                'timestamp': event.get('timestamp')
            }
            
        except Exception as e:
            print(f"Error parsing Pub/Sub message: {e}")
            return None
    
    def validate_notification(self, notification_data: Dict) -> bool:
        """
        Validate that notification is for our monitored account
        
        Args:
            notification_data: Parsed notification data
            
        Returns:
            True if valid
        """
        if not notification_data:
            return False
        
        # Check if notification is for our monitored email
        monitored_email = config.IMPERSONATE_EMAIL.lower()
        notification_email = notification_data.get('email_address', '').lower()
        
        if notification_email != monitored_email:
            print(f"Notification for different account: {notification_email} != {monitored_email}")
            return False
        
        return True
    
    def should_process_notification(
        self,
        notification_data: Dict,
        is_suspension_time: bool
    ) -> Dict:
        """
        Determine if notification should be processed
        
        Args:
            notification_data: Parsed notification data
            is_suspension_time: Whether in suspension period
            
        Returns:
            Dictionary with decision and reason
        """
        # Check if valid
        if not self.validate_notification(notification_data):
            return {
                'should_process': False,
                'reason': 'invalid_notification'
            }
        
        # Check suspension time
        if is_suspension_time:
            return {
                'should_process': False,
                'reason': 'suspension_time'
            }
        
        return {
            'should_process': True,
            'reason': 'valid_notification'
        }
