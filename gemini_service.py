"""
Gemini API service module for AI responses - CLEANED VERSION
✅ FIXED: Removed all duplications, using only PromptEngine
✅ FIXED: Removed deprecated _build_prompt method
"""

import requests
import json
import time
from typing import Optional, Dict
import config
from utils import get_current_season, get_special_day_greeting
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from prompt_engine import PromptEngine, PromptContext
from territory_validator import TerritoryValidator

logger = logging.getLogger(__name__)

ITALIAN_TZ = ZoneInfo("Europe/Rome")


def retry_on_failure(max_retries=3, delay=2, backoff_factor=2):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout as e:
                    if attempt < max_retries - 1:
                        wait_time = delay * (backoff_factor ** attempt)
                        logger.warning(f"⚠️  Gemini API timeout (attempt {attempt + 1}/{max_retries})")
                        logger.info(f"   Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ All {max_retries} Gemini API attempts timed out")
                        raise
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        wait_time = delay * (backoff_factor ** attempt)
                        logger.warning(f"⚠️  Gemini API error (attempt {attempt + 1}/{max_retries}): {e}")
                        logger.info(f"   Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ All {max_retries} Gemini API attempts failed")
                        raise
                except Exception as e:
                    logger.error(f"❌ Gemini API error (no retry): {e}")
                    raise
        return wrapper
    return decorator


class GeminiService:
    """Service for Gemini AI API interactions - CLEANED VERSION"""

    def __init__(self):
        """Initialize Gemini service"""
        self.api_key = config.GEMINI_API_KEY
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.MODEL_NAME}:generateContent"

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        if len(self.api_key) < 20:
            logger.warning("⚠️  GEMINI_API_KEY seems too short")

        # ✅ FIXED: Initialize only once
        self.prompt_engine = PromptEngine()
        self.territory_validator = TerritoryValidator()

        logger.info(f"✓ Gemini service initialized with model: {config.MODEL_NAME}")

    def _detect_email_language(self, email_content: str, email_subject: str) -> str:
        """
        Detect email language
        
        ✅ CENTRALIZED: This is the ONLY place for language detection
        """
        text = (email_subject + ' ' + email_content).lower()

        # Language indicators
        english_keywords = ['the', 'and', 'would', 'could', 'please', 'thank you',
                           'dear', 'we are', 'project', 'information']
        spanish_keywords = ['el', 'la', 'de', 'que', 'por favor', 'gracias',
                           'querido', 'somos', 'proyecto']
        italian_keywords = ['il', 'la', 'di', 'che', 'per favore', 'grazie',
                           'gentile', 'siamo', 'progetto']

        # Count matches
        scores = {
            'en': sum(1 for kw in english_keywords if f' {kw} ' in f' {text} '),
            'es': sum(1 for kw in spanish_keywords if f' {kw} ' in f' {text} '),
            'it': sum(1 for kw in italian_keywords if f' {kw} ' in f' {text} ')
        }

        detected_lang = max(scores, key=scores.get)
        
        # Low confidence = default to Italian
        if scores[detected_lang] < 2:
            logger.debug("Low confidence, defaulting to Italian")
            return 'it'

        logger.info(f"Detected: {detected_lang.upper()} (score: {scores[detected_lang]})")
        return detected_lang

    def _get_adaptive_greeting(self, now: datetime, sender_name: str, language: str = 'it') -> tuple:
        """Get greeting and closing adapted to language and time"""
        special_greeting = get_special_day_greeting(now)
        hour = now.hour
        day = now.weekday()

        # Italian
        if language == 'it':
            if special_greeting:
                greeting = special_greeting
            elif day == 6:
                greeting = 'Buona domenica.'
            elif 6 <= hour < 13:
                greeting = 'Buongiorno.'
            elif 13 <= hour < 19:
                greeting = 'Buon pomeriggio.'
            else:
                greeting = 'Buonasera.'
            closing = 'Cordiali saluti,'

        # English
        elif language == 'en':
            if special_greeting:
                special_map = {
                    'Buon Natale!': 'Merry Christmas!',
                    'Buona Pasqua!': 'Happy Easter!',
                    'Buon Capodanno!': 'Happy New Year!',
                }
                greeting = special_map.get(special_greeting, 'Greetings,')
            elif day == 6:
                greeting = 'Happy Sunday,'
            elif 6 <= hour < 12:
                greeting = 'Good morning,'
            elif 12 <= hour < 18:
                greeting = 'Good afternoon,'
            else:
                greeting = 'Good evening,'
            closing = 'Kind regards,'

        # Spanish
        elif language == 'es':
            if special_greeting:
                special_map = {
                    'Buon Natale!': '¡Feliz Navidad!',
                    'Buona Pasqua!': '¡Feliz Pascua!',
                }
                greeting = special_map.get(special_greeting, 'Saludos,')
            elif day == 6:
                greeting = 'Feliz domingo,'
            elif 6 <= hour < 13:
                greeting = 'Buenos días,'
            else:
                greeting = 'Buenas tardes,'
            closing = 'Cordiales saludos,'

        else:
            greeting = f'Gentile {sender_name},'
            closing = 'Cordiali saluti,'

        return greeting, closing

    @retry_on_failure(max_retries=3, delay=2, backoff_factor=2)
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
        Generate AI response - CLEANED VERSION
        
        ✅ FIXED: Uses ONLY PromptEngine, no duplication
        """
        # Quick check for acknowledgment
        main_reply = self._extract_main_reply(email_content)
        if self._is_only_acknowledgement(main_reply):
            logger.info("Detected acknowledgment, returning NO_REPLY")
            return "NO_REPLY"

        # Detect language and prepare context
        now = datetime.now(ITALIAN_TZ)
        detected_language = self._detect_email_language(email_content, email_subject)
        salutation, closing = self._get_adaptive_greeting(now, sender_name, detected_language)
        current_season = get_current_season(now)

        # ═══════════════════════════════════════════════════════════════
        # Territory verification (if address found in email)
        # ═══════════════════════════════════════════════════════════════
        territory_info = self.territory_validator.analyze_email_for_address(
            email_content, email_subject
        )

        if territory_info['address_found']:
            verification = territory_info['verification']
            logger.info(f"🏘️ Territory: {verification['reason']}")
            
            territory_context = f"""
{'='*70}
🎯 VERIFICA TERRITORIO AUTOMATICA (INFORMAZIONE VERIFICATA)
{'='*70}
Indirizzo: {territory_info['street']} n. {territory_info['civic']}

