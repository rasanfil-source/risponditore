"""
NLP Classification module for email filtering and categorization
🔧 SIMPLIFIED: Minimal filtering, delegates complex decisions to Gemini
"""

import re
from typing import Dict, Optional
import config

class EmailClassifier:
    """
    Simplified email classifier - filters only obvious cases
    
    🎯 NEW PHILOSOPHY:
    - Filter ONLY ultra-simple acknowledgments (<=3 words)
    - Filter ONLY standalone greetings
    - EVERYTHING ELSE goes to Gemini for intelligent analysis
    - Zero false negatives: when in doubt, let Gemini decide
    """

    def __init__(self):
        """Initialize classifier with minimal patterns"""
        print("🧠 Initializing Simplified EmailClassifier...")
        
        # ULTRA-RESTRICTIVE: Only 3-word max acknowledgments
        self.ultra_simple_ack_patterns = [
            r'^grazie\.?\s*$',           # "grazie"
            r'^grazie\s+mille\.?\s*$',   # "grazie mille"
            r'^ricevuto\.?\s*$',         # "ricevuto"
            r'^ok\.?\s*$',               # "ok"
            r'^perfetto\.?\s*$',         # "perfetto"
            r'^ok\s+ricevuto\.?\s*$',    # "ok ricevuto"
        ]

        self.greeting_only_patterns = [
            r'^(buongiorno|buonasera|salve|ciao)\.?\s*$',
            r'^cordiali\s+saluti\.?\s*$',
            r'^distinti\s+saluti\.?\s*$',
        ]

        # Categorie per hint a Gemini (opzionali)
        self.categories = {
            'appointment': [
                'appuntamento', 'fissare', 'prenotare', 'quando posso',
                'disponibilità', 'orario', 'incontro', 'prenotazione',
                'riservare', 'riserva', 'posti', 'visita',
                'appointment', 'schedule', 'book', 'booking', 'availability', 
                'meeting', 'reservation', 'reserve', 'visit'
            ],
            'information': [
                'informazioni', 'chiedere', 'sapere', 'vorrei sapere',
                'come faccio', 'dove', 'cosa serve', 'requisiti',
                'information', 'ask', 'know', 'how to', 'where', 'what', 'requirements'
            ],
            'sacrament': [
                'battesimo', 'comunione', 'cresima', 'matrimonio',
                'sacramento', 'confessione', 'prima comunione',
                'baptism', 'communion', 'confirmation', 'marriage', 'sacrament', 'confession'
            ],
            'collaboration': [
                'collaborare', 'volontario', 'aiutare', 'proposta',
                'progetto', 'iniziativa', 'gruppo', 'offrire', 'contribuire',
                'collaborate', 'volunteer', 'help', 'proposal', 'project',
                'initiative', 'group', 'offer', 'contribute', 'exhibition',
                'autograph', 'message', 'support', 'participate'
            ],
            'complaint': [
                'lamentela', 'problema', 'disservizio', 'insoddisfatto',
                'reclamo', 'complaint', 'problem', 'issue', 'dissatisfied'
            ]
        }
        
        print(f"✓ Simplified Classifier initialized")
        print(f"   Philosophy: Filter only obvious cases, delegate rest to Gemini")

    def classify_email(self, subject: str, body: str, is_reply: bool = False) -> Dict:
        """
        Simplified classification: filter only ultra-obvious cases
        
        🎯 NEW APPROACH:
        - Check ONLY for 3-word-max acknowledgments
        - Check ONLY for standalone greetings
        - Everything else → should_reply=True (let Gemini decide)

        Args:
            subject: Email subject
            body: Email body text
            is_reply: Whether this is a reply in a thread

        Returns:
            Classification result with should_reply decision
        """
        
        print(f"   🔍 Classifying: '{subject[:50]}...'")

        # Extract main content (remove quotes/signatures)
        main_content = self._extract_main_content(body)
        content_length = len(main_content)
        print(f"      Main content: {content_length} chars")

        # FILTER 1: Ultra-simple acknowledgment (max 3 words, no questions)
        if self._is_ultra_simple_acknowledgment(main_content):
            print(f"      ✗ Ultra-simple acknowledgment (<=3 words, no question)")
            return {
                'should_reply': False,
                'reason': 'ultra_simple_acknowledgment',
                'category': None,
                'confidence': 1.0
            }

        # FILTER 2: Greeting only (standalone)
        if self._is_greeting_only(main_content):
            print(f"      ✗ Greeting only (standalone)")
            return {
                'should_reply': False,
                'reason': 'greeting_only',
                'category': None,
                'confidence': 0.95
            }

        # EVERYTHING ELSE: Pass to Gemini for intelligent analysis
        category = self._categorize_content(subject + ' ' + main_content)
        
        print(f"      ✓ Passing to Gemini for intelligent analysis")
        if category:
            print(f"      → Category hint: {category}")
        
        return {
            'should_reply': True,  # Default: let Gemini decide
            'reason': 'needs_ai_analysis',
            'category': category,
            'confidence': 0.85 if category else 0.75
        }

    # ========================================================================
    # MINIMAL HELPER METHODS
    # ========================================================================

    def _extract_main_content(self, body: str) -> str:
        """Extract main content, removing quoted text and signatures"""
        markers = [
            r'^>.*$',
            r'^On .* wrote:.*$',
            r'^Il giorno .* ha scritto:.*$',
            r'^-{3,}.*Original Message.*$',
            r'^_{3,}.*$',
        ]

        lines = body.split('\n')
        clean_lines = []

        for line in lines:
            stripped = line.strip()

            # 🔹 Se la riga è vuota, la manteniamo (aiuta a separare paragrafi)
            if stripped == '':
                clean_lines.append(line)
                continue

            # 🔹 Salta il saluto iniziale (solo se è esattamente un saluto su quella riga)
            if re.match(r'^(salve|buongiorno|buonasera|ciao)[\s,!.]*$', stripped, re.IGNORECASE):
                # Ignora questa riga ma NON interrompere la lettura del resto del messaggio
                continue

            # 🔹 Se la riga è una citazione (marker), interrompi: il resto è storico
            if any(re.match(marker, stripped, re.IGNORECASE) for marker in markers):
                break

            clean_lines.append(line)

        # Assicuriamoci che clean_lines sia una lista
        if not isinstance(clean_lines, list):
            clean_lines = []

        content = '\n'.join(clean_lines).strip()

        # 🔹 Rimozione firme comuni
        signature_markers = [
            r'cordiali saluti', r'distinti saluti', r'in fede',
            r'best regards', r'sincerely', r'sent from my iphone', r'inviato da'
        ]

        for marker in signature_markers:
            m = re.search(marker, content, re.IGNORECASE)
            if m:
                content = content[:m.start()].strip()
                break

        return content



    def _is_ultra_simple_acknowledgment(self, text: str) -> bool:
        """
        Check if text is ULTRA-SIMPLE acknowledgment
        
        RESTRICTIVE: Only <=3 words, no questions, pure thanks
        
        Examples that PASS (get filtered):
        - "grazie"
        - "grazie mille"
        - "ok ricevuto"
        
        Examples that DON'T pass (go to Gemini):
        - "grazie! ma per sabato?" (has question)
        - "grazie per tutto, ci vediamo" (>3 words)
        - "ricevuto, quando posso venire?" (has question)
        """
        if not text or len(text.strip()) == 0:
            return False
        
        # Normalize
        normalized = text.lower().strip()
        normalized = re.sub(r'[^\w\sàèéìòù?!]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # If contains question mark, NOT a simple ack
        if '?' in text:
            return False
        
        # Count words
        word_count = len(normalized.split())
        
        # STRICT: max 3 words
        if word_count > 3:
            return False
        
        # Must contain thank/received word
        thank_words = ['grazie', 'ringrazio', 'ricevuto', 'ok', 'perfetto']
        has_thanks = any(word in normalized for word in thank_words)
        
        if has_thanks and word_count <= 3:
            return True
        
        return False

    def _is_greeting_only(self, text: str) -> bool:
        """Check if text is only a standalone greeting"""
        normalized = text.lower().strip()
        normalized = re.sub(r'[^\w\sàèéìòù]', '', normalized)
        
        for pattern in self.greeting_only_patterns:
            if re.match(pattern, normalized, re.IGNORECASE):
                return True
        
        return False

    def _categorize_content(self, text: str) -> Optional[str]:
        """Categorize email content (hint for Gemini)"""
        text_lower = text.lower()
        
        category_scores = {}
        for category, keywords in self.categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return None

        return max(category_scores, key=category_scores.get)

    def should_process_by_time(self, is_suspension_time: bool) -> bool:
        """Check if email should be processed based on suspension time"""
        return not is_suspension_time
    
    def get_stats(self) -> Dict:
        """Get classifier statistics"""
        return {
            'categories': len(self.categories),
            'ultra_simple_ack_patterns': len(self.ultra_simple_ack_patterns),
            'greeting_patterns': len(self.greeting_only_patterns),
            'philosophy': 'minimal_filtering_gemini_decides'
        }
