"""
Main entry point for Parish Secretary Cloud Function (Pub/Sub triggered)
Processes Gmail notifications via Pub/Sub events
"""

import json
import logging
from typing import Dict
import functions_framework
from cloudevents.http import CloudEvent

import config
from auth import verify_authentication
from pubsub_handler import PubSubHandler
from email_processor import EmailProcessor
from utils import is_in_suspension_time

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize handlers (created once per cold start)
pubsub_handler = None
email_processor = None
_init_done = False

def init_services():
    """Initialize services (lazy loading)"""
    global pubsub_handler, email_processor, _init_done

    # Istanzia i manager una sola volta per cold start
    if pubsub_handler is None:
        pubsub_handler = PubSubHandler()
    if email_processor is None:
        email_processor = EmailProcessor()

    # CRITICAL FIX: Verifica autenticazione SOLO a cold start (non ad ogni invocazione)
    if not _init_done:
        try:
            if not verify_authentication():
                logger.error("Authentication failed at cold start")
            else:
                logger.info("✓ Authentication verified at cold start")
        except Exception as e:
            logger.error(f"Auth check error at init: {e}")
        _init_done = True


@functions_framework.cloud_event
def process_gmail_notification(cloud_event: CloudEvent):
    """
    Cloud Function entry point for Pub/Sub triggered by Gmail
    
    Args:
        cloud_event: CloudEvent from Pub/Sub
    """
    try:
        # Check if system is manually paused
        import os
        if os.environ.get('SYSTEM_PAUSED', 'false').lower() == 'true':
            logger.warning("⏸️  Sistema in PAUSA (SYSTEM_PAUSED=true)")
            return
        
        logger.info(f"Received Pub/Sub event: {cloud_event.data}")
        
        # Initialize services
        init_services()
        
        # Parse Pub/Sub message
        notification_data = pubsub_handler.parse_pubsub_message(cloud_event.data)
        
        if not notification_data:
            logger.warning("Invalid notification data")
            return
        
        logger.info(f"Processing notification for: {notification_data.get('email_address')}")
        
        # Check if in suspension time
        in_suspension = is_in_suspension_time()
        
        # Validate notification
        decision = pubsub_handler.should_process_notification(
            notification_data,
            in_suspension
        )
        
        if not decision['should_process']:
            logger.info(f"Skipping notification: {decision['reason']}")
            return
        
        # CRITICAL FIX: CONDITIONAL AUTH CHECK - Only if explicitly enabled
        if config.VERIFY_AUTH_ON_EACH_INVOCATION:
            logger.info("Verifying authentication (per-invocation check enabled)")
            if not verify_authentication():
                logger.error("Authentication failed")
                return
        
        # Process new messages
        result = email_processor.process_new_messages()
        
        logger.info(f"Processing complete: {result}")
        
    except Exception as e:
        logger.error(f"Error in process_gmail_notification: {e}", exc_info=True)
        # Don't raise - we don't want Pub/Sub to retry on permanent errors


# HTTP endpoint for manual testing and monitoring
@functions_framework.http
def process_emails_http(request):
    """
    HTTP endpoint for manual testing and Cloud Scheduler
    
    Args:
        request: Flask request object
        
    Returns:
        JSON response
    """
    try:
        # Handle CORS preflight
        if request.method == 'OPTIONS':
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Max-Age': '3600'
            }
            return ('', 204, headers)
        
        # Set CORS headers
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        }
        
        # Check suspension time
        if is_in_suspension_time():
            result = {
                'status': 'suspended',
                'message': 'Service suspended for working hours'
            }
            return (json.dumps(result), 200, headers)
        
        # Initialize services
        init_services()
        
        # CRITICAL FIX: CONDITIONAL AUTH CHECK - Only if explicitly enabled
        if config.VERIFY_AUTH_ON_EACH_INVOCATION:
            logger.info("Verifying authentication (per-invocation check enabled)")
            if not verify_authentication():
                result = {
                    'status': 'error',
                    'message': 'Authentication failed'
                }
                return (json.dumps(result), 500, headers)
        
        # Process emails
        result = email_processor.process_new_messages()
        
        # Return JSON response
        return (json.dumps(result), 200, headers)
        
    except Exception as e:
        logger.error(f"Error in HTTP endpoint: {e}", exc_info=True)
        error_response = {
            'status': 'error',
            'message': str(e)
        }
        return (json.dumps(error_response), 500, {'Content-Type': 'application/json'})


# For local testing
if __name__ == "__main__":
    import os
    
    # Set up environment variables for local testing
    os.environ['IMPERSONATE_EMAIL'] = 'your-email@yourdomain.com'
    os.environ['SPREADSHEET_ID'] = 'your-spreadsheet-id'
    os.environ['GEMINI_API_KEY'] = 'your-api-key'
    
    # Test HTTP endpoint
    class MockRequest:
        method = 'POST'
    
    result = process_emails_http(MockRequest())
    print(f"Result: {result}")
