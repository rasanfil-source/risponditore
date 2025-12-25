"""
Utility functions for date calculations, filters, and text processing
Enhanced with intelligent temporal context generation and robust error handling
✅ FIXED: Support for multiple date formats (DD/MM/YYYY, DD-MM-YYYY, etc.)
✅ FIXED: Better date validation to prevent invalid dates
✅ NEW: Special holiday Mass timing rules (only 7:00 PM on specific holidays)
✅ NEW: Easter date calculation test for 2026-2040
"""

from datetime import datetime, timedelta
import re
import logging
import locale
from typing import Optional, List, Dict, Tuple
import config

logger = logging.getLogger(__name__)

# ============================================================================
# TIMEZONE SETUP WITH ROBUST FALLBACK
# ============================================================================

def _get_italian_timezone():
    """
    Get Italian timezone with robust fallback
    
    Tries:
    1. zoneinfo.ZoneInfo (Python 3.9+, preferred)
    2. pytz.timezone (fallback)
    3. UTC as last resort (logs error)
    
    Returns:
        Timezone object (ZoneInfo or pytz or UTC)
    """
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Rome")
        logger.debug("✓ Using zoneinfo for Italian timezone")
        return tz
    except Exception as e:
        logger.warning(f"⚠️  zoneinfo failed ({e}), trying pytz")
        
        try:
            import pytz
            tz = pytz.timezone("Europe/Rome")
            logger.warning("⚠️  Using pytz fallback for Italian timezone")
            return tz
        except Exception as e2:
            logger.error(f"❌ Both zoneinfo and pytz failed: {e2}")
            logger.error("   Defaulting to UTC - DATES WILL BE WRONG!")
            from datetime import timezone
            return timezone.utc

# Initialize at module level
ITALIAN_TZ = _get_italian_timezone()


# ============================================================================
# LOCALE SETUP WITH MULTIPLE FALLBACKS
# ============================================================================

