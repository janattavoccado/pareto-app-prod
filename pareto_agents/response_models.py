"""
Pydantic models for OpenAI Agents SDK responses
Provides type-safe parsing and extraction of agent responses with comprehensive validation
Flexible schema to handle various response formats from the agents SDK

File location: pareto_agents/response_models.py
"""

from typing import List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Configuration
# ============================================================================

class ParetoBaseModel(BaseModel):
    """Base model with common configuration for all Pareto models"""
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields from API responses
        str_strip_whitespace=True,  # Strip whitespace from strings
        validate_assignment=True,  # Validate on assignment
    )


# ============================================================================
# Pydantic Models for OpenAI Agents SDK Response Structure
# ============================================================================

class InputTokensDetails(ParetoBaseModel):
    """Details about input token usage"""
    cached_tokens: int = 0


class OutputTokensDetails(ParetoBaseModel):
    """Details about output token usage"""
    reasoning_tokens: int = 0


class Usage(ParetoBaseModel):
    """Token usage information - all fields optional with defaults"""
    requests: int = 0
    input_tokens: int = 0
    input_tokens_details: Optional[InputTokensDetails] = None
    output_tokens: int = 0
    output_tokens_details: Optional[OutputTokensDetails] = None
    total_tokens: int = 0
    request_usage_entries: List[Any] = Field(default_factory=list)
    
    @property
    def total_cost_estimate(self) -> float:
        """Estimate cost based on token usage (rough estimate)"""
        # Approximate pricing: $0.50 per 1M input tokens, $1.50 per 1M output tokens
        input_cost = (self.input_tokens / 1_000_000) * 0.50
        output_cost = (self.output_tokens / 1_000_000) * 1.50
        return input_cost + output_cost


