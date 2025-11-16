"""
Cloud Function to renew Gmail watch automatically
Deploy this separately and call it via Cloud Scheduler every 6 days
"""

import functions_framework
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

@functions_framework.http
def renew_gmail_watch(request):
    """Renew Gmail watch subscription"""
    
    try:
        # Configuration from environment
        impersonate_email = os.environ.get('IMPERSONATE_EMAIL')
        project_id = os.environ.get('GCP_PROJECT', 'ordinal-gear-472720-h5')
        topic_name = os.environ.get('PUBSUB_TOPIC', 'gmail-notifications')
        
        # Get service account credentials
        service_account_file = os.environ.get('SERVICE_ACCOUNT_FILE', 'service-account-key.json')
        
        with open(service_account_file, 'r') as f:
            service_account_info = json.load(f)
        
        # Create credentials
        scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        
        # Impersonate
        delegated_credentials = credentials.with_subject(impersonate_email)
        
        # Build service
        service = build('gmail', 'v1', credentials=delegated_credentials)
        
        # Renew watch
        request_body = {
            'topicName': f'projects/{project_id}/topics/{topic_name}',
            'labelIds': ['INBOX']
        }
        
        result = service.users().watch(
            userId='me',
            body=request_body
        ).execute()
        
        print(f"✓ Gmail watch renewed: historyId={result['historyId']}, expiration={result['expiration']}")
        
        return {
            'status': 'success',
            'historyId': result['historyId'],
            'expiration': result['expiration']
        }, 200
        
    except Exception as e:
        print(f"✗ Error renewing watch: {e}")
        return {
            'status': 'error',
            'message': str(e)
        }, 500