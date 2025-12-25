"""
Gemini API service module for AI responses - CLEANED VERSION
✅ FIXED: Removed all duplications, using only PromptEngine
✅ FIXED: Removed deprecated _build_prompt method
"""

import requests
import json
import time
from typing import Optional, Dict, Any, Union
import config
from utils import get_current_season, get_special_day_greeting, compute_salutation_mode
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from prompt_engine import PromptEngine, PromptContext
from prompt_context import create_prompt_context
from knowledge_engine import KnowledgeEngine
from territory_validator import TerritoryValidator
from request_classifier import RequestTypeClassifier
import re

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
    """Service for Gemini AI API interactions - with conditional KB injection"""

    def __init__(self, sheets_manager=None):
        """
        Initialize Gemini service
        
        Args:
            sheets_manager: Optional SheetsManager for loading knowledge layers.
                           Required for doctrinal KB injection.
        """
        self.api_key = config.GEMINI_API_KEY
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.MODEL_NAME}:generateContent"

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        if len(self.api_key) < 20:
            logger.warning("⚠️  GEMINI_API_KEY seems too short")

        # Initialize components
        self.prompt_engine = PromptEngine()
        self.knowledge_engine = KnowledgeEngine(sheets_manager)  # Pass sheets_manager
        self.territory_validator = TerritoryValidator()
        self.request_classifier = RequestTypeClassifier()  # NEW: Request type classification

        logger.info(f"✓ Gemini service initialized with model: {config.MODEL_NAME}")

    def _detect_email_language(self, email_content: str, email_subject: str) -> str:
        """
        Detect email language with enhanced detection for English, Spanish, Italian
        
        ✅ CENTRALIZED: This is the ONLY place for language detection
        ✅ IMPROVED: Regex-based word detection to prevent partial matches
        ✅ FIXED: Removed ambiguous keywords like 'a', 'in'
        """
        text = (email_subject + ' ' + email_content).lower()
        original_text = email_subject + ' ' + email_content  # Keep original for special chars

        # ═══════════════════════════════════════════════════════════════
        # Spanish-specific character detection (highly distinctive)
        # ═══════════════════════════════════════════════════════════════
        spanish_char_score = 0
        if '¿' in original_text or '¡' in original_text:
            spanish_char_score = 5  # Strong indicator
            logger.debug("   Found Spanish-specific punctuation (¿ or ¡)")
        
        # ñ is unique to Spanish (not used in Italian or English)
        if 'ñ' in text or 'Ñ' in original_text:
            spanish_char_score += 3  # Good indicator (slightly less than ¿¡ since ñ can appear in names)
            logger.debug("   Found Spanish-specific character (ñ)")
        
        # ═══════════════════════════════════════════════════════════════
        # Enhanced language keywords (more distinctive)
        # ═══════════════════════════════════════════════════════════════
        
        # English keywords - ✅ ENHANCED with weighted scoring
        # High-value keywords (unique to English, score 2 each)
        english_unique_keywords = [
            'the', 'would', 'could', 'should', 'might',
            'we are', 'you are', 'they are', 'i am', "i'm", "we're", "you're",
            'please', 'thank you', 'thanks', 'dear sir', 'dear madam',
            'kind regards', 'best regards', 'sincerely', 'yours truly',
            'looking forward', 'i would like', 'we would like',
            'let me know', 'get back to', 'reach out',
            'in order to', 'as well as', 'such as',
            'however', 'therefore', 'furthermore', 'moreover',
            'regarding', 'concerning', 'attached', 'enclosed',
            'schedule', 'meeting', 'appointment', 'available',
        ]
        
        # Standard English keywords (score 1 each)
        english_standard_keywords = [
            # Articles and conjunctions (REMOVED 'a', 'in')
            ' and ', ' but ', ' an ',
            # Modal verbs and auxiliaries
            'will', 'can', 'may', 'shall', 'must',
            'have', 'has', 'had', 'do', 'does', 'did',
            # Common verbs
            'send', 'get', 'want', 'need', 'make', 'give', 'take',
            'know', 'think', 'see', 'find', 'help', 'work',
            # Question words
            'what', 'when', 'where', 'how', 'why', 'which', 'who',
            # Prepositions (REMOVED 'in')
            ' on ', ' of ', ' to ', ' from ', ' for ', ' with ', ' at ', ' by ',
            # Business/marketing terms
            'website', 'business', 'offer', 'price', 'service', 'services',
            'interested', 'project', 'information', 'plan', 'list',
            'email', 'contact', 'phone', 'address',
            # Common adjectives/adverbs
            'good', 'best', 'first', 'your', 'our', 'this', 'that',
            'because', 'so', 'if', 'are', 'is', 'am',
            # More common English words
            'also', 'just', 'about', 'very', 'much', 'more', 'some', 'any',
            'well', 'only', 'even', 'still', 'already', 'again',
            'here', 'there', 'now', 'then', 'today', 'tomorrow', 'yesterday',
        ]
        
        # Spanish keywords (more distinctive, avoiding overlap with Italian)
        spanish_keywords = [
            # Common verbs and conjugations
            # Removed: 'tengo', 'tiene' (overlap with Italian 'tenere')
            'he ido', 'había', 'hay', 'ido', 'sido', 
            'hacer', 'haber', 'poder', 'estar', 'estoy', 'están',
            # Questions and common words
            'por qué', 'porque', 'cuándo', 'cómo', 'dónde', 'qué tal',
            # Greetings and phrases
            'por favor', 'muchas gracias', 'buenos días', 'buenas tardes',
            'querido', 'estimado', 'saludos',
            # Pronouns and particles
            # Removed: 'sí', 'al', 'son' (Italian overlap)
            ' no ', ' un ', ' unos ', ' unas ',
            ' del ', ' con el ', ' en el ', ' es ',
            # Common Spanish words
            'somos', 'proyecto', 'información', 'quiero', 'quisiera', 'necesito',
            'bueno', 'bien', 'asi', 'luego', 'entonces',
            # High-frequency non-accented words (User request + extras)
            # Removed: 'una', 'de' (Italian overlap)
            # Removed: 'como' (exists in Italian 'Como'), 'tengo'/'tiene' (verb tenere), 'son' (apocope)
            'que', 'cuando', 'quien', 'tambien', 'para', 'por', 
            ' y ', 'sus', 'hola', 'los', 'las', 'el ',
            'informacion', 'favor', 'muy', 'usted', 'ahora', 'aqui', 'gracias'
        ]
        
        # Italian keywords (more distinctive, avoiding overlap with Spanish)
        italian_keywords = [
            # Common verbs and conjugations
            'sono', 'siamo', 'stato', 'stata', 'ho', 'hai', 'abbiamo',
            'fare', 'avere', 'essere', 'potere', 'volere',
            # Questions and common words  
            'perché', 'perchè', 'quando', 'come', 'dove', 'cosa',
            # Greetings and phrases
            'per favore', 'per piacere', 'molte grazie', 'buongiorno',
            'buonasera', 'gentile', 'egregio', 'cordiali saluti',
            # Pronouns and particles (Updated: removed 'con', 'la', 'lo' to avoid Spanish overlap)
            ' non ', ' il ', ' di ', ' da ',
            ' nel ', ' della ', ' degli ', ' delle ',
            # Common Italian words
            'progetto', 'informazione', 'informazioni', 'vorrei', 'gradirei'
        ]

        # ═══════════════════════════════════════════════════════════════
        # Match counting with REGEX WORD BOUNDARIES
        # ═══════════════════════════════════════════════════════════════
        
        def count_matches(keywords, txt, weight=1):
            count = 0
            for kw in keywords:
                # If keyword has explicit spaces, treat as substring match
                if kw.startswith(' ') or kw.endswith(' '):
                    if kw in txt:
                        count += weight * txt.count(kw)
                else:
                    # Use regex boundaries for clean words
                    # Escape keyword to handle potential special chars
                    pattern = r'\b' + re.escape(kw) + r'\b'
                    matches = re.findall(pattern, txt)
                    if matches:
                        count += weight * len(matches)
            return count

        english_score = (
            count_matches(english_unique_keywords, text, 2) +
            count_matches(english_standard_keywords, text, 1)
        )
        
        scores = {
            'en': english_score,
            'es': count_matches(spanish_keywords, text, 1) + spanish_char_score,
            'it': count_matches(italian_keywords, text, 1)
        }

        # Log scoring details
        logger.info(f"   Language scores: EN={scores['en']}, ES={scores['es']}, IT={scores['it']}")
        
        detected_lang = max(scores, key=scores.get)
        max_score = scores[detected_lang]
        
        # ═══════════════════════════════════════════════════════════════
        # Confidence threshold logic
        # ═══════════════════════════════════════════════════════════════
        
        # If Spanish has special characters, prefer Spanish
        if spanish_char_score > 0 and scores['es'] >= scores['it']:
            logger.info(f"   ✓ Detected: SPANISH (score: {scores['es']}, includes special chars)")
            return 'es'
        
        # If English score is meaningful (>= 2), AND English is the highest or tied for highest
        if scores['en'] >= 2 and scores['en'] >= scores['it'] and scores['en'] >= scores['es']:
            logger.info(f"   ✓ Detected: ENGLISH (score: {scores['en']})")
            return 'en'
        
        # If all scores are very low, default to Italian (parish is Italian)
        if max_score < 2:
            logger.debug("   Low confidence across all languages, defaulting to Italian")
            return 'it'

        logger.info(f"   ✓ Detected: {detected_lang.upper()} (score: {max_score})")
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

    def _get_request_type_hint(self, request_type: str, needs_doctrine: bool = False, needs_discernment: bool = False) -> str:
        """
        Generate hint for AI based on classified request type
        
        Args:
            request_type: 'technical', 'pastoral', or 'mixed'
            needs_doctrine: True if doctrinal content was detected
            needs_discernment: True if personal discernment is needed
            
        Returns:
            Hint string to guide response style
        """
        # ═══════════════════════════════════════════════════════════════
        # CF-02: DOCTRINAL MANDATE - When doctrine is needed WITHOUT discernment
        # ═══════════════════════════════════════════════════════════════
        if needs_doctrine and not needs_discernment:
            return """
🎯 TIPO RICHIESTA RILEVATO: DOTTRINALE INFORMATIVA
═══════════════════════════════════════════════════════════════════════════

📖 REGOLA CF-02 - SPIEGAZIONE DOTTRINALE OBBLIGATORIA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Questa richiesta è DOTTRINALE/CANONICA in FORMA GENERALE.
NON coinvolge una situazione personale o discernimento.

✅ IL TUO COMPITO: SPIEGA direttamente l'insegnamento della Chiesa.
❌ NON rimandare al sacerdote per domande informative.

Linee guida per la risposta:
- Rispondi in modo CHIARO, COMPLETO e FEDELE al Magistero
- Fornisci la spiegazione dottrinale richiesta DIRETTAMENTE
- Usa un tono CATECHETICO ma accessibile
- Cita principi, non opinioni personali
- Se hai la Knowledge Base dottrinale, USALA per rispondere

⚠️ ATTENZIONE: Il rinvio al sacerdote in questo caso è IMPROPRIO.
   La persona chiede di essere INFORMATA, non accompagnata.
   
═══════════════════════════════════════════════════════════════════════════
"""
        
        if request_type == 'technical':
            return """
🎯 TIPO RICHIESTA RILEVATO: TECNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Linee guida per la risposta:
- Rispondi in modo CHIARO e BREVE
- Fornisci l'informazione richiesta direttamente
- Non eccedere in empatia o moralizzazione
- Evita lunghe introduzioni emotive
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        elif request_type == 'pastoral':
            return """
