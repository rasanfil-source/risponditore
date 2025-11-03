from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

with open('service-account-key.json') as f:
    creds_info = json.load(f)

creds = service_account.Credentials.from_service_account_info(
    creds_info,
    scopes=['https://www.googleapis.com/auth/gmail.readonly']
).with_subject('info@parrocchiasanteugenio.it')

service = build('gmail', 'v1', credentials=creds)

# Non esiste un'API "getWatch", ma possiamo verificare il profile
try:
    profile = service.users().getProfile(userId='me').execute()
    print(f"✓ Account Gmail accessibile: {profile['emailAddress']}")
    print(f"✓ Messaggi totali: {profile['messagesTotal']}")
    print("✓ Se non ci sono errori, il watch dovrebbe essere attivo")
except Exception as e:
    print(f"✗ Errore: {e}")
