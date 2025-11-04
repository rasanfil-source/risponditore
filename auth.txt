"""
Authentication module for Google Workspace with Domain-Wide Delegation
Handles service account impersonation for Gmail and Sheets access
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import os
from typing import Optional
from google.cloud import secretmanager
import config

def get_service_account_credentials():
    """
    Load service account credentials from file or Secret Manager
    """
    # Try to load from Secret Manager first (for production)
    if os.environ.get('USE_SECRET_MANAGER', 'false').lower() == 'true':
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get('GCP_PROJECT')
        secret_name = f"projects/{project_id}/secrets/service-account-key/versions/latest"
        
        try:
            response = client.access_secret_version(request={"name": secret_name})
            secret_value = response.payload.data.decode("UTF-8")
            return json.loads(secret_value)
        except Exception as e:
            print(f"Error loading from Secret Manager: {e}")
            # Fall back to file
    
    # Load from file
    if os.path.exists(config.SERVICE_ACCOUNT_FILE):
        with open(config.SERVICE_ACCOUNT_FILE, 'r') as f:
            return json.load(f)
    
    raise ValueError("No service account credentials found")

def get_delegated_credentials(scopes: list, subject: str = None):
    """
    Create credentials with domain-wide delegation for impersonation
    
    Args:
        scopes: List of OAuth2 scopes needed
        subject: Email of the user to impersonate (defaults to config.IMPERSONATE_EMAIL)
    
    Returns:
        Credentials object configured for impersonation
    """
    if subject is None:
        subject = config.IMPERSONATE_EMAIL
    
    service_account_info = get_service_account_credentials()
    
    # Create credentials from service account
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
    )
    
    # CRUCIAL: Delegate (impersonate) the target user
    delegated_credentials = credentials.with_subject(subject)
    
    return delegated_credentials

def get_gmail_service(user_email: str = None):
    """
    Get Gmail API service with impersonation
    
    Args:
        user_email: Email of the user to impersonate (optional)
    
    Returns:
        Gmail API service object
    """
    scopes = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.labels'
    ]
    
    credentials = get_delegated_credentials(scopes, user_email)
    
    service = build('gmail', 'v1', credentials=credentials)
    return service

def get_sheets_service(user_email: str = None):
    """
    Get Google Sheets API service with impersonation
    
    Args:
        user_email: Email of the user to impersonate (optional)
    
    Returns:
        Sheets API service object
    """
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    credentials = get_delegated_credentials(scopes, user_email)
    
    service = build('sheets', 'v4', credentials=credentials)
    return service

def verify_authentication():
    """
    Test function to verify that authentication and impersonation work
    """
    try:
        gmail_service = get_gmail_service()
        profile = gmail_service.users().getProfile(userId='me').execute()
        print(f"Successfully authenticated as: {profile['emailAddress']}")
        
        sheets_service = get_sheets_service()
        spreadsheet = sheets_service.spreadsheets().get(
            spreadsheetId=config.SPREADSHEET_ID
        ).execute()
        print(f"Successfully accessed spreadsheet: {spreadsheet['properties']['title']}")
        
        return True
    except Exception as e:
        print(f"Authentication verification failed: {e}")
        return False
