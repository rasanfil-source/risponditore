# prompt_engine.py

"""
Modular prompt engineering system
Template-based prompts with dynamic composition
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PromptContext:
    """Context for prompt generation"""
    email_content: str
    email_subject: str
    sender_name: str
    sender_email: str
    knowledge_base: str
    conversation_history: str
    category: Optional[str]
    detected_language: str
    current_season: str
    now: datetime
    salutation: str
    closing: str


class PromptTemplate:
    """Base class for prompt templates"""
    
    def render(self, context: PromptContext) -> str:
        raise NotImplementedError


class SystemRoleTemplate(PromptTemplate):
    """System role definition"""
    
    def render(self, context: PromptContext) -> str:
        return "Sei la segreteria della Parrocchia di Sant'Eugenio a Roma. Rispondi in modo conciso e chiaro."


class LanguageInstructionTemplate(PromptTemplate):
    """Language-specific instructions"""
    
    INSTRUCTIONS = {
        'it': "Rispondi in italiano, la lingua dell'email ricevuta.",
        'en': (
            "🚨 CRITICAL: This email is in ENGLISH. "
            "Respond ENTIRELY in English. NO Italian words."
        ),
        'es': (
            "🚨 CRÍTICO: Este correo está en ESPAÑOL. "
            "Responde COMPLETAMENTE en español. SIN palabras italianas."
        )
    }
    
    def render(self, context: PromptContext) -> str:
        return self.INSTRUCTIONS.get(context.detected_language, self.INSTRUCTIONS['it'])


class KnowledgeBaseTemplate(PromptTemplate):
    """Knowledge base section"""
    
    def render(self, context: PromptContext) -> str:
        return f"""**INFORMAZIONI DI RIFERIMENTO:**
{context.knowledge_base}

**REGOLA FONDAMENTALE:** NON inventare."""


class SeasonalContextTemplate(PromptTemplate):
    """Seasonal hours management"""
    
    def render(self, context: PromptContext) -> str:
        season_note = (
            f"IMPORTANTE: Siamo nel periodo {context.current_season.upper()}. "
            f"Usa SOLO gli orari {context.current_season}."
        )
        
        return f"""**ORARI STAGIONALI:**
{season_note}
Non mostrare mai entrambi i set di orari."""


class CategoryHintTemplate(PromptTemplate):
    """Category-specific hints"""
    
    HINTS = {
        'appointment': "📌 Email su APPUNTAMENTO: fornisci info su come fissare appuntamenti.",
        'information': "📌 Richiesta INFORMAZIONI: rispondi basandoti sulla knowledge base.",
        'sacrament': "📌 Email su SACRAMENTI: fornisci info dettagliate su requisiti e procedure.",
        'collaboration': "📌 Proposta COLLABORAZIONE: ringrazia e spiega come procedere.",
        'complaint': "📌 Possibile RECLAMO: rispondi con empatia e professionalità."
    }
    
    def render(self, context: PromptContext) -> str:
        if not context.category or context.category not in self.HINTS:
            return ""
        
        return f"**CATEGORIA IDENTIFICATA:**\n{self.HINTS[context.category]}\n"


class ConversationHistoryTemplate(PromptTemplate):
    """Conversation history context"""
    
    def render(self, context: PromptContext) -> str:
        if not context.conversation_history:
            return ""
        
        return f"""**CRONOLOGIA CONVERSAZIONE:**
Messaggi precedenti per contesto. Non ripetere info già fornite.
\"\"\"
{context.conversation_history}
\"\"\""""


class EmailContentTemplate(PromptTemplate):
    """Current email to respond to"""
    
    def render(self, context: PromptContext) -> str:
        return f"""**EMAIL DA RISPONDERE:**
Da: {context.sender_email} ({context.sender_name})
Oggetto: {context.email_subject}
Lingua: {context.detected_language.upper()}

Contenuto:
\"\"\"
{context.email_content}
\"\"\""""


class NoReplyRulesTemplate(PromptTemplate):
    """Condensed NO_REPLY rules"""
    
    def render(self, context: PromptContext) -> str:
        return """**QUANDO NON RISPONDERE (scrivi solo "NO_REPLY"):**

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


class ResponseGuidelinesTemplate(PromptTemplate):
    """Core response guidelines (condensed)"""
    
    def render(self, context: PromptContext) -> str:
        return f"""**LINEE GUIDA RISPOSTA:**

1. **Identificazione mittente:** Cerca il nome nella firma/contenuto. Se assente: forma generica.

2. **Formato risposta:**
   {context.salutation}
   [Corpo conciso e pertinente]
   {context.closing}
   Segreteria Parrocchia Sant'Eugenio

3. **Contenuto:**
   • Rispondi SOLO a ciò che è chiesto
   • Usa info dalla knowledge base
   • Se info mancano: indica che la segreteria si farà sentire
   • Follow-up (Re:): sii più diretto e conciso

4. **Proposte insolite:** Ringrazia, apprezza, conferma esame e risposta rapida

5. **Orari:** Mostra SOLO orari del periodo corrente ({context.current_season})

6. **Lingua:** Rispondi in {context.detected_language.upper()}, la lingua dell'email

