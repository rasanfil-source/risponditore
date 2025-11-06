# prompt_engine.py - VERSIONE 2.0 MIGLIORATA

"""
Modular prompt engineering system - ENHANCED VERSION
Template-based prompts with conversational intelligence

WHAT'S NEW in v2.0:
✨ ConversationalGuidelinesTemplate - teaches human-like responses
✨ KnowledgeBaseExtractionTemplate - smart KB info extraction
✨ Enhanced ResponseGuidelinesTemplate - prioritizes completeness
✨ Multi-question handling strategy
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


# ═══════════════════════════════════════════════════════════════════════════
# EXISTING TEMPLATES (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

class SystemRoleTemplate(PromptTemplate):
    """System role definition"""
    
    def render(self, context: PromptContext) -> str:
        return "Sei la segreteria della Parrocchia di Sant'Eugenio a Roma. Rispondi in modo cordiale, completo e conversazionale."


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


# ═══════════════════════════════════════════════════════════════════════════
# ✨ NEW TEMPLATE 1: Knowledge Base Extraction Strategy
# ═══════════════════════════════════════════════════════════════════════════

class KnowledgeBaseExtractionTemplate(PromptTemplate):
    """Strategia di estrazione intelligente dalla KB"""
    
    def render(self, context: PromptContext) -> str:
        return """**STRATEGIA DI ESTRAZIONE DALLA KNOWLEDGE BASE:**

🔍 **Come leggere la KB in modo intelligente:**

1. **CERCA PATTERN CORRELATI:**
   Se l'email chiede di "Santiago", cerca nella KB:
   • "Santiago" (ovviamente)
   • "Cammino"
   • "pellegrinaggio"
   • "Portogallo" (potrebbe essere nel percorso)
   • Mesi/date menzionati nell'email (es. "giugno", "luglio")

2. **ESTRAI DETTAGLI NASCOSTI:**
   Nella KB potresti trovare:
   ```
   Categoria: Pellegrinaggi
   Dettagli: Dal 27/06 al 04/07/2026. Via portoghese da Tui. 
             Partenza con volo per Porto, transfer a Tui. 
             Ritorno da Santiago. Costi: ostello ~500€, camere private ~700€.
   ```
   
   Da questo DEVI ricavare TUTTI i dettagli:
   • Date esatte: 27/06-04/07/2026
   • Percorso: via portoghese, Tui → Santiago
   • Logistica: volo Porto, transfer, ritorno Santiago
   • Costi dettagliati: base + extra

3. **COMBINA INFORMAZIONI:**
   Se l'email chiede "costo totale", NON dire solo "vedi link".
   Fai il calcolo approssimativo dalla KB:
   • Base ostello: 500€
   • Transfer: 80€
   • Volo: 200€
   • TOTALE stimato: ~780€
   
   Poi aggiungi: "Per dettagli aggiornati: [link]"

4. **GESTIONE INFO PARZIALI:**
   Se nella KB manca qualcosa (es. "si può fare in bici?"):
   • NON inventare
   • NON ignorare la domanda
   • Rispondi con logica: "Il gruppo va a piedi. Il percorso è 
     tecnicamente percorribile in bici, ma serve organizzazione diversa."

💡 **REGOLA D'ORO:**
Ogni dettaglio nella KB è lì per essere USATO nelle risposte, 
non solo per "rimandare al link"."""


class KnowledgeBaseTemplate(PromptTemplate):
    """Knowledge base section"""
    
    def render(self, context: PromptContext) -> str:
        return f"""**INFORMAZIONI DI RIFERIMENTO:**
{context.knowledge_base}

**REGOLA FONDAMENTALE:** Usa le info qui presenti in modo ATTIVO. NON inventare."""


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

1. Newsletter, pubblicità, email automatiche
2. Bollette, fatture, ricevute
3. Condoglianze, necrologi
4. Email con "no-reply"
5. Comunicazioni politiche

6. **Follow-up di SOLO ringraziamento** (tutte queste condizioni):
   ✓ Oggetto inizia con "Re:"
   ✓ Contiene SOLO: ringraziamenti, conferme
   ✓ NON contiene: domande, nuove richieste

⚠️ "NO_REPLY" significa che NON invierò risposta. Scrivi SOLO "NO_REPLY"."""


