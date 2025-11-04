"""
Google Sheets service module for knowledge base management
Handles loading data from Google Sheets with caching and error recovery
🔧 FIXED: Thread-safe cache with lock mechanism
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from cachetools import TTLCache
from threading import Lock
from auth import get_sheets_service
import config
import logging

logger = logging.getLogger(__name__)


class SheetsManager:
    """
    Manager for Google Sheets operations with thread-safe caching
    
    🔧 IMPROVEMENTS:
    - Thread-safe cache with lock
    - Better error handling and recovery
    - Stale cache fallback for resilience
    - Detailed logging
    """
    
    def __init__(self, user_email: str = None):
        """
        Initialize Sheets manager with thread-safe caching
        
        Args:
            user_email: Email to impersonate (optional)
        """
        self.service = get_sheets_service(user_email)
        self.cache = TTLCache(maxsize=10, ttl=config.CACHE_DURATION_SECONDS)
        self._cache_lock = Lock()  # 🔧 FIX: Thread-safe cache access
        
        logger.info(f"✓ Sheets service initialized (cache TTL: {config.CACHE_DURATION_SECONDS}s)")
    
    # ========================================================================
    # THREAD-SAFE CACHE OPERATIONS
    # ========================================================================
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """
        Thread-safe cache read
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        with self._cache_lock:
            return self.cache.get(key)
    
    def _set_in_cache(self, key: str, value: Dict):
        """
        Thread-safe cache write
        
        Args:
            key: Cache key
            value: Value to cache
        """
        with self._cache_lock:
            self.cache[key] = value
    
    def _clear_cache_item(self, key: str):
        """
        Thread-safe cache item removal
        
        Args:
            key: Cache key to remove
        """
        with self._cache_lock:
            if key in self.cache:
                del self.cache[key]
    
    # ========================================================================
    # KNOWLEDGE BASE LOADING
    # ========================================================================
    
    def load_knowledge_base(self) -> Optional[Dict]:
        """
        Load knowledge base from Google Sheets with caching and fallback
        
        🔧 IMPROVEMENTS:
        - Thread-safe cache access
        - Stale cache fallback on errors
        - Better validation
        - Detailed error messages
        
        Returns:
            Dictionary containing:
            - knowledge_base_string: Formatted KB text
            - ignore_keywords: List of keywords to ignore
            - ignore_domains: List of domains/emails to ignore
        """
        cache_key = 'knowledge_base'
        
        # Check cache first (thread-safe)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.info("📦 Loading knowledge base from cache")
            return cached_data
        
        logger.info(f"📊 Cache miss, loading from Google Sheets...")
        logger.info(f"   Spreadsheet: {config.SPREADSHEET_ID}")
        logger.info(f"   Sheet: {config.SHEET_NAME}")
        
        try:
            # Get the main instructions sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f'{config.SHEET_NAME}!A:C'
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                error_msg = (
                    f"No data found in sheet '{config.SHEET_NAME}'.\n"
                    f"   Spreadsheet ID: {config.SPREADSHEET_ID}\n"
                    f"   Please verify:\n"
                    f"   1. Sheet name is correct (case-sensitive)\n"
                    f"   2. Sheet contains data in columns A, B, C\n"
                    f"   3. Service account has Viewer access"
                )
                logger.error(f"❌ {error_msg}")
                
                # Try stale cache as emergency fallback
                cached_data = self._get_from_cache(cache_key)
                if cached_data:
                    logger.warning("⚠️  Using stale cache data as emergency fallback")
                    return cached_data
                
                raise ValueError(error_msg)
            
            logger.info(f"✓ Retrieved {len(values)} rows from sheet")
            
            # Process rows
            knowledge_base_entries = []
            ignore_keywords = []
            ignore_domains = []
            
            rows_processed = 0
            rows_skipped = 0
            
            # Skip header row
            for row in values[1:]:
                if len(row) < 3:
                    rows_skipped += 1
                    continue
                
                category = row[0].strip() if row[0] else ''
                question = row[1].strip() if len(row) > 1 and row[1] else ''
                answer = row[2].strip() if len(row) > 2 and row[2] else ''
                
                if not category:
                    rows_skipped += 1
                    continue
                
                # Check for special ignore categories
                category_lower = category.lower()
                if 'da non processare' in category_lower or 'da ignorare' in category_lower:
                    if answer:
                        items = [item.strip() for item in answer.split(',')]
                        for item in items:
                            if '@' in item:
                                ignore_domains.append(item)
                            else:
                                ignore_keywords.append(item)
                        rows_processed += 1
                else:
                    # Add to knowledge base
                    knowledge_base_entries.append({
                        'category': category,
                        'question': question,
                        'answer': answer
                    })
                    rows_processed += 1
            
            logger.info(f"   Processed: {rows_processed} rows, Skipped: {rows_skipped} rows")
            
            # Build knowledge base string
            knowledge_base_string = self._format_knowledge_base(knowledge_base_entries)
            
            # Merge with configured ignore lists
            ignore_keywords.extend(config.IGNORE_KEYWORDS)
            ignore_domains.extend(config.IGNORE_DOMAINS)
            
            # Remove duplicates
            ignore_keywords = list(set(ignore_keywords))
            ignore_domains = list(set(ignore_domains))
            
            # Validate result
            if not knowledge_base_string or len(knowledge_base_string) < 100:
                logger.warning(f"⚠️  Knowledge base seems too short ({len(knowledge_base_string)} chars)")
            
            result_data = {
                'knowledge_base_string': knowledge_base_string,
                'ignore_keywords': ignore_keywords,
                'ignore_domains': ignore_domains,
                'loaded_at': datetime.now().isoformat(),
                'entry_count': len(knowledge_base_entries)
            }
            
            # Store in cache (thread-safe)
            self._set_in_cache(cache_key, result_data)
            
            logger.info(f"✓ Knowledge base loaded and cached")
            logger.info(f"   KB entries: {len(knowledge_base_entries)}")
            logger.info(f"   KB size: {len(knowledge_base_string)} chars")
            logger.info(f"   Ignore keywords: {len(ignore_keywords)}")
            logger.info(f"   Ignore domains: {len(ignore_domains)}")
            
            return result_data
            
        except Exception as e:
            logger.error(f"❌ Error loading knowledge base: {e}")
            logger.error(f"   Spreadsheet ID: {config.SPREADSHEET_ID}")
            logger.error(f"   Sheet name: {config.SHEET_NAME}")
            
            # Try to use stale cache as last resort
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                logger.warning("⚠️  Using stale cache as emergency fallback")
                logger.warning(f"   Cached at: {cached_data.get('loaded_at', 'unknown')}")
                return cached_data
            
            # No cache available, re-raise error
            raise
    
    # ========================================================================
    # REPLACEMENTS LOADING
    # ========================================================================
    
    def load_replacements(self) -> Dict[str, str]:
        """
        Load text replacements from the Sostituzioni sheet with caching
        
        🔧 IMPROVEMENTS:
        - Thread-safe cache access
        - Better error handling
        - Validation of replacement entries
        
        Returns:
            Dictionary of replacements (bad_text -> good_text)
        """
        cache_key = 'replacements'
        
        # Check cache first (thread-safe)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.info("📦 Loading replacements from cache")
            return cached_data
        
        try:
            logger.info(f"📊 Loading replacements from sheet: {config.REPLACEMENTS_SHEET}")
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f'{config.REPLACEMENTS_SHEET}!A:B'
            ).execute()
            
            values = result.get('values', [])
            replacements = {}
            
            if not values:
                logger.warning("⚠️  Replacements sheet is empty")
                return {}
            
            # Skip header row
            rows_loaded = 0
            rows_skipped = 0
            
            for row in values[1:]:
                if len(row) >= 2:
                    bad_text = row[0].strip() if row[0] else ''
                    good_text = row[1].strip() if row[1] else ''
                    
                    if bad_text and good_text:
                        # Validate: warn if bad_text is same as good_text
                        if bad_text == good_text:
                            logger.warning(f"⚠️  Redundant replacement: '{bad_text}' -> '{good_text}'")
                            rows_skipped += 1
                            continue
                        
                        replacements[bad_text] = good_text
                        rows_loaded += 1
                    else:
                        rows_skipped += 1
                else:
                    rows_skipped += 1
            
            # Store in cache (thread-safe)
            self._set_in_cache(cache_key, replacements)
            
            logger.info(f"✓ Loaded {rows_loaded} replacement rules")
            if rows_skipped > 0:
                logger.info(f"   Skipped {rows_skipped} invalid/redundant rows")
            
            return replacements
            
        except Exception as e:
            logger.warning(f"⚠️  Could not load replacements sheet: {e}")
            logger.warning(f"   This is non-critical, continuing without replacements")
            
            # Return empty dict instead of None
            return {}
    
    # ========================================================================
    # KNOWLEDGE BASE FORMATTING
    # ========================================================================
    
    def _format_knowledge_base(self, entries: List[Dict]) -> str:
        """
        Format knowledge base entries into a structured string
        
        Args:
            entries: List of knowledge base entries with category, question, answer
            
        Returns:
            Formatted knowledge base string
        """
        if not entries:
            logger.warning("⚠️  No knowledge base entries to format")
            return ""
        
        formatted_entries = []
        
        for entry in entries:
            # Skip entries with missing data
            if not entry.get('answer'):
                logger.debug(f"Skipping entry without answer: {entry.get('category', 'unknown')}")
                continue
            
            formatted_entry = f"""
--- Informazione ---
Categoria: {entry['category']}
Argomento: {entry['question']}
Dettagli: {entry['answer']}"""
            formatted_entries.append(formatted_entry)
        
        result = '\n'.join(formatted_entries)
        
        logger.debug(f"   Formatted {len(formatted_entries)} KB entries into {len(result)} chars")
        
        return result
    
    # ========================================================================
    # CACHE MANAGEMENT
    # ========================================================================
    
    def clear_cache(self):
        """
        Clear the knowledge base cache (thread-safe)
        """
        with self._cache_lock:
            items_cleared = len(self.cache)
            self.cache.clear()
            logger.info(f"🗑️  Cache cleared ({items_cleared} items)")
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics (thread-safe)
        
        Returns:
            Dictionary with cache stats
        """
        with self._cache_lock:
            return {
                'items': len(self.cache),
                'maxsize': self.cache.maxsize,
                'ttl': self.cache.ttl,
                'keys': list(self.cache.keys()),
                'thread_safe': True
            }
    
    def force_reload(self) -> bool:
        """
        Force reload of all data from Sheets (bypassing cache)
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("🔄 Force reloading data from Sheets...")
        
        # Clear cache
        self.clear_cache()
        
        # Reload knowledge base
        try:
            kb_data = self.load_knowledge_base()
            kb_success = kb_data is not None
        except Exception as e:
            logger.error(f"❌ Failed to reload knowledge base: {e}")
            kb_success = False
        
        # Reload replacements (non-critical)
        try:
            replacements = self.load_replacements()
            repl_success = True
        except Exception as e:
            logger.warning(f"⚠️  Failed to reload replacements: {e}")
            repl_success = False
        
        success = kb_success  # Only KB is critical
        
        if success:
            logger.info("✓ Force reload successful")
        else:
            logger.error("❌ Force reload failed")
        
        return success
    
    def get_knowledge_base_summary(self) -> Dict:
        """
        Get summary of current knowledge base (from cache or fresh load)
        
        Returns:
            Dictionary with KB summary statistics
        """
        try:
            kb_data = self.load_knowledge_base()
            
            if not kb_data:
                return {'status': 'error', 'message': 'No data available'}
            
            return {
                'status': 'ok',
                'entry_count': kb_data.get('entry_count', 0),
                'kb_size_chars': len(kb_data.get('knowledge_base_string', '')),
                'ignore_keywords_count': len(kb_data.get('ignore_keywords', [])),
                'ignore_domains_count': len(kb_data.get('ignore_domains', [])),
                'loaded_at': kb_data.get('loaded_at', 'unknown'),
                'cached': self._get_from_cache('knowledge_base') is not None
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    # ========================================================================
    # VALIDATION AND HEALTH CHECK
    # ========================================================================
    
    def validate_spreadsheet_access(self) -> Dict:
        """
        Validate that we can access the spreadsheet
        
        Returns:
            Dictionary with validation results
        """
        results = {
            'spreadsheet_accessible': False,
            'main_sheet_exists': False,
            'replacements_sheet_exists': False,
            'errors': []
        }
        
        try:
            # Try to get spreadsheet metadata
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=config.SPREADSHEET_ID
            ).execute()
            
            results['spreadsheet_accessible'] = True
            results['spreadsheet_title'] = spreadsheet.get('properties', {}).get('title', 'Unknown')
            
            # Check if sheets exist
            sheets = spreadsheet.get('sheets', [])
            sheet_names = [sheet.get('properties', {}).get('title', '') for sheet in sheets]
            
            results['available_sheets'] = sheet_names
            results['main_sheet_exists'] = config.SHEET_NAME in sheet_names
            results['replacements_sheet_exists'] = config.REPLACEMENTS_SHEET in sheet_names
            
            if not results['main_sheet_exists']:
                results['errors'].append(f"Main sheet '{config.SHEET_NAME}' not found")
            
            if not results['replacements_sheet_exists']:
                results['errors'].append(f"Replacements sheet '{config.REPLACEMENTS_SHEET}' not found (non-critical)")
            
        except Exception as e:
            results['errors'].append(f"Cannot access spreadsheet: {str(e)}")
        
        results['is_valid'] = results['spreadsheet_accessible'] and results['main_sheet_exists']
        
        return results


