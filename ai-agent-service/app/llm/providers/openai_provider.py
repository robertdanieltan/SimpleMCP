"""
OpenAI LLM Provider

This module implements the OpenAI provider for the LLM abstraction layer,
providing OpenAI API integration with comprehensive error handling and rate limiting.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import time

import openai
from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion

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

logger = get_provider_logger("openai")


class OpenAIProvider(LLMProvider):
    """
    OpenAI LLM Provider implementation
    
    Provides OpenAI API integration with the standardized LLM interface,
    including comprehensive error handling, rate limiting, and health monitoring.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OpenAI provider with configuration
        
        Args:
            config: Configuration dictionary containing:
                - api_key: OpenAI API key
                - model: Model name (default: 'gpt-3.5-turbo')
                - enabled: Whether provider is enabled
                - organization: Optional organization ID
                - base_url: Optional base URL for API
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model_name = config.get('model', 'gpt-3.5-turbo')
        self.enabled = config.get('enabled', bool(self.api_key))
        self.organization = config.get('organization')
        self.base_url = config.get('base_url')
        
        self.client = None
        self.async_client = None
        
        # Rate limiting tracking
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window = 60  # 1 minute window
        self._max_requests_per_minute = 3500  # Conservative limit for GPT-3.5-turbo
        
        logger.info(f"OpenAI provider initialized with model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """
        Initialize the OpenAI provider
        
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
                    provider="openai"
                )
            
            if not self.enabled:
                logger.info("OpenAI provider is disabled")
                return False
            
            # Initialize OpenAI clients
            client_kwargs = {
                'api_key': self.api_key,
            }
            
            if self.organization:
                client_kwargs['organization'] = self.organization
            if self.base_url:
                client_kwargs['base_url'] = self.base_url
            
            self.client = OpenAI(**client_kwargs)
            self.async_client = AsyncOpenAI(**client_kwargs)
            
            # Test the connection with a simple health check
            await self._test_connection()
            
            self._is_initialized = True
            self._update_health_status(ProviderStatus.AVAILABLE)
            logger.info("OpenAI provider initialized successfully")
            return True
            
        except ProviderConfigurationError:
            raise
        except openai.AuthenticationError as e:
            error_msg = "Invalid OpenAI API key"
            logger.error(f"OpenAI authentication failed: {e}")
            raise ProviderAuthenticationError(error_msg, provider="openai")
        except Exception as e:
            error_msg = f"Failed to initialize OpenAI provider: {str(e)}"
            logger.error(error_msg)
            raise ProviderInitializationError(error_msg, provider="openai")
    
    async def _test_connection(self):
        """Test connection to OpenAI API with a simple request"""
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                temperature=0.0
            )
            if not response.choices or not response.choices[0].message.content:
                raise ProviderInitializationError(
                    "OpenAI API test failed - no response received",
                    provider="openai"
                )
        except Exception as e:
            raise ProviderInitializationError(
                f"OpenAI API connection test failed: {str(e)}",
                provider="openai"
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
        Generate response using OpenAI API
        
        Args:
            prompt: Input prompt for the LLM
            context: Optional context information
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0.0-1.0)
            **kwargs: Additional OpenAI-specific parameters
            
        Returns:
            LLMResponse with generated content or error information
        """
        error_handler = get_error_handler()
        error_context = create_error_context(
            provider_name="openai",
            operation="generate_response",
            user_input=prompt,
            additional_context={"max_tokens": max_tokens, "temperature": temperature}
        )
        
        if not self.is_available():
            error = ProviderUnavailableError(
                "OpenAI provider is not available. Please check configuration.",
                provider="openai"
            )
            return error_handler.create_error_response(error, error_context)
        
        try:
            with error_handler.handle_provider_operation(error_context, FallbackStrategy.RULE_BASED):
                # Log request
                logger.log_request(prompt, request_id=error_context.request_id)
                
                # Check rate limits
                await self._check_rate_limit()
                
                # Prepare messages with context
                messages = self._prepare_messages(prompt, context)
                
                # Generate response with error handling
                start_time = time.time()
                response = await self._generate_with_retry(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                response_time = int((time.time() - start_time) * 1000)
                
                if response.choices and response.choices[0].message.content:
                    # Log successful response
                    logger.log_response(
                        response.choices[0].message.content.strip(),
                        success=True,
                        response_time_ms=response_time,
                        tokens_used=response.usage.total_tokens if response.usage else None,
                        model=response.model,
                        request_id=error_context.request_id
                    )
                    
                    return LLMResponse(
                        success=True,
                        response=response.choices[0].message.content.strip(),
                        source="openai",
                        model=response.model,
                        tokens_used=response.usage.total_tokens if response.usage else None
                    )
                else:
                    error = ProviderResponseError(
                        "AI service returned an empty response",
                        provider="openai"
                    )
                    logger.log_error(error, "generate_response", request_id=error_context.request_id)
                    return error_handler.create_error_response(error, error_context)
                    
        except (ProviderRateLimitError, ProviderAuthenticationError, ProviderNetworkError, ProviderModelError) as e:
            logger.log_error(e, "generate_response", request_id=error_context.request_id)
            return error_handler.create_error_response(e, error_context)
        except Exception as e:
            # Convert unexpected errors to provider errors
            provider_error = ProviderResponseError(
                f"Unexpected error: {str(e)}",
                provider="openai",
                details={"original_exception": type(e).__name__}
            )
            logger.log_error(provider_error, "generate_response", request_id=error_context.request_id)
            return error_handler.create_error_response(provider_error, error_context)
    
    async def _generate_with_retry(
        self, 
        messages: List[Dict[str, str]], 
        max_retries: int = 3, 
        **kwargs
    ) -> ChatCompletion:
        """Generate content with retry logic for transient errors"""
        for attempt in range(max_retries):
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    **kwargs
                )
                return response
                
            except openai.RateLimitError as e:
                if attempt == max_retries - 1:
                    # Extract retry-after from headers if available
                    retry_after = getattr(e, 'retry_after', 60)
                    raise ProviderRateLimitError(
                        "Rate limit exceeded",
                        provider="openai",
                        retry_after=retry_after
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except openai.AuthenticationError as e:
                raise ProviderAuthenticationError(
                    "Invalid API key",
                    provider="openai"
                )
                
            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                if attempt == max_retries - 1:
                    raise ProviderNetworkError(
                        f"Network error: {str(e)}",
                        provider="openai"
                    )
                await asyncio.sleep(2 ** attempt)
                
            except openai.BadRequestError as e:
                # Don't retry bad requests
                raise ProviderModelError(
                    f"Invalid request: {str(e)}",
                    provider="openai"
                )
                
            except openai.InternalServerError as e:
                if attempt == max_retries - 1:
                    raise ProviderResponseError(
                        f"Server error: {str(e)}",
                        provider="openai"
                    )
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
    
    def _prepare_messages(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        Prepare messages for OpenAI chat completion format
        
        Args:
            prompt: User's input prompt
            context: Optional context information
            
        Returns:
            List of message dictionaries for OpenAI API
        """
        system_message = {
            "role": "system",
            "content": """You are an AI assistant that helps with task and project management. 
You can create, update, list, and delete tasks and projects through an MCP service.

Key capabilities:
- Natural language understanding for task management requests
- Project organization and planning
- Task prioritization and status tracking
- Clear, helpful responses

Always be helpful, concise, and focused on task/project management activities."""
        }
        
        user_content = prompt
        if context:
            user_content = f"{prompt}\n\nContext: {context}"
        
        user_message = {
            "role": "user",
            "content": user_content
        }
        
        return [system_message, user_message]
    
    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self._last_request_time > self._rate_limit_window:
            self._request_count = 0
            self._last_request_time = current_time
        
        # Check if we're over the limit
        if self._request_count >= self._max_requests_per_minute:
            wait_time = self._rate_limit_window - (current_time - self._last_request_time)
            if wait_time > 0:
                raise ProviderRateLimitError(
                    "Local rate limit exceeded",
                    provider="openai",
                    retry_after=int(wait_time)
                )
        
        self._request_count += 1
    
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
        if not self.is_available():
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "action": "error",
                "error": "OpenAI provider unavailable"
            }
        
        intent_messages = [
            {
                "role": "system",
                "content": """You are an intent analysis system for task/project management. 
Analyze user requests and respond with JSON only.

Identify:
1. Primary intent (create_task, list_tasks, update_task, delete_task, create_project, list_projects, general_query)
2. Confidence level (0.0-1.0)
3. Key entities (task names, project names, priorities, statuses, dates)
4. Required action

Respond ONLY with valid JSON in this exact format:
{
    "intent": "intent_name",
    "confidence": 0.9,
    "entities": {"key": "value"},
    "action": "action_to_take"
}"""
            },
            {
                "role": "user",
                "content": f"Analyze this request: {user_input}"
            }
        ]
        
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=intent_messages,
                max_tokens=200,
                temperature=0.1  # Low temperature for consistent JSON output
            )
            
            if response.choices and response.choices[0].message.content:
                try:
                    intent_data = json.loads(response.choices[0].message.content.strip())
                    return intent_data
                except json.JSONDecodeError:
                    logger.warning("Failed to parse intent analysis JSON from OpenAI")
                    return self._fallback_intent_analysis(user_input)
            else:
                logger.warning("OpenAI returned empty response for intent analysis")
                return self._fallback_intent_analysis(user_input)
                
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
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
        Check if OpenAI provider is available and configured
        
        Returns:
            True if provider is ready to use, False otherwise
        """
        return (
            self.enabled and 
            self._is_initialized and 
            self.async_client is not None and
            self._health_status == ProviderStatus.AVAILABLE
        )
    
    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get OpenAI provider capabilities and limitations
        
        Returns:
            ProviderCapabilities object with OpenAI specifications
        """
        # Capabilities vary by model, these are for GPT-3.5-turbo
        if "gpt-4" in self.model_name.lower():
            max_tokens = 8192
            context_window = 8192
            cost_per_token = 0.00003  # Approximate cost per token for GPT-4
            rate_limit_rpm = 200
            rate_limit_tpm = 40000
        else:  # GPT-3.5-turbo
            max_tokens = 4096
            context_window = 4096
            cost_per_token = 0.000002  # Approximate cost per token for GPT-3.5-turbo
            rate_limit_rpm = 3500
            rate_limit_tpm = 90000
        
        return ProviderCapabilities(
            max_tokens=max_tokens,
            supports_streaming=True,  # OpenAI supports streaming
            supports_functions=True,  # OpenAI supports function calling
            supported_languages=[
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
                "ar", "hi", "th", "vi", "id", "ms", "tl", "sw", "nl", "pl",
                "tr", "he", "sv", "da", "no", "fi", "cs", "hu", "ro", "bg"
            ],
            cost_per_token=cost_per_token,
            context_window=context_window,
            supports_images=False,  # Standard models don't support images
            supports_audio=False,
            rate_limit_rpm=rate_limit_rpm,
            rate_limit_tpm=rate_limit_tpm
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on OpenAI provider
        
        Returns:
            Health check results with standardized format
        """
        start_time = time.time()
        
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "provider": "openai",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider is disabled in configuration"},
                    "response_time_ms": None,
                    "error": None
                }
            
            if not self._is_initialized:
                return {
                    "status": "unhealthy",
                    "provider": "openai",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider not initialized"},
                    "response_time_ms": None,
                    "error": "Provider not initialized"
                }
            
            # Perform a simple test request
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Health check test"}],
                max_tokens=5,
                temperature=0.0
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            if response.choices and response.choices[0].message.content:
                self._update_health_status(ProviderStatus.AVAILABLE)
                return {
                    "status": "healthy",
                    "provider": "openai",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "model": response.model,
                        "api_configured": bool(self.api_key),
                        "organization": self.organization,
                        "test_response_length": len(response.choices[0].message.content),
                        "tokens_used": response.usage.total_tokens if response.usage else None
                    },
                    "response_time_ms": response_time,
                    "error": None
                }
            else:
                self._update_health_status(ProviderStatus.ERROR)
                return {
                    "status": "degraded",
                    "provider": "openai",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Empty response from test request"},
                    "response_time_ms": response_time,
                    "error": "Empty response from health check"
                }
                
        except openai.AuthenticationError:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "openai",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": "Authentication failed"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": "Invalid API key"
            }
            
        except openai.RateLimitError as e:
            self._update_health_status(ProviderStatus.RATE_LIMITED)
            return {
                "status": "degraded",
                "provider": "openai",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": "Rate limit exceeded"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": "Rate limit exceeded"
            }
            
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "openai",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Network error: {str(e)}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": f"Network error: {str(e)}"
            }
            
        except Exception as e:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "openai",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Health check failed: {str(e)}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
    
    async def cleanup(self):
        """
        Cleanup OpenAI provider resources
        
        Close any open connections and reset state
        """
        if self.async_client:
            await self.async_client.close()
        if self.client:
            self.client.close()
        
        self.client = None
        self.async_client = None
        self._is_initialized = False
        self._update_health_status(ProviderStatus.UNAVAILABLE)
        logger.info("OpenAI provider cleaned up")