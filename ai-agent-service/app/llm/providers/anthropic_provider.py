"""
Anthropic LLM Provider

This module implements the Anthropic provider for the LLM abstraction layer,
providing Claude API integration with comprehensive error handling and rate limiting.
"""

import os
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import time

import anthropic
from anthropic import Anthropic, AsyncAnthropic

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

logger = get_provider_logger("anthropic")


class AnthropicProvider(LLMProvider):
    """
    Anthropic LLM Provider implementation
    
    Provides Claude API integration with the standardized LLM interface,
    including comprehensive error handling, rate limiting, and health monitoring.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Anthropic provider with configuration
        
        Args:
            config: Configuration dictionary containing:
                - api_key: Anthropic API key
                - model: Model name (default: 'claude-3-sonnet-20240229')
                - enabled: Whether provider is enabled
                - base_url: Optional base URL for API
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model_name = config.get('model', 'claude-3-sonnet-20240229')
        self.enabled = config.get('enabled', bool(self.api_key))
        self.base_url = config.get('base_url')
        
        self.client = None
        self.async_client = None
        
        # Rate limiting tracking
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window = 60  # 1 minute window
        self._max_requests_per_minute = 1000  # Conservative limit for Claude
        
        logger.info(f"Anthropic provider initialized with model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """
        Initialize the Anthropic provider
        
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
                    provider="anthropic"
                )
            
            if not self.enabled:
                logger.info("Anthropic provider is disabled")
                return False
            
            # Initialize Anthropic clients
            client_kwargs = {
                'api_key': self.api_key,
            }
            
            if self.base_url:
                client_kwargs['base_url'] = self.base_url
            
            self.client = Anthropic(**client_kwargs)
            self.async_client = AsyncAnthropic(**client_kwargs)
            
            # Test the connection with a simple health check
            await self._test_connection()
            
            self._is_initialized = True
            self._update_health_status(ProviderStatus.AVAILABLE)
            logger.info("Anthropic provider initialized successfully")
            return True
            
        except ProviderConfigurationError:
            raise
        except anthropic.AuthenticationError as e:
            error_msg = "Invalid Anthropic API key"
            logger.error(f"Anthropic authentication failed: {e}")
            raise ProviderAuthenticationError(error_msg, provider="anthropic")
        except Exception as e:
            error_msg = f"Failed to initialize Anthropic provider: {str(e)}"
            logger.error(error_msg)
            raise ProviderInitializationError(error_msg, provider="anthropic")
    
    async def _test_connection(self):
        """Test connection to Anthropic API with a simple request"""
        try:
            response = await self.async_client.messages.create(
                model=self.model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "Hello"}]
            )
            if not response.content or not response.content[0].text:
                raise ProviderInitializationError(
                    "Anthropic API test failed - no response received",
                    provider="anthropic"
                )
        except Exception as e:
            raise ProviderInitializationError(
                f"Anthropic API connection test failed: {str(e)}",
                provider="anthropic"
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
        Generate response using Anthropic API
        
        Args:
            prompt: Input prompt for the LLM
            context: Optional context information
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0.0-1.0)
            **kwargs: Additional Anthropic-specific parameters
            
        Returns:
            LLMResponse with generated content or error information
        """
        if not self.is_available():
            return self._create_error_response(
                "Anthropic provider is not available. Please check configuration.",
                "PROVIDER_UNAVAILABLE"
            )
        
        try:
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
            
            if response.content and response.content[0].text:
                return LLMResponse(
                    success=True,
                    response=response.content[0].text.strip(),
                    source="anthropic",
                    model=response.model,
                    tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None
                )
            else:
                logger.warning("Anthropic returned empty response")
                return self._create_error_response(
                    "AI service returned an empty response",
                    "EMPTY_RESPONSE"
                )
                
        except ProviderRateLimitError as e:
            logger.warning(f"Anthropic rate limit exceeded: {e}")
            return self._create_error_response(
                "Rate limit exceeded. Please try again later.",
                "RATE_LIMIT_EXCEEDED"
            )
        except ProviderAuthenticationError as e:
            logger.error(f"Anthropic authentication error: {e}")
            return self._create_error_response(
                "Authentication failed. Please check API key.",
                "AUTHENTICATION_ERROR"
            )
        except ProviderNetworkError as e:
            logger.error(f"Anthropic network error: {e}")
            return self._create_error_response(
                "Network error occurred. Please try again.",
                "NETWORK_ERROR"
            )
        except ProviderModelError as e:
            logger.error(f"Anthropic model error: {e}")
            return self._create_error_response(
                f"Model error: {str(e)}",
                "MODEL_ERROR"
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            return self._create_error_response(
                f"AI service temporarily unavailable: {str(e)}",
                "PROVIDER_ERROR"
            )
    
    async def _generate_with_retry(
        self, 
        messages: List[Dict[str, str]], 
        max_retries: int = 3, 
        **kwargs
    ):
        """Generate content with retry logic for transient errors"""
        for attempt in range(max_retries):
            try:
                response = await self.async_client.messages.create(
                    model=self.model_name,
                    messages=messages,
                    **kwargs
                )
                return response
                
            except anthropic.RateLimitError as e:
                if attempt == max_retries - 1:
                    # Extract retry-after from headers if available
                    retry_after = getattr(e, 'retry_after', 60)
                    raise ProviderRateLimitError(
                        "Rate limit exceeded",
                        provider="anthropic",
                        retry_after=retry_after
                    )
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
            except anthropic.AuthenticationError as e:
                raise ProviderAuthenticationError(
                    "Invalid API key",
                    provider="anthropic"
                )
                
            except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
                if attempt == max_retries - 1:
                    raise ProviderNetworkError(
                        f"Network error: {str(e)}",
                        provider="anthropic"
                    )
                await asyncio.sleep(2 ** attempt)
                
            except anthropic.BadRequestError as e:
                # Don't retry bad requests
                raise ProviderModelError(
                    f"Invalid request: {str(e)}",
                    provider="anthropic"
                )
                
            except anthropic.InternalServerError as e:
                if attempt == max_retries - 1:
                    raise ProviderResponseError(
                        f"Server error: {str(e)}",
                        provider="anthropic"
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
        Prepare messages for Anthropic messages format
        
        Args:
            prompt: User's input prompt
            context: Optional context information
            
        Returns:
            List of message dictionaries for Anthropic API
        """
        # Anthropic doesn't use system messages in the same way as OpenAI
        # Instead, we'll include system context in the user message
        system_context = """You are an AI assistant that helps with task and project management. 
You can create, update, list, and delete tasks and projects through an MCP service.

Key capabilities:
- Natural language understanding for task management requests
- Project organization and planning
- Task prioritization and status tracking
- Clear, helpful responses

Always be helpful, concise, and focused on task/project management activities."""
        
        user_content = f"{system_context}\n\nUser request: {prompt}"
        if context:
            user_content += f"\n\nContext: {context}"
        
        return [{"role": "user", "content": user_content}]
    
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
                    provider="anthropic",
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
                "error": "Anthropic provider unavailable"
            }
        
        intent_prompt = f"""Analyze this user request for task/project management intent:
"{user_input}"

Identify:
1. Primary intent (create_task, list_tasks, update_task, delete_task, create_project, list_projects, general_query)
2. Confidence level (0.0-1.0)
3. Key entities (task names, project names, priorities, statuses, dates)
4. Required action

Respond ONLY with valid JSON in this exact format:
{{
    "intent": "intent_name",
    "confidence": 0.9,
    "entities": {{"key": "value"}},
    "action": "action_to_take"
}}"""
        
        try:
            response = await self.async_client.messages.create(
                model=self.model_name,
                max_tokens=200,
                temperature=0.1,  # Low temperature for consistent JSON output
                messages=[{"role": "user", "content": intent_prompt}]
            )
            
            if response.content and response.content[0].text:
                try:
                    intent_data = json.loads(response.content[0].text.strip())
                    return intent_data
                except json.JSONDecodeError:
                    logger.warning("Failed to parse intent analysis JSON from Anthropic")
                    return self._fallback_intent_analysis(user_input)
            else:
                logger.warning("Anthropic returned empty response for intent analysis")
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
        Check if Anthropic provider is available and configured
        
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
        Get Anthropic provider capabilities and limitations
        
        Returns:
            ProviderCapabilities object with Anthropic specifications
        """
        # Capabilities vary by model, these are for Claude-3 Sonnet
        if "opus" in self.model_name.lower():
            max_tokens = 4096
            context_window = 200000
            cost_per_token = 0.000075  # Approximate cost per token for Claude-3 Opus
            rate_limit_rpm = 50
            rate_limit_tpm = 40000
        elif "haiku" in self.model_name.lower():
            max_tokens = 4096
            context_window = 200000
            cost_per_token = 0.00000125  # Approximate cost per token for Claude-3 Haiku
            rate_limit_rpm = 1000
            rate_limit_tpm = 100000
        else:  # Sonnet (default)
            max_tokens = 4096
            context_window = 200000
            cost_per_token = 0.000015  # Approximate cost per token for Claude-3 Sonnet
            rate_limit_rpm = 1000
            rate_limit_tpm = 80000
        
        return ProviderCapabilities(
            max_tokens=max_tokens,
            supports_streaming=True,  # Anthropic supports streaming
            supports_functions=False,  # Claude doesn't have function calling like OpenAI
            supported_languages=[
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
                "ar", "hi", "th", "vi", "id", "ms", "tl", "sw", "nl", "pl",
                "tr", "he", "sv", "da", "no", "fi", "cs", "hu", "ro", "bg",
                "uk", "el", "ca", "hr", "sk", "sl", "et", "lv", "lt", "mt"
            ],
            cost_per_token=cost_per_token,
            context_window=context_window,
            supports_images=True,  # Claude-3 supports vision
            supports_audio=False,
            rate_limit_rpm=rate_limit_rpm,
            rate_limit_tpm=rate_limit_tpm
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on Anthropic provider
        
        Returns:
            Health check results with standardized format
        """
        start_time = time.time()
        
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "provider": "anthropic",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider is disabled in configuration"},
                    "response_time_ms": None,
                    "error": None
                }
            
            if not self._is_initialized:
                return {
                    "status": "unhealthy",
                    "provider": "anthropic",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider not initialized"},
                    "response_time_ms": None,
                    "error": "Provider not initialized"
                }
            
            # Perform a simple test request
            response = await self.async_client.messages.create(
                model=self.model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "Health check test"}]
            )
            
            response_time = int((time.time() - start_time) * 1000)
            
            if response.content and response.content[0].text:
                self._update_health_status(ProviderStatus.AVAILABLE)
                return {
                    "status": "healthy",
                    "provider": "anthropic",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "model": response.model,
                        "api_configured": bool(self.api_key),
                        "test_response_length": len(response.content[0].text),
                        "input_tokens": response.usage.input_tokens if response.usage else None,
                        "output_tokens": response.usage.output_tokens if response.usage else None
                    },
                    "response_time_ms": response_time,
                    "error": None
                }
            else:
                self._update_health_status(ProviderStatus.ERROR)
                return {
                    "status": "degraded",
                    "provider": "anthropic",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Empty response from test request"},
                    "response_time_ms": response_time,
                    "error": "Empty response from health check"
                }
                
        except anthropic.AuthenticationError:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "anthropic",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": "Authentication failed"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": "Invalid API key"
            }
            
        except anthropic.RateLimitError as e:
            self._update_health_status(ProviderStatus.RATE_LIMITED)
            return {
                "status": "degraded",
                "provider": "anthropic",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": "Rate limit exceeded"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": "Rate limit exceeded"
            }
            
        except (anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "anthropic",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Network error: {str(e)}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": f"Network error: {str(e)}"
            }
            
        except Exception as e:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "anthropic",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Health check failed: {str(e)}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
    
    async def cleanup(self):
        """
        Cleanup Anthropic provider resources
        
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
        logger.info("Anthropic provider cleaned up")