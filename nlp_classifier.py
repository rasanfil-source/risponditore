"""
NLP Classification module for email filtering and categorization
🔧 SIMPLIFIED: Minimal filtering, delegates complex decisions to Gemini
✅ NEW: Internal communication filter (v1.1)
"""

import re
from typing import Dict, Optional
import config

class EmailClassifier:
    """
    Simplified email classifier - filters only obvious cases
    
    🎯 PHILOSOPHY:
    - Filter ONLY ultra-simple acknowledgments (<=3 words)
    - Filter ONLY standalone greetings
    - Filter ONLY internal communications (NEW v1.1)
    - EVERYTHING ELSE goes to Gemini for intelligent analysis
    - Zero false negatives: when in doubt, let Gemini decide
    """

    def __init__(self):
        """Initialize classifier with minimal patterns"""
        print("🧠 Initializing EmailClassifier v1.1 (with Internal Comm Filter)...")
        
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

        # 🆕 NEW v1.1: Internal communication patterns
        self.internal_communication_patterns = [
            # Specific names (staff)
            r'alla\s+(?:cortese\s+)?attenzione\s+(?:di\s+)?(?:don\s+)?giandomenic',
            r'(?:alla\s+)?c\.?a\.?\s+(?:di\s+)?(?:don\s+)?giandomenic',
            r'per\s+(?:don\s+)?giandomenic',
            
            # Generic staff patterns
            r'alla\s+(?:cortese\s+)?attenzione\s+(?:di\s+)?(?:don|padre)',
            r'(?:alla\s+)?c\.?a\.?\s+(?:di\s+)?(?:don|padre)',
            r'per\s+(?:il\s+)?parroco(?:\s+[A-Z])?',
            r'(?:per|a)\s+(?:don|padre)\s+[A-Z]',
            
            # Explicit internal communications
            r'comunicazione\s+interna',
            r'circolare\s+(?:interna|parrocchiale)',
            r'memo\s+interno',
            r'nota\s+(?:interna|riservata)',
            
            # Organizational internal patterns
            r'riunione\s+(?:dello\s+)?staff',
            r'consiglio\s+pastorale',
            r'coordinamento\s+(?:catechisti|volontari)',
            r'gruppo\s+(?:animatori|operatori)',
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
        
        print(f"✓ Classifier initialized")
        print(f"   Ultra-simple ACK patterns: {len(self.ultra_simple_ack_patterns)}")
        print(f"   Greeting patterns: {len(self.greeting_only_patterns)}")
        print(f"   🆕 Internal comm patterns: {len(self.internal_communication_patterns)}")
        print(f"   Categories: {len(self.categories)}")
        print(f"   Philosophy: Filter only obvious cases, delegate rest to Gemini")

    def classify_email(self, subject: str, body: str, is_reply: bool = False) -> Dict:
        """
        Simplified classification: filter only ultra-obvious cases
        
        🆕 v1.1: Added internal communication filtering as FIRST check
        
        🎯 APPROACH:
        - FILTER 0: Internal communications (HIGHEST PRIORITY)
        - FILTER 1: Ultra-simple acknowledgments (max 3 words)
        - FILTER 2: Standalone greetings
        - Everything else → should_reply=True (let Gemini decide)

        Args:
            subject: Email subject
            body: Email body text
            is_reply: Whether this is a reply in a thread

        Returns:
            Classification result with should_reply decision
        """
        
        print(f"   🔍 Classifying: '{subject[:50]}...'")

        # ═══════════════════════════════════════════════════════════════
        # 🆕 FILTER 0: Internal Communications (HIGHEST PRIORITY)
        # ═══════════════════════════════════════════════════════════════
        if self._is_internal_communication(subject, body):
            print(f"      ✗ Internal communication detected")
            return {
                'should_reply': False,
                'reason': 'internal_communication',
                'category': None,
                'confidence': 1.0
            }

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
    # 🆕 NEW v1.1: INTERNAL COMMUNICATION DETECTION
    # ========================================================================

    def _is_internal_communication(self, subject: str, body: str) -> bool:
        """
        🆕 NEW v1.1: Detect internal communications
        
        Checks for:
        - Specific staff names (e.g., "C.A. Giandomenico")
        - Generic staff addresses (e.g., "Per il parroco")
        - Explicit internal keywords (e.g., "Comunicazione interna")
        - Multiple internal indicators
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            True if internal communication (should NOT reply automatically)
        """
        # Combine subject + beginning of body (first 1000 chars)
        text = (subject + ' ' + body[:1000]).lower()
        
        # Normalize spaces
        text = ' '.join(text.split())
        
        # Check all internal communication patterns
        for pattern in self.internal_communication_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                match = re.search(pattern, text, re.IGNORECASE)
                matched_text = match.group() if match else pattern
                print(f"         ✓ Matched internal pattern: '{matched_text}'")
                return True
        
        # Additional check: Multiple internal indicators
        # If 3+ indicators present, likely internal even without exact pattern match
        internal_indicators = [
            'staff' in text,
            'coordinamento' in text,
            'consiglio' in text,
            'riunione' in text and ('team' in text or 'gruppo' in text),
            'circolare' in text,
            'memo' in text,
            'riservat' in text,  # riservata/riservato
            text.startswith(('c.a.', 'alla c.a.', 'alla cortese attenzione')),
        ]
        
        indicator_count = sum(internal_indicators)
        
        if indicator_count >= 3:
            print(f"         ✓ Multiple internal indicators detected: {indicator_count}/8")
            return True
        
        return False

    # ========================================================================
    # EXISTING HELPER METHODS
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

            # Keep empty lines (help separate paragraphs)
            if stripped == '':
                clean_lines.append(line)
                continue

            # Skip greeting line (only if it's exactly a greeting on that line)
            if re.match(r'^(salve|buongiorno|buonasera|ciao)[\s,!.]*$', stripped, re.IGNORECASE):
                continue

            # If line is a quote marker, stop reading
            if any(re.match(marker, stripped, re.IGNORECASE) for marker in markers):
                break

            clean_lines.append(line)

        content = '\n'.join(clean_lines).strip()

        # Remove common signatures
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
            'version': '1.1',
            'categories': len(self.categories),
            'ultra_simple_ack_patterns': len(self.ultra_simple_ack_patterns),
            'greeting_patterns': len(self.greeting_only_patterns),
            'internal_comm_patterns': len(self.internal_communication_patterns),  # 🆕
            'philosophy': 'minimal_filtering_gemini_decides',
            'new_features': ['internal_communication_filter']  # 🆕
        }


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    """Test the classifier with internal communication detection"""
    
    print("=" * 80)
    print("TESTING EMAIL CLASSIFIER v1.1 - Internal Communication Filter")
    print("=" * 80)
    
    classifier = EmailClassifier()
    
    # Test cases
    test_cases = [
        {
            'subject': 'Alla cortese attenzione di Don Giandomenico',
            'body': 'Memo interno per il parroco riguardo la riunione di domani.',
            'expected': {'should_reply': False, 'reason': 'internal_communication'}
        },
        {
            'subject': 'C.A. Giandomenico',
            'body': 'Riunione staff coordinamento catechisti venerdì prossimo.',
            'expected': {'should_reply': False, 'reason': 'internal_communication'}
        },
        {
            'subject': 'Per il parroco',
            'body': 'Circolare interna: aggiornamento calendario liturgico.',
            'expected': {'should_reply': False, 'reason': 'internal_communication'}
        },
        {
            'subject': 'Info catechesi',
            'body': 'Buongiorno, vorrei sapere quando inizia la catechesi per ragazzi.',
            'expected': {'should_reply': True, 'reason': 'needs_ai_analysis'}
        },
        {
            'subject': 'Re: Info orari',
            'body': 'Grazie mille!',
            'expected': {'should_reply': False, 'reason': 'ultra_simple_acknowledgment'}
        },
        {
            'subject': 'Richiesta certificato',
            'body': 'Salve, avrei bisogno del certificato di battesimo.',
            'expected': {'should_reply': True, 'reason': 'needs_ai_analysis'}
        },
        {
            'subject': 'Comunicazione interna',
            'body': 'Nota per il consiglio pastorale.',
            'expected': {'should_reply': False, 'reason': 'internal_communication'}
        },
    ]
    
    print("\n" + "─" * 80)
    print("RUNNING TESTS")
    print("─" * 80 + "\n")
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        result = classifier.classify_email(test['subject'], test['body'])
        
        expected_reply = test['expected']['should_reply']
        expected_reason = test['expected']['reason']
        
        got_reply = result['should_reply']
        got_reason = result['reason']
        
        match = (got_reply == expected_reply and got_reason == expected_reason)
        
        status = "✅ PASS" if match else "❌ FAIL"
        
        print(f"\nTest {i}: {status}")
        print(f"  Subject: {test['subject']}")
        print(f"  Expected: should_reply={expected_reply}, reason={expected_reason}")
        print(f"  Got:      should_reply={got_reply}, reason={got_reason}")
        
        if match:
            passed += 1
        else:
            failed += 1
            print(f"  ⚠️  MISMATCH!")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80 + "\n")
    
    # Print stats
    stats = classifier.get_stats()
    print("CLASSIFIER STATISTICS:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    exit(0 if failed == 0 else 1)