Risultato: {'✅ RIENTRA' if verification['in_parish'] else '❌ NON RIENTRA'}

Dettaglio: {verification['reason']}

⚠️ Usa ESATTAMENTE queste informazioni verificate programmaticamente.
{'='*70}
"""
            knowledge_base = territory_context + knowledge_base

        # ✅ FIXED: Use PromptEngine (single source of truth)
        prompt = self.prompt_engine.build_prompt(
            email_content=email_content,
            email_subject=email_subject,
            knowledge_base=knowledge_base,
            sender_name=sender_name,
            sender_email=sender_email,
            conversation_history=conversation_history,
            category=category,
            detected_language=detected_language,
            current_season=current_season,
            now=now,
            salutation=salutation,
            closing=closing
        )

        # Validate prompt size
        if len(prompt) > 100000:
            logger.warning(f"⚠️  Prompt very large ({len(prompt)} chars)")

        # Call Gemini API
        try:
            logger.info(f"🤖 Calling Gemini API for: {sender_email}")
            logger.debug(f"   Prompt size: {len(prompt)} chars")

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
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                if not result.get("candidates"):
                    logger.error("❌ Invalid Gemini response: no candidates")
                    return None

                if not result["candidates"][0].get("content"):
                    logger.error("❌ Invalid Gemini response: no content")
                    return None

                generated_text = result["candidates"][0]["content"]["parts"][0]["text"]

                if not generated_text or len(generated_text.strip()) == 0:
                    logger.error("❌ Gemini returned empty response")
                    return None

                logger.info(f"✓ Response generated ({len(generated_text)} chars)")
                return generated_text
            else:
                logger.error(f"❌ Gemini API error: {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")
                return None

        except requests.exceptions.Timeout:
            logger.error("⏱️  Gemini API timeout after 30s")
            raise
        except Exception as e:
            logger.error(f"❌ Error calling Gemini API: {e}")
            raise

    @retry_on_failure(max_retries=2, delay=1, backoff_factor=2)
    def summarize_conversation(self, conversation_history: str) -> str:
        """Summarize long conversation history"""
        word_count = len(conversation_history.split())
        if word_count < 60:
            return conversation_history

        prompt = f"""
Riassumi la seguente conversazione email in massimo 5 frasi, mantenendo SOLO:
- richieste specifiche
- risposte già fornite
- eventuali follow-up importanti

Conversazione:
{conversation_history}
"""

        try:
            logger.info(f"📝 Summarizing conversation ({word_count} words)...")

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
                timeout=20
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("candidates") and result["candidates"][0].get("content"):
                    summary = result["candidates"][0]["content"]["parts"][0]["text"].strip()

                    if len(summary.split()) < 15:
                        logger.warning("⚠️  Summary too short, using full history")
                        return conversation_history

                    logger.info(f"✓ Conversation summarized")
                    return summary

        except requests.exceptions.Timeout:
            logger.warning("⏱️  Summary timeout, using full history")
            return conversation_history
        except Exception as e:
            logger.warning(f"⚠️  Error summarizing: {e}, using full history")
            return conversation_history

        return conversation_history

    def _extract_main_reply(self, content: str) -> str:
        """Extract main reply without quoted text"""
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
        """Check if text is only acknowledgement"""
        if not text:
            return False
        
        import re
        cleaned = text.lower().replace(',', '').strip()
        cleaned = re.sub(r'\?', '', cleaned)
        words_in_text = cleaned.split()
        
        # Ultra-simple patterns
        ack_patterns = [
            r'^grazie$',
            r'^grazie\s*mille$',
            r'^ricevuto$',
            r'^ok\s*ricevuto$',
            r'^perfetto$',
            r'^ok$'
        ]
        
        for pattern in ack_patterns:
            if re.match(pattern, cleaned):
                return True
        
        # If has request words → NOT acknowledgment
        request_words = ['vorrei', 'sapere', 'informazioni', 'quando', 'come']
        if any(word in words_in_text for word in request_words):
            return False
        
        # Only if has "grazie" AND no requests
        if 'grazie' in cleaned and len(words_in_text) <= 3:
            return True
        
        return False

    def test_connection(self) -> Dict:
        """Test Gemini API connection"""
        results = {
            'connection_ok': False,
            'can_generate': False,
            'errors': []
        }

        try:
            test_prompt = "Rispondi con una sola parola: OK"

            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": test_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 10
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            results['connection_ok'] = response.status_code == 200

            if response.status_code == 200:
                result = response.json()
                if result.get("candidates"):
                    results['can_generate'] = True
                else:
                    results['errors'].append("API returned no candidates")
            else:
                results['errors'].append(f"API returned status {response.status_code}")

        except Exception as e:
            results['errors'].append(f"Connection error: {str(e)}")

        results['is_healthy'] = results['connection_ok'] and results['can_generate']
        return results