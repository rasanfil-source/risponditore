"""
Utility functions for date calculations, filters, and text processing
"""

from datetime import datetime, timedelta
import re
import logging
from typing import Optional, List, Dict
from email.utils import parseaddr
import config
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Definisci il fuso orario italiano
ITALIAN_TZ = ZoneInfo("Europe/Rome")

def is_in_suspension_time() -> bool:
    """
    Check if current time is within suspension hours
    """
    now = datetime.now(ITALIAN_TZ)
    month = now.month
    day = now.day
    
    if is_in_special_period(month, day):
        return False
    
    weekday = now.weekday()
    hour = now.hour
    
    if weekday in config.SUSPENSION_HOURS:
        for start_hour, end_hour in config.SUSPENSION_HOURS[weekday]:
            if start_hour <= hour < end_hour:
                return True
    return False

def is_in_special_period(month: int, day: int) -> bool:
    """
    Check if date is in a special period (holidays, vacations)
    """
    for (start_month, start_day), (end_month, end_day) in config.SPECIAL_PERIODS:
        if start_month > end_month:  # Periodo che attraversa fine anno
            if month >= start_month and day >= start_day:
                return True
            if month <= end_month and day <= end_day:
                return True
        else:
            if month == start_month and day >= start_day:
                if month == end_month:
                    return day <= end_day
                return True
            elif start_month < month < end_month:
                return True
            elif month == end_month and day <= end_day:
                return True
    
    for holiday_month, holiday_day in config.HOLIDAYS:
        if month == holiday_month and day == holiday_day:
            return True
    
    return False

def get_current_season(date_obj: datetime = None) -> str:
    """
    Determine current season (summer/winter)
    """
    if date_obj is None:
        date_obj = datetime.now(ITALIAN_TZ)
    
    month = date_obj.month
    day = date_obj.day
    
    if month == config.SUMMER_START[0] and day >= config.SUMMER_START[1]:
        return 'estivo'
    elif config.SUMMER_START[0] < month < config.SUMMER_END[0]:
        return 'estivo'
    elif month == config.SUMMER_END[0] and day <= config.SUMMER_END[1]:
        return 'estivo'
    return 'invernale'

def get_special_day_greeting(date_obj: datetime = None) -> Optional[str]:
    """
    Get special day greeting if applicable
    """
    if date_obj is None:
        date_obj = datetime.now(ITALIAN_TZ)
    
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    today = date_obj.date()
    
    greetings = {
        (1, 1): 'Buon Capodanno!',
        (1, 6): 'Buona Epifania!',
        (8, 15): 'Auguri per oggi!',
        (11, 1): 'Buona festa di Ognissanti!',
        (12, 8): 'Buona Immacolata!',
        (12, 25): 'Buon Natale!'
    }
    
    if (month, day) in greetings:
        return greetings[(month, day)]
    
    # Pasqua e feste mobili
    easter = get_western_easter_date(year)
    easter_end = easter + timedelta(days=7)
    if easter <= today <= easter_end:
        return 'Buona Pasqua!'
    
    pentecost = easter + timedelta(days=49)
    if today == pentecost:
        return 'Buona Pentecoste!'
    
    corpus_domini = easter + timedelta(days=63)
    if today == corpus_domini:
        return 'Auguri per oggi!'
    
    holy_family = get_holy_family_sunday(year)
    if holy_family and today == holy_family:
        return 'Buona Festa della Sacra Famiglia.'
    
    return None

def get_western_easter_date(year: int) -> datetime.date:
    """
    Calculate Western Easter date using Computus algorithm
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    
    return datetime(year, month, day).date()

def get_holy_family_sunday(year: int) -> Optional[datetime.date]:
    """
    Get Holy Family Sunday (Sunday between Dec 26-31)
    """
    for day in range(26, 32):
        try:
            date = datetime(year, 12, day)
            if date.weekday() == 6:  # Domenica
                return date.date()
        except ValueError:
            continue
    return None

def should_ignore_email(subject: str, content: str, sender_email: str,
                        ignore_keywords: List[str], ignore_senders: List[str]) -> bool:
    """
    Check if email should be ignored based on keywords and senders
    
    Args:
        subject: Email subject
        content: Email content
        sender_email: Sender email address
        ignore_keywords: List of keywords to ignore
        ignore_senders: List of sender domains/emails to ignore
        
    Returns:
        True if email should be ignored
    """
    text = (subject + ' ' + content).lower()
    
    for keyword in ignore_keywords:
        if keyword.lower() in text:
            logger.info(f"Email ignored due to keyword: '{keyword}'")
            return True
    
    # Parse a clean email address and domain for accurate matching
    _, clean_email = parseaddr(sender_email)
    email_lower = clean_email.lower()
    domain_lower = email_lower.split('@')[-1] if '@' in email_lower else ''

    for sender in ignore_senders:
        sender_l = sender.lower().strip()
        if not sender_l:
            continue
        # Match full email exactly
        if '@' in sender_l:
            if email_lower == sender_l:
                logger.info(f"Email ignored due to sender (exact match): '{sender}'")
                return True
        else:
            # Match domain by suffix (.example.com should match sub.example.com)
            if domain_lower == sender_l or domain_lower.endswith('.' + sender_l):
                logger.info(f"Email ignored due to sender domain: '{sender}'")
                return True
    
    return False

def apply_replacements(text: str, replacements: Dict[str, str]) -> str:
    """
    Apply text replacements
    
    Args:
        text: Text to process
        replacements: Dictionary of replacements (bad_text -> good_text)
        
    Returns:
        Text with replacements applied
    """
    for bad_expr, good_expr in replacements.items():
        escaped_bad = re.escape(bad_expr)
        text = re.sub(escaped_bad, good_expr, text, flags=re.IGNORECASE)
    return text

def generate_dynamic_knowledge_base(knowledge_base_string: str) -> str:
    """
    Add dynamic date information to knowledge base
    
    Args:
        knowledge_base_string: Base knowledge base string
        
    Returns:
        Knowledge base with dynamic date info prepended
    """
    now = datetime.now(ITALIAN_TZ)
    tomorrow = now + timedelta(days=1)
    day_after_tomorrow = now + timedelta(days=2)
    
    date_format = "%A %d %B %Y"
    import locale
    try:
        locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')
    except:
        pass
    
    today_string = now.strftime(date_format)
    tomorrow_string = tomorrow.strftime(date_format)
    day_after_tomorrow_string = day_after_tomorrow.strftime(date_format)
    
    dynamic_info = f"""--- Informazioni Dinamiche Contestuali ---
Data di oggi: {today_string}
Data di domani: {tomorrow_string}
Data di dopodomani: {day_after_tomorrow_string}
Periodo estivo: dal 29 giugno al 30 agosto.
Periodo invernale: dal 31 agosto al 28 giugno.
--- Fine Informazioni Dinamiche ---
"""
    return dynamic_info + knowledge_base_string

def extract_thread_messages(thread: Dict) -> List[Dict]:
    """
    Extract all messages from a thread
    
    Args:
        thread: Gmail thread object
        
    Returns:
        List of message dictionaries
    """
    messages = []
    for message in thread.get('messages', []):
        msg_dict = {
            'id': message['id'],
            'threadId': message['threadId']
        }
        headers = message['payload'].get('headers', [])
        for header in headers:
            name = header['name'].lower()
            if name == 'from':
                msg_dict['from'] = header['value']
            elif name == 'subject':
                msg_dict['subject'] = header['value']
            elif name == 'date':
                msg_dict['date'] = header['value']
        messages.append(msg_dict)
    return messages