class ResponseOutputText(ParetoBaseModel):
    """Text content in a response output"""
    annotations: List[Any] = Field(default_factory=list)
    text: str
    type: str = "output_text"
    logprobs: List[Any] = Field(default_factory=list)
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure text is not empty"""
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()


class ResponseOutputMessage(ParetoBaseModel):
    """A single response output message"""
    id: str
    content: List[ResponseOutputText]
    role: str = "assistant"
    status: str = "completed"
    type: str = "message"
    
    def get_text(self) -> str:
        """Extract text from first content item"""
        if self.content:
            return self.content[0].text
        return ""


class ModelResponse(ParetoBaseModel):
    """Complete response from OpenAI Agents SDK - flexible schema"""
    output: List[ResponseOutputMessage] = Field(default_factory=list)
    usage: Optional[Usage] = None
    response_id: str = ""
    
    def get_text(self) -> str:
        """Extract text from first output message"""
        if self.output:
            return self.output[0].get_text()
        return ""
    
    def get_all_text(self) -> str:
        """Extract and concatenate all text from all output messages"""
        texts = [msg.get_text() for msg in self.output if msg.get_text()]
        return " ".join(texts)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return self.model_dump_json()


# ============================================================================
# Response Extraction Functions with Pydantic
# ============================================================================

def parse_model_response(response: Any) -> Optional[ModelResponse]:
    """
    Parse any response format into a ModelResponse Pydantic model
    Flexible parsing with graceful fallbacks
    
    Args:
        response: Response object from agent (dict, ModelResponse, or raw object)
        
    Returns:
        ModelResponse: Parsed response or None if parsing fails
    """
    try:
        # Already a Pydantic ModelResponse
        if isinstance(response, ModelResponse):
            return response
        
        # Dict format - parse with Pydantic
        if isinstance(response, dict):
            try:
                return ModelResponse(**response)
            except Exception as e:
                logger.debug(f"Could not parse dict as ModelResponse: {e}")
                # Try to extract what we can
                return ModelResponse(
                    output=response.get('output', []),
                    usage=response.get('usage'),
                    response_id=response.get('response_id', ''),
                )
        
        # Try to convert object to dict first
        if hasattr(response, '__dict__'):
            # Try model_dump if it's a Pydantic model
            if hasattr(response, 'model_dump'):
                try:
                    return ModelResponse(**response.model_dump())
                except Exception as e:
                    logger.debug(f"Could not parse model_dump: {e}")
            
            # Try to extract attributes manually
            try:
                response_dict = {
                    'output': getattr(response, 'output', []),
                    'usage': getattr(response, 'usage', None),
                    'response_id': getattr(response, 'response_id', ''),
                }
                return ModelResponse(**response_dict)
            except Exception as e:
                logger.debug(f"Could not extract attributes: {e}")
        
        logger.warning(f"Could not parse response of type: {type(response)}")
        return None
    
    except Exception as e:
        logger.error(f"Error parsing ModelResponse: {str(e)}", exc_info=True)
        return None


def extract_text_from_raw_response(response: Any) -> str:
    """
    Extract text from raw response object using attribute access
    Fallback when Pydantic parsing doesn't work
    
    Args:
        response: Raw response object
        
    Returns:
        str: Extracted text or empty string
    """
    try:
        logger.info(f"Attempting raw extraction from {type(response).__name__}")
        
        # Try to access output attribute
        if hasattr(response, 'output'):
            logger.info(f"Response has 'output' attribute")
            output = getattr(response, 'output', None)
            logger.info(f"Output type: {type(output).__name__}, value: {output}")
            
            if output:
                output_list = output if isinstance(output, list) else [output]
                logger.info(f"Processing {len(output_list)} output items")
                
                for i, output_msg in enumerate(output_list):
                    logger.info(f"Output item {i}: {type(output_msg).__name__}")
                    
                    if hasattr(output_msg, 'content'):
                        content = getattr(output_msg, 'content', None)
                        logger.info(f"Content type: {type(content).__name__}, value: {content}")
                        
                        if content:
                            content_list = content if isinstance(content, list) else [content]
                            logger.info(f"Processing {len(content_list)} content items")
                            
                            for j, content_item in enumerate(content_list):
                                logger.info(f"Content item {j}: {type(content_item).__name__}")
                                
                                if hasattr(content_item, 'text'):
                                    text = getattr(content_item, 'text', None)
                                    logger.info(f"Found text: {text}")
                                    
                                    if text:
                                        text_str = str(text).strip()
                                        if text_str:
                                            logger.info(f"Extracted text: {text_str[:100]}")
                                            return text_str
        
        logger.info("No text found in raw response")
        return ""
    
    except Exception as e:
        logger.error(f"Error extracting text from raw response: {e}", exc_info=True)
        return ""


def get_response_text(response: Any) -> str:
    """
    Extract text from any response format using Pydantic
    Multiple fallback strategies for robustness
    
    Args:
        response: Response object from agent
        
    Returns:
        str: Extracted text or empty string
    """
    try:
        if response is None:
            logger.warning("Response is None")
            return ""
        
        # Log response type and structure
        logger.info(f"=== RESPONSE EXTRACTION START ===")
        logger.info(f"Response type: {type(response).__name__}")
        
        # Try to get string representation
        try:
            response_str = str(response)[:300]
            logger.info(f"Response string: {response_str}")
        except Exception as e:
            logger.info(f"Could not convert response to string: {e}")
        
        # Strategy 1: Try to parse as ModelResponse
        logger.info("Strategy 1: Parsing as ModelResponse")
        model_response = parse_model_response(response)
        
        if model_response:
            text = model_response.get_text()
            logger.info(f"ModelResponse parsed, text: '{text}'")
            if text:
                logger.info(f"✅ Successfully extracted text using Pydantic: {text[:80]}")
                logger.info(f"=== RESPONSE EXTRACTION END ===")
                return text
        else:
            logger.info("Could not parse as ModelResponse")
        
        # Strategy 2: Try direct attribute access (raw object)
        logger.info("Strategy 2: Raw attribute access")
        text = extract_text_from_raw_response(response)
        logger.info(f"Raw extraction result: '{text}'")
        if text:
            logger.info(f"✅ Extracted text using raw attribute access: {text[:80]}")
            logger.info(f"=== RESPONSE EXTRACTION END ===")
            return text
        
        logger.warning(f"❌ Could not extract text from response - all strategies failed")
        logger.info(f"=== RESPONSE EXTRACTION END ===")
        return ""
    
    except Exception as e:
        logger.error(f"Error extracting text from response: {str(e)}", exc_info=True)
        logger.info(f"=== RESPONSE EXTRACTION END (ERROR) ===")
        return ""


def get_response_usage(response: Any) -> Optional[dict]:
    """
    Extract usage information from response using Pydantic
    
    Args:
        response: Response object from agent
        
    Returns:
        dict: Usage information or None
    """
    try:
        model_response = parse_model_response(response)
        
        if model_response and model_response.usage:
            return model_response.usage.model_dump()
        
        return None
    
    except Exception as e:
        logger.debug(f"Could not extract usage: {e}")
        return None


def get_response_id(response: Any) -> str:
    """
    Extract response ID from response
    
    Args:
        response: Response object from agent
        
    Returns:
        str: Response ID or empty string
    """
    try:
        model_response = parse_model_response(response)
        
        if model_response:
            return model_response.response_id
        
        if hasattr(response, 'response_id'):
            return str(response.response_id)
        
        return ""
    
    except Exception as e:
        logger.debug(f"Could not extract response ID: {e}")
        return ""


def validate_response(response: Any) -> bool:
    """
    Validate if response is a valid ModelResponse
    
    Args:
        response: Response object to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        model_response = parse_model_response(response)
        if model_response and model_response.get_text():
            return True
        return False
    except Exception:
        return False


def get_response_summary(response: Any) -> dict:
    """
    Get a summary of the response including text, usage, and ID
    
    Args:
        response: Response object from agent
        
    Returns:
        dict: Summary with text, usage, and response_id
    """
    try:
        model_response = parse_model_response(response)
        
        if model_response:
            return {
                'text': model_response.get_text(),
                'usage': model_response.usage.model_dump() if model_response.usage else None,
                'response_id': model_response.response_id,
                'valid': bool(model_response.get_text()),
            }
        
        return {
            'text': '',
            'usage': None,
            'response_id': '',
            'valid': False,
        }
    
    except Exception as e:
        logger.error(f"Error getting response summary: {str(e)}", exc_info=True)
        return {
            'text': '',
            'usage': None,
            'response_id': '',
            'valid': False,
        }
