"""
LLM Provider Utilities

This module provides common utility functions for LLM providers,
including response formatting, error handling, and validation helpers.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


def sanitize_api_key(api_key: str, visible_chars: int = 4) -> str:
    """
    Sanitize API key for logging by showing only first few characters
    
    Args:
        api_key: The API key to sanitize
        visible_chars: Number of characters to show at the beginning
        
    Returns:
        Sanitized API key string
    """
    if not api_key:
        return "None"
    
    if len(api_key) <= visible_chars:
        return "*" * len(api_key)
    
    return api_key[:visible_chars] + "*" * (len(api_key) - visible_chars)


def validate_temperature(temperature: float) -> float:
    """
    Validate and clamp temperature value to valid range
    
    Args:
        temperature: Temperature value to validate
        
    Returns:
        Clamped temperature value between 0.0 and 1.0
    """
    return max(0.0, min(1.0, temperature))


def validate_max_tokens(max_tokens: int, provider_limit: int) -> int:
    """
    Validate and clamp max_tokens to provider limits
    
    Args:
        max_tokens: Requested max tokens
        provider_limit: Provider's maximum token limit
        
    Returns:
        Validated max tokens value
    """
    return max(1, min(max_tokens, provider_limit))


def extract_json_from_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from response text, handling various formats
    
    Args:
        response_text: Response text that may contain JSON
        
    Returns:
        Parsed JSON dictionary or None if no valid JSON found
    """
    # Try to parse the entire response as JSON first
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass
    
    # Look for JSON blocks in markdown format
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_pattern, response_text, re.DOTALL | re.IGNORECASE)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # Look for JSON objects without markdown formatting
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, response_text)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    return None


def format_error_message(error: Exception, provider: str) -> str:
    """
    Format error message for user-friendly display
    
    Args:
        error: Exception that occurred
        provider: Name of the provider where error occurred
        
    Returns:
        Formatted error message
    """
    error_type = type(error).__name__
    
    # Common error message mappings
    error_messages = {
        "ConnectionError": f"Unable to connect to {provider} service. Please check your internet connection.",
        "TimeoutError": f"{provider} service is taking too long to respond. Please try again.",
        "AuthenticationError": f"Authentication failed for {provider}. Please check your API key.",
        "RateLimitError": f"{provider} rate limit exceeded. Please wait before making more requests.",
        "ModelError": f"The specified model is not available in {provider}.",
        "ValidationError": f"Invalid request parameters for {provider}.",
    }
    
    return error_messages.get(error_type, f"An error occurred with {provider}: {str(error)}")


def create_fallback_intent_analysis(user_input: str) -> Dict[str, Any]:
    """
    Create fallback intent analysis using simple keyword matching
    
    Args:
        user_input: User's natural language input
        
    Returns:
        Basic intent analysis dictionary
    """
    user_lower = user_input.lower()
    
    # Define keyword patterns for different intents
    intent_patterns = {
        "create_task": ["create", "add", "new", "make"],
        "list_tasks": ["list", "show", "get", "view", "display"],
        "update_task": ["update", "modify", "change", "edit", "alter"],
        "delete_task": ["delete", "remove", "cancel", "drop"],
        "create_project": ["create project", "new project", "add project"],
        "list_projects": ["list projects", "show projects", "view projects"],
    }
    
    # Check for project-specific keywords
    has_project_keyword = "project" in user_lower
    
    # Find matching intent
    matched_intent = "general_query"
    confidence = 0.5
    
    for intent, keywords in intent_patterns.items():
        for keyword in keywords:
            if keyword in user_lower:
                # Adjust intent based on project keyword
                if "project" in intent and not has_project_keyword:
                    continue
                if "project" not in intent and intent.startswith(("create", "list")) and has_project_keyword:
                    matched_intent = intent.replace("task", "project")
                else:
                    matched_intent = intent
                confidence = 0.7
                break
        if confidence > 0.5:
            break
    
    # Extract basic entities
    entities = {}
    if "priority" in user_lower:
        if "high" in user_lower:
            entities["priority"] = "high"
        elif "low" in user_lower:
            entities["priority"] = "low"
        else:
            entities["priority"] = "medium"
    
    if "urgent" in user_lower:
        entities["priority"] = "high"
    
    return {
        "intent": matched_intent,
        "confidence": confidence,
        "entities": entities,
        "action": matched_intent,
        "source": "fallback_analysis"
    }


def estimate_token_count(text: str) -> int:
    """
    Estimate token count for text (rough approximation)
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    # Rough approximation: 1 token ≈ 4 characters for English text
    return max(1, len(text) // 4)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def create_health_check_response(
    provider_name: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    response_time_ms: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create standardized health check response
    
    Args:
        provider_name: Name of the provider
        status: Health status ("healthy", "unhealthy", "degraded")
        details: Additional details about the health check
        error: Error message if unhealthy
        response_time_ms: Response time in milliseconds
        
    Returns:
        Standardized health check response
    """
    return {
        "status": status,
        "provider": provider_name,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details or {},
        "response_time_ms": response_time_ms,
        "error": error
    }


def log_provider_interaction(
    provider_name: str,
    operation: str,
    success: bool,
    duration_ms: Optional[int] = None,
    error: Optional[str] = None,
    tokens_used: Optional[int] = None
):
    """
    Log provider interaction for monitoring and debugging
    
    Args:
        provider_name: Name of the provider
        operation: Operation performed (e.g., "generate_response", "analyze_intent")
        success: Whether the operation was successful
        duration_ms: Operation duration in milliseconds
        error: Error message if operation failed
        tokens_used: Number of tokens used in the operation
    """
    log_data = {
        "provider": provider_name,
        "operation": operation,
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    
    if tokens_used is not None:
        log_data["tokens_used"] = tokens_used
    
    if error:
        log_data["error"] = error
    
    if success:
        logger.info(f"Provider interaction successful: {log_data}")
    else:
        logger.error(f"Provider interaction failed: {log_data}")


def merge_contexts(base_context: Optional[Dict[str, Any]], additional_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Merge two context dictionaries, with additional_context taking precedence
    
    Args:
        base_context: Base context dictionary
        additional_context: Additional context to merge
        
    Returns:
        Merged context dictionary
    """
    merged = base_context.copy() if base_context else {}
    
    if additional_context:
        merged.update(additional_context)
    
    return merged