"""
Response Templates Module
Pre-validated templates for common scenarios
Fase 2B: Improve response consistency and intelligence
✅ FIXED: Prima persona plurale (voce istituzionale)
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class TemplateContext:
    """Context for template rendering"""
    sender_name: str
    salutation: str
    closing: str
    specific_info: Dict[str, str]


class ResponseTemplate:
    """Base class for response templates"""
    
    def render(self, context: TemplateContext) -> str:
        """Render template with context"""
        raise NotImplementedError
    
    def get_structure_hints(self) -> str:
        """Get structural hints for Gemini to follow this template"""
        raise NotImplementedError


class SacramentRequestTemplate(ResponseTemplate):
    """Template for sacrament requests (Battesimo, Cresima, Matrimonio)"""
    
    def get_structure_hints(self) -> str:
        hints = "**STRUTTURA RISPOSTA SACRAMENTO:**\n\n"
        hints += "[BLOCCO 1: Accoglienza entusiasta]\n"
        hints += "• Esprimere gioia per il sacramento\n"
        hints += "• Frase di benvenuto calorosa\n"
        hints += "• Es: Siamo lieti di accompagnarvi in questo importante cammino\n\n"
        hints += "[BLOCCO 2: Informazioni pratiche]\n"
        hints += "• Requisiti necessari (se presenti in KB)\n"
        hints += "• Date e orari disponibili\n"
        hints += "• Documenti richiesti\n\n"
        hints += "[BLOCCO 3: Procedura di iscrizione]\n"
        hints += "• Come procedere (contatti, form, appuntamento)\n"
        hints += "• Tempi previsti\n\n"
        hints += "[BLOCCO 4: Rassicurazione]\n"
        hints += "• Disponibilità per chiarimenti\n"
        hints += "• Tono rassicurante e positivo\n"
        return hints

    def render(self, context: TemplateContext) -> str:
        """Render complete sacrament response"""
        specific = context.specific_info
        
        response = context.salutation + "\n\n"
        response += "Siamo lieti di accompagnarvi in questo importante passo della vita cristiana.\n\n"
        response += "**Informazioni per " + specific.get('sacramento', 'il sacramento') + ":**\n\n"
        response += specific.get('requisiti', '[Requisiti dalla knowledge base]') + "\n\n"
        response += specific.get('procedura', '[Procedura dalla knowledge base]') + "\n\n"
        response += "**Per procedere:**\n"
        response += specific.get('prossimi_passi', '[Contattare la segreteria o compilare form]') + "\n\n"
        response += "Restiamo a disposizione per qualsiasi chiarimento.\n\n"  # ✅ FIXED
        response += context.closing + "\n"
        response += "Segreteria Parrocchia Sant'Eugenio"
        
        return response


class AppointmentRequestTemplate(ResponseTemplate):
    """Template for appointment requests"""
    
    def get_structure_hints(self) -> str:
        hints = "**STRUTTURA RISPOSTA APPUNTAMENTO:**\n\n"
        hints += "[BLOCCO 1: Riconoscimento richiesta]\n"
        hints += "• Breve conferma di aver ricevuto la richiesta\n"
        hints += "• Es: Abbiamo ricevuto la sua richiesta di appuntamento\n\n"  # ✅ FIXED
        hints += "[BLOCCO 2: Opzioni concrete]\n"
        hints += "• Orari segreteria/disponibilita\n"
        hints += "• Telefono diretto se urgente\n"
        hints += "• Form prenotazione se disponibile\n\n"
        hints += "[BLOCCO 3: Tempi di risposta]\n"
        hints += "• Quando ricevera conferma\n"
        hints += "• Es: Le risponderemo entro 24-48 ore\n"
        return hints

    def render(self, context: TemplateContext) -> str:
        specific = context.specific_info
        
        response = context.salutation + "\n\n"
        response += "Abbiamo ricevuto la sua richiesta di appuntamento.\n\n"  # ✅ FIXED
        response += "**Per fissare l'appuntamento:**\n"
        response += specific.get('opzioni_contatto', '[Opzioni dalla KB: telefono, form, etc.]') + "\n\n"
        response += specific.get('disponibilita', '[Orari segreteria dalla KB]') + "\n\n"
        response += "Le risponderemo entro " + specific.get('tempo_risposta', '24-48 ore') + " per confermare data e ora.\n\n"
        response += context.closing + "\n"
        response += "Segreteria Parrocchia Sant'Eugenio"
        
        return response


class InformationRequestTemplate(ResponseTemplate):
    """Template for general information requests"""
    
    def get_structure_hints(self) -> str:
        hints = "**STRUTTURA RISPOSTA INFORMAZIONI:**\n\n"
        hints += "[BLOCCO 1: Risposta diretta]\n"
        hints += "• Vai subito al punto\n"
        hints += "• Rispondi alla domanda specifica\n\n"
        hints += "[BLOCCO 2: Dettagli strutturati]\n"
        hints += "• Se necessario, lista ordinata di dettagli\n"
        hints += "• Uso di bullet per elenchi\n\n"
        hints += "[BLOCCO 3: Riferimenti aggiuntivi]\n"
        hints += "• Link per approfondimenti (se disponibili)\n"
        hints += "• Contatti per altre domande\n"
        return hints

    def render(self, context: TemplateContext) -> str:
        specific = context.specific_info
        
        response = context.salutation + "\n\n"
        response += specific.get('risposta_diretta', '[Risposta principale alla domanda]') + "\n\n"
        response += "**Dettagli:**\n"
        response += specific.get('dettagli', '[Informazioni aggiuntive dalla KB]') + "\n\n"
        response += specific.get('riferimenti', '') + "\n"
        response += context.closing + "\n"
        response += "Segreteria Parrocchia Sant'Eugenio"
        
        return response


class CollaborationProposalTemplate(ResponseTemplate):
    """Template for collaboration/volunteer proposals"""
    
    def get_structure_hints(self) -> str:
        hints = "**STRUTTURA RISPOSTA COLLABORAZIONE:**\n\n"
        hints += "[BLOCCO 1: Ringraziamento sentito]\n"
        hints += "• Ringraziare con sincerità\n"
        hints += "• Apprezzare l'iniziativa\n\n"
        hints += "[BLOCCO 2: Valutazione positiva]\n"
        hints += "• Esprimere interesse per la proposta\n"
        hints += "• Tono entusiasta ma professionale\n\n"
        hints += "[BLOCCO 3: Prossimi passi]\n"
        hints += "• Come procedera la parrocchia\n"
        hints += "• Tempi previsti per valutazione\n\n"
        hints += "[BLOCCO 4: Chiusura positiva]\n"
        hints += "• Ribadire apprezzamento\n"
        hints += "• Mantenere porta aperta\n"
        return hints

    def render(self, context: TemplateContext) -> str:
        specific = context.specific_info
        
        response = context.salutation + "\n\n"
        response += "La ringraziamo sentitamente per la sua " + specific.get('tipo_proposta', 'disponibilita/proposta') + ".\n\n"
        response += "Apprezziamo molto " + specific.get('cosa_apprezzato', 'il suo interesse verso la nostra comunita') + " e valuteremo con attenzione " + specific.get('cosa_valutato', 'quanto proposto') + ".\n\n"
        response += "**Prossimi passi:**\n"
        response += specific.get('prossimi_passi', '[Chi la contattara e quando dalla KB]') + "\n\n"
        response += "Grazie ancora per il suo contributo alla vita della parrocchia.\n\n"
        response += context.closing + "\n"
        response += "Segreteria Parrocchia Sant'Eugenio"
        
        return response


class ComplaintResponseTemplate(ResponseTemplate):
    """Template for complaints or issues"""
    
    def get_structure_hints(self) -> str:
        hints = "**STRUTTURA RISPOSTA RECLAMO/PROBLEMA:**\n\n"
        hints += "[BLOCCO 1: Riconoscimento del problema]\n"
        hints += "• Riconoscere esplicitamente il disagio\n"
        hints += "• NON minimizzare\n\n"
        hints += "[BLOCCO 2: Empatia senza giustificazioni]\n"
        hints += "• Mostrare comprensione\n"
        hints += "• Evitare frasi difensive\n\n"
        hints += "[BLOCCO 3: Azione concreta]\n"
        hints += "• Cosa fara la parrocchia per risolvere\n"
        hints += "• Tempi previsti\n"
        hints += "• Impegno chiaro\n\n"
        hints += "[BLOCCO 4: Disponibilita continua]\n"
        hints += "• Mantenere canale di comunicazione aperto\n"
        return hints

    def render(self, context: TemplateContext) -> str:
        specific = context.specific_info
        
        response = context.salutation + "\n\n"
        response += "Comprendiamo " + specific.get('cosa_compreso', 'il disagio espresso') + " e ce ne scusiamo.\n\n"
        response += specific.get('riconoscimento_problema', '[Riconoscere specificamente il problema]') + "\n\n"
        response += "**Come procederemo:**\n"
        response += specific.get('azioni_concrete', '[Azioni specifiche per risolvere]') + "\n\n"
        response += specific.get('tempi_follow_up', 'La terremo aggiornata sull\'evoluzione della situazione.') + "\n\n"
        response += "Restiamo a disposizione per qualsiasi ulteriore necessità.\n\n"  # ✅ FIXED
        response += context.closing + "\n"
        response += "Segreteria Parrocchia Sant'Eugenio"
        
        return response


class BereavementTemplate(ResponseTemplate):
    """
    ✅ NEW: Template for bereavement/condolence situations
    
    Used when emails mention: lutto, defunto, funerale, esequie, etc.
    Provides an especially empathetic and respectful tone.
    """
    
    def get_structure_hints(self) -> str:
        hints = "**STRUTTURA RISPOSTA CONDOGLIANZE/LUTTO:**\n\n"
        hints += "[BLOCCO 1: Espressione di vicinanza - PRIORITÀ MASSIMA]\n"
        hints += "• Inizia SEMPRE con condoglianze sincere\n"
        hints += "• Tono sobrio, rispettoso, non formale\n"
        hints += "• Es: \"Ci uniamo al vostro dolore in questo momento difficile\"\n"
        hints += "• Es: \"Siamo profondamente vicini a voi e alla vostra famiglia\"\n\n"
        hints += "[BLOCCO 2: Disponibilità pastorale]\n"
        hints += "• Offrire supporto spirituale\n"
        hints += "• Menzionare disponibilità del sacerdote\n"
        hints += "• NON essere troppo tecnici/burocratici\n\n"
        hints += "[BLOCCO 3: Informazioni pratiche - SOLO SE RICHIESTE]\n"
        hints += "• Se chiedono info su funerale/esequie, fornirle con delicatezza\n"
        hints += "• Contatti diretti per organizzazione\n"
        hints += "• Evitare liste lunghe o formattazione eccessiva\n\n"
        hints += "[BLOCCO 4: Chiusura calda]\n"
        hints += "• Preghiera o vicinanza spirituale\n"
        hints += "• Es: \"Vi accompagniamo con la preghiera\"\n"
        hints += "• Es: \"Il Signore vi sia di conforto\"\n\n"
        hints += "⚠️ IMPORTANTE: In caso di lutto, NON usare:\n"
        hints += "• Icone/emoji\n"
        hints += "• Formattazione markdown pesante\n"
        hints += "• Tono burocratico o freddo\n"
        hints += "• Liste puntate per le condoglianze\n"
        return hints

    def render(self, context: TemplateContext) -> str:
        specific = context.specific_info
        
        response = context.salutation + "\n\n"
        response += "Ci stringiamo a voi in questo momento di dolore.\n\n"
        response += specific.get('vicinanza', 'Siamo profondamente vicini a voi e alla vostra famiglia.') + "\n\n"
        response += specific.get('supporto_pastorale', 'I nostri sacerdoti sono a disposizione per qualsiasi supporto spirituale.') + "\n\n"
        if specific.get('info_pratiche'):
            response += specific.get('info_pratiche') + "\n\n"
        response += "Vi accompagniamo con la preghiera.\n\n"
        response += context.closing + "\n"
        response += "Segreteria Parrocchia Sant'Eugenio"
        
        return response


class TemplateSelector:
    """
    Selects appropriate template based on email category and sub-intents
    
    ✅ REFACTORED: Removed urgency handling (not needed)
    ✅ EXTENSIBLE: Easy to add new sub-intent → template mappings
    """
    
    def __init__(self):
        self.templates = {
            'sacrament': SacramentRequestTemplate(),
            'appointment': AppointmentRequestTemplate(),
            'information': InformationRequestTemplate(),
            'collaboration': CollaborationProposalTemplate(),
            'complaint': ComplaintResponseTemplate(),
            'bereavement': BereavementTemplate(),  # ✅ NEW
        }
        
        # ✅ Sub-intent to template override mapping (extensible)
        # If a sub-intent is detected, override the category template
        self.sub_intent_template_overrides = {
            'emotional_distress': 'complaint',  # Use empathetic complaint template
            'bereavement': 'bereavement',       # ✅ NEW: special bereavement template
        }
    
    def select_template(self, category: Optional[str], sub_intents: Dict) -> ResponseTemplate:
        """
        Select most appropriate template
        
        Priority:
        1. Sub-intent overrides (e.g., emotional_distress → complaint template)
        2. Category-based selection
        3. Default to Information template
        
        Args:
            category: Email category from classifier
            sub_intents: Dict of detected sub-intents
            
        Returns:
            Appropriate ResponseTemplate
        """
        # Priority 1: Check sub-intent overrides
        for sub_intent, template_key in self.sub_intent_template_overrides.items():
            if sub_intents.get(sub_intent):
                if template_key in self.templates:
                    return self.templates[template_key]
        
        # Priority 2: Category match
        if category and category in self.templates:
            return self.templates[category]
        
        # Default
        return self.templates['information']
    
    def get_structure_hint(self, category: Optional[str], sub_intents: Dict) -> str:
        """
        Get structure hints for Gemini prompt
        
        This will be added to the prompt to guide response structure
        
        Args:
            category: Email category
            sub_intents: Dict of detected sub-intents
            
        Returns:
            Structure hint string for the prompt
        """
        template = self.select_template(category, sub_intents)
        return template.get_structure_hints()