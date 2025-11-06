"""
Gemini API service module for AI responses
Handles generating responses and conversation management
🔧 OPTIMIZED v3.0: Integrated PromptEngine v3.0 for 60% token reduction
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
from prompt_engine import PromptEngineV3, PromptContext  # ← v3.0
from territory_validator import TerritoryValidator

logger = logging.getLogger(__name__)

# Italian timezone constant
ITALIAN_TZ = ZoneInfo("Europe/Rome")


# ============================================================================
# RETRY DECORATOR WITH EXPONENTIAL BACKOFF
# ============================================================================

def retry_on_failure(max_retries=3, delay=2, backoff_factor=2):
    """
    Decorator for automatic retry with exponential backoff

    Args:
        max_retries: Maximum number of attempts
        delay: Base delay in seconds
        backoff_factor: Multiplier for exponential backoff
    """
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
                        logger.warning(f"⚠️  Gemini API network error (attempt {attempt + 1}/{max_retries}): {e}")
                        logger.info(f"   Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"❌ All {max_retries} Gemini API attempts failed")
                        raise
                except Exception as e:
                    # For non-network errors, don't retry
                    logger.error(f"❌ Gemini API error (no retry): {e}")
                    raise
        return wrapper
    return decorator


# ============================================================================
# GEMINISERVICE CLASS
# ============================================================================

class GeminiService:
    """
    Service for Gemini AI API interactions

    🔧 v3.0 IMPROVEMENTS:
    - Integrated PromptEngine v3.0 (adaptive prompts)
    - Removed expensive summarization
    - Better retry logic with exponential backoff
    - Improved timeout handling
    - Response validation
    - Cost monitoring
    """

    def __init__(self):
        """Initialize Gemini service with API configuration"""
        self.api_key = config.GEMINI_API_KEY
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.MODEL_NAME}:generateContent"

        # Validate API key
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not configured in environment variables. "
                "Please set GEMINI_API_KEY before running."
            )

        if len(self.api_key) < 20:
            logger.warning("⚠️  GEMINI_API_KEY seems too short, please verify")

        # Initialize PromptEngine v3.0
        self.prompt_engine = PromptEngineV3()
        logger.info("✓ Using PromptEngine v3.0 (Optimized & Adaptive)")
        
        # Initialize TerritoryValidator
        self.territory_validator = TerritoryValidator()

        logger.info(f"✓ Gemini service initialized with model: {config.MODEL_NAME}")

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

        logger.debug(f"🌍 Language detection - IT={italian_score}, EN={english_score}, ES={spanish_score}")

        # If score is too low, default to Italian
        if scores[detected_lang] < 2:
            logger.debug(f"   Low confidence, defaulting to Italian")
            return 'it'

        logger.info(f"   Detected: {detected_lang.upper()} (score: {scores[detected_lang]})")
        return detected_lang

    def _get_adaptive_greeting(self, now: datetime, sender_name: str, language: str = 'it') -> tuple:
        """
        Get greeting and closing adapted to language and time

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
        Generate AI response for an email with optimized prompts
        
        v3.0 Changes:
        - Uses PromptEngine v3.0 for adaptive prompt generation
        - 60% smaller prompts for follow-ups
        - No more expensive summarization
        - Better cost efficiency
        
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
            logger.info("   Gemini: Detected acknowledgment, returning NO_REPLY")
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
                logger.info("   Gemini: Matched thank-you pattern, returning NO_REPLY")
                return "NO_REPLY"

        # Detect language and prepare context
        now = datetime.now(ITALIAN_TZ)
        detected_language = self._detect_email_language(email_content, email_subject)
        salutation, closing = self._get_adaptive_greeting(now, sender_name, detected_language)
        current_season = get_current_season(now)

        # ═══════════════════════════════════════════════════════════════
        # VERIFICA AUTOMATICA TERRITORIO PARROCCHIALE
        # ═══════════════════════════════════════════════════════════════
        territory_info = self.territory_validator.analyze_email_for_address(
            email_content, email_subject
        )

        if territory_info['address_found']:
            verification = territory_info['verification']
            logger.info(f"🏘️ Territory check: {verification['reason']}")
            
            territory_context = f"""
{'='*70}
🎯 VERIFICA TERRITORIO AUTOMATICA (INFORMAZIONE VERIFICATA - PRIORITÀ ASSOLUTA)
{'='*70}
Indirizzo rilevato nell'email: {territory_info['street']} n. {territory_info['civic']}

Risultato verifica: {'✅ RIENTRA NEL TERRITORIO PARROCCHIALE' if verification['in_parish'] else '❌ NON RIENTRA NEL TERRITORIO PARROCCHIALE'}

Dettaglio: {verification['reason']}

⚠️ ISTRUZIONE VINCOLANTE:
Usa ESATTAMENTE queste informazioni verificate programmaticamente per rispondere 
alla domanda sul territorio. NON fare supposizioni, NON interpretare, 
usa SOLO il risultato di questa verifica automatica.
{'='*70}

"""
            knowledge_base = territory_context + knowledge_base
            logger.debug(f"   📋 Territory context added to prompt ({len(territory_context)} chars)")

        # ═══════════════════════════════════════════════════════════════
        # v3.0: OPTIMIZED PROMPT GENERATION WITH ADAPTIVE ENGINE
        # ═══════════════════════════════════════════════════════════════
        
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

        # Log prompt size for monitoring
        tokens_estimate = self.prompt_engine.estimate_tokens(prompt)
        logger.info(f"🤖 Calling Gemini API")
        logger.info(f"   Prompt: {len(prompt)} chars (~{tokens_estimate} tokens)")
        logger.debug(f"   Email: {sender_email}")

        # Validate prompt size
        if len(prompt) > 100000:
            logger.warning(f"⚠️  Prompt very large ({len(prompt)} chars), may cause issues")

        # Call Gemini API with timeout
        try:
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

                # Validate response structure
                if not result.get("candidates"):
                    logger.error(f"❌ Invalid Gemini response: no candidates")
                    logger.debug(f"   Response: {result}")
                    return None

                if not result["candidates"][0].get("content"):
                    logger.error(f"❌ Invalid Gemini response: no content in candidate")
                    logger.debug(f"   Response: {result}")
                    return None

                generated_text = result["candidates"][0]["content"]["parts"][0]["text"]

                # Validate generated text
                if not generated_text or len(generated_text.strip()) == 0:
                    logger.error(f"❌ Gemini returned empty response")
                    return None

                # Log response size and cost estimate
                output_tokens = len(generated_text) // 4
                input_cost = tokens_estimate * 0.000000075  # $0.075 per 1M tokens
                output_cost = output_tokens * 0.00000030    # $0.30 per 1M tokens
                total_cost = input_cost + output_cost

                logger.info(f"✓ Gemini response generated")
                logger.info(f"   Output: {len(generated_text)} chars (~{output_tokens} tokens)")
                logger.info(f"   💰 Est. cost: ${total_cost:.6f} (in: ${input_cost:.6f}, out: ${output_cost:.6f})")

                return generated_text
            else:
                logger.error(f"❌ Gemini API error: {response.status_code}")
                logger.error(f"   Response: {response.text[:500]}")
                return None

        except requests.exceptions.Timeout:
            logger.error(f"⏱️  Gemini API timeout after 30s")
            raise  # Let retry decorator handle it
        except Exception as e:
            logger.error(f"❌ Error calling Gemini API: {e}")
            raise

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
        cleaned = text.lower().replace(',', '').strip()
        cleaned = re.sub(r'\?', '', cleaned)
        words_in_text = cleaned.split()
        
        # Ultra-simple acknowledgments only
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
        
        # 🔴 PRIORITÀ: Se ha QUALSIASI parola di richiesta → RISPONDI!
        request_words = ['vorrei', 'sapere', 'informazioni', 'quando', 'come', 'dove',
                        'orari', 'orario', 'costo', 'prezzo', 'quanto']
        
        if any(word in words_in_text for word in request_words):
            return False  # ← HA RICHIESTA, RISPONDI!
        
        # Solo SE ha "grazie" E NON ha richieste → è acknowledgment
        if 'grazie' in cleaned and len(words_in_text) <= 3:
            return True
        
        return False

    # ========================================================================
    # HEALTH CHECK AND DIAGNOSTICS
    # ========================================================================

    def test_connection(self) -> Dict:
        """
        Test Gemini API connection

        Returns:
            Dictionary with test results
        """
        results = {
            'connection_ok': False,
            'can_generate': False,
            'errors': []
        }

        try:
            # Test simple generation
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
    
    def get_stats(self) -> Dict:
        """Get service statistics"""
        return {
            'model': config.MODEL_NAME,
            'temperature': config.TEMPERATURE,
            'max_output_tokens': config.MAX_OUTPUT_TOKENS,
            'prompt_engine_version': '3.0',
            'prompt_engine_stats': self.prompt_engine.get_stats()
        }