🎯 TIPO RICHIESTA RILEVATO: PASTORALE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Linee guida per la risposta:
- Rispondi in modo ACCOGLIENTE e PERSONALE
- Riconosci la situazione/sentimento espresso
- Accompagna la persona, non giudicare
- Non fermarti solo alla norma
- Invita al dialogo personale se opportuno
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:  # mixed
            return """
🎯 TIPO RICHIESTA RILEVATO: MISTA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Linee guida per la risposta:
- Rispondi TECNICAMENTE (chiarezza) ma con TONO pastorale
- Non fermarti alla sola regola
- Non scivolare nel permissivismo
- Bilancia informazione e accoglienza
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    @retry_on_failure(max_retries=3, delay=2, backoff_factor=2)
    def generate_response(
        self,
        email_content: str,
        email_subject: str,
        knowledge_base: str,
        sender_name: str,
        sender_email: str,
        conversation_history: str = "",
        category: Optional[str] = None,
        sub_intents: Optional[Dict] = None,  # ✅ NEW: Emotional nuances
        detected_language: Optional[str] = None,  # ✅ NEW: Language override from quick check
        memory_context: Optional[Dict] = None,  # 🧠 LIGHT MEMORY CONTEXT
        classification_confidence: float = 0.8,  # ✅ CORRECTED: Passed from classifier
        kb_contains_dates: bool = False  # ✅ CORRECTED: Passed from static KB check
    ) -> Optional[str]:
        """
        Generate AI response - CLEANED VERSION
        
        ✅ FIXED: Uses ONLY PromptEngine, no duplication
        ✅ NEW: Passes sub_intents for dynamic template selection
        """
        # Quick check for acknowledgment
        main_reply = self._extract_main_reply(email_content)
        if self._is_only_acknowledgement(main_reply):
            logger.info("Detected acknowledgment, returning NO_REPLY")
            return "NO_REPLY"

        # Detect language (use override if provided, else fallback to internal detection)
        now = datetime.now(ITALIAN_TZ)
        
        # ✅ FIX: Handle None explicitly for conversation_history
        conversation_history = conversation_history or ""
        
        if detected_language:
            logger.info(f"   Language pre-detected by Gemini: {detected_language}")
            final_language = detected_language
        else:
            final_language = self._detect_email_language(email_content, email_subject)
            
        salutation, closing = self._get_adaptive_greeting(now, sender_name, final_language)
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

        # ═══════════════════════════════════════════════════════════════
        # 🧠 DYNAMIC PROMPT FOCUSING (PromptContext)
        # ═══════════════════════════════════════════════════════════════
        # Classify request type first (needed for context)
        request_type_result = self.request_classifier.classify(
            email_subject, email_content
        )
        
        # Determine if reply
        is_reply = email_subject.lower().startswith(('re:', 'r:'))
        
        # NOTE: kb_contains_dates passed as argument to avoid false positives from injected headers
        
        # 🧠 COMPUTE SALUTATION MODE from memory for conversational continuity
        salutation_state = memory_context.get('salutation_state', {}) if memory_context else {}
        salutation_mode = compute_salutation_mode(
            message_count=len(conversation_history.split('---')) if conversation_history else 1,
            is_reply=is_reply,
            first_salutation_used=salutation_state.get('first_salutation_used', False),
            last_interaction_at=salutation_state.get('last_interaction_at'),
            now=now
        )
        logger.info(f"   🧠 Salutation mode: {salutation_mode}")
        
        # ═══════════════════════════════════════════════════════════════
        # 🧠 OVERRIDE SALUTO PER CONTINUITÀ CONVERSAZIONALE
        # Una regola testuale NON può vincere contro un dato strutturale.
        # Se il mode dice "no saluto", DEVI toglierlo fisicamente.
        # ═══════════════════════════════════════════════════════════════
        if salutation_mode == 'none_or_continuity':
            salutation = ""  # ⛔ NESSUN SALUTO - lascia che il template decida la frase di continuità
            logger.info("   🧠 Salutation override: CLEARED (none_or_continuity)")
        elif salutation_mode == 'soft':
            salutation = ""  # ⛔ NESSUN SALUTO RITUALE - Gemini sceglierà frase soft
            logger.info("   🧠 Salutation override: CLEARED (soft mode)")
        
        # Create PromptContext to compute concerns and profile
        prompt_ctx = create_prompt_context(
            detected_language=final_language,
            is_reply=is_reply,
            email_body=email_content,
            email_subject=email_subject,
            category=category,
            confidence=classification_confidence,  # ✅ USES REAL CONFIDENCE
            sub_intents=sub_intents or {},
            request_type=request_type_result.get('type', 'technical'),
            needs_doctrine=request_type_result.get('needs_doctrine', False),
            memory_exists=bool(memory_context),
            provided_info_count=len(memory_context.get('provided_info', [])) if memory_context else 0,
            message_count=len(conversation_history.split('---')) if conversation_history else 1,
            address_found=territory_info.get('address_found', False),
            kb_length=len(knowledge_base),
            kb_contains_dates=kb_contains_dates,  # ✅ USES STATIC CHECK
            salutation_mode=salutation_mode  # 🧠 CONVERSATIONAL CONTINUITY
        )
        
        # Log the prompt focusing decision
        logger.info(f"   🧠 PromptContext: profile={prompt_ctx.profile}, concerns={len(prompt_ctx.meta['active_concerns'])} active")
        if prompt_ctx.profile != 'heavy':
            logger.info(f"      Active concerns: {', '.join(prompt_ctx.meta['active_concerns'][:3])}...")
        
        # ✅ FIXED: Use PromptEngine with dynamic focusing
        prompt = self.prompt_engine.build_prompt(
            email_content=email_content,
            email_subject=email_subject,
            knowledge_base=knowledge_base,
            sender_name=sender_name,
            sender_email=sender_email,
            conversation_history=conversation_history,
            category=category,
            detected_language=final_language,
            current_season=current_season,
            now=now,
            salutation=salutation,
            closing=closing,
            sub_intents=sub_intents or {},
            memory_context=memory_context,
            prompt_profile=prompt_ctx.profile,  # 🎯 DYNAMIC PROFILE
            active_concerns=prompt_ctx.concerns,  # 🎯 ACTIVE CONCERNS
            salutation_mode=salutation_mode  # 🧠 CONVERSATION CONTINUITY
        )
        # ═══════════════════════════════════════════════════════════════
        # CONDITIONAL KB INJECTION (Based on Request Type Classification)
        # ═══════════════════════════════════════════════════════════════
        # Note: request_type_result already computed above for PromptContext
        
        guidelines = []
        
        # Level 0 – AI-Core Lite: ALWAYS injected (tone, limits, response type)
        lite = self.knowledge_engine.get_tone_guidelines()
        if lite:
            # Add request type hint to guide response style (CF-02 aware)
            type_hint = self._get_request_type_hint(
                request_type_result['type'],
                needs_doctrine=request_type_result.get('needs_doctrine', False),
                needs_discernment=request_type_result.get('needs_discernment', False)
            )
            guidelines.append(type_hint)
            guidelines.append(lite)
            logger.info(f"   📋 AI-Core Lite injected ({len(lite)} chars)")
        
        # Level 1 – AI-Core: only when discernment needed
        if request_type_result['needs_discernment']:
            core = self.knowledge_engine.get_pastoral_guidelines()
            if core:
                guidelines.append(core)
                logger.info(f"   📋 AI-Core (discernment) injected ({len(core)} chars)")
        
        # Level 2 – Dottrina: only for explicit doctrinal requests
        if request_type_result['needs_doctrine']:
            doctrine = self.knowledge_engine.get_doctrinal_content()
            if doctrine:
                guidelines.append(doctrine)
                logger.info(f"   📋 Dottrina injected ({len(doctrine)} chars)")
        
        # Inject as internal prefix (never shown to user)
        if guidelines:
            internal_section = "\n---\n" + "\n\n".join(guidelines) + "\n---\n"
            prompt = internal_section + prompt

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
            
            # ✅ FIX #7: Handle 429 (rate limit) and 503 (service unavailable) with retry
            elif response.status_code in (429, 503):
                error_msg = f"API returned {response.status_code}: {response.text[:200]}"
                logger.warning(f"⚠️ Transient Gemini API error: {error_msg}")
                # Raise to trigger retry decorator
                raise requests.exceptions.RequestException(error_msg)
            
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
    def should_respond_to_email(self, email_content: str, email_subject: str) -> Dict[str, Any]:
        """
        Lightweight Gemini call to decide if email needs response AND detect language
        
        Uses minimal tokens to decide YES/NO based on email content
        AND return the language code.
        
        Args:
            email_content: Email body text
            email_subject: Email subject
            
        Returns:
            Dict with:
            - 'should_respond': bool
            - 'language': str (code 'it', 'en', 'es', etc.)
            - 'reason': str
        """
        # Build lightweight prompt requesting JSON
        prompt = f"""Analizza questa email.
