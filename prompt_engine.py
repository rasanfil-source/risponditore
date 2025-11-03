"""
Prompt Engine - Modular prompt building system
Reduces token usage by ~40% through dynamic template composition
"""

from typing import Dict, List, Optional, Protocol
from datetime import datetime
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# TEMPLATE PROTOCOL
# ============================================================================

class PromptTemplate(Protocol):
    """Protocol for all prompt templates"""
    
    def render(self, context: Dict) -> str:
        """Render template with given context"""
        ...
    
    def get_name(self) -> str:
        """Get template name for debugging"""
        ...


# ============================================================================
# CONTEXT DATA CLASS
# ============================================================================

@dataclass
class PromptContext:
    """Context data for prompt rendering"""
    # Email data
    email_content: str
    email_subject: str
    sender_email: str
    sender_name: str
    
    # Knowledge & conversation
    knowledge_base: str
    conversation_history: Optional[str] = None
    
    # Detection results
    detected_language: str = 'it'
    category: Optional[str] = None
    
    # Temporal context
    current_datetime: Optional[datetime] = None
    current_season: Optional[str] = None
    
    # Greetings (pre-computed)
    salutation: Optional[str] = None
    closing_phrase: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for template rendering"""
        return {
            'email_content': self.email_content,
            'email_subject': self.email_subject,
            'sender_email': self.sender_email,
            'sender_name': self.sender_name,
            'knowledge_base': self.knowledge_base,
            'conversation_history': self.conversation_history or '',
            'detected_language': self.detected_language,
            'category': self.category or '',
            'current_season': self.current_season or 'invernale',
            'salutation': self.salutation or f'Gentile {self.sender_name},',
            'closing_phrase': self.closing_phrase or 'Cordiali saluti,'
        }


# ============================================================================
# CORE TEMPLATES
# ============================================================================

class SystemRoleTemplate:
    """System role and base instructions"""
    
    def get_name(self) -> str:
        return "SystemRole"
    
    def render(self, context: Dict) -> str:
        return """Sei la segreteria della Parrocchia di Sant'Eugenio a Roma.
Rispondi alle email in modo conciso, chiaro e solo con le informazioni esplicitamente richieste."""


class LanguageInstructionTemplate:
    """Language-specific instructions (dynamic based on detected language)"""
    
    def get_name(self) -> str:
        return "LanguageInstruction"
    
    def render(self, context: Dict) -> str:
        lang = context.get('detected_language', 'it')
        
        if lang == 'en':
            return """
════════════════════════════════════════════════════════════
CRITICAL PRIORITY INSTRUCTION
════════════════════════════════════════════════════════════
This email is written in ENGLISH.
You MUST respond ENTIRELY and EXCLUSIVELY in English.
Do NOT use ANY Italian words or phrases.
Translate ALL parish information to English.
This rule has ABSOLUTE PRIORITY over all other instructions.
════════════════════════════════════════════════════════════"""
        
        elif lang == 'es':
            return """
════════════════════════════════════════════════════════════
INSTRUCCIÓN CRÍTICA DE MÁXIMA PRIORIDAD
════════════════════════════════════════════════════════════
Este correo está escrito en ESPAÑOL.
Debes responder COMPLETA y EXCLUSIVAMENTE en español.
NO uses NINGUNA palabra o frase en italiano.
Traduce TODA la información parroquial al español.
Esta regla tiene PRIORIDAD ABSOLUTA sobre todas las demás instrucciones.
════════════════════════════════════════════════════════════"""
        
        else:  # Italian (default)
            return """Rispondi SEMPRE nella stessa lingua in cui è scritta l'email ricevuta.
Se l'email è in inglese, rispondi in inglese. Se è in spagnolo, rispondi in spagnolo.
Non tradurre e non mischiare lingue."""


class KnowledgeBaseTemplate:
    """Knowledge base injection"""
    
    def get_name(self) -> str:
        return "KnowledgeBase"
    
    def render(self, context: Dict) -> str:
        kb = context.get('knowledge_base', '')
        if not kb:
            return ""
        
        return f"""
═══════════════════════════════════════════════════════════════
INFORMAZIONI DI RIFERIMENTO DELLA PARROCCHIA
═══════════════════════════════════════════════════════════════
{kb}

