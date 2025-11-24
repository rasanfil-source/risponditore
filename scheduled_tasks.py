"""
Scheduled tasks for Cloud Functions
Gestisce task periodici come recap eventi
"""

import functions_framework
import logging
from email_processor import EmailProcessor
from event_booking import EventBookingManager
from event_notifications import EventNotificationManager

logger = logging.getLogger(__name__)


@functions_framework.cloud_event
def daily_event_recap(cloud_event):
    """
    Cloud Scheduler triggered function
    Runs daily at 10:00 AM to send event recaps
    """
    logger.info('====== DAILY EVENT RECAP CHECK ======')
    
    try:
        # Initialize services
        processor = EmailProcessor()
        booking_manager = EventBookingManager(
            processor.sheets,
            processor.gemini
        )
        notification_manager = EventNotificationManager(
            booking_manager,
            processor.gmail
        )
        
        # Send recaps for tomorrow's events
        notification_manager.send_day_before_recap()
        
        logger.info('✅ Controllo recap completato')
        return {'status': 'success'}
        
    except Exception as e:
        logger.error(f'❌ Errore controllo recap: {e}')
        
        # Send error notification to parish
        try:
            processor.gmail.send_email(
                to='segreteria@parrocchia.it',  # ⚠️ MODIFICA
                subject='⚠️ Errore sistema recap eventi',
                body=f'Si è verificato un errore nel controllo giornaliero recap eventi:\n\n{e}\n\nVerificare il sistema.'
            )
        except:
            pass
        
        return {'status': 'error', 'message': str(e)}
