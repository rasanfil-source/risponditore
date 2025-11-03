"""
Script to setup Gmail Watch for Pub/Sub notifications
Run this once to configure Gmail to send push notifications
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# Configuration
SERVICE_ACCOUNT_FILE = 'service-account-key.json'
IMPERSONATE_EMAIL = 'info@parrocchiasanteugenio.it'
PROJECT_ID = 'ordinal-gear-472720-h5'
TOPIC_NAME = 'gmail-notifications'

def setup_gmail_watch():
    """Setup Gmail watch for push notifications"""
    
    # Load service account credentials
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        service_account_info = json.load(f)
    
    # Create credentials with Gmail scope
    scopes = ['https://www.googleapis.com/auth/gmail.readonly']
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
    )
    
    # Impersonate the target user
    delegated_credentials = credentials.with_subject(IMPERSONATE_EMAIL)
    
    # Build Gmail service
    service = build('gmail', 'v1', credentials=delegated_credentials)
    
    # Setup watch request
    request_body = {
        'topicName': f'projects/{PROJECT_ID}/topics/{TOPIC_NAME}',
        'labelIds': ['INBOX']  # Monitor only INBOX
    }
    
    try:
        # Call watch API
        result = service.users().watch(
            userId='me',
            body=request_body
        ).execute()
        
        print("✓ Gmail watch setup successful!")
        print(f"  History ID: {result['historyId']}")
        print(f"  Expiration: {result['expiration']}")
        print(f"\nNOTE: Watch expires after 7 days. You'll need to renew it.")
        
        return result
        
    except Exception as e:
        print(f"✗ Error setting up Gmail watch: {e}")
        raise

if __name__ == '__main__':
    setup_gmail_watch()