REGOLA CRITICA - SOLO INFORMAZIONI VERIFICATE:
Usa ESCLUSIVAMENTE le informazioni presenti sopra. NON inventare orari, email, numeri di telefono o altre informazioni."""


class SeasonalContextTemplate:
    """Seasonal hours context"""
    
    def get_name(self) -> str:
        return "SeasonalContext"
    
    def render(self, context: Dict) -> str:
        season = context.get('current_season', 'invernale')
        
        if season == 'estivo':
            note = """⚠️ IMPORTANTE: Siamo attualmente nel periodo ESTIVO.
Utilizza SOLO gli orari estivi nelle risposte.
Non mostrare contemporaneamente sia gli orari estivi che quelli invernali.
Mostra SOLO quelli del periodo corrente."""
        else:
            note = """⚠️ IMPORTANTE: Siamo attualmente nel periodo INVERNALE.
Utilizza SOLO gli orari invernali nelle risposte.
Non mostrare contemporaneamente sia gli orari estivi che quelli invernali.
Mostra SOLO quelli del periodo corrente."""
        
        return f"""
═══════════════════════════════════════════════════════════════
GESTIONE ORARI STAGIONALI
═══════════════════════════════════════════════════════════════
{note}"""


class CategoryHintTemplate:
    """Category-specific hints (only if category detected)"""
    
    def get_name(self) -> str:
        return "CategoryHint"
    
    def render(self, context: Dict) -> str:
        category = context.get('category')
        if not category:
            return ""
        
        hints = {
            'appointment': """📅 NOTA: Questa email riguarda la richiesta di un appuntamento.
Fornisci informazioni su come fissare appuntamenti e gli orari disponibili.""",
            
            'information': """ℹ️ NOTA: Questa email richiede informazioni generali.
Rispondi in modo chiaro e completo basandoti sulla knowledge base.""",
            
            'sacrament': """✝️ NOTA: Questa email riguarda i sacramenti.
Fornisci informazioni dettagliate sui requisiti e le procedure.""",
            
            'collaboration': """🤝 NOTA: Questa email propone collaborazione o volontariato.
Ringrazia e spiega come procedere.""",
            
            'complaint': """⚠️ NOTA: Questa email potrebbe contenere un reclamo.
Rispondi con empatia e professionalità."""
        }
        
        hint = hints.get(category, "")
        if not hint:
            return ""
        
        return f"""
═══════════════════════════════════════════════════════════════
CATEGORIA EMAIL IDENTIFICATA
═══════════════════════════════════════════════════════════════
{hint}"""


class ConversationHistoryTemplate:
    """Conversation history (only if present)"""
    
    def get_name(self) -> str:
        return "ConversationHistory"
    
    def render(self, context: Dict) -> str:
        history = context.get('conversation_history', '').strip()
        if not history:
            return ""
        
        return f"""
═══════════════════════════════════════════════════════════════
CRONOLOGIA DELLA CONVERSAZIONE (CONTESTO)
═══════════════════════════════════════════════════════════════
Di seguito i messaggi precedenti. Analizzali per capire il contesto ed evitare di ripetere informazioni già date.

{history}
"""


class CurrentEmailTemplate:
    """Current email to respond to"""
    
    def get_name(self) -> str:
        return "CurrentEmail"
    
    def render(self, context: Dict) -> str:
        return f"""
═══════════════════════════════════════════════════════════════
ULTIMA EMAIL RICEVUTA A CUI RISPONDERE
═══════════════════════════════════════════════════════════════
Da: {context.get('sender_email')} (Nome di fallback: {context.get('sender_name')})
Oggetto: {context.get('email_subject')}
Lingua rilevata: {context.get('detected_language', 'it').upper()}

Contenuto:
───────────────────────────────────────────────────────────────
{context.get('email_content')}
───────────────────────────────────────────────────────────────"""


class NoReplyRulesTemplate:
    """Condensed NO_REPLY rules (reduced from 2400 to 800 chars)"""
    
    def get_name(self) -> str:
        return "NoReplyRules"
    
    def render(self, context: Dict) -> str:
        return """
═══════════════════════════════════════════════════════════════
REGOLA CRITICA - NO_REPLY (APPLICA CON RIGORE)
═══════════════════════════════════════════════════════════════
Rispondi ESATTAMENTE con solo "NO_REPLY" (senza altro testo) se l'email è:

1. Newsletter, pubblicità, email automatiche (Amazon, PayPal, tracking)
2. Bollette, fatture, ricevute, notifiche bancarie
3. Condoglianze, necrologi
4. Email con "no-reply" o "non rispondere"
5. Comunicazioni politiche, "Unsubscribe"

