"""
Utility functions for date calculations, filters, and text processing
Enhanced with intelligent temporal context generation
"""

from datetime import datetime, timedelta
import re
import logging
import locale
from typing import Optional, List, Dict, Tuple  # CRITICAL FIX: Added Tuple
import config
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Definisci il fuso orario italiano
ITALIAN_TZ = ZoneInfo("Europe/Rome")


# CRITICAL FIX: Robust locale setting with fallbacks
def _set_italian_locale() -> bool:
    """
    Set Italian locale for date formatting with multiple fallbacks
    
    Returns:
        True if successfully set, False otherwise
    """
    locales_to_try = [
        'it_IT.UTF-8',      # Linux/Mac standard
        'it_IT.utf8',       # Linux alternative
        'it_IT',            # Generic Italian
        'Italian_Italy.1252',  # Windows
        'ita_ita',          # Windows alternative
    ]
    
    for loc in locales_to_try:
        try:
            locale.setlocale(locale.LC_TIME, loc)
            logger.debug(f"✓ Set locale to {loc}")
            return True
        except locale.Error:
            continue
    
    logger.warning("⚠️  Could not set Italian locale - dates will be in system default language")
    return False


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

def extract_dates_from_knowledge_base(kb_text: str) -> List[Tuple[datetime, str]]:
    """
    Extract dates from knowledge base text (deduplicated)
    
    CRITICAL FIX: Now deduplicates dates to avoid duplicate annotations
    
    Args:
        kb_text: Knowledge base text
        
    Returns:
        List of (date, context_snippet) tuples, deduplicated and sorted
    """
    dates_dict = {}  # CRITICAL FIX: Use dict to deduplicate by date
    now = datetime.now(ITALIAN_TZ)
    
    # Pattern per date italiane comuni
    patterns = [
        # "4 ottobre", "19 ottobre 2025"
        r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+(\d{4}))?',
        # "ottobre 2025"
        r'(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})',
    ]
    
    month_map = {
        'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
        'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
        'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
    }
    
    for pattern in patterns:
        for match in re.finditer(pattern, kb_text, re.IGNORECASE):
            try:
                if len(match.groups()) == 3:  # "4 ottobre 2025" or "4 ottobre"
                    day = int(match.group(1))
                    month = month_map[match.group(2).lower()]
                    year = int(match.group(3)) if match.group(3) else now.year
                elif len(match.groups()) == 2:  # "ottobre 2025"
                    day = 1
                    month = month_map[match.group(1).lower()]
                    year = int(match.group(2))
                else:
                    continue
                
                date = datetime(year, month, day, tzinfo=ITALIAN_TZ)
                
                # Extract surrounding context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(kb_text), match.end() + 50)
                context = kb_text[start:end].strip()
                
                # CRITICAL FIX: Store by date key to deduplicate
                date_key = date.date()
                if date_key not in dates_dict:
                    dates_dict[date_key] = (date, context)
                    
            except (ValueError, KeyError) as e:
                logger.debug(f"Could not parse date from match: {match.group(0)} - {e}")
                continue
    
    # Return as sorted list
    return sorted(dates_dict.values(), key=lambda x: x[0])

def generate_temporal_awareness_context(now: datetime = None) -> str:
    """
    Generate rich temporal awareness context for AI
    
    This provides the AI with:
    - Current date with clear emphasis
    - Recent past events (what just happened)
    - Near future events (what's coming)
    - Examples of how to refer to past vs future events
    
    Args:
        now: Current datetime (default: now in Italian timezone)
        
    Returns:
        Rich temporal context string
    """
    if now is None:
        now = datetime.now(ITALIAN_TZ)
    
    # Calculate key dates
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)
    week_ago = now - timedelta(days=7)
    week_ahead = now + timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    two_weeks_ahead = now + timedelta(days=14)
    
    # CRITICAL FIX: Robust locale setting
    _set_italian_locale()
    
    # Format dates
    date_format = "%A %d %B %Y"
    today_str = now.strftime(date_format)
    yesterday_str = yesterday.strftime("%d %B")
    tomorrow_str = tomorrow.strftime("%d %B")
    week_ago_str = week_ago.strftime("%d %B")
    week_ahead_str = week_ahead.strftime("%d %B")
    
    context = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🕐 CONTESTO TEMPORALE INTELLIGENTE                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

