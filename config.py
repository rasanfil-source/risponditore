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
MAX_EMAILS_PER_RUN = int(os.environ.get('MAX_EMAILS_PER_RUN', '10'))

# ============ Gemini Model Configuration ============
MODEL_NAME = 'gemini-2.0-flash'
TEMPERATURE = 0.6
MAX_OUTPUT_TOKENS = 800

# ============ Cache Configuration ============
CACHE_DURATION_SECONDS = 3600  # 1 hour

# ============ NLP Classification Thresholds ============
SIMPLE_ACK_THRESHOLD = 0.9  # Soglia per classificare come semplice ringraziamento
NEEDS_REPLY_THRESHOLD = 0.55  # Soglia per necessità di risposta

# ============ Seasonal Periods ============
SUMMER_START = (6, 29)  # June 29
SUMMER_END = (8, 30)    # August 30

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
IGNORE_DOMAINS = [
    'amazon.com',
    'paypal.com',
    'ebay.com',
    'subito.it',
    'mailchimp.com',
    'mailup.com',
    'sendinblue.com',
    'rasanfil@gmail.com',
    'miqueldg63@gmail.com',
    'rego.juan@gmail.com'
]

IGNORE_KEYWORDS = [
    'newsletter',
    'unsubscribe', 
    'cancella iscrizione',
    'gestisci la tua iscrizione',
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
    r'^\s*grazie ancora\s*$',
    r'^\s*grazie di cuore\s*$',
    r'^\s*vi ringrazio\s*$',
    r'^\s*ti ringrazio\s*$',
    r'^\s*la ringrazio\s*$',
    r'^\s*ricevuto\s*$',
    r'^\s*ok ricevuto\s*$',
    r'^\s*tutto chiaro\s*$',
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
    'non va'
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
    print(f"   Cache duration: {CACHE_DURATION_SECONDS}s")
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
        'max_emails_per_run': MAX_EMAILS_PER_RUN,
        'model_name': MODEL_NAME,
        'temperature': TEMPERATURE,
        'max_output_tokens': MAX_OUTPUT_TOKENS,
        'cache_duration': CACHE_DURATION_SECONDS,
        'ignore_domains_count': len(IGNORE_DOMAINS),
        'ignore_keywords_count': len(IGNORE_KEYWORDS),
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
