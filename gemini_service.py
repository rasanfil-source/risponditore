"""
Gemini API service module for AI responses
Handles generating responses and summarizing conversations
"""

import requests
import json
import time
from typing import Optional, Dict
import config
from utils import get_current_season, get_special_day_greeting
from datetime import datetime
from zoneinfo import ZoneInfo

# Costante a livello di modulo
ITALIAN_TZ = ZoneInfo("Europe/Rome")


# ============ Retry Decorator ============

def retry_on_failure(max_retries=3, delay=2):
    """
    Decorator per retry automatico in caso di errore
    
    Args:
        max_retries: Numero massimo di tentativi
        delay: Ritardo base in secondi (con exponential backoff)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        print(f"⚠️  Gemini API attempt {attempt + 1}/{max_retries} failed: {e}")
                        print(f"   Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        print(f"❌ All {max_retries} Gemini API attempts failed")
                        raise
                except Exception as e:
                    # Per errori non di rete, non fare retry
                    print(f"❌ Gemini API error (no retry): {e}")
                    raise
        return wrapper
    return decorator


# ============ GeminiService Class ============

class GeminiService:
    def __init__(self):
        """Initialize Gemini service with API configuration"""
        self.api_key = config.GEMINI_API_KEY
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.MODEL_NAME}:generateContent"
        
        # Validazione API key
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not configured in environment variables. "
                "Please set GEMINI_API_KEY before running."
            )
        
        print(f"✓ Gemini service initialized with model: {config.MODEL_NAME}")
    
    def _detect_email_language(self, email_content: str, email_subject: str) -> str:
        """
        Detect the language of the email
        
        Args:
            email_content: Email body text
            email_subject: Email subject
            
        Returns:
            'it' for Italian, 'en' for English, 'es' for Spanish
        """
        text = (email_subject + ' ' + email_content).lower()
        
        # Simple keyword-based detection
        # English indicators
        english_keywords = ['the', 'and', 'would', 'could', 'please', 'thank you', 
                           'dear', 'we are', 'project', 'information', 'your', 'with',
                           'from', 'our', 'have', 'this', 'that', 'honored', 'exhibition',
                           'request', 'contribute', 'peace', 'students']
        english_score = sum(1 for kw in english_keywords if f' {kw} ' in f' {text} ')
        
        # Spanish indicators
        spanish_keywords = ['el', 'la', 'de', 'que', 'por favor', 'gracias',
                           'querido', 'somos', 'proyecto', 'información', 'con', 'para',
                           'su', 'este', 'esta']
        spanish_score = sum(1 for kw in spanish_keywords if f' {kw} ' in f' {text} ')
        
        # Italian indicators
        italian_keywords = ['il', 'la', 'di', 'che', 'per favore', 'grazie',
                           'gentile', 'siamo', 'progetto', 'informazioni', 'con', 'per',
                           'vorrei', 'quando', 'come']
        italian_score = sum(1 for kw in italian_keywords if f' {kw} ' in f' {text} ')
        
        # Determine language
        scores = {'it': italian_score, 'en': english_score, 'es': spanish_score}
        detected_lang = max(scores, key=scores.get)
        
        print(f"🌍 Language detection - IT={italian_score}, EN={english_score}, ES={spanish_score}")
        
        # If score is too low, default to Italian
        if scores[detected_lang] < 2:
            print(f"   Low confidence, defaulting to Italian")
            return 'it'
        
        print(f"   Detected: {detected_lang.upper()} (score: {scores[detected_lang]})")
        return detected_lang
    
    def _get_adaptive_greeting(self, now: datetime, sender_name: str, language: str = 'it') -> tuple:
        """
        Get greeting and closing adapted to language
        
        Args:
            now: Current datetime
            sender_name: Name of the sender
            language: Detected language code
            
        Returns:
            (greeting, closing) tuple
        """
        special_greeting = get_special_day_greeting(now)
        hour = now.hour
        day = now.weekday()
        
        # Italian greetings
        if language == 'it':
            if special_greeting:
                greeting = special_greeting
            elif day == 6:
                greeting = 'Buona domenica.'
            elif 6 <= hour < 13:
                greeting = 'Buongiorno.'
            elif 13 <= hour < 19:
                greeting = 'Buon pomeriggio.'
            elif 19 <= hour <= 23:
                greeting = 'Buonasera.'
            else:
                greeting = f'Gentile {sender_name},'
            
            closing = 'Cordiali saluti,'
        
        # English greetings
        elif language == 'en':
            if special_greeting:
                # Translate special greetings
                special_map = {
                    'Buon Natale!': 'Merry Christmas!',
                    'Buona Pasqua!': 'Happy Easter!',
                    'Buon Capodanno!': 'Happy New Year!',
                    'Buona Epifania!': 'Happy Epiphany!',
                    'Auguri per oggi!': 'Best wishes for today!',
                    'Buona festa di Ognissanti!': 'Happy All Saints\' Day!',
                    'Buona Immacolata!': 'Happy Immaculate Conception!',
                }
                greeting = special_map.get(special_greeting, 'Greetings,')
            elif day == 6:
                greeting = 'Happy Sunday,'
            elif 6 <= hour < 12:
                greeting = 'Good morning,'
            elif 12 <= hour < 18:
                greeting = 'Good afternoon,'
            elif 18 <= hour <= 23:
                greeting = 'Good evening,'
            else:
                greeting = f'Dear {sender_name},'
            
            closing = 'Kind regards,'
        
        # Spanish greetings
        elif language == 'es':
            if special_greeting:
                special_map = {
                    'Buon Natale!': '¡Feliz Navidad!',
                    'Buona Pasqua!': '¡Feliz Pascua!',
                    'Buon Capodanno!': '¡Feliz Año Nuevo!',
                    'Auguri per oggi!': '¡Felicidades por hoy!',
                }
                greeting = special_map.get(special_greeting, 'Saludos,')
            elif day == 6:
                greeting = 'Feliz domingo,'
            elif 6 <= hour < 13:
                greeting = 'Buenos días,'
            elif 13 <= hour < 20:
                greeting = 'Buenas tardes,'
            elif 20 <= hour <= 23:
                greeting = 'Buenas noches,'
            else:
                greeting = f'Estimado/a {sender_name},'
            
            closing = 'Cordiales saludos,'
        
        else:
            # Fallback to Italian
            greeting = f'Gentile {sender_name},'
            closing = 'Cordiali saluti,'
        
        return greeting, closing
    
    @retry_on_failure(max_retries=3, delay=2)
    def generate_response(
        self,
        email_content: str,
        email_subject: str,
        knowledge_base: str,
        sender_name: str,
        sender_email: str,
        conversation_history: str = "",
        category: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate AI response for an email with retry logic
        
        Args:
            email_content: Content of the email
            email_subject: Subject of the email
            knowledge_base: Knowledge base string
            sender_name: Name of the sender
            sender_email: Email address of sender
            conversation_history: Previous conversation history
            category: Email category from classifier (optional)
            
        Returns:
            AI generated response or None if error
        """
        # Check if it's just an acknowledgment (backup check)
        main_reply = self._extract_main_reply(email_content)
        if self._is_only_acknowledgement(main_reply):
            return "NO_REPLY"
        
        # Check for simple thank you patterns (backup check)
        normalized = email_content.strip().lower()
        thank_you_patterns = [
            r'^grazie\.?$',
            r'^grazie mille\.?$',
            r'^grazie di tutto\.?$',
            r'^ricevuto\.?$',
            r'^ok ricevuto\.?$',
            r'^tutto chiaro\.?$',
            r'^perfetto\.?$'
        ]
        
        import re
        for pattern in thank_you_patterns:
            if re.match(pattern, normalized):
                return "NO_REPLY"
        
        # Generate prompt
        prompt = self._build_prompt(
            email_content,
            email_subject,
            knowledge_base,
            sender_name,
            sender_email,
            conversation_history,
            category
        )
        
        # Call Gemini API with timeout
        try:
            print(f"🤖 Calling Gemini API for: {sender_email}")
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": config.TEMPERATURE,
                        "maxOutputTokens": config.MAX_OUTPUT_TOKENS
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=30  # 30 secondi di timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("candidates") and result["candidates"][0].get("content"):
                    generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"✓ Gemini response generated ({len(generated_text)} chars)")
                    return generated_text
                else:
                    print(f"❌ Invalid Gemini response structure: {result}")
                    return None
            else:
                print(f"❌ Gemini API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print(f"⏱️  Gemini API timeout after 30s")
            raise
        except Exception as e:
            print(f"❌ Error calling Gemini API: {e}")
            raise
    
    @retry_on_failure(max_retries=2, delay=1)
    def summarize_conversation(self, conversation_history: str) -> str:
        """
        Summarize a long conversation history with retry logic
        
        Args:
            conversation_history: Full conversation history
            
        Returns:
            Summarized conversation or original if short/error
        """
        # If history is short, no need to summarize
        word_count = len(conversation_history.split())
        if word_count < 60:
            return conversation_history
        
        prompt = f"""
Sei un assistente di segreteria. Riassumi la seguente conversazione email
in massimo 5 frasi, mantenendo SOLO:
- richieste specifiche dell'utente
- risposte già fornite dalla segreteria
- eventuali follow-up importanti
NON includere ringraziamenti, formule di cortesia, firme o dettagli irrilevanti.

Conversazione:
\"\"\"
{conversation_history}
\"\"\"
"""
        
        try:
            print(f"📝 Summarizing conversation ({word_count} words)...")
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 150
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=20  # 20 secondi di timeout per summarization
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("candidates") and result["candidates"][0].get("content"):
                    summary = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    # Validate summary
                    if len(summary.split()) < 15 or "non ho abbastanza informazioni" in summary.lower():
                        print("⚠️  Summary too short or vague, using full history")
                        return conversation_history
                    
                    print(f"✓ Conversation summarized ({len(summary.split())} words)")
                    return summary
                    
        except requests.exceptions.Timeout:
            print(f"⏱️  Summary timeout, using full history")
            return conversation_history
        except Exception as e:
            print(f"⚠️  Error summarizing conversation: {e}, using full history")
            return conversation_history
        
        return conversation_history
    
    def _build_prompt(
        self,
        email_content: str,
        email_subject: str,
        knowledge_base: str,
        sender_name: str,
        sender_email: str,
        conversation_history: str,
        category: Optional[str] = None
    ) -> str:
        """
        Build the prompt for Gemini API
        
        Returns:
            Complete prompt string
        """
        # Usa timezone italiano
        now = datetime.now(ITALIAN_TZ)
        
        # Detect language
        detected_language = self._detect_email_language(email_content, email_subject)
        
        # Get adaptive greeting and closing
        salutation, closing_phrase = self._get_adaptive_greeting(now, sender_name, detected_language)
        
        # Get current season
        current_season = get_current_season(now)
        seasonal_note = (
            'IMPORTANTE: Siamo attualmente nel periodo ESTIVO. Utilizza SOLO gli orari estivi nelle risposte.'
            if current_season == 'estivo'
            else 'IMPORTANTE: Siamo attualmente nel periodo INVERNALE. Utilizza SOLO gli orari invernali nelle risposte.'
        )
        
        # Language instruction based on detected language
        if detected_language == 'en':
            language_instruction = (
                "🚨 CRITICAL PRIORITY INSTRUCTION 🚨\n"
                "This email is written in ENGLISH.\n"
                "You MUST respond ENTIRELY and EXCLUSIVELY in English.\n"
                "Do NOT use ANY Italian words or phrases.\n"
                "Translate ALL parish information to English.\n"
                "This rule has ABSOLUTE PRIORITY over all other instructions."
            )
        elif detected_language == 'es':
            language_instruction = (
                "🚨 INSTRUCCIÓN CRÍTICA DE MÁXIMA PRIORIDAD 🚨\n"
                "Este correo está escrito en ESPAÑOL.\n"
                "Debes responder COMPLETA y EXCLUSIVAMENTE en español.\n"
                "NO uses NINGUNA palabra o frase en italiano.\n"
                "Traduce TODA la información parroquial al español.\n"
                "Esta regla tiene PRIORIDAD ABSOLUTA sobre todas las demás instrucciones."
            )
        else:
            language_instruction = (
                "Rispondi SEMPRE nella stessa lingua in cui è scritta l'email ricevuta. "
                "Se l'email è in inglese, rispondi in inglese. "
                "Se è in spagnolo, rispondi in spagnolo. "
                "Non tradurre e non mischiare lingue."
            )
        
        # Build prompt parts
        prompt_parts = [
            "Sei la segreteria della Parrocchia di Sant'Eugenio a Roma.",
            "Rispondi alle email in modo conciso, chiaro e solo con le informazioni esplicitamente richieste.",
            "",
            "="*60,
            language_instruction,
            "="*60,
            "",
            "**INFORMAZIONI DI RIFERIMENTO DELLA PARROCCHIA:**",
            knowledge_base,
            "",
            "**GESTIONE ORARI STAGIONALI:**",
            seasonal_note,
            "Non mostrare mai contemporaneamente sia gli orari estivi che quelli invernali. Mostra SOLO quelli del periodo corrente.",
            "",
        ]
        
        # Add category hint if available
        if category:
            category_hints = {
                'appointment': "NOTA: Questa email riguarda la richiesta di un appuntamento. Fornisci informazioni su come fissare appuntamenti e gli orari disponibili.",
                'information': "NOTA: Questa email richiede informazioni generali. Rispondi in modo chiaro e completo basandoti sulla knowledge base.",
                'sacrament': "NOTA: Questa email riguarda i sacramenti. Fornisci informazioni dettagliate sui requisiti e le procedure.",
                'collaboration': "NOTA: Questa email propone collaborazione o volontariato. Ringrazia e spiega come procedere.",
                'complaint': "NOTA: Questa email potrebbe contenere un reclamo. Rispondi con empatia e professionalità."
            }
            
            if category in category_hints:
                prompt_parts.extend([
                    "**CATEGORIA EMAIL IDENTIFICATA:**",
                    category_hints[category],
                    ""
                ])
        
        # Add conversation history if present
        if conversation_history:
            prompt_parts.extend([
                "**CRONOLOGIA DELLA CONVERSAZIONE (CONTESTO):**",
                "Di seguito i messaggi precedenti. Analizzali per capire il contesto ed evitare di ripetere informazioni già date.",
                '"""',
                conversation_history,
                '"""',
                "",
            ])
        
        # Add current email
        prompt_parts.extend([
            "**ULTIMA EMAIL RICEVUTA (A CUI RISPONDERE):**",
            f"Da: {sender_email} (Nome di fallback: {sender_name})",
            f"Oggetto: {email_subject}",
            f"🌍 LINGUA RILEVATA: {detected_language.upper()}",
            "Contenuto:",
            '"""',
            email_content,
            '"""',
            "",
            "⚠️ **REGOLA CRITICA - NO_REPLY (LEGGI ATTENTAMENTE):**",
            "Se l'email ricade in UNA QUALSIASI di queste categorie, devi rispondere ESATTAMENTE e SOLAMENTE con la parola \"NO_REPLY\" (senza aggiungere altro testo, spiegazioni o commenti):",
            "",
            "CATEGORIE DA IGNORARE (rispondi solo \"NO_REPLY\"):",
            "1. Newsletter, comunicazioni promozionali, pubblicità",
            "2. Email automatiche da servizi online (Amazon, PayPal, eBay, Subito.it, etc.)",
            "3. Notifiche di pagamento, bollette, ricevute, bonifici, fatture",
            "4. Avvisi di spedizione o tracciamento pacchi",
            "5. Avvisi di sicurezza o notifiche di accesso",
            "6. Email di condoglianze o necrologi",
            "7. Email che contengono \"non rispondere a questo messaggio\" o \"no-reply\"",
            "8. Email da indirizzi esplicitamente da ignorare (rasanfil@gmail.com, miqueldg63@gmail.com, rego.juan@gmail.com)",
            "9. Email contenenti ESCLUSIVAMENTE ringraziamenti o conferme di ricezione (es: \"grazie\", \"ricevuto\", \"ok ricevuto\")",
            "10. Comunicazioni politiche, elettorali o di partiti",
            "11. Email con link tipo \"Cancella iscrizione\", \"Unsubscribe\", \"Gestisci iscrizione\"",
            "",
            "⚠️ IMPORTANTE: \"NO_REPLY\" significa che il sistema NON invierà ALCUNA risposta. Non devi scrivere un messaggio che dice \"questa email non richiede risposta\". Scrivi SOLO la parola \"NO_REPLY\" e basta.",
            "",
            "**ISTRUZIONI DETTAGLIATE:**",
            "0. Se l'ultimo messaggio ricevuto contiene esclusivamente un ringraziamento o una conferma di ricezione, rispondi esattamente e solo con \"NO_REPLY\", indipendentemente dal contenuto della cronologia precedente.",
            f"1. **Analisi dell'Interlocutore (COMPITO PRIORITARIO):** Leggi attentamente il contenuto e la firma. Cerca nomi, pronomi o altri indizi per identificare il mittente. Se non riesci a determinare il nome, usa una forma generica come \"Gentile utente,\".",
            f"2. **Saluto Iniziale (IMPORTANTE):** Inizia la tua risposta esattamente con \"{salutation}\". Non aggiungere altro prima di questo saluto.",
            "3. **Corpo della Risposta:** Rispondi alla richiesta in modo chiaro e completo, basandoti esclusivamente sulle \"INFORMAZIONI DI RIFERIMENTO\" fornite.",
            "",
            "3-bis. **Email contenenti proposte pastorali, culturali, musicali o richieste insolite:**",
            "   1. Ringrazia il mittente per l'iniziativa",
            "   2. Mostra apprezzamento per elementi specifici della proposta",
            "   3. Conferma che la proposta sarà esaminata a breve",
            "   4. Comunica che verrà fornita una risposta in tempi rapidi",
            "",
            "4. **Gestione Informazioni Mancanti:** Se non hai le informazioni per rispondere, indicalo gentilmente e spiega che la segreteria prenderà in carico la richiesta.",
            "4-bis. **Richiesta di fissare date:** Rispondere che la segreteria esaminerà se è possibile accontentare la richiesta e farà sapere al più presto.",
            "5. **Gestione Follow-up:** Se l'oggetto inizia con \"Re:\" o \"R:\", significa che è un'email di follow-up. Sii più diretto e conciso.",
            f"5-bis. **Orari Stagionali:** Quando fornisci orari di apertura, mostra SOLO gli orari del periodo corrente ({current_season}). Non elencare mai entrambi i set di orari.",
            "6. **FILTRO INTELLIGENTE (NON RISPONDERE):** Se l'email rientra in una delle categorie da ignorare, rispondi solo con \"NO_REPLY\".",
            "",
            "6-bis. **Cresima adulti / Cresima ragazzi:**",
            "- Se la richiesta è scritta da un genitore per il proprio figlio, rispondi con le informazioni relative alla Cresima ragazzi.",
            "- Se la richiesta è scritta da un adulto per sé stesso, rispondi con le informazioni relative alla Cresima adulti.",
            "",
            "6-ter. **Informazioni sul ruolo di padrino/madrina:**",
            "- Se e solo se l'interlocutore dice che intende fare da padrino o madrina, integra le seguenti indicazioni:",
            '"Chi si avvicina alla Cresima con l\'intento di diventare padrino o madrina tenga presente i criteri da rispettare per essere idonei: aver compiuto 16 anni, non vivere in convivenza né essersi sposati solo civilmente, non aver procurato divorzio o essersi risposati civilmente, non essere genitore del cresimando, impegnarsi a condurre vita cristiana conforme alla fede."',
            "- se l'interlocutore non allude alla possibilità di fare da padrino o madrina, non menzionare questi criteri.",
            "",
            "7. Se una persona scrive dicendo che vorrebbe partecipare a una catechesi ma che impegni di lavoro o familiari non glielo consentono, rispondere dicendo che è possibile seguire programmi per venire incontro alle sue esigenze.",
            "8. **Risposte strettamente pertinenti:** Limita la risposta a ciò che è stato espressamente chiesto.",
            "8-bis. **Filtro temporale:** Se la domanda specifica un periodo temporale, limita la risposta SOLO a quel periodo.",
            "",
            f"9. **Chiusura:** Termina la risposta con \"{closing_phrase}\".",
            "",
            "**INTEGRAZIONI IMPORTANTI (VINCOLANTI):**",
            f"- **Lingua della risposta (PRIORITÀ ASSOLUTA):** Rispondi INTERAMENTE in {detected_language.upper()}. NON mescolare lingue.",
            "- **FILTRO TEMPORALE ASSOLUTO:** Quando una domanda contiene \"a [mese]\" o \"nel [periodo]\", rispondi SOLO con informazioni di quel specifico periodo.",
            "- **Distinzione certificato idoneità vs criteri Cresima:** se l'email parla di certificato/attestato di idoneità per fare da padrino/madrina, non elencare i criteri di idoneità della Cresima.",
            "- **Uso delle Informazioni Specifiche (CRUCIALE):** Quando la base di conoscenza fornisce un dettaglio specifico, DEVI USARE QUELLO.",
            f"- **Orari stagionali (CRUCIALE):** Quando menzioni orari di apertura, usa ESCLUSIVAMENTE quelli del periodo corrente ({current_season}).",
            f"- **Formato della risposta:** inizia esattamente con \"{salutation}\".",
            "  Corpo essenziale.",
            "  Chiudi esattamente con:",
            f"  \"{closing_phrase}\"",
            "  Segreteria Parrocchia Sant'Eugenio",
            "",
            f"- **Lingua della risposta (VINCOLANTE):** usa la lingua {detected_language.upper()}.",
            "CONTROLLO FINALE (obbligatorio):",
            f"Dopo aver scritto la risposta, rileggila con attenzione e verifica che sia interamente in {detected_language.upper()}.",
            "Riconosci con chiarezza ciò che l'interlocutore ha già fatto o comunicato, anche implicitamente.",
            "Non ripetere istruzioni o informazioni che lui stesso dichiara di aver già eseguito o compreso.",
            "Evita spiegazioni o suggerimenti che non aggiungono nulla di nuovo, né migliorano la chiarezza o la cortesia.",
            "Se il messaggio del mittente contiene un'azione già compiuta (es. «ho allegato il modulo»), non dire cosa dovrebbe fare, ma conferma con gratitudine e indica con semplicità il passo successivo, se esiste.",
            "Infine, rileggi l'intera risposta come se fossi tu a riceverla: deve suonare naturale, pertinente e rispettosa del tempo dell'altro.",
            "",
            "Adesso, genera la risposta completa utilizzando tutte le informazioni disponibili:"
        ])
        
        return '\n'.join(prompt_parts)
    
    def _extract_main_reply(self, content: str) -> str:
        """Extract main reply content without quoted text"""
        import re
        
        markers = [r'^>', r'^On .* wrote:', r'^Il giorno .* ha scritto:']
        cut_content = content
        
        for marker in markers:
            match = re.search(marker, content, re.MULTILINE)
            if match:
                cut_content = content[:match.start()]
                break
        
        return cut_content.strip()
    
    def _is_only_acknowledgement(self, text: str) -> bool:
        """Check if text is only an acknowledgement"""
        if not text:
            return False
        
        import re
        
        cleaned = text.lower().replace(' ', '').strip()
        cleaned = re.sub(r'[^\w\sàèéìòù?]', '', cleaned)
        
        ack_patterns = [
            r'^grazie$', r'^graziemille$', r'^grazieancora$',
            r'^graziedicuore$', r'^viringrazio$', r'^tiringrazio$',
            r'^laringrazio$', r'^ricevuto$', r'^okricevuto$',
            r'^tuttochiaro$', r'^perfetto$'
        ]
        
        for pattern in ack_patterns:
            if re.match(pattern, cleaned):
                return True
        
        # Check if contains thanks/received with a question
        if ('grazie' in cleaned or 'ricevuto' in cleaned):
            if '?' in cleaned or any(word in cleaned for word in 
                ['quando', 'come', 'dove', 'cosa', 'che', 'chi', 'perché',
                 'posso', 'potrei', 'vorrei', 'sapere', 'chiedo']):
                return False
            return True
        
        return False
