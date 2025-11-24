"""
Event Notification Manager - Sistema notifiche automatiche eventi
Versione Cloud Functions (Python)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
from zoneinfo import ZoneInfo
from gmail_service import GmailManager
from event_booking import EventBookingManager

logger = logging.getLogger(__name__)

ITALIAN_TZ = ZoneInfo("Europe/Rome")
PARISH_EMAIL = "info@parrocchiasanteugenio.it"  # ⚠️ MODIFICA CON EMAIL PARROCCHIA


class EventNotificationManager:
    """Gestisce notifiche automatiche per eventi con posti limitati"""
    
    def __init__(
        self,
        booking_manager: EventBookingManager,
        gmail_manager: GmailManager
    ):
        self.booking_manager = booking_manager
        self.gmail = gmail_manager
        self.notifications_sheet = 'NotificheEventi'
    
    def send_event_full_notification(
        self,
        event_name: str,
        max_seats: int,
        event_date: datetime = None
    ):
        """Invia notifica immediata quando evento raggiunge limite massimo"""
        if self._was_notification_sent(event_name, 'full'):
            logger.info(f"ℹ️  Notifica 'completo' già inviata per '{event_name}'")
            return
        
        subject = f"🎫 Evento completo: {event_name}"
        
        date_str = event_date.strftime('%d/%m/%Y') if event_date else 'Data non specificata'
        
        body = f"""Gentile Segreteria,

l'evento "{event_name}" ({date_str}) ha raggiunto il limite massimo di partecipanti.

📊 STATO PRENOTAZIONI:
• Posti totali: {max_seats}
• Posti occupati: {max_seats}
• Stato: COMPLETO ✅

Le prenotazioni successive riceveranno una risposta automatica indicando che i posti sono esauriti.

Un riepilogo finale verrà inviato il giorno precedente l'evento.

---
Questa è una notifica automatica del sistema di gestione prenotazioni."""
        
        try:
            self.gmail.send_email(
                to=PARISH_EMAIL,
                subject=subject,
                body=body
            )
            self._record_notification(event_name, 'full', max_seats, max_seats)
            logger.info(f"✅ Notifica 'evento completo' inviata per '{event_name}'")
        except Exception as e:
            logger.error(f"❌ Errore invio notifica: {e}")
    
    def send_day_before_recap(self):
        """Invia riepilogo per eventi di domani"""
        logger.info('🔔 Controllo recap eventi per domani...')
        
        tomorrow = datetime.now(ITALIAN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow += timedelta(days=1)
        
        tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)
        
        # Carica eventi
        kb = self.booking_manager.sheets.load_knowledge_base()
        events = self.booking_manager.parse_events_from_kb(kb)
        
        for event in events:
            if not event.get('event_date'):
                logger.warning(f"⚠️  Evento '{event['name']}' senza data, skip recap")
                continue
            
            event_date = event['event_date']
            if isinstance(event_date, str):
                event_date = datetime.fromisoformat(event_date)
            
            # Verifica se evento è domani
            if tomorrow <= event_date <= tomorrow_end:
                logger.info(f"📅 Evento domani: '{event['name']}'")
                
                if self._was_notification_sent(event['name'], 'recap_day_before'):
                    logger.info(f"ℹ️  Recap già inviato per '{event['name']}'")
                    continue
                
                self._send_event_recap(
                    event['name'],
                    event['max_seats'],
                    event_date
                )
    
    def _send_event_recap(self, event_name: str, max_seats: int, event_date: datetime):
        """Invia riepilogo dettagliato evento"""
        availability = self.booking_manager.check_availability(event_name, max_seats)
        bookings = self._get_event_bookings(event_name)
        
        subject = f"📋 Riepilogo prenotazioni: {event_name}"
        
        date_str = event_date.strftime('%d/%m/%Y')
        
        body = f"""Gentile Segreteria,

riepilogo prenotazioni per l'evento di DOMANI:

🎫 EVENTO: {event_name}
📅 DATA: {date_str}

📊 STATO PRENOTAZIONI:
• Posti totali: {max_seats}
• Posti occupati: {availability['current']}
• Posti disponibili: {max_seats - availability['current']}
• Stato: {'POSTI DISPONIBILI' if availability['available'] else 'COMPLETO ✅'}

"""
        
        if bookings:
            body += f"👥 ELENCO PARTECIPANTI ({len(bookings)}):\n\n"
            
            for i, booking in enumerate(bookings, 1):
                booking_date = datetime.fromisoformat(booking['date']) if isinstance(booking['date'], str) else booking['date']
                date_formatted = booking_date.strftime('%d/%m/%Y %H:%M')
                
                body += f"{i}. {booking['name']} ({booking['email']})\n"
                body += f"   Prenotato: {date_formatted}\n\n"
        else:
            body += "⚠️  NESSUN PARTECIPANTE REGISTRATO\n\n"
        
        body += """---
Questa è una notifica automatica del sistema di gestione prenotazioni."""
        
        try:
            self.gmail.send_email(
                to=PARISH_EMAIL,
                subject=subject,
                body=body
            )
            self._record_notification(
                event_name,
                'recap_day_before',
                availability['current'],
                max_seats
            )
            logger.info(f"✅ Recap inviato per '{event_name}' - {availability['current']}/{max_seats} partecipanti")
        except Exception as e:
            logger.error(f"❌ Errore invio recap: {e}")
    
    def _get_event_bookings(self, event_name: str) -> List[Dict]:
        """Ottiene lista prenotazioni confermate per evento"""
        data = self.booking_manager._get_sheet_data()
        
        bookings = []
        for row in data[1:]:  # Skip header
            if row[0] == event_name and row[4] == 'Confermato':
                bookings.append({
                    'email': row[1],
                    'name': row[2],
                    'date': row[3]
                })
        
        return bookings
    
    def _was_notification_sent(self, event_name: str, notification_type: str) -> bool:
        """Verifica se notifica già inviata"""
        try:
            data = self.booking_manager.sheets.read_sheet(self.notifications_sheet)
            
            for row in data[1:]:  # Skip header
                if row[0] == event_name and row[1] == notification_type:
                    return True
            
            return False
        except:
            # Foglio non esiste, crea
            self._create_notifications_sheet()
            return False
    
    def _record_notification(
        self,
        event_name: str,
        notification_type: str,
        current_bookings: int,
        max_seats: int
    ):
        """Registra notifica inviata"""
        try:
            self.booking_manager.sheets.append_row(
                self.notifications_sheet,
                [
                    event_name,
                    notification_type,
                    datetime.now(ITALIAN_TZ).isoformat(),
                    current_bookings,
                    max_seats
                ]
            )
            logger.info(f"📝 Notifica registrata: {event_name} - {notification_type}")
        except:
            self._create_notifications_sheet()
            self._record_notification(event_name, notification_type, current_bookings, max_seats)
    
    def _create_notifications_sheet(self):
        """Crea foglio tracciamento notifiche"""
        header = ['Evento', 'Tipo Notifica', 'Data Invio', 'N. Prenotazioni', 'Max Posti']
        self.booking_manager.sheets.create_sheet(self.notifications_sheet, header)
        logger.info(f"📋 Foglio '{self.notifications_sheet}' creato")
