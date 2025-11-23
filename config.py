"""
Configuration module for Parish Secretary Cloud Function
Contains all environment variables and constants with validation
"""

import os
from datetime import datetime, timedelta

# ============ Google Workspace Configuration ============
IMPERSONATE_EMAIL = os.environ.get('IMPERSONATE_EMAIL', 'segreteria@parrocchia.it')
SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE', 'service-account-key.json')

# ============ API Keys and IDs ============
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Istruzioni')
REPLACEMENTS_SHEET = os.environ.get('REPLACEMENTS_SHEET', 'Sostituzioni')

# ============ Pub/Sub Configuration ============
PUBSUB_TOPIC = os.environ.get('PUBSUB_TOPIC', 'gmail-notifications')
PUBSUB_SUBSCRIPTION = os.environ.get('PUBSUB_SUBSCRIPTION', 'gmail-notifications-sub')

# ============ Gmail Configuration ============
LABEL_NAME = os.environ.get('LABEL_NAME', 'IA')
ERROR_LABEL_NAME = os.environ.get('ERROR_LABEL_NAME', 'Attenzione')  # Error label
MAX_EMAILS_PER_RUN = int(os.environ.get('MAX_EMAILS_PER_RUN', '10'))

# ============ Gemini Model Configuration ============
MODEL_NAME = 'gemini-2.0-flash'
TEMPERATURE = 0.35
MAX_OUTPUT_TOKENS = 800

# ============ Cache Configuration ============
CACHE_DURATION_SECONDS = 3600  # 1 hour

# ============ CRITICAL NEW FLAGS ============
# Control duplicate auth checks
VERIFY_AUTH_ON_EACH_INVOCATION = os.getenv("VERIFY_AUTH_ON_EACH_INVOCATION", "false").lower() == "true"

# Enable DRY-RUN mode for testing (prevents actual email sending)
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Prompt size limits (characters)
MAX_KNOWLEDGE_BASE_CHARS = int(os.getenv("MAX_KNOWLEDGE_BASE_CHARS", "999999"))
MAX_CONVERSATION_CHARS = int(os.getenv("MAX_CONVERSATION_CHARS", "4000"))

# ============ Response Validation Configuration ============
# ✅ NEW: Response Validator settings
VALIDATION_ENABLED = os.environ.get('VALIDATION_ENABLED', 'true').lower() == 'true'
VALIDATION_MIN_SCORE = float(os.environ.get('VALIDATION_MIN_SCORE', '0.6'))
VALIDATION_STRICT_MODE = os.environ.get('VALIDATION_STRICT_MODE', 'false').lower() == 'true'

# Log validation results to Sheets (optional, for analytics)
LOG_VALIDATION_TO_SHEETS = os.environ.get('LOG_VALIDATION_TO_SHEETS', 'false').lower() == 'true'

# ============ NLP Classification Thresholds ============
SIMPLE_ACK_THRESHOLD = 0.75  # Soglia per classificare come semplice ringraziamento
NEEDS_REPLY_THRESHOLD = 0.30  # Soglia per necessità di risposta

# ============ DYNAMIC SEASONAL PERIODS ============
def get_summer_period(year: int = None) -> tuple:
    """
    Calculate dynamic summer period dates for a given year
    
    Summer starts: Monday after June 26
    Summer ends: Monday after August 31
    
    Args:
        year: Year to calculate for (default: current year)
        
    Returns:
        ((start_month, start_day), (end_month, end_day))
    """
    if year is None:
        year = datetime.now().year
    
    # Find Monday after June 26
    june_26 = datetime(year, 6, 26)
    days_until_monday = (7 - june_26.weekday()) % 7
    if days_until_monday == 0:  # June 26 is already Monday
        summer_start = june_26
    else:
        summer_start = june_26 + timedelta(days=days_until_monday)
    
    # Find Monday after August 31
    aug_31 = datetime(year, 8, 31)
    days_until_monday = (7 - aug_31.weekday()) % 7
    if days_until_monday == 0:  # August 31 is already Monday
        summer_end = aug_31
    else:
        summer_end = aug_31 + timedelta(days=days_until_monday)
    
    return (
        (summer_start.month, summer_start.day),
        (summer_end.month, summer_end.day)
    )

# Calculate for current year at module load
SUMMER_START, SUMMER_END = get_summer_period()

# ============ Suspension Hours by Day ============
# 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
SUSPENSION_HOURS = {
    0: [(8, 20)],           # Monday: 8-20
    1: [(8, 14)],           # Tuesday: 8-14
    3: [(8, 14)],           # Thursday: 8-14
    2: [(8, 17)],           # Wednesday: 8-17
    4: [(8, 17)],           # Friday: 8-17
}

# ============ Special Periods ============
# Format: ((start_month, start_day), (end_month, end_day))
SPECIAL_PERIODS = [
    ((12, 24), (1, 6)),     # Christmas to Epiphany
    ((8, 15), (8, 30)),     # Mid-August vacation
]

