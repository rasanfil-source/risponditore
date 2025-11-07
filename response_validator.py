"""
Response Validator Module - OPTIMIZED VERSION
Multi-level validation system for AI-generated email responses
Removes redundant checks (greetings/closings) and focuses on critical validations

Author: Parish Secretary AI System
Version: 2.0 (Optimized)
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ValidationResult:
    """
    Result of comprehensive response validation
    
    Attributes:
        is_valid: Whether response passes all validation checks
        score: Overall quality score (0.0 to 1.0)
        errors: List of critical errors (blocking issues)
        warnings: List of warnings (non-blocking issues)
        details: Detailed results per validation level
        metadata: Additional context about validation
    """
    is_valid: bool
    score: float  # 0.0 to 1.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Dict] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'is_valid': self.is_valid,
            'score': round(self.score, 3),
            'errors': self.errors,
            'warnings': self.warnings,
            'details': self.details,
            'metadata': self.metadata
        }
    
    def __str__(self) -> str:
        """Human-readable string representation"""
        status = "✓ VALID" if self.is_valid else "✗ INVALID"
        return (
            f"{status} (score: {self.score:.2f})\n"
            f"  Errors: {len(self.errors)}\n"
            f"  Warnings: {len(self.warnings)}"
        )
    
    def get_summary(self) -> str:
        """Get detailed summary of validation"""
        lines = [str(self)]
        
        if self.errors:
            lines.append("\nErrors:")
            for i, error in enumerate(self.errors, 1):
                lines.append(f"  {i}. {error}")
        
        if self.warnings:
            lines.append("\nWarnings:")
            for i, warning in enumerate(self.warnings[:5], 1):
                lines.append(f"  {i}. {warning}")
            if len(self.warnings) > 5:
                lines.append(f"  ... and {len(self.warnings) - 5} more")
        
        return "\n".join(lines)


# ============================================================================
# RESPONSE VALIDATOR CLASS
# ============================================================================

class ResponseValidator:
    """
    Optimized response validator - focuses on critical checks only
    
    WHAT WE CHECK (Critical):
    ✅ Length (too short/long = bad UX)
    ✅ Language consistency (critical for multilingual)
    ✅ Forbidden phrases (hallucination indicators)
    ✅ Placeholders (incomplete response)
    ✅ Required signature (brand identity)
    ✅ Hallucinated data (emails, phones, times not in KB)
    ✅ Semantic redundancy (duplicate information)
    
    WHAT WE DON'T CHECK (Redundant):
    ❌ Greetings (forced in prompt)
    ❌ Closings (forced in prompt)
    ❌ Excessive repetition (Gemini rarely does this)
    
    This removes ~40% of checks while maintaining effectiveness.
    """
    
    # Class-level constants
    MIN_VALID_SCORE = 0.6
    STRICT_MODE_SCORE = 0.8
    MIN_LENGTH_CHARS = 50
    OPTIMAL_MIN_LENGTH = 100
    WARNING_MAX_LENGTH = 3000
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator
        
        Args:
            strict_mode: If True, use higher validation threshold (0.8 vs 0.6)
        """
        logger.info("🔍 Initializing Optimized ResponseValidator...")
        
        self.strict_mode = strict_mode
        self.min_valid_score = self.STRICT_MODE_SCORE if strict_mode else self.MIN_VALID_SCORE
        
        # Forbidden phrases (hallucination/uncertainty indicators)
        self.forbidden_phrases = [
            'non ho abbastanza informazioni',
            'non posso rispondere',
            'mi dispiace ma non',
            'scusa ma non',
            'purtroppo non posso',
            'non sono sicuro',
            'non sono sicura',
            'potrebbe essere',
            'probabilmente',
            'forse',
            'suppongo',
            'immagino'
        ]
        
        # 🆕 Redundancy detection thresholds
        self.max_url_mentions = 1  # Same URL should appear max once
        self.max_semantic_overlap = 0.7  # 70% sentence similarity = redundant

        # Language markers (for detection)
        self.language_markers = {
            'it': ['grazie', 'cordiali', 'saluti', 'gentile', 'parrocchia', 'messa', 'vorrei', 'quando'],
            'en': ['thank', 'regards', 'dear', 'parish', 'mass', 'church', 'would', 'could'],
            'es': ['gracias', 'saludos', 'estimado', 'parroquia', 'misa', 'iglesia', 'querría']
        }
        
        # Placeholders
        self.placeholders = [
            '[', ']', 'XXX', 'TODO', '<insert>', 'placeholder', 'tbd', 'TBD'
        ]
        
        # Required signature pattern (case-insensitive)
        self.signature_pattern = re.compile(
            r"segreteria\s+parrocchia\s+sant['\']?eugenio",
            re.IGNORECASE
        )
        
        logger.info(f"✓ Optimized ResponseValidator initialized (strict_mode={strict_mode})")
        logger.info(f"   Min valid score: {self.min_valid_score}")
    
    def validate_response(
        self,
        response: str,
        detected_language: str,
        knowledge_base: str,
        email_content: str,
        email_subject: str
    ) -> ValidationResult:
        """
        Perform comprehensive validation of AI response
        
        Args:
            response: Generated response text to validate
            detected_language: Expected language code ('it', 'en', 'es')
            knowledge_base: Original knowledge base used
            email_content: Original email body
            email_subject: Original email subject
            
        Returns:
            ValidationResult with detailed validation status
        """
        errors = []
        warnings = []
        details = {}
        score = 1.0
        
        logger.info(f"🔍 Validating response ({len(response)} chars, lang={detected_language})...")
        
        # === CHECK 1: Length (CRITICAL for UX) ===
        length_result = self._check_length(response)
        errors.extend(length_result['errors'])
        warnings.extend(length_result['warnings'])
        details['length'] = length_result
        score *= length_result['score']
        
        # === CHECK 2: Language Consistency (CRITICAL for multilingual) ===
        lang_result = self._check_language(response, detected_language)
        errors.extend(lang_result['errors'])
        warnings.extend(lang_result['warnings'])
        details['language'] = lang_result
        score *= lang_result['score']
        
        # === CHECK 3: Signature (CRITICAL for brand identity) ===
        sig_result = self._check_signature(response)
        errors.extend(sig_result['errors'])
        details['signature'] = sig_result
        score *= sig_result['score']
        
        # === CHECK 4: Forbidden Content (CRITICAL) ===
        content_result = self._check_forbidden_content(response)
        errors.extend(content_result['errors'])
        details['content'] = content_result
        score *= content_result['score']
        
        # === CHECK 5: Hallucinations (CRITICAL) ===
        halluc_result = self._check_hallucinations(response, knowledge_base)
        errors.extend(halluc_result['errors'])
        warnings.extend(halluc_result['warnings'])
        details['hallucinations'] = halluc_result
        score *= halluc_result['score']
        
        # 🆕 === CHECK 6: Semantic Redundancy (IMPORTANT for UX) ===
        redundancy_result = self._check_semantic_redundancy(response)
        warnings.extend(redundancy_result['warnings'])
        details['redundancy'] = redundancy_result
        score *= redundancy_result['score']

        
        
        # === DETERMINE VALIDITY ===
        is_valid = len(errors) == 0 and score >= self.min_valid_score
        
        # === LOG RESULTS ===
        if errors:
            logger.warning(f"❌ Validation FAILED: {len(errors)} error(s)")
            for i, error in enumerate(errors, 1):
                logger.warning(f"   {i}. {error}")
        
        if warnings:
            logger.info(f"⚠️  {len(warnings)} warning(s)")
            for i, warning in enumerate(warnings[:3], 1):
                logger.info(f"   {i}. {warning}")
            if len(warnings) > 3:
                logger.info(f"   ... and {len(warnings) - 3} more")
        
        if is_valid:
            logger.info(f"✓ Validation PASSED (score: {score:.2f})")
        else:
            logger.warning(f"✗ Validation FAILED (score: {score:.2f}, threshold: {self.min_valid_score})")
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            errors=errors,
            warnings=warnings,
            details=details,
            metadata={
                'response_length': len(response),
                'expected_language': detected_language,
                'strict_mode': self.strict_mode,
                'threshold': self.min_valid_score
            }
        )
    
    # ========================================================================
    # VALIDATION CHECKS (Private Methods)
    # ========================================================================
    
    def _check_length(self, response: str) -> Dict:
        """
        Check response length
        
        Critical UX issue: too short = unhelpful, too long = overwhelming
        """
        errors = []
        warnings = []
        score = 1.0
        
        length = len(response.strip())
        
        if length < self.MIN_LENGTH_CHARS:
            errors.append(f"Response too short ({length} chars, min {self.MIN_LENGTH_CHARS})")
            score = 0.0
        elif length < self.OPTIMAL_MIN_LENGTH:
            warnings.append(f"Response quite short ({length} chars)")
            score *= 0.85
        elif length > self.WARNING_MAX_LENGTH:
            warnings.append(f"Response very long ({length} chars, may be verbose)")
            score *= 0.95
        
        return {
            'score': score,
            'errors': errors,
            'warnings': warnings,
            'length': length
        }
    
    def _check_language(self, response: str, expected_lang: str) -> Dict:
        """
        Check language consistency
        
        Critical for multilingual support: wrong language = unusable response
        """
        errors = []
        warnings = []
        score = 1.0
        
        response_lower = response.lower()
        
        # Detect actual language using markers
        marker_scores = {}
        for lang, markers in self.language_markers.items():
            marker_scores[lang] = sum(1 for marker in markers if marker in response_lower)
        
        detected_lang = max(marker_scores, key=marker_scores.get) if max(marker_scores.values()) > 0 else expected_lang
        
        # Check match
        if detected_lang != expected_lang:
            if marker_scores[detected_lang] >= 3 and marker_scores[expected_lang] < 2:
                errors.append(
                    f"Language mismatch: expected {expected_lang.upper()}, "
                    f"detected {detected_lang.upper()}"
                )
                score *= 0.30
            else:
                warnings.append("Possible language inconsistency")
                score *= 0.85
        
        # Check for mixed languages
        high_scoring_langs = [lang for lang, score in marker_scores.items() if score >= 3]
        if len(high_scoring_langs) > 1:
            warnings.append(f"Possible mixed languages: {', '.join(high_scoring_langs)}")
            score *= 0.85
        
        return {
            'score': score,
            'errors': errors,
            'warnings': warnings,
            'detected_lang': detected_lang,
            'marker_scores': marker_scores
        }
    
    def _check_signature(self, response: str) -> Dict:
        """
        Check required signature
        
        Critical for brand identity: missing signature = unprofessional
        """
        errors = []
        score = 1.0
        
        if not self.signature_pattern.search(response.lower()):
            errors.append("Missing required signature 'Segreteria Parrocchia Sant'Eugenio'")
            score = 0.70
        
        return {
            'score': score,
            'errors': errors
        }
    
    def _check_forbidden_content(self, response: str) -> Dict:
        """
        Check for forbidden phrases and placeholders

        Critical: uncertainty phrases or placeholders = incomplete/unreliable response
        """
        errors = []
        warnings = []
        score = 1.0

        response_lower = response.lower()

        # Check forbidden phrases (uncertainty indicators)
        found_forbidden = [phrase for phrase in self.forbidden_phrases if phrase in response_lower]
        if found_forbidden:
            errors.append(f"Contains uncertainty phrases: {', '.join(found_forbidden[:2])}")
            score *= 0.50

        # Check placeholders (incomplete response)
        found_placeholders = [p for p in self.placeholders if p.lower() in response_lower]
        if found_placeholders:
            errors.append(f"Contains placeholders: {', '.join(found_placeholders)}")
            score = 0.0

        # Check NO_REPLY leakage
        if 'NO_REPLY' in response and len(response.strip()) > 20:
            errors.append("Contains 'NO_REPLY' instruction (should have been filtered)")
            score = 0.0

        # 🆕 CHECK VOCE ISTITUZIONALE (prima persona singolare)
        first_person_singular_patterns = [
            (r'\ble consiglio\b', 'Le consiglio → Le consigliamo'),
            (r'\ble suggerisco\b', 'Le suggerisco → Le suggeriamo'),
            (r'\bposso aiutarla\b', 'posso aiutarla → possiamo aiutarla'),
            (r'\bposso aiutarti\b', 'posso aiutarti → possiamo aiutarti'),
            (r'\bsono a disposizione\b', 'sono a disposizione → siamo a disposizione'),
            (r'\bresto a disposizione\b', 'resto a disposizione → restiamo a disposizione'),
            (r'\bho verificato\b', 'ho verificato → abbiamo verificato'),
            (r'\bho controllato\b', 'ho controllato → abbiamo controllato'),
            (r'\bho controllato\b', 'ho controllato → abbiamo controllato'),
            (r'\bti consiglio\b', 'ti consiglio → ti consigliamo'),
        ]

        found_singular = []
        for pattern, suggestion in first_person_singular_patterns:
            if re.search(pattern, response_lower):
                found_singular.append(suggestion)

        if found_singular:
            warnings.append(
                f"Voce istituzionale violata (usa singolare invece di plurale): "
                f"{'; '.join(found_singular[:3])}"
            )
            score *= 0.75  # Penalità significativa ma non bloccante

        return {
            'score': score,
            'errors': errors,
            'warnings': warnings,  # 🆕 Assicurati che warnings sia incluso
            'found_forbidden': found_forbidden,
            'found_placeholders': found_placeholders,
            'found_singular_voice': found_singular  # 🆕 Nuovo campo
        }
    
    def _check_hallucinations(self, response: str, knowledge_base: str) -> Dict:
        """
        Check for hallucinated data (invented information not in KB)
        
        Critical: hallucinated contact info = misinformation to users
        """
        errors = []
        warnings = []
        score = 1.0
        hallucinations = {}
        
        # === Check 1: Times ===
        time_pattern = r'\b\d{1,2}[:.]\d{2}\b'
        response_times = set(re.findall(time_pattern, response))
        kb_times = set(re.findall(time_pattern, knowledge_base))
        invented_times = response_times - kb_times
        
        if invented_times:
            warnings.append(f"Times not in KB: {', '.join(sorted(invented_times))}")
            score *= 0.85
            hallucinations['times'] = list(invented_times)
        
        # === Check 2: Email Addresses ===
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        response_emails = set(e.lower() for e in re.findall(email_pattern, response, re.IGNORECASE))
        kb_emails = set(e.lower() for e in re.findall(email_pattern, knowledge_base, re.IGNORECASE))
        invented_emails = response_emails - kb_emails
        
        if invented_emails:
            errors.append(f"Email addresses not in KB: {', '.join(invented_emails)}")
            score *= 0.50
            hallucinations['emails'] = list(invented_emails)
        
        # === Check 3: Phone Numbers ===
        phone_pattern = r'\b\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b'
        response_phones = set(re.findall(phone_pattern, response))
        kb_phones = set(re.findall(phone_pattern, knowledge_base))
        invented_phones = response_phones - kb_phones
        
        if invented_phones:
            errors.append(f"Phone numbers not in KB: {', '.join(invented_phones)}")
            score *= 0.50
            hallucinations['phones'] = list(invented_phones)
        
        return {
            'score': score,
            'errors': errors,
            'warnings': warnings,
            'hallucinations': hallucinations
        }
    
    def _check_semantic_redundancy(self, response: str) -> Dict:
        """
        🆕 Check for semantic redundancies (duplicate information)
        
        Detects:
        1. Same URL mentioned multiple times
        2. Same information repeated in different words
        3. Circular references
        
        Important for UX: redundant info = poor communication quality
        """
        warnings = []
        score = 1.0
        redundancy_details = {}
        
        # === CHECK 1: URL Duplication ===
        url_pattern = r'(?:https?://)?(?:www\.)?[\w\-]+\.[\w\-./]+'
        urls = re.findall(url_pattern, response.lower())
        
        if urls:
            url_counts = Counter(urls)
            duplicated_urls = {url: count for url, count in url_counts.items() if count > 1}
            
            if duplicated_urls:
                for url, count in duplicated_urls.items():
                    warnings.append(
                        f"URL ripetuto {count} volte: '{url}' - rimuovere duplicati o "
                        f"usare riferimenti incrociati ('come indicato sopra')"
                    )
                    score *= 0.85  # Penalty per ogni URL duplicato
                
                redundancy_details['duplicate_urls'] = duplicated_urls
        
        # === CHECK 2: Sentence-level Redundancy ===
        sentences = self._split_into_sentences(response)
        
        if len(sentences) >= 3:
            redundant_pairs = []
            
            for i in range(len(sentences)):
                for j in range(i + 1, len(sentences)):
                    similarity = self._calculate_sentence_similarity(
                        sentences[i], 
                        sentences[j]
                    )
                    
                    if similarity > self.max_semantic_overlap:
                        redundant_pairs.append({
                            'sentence_1': sentences[i][:80] + '...',
                            'sentence_2': sentences[j][:80] + '...',
                            'similarity': similarity
                        })
            
            if redundant_pairs:
                # Prendi solo le prime 2 coppie più simili
                redundant_pairs.sort(key=lambda x: x['similarity'], reverse=True)
                top_redundancies = redundant_pairs[:2]
                
                for pair in top_redundancies:
                    warnings.append(
                        f"Contenuto ridondante (similarità {pair['similarity']:.0%}): "
                        f"confronta '{pair['sentence_1']}' con '{pair['sentence_2']}'"
                    )
                
                score *= max(0.70, 1.0 - (len(redundant_pairs) * 0.10))
                redundancy_details['redundant_sentences'] = len(redundant_pairs)
        
        # === CHECK 3: Information Repetition Patterns ===
        # Rileva pattern come "costo X ... costo X" o "data Y ... data Y"
        repetition_patterns = [
            (r'costo[:\s]+([€\d\.,]+)', 'costo'),
            (r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', 'data'),
            (r'(\d{1,2}:\d{2})', 'orario'),
            (r'€\s*(\d+)', 'prezzo')
        ]
        
        for pattern, info_type in repetition_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if len(matches) > 1:
                # Se trova lo stesso valore 2+ volte
                value_counts = Counter(matches)
                repeated_values = {val: count for val, count in value_counts.items() if count > 1}
                
                if repeated_values:
                    for value, count in repeated_values.items():
                        warnings.append(
                            f"{info_type.capitalize()} ripetuto {count} volte: '{value}' - "
                            f"consolidare le informazioni"
                        )
                        score *= 0.90
                    
                    redundancy_details[f'repeated_{info_type}'] = repeated_values
        
        return {
            'score': score,
            'warnings': warnings,
            'redundancy_details': redundancy_details
        }
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences (simple heuristic)"""
        # Remove greetings and signature to focus on content
        content = text
        for marker in ['cordiali saluti', 'segreteria parrocchia', 'buongiorno', 'buonasera']:
            content = re.sub(marker, '', content, flags=re.IGNORECASE)
        
        # Split su . ! ? seguito da spazio o newline
        sentences = re.split(r'[.!?]+\s+', content.strip())
        
        # Filtra frasi troppo corte (<15 chars) o vuote
        return [s.strip() for s in sentences if len(s.strip()) > 15]
    
    def _calculate_sentence_similarity(self, sent1: str, sent2: str) -> float:
        """
        Calculate semantic similarity between two sentences
        
        Uses simple word overlap ratio (Jaccard similarity)
        For production, consider using sentence embeddings (sentence-transformers)
        """
        # Normalizza
        words1 = set(self._tokenize_sentence(sent1))
        words2 = set(self._tokenize_sentence(sent2))
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity: intersection / union
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _tokenize_sentence(self, sentence: str) -> List[str]:
        """Tokenize sentence into meaningful words"""
        # Lowercase e rimuovi punteggiatura
        sentence = sentence.lower()
        sentence = re.sub(r'[^\w\s]', ' ', sentence)
        
        # Split su spazi
        words = sentence.split()
        
        # Rimuovi stopwords comuni italiane
        stopwords = {
            'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una',
            'di', 'da', 'a', 'in', 'su', 'per', 'con', 'tra', 'fra',
            'e', 'o', 'ma', 'se', 'che', 'ci', 'si', 'ne',
            'è', 'sono', 'ho', 'ha', 'hai', 'hanno', 'essere', 'avere'
        }
        
        return [w for w in words if len(w) > 2 and w not in stopwords]
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_validation_stats(self) -> Dict[str, any]:
        """Get validator configuration statistics"""
        return {
            'strict_mode': self.strict_mode,
            'min_valid_score': self.min_valid_score,
            'min_length': self.MIN_LENGTH_CHARS,
            'max_length_warning': self.WARNING_MAX_LENGTH,
            'forbidden_phrases_count': len(self.forbidden_phrases),
            'supported_languages': list(self.language_markers.keys()),
            'placeholders_count': len(self.placeholders)
        }