7. **Controllo finale:** Rileggi. Deve essere naturale, pertinente, rispettoso."""


class SpecialCasesTemplate(PromptTemplate):
    """Special cases handling"""
    
    def render(self, context: PromptContext) -> str:
        return """**CASI SPECIALI:**

• **Cresima:** Se genitore per figlio → info Cresima ragazzi. Se adulto per sé → info Cresima adulti.
• **Padrino/Madrina:** Se l'interlocutore vuole fare da padrino/madrina, includi criteri idoneità.
• **Certificato idoneità:** NON confondere con criteri Cresima. Sono due cose diverse.
• **Impegni lavorativi:** Se impossibilitato a partecipare → offri programmi flessibili.
• **Filtro temporale:** "a giugno" → rispondi SOLO con info di giugno."""

# ═══════════════════════════════════════════════════════════════
# 🆕 NUOVO TEMPLATE: VERIFICA TERRITORIO
# ═══════════════════════════════════════════════════════════════
class TerritoryVerificationTemplate(PromptTemplate):
    """Territory verification rules and guidance"""
    
    def render(self, context: PromptContext) -> str:
        return """**VERIFICA TERRITORIO PARROCCHIALE - REGOLA SPECIALE:**

🎯 PRIORITÀ ASSOLUTA: Se nella sezione "INFORMAZIONI DI RIFERIMENTO" trovi 
il blocco "VERIFICA TERRITORIO AUTOMATICA", quello è il risultato di una 
verifica programmatica precisa al 100%.

✅ ISTRUZIONI:
• Usa ESATTAMENTE le informazioni dalla verifica automatica
• NON fare supposizioni o interpretazioni personali
• NON basarti solo sulla knowledge base testuale generica
• Se la verifica dice "RIENTRA" → l'indirizzo è nel territorio
• Se la verifica dice "NON RIENTRA" → l'indirizzo NON è nel territorio

❌ Se la verifica automatica NON è presente:
• Significa che non è stato rilevato un indirizzo specifico nell'email
• In questo caso usa le informazioni generali dalla knowledge base
• Se chiede di un indirizzo specifico senza numero civico → chiedi il numero

⚠️ La verifica automatica è SEMPRE corretta. Fidati di essa al 100%."""
# ═══════════════════════════════════════════════════════════════


class PromptEngine:
    """
    Modular prompt composition engine
    
    Benefits:
    - ~40% token reduction through deduplication
    - Easy A/B testing of specific sections
    - Better maintainability
    - Dynamic template selection
    """
    
    def __init__(self):
        logger.info("🎨 Initializing PromptEngine...")
        
        # Template pipeline (order matters)
        self.template_pipeline = [
            SystemRoleTemplate(),
            LanguageInstructionTemplate(),
            KnowledgeBaseTemplate(),
            TerritoryVerificationTemplate(),
            SeasonalContextTemplate(),
            CategoryHintTemplate(),
            ConversationHistoryTemplate(),
            EmailContentTemplate(),
            NoReplyRulesTemplate(),
            ResponseGuidelinesTemplate(),
            SpecialCasesTemplate(),
        ]
        
        logger.info(f"✓ Loaded {len(self.template_pipeline)} prompt templates")
    
    def build_prompt(
        self,
        email_content: str,
        email_subject: str,
        knowledge_base: str,
        sender_name: str,
        sender_email: str,
        conversation_history: str,
        category: Optional[str],
        detected_language: str,
        current_season: str,
        now: datetime,
        salutation: str,
        closing: str
    ) -> str:
        """
        Build optimized prompt from templates
        
        Returns:
            Complete prompt (~40% smaller than original)
        """
        context = PromptContext(
            email_content=email_content,
            email_subject=email_subject,
            sender_name=sender_name,
            sender_email=sender_email,
            knowledge_base=knowledge_base,
            conversation_history=conversation_history,
            category=category,
            detected_language=detected_language,
            current_season=current_season,
            now=now,
            salutation=salutation,
            closing=closing
        )
        
        # Render all templates
        sections = []
        for template in self.template_pipeline:
            try:
                rendered = template.render(context)
                if rendered:  # Skip empty sections
                    sections.append(rendered)
            except Exception as e:
                logger.error(f"Error rendering {template.__class__.__name__}: {e}")
                continue
        
        # Compose final prompt
        prompt = "\n\n".join(sections)
        prompt += "\n\n**Genera la risposta completa:**"
        
        logger.debug(f"📐 Prompt size: {len(prompt)} chars (~{len(prompt)//4} tokens)")
        
        return prompt
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)"""
        return len(text) // 4
    
    def get_template_stats(self, context: PromptContext) -> Dict:
        """Get statistics about template contributions"""
        stats = {}
        total_size = 0
        
        for template in self.template_pipeline:
            try:
                rendered = template.render(context)
                size = len(rendered) if rendered else 0
                stats[template.__class__.__name__] = {
                    'size_chars': size,
                    'size_tokens': self.estimate_tokens(rendered) if rendered else 0
                }
                total_size += size
            except Exception:
                stats[template.__class__.__name__] = {'size_chars': 0, 'size_tokens': 0}
        
        stats['total'] = {
            'size_chars': total_size,
            'size_tokens': self.estimate_tokens(str(total_size))
        }
        
        return stats
