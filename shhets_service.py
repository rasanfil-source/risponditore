"""
Google Sheets service module for knowledge base management
Handles loading data from Google Sheets with caching
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
        
    def load_knowledge_base(self) -> Optional[Dict]:
        """
        Load knowledge base from Google Sheets with caching
        
        Returns:
            Dictionary containing knowledge base data, ignore keywords, and ignore domains
        """
        cache_key = 'knowledge_base'
        
        # Check cache first
        if cache_key in self.cache:
            print("Loading knowledge base from cache")
            return self.cache[cache_key]
        
        print("Cache empty, loading from Google Sheets")
        
        try:
            # Get the main instructions sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f'{config.SHEET_NAME}!A:C'
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                print("No data found in sheet")
                return None
            
            knowledge_base_entries = []
            ignore_keywords = []
            ignore_domains = []
            
            # Skip header row
            for row in values[1:]:
                if len(row) < 3:
                    continue
                    
                category = row[0].strip() if row[0] else ''
                question = row[1].strip() if len(row) > 1 and row[1] else ''
                answer = row[2].strip() if len(row) > 2 and row[2] else ''
                
                if not category:
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
                else:
                    # Add to knowledge base
                    knowledge_base_entries.append({
                        'category': category,
                        'question': question,
                        'answer': answer
                    })
            
            # Build knowledge base string
            knowledge_base_string = self._format_knowledge_base(knowledge_base_entries)
            
            # Add configured ignore lists
            ignore_keywords.extend(config.IGNORE_KEYWORDS)
            ignore_domains.extend(config.IGNORE_DOMAINS)
            
            result_data = {
                'knowledge_base_string': knowledge_base_string,
                'ignore_keywords': list(set(ignore_keywords)),  # Remove duplicates
                'ignore_domains': list(set(ignore_domains))
            }
            
            # Store in cache
            self.cache[cache_key] = result_data
            print(f"Knowledge base loaded and cached for {config.CACHE_DURATION_SECONDS} seconds")
            
            return result_data
            
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            return None
    
    def load_replacements(self) -> Dict[str, str]:
        """
        Load text replacements from the Sostituzioni sheet
        
        Returns:
            Dictionary of replacements (bad_text -> good_text)
        """
        cache_key = 'replacements'
        
        # Check cache first
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f'{config.REPLACEMENTS_SHEET}!A:B'
            ).execute()
            
            values = result.get('values', [])
            replacements = {}
            
            # Skip header row
            for row in values[1:]:
                if len(row) >= 2:
                    bad_text = row[0].strip() if row[0] else ''
                    good_text = row[1].strip() if row[1] else ''
                    
                    if bad_text and good_text:
                        replacements[bad_text] = good_text
            
            # Store in cache
            self.cache[cache_key] = replacements
            return replacements
            
        except Exception as e:
            print(f"Warning: Could not load replacements sheet: {e}")
            return {}
    
    def _format_knowledge_base(self, entries: List[Dict]) -> str:
        """
        Format knowledge base entries into a structured string
        
        Args:
            entries: List of knowledge base entries
            
        Returns:
            Formatted knowledge base string
        """
        formatted_entries = []
        
        for entry in entries:
            formatted_entry = f"""
--- Informazione ---
Categoria: {entry['category']}
Argomento: {entry['question']}
Dettagli: {entry['answer']}"""
            formatted_entries.append(formatted_entry)
        
        return '\n'.join(formatted_entries)
    
    def clear_cache(self):
        """Clear the knowledge base cache"""
        self.cache.clear()
        print("Cache cleared")
