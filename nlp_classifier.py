"""
NLP Classification module for email filtering and categorization
Uses regex, heuristics, and pattern matching for fast pre-filtering
"""

import re
from typing import Dict, Optional, Tuple
import config

class EmailClassifier:
    """
    Multi-stage email classifier for intelligent filtering
    """

    def __init__(self):
        """Initialize classifier with patterns and categories"""
        print("🧠 Initializing EmailClassifier...")
        
        self.acknowledgment_patterns = [
            r'^grazie\.?\s*$',
            r'^grazie\s+mille\.?\s*$',
            r'^grazie\s+di\s+tutto\.?\s*$',
            r'^grazie\s+ancora\.?\s*$',
            r'^grazie\s+di\s+cuore\.?\s*$',
            r'^vi\s+ringrazio\.?\s*$',
            r'^ti\s+ringrazio\.?\s*$',
            r'^la\s+ringrazio\.?\s*$',
            r'^ricevuto\.?\s*$',
            r'^ok\s+ricevuto\.?\s*$',
            r'^tutto\s+chiaro\.?\s*$',
            r'^perfetto\.?\s*$',
            r'^ok\.?\s*$',
            r'^va\s+bene\.?\s*$',
            r'^d\'accordo\.?\s*$'
        ]

        self.greeting_only_patterns = [
            r'^(buongiorno|buonasera|salve|ciao)\.?\s*$',
            r'^cordiali\s+saluti\.?\s*$',
            r'^distinti\s+saluti\.?\s*$',
            r'^a\s+presto\.?\s*$',
            r'^ci\s+vediamo\.?\s*$'
        ]

        # Categorie email per classificazione
        self.categories = {
            'appointment': [
                'appuntamento', 'fissare', 'prenotare', 'quando posso',
                'disponibilità', 'orario', 'incontro',
                # English equivalents
                'appointment', 'schedule', 'book', 'availability', 'meeting'
            ],
            'information': [
                'informazioni', 'chiedere', 'sapere', 'vorrei sapere',
                'come faccio', 'dove', 'cosa serve', 'requisiti',
                # English equivalents
                'information', 'ask', 'know', 'how to', 'where', 'what', 'requirements'
            ],
            'sacrament': [
                'battesimo', 'comunione', 'cresima', 'matrimonio',
                'sacramento', 'confessione', 'prima comunione',
                # English equivalents
                'baptism', 'communion', 'confirmation', 'marriage', 'sacrament', 'confession'
            ],
            'collaboration': [
                'collaborare', 'volontario', 'aiutare', 'proposta',
                'progetto', 'iniziativa', 'gruppo', 'offrire', 'contribuire',
                # English equivalents
                'collaborate', 'volunteer', 'help', 'proposal', 'project',
                'initiative', 'group', 'offer', 'contribute', 'exhibition',
                'autograph', 'message', 'support', 'participate'
            ],
            'complaint': [
                'lamentela', 'problema', 'disservizio', 'insoddisfatto',
                'reclamo',
                # English equivalents
                'complaint', 'problem', 'issue', 'dissatisfied'
            ]
        }

        # Keywords that indicate a legitimate request even if unusual
        self.legitimate_request_indicators = [
            # Italian
            r'\bvorremmo\b', r'\bgradiremmo\b', r'\bci piacerebbe\b',
            r'\bse possibile\b', r'\bsarebbe possibile\b',
            r'\bpotrebbe\b', r'\bpotreste\b',
            r'\bcontribuire\b', r'\bpartecipare\b',
            # English
            r'\bwould be honored\b', r'\bwould appreciate\b', r'\bcould you\b',
            r'\bif possible\b', r'\bwould it be possible\b',
            r'\bwe are\b.*\bproject\b', r'\bwe would like\b',
            r'\bcontribute\b', r'\bparticipate\b'
        ]
        
        print(f"✓ Classifier initialized with {len(self.categories)} categories")

    def classify_email(self, subject: str, body: str, is_reply: bool = False) -> Dict:
        """
        Classify email through multi-stage pipeline

        Args:
            subject: Email subject
            body: Email body text
            is_reply: Whether this is a reply in a thread

        Returns:
            Classification result dictionary with:
            - should_reply: bool
            - reason: str
            - category: Optional[str]
            - confidence: float
        """
        
        print(f"   🔍 Classifying: '{subject[:50]}...'")

        # Stage 1: Fast regex filters
        main_content = self._extract_main_content(body)
        content_length = len(main_content)
        print(f"      Main content: {content_length} chars")

        # Check for simple acknowledgment
        if self._is_simple_acknowledgment(main_content):
            print(f"      ✗ Simple acknowledgment detected")
            return {
                'should_reply': False,
                'reason': 'simple_acknowledgment',
                'category': None,
                'confidence': 1.0
            }

        # Check for greeting only
        if self._is_greeting_only(main_content):
            print(f"      ✗ Greeting only")
            return {
                'should_reply': False,
                'reason': 'greeting_only',
                'category': None,
                'confidence': 0.95
            }

        # Check for legitimate request indicators (BEFORE other filters)
        if self._has_legitimate_request_indicator(subject + ' ' + main_content):
            category = self._categorize_content(subject + ' ' + main_content)
            print(f"      ✓ Legitimate request indicator found")
            print(f"      → Category: {category or 'collaboration'}")
            return {
                'should_reply': True,
                'reason': 'legitimate_request',
                'category': category or 'collaboration',
                'confidence': 0.9
            }

        # Stage 2: Content analysis
        # Check if it's a follow-up without new questions
        if is_reply and not self._contains_questions(main_content):
            if self._is_confirmation_without_questions(main_content):
                print(f"      ✗ Confirmation without questions")
                return {
                    'should_reply': False,
                    'reason': 'confirmation_without_questions',
                    'category': None,
                    'confidence': 0.85
                }

        # Stage 3: Check for questions or requests
        has_questions = self._contains_questions(main_content)
        has_request = self._contains_request(main_content)
        
        print(f"      Questions: {has_questions}, Requests: {has_request}")

        MIN_CONTENT_LENGTH = 40

        if not has_questions and not has_request:
            # Rispondi comunque se il messaggio è sostanzioso
            if len(main_content.strip()) >= MIN_CONTENT_LENGTH:
                print(f"      ✓ Sustained message (>={MIN_CONTENT_LENGTH} chars)")
                return {
                    'should_reply': True,
                    'reason': 'sustained_message_without_explicit_request',
                    'category': 'general_contact',
                    'confidence': 0.7
                }
            
            # Check for implicit request
            if self._has_implicit_request(main_content):
                category = self._categorize_content(subject + ' ' + main_content)
                print(f"      ✓ Implicit request detected")
                print(f"      → Category: {category or 'general'}")
                return {
                    'should_reply': True,
                    'reason': 'implicit_request',
                    'category': category,
                    'confidence': 0.75
                }
            
            print(f"      ✗ No actionable content")
            return {
                'should_reply': False,
                'reason': 'no_actionable_content',
                'category': None,
                'confidence': 0.70
            }

        # Stage 4: Categorize email
        category = self._categorize_content(subject + ' ' + main_content)
        
        print(f"      ✓ Needs response")
        print(f"      → Category: {category or 'general'}")
        
        return {
            'should_reply': True,
            'reason': 'needs_response',
            'category': category,
            'confidence': 0.8 if category else 0.6
        }

    # ================ Helper Methods ================

    def _has_legitimate_request_indicator(self, text: str) -> bool:
        """
        Check if text contains indicators of a legitimate request
        even if it doesn't fit standard patterns
        """
        text_lower = text.lower()
        for pattern in self.legitimate_request_indicators:
            if re.search(pattern, text_lower):
                return True
        return False

    def _extract_main_content(self, body: str) -> str:
        """
        Extract main reply content, removing quoted text and signatures
        """
        markers = [
            r'^>.*$',  # Standard quote marker
            r'^On .* wrote:.*$',  # English quote header
            r'^Il giorno .* ha scritto:.*$',  # Italian quote header
            r'^-{3,}.*Original Message.*$',  # Original message separator
            r'^_{3,}.*$',  # Underscore separator
        ]
        
        lines = body.split('\n')
        clean_lines = []
        
        for line in lines:
            is_quote = False
            for marker in markers:
                if re.match(marker, line.strip(), re.IGNORECASE):
                    is_quote = True
                    break
            if is_quote:
                break
            clean_lines.append(line)
        
        content = '\n'.join(clean_lines).strip()
        
        # Remove common signature markers
        signature_markers = [
            r'cordiali saluti',
            r'distinti saluti',
            r'in fede',
            r'best regards',
            r'sincerely',
            r'sent from my iphone',
            r'inviato da'
        ]
        
        for marker in signature_markers:
            match = re.search(marker, content, re.IGNORECASE)
            if match:
                content = content[:match.start()].strip()
        
        return content

    def _is_simple_acknowledgment(self, text: str) -> bool:
        """
        Check if text is only a simple acknowledgment
        """
        if not text or len(text.strip()) == 0:
            return False
        
        normalized = text.lower().strip()
        normalized = re.sub(r'[^\w\sàèéìòù?!]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        for pattern in self.acknowledgment_patterns:
            if re.match(pattern, normalized, re.IGNORECASE):
                return True
        
        word_count = len(normalized.split())
        if word_count <= 5:
            thank_words = ['grazie', 'ringrazio', 'ricevuto', 'ok', 'perfetto']
            if any(word in normalized for word in thank_words):
                if '?' not in text:
                    return True
        
        return False

    def _is_greeting_only(self, text: str) -> bool:
        """
        Check if text is only a greeting
        """
        normalized = text.lower().strip()
        normalized = re.sub(r'[^\w\sàèéìòù]', '', normalized)
        
        for pattern in self.greeting_only_patterns:
            if re.match(pattern, normalized, re.IGNORECASE):
                return True
        
        return False

    def _contains_questions(self, text: str) -> bool:
        """
        Check if text contains questions
        """
        # Direct question marks
        if '?' in text:
            return True

        # Italian question words
        italian_question_words = [
            r'\bquando\b', r'\bcome\b', r'\bdove\b', r'\bcosa\b',
            r'\bche\b', r'\bchi\b', r'\bperché\b', r'\bperchè\b',
            r'\bquale\b', r'\bquali\b', r'\bquanto\b', r'\bquanta\b'
        ]

        # English question words
        english_question_words = [
            r'\bwhen\b', r'\bhow\b', r'\bwhere\b', r'\bwhat\b',
            r'\bwho\b', r'\bwhy\b', r'\bwhich\b', r'\bcould\b', r'\bwould\b'
        ]

        text_lower = text.lower()
        for word_pattern in italian_question_words + english_question_words:
            if re.search(word_pattern, text_lower):
                return True
        
        return False

    def _contains_request(self, text: str) -> bool:
        """
        Check if text contains a request
        """
        request_patterns = [
            # Italian
            r'\bvorrei\b', r'\bgradirei\b', r'\bchiedo\b',
            r'\bavrei bisogno\b', r'\bho bisogno\b',
            r'\bpotrebbe\b', r'\bpotreste\b', r'\bpuò\b', r'\bpuoi\b',
            r'\bposso\b', r'\bpotrei\b', r'\bdesidero\b',
            r'\bserve\b', r'\bservono\b', r'\bnecessario\b',
            r'\bvorremmo\b', r'\bgradiremmo\b', r'\bci piacerebbe\b',
            r'\bse possibile\b', r'\bsarebbe possibile\b',
            # English
            r'\bwould like\b', r'\bwould appreciate\b', r'\bneed\b',
            r'\bcould you\b', r'\bwould you\b', r'\bcan you\b',
            r'\bmay i\b', r'\bplease\b'
        ]
        
        text_lower = text.lower()
        for pattern in request_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False

    def _has_implicit_request(self, text: str) -> bool:
        """
        Check for implicit requests (tentative language) - MORE PERMISSIVE
        """
        implicit_patterns = [
            # Italian
            r'\binteressato\b', r'\binteressata\b',
            r'\bpossibile\b', r'\bpossibilità\b',
            r'\binformazioni\b', r'\bdettagli\b',
            r'\bpartecipare\b', r'\biscrivere\b',
            r'\bcontribuire\b', r'\boffrire\b',
            # English - EXPANDED
            r'\binterested\b', r'\bpossible\b', r'\bpossibility\b',
            r'\binformation\b', r'\bdetails\b',
            r'\bparticipate\b', r'\bjoin\b',
            r'\bcontribute\b', r'\boffer\b',
            r'\bhonored\b', r'\bappreciate\b',
            r'\bproject\b', r'\bexhibition\b',
            r'\bcollecting\b', r'\bsend\b'
        ]
        
        text_lower = text.lower()
        for pattern in implicit_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False

    def _is_confirmation_without_questions(self, text: str) -> bool:
        """
        Check if it's just a confirmation without new questions
        """
        confirmation_words = [
            'confermo', 'confermiamo', 'va bene', 'ok',
            'd\'accordo', 'perfetto', 'bene così',
            # English
            'confirm', 'confirmed', 'okay', 'ok', 'fine', 'perfect'
        ]

        text_lower = text.lower()
        has_confirmation = any(word in text_lower for word in confirmation_words)
        has_question = self._contains_questions(text)
        has_request = self._contains_request(text)

        return has_confirmation and not has_question and not has_request

    def _categorize_content(self, text: str) -> Optional[str]:
        """
        Categorize email content

        Returns:
            Category name or None
        """
        text_lower = text.lower()
        
        # Count keyword matches per category
        category_scores = {}
        for category, keywords in self.categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return None

        # Return category with highest score
        best_category = max(category_scores, key=category_scores.get)
        return best_category

    def should_process_by_time(self, is_suspension_time: bool) -> bool:
        """
        Check if email should be processed based on suspension time

        Args:
            is_suspension_time: Whether current time is in suspension period

        Returns:
            True if should process
        """
        return not is_suspension_time
    
    def get_stats(self) -> Dict:
        """
        Get classifier statistics
        
        Returns:
            Dictionary with classifier stats
        """
        return {
            'categories': len(self.categories),
            'acknowledgment_patterns': len(self.acknowledgment_patterns),
            'greeting_patterns': len(self.greeting_only_patterns),
            'legitimate_indicators': len(self.legitimate_request_indicators),
            'category_keywords': {
                cat: len(keywords) for cat, keywords in self.categories.items()
            }
        }
