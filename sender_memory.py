"""
Sender Memory Module
Tracks recurring senders for personalized responses
Fase 3C: Personalization for returning users
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class SenderMemory:
    """
    Lightweight memory for recurring senders
    Remembers previous interactions without heavy database
    """
    
    def __init__(self, storage_path: str = "sender_memory.json"):
        self.storage_path = storage_path
        self.sender_data: Dict[str, Dict] = {}
        
        self._load_data()
        
        logger.info("🧠 SenderMemory initialized")
    
    def track_interaction(
        self,
        sender_email: str,
        sender_name: str,
        category: Optional[str] = None,
        topics: List[str] = None
    ):
        """
        Track an interaction with a sender
        
        Args:
            sender_email: Email address
            sender_name: Sender's name
            category: Email category
            topics: List of topics discussed
        """
        email_lower = sender_email.lower()
        
        if email_lower not in self.sender_data:
            self.sender_data[email_lower] = {
                'name': sender_name,
                'first_contact': datetime.now().isoformat(),
                'last_contact': datetime.now().isoformat(),
                'interaction_count': 0,
                'categories': defaultdict(int),
                'topics': defaultdict(int)
            }
        
        sender = self.sender_data[email_lower]
        sender['name'] = sender_name  # Update name if changed
        sender['last_contact'] = datetime.now().isoformat()
        sender['interaction_count'] += 1
        
        if category:
            sender['categories'][category] += 1
        
        if topics:
            for topic in topics:
                sender['topics'][topic] += 1
        
        self._save_data()
        
        logger.debug(f"📝 Tracked interaction with {sender_email} ({sender['interaction_count']} total)")
    
    def get_sender_context(self, sender_email: str) -> Optional[str]:
        """
        Get context about a recurring sender
        
        Returns formatted context string for prompt, or None if first-time sender
        """
        email_lower = sender_email.lower()
        
        if email_lower not in self.sender_data:
            return None
        
        sender = self.sender_data[email_lower]
        
        # Don't treat as recurring until 2+ interactions
        if sender['interaction_count'] < 2:
            return None
        
        # Build context
        context_lines = [
            "═══════════════════════════════════════════════════════════════",
            "📧 MITTENTE RICORRENTE - CONTESTO PRECEDENTE",
            "═══════════════════════════════════════════════════════════════",
            "",
            f"👤 Nome: {sender['name']}",
            f"📊 Interazioni precedenti: {sender['interaction_count']}",
            f"📅 Prima interazione: {sender['first_contact'][:10]}",
            f"📅 Ultima interazione: {sender['last_contact'][:10]}",
            ""
        ]
        
        # Most discussed topics
        if sender['topics']:
            top_topics = sorted(
                sender['topics'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            context_lines.append("🔍 Argomenti discussi in passato:")
            for topic, count in top_topics:
                context_lines.append(f"   • {topic} ({count}x)")
            context_lines.append("")
        
        # Most common categories
        if sender['categories']:
            top_category = max(sender['categories'].items(), key=lambda x: x[1])
            context_lines.append(f"📂 Categoria più frequente: {top_category[0]}")
            context_lines.append("")
        
        context_lines.extend([
            "💡 INDICAZIONI:",
            "   • Usa espressioni come 'Come già discusso...' se pertinente",
            "   • Evita di ripetere informazioni già fornite in passato",
            "   • Mantieni tono coerente con interazioni precedenti",
            "",
            "═══════════════════════════════════════════════════════════════",
            ""
        ])
        
        return "\n".join(context_lines)
    
    def _save_data(self):
        """Save sender data to file"""
        try:
            # Convert defaultdict to regular dict for JSON
            save_data = {}
            for email, data in self.sender_data.items():
                save_data[email] = {
                    'name': data['name'],
                    'first_contact': data['first_contact'],
                    'last_contact': data['last_contact'],
                    'interaction_count': data['interaction_count'],
                    'categories': dict(data['categories']),
                    'topics': dict(data['topics'])
                }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving sender data: {e}")
    
    def _load_data(self):
        """Load sender data from file"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Convert back to defaultdict
            for email, sender_data in data.items():
                self.sender_data[email] = {
                    'name': sender_data['name'],
                    'first_contact': sender_data['first_contact'],
                    'last_contact': sender_data['last_contact'],
                    'interaction_count': sender_data['interaction_count'],
                    'categories': defaultdict(int, sender_data.get('categories', {})),
                    'topics': defaultdict(int, sender_data.get('topics', {}))
                }
            
            logger.info(f"📁 Loaded {len(self.sender_data)} sender records")
            
        except FileNotFoundError:
            logger.info("📁 No existing sender data, starting fresh")
        except Exception as e:
            logger.error(f"Error loading sender data: {e}")
