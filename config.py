"""
Configuration module for Parish Secretary Cloud Function
Contains all environment variables and constants
"""

import os
from datetime import datetime, timedelta

# Google Workspace Configuration
IMPERSONATE_EMAIL = os.environ.get('IMPERSONATE_EMAIL', 'segreteria@parrocchia.it')
SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE', 'service-account-key.json')

# API Keys and IDs
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Istruzioni')
REPLACEMENTS_SHEET = os.environ.get('REPLACEMENTS_SHEET', 'Sostituzioni')

# Pub/Sub Configuration
PUBSUB_TOPIC = os.environ.get('PUBSUB_TOPIC', 'gmail-notifications')
PUBSUB_SUBSCRIPTION = os.environ.get('PUBSUB_SUBSCRIPTION', 'gmail-notifications-sub')

# Gmail Configuration
LABEL_NAME = os.environ.get('LABEL_NAME', 'IA')
MAX_EMAILS_PER_RUN = int(os.environ.get('MAX_EMAILS_PER_RUN', '10'))

# Gemini Model Configuration
MODEL_NAME = 'gemini-2.0-flash'
TEMPERATURE = 0.6
MAX_OUTPUT_TOKENS = 800

# Cache Configuration
CACHE_DURATION_SECONDS = 3600  # 1 hour

# NLP Classification Thresholds
SIMPLE_ACK_THRESHOLD = 0.9  # Soglia per classificare come semplice ringraziamento
NEEDS_REPLY_THRESHOLD = 0.55  # Soglia per necessità di risposta

# Seasonal Periods
SUMMER_START = (6, 29)  # June 29
SUMMER_END = (8, 30)    # August 30

# Suspension Hours by Day (0=Monday, 6=Sunday)
SUSPENSION_HOURS = {
    0: [(8, 20)],           # Monday: 8-20
    1: [(8, 14)],           # Tuesday: 8-14
    3: [(8, 14)],           # Thursday: 8-14
    2: [(8, 17)],           # Wednesday: 8-17
    4: [(8, 17)],           # Friday: 8-17
}

# Special Periods (MM-DD format)
SPECIAL_PERIODS = [
    ((12, 24), (1, 6)),     # Christmas to Epiphany
    ((8, 15), (8, 30)),     # Mid-August vacation
]

# Holiday Dates (MM-DD format)
HOLIDAYS = [
    (4, 25),   # April 25
    (5, 1),    # May 1
    (8, 15),   # August 15
    (11, 1),   # November 1
    (12, 8),   # December 8
]

# Email Ignore Lists
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

# Simple Acknowledgment Patterns (per messaggi che non richiedono risposta)
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

# Force Reply Keywords (se presenti nel messaggio, si risponde sempre)
FORCE_REPLY_KEYWORDS = [
    'non va bene',
    'sbagliato',
    'errore',
    'non funziona',
    'non è giusto',
    'non corretto',
    'non va'
]