# ============================================================================
# DISTRIBUTED CACHE OPTION (for production with high concurrency)
# ============================================================================

class SheetsManagerDistributed(SheetsManager):
    """
    Alternative implementation with distributed cache (Memorystore/Redis)
    
    Use this for production environments with multiple Cloud Function instances
    
    Setup:
    1. Enable Cloud Memorystore for Redis
    2. Set environment variable: USE_MEMORYSTORE=true
    3. Set environment variable: MEMORYSTORE_INSTANCE=<instance-connection-string>
    4. Add to requirements.txt: redis>=4.5.0
    """
    
    def __init__(self, user_email: str = None):
        """Initialize with distributed cache"""
        self.service = get_sheets_service(user_email)
        
        # Initialize Redis connection
        import os
        if os.getenv('USE_MEMORYSTORE', 'false').lower() == 'true':
            try:
                import redis
                redis_host = os.getenv('MEMORYSTORE_HOST', 'localhost')
                redis_port = int(os.getenv('MEMORYSTORE_PORT', 6379))
                
                self.cache = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    decode_responses=True,
                    socket_timeout=5
                )
                self.use_distributed_cache = True
                logger.info(f"✓ Using distributed cache: {redis_host}:{redis_port}")
            except Exception as e:
                logger.warning(f"⚠️  Distributed cache failed, falling back to local: {e}")
                self.cache = TTLCache(maxsize=10, ttl=config.CACHE_DURATION_SECONDS)
                self._cache_lock = Lock()
                self.use_distributed_cache = False
        else:
            # Fallback to local cache
            self.cache = TTLCache(maxsize=10, ttl=config.CACHE_DURATION_SECONDS)
            self._cache_lock = Lock()
            self.use_distributed_cache = False
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get from distributed or local cache"""
        if self.use_distributed_cache:
            try:
                value = self.cache.get(key)
                if value:
                    return json.loads(value)
                return None
            except Exception as e:
                logger.warning(f"⚠️  Distributed cache read error: {e}")
                return None
        else:
            # Local cache with lock
            with self._cache_lock:
                return self.cache.get(key)
    
    def _set_in_cache(self, key: str, value: Dict):
        """Set in distributed or local cache"""
        if self.use_distributed_cache:
            try:
                self.cache.setex(
                    key,
                    config.CACHE_DURATION_SECONDS,
                    json.dumps(value)
                )
            except Exception as e:
                logger.warning(f"⚠️  Distributed cache write error: {e}")
        else:
            # Local cache with lock
            with self._cache_lock:
                self.cache[key] = value
