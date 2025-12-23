"""
Request Type Classifier Module
Classifies email requests as Technical, Pastoral, or Mixed

This classification drives conditional injection of doctrinal KB layers.
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class RequestTypeClassifier:
    """
    Classifica le richieste in:
    - TECHNICAL: domande procedurali ("si può", "quanti", "quando")
    - PASTORAL: coinvolgimento personale ("mi sento", emozioni, ferite)
    - MIXED: entrambi gli aspetti
    
    Logica di attivazione KB:
    - AI-Core Lite: SEMPRE (tono, limiti, tipo risposta)
    - AI-Core: Solo quando needs_discernment = True
    - Dottrina: Solo quando needs_doctrine = True
    """
    
    # ========================================================================
    # INDICATORI TECNICI
    # Domande procedurali, normative, su numeri, condizioni formali
    # ========================================================================
    
    TECHNICAL_INDICATORS: List[Tuple[str, int]] = [
        # Possibilità/obbligo (weight 2)
        (r'\bsi può\b', 2),
        (r'\bnon si può\b', 2),
        (r'\bè possibile\b', 2),
        (r'\bè obbligatorio\b', 2),
        (r'\bbisogna\b', 2),
        (r'\bdeve\b', 1),
        (r'\bdevono\b', 1),
        
        # Domande su numeri/quantità (weight 2)
        (r'\bquanti\b', 2),
        (r'\bquante\b', 2),
        (r'\bquanto costa\b', 2),
        
        # Domande temporali (weight 1)
        (r'\bquando\b', 1),
        (r'\ba che ora\b', 2),
        (r'\borari\b', 2),
        
        # Domande procedurali (weight 2)
        (r'\bcome (?:si )?fa\b', 2),
        (r'\bcome funziona\b', 2),
        (r'\bqual è la procedura\b', 2),
        (r'\bche documenti?\b', 2),
        
        # Riferimenti a ruoli formali (weight 1)
        (r'\bpadrino\b', 1),
        (r'\bmadrina\b', 1),
        (r'\btestimone\b', 1),
        (r'\bcertificato\b', 2),
        (r'\bdocument\w+\b', 1),
        (r'\bmodulo\b', 1),
        (r'\biscrizione\b', 1),
    ]
    
    # ========================================================================
    # INDICATORI PASTORALI
    # Prima persona, emozioni, situazioni di vita, richieste di senso
    # ========================================================================
    
    PASTORAL_INDICATORS: List[Tuple[str, int]] = [
        # Prima persona emotiva (weight 3)
        (r'\bmi sento\b', 3),
        (r'\bmi pesa\b', 3),
        (r'\bmi sono sentit[oa]\b', 3),
        (r'\bnon mi sento\b', 3),
        
        # Emozioni (weight 2)
        (r'\bsoffr\w+\b', 2),
        (r'\bdifficolt[àa]\b', 2),
        (r'\bferit[oa]\b', 2),
        (r'\besclus[oa]\b', 2),
        (r'\bsol[oa]\b', 2),
        (r'\bpaura\b', 2),
        (r'\bansia\b', 2),
        (r'\btristezza\b', 2),
        (r'\bcolpa\b', 2),
        (r'\bvergogna\b', 2),
        
        # Incomprensione (weight 2)
        (r'\bnon capisco\b', 2),
        (r'\bnon riesco a capire\b', 2),
        
        # Situazioni di vita complesse (weight 2)
        (r'\bdivorziat[oa]\b', 2),
        (r'\bseparat[oa]\b', 2),
        (r'\brisposat[oa]\b', 2),
        (r'\bconvivente\b', 2),
        (r'\blutto\b', 2),
        (r'\bdefunt[oa]\b', 2),
        (r'\bmalattia\b', 2),
        
        # Richieste di senso (weight 3)
        (r'\bperché la chiesa\b', 3),
        (r'\bperché dio\b', 3),
        (r'\bche senso ha\b', 3),
        (r'\bcome vivere\b', 3),
        (r'\bcome affrontare\b', 2),
    ]
    
    # ========================================================================
    # INDICATORI DOTTRINALI ESPLICITI
    # Richieste di spiegazione teologica/dottrinale
    # ========================================================================
    
    DOCTRINE_INDICATORS: List[Tuple[str, int]] = [
        (r'\bspiegazione\b', 2),
        (r'\bspiegami\b', 2),
        (r'\bperché la chiesa (?:insegna|dice|crede)\b', 3),
        (r'\bfondamento teologic\w+\b', 3),
        (r'\bdottrina\b', 2),
        (r'\bmagistero\b', 3),
        (r'\bcatechismo\b', 2),
        (r'\binsegnamento della chiesa\b', 3),
    ]
    
    def __init__(self):
        logger.info("✓ RequestTypeClassifier initialized")
    
    def classify(self, subject: str, body: str) -> Dict:
        """
        Classifica la richiesta email
        
        Args:
            subject: Oggetto email
            body: Corpo email
            
        Returns:
            {
                'type': 'technical' | 'pastoral' | 'mixed',
                'technical_score': int,
                'pastoral_score': int,
                'doctrine_score': int,
                'needs_discernment': bool,  # Attiva AI-Core
                'needs_doctrine': bool,      # Attiva Dottrina
                'detected_indicators': List[str]
            }
        """
        text = f"{subject} {body}".lower()
        
        # Calculate scores
        technical_score, tech_indicators = self._calculate_score(text, self.TECHNICAL_INDICATORS)
        pastoral_score, pastoral_indicators = self._calculate_score(text, self.PASTORAL_INDICATORS)
        doctrine_score, doctrine_indicators = self._calculate_score(text, self.DOCTRINE_INDICATORS)
        
        # Determine type
        if pastoral_score >= 3 and pastoral_score > technical_score:
            request_type = 'pastoral'
        elif technical_score >= 2 and pastoral_score <= 1:
            request_type = 'technical'
        elif pastoral_score >= 2 and technical_score >= 2:
            request_type = 'mixed'
        else:
            # Default to technical for low-signal requests
            request_type = 'technical'
        
        # Determine activation flags
        needs_discernment = (
            pastoral_score >= 2 or 
            request_type in ('pastoral', 'mixed')
        )
        
        needs_doctrine = doctrine_score >= 2
        
        result = {
            'type': request_type,
            'technical_score': technical_score,
            'pastoral_score': pastoral_score,
            'doctrine_score': doctrine_score,
            'needs_discernment': needs_discernment,
            'needs_doctrine': needs_doctrine,
            'detected_indicators': tech_indicators + pastoral_indicators + doctrine_indicators
        }
        
        logger.info(f"   📊 Request classification: {request_type.upper()}")
        logger.info(f"      Tech={technical_score}, Pastor={pastoral_score}, Doctr={doctrine_score}")
        logger.info(f"      Discernment={needs_discernment}, Doctrine={needs_doctrine}")
        
        return result
    
    def _calculate_score(self, text: str, indicators: List[Tuple[str, int]]) -> Tuple[int, List[str]]:
        """
        Calculate weighted score for a set of indicators
        
        Args:
            text: Text to analyze
            indicators: List of (pattern, weight) tuples
            
        Returns:
            (total_score, list_of_matched_patterns)
        """
        total = 0
        matched = []
        
        for pattern, weight in indicators:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                total += weight * len(matches)
                matched.append(pattern)
        
        return total, matched