# ═══════════════════════════════════════════════════════════════════════════
# ✨ NEW TEMPLATE 2: Conversational Guidelines (CORE IMPROVEMENT)
# ═══════════════════════════════════════════════════════════════════════════

class ConversationalGuidelinesTemplate(PromptTemplate):
    """Linee guida per risposte conversazionali e complete"""
    
    def render(self, context: PromptContext) -> str:
        return """**LINEE GUIDA CONVERSAZIONALI (PRIORITÀ ALTA):**

🎯 **Filosofia di risposta:**
• NON essere un FAQ robot che risponde solo con link
• Sii un segretario umano, cordiale, che DIALOGA con le persone
• Rispondi a TUTTE le sotto-domande dell'email

📋 **Checklist per ogni risposta:**
1. ✅ Ho risposto a OGNI domanda nell'email?
2. ✅ Ho fornito CONTESTO oltre ai dati nudi?
3. ✅ Ho indicato COSTI TOTALI realistici (non solo "vedi link")?
4. ✅ Ho offerto ALTERNATIVE se necessario?
5. ✅ Ho chiuso con DOMANDA/CALL-TO-ACTION?

💡 **Esempio di approccio conversazionale:**

DOMANDA: "Quanto costa Santiago e si può fare in bici?"

❌ SBAGLIATO (troppo secco):
"Il costo è qui: [link]. Si fa a piedi."

✅ CORRETTO (conversazionale):
"Buonasera, [Nome]!
Il nostro gruppo parte il 27/06 da Tui (via portoghese).
Costi: ostello ~500€ + pasti + transfer (~80€) + volo (~200€) = ~780€ totali.
Il gruppo va a piedi. Il percorso è tecnicamente percorribile in bici,
ma serve organizzazione dedicata.
Ti interessa unirti al gruppo a piedi o cerchi un'opzione in bici?
Dettagli completi: [link]"

🔑 **Differenze chiave:**
• Nome usato
• Dettagli specificati (non solo link)
• Costi totali stimati
• Risposta completa alla domanda bici
• Domanda finale

📝 **GESTIONE DOMANDE MULTIPLE:**

Processo:
1. Identifica OGNI domanda (esplicita o implicita)
2. Per OGNI domanda: verifica info in KB
3. Rispondi a TUTTE con dettagli
4. Se manca info: dillo e offri follow-up

ESEMPIO:
Email: "Costo Santiago dal 29/06? Da dove si parte? Bici?"

Domande identificate:
• Q1: Costo
• Q2: Date (29/06 vs date gruppo)
• Q3: Partenza
• Q4: Bici

Risposta strutturata:
[Saluto]
Q1-Q2: "Il gruppo parte il 27/06 (date vicine). Costi totali ~780€..."
Q3: "Partenza da Tui dopo volo Porto..."
Q4: "Gruppo a piedi, bici possibile ma logistica diversa..."
[Domanda per chiarire preferenze]"""


# ═══════════════════════════════════════════════════════════════════════════
# ✨ UPDATED TEMPLATE: Response Guidelines (Enhanced)
# ═══════════════════════════════════════════════════════════════════════════

