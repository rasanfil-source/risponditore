# prompt_context.py - Dynamic Prompt Focusing (Ported from GAS)
"""
Computes runtime concerns and prompt profile for dynamic prompt generation.
Focuses AI attention on what matters most for each email.

✅ PORTED FROM GAS: PromptContext.txt
✅ 9 Concerns computed from runtime signals
✅ 3 Profiles: lite / standard / heavy
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptContextInput:
    """
    Input signals for concern computation.
    All signals are collected during email processing pipeline.
    """
    # Email signals
    detected_language: str = 'it'
    is_reply: bool = False
    email_body: str = ''
    email_subject: str = ''
    
    # Classification signals
    category: Optional[str] = None
    confidence: float = 0.8
    sub_intents: Dict = field(default_factory=dict)
    
    # Request Type signals
    request_type: str = 'technical'
    needs_doctrine: bool = False
    
    # Memory signals
    memory_exists: bool = False
    provided_info_count: int = 0
    
    # Conversation signals
    message_count: int = 1
    
    # Territory signals
    address_found: bool = False
    
    # Knowledge Base signals
    kb_length: int = 0
    kb_contains_dates: bool = False
    
    # Temporal signals (computed from email content)
    mentions_dates: bool = False
    mentions_times: bool = False
    
    # Salutation mode (computed from conversation state)
    salutation_mode: str = 'full'  # 'full', 'none_or_continuity', 'soft'


class PromptContext:
    """
    Compute concerns and profile for dynamic prompt generation.
    
    This class analyzes runtime signals to determine:
    1. Which concerns are active (9 boolean flags)
    2. Which prompt profile to use (lite/standard/heavy)
    
    The profile determines which templates to include in the prompt,
    focusing AI attention and potentially saving tokens.
    """
    
    # Italian months for date detection
    ITALIAN_MONTHS = [
        'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
        'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'
    ]
    
    def __init__(self, input: PromptContextInput):
        self.input = input
        
        # Auto-detect temporal mentions if not provided
        if not input.mentions_dates:
            input.mentions_dates = self._detect_date_mentions()
        if not input.mentions_times:
            input.mentions_times = self._detect_time_mentions()
        
        # Compute concerns and profile
        self.concerns = self._compute_concerns()
        self.profile = self._compute_profile()
        self.meta = self._build_meta()
        
        logger.debug(f"PromptContext created: profile={self.profile}, concerns={self.meta['active_concerns']}")
    
    def _detect_date_mentions(self) -> bool:
        """Check if email mentions dates"""
        text = f"{self.input.email_subject} {self.input.email_body}".lower()
        
        # Check Italian months
        for month in self.ITALIAN_MONTHS:
            if month in text:
                return True
        
        # Check date patterns (e.g., 15/01, 2024)
        if re.search(r'\b\d{1,2}[/.-]\d{1,2}(?:[/.-]\d{2,4})?\b', text):
            return True
        
        return False
    
    def _detect_time_mentions(self) -> bool:
        """Check if email mentions times"""
        text = f"{self.input.email_subject} {self.input.email_body}"
        
        # Check time patterns (e.g., 10:30, 10.30, ore 10)
        if re.search(r'\b\d{1,2}[:\.]\d{2}\b', text):
            return True
        if re.search(r'\bore\s+\d{1,2}\b', text, re.IGNORECASE):
            return True
        
        return False
    
    def _compute_concerns(self) -> Dict[str, bool]:
        """
        Compute 9 concern flags based on runtime signals.
        
        Each concern indicates a potential risk area that needs
        reinforcement in the prompt.
        """
        i = self.input
        
        concerns = {
            # Language Safety: Non-Italian or low confidence needs reinforcement
            'language_safety': (
                i.detected_language != 'it' or
                i.confidence < 0.8
            ),
            
            # Hallucination Risk: Large KB or temporal references increase risk
            'hallucination_risk': (
                i.kb_length > 800 or
                i.mentions_dates or
                i.mentions_times
            ),
            
            # Formatting Risk: Times or info-heavy categories need formatting rules
            'formatting_risk': (
                i.mentions_times or
                i.category in ['information', 'sacrament']
            ),
            
            # Temporal Risk: Dates in email or KB need temporal awareness
            'temporal_risk': (
                i.mentions_dates or
                i.kb_contains_dates
            ),
            
            # Doctrinal Risk: Sensitive topics need pastoral guidance
            'doctrinal_risk': (
                i.needs_doctrine or
                i.address_found or
                self._has_canonical_complexity()
            ),
            
            # Emotional Sensitivity: Pastoral situations need empathy
            'emotional_sensitivity': (
                i.request_type == 'pastoral' or
                i.sub_intents.get('emotional_distress', False) or
                i.sub_intents.get('bereavement', False)
            ),
            
            # Repetition Risk: Existing memory needs anti-repetition
            'repetition_risk': (
                i.memory_exists or
                i.message_count > 1
            ),
            
            # Identity Consistency: Maintain institutional voice
            'identity_consistency': (
                not i.is_reply or
                i.request_type != 'technical'
            ),
            
            # Response Scope Control: Focus response on what's asked
            'response_scope_control': (
                i.is_reply or
                i.confidence < 0.7
            ),
            
            # Salutation Control: Manage greeting style in follow-ups
            'salutation_control': (
                i.salutation_mode in ['none_or_continuity', 'soft']
            )
        }
        
        return concerns
    
    def _has_canonical_complexity(self) -> bool:
        """
        Check if email mentions canonically complex situations.
        These require pastoral prudence and should NOT get standard info.
        """
        text = f"{self.input.email_subject} {self.input.email_body}".lower()
        
        # Canonical complexity indicators
        complex_patterns = [
            r'\bdivorzi[ao]t[aoi]?\b',       # divorziato/a
            r'\bseparat[aoi]\b',              # separato/a  
            r'\brisposat[aoi]\b',             # risposato/a
            r'\bconviven\w*\b',               # convivente/convivenza
            r'\bannullamento\b',              # annullamento
            r'\bmusulman[aoi]?\b',            # musulmano/a
            r'\bisla\w*\b',                   # islam/islamico
            r'\bprotestante\b',               # protestante
            r'\banglican[ao]?\b',             # anglicano/a
            r'\bortodoss[ao]?\b',             # ortodosso/a
            r'\bnon\s*cattolic[ao]\b',        # non cattolico
            r'\bateo\b|\batea\b',             # ateo/atea
            r'\bdivorce[d]?\b',               # English: divorce
            r'\bmuslim\b',                    # English: muslim
            r'\bmusulmán\b',                  # Spanish: musulmán
        ]
        
        for pattern in complex_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Canonical complexity detected: pattern '{pattern}' matched")
                return True
        
        return False
    
    def _compute_profile(self) -> str:
        """
        Determine prompt profile based on active concerns.
        
        Profiles:
        - heavy: Full prompt with all templates (doctrinal/emotional cases)
        - standard: Normal prompt with key sections (info-heavy cases)
        - lite: Minimal prompt, essential templates only (simple cases)
        
        Returns:
            Profile string: 'lite', 'standard', or 'heavy'
        """
        c = self.concerns
        
        # HEAVY: Doctrinal or emotional sensitivity requires full attention
        if c['doctrinal_risk'] or c['emotional_sensitivity']:
            return 'heavy'
        
        # STANDARD: Hallucination, formatting, or temporal risks need regular attention
        if c['hallucination_risk'] or c['formatting_risk'] or c['temporal_risk']:
            return 'standard'
        
        # LITE: Simple cases, minimal prompt
        return 'lite'
    
    def _build_meta(self) -> Dict:
        """Build metadata for debugging and logging"""
        active = [k for k, v in self.concerns.items() if v]
        
        return {
            'profile': self.profile,
            'active_concerns': active,
            'concern_count': len(active)
        }
    
    def get_template_filter(self) -> List[str]:
        """
        Get list of template class names to SKIP based on profile.
        
        Returns:
            List of template class names that should be skipped
        """
        if self.profile == 'lite':
            # Skip verbose templates for simple requests
            return [
                'ExamplesTemplate',
                'FormattingGuidelinesTemplate',
                'HumanToneGuidelinesTemplate',
                'SpecialCasesTemplate',
            ]
        elif self.profile == 'standard':
            # Skip only examples for standard requests
            if not self.concerns.get('formatting_risk'):
                return ['ExamplesTemplate']
            return []
        else:
            # heavy: Include everything
            return []
    
    def should_include_template(self, template_name: str) -> bool:
        """
        Check if a specific template should be included based on profile.
        
        Args:
            template_name: Class name of the template
            
        Returns:
            True if template should be included
        """
        skip_list = self.get_template_filter()
        return template_name not in skip_list
    
    @property
    def salutation_mode(self) -> str:
        """Get the salutation mode for this context"""
        return self.input.salutation_mode


def create_prompt_context(
    detected_language: str,
    is_reply: bool,
    email_body: str,
    email_subject: str,
    category: Optional[str] = None,
    confidence: float = 0.8,
    sub_intents: Dict = None,
    request_type: str = 'technical',
    needs_doctrine: bool = False,
    memory_exists: bool = False,
    provided_info_count: int = 0,
    message_count: int = 1,
    address_found: bool = False,
    kb_length: int = 0,
    kb_contains_dates: bool = False,
    salutation_mode: str = 'full'
) -> PromptContext:
    """
    Factory function to create PromptContext with sensible defaults.
    
    This is the main entry point for creating a PromptContext.
    """
    input_obj = PromptContextInput(
        detected_language=detected_language,
        is_reply=is_reply,
        email_body=email_body,
        email_subject=email_subject,
        category=category,
        confidence=confidence,
        sub_intents=sub_intents or {},
        request_type=request_type,
        needs_doctrine=needs_doctrine,
        memory_exists=memory_exists,
        provided_info_count=provided_info_count,
        message_count=message_count,
        address_found=address_found,
        kb_length=kb_length,
        kb_contains_dates=kb_contains_dates,
        salutation_mode=salutation_mode
    )
    
    return PromptContext(input_obj)