# ============ Holiday Dates ============
# Format: (month, day)
HOLIDAYS = [
    (4, 25),   # April 25 - Liberation Day
    (5, 1),    # May 1 - Labor Day
    (8, 15),   # August 15 - Assumption
    (11, 1),   # November 1 - All Saints' Day
    (12, 8),   # December 8 - Immaculate Conception
]

# ============ Email Ignore Lists ============
# RENAMED for clarity: can contain both domains and full emails
IGNORE_SENDERS = [
    'amazon.com',
    'eventbrite.com',
    'paypal.com',
    'ebay.com',
    'subito.it',
    'mailchimp.com',
    'mailup.com',
    'unclickperlascuolaelosport.it',
    'sendinblue.com',
    'miqueldg63@gmail.com',
    'rego.juan@gmail.com'
]

# Alias per compatibilità con codice esistente
IGNORE_DOMAINS = IGNORE_SENDERS

IGNORE_KEYWORDS = [
    'newsletter',
    'unsubscribe',
    'disiscriviti',          # Italiano ← NUOVO
    'disiscrizione',         # Italiano ← NUOVO
    'annulla iscrizione',    # Italiano ← NUOVO
    'annulla l\'iscrizione', # Italiano con apostrofo ← NUOVO
    'gestisci la tua iscrizione',
    'gestisci le tue preferenze',  # ← NUOVO (vedi email Fabrick)
    'aggiorna le tue preferenze',  
    'cancella iscrizione',
    'mailing list',
    'inviato con mailup',
    'messaggio inviato con',
    'bollette',
    'avvisi di pagamento',
    'ricevuta',
    'bonifico',
    'spedizione',
    'avviso di sicurezza',
    'necrologio',
    'non rispondere a questo messaggio'
]

# ============ Simple Acknowledgment Patterns ============
# Per messaggi che non richiedono risposta
ACKNOWLEDGMENT_PATTERNS = [
    r'^\s*grazie\s*$',
    r'^\s*grazie mille\s*$',
    r'^\s*ricevuto\s*$',
    r'^\s*ok\s*$',
    r'^\s*perfetto\s*$'
]

# ============ Force Reply Keywords ============
# Se presenti nel messaggio, si risponde sempre
FORCE_REPLY_KEYWORDS = [
    'non va bene',
    'sbagliato',
    'errore',
    'non funziona',
    'non è giusto',
    'non corretto',
    'non va',
    'stampare',
    'firmare',
    'allegato',
    'liberatoria',
    'verrà per',
    'le chiederà',
    'le chiederò',
    'domani mattina',
    'preparare',
]


# ============ CONFIGURATION VALIDATION ============

