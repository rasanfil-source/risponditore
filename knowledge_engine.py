"""
Knowledge Engine Module - Refactored
Loads and provides access to the three doctrinal knowledge layers from Google Sheets

Layers:
- AI-Core Lite: Always active (tone, limits, response type)
- AI-Core: Activated for discernment (pastoral situations)  
- Dottrina: Activated for explicit doctrinal requests
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class KnowledgeEngine:
    """
    Loads and provides access to the three knowledge layers from Google Sheets.
    The content is used only to influence prompt construction as internal guardrails.
    
    IMPORTANT: Content is NEVER exposed directly to the user!
    """
    
    def __init__(self, sheets_manager=None):
        """
        Initialize KnowledgeEngine
        
        Args:
            sheets_manager: Optional SheetsManager instance for loading from Sheets.
                           If None, layers will be empty (for testing).
        """
        self.sheets_manager = sheets_manager
        self._cache = None
        
        # Load layers if sheets_manager provided
        if sheets_manager:
            self._load_layers()
        else:
            self.lite = ""
            self.core = ""
            self.doctrine = ""
            logger.warning("⚠️  KnowledgeEngine initialized without SheetsManager - layers empty")
    
    def _load_layers(self):
        """Load all three layers from Google Sheets via SheetsManager"""
        try:
            data = self.sheets_manager.load_doctrinal_kb()
            
            self.lite = data.get('ai_core_lite', '')
            self.core = data.get('ai_core', '')
            self.doctrine = data.get('dottrina', '')
            
            logger.info(f"✓ Knowledge layers loaded:")
            logger.info(f"   AI-Core Lite: {len(self.lite)} chars")
            logger.info(f"   AI-Core: {len(self.core)} chars")
            logger.info(f"   Dottrina: {len(self.doctrine)} chars")
            
        except Exception as e:
            logger.error(f"❌ Error loading knowledge layers: {e}")
            self.lite = ""
            self.core = ""
            self.doctrine = ""
    
    def get_tone_guidelines(self) -> str:
        """
        Get AI-Core Lite content (tone, limits, response type)
        
        This layer is ALWAYS injected into the prompt.
        It determines:
        - What TYPE of response is appropriate
        - What TONE to use
        - What LIMITS not to exceed
        
        Returns:
            Formatted guidelines string
        """
        return self.lite
    
    def get_pastoral_guidelines(self) -> str:
        """
        Get AI-Core content (discernment criteria)
        
        This layer is injected ONLY when discernment is needed:
        - Personal involvement detected
        - Moral tension present
        - Wounds/suffering mentioned
        - Questions about meaning/living faith
        
        Returns:
            Formatted pastoral guidelines string
        """
        return self.core
    
    def get_doctrinal_content(self) -> str:
        """
        Get full Dottrina content (theological depth)
        
        This layer is injected ONLY for explicit doctrinal requests:
        - Requests for explanation ("spiegazione")
        - Questions about Church teaching
        - Theological foundation queries
        
        Returns:
            Formatted doctrinal content string
        """
        return self.doctrine
    
    def reload(self):
        """Force reload of all layers from Google Sheets"""
        if self.sheets_manager:
            logger.info("🔄 Reloading knowledge layers...")
            self._load_layers()
        else:
            logger.warning("⚠️  Cannot reload: no SheetsManager configured")
    
    def get_stats(self) -> dict:
        """Get statistics about loaded knowledge layers"""
        return {
            'lite_chars': len(self.lite),
            'core_chars': len(self.core),
            'doctrine_chars': len(self.doctrine),
            'total_chars': len(self.lite) + len(self.core) + len(self.doctrine),
            'has_sheets_manager': self.sheets_manager is not None
        }
