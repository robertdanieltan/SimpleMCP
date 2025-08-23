"""
Gemini LLM Provider

This module implements the Gemini provider for the LLM abstraction layer,
providing Google Gemini API integration with comprehensive error handling.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import time

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core import exceptions as google_exceptions

from ..base import LLMProvider, LLMResponse, ProviderCapabilities, ProviderStatus
from ..exceptions import (
    ProviderInitializationError,
    ProviderConfigurationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderNetworkError,
    ProviderModelError,
    ProviderResponseError,
    ProviderUnavailableError
)
from ..error_handler import get_error_handler, create_error_context, FallbackStrategy
from ..logging_config import get_provider_logger

logger = get_provider_logger("gemini")


class GeminiProvider(LLMProvider):
    """
    Gemini LLM Provider implementation
    
    Provides Google Gemini API integration with the standardized LLM interface,
    including comprehensive error handling, health monitoring, and fallback capabilities.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Gemini provider with configuration
        
        Args:
            config: Configuration dictionary containing:
                - api_key: Gemini API key
                - model: Model name (default: 'gemini-pro')
                - enabled: Whether provider is enabled
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model_name = config.get('model', 'gemini-pro')
        self.enabled = config.get('enabled', bool(self.api_key))
        self.model = None
        
        # Safety settings for content generation
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        
        logger.info(f"Gemini provider initialized with model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """
        Initialize the Gemini provider
        
        Returns:
            True if initialization successful, False otherwise
            
        Raises:
            ProviderConfigurationError: If configuration is invalid
            ProviderAuthenticationError: If API key is invalid
            ProviderInitializationError: If initialization fails
        """
        try:
            # Validate configuration
            if not self._validate_config(['api_key']):
                raise ProviderConfigurationError(
                    "Missing required configuration: api_key",
                    provider="gemini"
                )
            
            if not self.enabled:
                logger.info("Gemini provider is disabled")
                return False
            
            # Configure Gemini API
            genai.configure(api_key=self.api_key)
            
            # Initialize model
            self.model = genai.GenerativeModel(self.model_name)
            
            # Test the connection with a simple health check
            await self._test_connection()
            
            self._is_initialized = True
            self._update_health_status(ProviderStatus.AVAILABLE)
            logger.info("Gemini provider initialized successfully")
            return True
            
        except ProviderConfigurationError:
            raise
        except google_exceptions.Unauthenticated as e:
            error_msg = "Invalid Gemini API key"
            logger.error(f"Gemini authentication failed: {e}")
            raise ProviderAuthenticationError(error_msg, provider="gemini")
        except Exception as e:
            error_msg = f"Failed to initialize Gemini provider: {str(e)}"
            logger.error(error_msg)
            raise ProviderInitializationError(error_msg, provider="gemini")
    
    async def _test_connection(self):
        """Test connection to Gemini API with a simple request"""
        try:
            test_response = self.model.generate_content(
                "Hello",
                safety_settings=self.safety_settings
            )
            if not test_response.text:
                raise ProviderInitializationError(
                    "Gemini API test failed - no response received",
                    provider="gemini"
                )
        except Exception as e:
            raise ProviderInitializationError(
                f"Gemini API connection test failed: {str(e)}",
                provider="gemini"
            )
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response using Gemini API
        
        Args:
            prompt: Input prompt for the LLM
            context: Optional context information
            max_tokens: Maximum tokens in response (note: Gemini uses different token limits)
            temperature: Response randomness (0.0-1.0)
            **kwargs: Additional Gemini-specific parameters
            
        Returns:
            LLMResponse with generated content or error information
        """
        error_handler = get_error_handler()
        error_context = create_error_context(
            provider_name="gemini",
            operation="generate_response",
            user_input=prompt,
            additional_context={"max_tokens": max_tokens, "temperature": temperature}
        )
        
        if not self.is_available():
            error = ProviderUnavailableError(
                "Gemini provider is not available. Please check configuration.",
                provider="gemini"
            )
            return error_handler.create_error_response(error, error_context)
        
        try:
            with error_handler.handle_provider_operation(error_context, FallbackStrategy.RULE_BASED):
                # Log request
                logger.log_request(prompt, request_id=error_context.request_id)
                
                # Prepare the full prompt with context
                full_prompt = self._prepare_prompt(prompt, context)
                
                # Generate response with error handling
                start_time = time.time()
                response = await self._generate_with_retry(full_prompt, **kwargs)
                response_time = int((time.time() - start_time) * 1000)
                
                if response.text:
                    # Approximate token count (Gemini doesn't provide exact count)
                    tokens_used = len(response.text.split())
                    
                    # Log successful response
                    logger.log_response(
                        response.text.strip(),
                        success=True,
                        response_time_ms=response_time,
                        tokens_used=tokens_used,
                        model=self.model_name,
                        request_id=error_context.request_id
                    )
                    
                    return LLMResponse(
                        success=True,
                        response=response.text.strip(),
                        source="gemini",
                        model=self.model_name,
                        tokens_used=tokens_used
                    )
                else:
                    error = ProviderResponseError(
                        "AI service returned an empty response",
                        provider="gemini"
                    )
                    logger.log_error(error, "generate_response", request_id=error_context.request_id)
                    return error_handler.create_error_response(error, error_context)
                    
        except (ProviderRateLimitError, ProviderAuthenticationError, ProviderNetworkError) as e:
            logger.log_error(e, "generate_response", request_id=error_context.request_id)
            return error_handler.create_error_response(e, error_context)
        except Exception as e:
            # Convert unexpected errors to provider errors
            provider_error = ProviderResponseError(
                f"Unexpected error: {str(e)}",
                provider="gemini",
                details={"original_exception": type(e).__name__}
            )
            logger.log_error(provider_error, "generate_response", request_id=error_context.request_id)
            return error_handler.create_error_response(provider_error, error_context)
    
    async def _generate_with_retry(self, prompt: str, max_retries: int = 3, **kwargs):
        """Generate content with retry logic for transient errors"""
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    safety_settings=self.safety_settings,
                    **kwargs
                )
                return response
                
            except google_exceptions.ResourceExhausted as e:
                if attempt == max_retries - 1:
                    raise ProviderRateLimitError(
                        "Rate limit exceeded",
                        provider="gemini",
                        retry_after=60
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except google_exceptions.Unauthenticated as e:
                raise ProviderAuthenticationError(
                    "Invalid API key",
                    provider="gemini"
                )
                
            except (google_exceptions.DeadlineExceeded, google_exceptions.ServiceUnavailable) as e:
                if attempt == max_retries - 1:
                    raise ProviderNetworkError(
                        f"Network error: {str(e)}",
                        provider="gemini"
                    )
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
    
    def _prepare_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare the full prompt with context and system instructions
        
        Args:
            prompt: User's input prompt
            context: Optional context information
            
        Returns:
            Formatted prompt string
        """
        system_prompt = """You are an AI assistant that helps with task and project management. 
You can create, update, list, and delete tasks and projects through an MCP service.

Key capabilities:
- Natural language understanding for task management requests
- Project organization and planning
- Task prioritization and status tracking
- Clear, helpful responses

Always be helpful, concise, and focused on task/project management activities."""
        
        context_str = ""
        if context:
            context_str = f"\nContext: {context}"
        
        return f"{system_prompt}\n\nUser request: {prompt}{context_str}"
    
    async def analyze_intent(
        self, 
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent for task/project management operations
        
        Args:
            user_input: User's natural language input
            context: Optional context information
            
        Returns:
            Intent analysis results with standardized format
        """
        error_handler = get_error_handler()
        error_context = create_error_context(
            provider_name="gemini",
            operation="analyze_intent",
            user_input=user_input
        )
        
        if not self.is_available():
            logger.log_operation(
                logging.WARNING,
                "analyze_intent",
                "Gemini provider unavailable for intent analysis",
                success=False,
                request_id=error_context.request_id
            )
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "action": "error",
                "error": "Gemini provider unavailable"
            }
        
        intent_prompt = f"""
Analyze this user request for task/project management intent:
"{user_input}"

Identify:
1. Primary intent (create_task, list_tasks, update_task, delete_task, create_project, list_projects, general_query)
2. Confidence level (0.0-1.0)
3. Key entities (task names, project names, priorities, statuses, dates)
4. Required action

Respond in this exact JSON format:
{{
    "intent": "intent_name",
    "confidence": 0.9,
    "entities": {{"key": "value"}},
    "action": "action_to_take"
}}
"""
        
        try:
            with error_handler.handle_provider_operation(error_context, FallbackStrategy.RULE_BASED):
                response = await self.generate_response(intent_prompt, context)
                if response.success:
                    # Try to parse JSON from response
                    try:
                        intent_data = json.loads(response.response)
                        logger.log_operation(
                            logging.INFO,
                            "analyze_intent",
                            f"Intent analysis successful: {intent_data.get('intent', 'unknown')}",
                            success=True,
                            request_id=error_context.request_id,
                            intent=intent_data.get('intent'),
                            confidence=intent_data.get('confidence')
                        )
                        return intent_data
                    except json.JSONDecodeError:
                        logger.log_operation(
                            logging.WARNING,
                            "analyze_intent",
                            "Failed to parse intent analysis JSON, using fallback",
                            success=False,
                            request_id=error_context.request_id,
                            error_type="JSONDecodeError"
                        )
                        return self._fallback_intent_analysis(user_input)
                else:
                    logger.log_operation(
                        logging.WARNING,
                        "analyze_intent",
                        f"Intent analysis failed: {response.error}",
                        success=False,
                        request_id=error_context.request_id,
                        error_code=response.error
                    )
                    return self._fallback_intent_analysis(user_input)
                    
        except Exception as e:
            logger.log_error(e, "analyze_intent", request_id=error_context.request_id)
            return self._fallback_intent_analysis(user_input)
    
    def _fallback_intent_analysis(self, user_input: str) -> Dict[str, Any]:
        """
        Simple rule-based intent analysis fallback
        
        Args:
            user_input: User's input
            
        Returns:
            Basic intent analysis
        """
        user_lower = user_input.lower()
        
        # Simple keyword matching
        if any(word in user_lower for word in ["create", "add", "new"]):
            if "project" in user_lower:
                return {
                    "intent": "create_project",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "create_project"
                }
            else:
                return {
                    "intent": "create_task",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "create_task"
                }
        elif any(word in user_lower for word in ["list", "show", "get", "view"]):
            if "project" in user_lower:
                return {
                    "intent": "list_projects",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "list_projects"
                }
            else:
                return {
                    "intent": "list_tasks",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "list_tasks"
                }
        elif any(word in user_lower for word in ["update", "modify", "change", "edit"]):
            return {
                "intent": "update_task",
                "confidence": 0.6,
                "entities": {},
                "action": "update_task"
            }
        elif any(word in user_lower for word in ["delete", "remove", "cancel"]):
            return {
                "intent": "delete_task",
                "confidence": 0.6,
                "entities": {},
                "action": "delete_task"
            }
        else:
            return {
                "intent": "general_query",
                "confidence": 0.5,
                "entities": {},
                "action": "general_response"
            }
    
    def is_available(self) -> bool:
        """
        Check if Gemini provider is available and configured
        
        Returns:
            True if provider is ready to use, False otherwise
        """
        return (
            self.enabled and 
            self._is_initialized and 
            self.model is not None and
            self._health_status == ProviderStatus.AVAILABLE
        )
    
    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get Gemini provider capabilities and limitations
        
        Returns:
            ProviderCapabilities object with Gemini specifications
        """
        return ProviderCapabilities(
            max_tokens=30720,  # Gemini Pro context window
            supports_streaming=False,  # Not implemented in this version
            supports_functions=False,  # Not implemented in this version
            supported_languages=[
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
                "ar", "hi", "th", "vi", "id", "ms", "tl", "sw"
            ],
            context_window=30720,
            supports_images=True,  # Gemini Pro Vision capability
            supports_audio=False,
            rate_limit_rpm=60,  # Approximate rate limit
            rate_limit_tpm=32000  # Approximate token limit per minute
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on Gemini provider
        
        Returns:
            Health check results with standardized format
        """
        start_time = time.time()
        
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "provider": "gemini",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider is disabled in configuration"},
                    "response_time_ms": None,
                    "error": None
                }
            
            if not self._is_initialized:
                return {
                    "status": "unhealthy",
                    "provider": "gemini",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider not initialized"},
                    "response_time_ms": None,
                    "error": "Provider not initialized"
                }
            
            # Perform a simple test request
            test_response = self.model.generate_content(
                "Health check test",
                safety_settings=self.safety_settings
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            if test_response.text:
                self._update_health_status(ProviderStatus.AVAILABLE)
                return {
                    "status": "healthy",
                    "provider": "gemini",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "model": self.model_name,
                        "api_configured": bool(self.api_key),
                        "test_response_length": len(test_response.text)
                    },
                    "response_time_ms": response_time,
                    "error": None
                }
            else:
                self._update_health_status(ProviderStatus.ERROR)
                return {
                    "status": "degraded",
                    "provider": "gemini",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Empty response from test request"},
                    "response_time_ms": response_time,
                    "error": "Empty response from health check"
                }
                
        except google_exceptions.Unauthenticated:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "gemini",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": "Authentication failed"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": "Invalid API key"
            }
            
        except google_exceptions.ResourceExhausted:
            self._update_health_status(ProviderStatus.RATE_LIMITED)
            return {
                "status": "degraded",
                "provider": "gemini",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": "Rate limit exceeded"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": "Rate limit exceeded"
            }
            
        except Exception as e:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "gemini",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Health check failed: {str(e)}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
    
    async def cleanup(self):
        """
        Cleanup Gemini provider resources
        
        Gemini doesn't require explicit cleanup, but we reset the state
        """
        self.model = None
        self._is_initialized = False
        self._update_health_status(ProviderStatus.UNAVAILABLE)
        logger.info("Gemini provider cleaned up")