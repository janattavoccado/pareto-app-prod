#!/usr/bin/env python3
"""
Debug script to analyze OpenAI Agents SDK response structure
Helps troubleshoot response extraction issues

Usage:
    python debug_agent_response.py

This script will:
1. Initialize the agents
2. Send a test message
3. Analyze the response structure in detail
4. Show all attributes and nested values
5. Test extraction methods
"""

import asyncio
import json
import logging
from typing import Any
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import agent components
from pareto_agents.agents import process_message_sync
from pareto_agents.agent_response_models import (
    parse_agent_response,
    extract_agent_text,
    ModelResponse
)


def analyze_response_structure(response: Any, indent: int = 0) -> None:
    """
    Recursively analyze and print response structure
    
    Args:
        response: Response object to analyze
        indent: Indentation level for printing
    """
    prefix = "  " * indent
    
    print(f"\n{prefix}=== RESPONSE STRUCTURE ANALYSIS ===")
    print(f"{prefix}Type: {type(response).__name__}")
    print(f"{prefix}Module: {type(response).__module__}")
    
    # Print string representation
    try:
        response_str = str(response)
        if len(response_str) > 200:
            print(f"{prefix}String (truncated): {response_str[:200]}...")
        else:
            print(f"{prefix}String: {response_str}")
    except Exception as e:
        print(f"{prefix}String representation failed: {e}")
    
    # Print attributes
    if hasattr(response, '__dict__'):
        print(f"\n{prefix}Attributes:")
        for attr_name, attr_value in response.__dict__.items():
            print(f"{prefix}  - {attr_name}: {type(attr_value).__name__}")
            
            # Analyze nested structures
            if hasattr(attr_value, '__iter__') and not isinstance(attr_value, (str, bytes)):
                try:
                    attr_list = list(attr_value) if not isinstance(attr_value, list) else attr_value
                    print(f"{prefix}    (list with {len(attr_list)} items)")
                    
                    if attr_list and len(attr_list) > 0:
                        first_item = attr_list[0]
                        print(f"{prefix}    First item type: {type(first_item).__name__}")
                        
                        if hasattr(first_item, '__dict__'):
                            for sub_attr, sub_value in first_item.__dict__.items():
                                print(f"{prefix}      - {sub_attr}: {type(sub_value).__name__}")
                                
                                # Go one level deeper for content
                                if sub_attr == 'content' and hasattr(sub_value, '__iter__'):
                                    try:
                                        content_list = list(sub_value) if not isinstance(sub_value, list) else sub_value
                                        print(f"{prefix}        (list with {len(content_list)} items)")
                                        if content_list:
                                            print(f"{prefix}        First content type: {type(content_list[0]).__name__}")
                                            if hasattr(content_list[0], '__dict__'):
                                                for content_attr, content_value in content_list[0].__dict__.items():
                                                    print(f"{prefix}          - {content_attr}: {type(content_value).__name__}")
                                                    if content_attr == 'text':
                                                        print(f"{prefix}            Value: {content_value}")
                                    except Exception as e:
                                        print(f"{prefix}        Error analyzing content: {e}")
                except Exception as e:
                    print(f"{prefix}    Error analyzing list: {e}")
            
            # Print value if it's simple
            elif isinstance(attr_value, (str, int, float, bool, type(None))):
                if isinstance(attr_value, str) and len(attr_value) > 100:
                    print(f"{prefix}    Value: {attr_value[:100]}...")
                else:
                    print(f"{prefix}    Value: {attr_value}")
    
    # Try to convert to dict
    if hasattr(response, 'model_dump'):
        print(f"\n{prefix}Model dump available:")
        try:
            dumped = response.model_dump()
            print(json.dumps(dumped, indent=2, default=str)[:500])
        except Exception as e:
            print(f"{prefix}  Error: {e}")
    
    print(f"\n{prefix}=== END ANALYSIS ===\n")


def test_extraction_methods(response: Any) -> None:
    """
    Test various extraction methods on the response
    
    Args:
        response: Response object to test
    """
    print("\n=== TESTING EXTRACTION METHODS ===\n")
    
    # Test 1: Direct attribute access
    print("1. Direct attribute access:")
    if hasattr(response, 'output'):
        print(f"   - Has 'output': {type(response.output)}")
        if response.output:
            print(f"   - Output length: {len(response.output)}")
            if len(response.output) > 0:
                first = response.output[0]
                print(f"   - First output type: {type(first).__name__}")
                if hasattr(first, 'content'):
                    print(f"   - Has 'content': {type(first.content)}")
                    if first.content and len(first.content) > 0:
                        print(f"   - First content type: {type(first.content[0]).__name__}")
                        if hasattr(first.content[0], 'text'):
                            print(f"   - Text value: {first.content[0].text}")
    else:
        print("   - No 'output' attribute")
    
    # Test 2: Pydantic parsing
    print("\n2. Pydantic model parsing:")
    try:
        model_response = parse_agent_response(response)
        if model_response:
            print(f"   ✅ Successfully parsed as ModelResponse")
            print(f"   - Type: {type(model_response)}")
            print(f"   - Output count: {len(model_response.output)}")
            
            # Test get_text method
            text = model_response.get_text()
            print(f"   - get_text() result: '{text}'")
            
            # Test get_all_text method
            all_text = model_response.get_all_text()
            print(f"   - get_all_text() result: '{all_text}'")
        else:
            print(f"   ❌ Failed to parse as ModelResponse")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Extraction function
    print("\n3. Extract agent text function:")
    try:
        text = extract_agent_text(response)
        if text:
            print(f"   ✅ Successfully extracted: '{text}'")
        else:
            print(f"   ❌ Extracted empty string")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n=== END EXTRACTION TESTS ===\n")


async def test_agent_message() -> None:
    """
    Send a test message through the agent and analyze the response
    """
    print("\n" + "="*70)
    print("TESTING AGENT MESSAGE PROCESSING")
    print("="*70 + "\n")
    
    # Test message
    test_message = "hello"
    test_phone = "+46735408023"
    test_user_data = {
        "first_name": "Jan",
        "last_name": "Nylen",
        "email": "jan.avoccado.pareto@gmail.com",
        "phone_number": test_phone,
        "enabled": True,
    }
    
    print(f"Test message: '{test_message}'")
    print(f"Test phone: '{test_phone}'")
    print(f"Test user: {test_user_data['first_name']} {test_user_data['last_name']}\n")
    
    try:
        # Process message
        print("Processing message through agent...")
        result = process_message_sync(test_message, test_phone, test_user_data)
        
        print(f"\nResult type: {type(result)}")
        print(f"Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
        
        if isinstance(result, dict):
            print(f"\nResult content:")
            for key, value in result.items():
                if key == 'raw_result':
                    print(f"  {key}: {type(value).__name__} (analyzing below)")
                elif isinstance(value, str):
                    if len(value) > 100:
                        print(f"  {key}: {value[:100]}...")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {key}: {value}")
            
            # Analyze raw_result if present
            if 'raw_result' in result:
                print("\nAnalyzing raw_result:")
                analyze_response_structure(result['raw_result'])
                test_extraction_methods(result['raw_result'])
    
    except Exception as e:
        logger.error(f"Error testing agent: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")


def main() -> None:
    """Main debug script entry point"""
    print("\n" + "="*70)
    print("PARETO AGENT RESPONSE DEBUG SCRIPT")
    print("="*70)
    
    try:
        # Run async test
        asyncio.run(test_agent_message())
        
        print("\n" + "="*70)
        print("DEBUG COMPLETE")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"Debug script error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}\n")


if __name__ == "__main__":
    main()