class ResponseGuidelinesTemplate(PromptTemplate):
    """Core response guidelines (enhanced - prioritizes completeness)"""
    
    def render(self, context: PromptContext) -> str:
        return f"""**LINEE GUIDA RISPOSTA (AGGIORNATE):**

1. **Identificazione mittente:** 
   Usa SEMPRE il nome nel saluto se disponibile.

2. **Formato risposta:**
   {context.salutation}
   [Corpo COMPLETO e CONVERSAZIONALE]
   {context.closing}
   Segreteria Parrocchia Sant'Eugenio

3. **Contenuto (PRIORITÀ: COMPLETEZZA > CONCISIONE):**
   
   ⚠️ IMPORTANTE: NON essere troppo conciso!
   
   • Rispondi a TUTTE le domande
   • Fornisci DETTAGLI dalla KB (non solo link)
   • Costi: dai stima totale
   • Date/luoghi: specificali
   • Info mancanti: dillo e offri follow-up
   
   LUNGHEZZA TIPICA: 150-300 parole

4. **Orari:** SOLO periodo corrente ({context.current_season})

5. **Lingua:** {context.detected_language.upper()}

6. **Controllo finale:**
   ✓ Nome mittente usato?
   ✓ Tutte le domande coperte?
   ✓ Dettagli dalla KB forniti?
   ✓ Costi totali stimati?
   ✓ Call-to-action finale?
   ✓ Tono cordiale?

7. **ESEMPI TONO:**
   ❌ "Costo: [link]. A piedi."
   ✅ "Il gruppo parte il [data] da Tui. Costi ~780€ totali
      (ostello + voli + pasti). Va a piedi, ma bici è 
      tecnicamente possibile. Ti interessa unirti?"
"""


class TerritoryVerificationTemplate(PromptTemplate):
    """Territory verification rules"""
    
    def render(self, context: PromptContext) -> str:
        return """**VERIFICA TERRITORIO PARROCCHIALE:**

Se trovi blocco "VERIFICA TERRITORIO AUTOMATICA" nelle INFO:
✅ Usa ESATTAMENTE quelle informazioni (verifica al 100% corretta)
❌ NON fare supposizioni o interpretazioni

Se assente: usa info generiche dalla KB."""


class SpecialCasesTemplate(PromptTemplate):
    """Special cases handling"""
    
    def render(self, context: PromptContext) -> str:
        return """**CASI SPECIALI:**

• **Cresima:** Genitore→ragazzi, Adulto→adulti
• **Padrino/Madrina:** Se vuole fare → criteri
• **Impegni:** Se impossibilitato → programmi flessibili
• **Filtro temporale:** "a giugno" → solo info giugno"""


# ═══════════════════════════════════════════════════════════════════════════
# PROMPT ENGINE (Updated)
# ═══════════════════════════════════════════════════════════════════════════

class PromptEngine:
    """
    Enhanced modular prompt composition engine
    
    v2.0 Benefits:
    - Conversational, human-like responses
    - Multi-question handling
    - Smart KB extraction
    - Completeness over brevity
    """
    
    def __init__(self):
        logger.info("🎨 Initializing Enhanced PromptEngine v2.0...")
        
        # Template pipeline (order matters)
        self.template_pipeline = [
            SystemRoleTemplate(),
            LanguageInstructionTemplate(),
            
            # ✨ NEW: KB extraction strategy
            KnowledgeBaseExtractionTemplate(),
            
            KnowledgeBaseTemplate(),
            TerritoryVerificationTemplate(),
            SeasonalContextTemplate(),
            CategoryHintTemplate(),
            ConversationHistoryTemplate(),
            EmailContentTemplate(),
            NoReplyRulesTemplate(),
            
            # ✨ NEW: Conversational guidelines
            ConversationalGuidelinesTemplate(),
            
            # ✨ UPDATED: Enhanced response guidelines
            ResponseGuidelinesTemplate(),
            
            SpecialCasesTemplate(),
        ]
        
        logger.info(f"✓ Loaded {len(self.template_pipeline)} templates (v2.0 enhanced)")
        logger.info("✨ Conversational AI mode ENABLED")
    
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
        """Build enhanced conversational prompt"""
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
                if rendered:
                    sections.append(rendered)
            except Exception as e:
                logger.error(f"Error rendering {template.__class__.__name__}: {e}")
                continue
        
        # Compose final prompt
        prompt = "\n\n".join(sections)
        prompt += "\n\n**Genera la risposta completa e conversazionale:**"
        
        logger.debug(f"📐 Prompt size: {len(prompt)} chars")
        
        return prompt
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation"""
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