def _set_italian_locale() -> bool:
    """
    Set Italian locale for date formatting with multiple fallbacks
    
    Returns:
        True if successfully set, False otherwise
    """
    locales_to_try = [
        'it_IT.UTF-8',          # Linux/Mac standard
        'it_IT.utf8',           # Linux alternative
        'it_IT',                # Generic Italian
        'Italian_Italy.1252',   # Windows
        'ita_ita',              # Windows alternative
        'it',                   # Minimal Italian
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


# ============================================================================
# SALUTATION MODE COMPUTATION - Conversational Continuity
# ============================================================================

# Threshold for considering a follow-up as "recent" (conversation still warm)
FOLLOWUP_THRESHOLD_HOURS = 48


def compute_salutation_mode(
    *,
    message_count: int,
    is_reply: bool,
    first_salutation_used: bool = False,
    last_interaction_at: datetime = None,
    now: datetime = None,
) -> str:
    """
    Compute the appropriate salutation mode for conversational continuity.
    
    Prevents mechanical repetition of greetings in follow-up emails.
    A human doesn't repeat "Buon Natale" in every message of the same thread.
    
    Args:
        message_count: Number of messages in the thread
        is_reply: Whether this is a reply (Re:)
        first_salutation_used: Whether the first salutation was already used
        last_interaction_at: Timestamp of last interaction
        now: Current timestamp (default: now)
        
    Returns:
        One of:
        - 'full': Use complete ritual greeting (first contact)
        - 'none_or_continuity': Skip greeting or use continuity phrase (recent follow-up)
        - 'soft': Use soft greeting (resumed conversation after pause)
    """
    if now is None:
        now = datetime.now(ITALIAN_TZ)
    
    # First message or first contact: full greeting is appropriate
    if message_count <= 1 or not first_salutation_used:
        logger.debug("Salutation mode: FULL (first contact)")
        return "full"
    
    # Not a reply: treat as new conversation
    if not is_reply:
        logger.debug("Salutation mode: FULL (not a reply)")
        return "full"
    
    # No timestamp available: be cautious, use soft greeting
    if not last_interaction_at:
        logger.debug("Salutation mode: SOFT (no timestamp available)")
        return "soft"
    
    # Calculate time delta
    try:
        # Handle timezone-naive vs timezone-aware comparison
        if hasattr(last_interaction_at, 'tzinfo') and last_interaction_at.tzinfo is not None:
            if hasattr(now, 'tzinfo') and now.tzinfo is None:
                now = now.replace(tzinfo=last_interaction_at.tzinfo)
        
        delta = now - last_interaction_at
        hours_since_last = delta.total_seconds() / 3600
        
        # Recent follow-up: conversation is still "warm"
        if hours_since_last <= FOLLOWUP_THRESHOLD_HOURS:
            logger.debug(f"Salutation mode: NONE_OR_CONTINUITY (last interaction {hours_since_last:.1f}h ago)")
            return "none_or_continuity"
        
        # Follow-up after pause: use soft greeting
        logger.debug(f"Salutation mode: SOFT (last interaction {hours_since_last:.1f}h ago)")
        return "soft"
        
    except Exception as e:
        logger.warning(f"⚠️ Error computing salutation mode: {e}")
        return "soft"


# ============================================================================
# SUSPENSION TIME AND SPECIAL PERIODS
# ============================================================================

def is_in_suspension_time() -> bool:
    """
    Check if current time is within suspension hours
    
    Returns:
        True if system should be suspended
    """
    now = datetime.now(ITALIAN_TZ)
    month = now.month
    day = now.day
    
    # Special periods and holidays override suspension hours
    if is_in_special_period(month, day):
        return False
    
    weekday = now.weekday()
    hour = now.hour
    
    # Check if current hour is in suspension hours for this weekday
    if weekday in config.SUSPENSION_HOURS:
        for start_hour, end_hour in config.SUSPENSION_HOURS[weekday]:
            if start_hour <= hour < end_hour:
                return True
    
    return False


def is_in_special_period(month: int, day: int) -> bool:
    """
    Check if date is in a special period (holidays, vacations)
    
    Args:
        month: Month (1-12)
        day: Day of month
        
    Returns:
        True if date is in special period
    """
    # Check special periods (can span year boundaries)
    for (start_month, start_day), (end_month, end_day) in config.SPECIAL_PERIODS:
        if start_month > end_month:  # Period crosses year boundary
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
    
    # Check single-day holidays
    for holiday_month, holiday_day in config.HOLIDAYS:
        if month == holiday_month and day == holiday_day:
            return True
    
    # ═══════════════════════════════════════════════════════════════
    # ✅ NEW: Easter-based holidays (dynamic dates)
    # ═══════════════════════════════════════════════════════════════
    try:
        now = datetime.now(ITALIAN_TZ)
        year = now.year
        
        # Calculate Easter and related dates
        easter = get_western_easter_date(year)
        sabato_santo = easter - timedelta(days=1)  # Holy Saturday (day before Easter)
        pasquetta = easter + timedelta(days=1)     # Easter Monday (day after Easter)
        
        current_date = datetime(year, month, day).date()
        
        # Check if today is Sabato Santo or Pasquetta
        if current_date == sabato_santo:
            logger.info("✓ Special period: Sabato Santo (Holy Saturday)")
            return True
        if current_date == pasquetta:
            logger.info("✓ Special period: Pasquetta (Easter Monday)")
            return True
            
    except Exception as e:
        logger.warning(f"⚠️ Error checking Easter-based holidays: {e}")
    
    return False


def get_current_season(date_obj: datetime = None) -> str:
    """
    Determine current season (summer/winter) with dynamic summer period
    
    Summer period is calculated dynamically:
    - Start: Monday after June 26
    - End: Monday after August 31
    
    Args:
        date_obj: Date to check (default: now)
        
    Returns:
        'estivo' or 'invernale'
    """
    if date_obj is None:
        date_obj = datetime.now(ITALIAN_TZ)
    
    month = date_obj.month
    day = date_obj.day
    year = date_obj.year
    
    # Get dynamic summer period for this year
    summer_start, summer_end = config.get_summer_period(year)
    
    # Check if in summer period
    # Convert dates to comparable format (month, day) tuples
    current_date = (month, day)
    
    # Handle case where summer period might span across months
    if summer_start[0] == summer_end[0]:
        # Same month (unlikely but handled)
        if month == summer_start[0] and summer_start[1] <= day <= summer_end[1]:
            return 'estivo'
    else:
        # Different months (normal case: June-September)
        if month == summer_start[0] and day >= summer_start[1]:
            return 'estivo'
        elif summer_start[0] < month < summer_end[0]:
            return 'estivo'
        elif month == summer_end[0] and day <= summer_end[1]:
            return 'estivo'
    
    return 'invernale'


# ============================================================================
# SPECIAL DAY GREETINGS
# ============================================================================

def get_special_day_greeting(date_obj: datetime = None) -> Optional[str]:
    """
    Get special day greeting if applicable
    
    Args:
        date_obj: Date to check (default: now)
        
    Returns:
        Greeting string or None
    """
    if date_obj is None:
        date_obj = datetime.now(ITALIAN_TZ)
    
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day
    today = date_obj.date()
    
    # Fixed date holidays
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
    
    # Mobile feasts (Easter-based)
    try:
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
    except Exception as e:
        logger.warning(f"⚠️  Error calculating Easter-based holidays: {e}")
    
    # Holy Family Sunday
    try:
        holy_family = get_holy_family_sunday(year)
        if holy_family and today == holy_family:
            return 'Buona Festa della Sacra Famiglia.'
    except Exception as e:
        logger.warning(f"⚠️  Error calculating Holy Family Sunday: {e}")
    
    return None


def get_western_easter_date(year: int) -> datetime.date:
    """
    Calculate Western Easter date using Computus algorithm
    
    Args:
        year: Year to calculate Easter for
        
    Returns:
        Easter date
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
    
    Args:
        year: Year to calculate for
        
    Returns:
        Date of Holy Family Sunday or None
    """
    for day in range(26, 32):
        try:
            date = datetime(year, 12, day)
            if date.weekday() == 6:  # Sunday
                return date.date()
        except ValueError:
            continue
    
    return None


# ============================================================================
# ✅ NEW: HOLIDAY MASS TIMING RULE
# ============================================================================

def is_special_holiday_mass_time(date_obj: datetime = None) -> bool:
    """
    Check if date requires special Mass timing (only 7:00 PM Mass)
    
    Special holidays when Mass is ONLY at 7:00 PM:
    - Easter Monday
    - St. Stephen's Day (Dec 26)
    - May 1st (Labor Day)
    - April 25th (Liberation Day)
    - June 2nd (Republic Day)
    
    Exception: If these days fall on a Sunday, use normal Sunday schedule
    
    Args:
        date_obj: Date to check (default: now)
        
    Returns:
        True if only 7:00 PM Mass applies
    """
    if date_obj is None:
        date_obj = datetime.now(ITALIAN_TZ)
    
    month = date_obj.month
    day = date_obj.day
    year = date_obj.year
    
    # Check if it's Sunday - exception to the rule
    if date_obj.weekday() == 6:  # Sunday
        return False
    
    # Check specific holidays
    special_holidays = [
        (4, 25),  # April 25 - Liberation Day
        (5, 1),   # May 1 - Labor Day
        (6, 2),   # June 2 - Republic Day
        (12, 26), # Dec 26 - St. Stephen's Day
    ]
    
    # Check for April 25, May 1, June 2, Dec 26
    if (month, day) in special_holidays:
        return True
    
    # Check for Easter Monday (dynamic date)
    try:
        easter = get_western_easter_date(year)
        easter_monday = easter + timedelta(days=1)
        
        # Normalize date_obj to date for comparison
        check_date = date_obj.date() if hasattr(date_obj, 'date') else date_obj
        
        if check_date == easter_monday:
            return True
    except Exception as e:
        logger.warning(f"⚠️ Error calculating Easter Monday: {e}")
    
    return False


def get_mass_timing_context(date_obj: datetime = None) -> str:
    """
    Generate context for Mass timing rules
    
    Args:
        date_obj: Date to check (default: now)
        
    Returns:
        Context string for AI about Mass timing rules
    """
    if date_obj is None:
        date_obj = datetime.now(ITALIAN_TZ)
    
    date_str = date_obj.strftime("%d %B %Y")
    day_name = date_obj.strftime("%A")
    
    if is_special_holiday_mass_time(date_obj):
        return f"""
⚠️ IMPORTANTE - ORARI MESSA SPECIALI:
Oggi è {date_str} ({day_name}), una festività con orari speciali:
• Le Messe si celebrano SOLO alle ore 19:00
• Gli orari regolari delle Messe non si applicano oggi

Questa regola sovrascrive qualsiasi orario di Messa indicato nella knowledge base.
"""
    
    return ""



# ============================================================================
# ✅ FIXED: DATE EXTRACTION WITH MULTIPLE FORMATS
# ============================================================================

def extract_dates_from_knowledge_base(kb_text: str) -> List[Tuple[datetime, str]]:
    """
    ✅ FIXED: Extract dates from knowledge base supporting multiple formats
    
    Supported formats:
    - Textual: "4 ottobre 2025", "ottobre 2025"
    - Numeric: "04/10/2025", "4-10-2025", "04.10.2025"
    
    Args:
        kb_text: Knowledge base text
        
    Returns:
        List of (date, context_snippet) tuples, deduplicated and sorted
    """
    dates_dict = {}  # Use dict to deduplicate by date
    now = datetime.now(ITALIAN_TZ)
    
    # Month mapping for Italian months
    month_map = {
        'gennaio': 1, 'febbraio': 2, 'marzo': 3, 'aprile': 4,
        'maggio': 5, 'giugno': 6, 'luglio': 7, 'agosto': 8,
        'settembre': 9, 'ottobre': 10, 'novembre': 11, 'dicembre': 12
    }
    
    # ✅ FIXED: Extended patterns for multiple formats
    patterns = [
        # Format 1: "4 ottobre 2025" or "4 ottobre"
        (r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)(?:\s+(\d{4}))?', 'textual_day_month'),
        
        # Format 2: "ottobre 2025"
        (r'(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})', 'textual_month_year'),
        
        # Format 3: ✅ NEW - Numeric formats
        # "04/10/2025" or "4/10/2025" or "04-10-2025" or "04.10.2025"
        (r'(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})', 'numeric_dmy'),
    ]
    
    for pattern, format_type in patterns:
        for match in re.finditer(pattern, kb_text, re.IGNORECASE):
            try:
                # Parse based on format type
                if format_type == 'textual_day_month':
                    # "4 ottobre 2025" or "4 ottobre"
                    day = int(match.group(1))
                    month = month_map[match.group(2).lower()]
                    year = int(match.group(3)) if match.group(3) else now.year
                
                elif format_type == 'textual_month_year':
                    # "ottobre 2025"
                    day = 1
                    month = month_map[match.group(1).lower()]
                    year = int(match.group(2))
                
                elif format_type == 'numeric_dmy':
                    # ✅ NEW: "04/10/2025" (DD/MM/YYYY format - European)
                    day = int(match.group(1))
                    month = int(match.group(2))
                    year = int(match.group(3))
                
                else:
                    continue
                
                # ✅ FIXED: Validate date before creating datetime
                # This prevents invalid dates like 31 February
                try:
                    date = datetime(year, month, day, tzinfo=ITALIAN_TZ)
                except ValueError as e:
                    logger.debug(f"Invalid date skipped: {day}/{month}/{year} - {e}")
                    continue
                
                # Extract surrounding context (50 chars before and after)
                start = max(0, match.start() - 50)
                end = min(len(kb_text), match.end() + 50)
                context = kb_text[start:end].strip()
                
                # Store by date key to deduplicate
                date_key = date.date()
                if date_key not in dates_dict:
                    dates_dict[date_key] = (date, context)
                    logger.debug(f"Date extracted: {date.strftime('%d/%m/%Y')} ({format_type})")
                    
            except KeyError as e:
                logger.debug(f"Could not parse month: {e}")
                continue
            except ValueError as e:
                logger.debug(f"Invalid date values: {e}")
                continue
            except Exception as e:
                logger.warning(f"⚠️  Unexpected error parsing date: {match.group(0)} - {e}")
                continue
    
    # Return as sorted list
    sorted_dates = sorted(dates_dict.values(), key=lambda x: x[0])
    
    if sorted_dates:
        logger.info(f"   Extracted {len(sorted_dates)} unique dates from KB")
    
    return sorted_dates


# ============================================================================
# TEMPORAL AWARENESS CONTEXT GENERATION
# ============================================================================

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
    
    # Set Italian locale for date formatting
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
"""

    # ═══════════════════════════════════════════════════════════════
    # ✅ NEW: MASS TIMING RULES FOR SPECIAL HOLIDAYS
    # ═══════════════════════════════════════════════════════════════
    
    mass_timing_context = get_mass_timing_context(now)
    if mass_timing_context:
        context += "\n" + mass_timing_context + "\n"
    
    context += "╚══════════════════════════════════════════════════════════════════════════════╝"
    
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


# ============================================================================
# EMAIL FILTERING AND TEXT PROCESSING
# ============================================================================

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
    
    # Check keywords
    for keyword in ignore_keywords:
        if keyword.lower() in text:
            logger.info(f"Email ignored due to keyword: '{keyword}'")
            return True
    
    # Check senders
    for sender in ignore_senders:
        if sender.lower() in sender_email.lower():
            logger.info(f"Email ignored due to sender: '{sender}'")
            return True
    
    # ═══════════════════════════════════════════════════════════════
    # ✅ NUOVO: FILTRO 3 - INVITI ISTITUZIONALI E CONVEGNI
    # ═══════════════════════════════════════════════════════════════
    
    institutional_invite_patterns = [
        # Parole chiave inviti
        r'invit(?:o|iamo|arvi)\s+(?:a|al|alla|per)',  # "invito a", "invitiamo alla"
        r'convegno\s+',  # "convegno"
        r'seminario\s+',  # "seminario"
        r'conferenza\s+',  # "conferenza"
        r'corso\s+di\s+formazione',  # "corso di formazione"
        r'giornata\s+di\s+studio',  # "giornata di studio"
        r'incontro\s+formativo',  # "incontro formativo"
        
        # Formule di cortesia istituzionali
        r'abbiamo\s+il\s+piacere\s+di\s+invitarvi',
        r'siamo\s+lieti\s+di\s+invitarvi',
        r'vi\s+invitiamo\s+a\s+partecipare',
        
        # Link iscrizione/segnalazione
        r'link\s+(?:dove|per)\s+(?:è\s+possibile\s+)?segnal(?:are|azione)',
        r'clicca\s+(?:qui|sul\s+link)\s+per\s+iscri',
        r'confermare\s+la\s+(?:tua|vostra)\s+presenza',
        
        # Documenti allegati (manifestos, posters)
        r'(?:alleghiamo|trovate\s+allegat[oa])\s+(?:la\s+)?(?:locandina|manifesto|programma)',
        
        # Event program
        r'in\s+programma\s+(?:il|sabato|domenica|lunedì)',
        r'ore\s+\d{1,2}[.:]\d{2}\s+(?:presso|al|alla)',
    ]
    
    for pattern in institutional_invite_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.info(f"✗ Ignored by institutional invite pattern: '{pattern[:30]}...'")
            return True
    
    # ═══════════════════════════════════════════════════════════════
    # ✅ NUOVO: FILTRO 4 - CONTENUTI PROMOZIONALI/DONAZIONI
    # ═══════════════════════════════════════════════════════════════
    
    promotional_patterns = [
        r'vuoi\s+sostenere',  # "vuoi sostenere le nostre attività"
        r'dona\s+ora',  # "dona ora"
        r'sostieni\s+(?:le\s+nostre|la\s+nostra)',  # "sostieni le nostre attività"
        r'contribuisci\s+con',  # "contribuisci con una donazione"
        r'clicca\s+sull[\']immagine',  # "clicca sull'immagine"
        r'5\s*x\s*1000',  # "5x1000"
        r'sostegno\s+economico',  # "sostegno economico"
    ]
    
    for pattern in promotional_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.info(f"✗ Ignored by promotional pattern: '{pattern[:30]}...'")
            return True
    
    # ═══════════════════════════════════════════════════════════════
    # ✅ NUOVO: FILTRO 5 - MITTENTI ISTITUZIONALI (NON PRIVATI)
    # ═══════════════════════════════════════════════════════════════
    
    # Pattern per identificare mittenti istituzionali
    institutional_sender_patterns = [
        r'segreteria@',  # segreteria di altre organizzazioni
        r'info@(?!(?:parrocchiasanteugenio|parrocchia\.it))',  # info@ ma non la nostra
        r'comunicazione@',
        r'ufficio(?:stampa|comunicazione)@',
        r'newsletter@',
        r'noreply@',
        r'no-reply@',
    ]
    
    # Eccezione: NON filtrare se è la nostra parrocchia
    if 'parrocchiasanteugenio' not in sender_email.lower():
        for pattern in institutional_sender_patterns:
            if re.search(pattern, sender_email.lower()):
                # DOPPIO CHECK: è davvero promozionale?
                if any(keyword in text for keyword in ['invit', 'convegno', 'seminario', 'corso']):
                    logger.info(f"✗ Ignored by institutional sender + promotional content")
                    return True
    
    # ═══════════════════════════════════════════════════════════════
    # ✅ NUOVO: FILTRO 6 - FOOTER TIPICI DI NEWSLETTER
    # ═══════════════════════════════════════════════════════════════
    
    newsletter_footer_patterns = [
        r'vuoi\s+sostenere\s+le\s+nostre\s+attività',
        r'privo\s+di\s+virus',  # "Privo di virus. www.avg.com"
        r'scansionato\s+da\s+(?:gmail|avg|avast)',
        r'immagine\s+rimossa\s+dal\s+mittente',
        r'messaggio\s+troncato.*visualizza\s+intero\s+messaggio',
    ]
    
    for pattern in newsletter_footer_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            logger.info(f"✗ Ignored by newsletter footer pattern")
            return True

# ═══════════════════════════════════════════════════════════════
# ✅ NUOVO: FILTRO 6B - FOOTER NEWSLETTER ITALIANI
# ═══════════════════════════════════════════════════════════════

    italian_newsletter_footer = [
        r'privacy\s+policy.*(?:disiscriviti|annulla)',
        r'aggiorna\s+le\s+tue\s+preferenze.*disiscriviti',
        r'gestisci\s+(?:le\s+tue\s+)?(?:preferenze|iscrizioni)',
        r'(?:clicca|click)\s+qui\s+per\s+(?:disiscriverti|annullare)',
        r'non\s+desideri\s+più\s+ricevere',
        r'per\s+non\s+ricevere\s+più',
        r'se\s+non\s+vuoi\s+più\s+ricevere',
    ]

    for pattern in italian_newsletter_footer:
        if re.search(pattern, text, re.IGNORECASE):
            logger.info(f"✗ Ignored by Italian newsletter footer pattern")
            return True

    # ═══════════════════════════════════════════════════════════════
    # ✅ NUOVO: FILTRO 7 - COMBINAZIONI SOSPETTE
    # ═══════════════════════════════════════════════════════════════
    
    # Se contiene INSIEME più elementi tipici di newsletter/eventi
    suspicious_indicators = 0
    
    if re.search(r'(?:alleghiamo|trovate\s+allegat)', text, re.IGNORECASE):
        suspicious_indicators += 1
    if re.search(r'(?:link|url|https?://)', text, re.IGNORECASE):
        suspicious_indicators += 1
    if re.search(r'(?:locandina|manifesto|programma)', text, re.IGNORECASE):
        suspicious_indicators += 1
    if re.search(r'(?:presidente|segretari[ao]|assistente)', text, re.IGNORECASE):
        suspicious_indicators += 1
    if re.search(r'carissim[ie]|car[ie]\s+(?:amici|fratelli)', text, re.IGNORECASE):
        suspicious_indicators += 1
    
    if suspicious_indicators >= 3:
        logger.info(f"✗ Ignored by suspicious indicators count: {suspicious_indicators}/5")
        return True
    
    # ═══════════════════════════════════════════════════════════════
    
    return False


# ═══════════════════════════════════════════════════════════════
# ✅ HELPER: Detect se email è BROADCAST vs PERSONALE
# ═══════════════════════════════════════════════════════════════

def is_broadcast_email(content: str, sender_email: str) -> bool:
    """
    Detect if email is a broadcast/newsletter vs personal message
    
    Broadcast indicators:
    - Generic greetings (Carissimi, Cari amici)
    - Multiple recipients implied
    - Footer with organization info
    - Links to external registration
    
    Returns:
        True if likely broadcast email
    """
    text = content.lower()
    
    # Generic greetings (not personal)
    generic_greetings = [
        r'carissim[ie]',
        r'car[ie]\s+(?:amici|fratelli|sorelle)',
        r'gentili\s+(?:signori|utenti)',
        r'a\s+tutti',
        r'alla\s+comunità',
    ]
    
    has_generic_greeting = any(
        re.search(pattern, text, re.IGNORECASE) 
        for pattern in generic_greetings
    )
    
    # Organizational footer
    has_org_footer = bool(re.search(
        r'(?:presidente|segretari[ao]|assistente)\s+(?:diocesan[oa]|ecclesiastic[oa])',
        text,
        re.IGNORECASE
    ))
    
    # External links
    has_external_link = bool(re.search(r'https?://(?!parrocchiasanteugenio)', text))
    
    # Multiple indicators = broadcast
    return indicators >= 2


def apply_replacements(text: str, replacements: Dict[str, str]) -> str:
    """
    Apply text replacements
    
    Args:
        text: Text to process
        replacements: Dictionary of replacements (bad_text -> good_text)
        
    Returns:
        Text with replacements applied
    """
    if not replacements:
        return text
    
    for bad_expr, good_expr in replacements.items():
        try:
            escaped_bad = re.escape(bad_expr)
            text = re.sub(escaped_bad, good_expr, text, flags=re.IGNORECASE)
        except Exception as e:
            logger.warning(f"⚠️  Error applying replacement '{bad_expr}': {e}")
            continue
    
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