6. **Follow-up di SOLO ringraziamento** (tutte queste condizioni):
   ✓ Oggetto inizia con "Re:" (è una risposta)
   ✓ Contiene SOLO: ringraziamenti, conferme ("ricevuto", "ok", "perfetto")
   ✓ NON contiene: domande, nuove richieste, richieste di conferma
   
   Esempi NO_REPLY:
   • Re: Orari → "Grazie mille! Ricevuto."
   • Re: Info → "Perfetto, grazie!"
   
   Esempi RISPONDI:
   • Re: Orari → "Grazie! Ma domenica gli orari cambiano?"
   • Primo messaggio → "Grazie" (NON è Re:, quindi rispondi)

⚠️ "NO_REPLY" significa che NON invierò risposta. Scrivi SOLO "NO_REPLY", nient'altro."""


class ResponseGuidelinesTemplate:
    """Response formatting guidelines (condensed)"""
    
    def get_name(self) -> str:
        return "ResponseGuidelines"
    
    def render(self, context: Dict) -> str:
        salutation = context.get('salutation', 'Gentile utente,')
        closing = context.get('closing_phrase', 'Cordiali saluti,')
        lang = context.get('detected_language', 'it').upper()
        
        return f"""
═══════════════════════════════════════════════════════════════
LINEE GUIDA PER LA RISPOSTA
═══════════════════════════════════════════════════════════════
1. Identificazione mittente: Cerca il nome nel contenuto/firma. Se non trovi, usa forma generica.

2. Formato risposta:
   • Inizia esattamente con: {salutation}
   • Corpo: Risposta concisa basata SOLO su informazioni verificate
   • Chiudi con: {closing}
                 Segreteria Parrocchia Sant'Eugenio

3. Lingua: Rispondi INTERAMENTE in {lang}. NON mescolare lingue.

4. Informazioni mancanti: Se non hai le info, indicalo gentilmente e spiega che la segreteria prenderà in carico.

5. Follow-up (oggetto con "Re:"): Sii più diretto e conciso.

CONTROLLO FINALE: Rileggi e verifica che sia interamente in {lang}."""


# ============================================================================
# PROMPT ENGINE CLASS
# ============================================================================

class PromptEngine:
    """
    Main prompt engine that orchestrates template rendering
    
    Usage:
        engine = PromptEngine()
        prompt = engine.build_prompt(context)
    """
    
    def __init__(self):
        """Initialize engine with template pipeline"""
        logger.info("Initializing PromptEngine...")
        
        # Template pipeline (order matters!)
        self.templates: List[PromptTemplate] = [
            SystemRoleTemplate(),
            LanguageInstructionTemplate(),
            KnowledgeBaseTemplate(),
            SeasonalContextTemplate(),
            CategoryHintTemplate(),
            ConversationHistoryTemplate(),
            CurrentEmailTemplate(),
            NoReplyRulesTemplate(),
            ResponseGuidelinesTemplate()
        ]
        
        logger.info(f"✓ PromptEngine initialized with {len(self.templates)} templates")
    
    def build_prompt(self, context: PromptContext) -> str:
        """
        Build complete prompt from context
        
        Args:
            context: PromptContext with all necessary data
            
        Returns:
            Complete rendered prompt string
        """
        logger.debug("Building prompt from context...")
        
        # Convert context to dict
        context_dict = context.to_dict()
        
        # Render all templates
        sections = []
        for template in self.templates:
            try:
                rendered = template.render(context_dict)
                if rendered and rendered.strip():
                    sections.append(rendered.strip())
                    logger.debug(f"   ✓ Rendered {template.get_name()}: {len(rendered)} chars")
            except Exception as e:
                logger.error(f"   ✗ Error rendering {template.get_name()}: {e}")
                # Continue with other templates
        
        # Join sections
        prompt = "\n\n".join(sections)
        
        logger.info(f"✓ Prompt built: {len(prompt)} chars, {len(sections)} sections")
        
        return prompt
    
    def get_template_stats(self, context: PromptContext) -> Dict[str, int]:
        """
        Get statistics about rendered template sizes
        
        Args:
            context: PromptContext with all necessary data
            
        Returns:
            Dict mapping template name to character count
        """
        context_dict = context.to_dict()
        stats = {}
        
        for template in self.templates:
            try:
                rendered = template.render(context_dict)
                stats[template.get_name()] = len(rendered) if rendered else 0
            except Exception as e:
                stats[template.get_name()] = -1  # Error indicator
        
        return stats