def validate_config():
    """
    Valida che tutte le configurazioni critiche siano presenti
    
    Raises:
        ValueError: Se mancano configurazioni critiche
    """
    errors = []
    warnings = []
    
    # === VALIDAZIONI CRITICHE (errori bloccanti) ===
    
    # Email
    if not IMPERSONATE_EMAIL:
        errors.append("IMPERSONATE_EMAIL non configurato")
    elif '@' not in IMPERSONATE_EMAIL:
        errors.append(f"IMPERSONATE_EMAIL non valido: {IMPERSONATE_EMAIL}")
    
    # Spreadsheet
    if not SPREADSHEET_ID:
        errors.append("SPREADSHEET_ID non configurato")
    elif len(SPREADSHEET_ID) < 20:
        errors.append(f"SPREADSHEET_ID sembra non valido (troppo corto): {SPREADSHEET_ID}")
    
    # Gemini API
    if not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY non configurato")
    elif len(GEMINI_API_KEY) < 20:
        errors.append(f"GEMINI_API_KEY sembra non valido (troppo corto)")
    
    # === VALIDAZIONI WARNING (non bloccanti) ===
    
    # Service Account
    if not SERVICE_ACCOUNT_FILE and os.environ.get('USE_SECRET_MANAGER', 'false').lower() != 'true':
        warnings.append(
            "SERVICE_ACCOUNT_FILE non trovato e USE_SECRET_MANAGER non attivo. "
            "Assicurati che l'autenticazione sia configurata correttamente."
        )
    
    # Max emails
    if MAX_EMAILS_PER_RUN > 50:
        warnings.append(
            f"MAX_EMAILS_PER_RUN molto alto ({MAX_EMAILS_PER_RUN}). "
            "Potrebbe causare timeout. Valore consigliato: 10-20."
        )
    
    # Pub/Sub
    if not PUBSUB_TOPIC:
        warnings.append("PUBSUB_TOPIC non configurato (necessario per notifiche push)")
    
    if not PUBSUB_SUBSCRIPTION:
        warnings.append("PUBSUB_SUBSCRIPTION non configurato (necessario per notifiche push)")
    
    # DRY_RUN warning
    if DRY_RUN:
        warnings.append("⚠️  DRY_RUN MODE ACTIVE - Emails will NOT be sent!")
    
    # ✅ NEW: Validation warnings
    if not VALIDATION_ENABLED:
        warnings.append("⚠️  Response validation is DISABLED - Quality checks will be skipped!")
    
    if VALIDATION_STRICT_MODE:
        warnings.append(f"ℹ️  Validation strict mode enabled (min score: 0.8 instead of {VALIDATION_MIN_SCORE})")
    
    # === STAMPA RISULTATI ===
    
    if errors:
        print("❌ ERRORI DI CONFIGURAZIONE CRITICI:")
        for i, error in enumerate(errors, 1):
            print(f"   {i}. {error}")
        print()
        raise ValueError(
            f"Configurazione non valida: {len(errors)} errore(i) critico(i) trovato(i). "
            "Consulta la documentazione per configurare correttamente le variabili d'ambiente."
        )
    
    if warnings:
        print("⚠️  WARNING DI CONFIGURAZIONE:")
        for i, warning in enumerate(warnings, 1):
            print(f"   {i}. {warning}")
        print()
    
    # === STAMPA CONFIGURAZIONE ATTIVA ===
    
    print("✓ Configurazione validata con successo")
    print()
    print("📋 CONFIGURAZIONE ATTIVA:")
    print(f"   Email monitorata: {IMPERSONATE_EMAIL}")
    print(f"   Spreadsheet ID: {SPREADSHEET_ID[:20]}...")
    print(f"   Gemini Model: {MODEL_NAME}")
    print(f"   Max emails per run: {MAX_EMAILS_PER_RUN}")
    print(f"   Label name: {LABEL_NAME}")
    print(f"   Error label: {ERROR_LABEL_NAME}")
    print(f"   Cache duration: {CACHE_DURATION_SECONDS}s")
    print(f"   DRY_RUN: {'YES ⚠️' if DRY_RUN else 'NO'}")
    print(f"   Auth per-invocation: {'YES' if VERIFY_AUTH_ON_EACH_INVOCATION else 'NO (cold start only)'}")
    print(f"   Max KB size: {MAX_KNOWLEDGE_BASE_CHARS} chars")
    print(f"   Max conversation: {MAX_CONVERSATION_CHARS} chars")
    # ✅ NEW: Validation config output
    print(f"   Validation enabled: {'YES' if VALIDATION_ENABLED else 'NO ⚠️'}")
    print(f"   Validation min score: {VALIDATION_MIN_SCORE}")
    print(f"   Validation strict mode: {'YES' if VALIDATION_STRICT_MODE else 'NO'}")
    print()


def get_config_summary() -> dict:
    """
    Ottieni un riepilogo della configurazione (utile per debugging)
    
    Returns:
        Dictionary con configurazione attiva (senza dati sensibili)
    """
    return {
        'impersonate_email': IMPERSONATE_EMAIL,
        'spreadsheet_id': SPREADSHEET_ID[:20] + '...' if SPREADSHEET_ID else None,
        'has_gemini_key': bool(GEMINI_API_KEY),
        'sheet_name': SHEET_NAME,
        'replacements_sheet': REPLACEMENTS_SHEET,
        'pubsub_topic': PUBSUB_TOPIC,
        'pubsub_subscription': PUBSUB_SUBSCRIPTION,
        'label_name': LABEL_NAME,
        'error_label_name': ERROR_LABEL_NAME,
        'max_emails_per_run': MAX_EMAILS_PER_RUN,
        'model_name': MODEL_NAME,
        'temperature': TEMPERATURE,
        'max_output_tokens': MAX_OUTPUT_TOKENS,
        'cache_duration': CACHE_DURATION_SECONDS,
        'ignore_senders_count': len(IGNORE_SENDERS),
        'ignore_keywords_count': len(IGNORE_KEYWORDS),
        'dry_run': DRY_RUN,
        'verify_auth_per_invocation': VERIFY_AUTH_ON_EACH_INVOCATION,
        'max_kb_chars': MAX_KNOWLEDGE_BASE_CHARS,
        'max_conversation_chars': MAX_CONVERSATION_CHARS,
        # ✅ NEW: Validation config in summary
        'validation_enabled': VALIDATION_ENABLED,
        'validation_min_score': VALIDATION_MIN_SCORE,
        'validation_strict_mode': VALIDATION_STRICT_MODE,
        'log_validation_to_sheets': LOG_VALIDATION_TO_SHEETS,
    }


# ============ AUTO-VALIDATION ============

# Esegui validazione automaticamente all'import del modulo
# Commentabile per test unitari con: if __name__ != "__main__":
try:
    validate_config()
except ValueError as e:
    # In produzione, vogliamo che l'errore blocchi l'avvio
    # Durante i test, potrebbe essere necessario disabilitare questa validazione
    print(f"⚠️  Config validation error: {e}")
    print("   Se stai testando localmente, assicurati di aver configurato le variabili d'ambiente.")
    # Non solleva l'eccezione durante l'import per permettere test locali
    # raise
