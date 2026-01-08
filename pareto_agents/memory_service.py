"""
Memory Service for Pareto Agents
Integrates with Mem0 Platform for persistent memory across conversations

File location: pareto_agents/memory_service.py
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Check if mem0ai is available
try:
    from mem0 import MemoryClient
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("mem0ai package not installed. Memory features will be disabled.")


class MemoryService:
    """
    Service for managing agent memory using Mem0 Platform.
    
    Features:
    - Store conversation memories per user
    - Retrieve relevant memories for context
    - Search memories with filters
    - Support for user-specific and agent-specific memories
    """
    
    def __init__(self):
        """Initialize the Memory Service with Mem0 client."""
        self.client = None
        self.enabled = False
        self.org_id = os.environ.get('MEM0_ORG_ID')
        self.project_id = os.environ.get('MEM0_PROJECT_ID')
        
        if not MEM0_AVAILABLE:
            logger.warning("Memory service disabled: mem0ai package not installed")
            return
        
        api_key = os.environ.get('MEM0_API_KEY')
        if not api_key:
            logger.warning("Memory service disabled: MEM0_API_KEY not set")
            return
        
        try:
            # Initialize Mem0 client
            # Note: Mem0 Platform API requires api_key, and optionally org_id and project_id
            client_kwargs = {"api_key": api_key}
            
            # Add org_id and project_id if provided
            # Both are optional for basic usage, but recommended for organization
            if self.org_id:
                client_kwargs["org_id"] = self.org_id
                logger.info(f"Using Mem0 org_id: {self.org_id[:20]}...")
            if self.project_id:
                client_kwargs["project_id"] = self.project_id
                logger.info(f"Using Mem0 project_id: {self.project_id[:20]}...")
            
            self.client = MemoryClient(**client_kwargs)
            self.enabled = True
            logger.info("✅ Memory service initialized successfully")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Failed to initialize memory service: {error_msg}")
            
            # Provide helpful guidance for common errors
            if "org_id" in error_msg.lower() or "project_id" in error_msg.lower():
                logger.error("💡 Hint: Set MEM0_ORG_ID environment variable. Find it in Mem0 dashboard under Settings > Organization.")
            
            self.enabled = False
    
    def _normalize_user_id(self, phone_number: str) -> str:
        """
        Normalize phone number to use as user_id.
        Removes special characters and ensures consistency.
        """
        # Remove spaces, dashes, and other special characters
        normalized = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        return normalized
    
    def add_memory(
        self,
        user_message: str,
        assistant_response: str,
        phone_number: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict]:
        """
        Store a conversation exchange as memory.
        
        Args:
            user_message: The user's message
            assistant_response: The assistant's response
            phone_number: User's phone number (used as user_id)
            metadata: Optional additional metadata
            
        Returns:
            Memory creation result or None if failed
        """
        if not self.enabled:
            logger.debug("Memory service not enabled, skipping add_memory")
            return None
        
        try:
            user_id = self._normalize_user_id(phone_number)
            
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_response}
            ]
            
            # Build metadata
            mem_metadata = {
                "source": "pareto_agent",
                "timestamp": datetime.utcnow().isoformat(),
                "phone_number": phone_number
            }
            if metadata:
                mem_metadata.update(metadata)
            
            # Add memory to Mem0
            result = self.client.add(
                messages=messages,
                user_id=user_id,
                metadata=mem_metadata,
                version="v2"
            )
            
            logger.info(f"✅ Memory stored for user {user_id[:8]}...")
            logger.debug(f"Memory result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store memory: {e}")
            return None
    
    def add_single_memory(
        self,
        content: str,
        phone_number: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict]:
        """
        Store a single piece of information as memory.
        
        Args:
            content: The information to remember
            phone_number: User's phone number (used as user_id)
            metadata: Optional additional metadata
            
        Returns:
            Memory creation result or None if failed
        """
        if not self.enabled:
            return None
        
        try:
            user_id = self._normalize_user_id(phone_number)
            
            messages = [
                {"role": "user", "content": content}
            ]
            
            mem_metadata = {
                "source": "pareto_agent",
                "timestamp": datetime.utcnow().isoformat(),
                "type": "explicit_memory"
            }
            if metadata:
                mem_metadata.update(metadata)
            
            result = self.client.add(
                messages=messages,
                user_id=user_id,
                metadata=mem_metadata,
                version="v2"
            )
            
            logger.info(f"✅ Single memory stored for user {user_id[:8]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to store single memory: {e}")
            return None
    
    def search_memories(
        self,
        query: str,
        phone_number: str,
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Dict]:
        """
        Search for relevant memories based on a query.
        
        Args:
            query: The search query
            phone_number: User's phone number to filter memories
            top_k: Maximum number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of relevant memories
        """
        if not self.enabled:
            logger.debug("Memory service not enabled, skipping search")
            return []
        
        try:
            user_id = self._normalize_user_id(phone_number)
            
            results = self.client.search(
                query=query,
                filters={"user_id": user_id},
                version="v2",
                top_k=top_k,
                threshold=threshold
            )
            
            # Handle both list and dict response formats
            if isinstance(results, dict) and 'results' in results:
                memories = results['results']
            elif isinstance(results, list):
                memories = results
            else:
                memories = []
            
            logger.info(f"🔍 Found {len(memories)} relevant memories for user {user_id[:8]}...")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Failed to search memories: {e}")
            return []
    
    def get_all_memories(
        self,
        phone_number: str,
        page: int = 1,
        page_size: int = 50
    ) -> List[Dict]:
        """
        Get all memories for a user.
        
        Args:
            phone_number: User's phone number
            page: Page number for pagination
            page_size: Number of results per page
            
        Returns:
            List of all memories for the user
        """
        if not self.enabled:
            return []
        
        try:
            user_id = self._normalize_user_id(phone_number)
            
            results = self.client.get_all(
                filters={"user_id": user_id},
                version="v2",
                page=page,
                page_size=page_size
            )
            
            if isinstance(results, dict) and 'results' in results:
                memories = results['results']
            elif isinstance(results, list):
                memories = results
            else:
                memories = []
            
            logger.info(f"📋 Retrieved {len(memories)} memories for user {user_id[:8]}...")
            return memories
            
        except Exception as e:
            logger.error(f"❌ Failed to get memories: {e}")
            return []
    
    def get_context_for_message(
        self,
        message: str,
        phone_number: str,
        max_memories: int = 3
    ) -> str:
        """
        Get relevant memory context for a new message.
        Returns a formatted string to include in the agent prompt.
        
        Args:
            message: The incoming user message
            phone_number: User's phone number
            max_memories: Maximum number of memories to include
            
        Returns:
            Formatted context string
        """
        if not self.enabled:
            return ""
        
        memories = self.search_memories(
            query=message,
            phone_number=phone_number,
            top_k=max_memories,
            threshold=0.25
        )
        
        if not memories:
            return ""
        
        # Format memories as context
        context_parts = ["📝 **Relevant memories about this user:**"]
        for i, mem in enumerate(memories, 1):
            memory_text = mem.get('memory', '')
            if memory_text:
                context_parts.append(f"  {i}. {memory_text}")
        
        context = "\n".join(context_parts)
        logger.debug(f"Memory context: {context}")
        return context
    
    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: The ID of the memory to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            self.client.delete(memory_id)
            logger.info(f"🗑️ Memory {memory_id} deleted")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete memory: {e}")
            return False
    
    def delete_all_user_memories(self, phone_number: str) -> bool:
        """
        Delete all memories for a user.
        
        Args:
            phone_number: User's phone number
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            user_id = self._normalize_user_id(phone_number)
            self.client.delete_all(filters={"user_id": user_id})
            logger.info(f"🗑️ All memories deleted for user {user_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete user memories: {e}")
            return False


# Global instance for easy access
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """
    Get the global memory service instance.
    Creates one if it doesn't exist.
    """
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def add_conversation_memory(
    user_message: str,
    assistant_response: str,
    phone_number: str,
    metadata: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Convenience function to add a conversation memory.
    """
    service = get_memory_service()
    return service.add_memory(user_message, assistant_response, phone_number, metadata)


def get_memory_context(message: str, phone_number: str) -> str:
    """
    Convenience function to get memory context for a message.
    """
    service = get_memory_service()
    return service.get_context_for_message(message, phone_number)


def search_user_memories(query: str, phone_number: str, top_k: int = 5) -> List[Dict]:
    """
    Convenience function to search user memories.
    """
    service = get_memory_service()
    return service.search_memories(query, phone_number, top_k)
