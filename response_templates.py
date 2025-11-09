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


class UrgentRequestTemplate(ResponseTemplate):
    """Template for urgent requests"""
    
    def get_structure_hints(self) -> str:
        hints = "**STRUTTURA RISPOSTA URGENTE:**\n\n"
        hints += "[BLOCCO 1: Riconoscimento urgenza]\n"
        hints += "• Confermare immediatamente di aver capito l'urgenza\n\n"
        hints += "[BLOCCO 2: Informazione immediata]\n"
        hints += "• Fornire subito l'info piu importante\n"
        hints += "• Niente preamboli\n"
        hints += "• Dritto al punto\n\n"
        hints += "[BLOCCO 3: Contatti urgenti]\n"
        hints += "• Se applicabile, telefono diretto\n"
        hints += "• Orari immediati di disponibilita\n\n"
        hints += "[BLOCCO 4: Rassicurazione tempi]\n"
        hints += "• Quando ricevera risposta definitiva\n"
        return hints

    def render(self, context: TemplateContext) -> str:
        specific = context.specific_info
        
        response = context.salutation + "\n\n"
        response += "Comprendiamo l'urgenza della sua richiesta.\n\n"
        response += specific.get('info_immediata', '[Informazione piu importante SUBITO]') + "\n\n"
        response += "**Per urgenze immediate:**\n"
        response += specific.get('contatti_urgenti', '[Telefono/contatto diretto se disponibile]') + "\n\n"
        response += specific.get('follow_up_rapido', 'La ricontatteremo al piu presto.') + "\n\n"
        response += context.closing + "\n"
        response += "Segreteria Parrocchia Sant'Eugenio"
        
        return response


class TemplateSelector:
    """
    Selects appropriate template based on email category and sub-intents
    Fase 2B: Intelligent template matching
    """
    
    def __init__(self):
        self.templates = {
            'sacrament': SacramentRequestTemplate(),
            'appointment': AppointmentRequestTemplate(),
            'information': InformationRequestTemplate(),
            'collaboration': CollaborationProposalTemplate(),
            'complaint': ComplaintResponseTemplate(),
            'urgent': UrgentRequestTemplate()
        }
    
    def select_template(self, category: Optional[str], sub_intents: Dict) -> ResponseTemplate:
        """
        Select most appropriate template
        
        Priority:
        1. Urgent sub-intent (highest priority)
        2. Emotional distress -> Complaint template
        3. Category-based selection
        4. Default to Information template
        """
        # Priority 1: Urgent
        if 'urgent' in sub_intents or 'emotional_distress' in sub_intents:
            if 'emotional_distress' in sub_intents:
                return self.templates['complaint']
            return self.templates['urgent']
        
        # Priority 2: Category match
        if category and category in self.templates:
            return self.templates[category]
        
        # Default
        return self.templates['information']
    
    def get_structure_hint(self, category: Optional[str], sub_intents: Dict) -> str:
        """
        Get structure hints for Gemini prompt
        
        This will be added to the prompt to guide response structure
        """
        template = self.select_template(category, sub_intents)
        return template.get_structure_hints()