📅 OGGI È: {today_str}
   ↑ Questa è la data di riferimento ASSOLUTA per tutte le risposte

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ LINEA TEMPORALE:

   📍 Due settimane fa: {two_weeks_ago.strftime("%d %B")}
   📍 Una settimana fa: {week_ago_str}
   📍 Ieri: {yesterday_str}
   
   🔴 >>> OGGI: {now.strftime("%d %B %Y")} <<<  [PUNTO DI RIFERIMENTO]
   
   📍 Domani: {tomorrow_str}
   📍 Tra una settimana: {week_ahead_str}
   📍 Tra due settimane: {two_weeks_ahead.strftime("%d %B")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 ISTRUZIONI CRITICHE SUL TEMPO:

1. ⚠️  REGOLA FONDAMENTALE:
   Se una data nella knowledge base è PRECEDENTE a oggi ({now.strftime("%d %B %Y")}):
   → USA IL PASSATO: "è iniziato/a", "è cominciato/a", "ha avuto inizio"
   → NON dire MAI "inizierà", "comincerà", "avrà inizio"

2. 📊 ESEMPI PRATICI:

   SCENARIO A - Evento del 19 ottobre, oggi è {now.strftime("%d %B")}:
   ❌ SBAGLIATO: "La catechesi inizierà il 19 ottobre"
   ✅ CORRETTO: "La catechesi è già iniziata il 19 ottobre"
   ✅ CORRETTO: "La catechesi è cominciata sabato 19 ottobre"
   
   SCENARIO B - Evento del 4 ottobre, oggi è {now.strftime("%d %B")}:
   ❌ SBAGLIATO: "Il corso inizierà il 4 ottobre 2025"
   ✅ CORRETTO: "Il corso è già iniziato il 4 ottobre"
   ✅ CORRETTO: "Il corso prematrimoniale è iniziato venerdì 4 ottobre"
   
   SCENARIO C - Evento del 15 novembre, oggi è {now.strftime("%d %B")}:
   ✅ CORRETTO: "Il prossimo incontro si terrà il 15 novembre"
   ✅ CORRETTO: "L'evento è previsto per venerdì 15 novembre"

3. 🎯 LINEE GUIDA INTELLIGENTI:

   Per eventi passati (prima di oggi):
   • Usa sempre il passato prossimo: "è iniziato", "si è tenuto", "ha avuto luogo"
   • Aggiungi "già" per enfatizzare: "è già iniziato"
   • Se molto recente (< 7 giorni): "è iniziato di recente", "è appena cominciato"
   • Se chiesto info su partecipazione: "Puoi ancora unirti" o "Per informazioni sui prossimi incontri..."
   
   Per eventi futuri (dopo oggi):
   • Usa il futuro semplice: "inizierà", "si terrà", "avrà luogo"
   • Usa "prossimo/a" per chiarezza: "il prossimo incontro"
   
   Per eventi in corso (es. corso già iniziato ma non finito):
   • "È in corso da...", "Procede regolarmente...", "È possibile ancora iscriversi..."

4. 🔍 VERIFICA PRIMA DI RISPONDERE:
   a) Identifica TUTTE le date menzionate nella tua risposta
   b) Per OGNI data, chiediti: "È prima o dopo {now.strftime("%d %B %Y")}?"
   c) Usa il tempo verbale appropriato
   d) Se hai dubbi, preferisci: "già iniziato" piuttosto che "inizierà"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 REMINDER: La data di OGGI ({today_str}) è il tuo PUNTO DI RIFERIMENTO.
   Tutti gli eventi vengono valutati rispetto a questa data.
   NON assumere mai che un evento sia nel futuro solo perché è menzionato nella KB.
   CONTROLLA SEMPRE la data rispetto a OGGI.

╚══════════════════════════════════════════════════════════════════════════════╝
"""
    
    return context

def generate_dynamic_knowledge_base(knowledge_base_string: str) -> str:
    """
    Add dynamic date information to knowledge base with temporal awareness
    
    Args:
        knowledge_base_string: Base knowledge base string
        
    Returns:
        Knowledge base with enriched temporal context
    """
    now = datetime.now(ITALIAN_TZ)
    
    # Generate rich temporal awareness context
    temporal_context = generate_temporal_awareness_context(now)
    
    # Extract dates from KB and provide context
    dates_found = extract_dates_from_knowledge_base(knowledge_base_string)
    
    if dates_found:
        date_context = "\n\n📋 DATE RILEVATE NELLA KNOWLEDGE BASE:\n"
        date_context += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for date, context in dates_found:  # Already sorted and deduplicated
            days_diff = (date.date() - now.date()).days
            
            if days_diff < 0:
                status = f"⏪ PASSATO (era {abs(days_diff)} giorni fa)"
                verb_hint = "→ Usa PASSATO: 'è iniziato', 'si è tenuto'"
            elif days_diff == 0:
                status = "🔴 OGGI"
                verb_hint = "→ Usa PRESENTE: 'inizia', 'si tiene'"
            else:
                status = f"⏩ FUTURO (tra {days_diff} giorni)"
                verb_hint = "→ Usa FUTURO: 'inizierà', 'si terrà'"
            
            date_context += f"📅 {date.strftime('%d %B %Y')} - {status}\n"
            date_context += f"   {verb_hint}\n"
            date_context += f"   Contesto: ...{context[:100]}...\n\n"
        
        temporal_context += date_context
    
    # Combine temporal context with KB
    return temporal_context + "\n\n" + knowledge_base_string

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
    
    for sender in ignore_senders:
        if sender.lower() in sender_email.lower():
            logger.info(f"Email ignored due to sender: '{sender}'")
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
