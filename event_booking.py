"""
Event Booking Manager - Gestione posti limitati per eventi
Versione Cloud Functions (Python)
"""

import re
import logging
from typing import List, Dict, Optional
from datetime import datetime
from sheets_service import SheetsManager
from gemini_service import GeminiService

logger = logging.getLogger(__name__)


class EventBookingManager:
    """Gestisce prenotazioni per eventi con posti limitati"""
    
    def __init__(self, sheets_manager: SheetsManager, gemini_service: GeminiService):
        self.sheets = sheets_manager
        self.gemini = gemini_service
        self.sheet_name = 'Prenotazioni'
        self.events_cache = None
    
    def parse_events_from_kb(self, knowledge_base: str) -> List[Dict]:
        """
        Estrae eventi con posti limitati dalla KB
        Pattern: "Posti limitati. Max: NN" o "Max posti: NN"
        """
        events = []
        pattern = r'(?:posti limitati[.:]\s*max:\s*(\d+)|max\s*posti:\s*(\d+))'
        
        # Split KB in sezioni
        sections = re.split(r'\n\s*\n', knowledge_base)
        
        for section in sections:
            matches = re.finditer(pattern, section, re.IGNORECASE)
            for match in matches:
                max_seats = int(match.group(1) or match.group(2))
                event_name = self._extract_event_name(section)
                event_date = self._extract_event_date(section)
                
                if event_name:
                    events.append({
                        'name': event_name,
                        'max_seats': max_seats,
                        'event_date': event_date,
                        'text_section': section
                    })
                    logger.info(f"📅 Evento trovato: '{event_name}' - Max {max_seats} posti - Data: {event_date or 'Non specificata'}")
        
        self.events_cache = events
        return events
    
    def _extract_event_name(self, section: str) -> Optional[str]:
        """Estrae nome evento dalla sezione KB"""
        lines = [l.strip() for l in section.split('\n') if l.strip()]
        if not lines:
            return None
        
        # Prima riga significativa
        name = lines[0]
        name = re.sub(r'^[#*-]\s*', '', name)  # Rimuovi markdown
        name = re.sub(r'[.:]\s*$', '', name)   # Rimuovi : o .
        
        if len(name) > 100:
            name = name[:97] + '...'
        
        return name
    
    def _extract_event_date(self, section: str) -> Optional[datetime]:
        """Estrae data evento dalla sezione KB"""
        month_names = {
            'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
            'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
            'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
        }
        
        patterns = [
            # 15 dicembre 2025 o 15 dicembre
            (r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+(\d{4}))?', 'text'),
            # 15/12/2025
            (r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', 'numeric_full'),
            # 15/12
            (r'(\d{1,2})[\/\-\.](\d{1,2})(?![\/\-\.\d])', 'numeric_short')
        ]
        
        for pattern, ptype in patterns:
            match = re.search(pattern, section, re.IGNORECASE)
            if match:
                try:
                    if ptype == 'text':
                        day = int(match.group(1))
                        month = month_names[match.group(2).lower()]
                        year = int(match.group(3)) if match.group(3) else datetime.now().year
                    elif ptype == 'numeric_full':
                        day = int(match.group(1))
                        month = int(match.group(2))
                        year = int(match.group(3))
                    else:  # numeric_short
                        day = int(match.group(1))
                        month = int(match.group(2))
                        year = datetime.now().year
                    
                    if 1 <= day <= 31 and 1 <= month <= 12:
                        event_date = datetime(year, month, day)
                        
                        # Se data passata senza anno esplicito, assume anno prossimo
                        if event_date < datetime.now() and ptype in ['text', 'numeric_short'] and not match.group(3):
                            event_date = datetime(year + 1, month, day)
                        
                        return event_date
                except ValueError:
                    continue
        
        return None
    
    def identify_event_from_email(
        self,
        email_subject: str,
        email_body: str,
        available_events: List[Dict]
    ) -> Optional[Dict]:
        """Identifica evento dalla email usando Gemini"""
        if not available_events:
            return None
        
        events_list = '\n'.join([f"- {e['name']}" for e in available_events])
        
        prompt = f"""Analizza questa email e identifica a quale evento si riferisce.

EVENTI DISPONIBILI CON POSTI LIMITATI:
{events_list}

EMAIL:
Oggetto: {email_subject}
Testo: {email_body[:500]}

ISTRUZIONI:
1. Se l'email menziona uno degli eventi sopra, rispondi SOLO con il nome esatto dell'evento
2. Se non è chiaro o non menziona eventi, rispondi: NESSUNO
3. Non aggiungere spiegazioni, SOLO il nome evento o NESSUNO

Risposta:"""
        
        try:
            response = self.gemini.generate_response(
                prompt,
                temperature=0.1,
                max_tokens=50
            )
            
            event_name = response.strip()
            
            if event_name == 'NESSUNO':
                return None
            
            # Verifica match
            for event in available_events:
                if (event['name'].lower() in event_name.lower() or
                    event_name.lower() in event['name'].lower()):
                    logger.info(f"✓ Evento identificato: '{event['name']}'")
                    return event
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Errore identificazione evento: {e}")
            return None
    
    def check_availability(self, event_name: str, max_seats: int) -> Dict:
        """Verifica disponibilità posti"""
        data = self._get_sheet_data()
        
        confirmed_count = sum(
            1 for row in data[1:]  # Skip header
            if row[0] == event_name and row[4] == 'Confermato'
        )
        
        available = confirmed_count < max_seats
        
        logger.info(f"📊 Evento '{event_name}': {confirmed_count}/{max_seats} posti occupati")
        
        return {
            'available': available,
            'current': confirmed_count,
            'max': max_seats
        }
    
    def register_booking(
        self,
        event_name: str,
        email: str,
        sender_name: str,
        max_seats: int
    ) -> Dict:
        """Registra prenotazione (gestisce doppie richieste)"""
        data = self._get_sheet_data()
        
        # Cerca prenotazione esistente
        existing_row = None
        for i, row in enumerate(data[1:], start=2):
            if row[0] == event_name and row[1] == email:
                existing_row = i
                break
        
        timestamp = datetime.now().isoformat()
        
        if existing_row:
            # Aggiorna timestamp
            self.sheets.update_cell(self.sheet_name, existing_row, 4, timestamp)
            self.sheets.update_cell(self.sheet_name, existing_row, 6, 'Richiesta duplicata - aggiornato')
            
            logger.info(f"♻️  Prenotazione aggiornata per {email}")
            
            return {
                'type': 'updated',
                'message': 'Prenotazione già presente, aggiornata'
            }
        
        # Verifica disponibilità (race condition check)
        availability = self.check_availability(event_name, max_seats)
        if not availability['available']:
            return {
                'type': 'full',
                'message': 'Posti esauriti durante la registrazione'
            }
        
        # Nuova prenotazione
        new_position = availability['current'] + 1
        new_row = [
            event_name,
            email,
            sender_name,
            timestamp,
            'Confermato',
            f'Posto {new_position}/{max_seats}'
        ]
        
        self.sheets.append_row(self.sheet_name, new_row)
        
        logger.info(f"✅ Prenotazione registrata: {sender_name} - Posto {new_position}/{max_seats}")
        
        return {
            'type': 'confirmed',
            'position': new_position,
            'message': f'Prenotazione confermata! Sei il partecipante n. {new_position} su {max_seats} posti disponibili.'
        }
    
    def cancel_booking(self, event_name: str, email: str) -> Dict:
        """Cancella prenotazione"""
        data = self._get_sheet_data()
        
        for i, row in enumerate(data[1:], start=2):
            if row[0] == event_name and row[1] == email and row[4] == 'Confermato':
                self.sheets.update_cell(self.sheet_name, i, 5, 'Cancellato')
                self.sheets.update_cell(self.sheet_name, i, 4, datetime.now().isoformat())
                
                logger.info(f"🗑️  Prenotazione cancellata: {email} per '{event_name}'")
                
                return {
                    'success': True,
                    'message': 'Prenotazione cancellata con successo'
                }
        
        return {
            'success': False,
            'message': 'Nessuna prenotazione attiva trovata'
        }
    
    def _get_sheet_data(self) -> List[List]:
        """Ottiene dati foglio (crea se non esiste)"""
        try:
            return self.sheets.read_sheet(self.sheet_name)
        except:
            # Crea foglio con header
            self._create_sheet()
            return [['Evento', 'Email', 'Nome', 'Data Richiesta', 'Stato', 'Note']]
    
    def _create_sheet(self):
        """Crea foglio Prenotazioni"""
        header = ['Evento', 'Email', 'Nome', 'Data Richiesta', 'Stato', 'Note']
        self.sheets.create_sheet(self.sheet_name, header)
        logger.info(f"📋 Foglio '{self.sheet_name}' creato")
