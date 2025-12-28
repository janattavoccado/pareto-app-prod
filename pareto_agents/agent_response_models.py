"""
Pydantic models for OpenAI Agents SDK response structures
Minimal, focused models for type-safe response extraction

File location: pareto_agents/agent_response_models.py
"""

from typing import List, Optional, Any
from pydantic import BaseModel, ConfigDict, field_validator
import logging

logger = logging.getLogger(__name__)


class ResponseOutputText(BaseModel):
    """Text content in a response output"""
    model_config = ConfigDict(extra='allow')
    
    text: str
    type: str = "output_text"
    
    @field_validator('text', mode='before')
    @classmethod
    def strip_text(cls, v: str) -> str:
        """Strip whitespace from text"""
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()


class ResponseOutputMessage(BaseModel):
    """A single response output message"""
    model_config = ConfigDict(extra='allow')
    
    id: str
    content: List[ResponseOutputText]
    role: str = "assistant"
    status: str = "completed"
    type: str = "message"
    
    def get_text(self) -> str:
        """Extract text from first content item"""
        if self.content and len(self.content) > 0:
            return self.content[0].text
        return ""


class ModelResponse(BaseModel):
    """Complete response from OpenAI Agents SDK"""
    model_config = ConfigDict(extra='allow')
    
    output: List[ResponseOutputMessage] = []
    response_id: str = ""
    
    def get_text(self) -> str:
        """Extract text from first output message"""
        if self.output and len(self.output) > 0:
            return self.output[0].get_text()
        return ""
    
    def get_all_text(self) -> str:
        """Extract and concatenate all text from all output messages"""
        texts = [msg.get_text() for msg in self.output if msg.get_text()]
        return " ".join(texts)


def parse_agent_response(response: Any) -> Optional[ModelResponse]:
    """
    Parse agent response into ModelResponse Pydantic model
    
    Args:
        response: Response object from agent
        
    Returns:
        ModelResponse: Parsed response or None if parsing fails
    """
    try:
        # Already a ModelResponse
        if isinstance(response, ModelResponse):
            return response
        
        # Try to parse as dict
        if isinstance(response, dict):
            return ModelResponse(**response)
        
        # Try to convert object to dict
        if hasattr(response, 'model_dump'):
            # It's a Pydantic model
            return ModelResponse(**response.model_dump())
        
        if hasattr(response, '__dict__'):
            # Try to extract attributes
            response_dict = {
                'output': getattr(response, 'output', []),
                'response_id': getattr(response, 'response_id', ''),
            }
            return ModelResponse(**response_dict)
        
        logger.warning(f"Could not parse response of type: {type(response).__name__}")
        return None
    
    except Exception as e:
        logger.error(f"Error parsing agent response: {str(e)}", exc_info=True)
        return None


def extract_agent_text(response: Any) -> str:
    """
    Extract text from agent response using Pydantic models
    
    Args:
        response: Response object from agent
        
    Returns:
        str: Extracted text or empty string
    """
    try:
        # Parse as ModelResponse
        model_response = parse_agent_response(response)
        
        if model_response:
            text = model_response.get_text()
            if text:
                logger.info(f"✅ Extracted agent text: {text[:80]}")
                return text
        
        logger.warning("Could not extract text from agent response")
        return ""
    
    except Exception as e:
        logger.error(f"Error extracting agent text: {str(e)}", exc_info=True)
        return ""