Rispondi ESCLUSIVAMENTE con un oggetto JSON.

Email:
Oggetto: {email_subject}
Testo: {email_content[:800]}

Compiti:
1. Decidi se richiede risposta (reply_needed: true/false)
2. Rileva la lingua (language: codice iso 2 lettere es. 'it', 'en', 'es', 'fr')
3. Motivo sintetico (reason)

Criteri per reply_needed:
- FALSE se è solo ringraziamento/conferma ricevuta/saluto generico
- FALSE se è solo acknowledgment ("ok", "perfetto", "grazie")
- TRUE se contiene domande, richieste, dubbi, richiesta conferma azione

Output JSON atteso:
{{
  "reply_needed": boolean,
  "language": "string",
  "reason": "string"
}}
"""

        try:
            logger.info(f"🔍 Gemini quick check + Lang detect for: {email_subject[:40]}...")
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0,  # Deterministic decision
                        "maxOutputTokens": 100,
                        "responseMimeType": "application/json"  # Force JSON
                    }
                },
                headers={"Content-Type": "application/json"},
                timeout=config.GEMINI_QUICK_CHECK_TIMEOUT
            )
            
            # Default failsafe result
            default_result = {'should_respond': True, 'language': 'it', 'reason': 'failsafe'}

            if response.status_code == 200:
                result = response.json()
                
                if not result.get("candidates"):
                    logger.warning("⚠️  Quick check: No candidates, defaulting to YES/IT")
                    return default_result
                
                # Parse JSON response
                try:
                    text_response = result["candidates"][0]["content"]["parts"][0]["text"]
                    data = json.loads(text_response)
                    
                    # 🔧 FIX: Handle case where Gemini returns a list [ {...} ]
                    if isinstance(data, list):
                        if len(data) > 0:
                            data = data[0]
                        else:
                            data = {}
                    
                    # ✅ FIX: Robust boolean validation for reply_needed
                    # Gemini may return "true" (string) instead of true (boolean)
                    raw_decision = data.get('reply_needed', True)
                    if isinstance(raw_decision, bool):
                        decision = raw_decision
                    elif isinstance(raw_decision, str):
                        decision = raw_decision.lower() == 'true'
                    else:
                        decision = True  # Failsafe: respond when uncertain
                    
                    language = data.get('language', 'it').lower()
                    reason = data.get('reason', 'no reason provided')
                    
                    # Normalize common language codes if needed
                    if language not in config.SUPPORTED_LANGUAGES:
                        logger.warning(f"   ⚠️ Possible invalid language code '{language}', defaulting to 'it'")
                        language = 'it'
                    
                    logger.info(f"   Quick check: Reply={decision}, Lang={language} ({reason})")
                    
                    return {
                        'should_respond': decision,
                        'language': language,
                        'reason': reason
                    }
                    
                except json.JSONDecodeError:
                    logger.error(f"❌ JSON decode error in quick check: {text_response}")
                    return default_result
                
            else:
                logger.warning(f"⚠️  Quick check API error: {response.status_code}, defaulting to YES/IT")
                return default_result
                
        except requests.exceptions.Timeout:
            logger.warning("⏱️  Quick check timeout, defaulting to YES/IT")
            return {'should_respond': True, 'language': 'it', 'reason': 'timeout'}
            
        except Exception as e:
            logger.warning(f"⚠️  Quick check failed: {e}, defaulting to YES/IT")
            return {'should_respond': True, 'language': 'it', 'reason': f'error: {str(e)}'}

        