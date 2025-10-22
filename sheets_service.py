"""
Google Sheets service module for knowledge base management
Handles loading data from Google Sheets with caching and error recovery
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from cachetools import TTLCache
from auth import get_sheets_service
import config

class SheetsManager:
    def __init__(self, user_email: str = None):
        """Initialize Sheets manager with caching"""
        self.service = get_sheets_service(user_email)
        self.cache = TTLCache(maxsize=10, ttl=config.CACHE_DURATION_SECONDS)
        print(f"✓ Sheets cache initialized (TTL: {config.CACHE_DURATION_SECONDS}s)")
        
    def load_knowledge_base(self) -> Optional[Dict]:
        """
        Load knowledge base from Google Sheets with caching and fallback
        
        Returns:
            Dictionary containing knowledge base data, ignore keywords, and ignore domains
        """
        cache_key = 'knowledge_base'
        
        # Check cache first
        if cache_key in self.cache:
            print("📦 Loading knowledge base from cache")
            return self.cache[cache_key]
        
        print(f"📊 Cache miss, loading from Google Sheets...")
        print(f"   Spreadsheet: {config.SPREADSHEET_ID}")
        print(f"   Sheet: {config.SHEET_NAME}")
        
        try:
            # Get the main instructions sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f'{config.SHEET_NAME}!A:C'
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print("❌ No data found in sheet")
                print(f"   Check that sheet '{config.SHEET_NAME}' exists and has data")
                
                # Se c'è una versione in cache (anche scaduta), usala come fallback
                if cache_key in self.cache:
                    print("⚠️  Using stale cache data as emergency fallback")
                    return self.cache[cache_key]
                
                return None
            
            print(f"✓ Retrieved {len(values)} rows from sheet")
            
            knowledge_base_entries = []
            ignore_keywords = []
            ignore_domains = []
            
            # Skip header row
            rows_processed = 0
            rows_skipped = 0
            
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
            
            print(f"   Processed: {rows_processed} rows, Skipped: {rows_skipped} rows")
            
            # Build knowledge base string
            knowledge_base_string = self._format_knowledge_base(knowledge_base_entries)
            
            # Add configured ignore lists
            ignore_keywords.extend(config.IGNORE_KEYWORDS)
            ignore_domains.extend(config.IGNORE_DOMAINS)
            
            # Remove duplicates
            ignore_keywords = list(set(ignore_keywords))
            ignore_domains = list(set(ignore_domains))
            
            result_data = {
                'knowledge_base_string': knowledge_base_string,
                'ignore_keywords': ignore_keywords,
                'ignore_domains': ignore_domains
            }
            
            # Store in cache
            self.cache[cache_key] = result_data
            
            print(f"✓ Knowledge base loaded and cached")
            print(f"   KB entries: {len(knowledge_base_entries)}")
            print(f"   Ignore keywords: {len(ignore_keywords)}")
            print(f"   Ignore domains: {len(ignore_domains)}")
            
            return result_data
            
        except Exception as e:
            print(f"❌ Error loading knowledge base: {e}")
            print(f"   Spreadsheet ID: {config.SPREADSHEET_ID}")
            print(f"   Sheet name: {config.SHEET_NAME}")
            
            # Try to use stale cache as last resort
            if cache_key in self.cache:
                print("⚠️  Using stale cache as emergency fallback")
                return self.cache[cache_key]
            
            return None
    
    def load_replacements(self) -> Dict[str, str]:
        """
        Load text replacements from the Sostituzioni sheet with caching
        
        Returns:
            Dictionary of replacements (bad_text -> good_text)
        """
        cache_key = 'replacements'
        
        # Check cache first
        if cache_key in self.cache:
            print("📦 Loading replacements from cache")
            return self.cache[cache_key]
        
        try:
            print(f"📊 Loading replacements from sheet: {config.REPLACEMENTS_SHEET}")
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f'{config.REPLACEMENTS_SHEET}!A:B'
            ).execute()
            
            values = result.get('values', [])
            replacements = {}
            
            if not values:
                print("⚠️  Replacements sheet is empty")
                return {}
            
            # Skip header row
            rows_loaded = 0
            for row in values[1:]:
                if len(row) >= 2:
                    bad_text = row[0].strip() if row[0] else ''
                    good_text = row[1].strip() if row[1] else ''
                    
                    if bad_text and good_text:
                        replacements[bad_text] = good_text
                        rows_loaded += 1
            
            # Store in cache
            self.cache[cache_key] = replacements
            
            print(f"✓ Loaded {rows_loaded} replacement rules")
            return replacements
            
        except Exception as e:
            print(f"⚠️  Could not load replacements sheet: {e}")
            print(f"   This is non-critical, continuing without replacements")
            
            # Return empty dict instead of None
            return {}
    
    def _format_knowledge_base(self, entries: List[Dict]) -> str:
        """
        Format knowledge base entries into a structured string
        
        Args:
            entries: List of knowledge base entries
            
        Returns:
            Formatted knowledge base string
        """
        if not entries:
            print("⚠️  No knowledge base entries to format")
            return ""
        
        formatted_entries = []
        
        for entry in entries:
            formatted_entry = f"""
--- Informazione ---
Categoria: {entry['category']}
Argomento: {entry['question']}
Dettagli: {entry['answer']}"""
            formatted_entries.append(formatted_entry)
        
        result = '\n'.join(formatted_entries)
        
        print(f"   Formatted {len(entries)} KB entries into {len(result)} chars")
        
        return result
    
    def clear_cache(self):
        """Clear the knowledge base cache"""
        items_cleared = len(self.cache)
        self.cache.clear()
        print(f"🗑️  Cache cleared ({items_cleared} items)")
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache stats
        """
        return {
            'items': len(self.cache),
            'maxsize': self.cache.maxsize,
            'ttl': self.cache.ttl,
            'keys': list(self.cache.keys())
        }
    
    def force_reload(self) -> bool:
        """
        Force reload of all data from Sheets (bypassing cache)
        
        Returns:
            True if successful
        """
        print("🔄 Force reloading data from Sheets...")
        
        self.clear_cache()
        
        kb_data = self.load_knowledge_base()
        replacements = self.load_replacements()
        
        success = kb_data is not None
        
        if success:
            print("✓ Force reload successful")
        else:
            print("❌ Force reload failed")
        
        return success
