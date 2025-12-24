"""
Memory Service using Google Cloud Firestore
Stores lightweight conversation context to improve AI responses and continuity.
"""

import logging
import os
import datetime
from typing import Dict, Optional, List, Any
from google.cloud import firestore
from auth import get_service_account_credentials

logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Manages conversation memory in Firestore.
    
    Structure per thread:
    {
        "language": "it" | "en" | "es",
        "category": "information",
        "tone": "standard",
        "provided_info": ["orari_messe", "contatti"], # List of info already given
        "last_updated": timestamp,
        "message_count": int,
        "participants": ["..."]
    }
    """
    
    def __init__(self, collection_name: str = "conversation_memory"):
        """Initialize Firestore client"""
        self.collection_name = collection_name
        self.client = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initialize Firestore client with error recovery"""
        try:
            # In Cloud Functions, this often works automatically with default credentials
            # If explicit credentials are required (e.g. local dev), we can use auth.py helpers
            
            project_id = os.environ.get('GCP_PROJECT')
            logger.info(f"🧠 Initializing Firestore Memory (Project: {project_id})...")
            
            # Try default initialization
            self.client = firestore.Client(project=project_id)
            logger.info("✓ Firestore client initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Firestore: {e}")
            logger.warning("   Memory features will be disabled for this session.")
            self.client = None

    def get_memory(self, thread_id: str) -> Dict[str, Any]:
        """
        Retrieve memory for a specific thread
        
        Args:
            thread_id: Gmail Thread ID
            
        Returns:
            Dictionary with context or empty dict if not found/error
        """
        if not self.client or not thread_id:
            return {}
            
        try:
            doc_ref = self.client.collection(self.collection_name).document(thread_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                logger.info(f"🧠 Memory hit for thread {thread_id} (Lang: {data.get('language')})")
                return data
            else:
                logger.info(f"🧠 Memory miss for thread {thread_id} (New conversation)")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error retrieving memory: {e}")
            return {}

    def update_memory(self, thread_id: str, new_data: Dict[str, Any]):
        """
        Update memory for a thread (merge with existing)
        
        Args:
            thread_id: Gmail Thread ID
            new_data: Dictionary of data to merge
        """
        if not self.client or not thread_id:
            return
            
        try:
            doc_ref = self.client.collection(self.collection_name).document(thread_id)
            
            # Add timestamp
            new_data['last_updated'] = datetime.datetime.now()
            
            # Use set with merge=True to update or create
            doc_ref.set(new_data, merge=True)
            logger.info(f"🧠 Memory updated for thread {thread_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating memory: {e}")

    def add_provided_info_topics(self, thread_id: str, topics: List[str]):
        """
        Add to the list of provided information topics to avoid repetition
        
        Args:
            thread_id: Gmail Thread ID
            topics: List of topic strings
        """
        if not self.client or not thread_id or not topics:
            return
            
        try:
            doc_ref = self.client.collection(self.collection_name).document(thread_id)
            
            # Atomic array union to add new topics without duplication
            doc_ref.update({
                "provided_info": firestore.ArrayUnion(topics),
                "last_updated": datetime.datetime.now()
            })
            logger.info(f"🧠 Memory: Added provided topics {topics}")
            
        except Exception as e:
            # If document doesn't exist, create it
            if "NOT_FOUND" in str(e) or "Not found" in str(e):
                try:
                    self.update_memory(thread_id, {"provided_info": topics})
                except Exception as create_err:
                    logger.error(f"❌ Error creating memory document: {create_err}")
            else:
                logger.error(f"❌ Error adding provided info: {e}")
