"""
Ollama LLM Provider

This module implements the Ollama provider for the LLM abstraction layer,
providing local LLM integration through Ollama's HTTP API with comprehensive
error handling and model management.
"""

import os
import logging
import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

import httpx

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

logger = get_provider_logger("ollama")


class OllamaProvider(LLMProvider):
    """
    Ollama LLM Provider implementation
    
    Provides local LLM integration through Ollama's HTTP API with the standardized
    LLM interface, including model discovery, dynamic model switching, and offline
    functionality.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Ollama provider with configuration
        
        Args:
            config: Configuration dictionary containing:
                - base_url: Ollama server URL (default: 'http://localhost:11434')
                - model: Default model name (default: 'llama2')
                - enabled: Whether provider is enabled
                - timeout: Request timeout in seconds
                - keep_alive: Keep model loaded time (e.g., '5m', '1h')
        """
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model_name = config.get('model', 'llama2')
        self.enabled = config.get('enabled', True)
        self.timeout = config.get('timeout', 60)
        self.keep_alive = config.get('keep_alive', '5m')
        
        self.client = None
        self._available_models = []
        self._model_info = {}
        self._full_model_names = {}  # Map base names to full names with tags
        
        # Rate limiting (Ollama is local, so more generous limits)
        self._last_request_time = 0
        self._request_count = 0
        self._rate_limit_window = 60  # 1 minute window
        self._max_requests_per_minute = 100  # Local server can handle more
        
        logger.info(f"Ollama provider initialized with base URL: {self.base_url}, model: {self.model_name}")
    
    async def initialize(self) -> bool:
        """
        Initialize the Ollama provider
        
        Returns:
            True if initialization successful, False otherwise
            
        Raises:
            ProviderConfigurationError: If configuration is invalid
            ProviderNetworkError: If Ollama server is not accessible
            ProviderInitializationError: If initialization fails
        """
        try:
            if not self.enabled:
                logger.info("Ollama provider is disabled")
                return False
            
            # Initialize HTTP client
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={'Content-Type': 'application/json'}
            )
            
            # Test connection and discover models
            await self._test_connection()
            await self._discover_models()
            
            # Validate that the configured model is available
            if self.model_name not in self._available_models:
                logger.warning(f"Configured model '{self.model_name}' not found. Available models: {self._available_models}")
                if self._available_models:
                    # Use the first available model as fallback
                    self.model_name = self._available_models[0]
                    logger.info(f"Using fallback model: {self.model_name}")
                else:
                    raise ProviderInitializationError(
                        "No models available on Ollama server",
                        provider="ollama"
                    )
            
            self._is_initialized = True
            self._update_health_status(ProviderStatus.AVAILABLE)
            logger.info(f"Ollama provider initialized successfully with model: {self.model_name}")
            return True
            
        except ProviderInitializationError:
            raise
        except httpx.ConnectError as e:
            error_msg = f"Cannot connect to Ollama server at {self.base_url}"
            logger.error(f"Ollama connection failed: {e}")
            raise ProviderNetworkError(error_msg, provider="ollama")
        except Exception as e:
            error_msg = f"Failed to initialize Ollama provider: {str(e)}"
            logger.error(error_msg)
            raise ProviderInitializationError(error_msg, provider="ollama")
    
    async def _test_connection(self):
        """Test connection to Ollama server"""
        try:
            response = await self.client.get("/api/version")
            response.raise_for_status()
            version_info = response.json()
            logger.info(f"Connected to Ollama server version: {version_info.get('version', 'unknown')}")
        except Exception as e:
            raise ProviderInitializationError(
                f"Ollama server connection test failed: {str(e)}",
                provider="ollama"
            )
    
    async def _discover_models(self):
        """Discover available models on the Ollama server"""
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            
            self._available_models = []
            self._model_info = {}
            self._full_model_names = {}  # Map base names to full names
            
            for model in data.get('models', []):
                full_name = model.get('name', '')
                base_name = full_name.split(':')[0]  # Remove tag if present
                
                if base_name and base_name not in self._available_models:
                    self._available_models.append(base_name)
                    self._full_model_names[base_name] = full_name
                    self._model_info[base_name] = {
                        'name': full_name,
                        'base_name': base_name,
                        'size': model.get('size', 0),
                        'modified_at': model.get('modified_at'),
                        'digest': model.get('digest'),
                        'details': model.get('details', {})
                    }
            
            logger.info(f"Discovered {len(self._available_models)} models: {self._available_models}")
            
        except Exception as e:
            logger.warning(f"Failed to discover models: {e}")
            # Don't fail initialization if model discovery fails
            self._available_models = [self.model_name]  # Assume configured model exists
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response using Ollama API
        
        Args:
            prompt: Input prompt for the LLM
            context: Optional context information
            max_tokens: Maximum tokens in response (Ollama uses num_predict)
            temperature: Response randomness (0.0-1.0)
            **kwargs: Additional Ollama-specific parameters
            
        Returns:
            LLMResponse with generated content or error information
        """
        error_handler = get_error_handler()
        error_context = create_error_context(
            provider_name="ollama",
            operation="generate_response",
            user_input=prompt,
            additional_context={"max_tokens": max_tokens, "temperature": temperature, "model": self.model_name}
        )
        
        if not self.is_available():
            error = ProviderUnavailableError(
                "Ollama provider is not available. Please check that Ollama is running.",
                provider="ollama"
            )
            return error_handler.create_error_response(error, error_context)
        
        try:
            with error_handler.handle_provider_operation(error_context, FallbackStrategy.RULE_BASED):
                # Log request
                logger.log_request(prompt, request_id=error_context.request_id)
                
                # Check rate limits
                await self._check_rate_limit()
                
                # Prepare the full prompt with context
                full_prompt = self._prepare_prompt(prompt, context)
                
                # Generate response with error handling
                start_time = time.time()
                response = await self._generate_with_retry(
                    prompt=full_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                response_time = int((time.time() - start_time) * 1000)
                
                if response:
                    response_text = response.get('response', '')
                    thinking_text = response.get('thinking', '')
                    
                    # Some models (like reasoning models) may have empty response but valid thinking
                    # Use response if available, otherwise use thinking, otherwise create a helpful message
                    final_response = response_text
                    if not final_response and thinking_text:
                        final_response = f"[Model thinking: {thinking_text}]"
                    elif not final_response and response.get('done'):
                        final_response = "The model processed your request but didn't generate a text response."
                    
                    if final_response:
                        # Ollama doesn't provide exact token counts, so we estimate
                        tokens_used = len(final_response.split()) + len(full_prompt.split())
                        
                        # Log successful response
                        logger.log_response(
                            final_response.strip(),
                            success=True,
                            response_time_ms=response_time,
                            tokens_used=tokens_used,
                            model=response.get('model', self.model_name),
                            request_id=error_context.request_id
                        )
                        
                        return LLMResponse(
                            success=True,
                            response=final_response.strip(),
                            source="ollama",
                            model=response.get('model', self.model_name),
                            tokens_used=tokens_used
                        )
                    else:
                        error = ProviderResponseError(
                            "Local LLM returned no usable response",
                            provider="ollama"
                        )
                        logger.log_error(error, "generate_response", request_id=error_context.request_id)
                        return error_handler.create_error_response(error, error_context)
                else:
                    error = ProviderResponseError(
                        "Local LLM returned an empty response",
                        provider="ollama"
                    )
                    logger.log_error(error, "generate_response", request_id=error_context.request_id)
                    return error_handler.create_error_response(error, error_context)
                    
        except (ProviderNetworkError, ProviderModelError) as e:
            logger.log_error(e, "generate_response", request_id=error_context.request_id)
            return error_handler.create_error_response(e, error_context)
        except Exception as e:
            # Convert unexpected errors to provider errors
            provider_error = ProviderResponseError(
                f"Unexpected error: {str(e)}",
                provider="ollama",
                details={"original_exception": type(e).__name__}
            )
            logger.log_error(provider_error, "generate_response", request_id=error_context.request_id)
            return error_handler.create_error_response(provider_error, error_context)
    
    async def _generate_with_retry(
        self, 
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        max_retries: int = 3, 
        **kwargs
    ) -> Dict[str, Any]:
        """Generate content with retry logic for transient errors"""
        
        # Prepare request payload
        full_model_name = self._get_full_model_name()
        payload = {
            "model": full_model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
        }
        
        # Add keep_alive if configured
        if self.keep_alive:
            payload["keep_alive"] = self.keep_alive
        
        # Add any additional options
        if kwargs:
            payload["options"].update(kwargs)
        
        for attempt in range(max_retries):
            try:
                response = await self.client.post("/api/generate", json=payload)
                response.raise_for_status()
                return response.json()
                
            except httpx.ConnectError as e:
                if attempt == max_retries - 1:
                    raise ProviderNetworkError(
                        f"Cannot connect to Ollama server: {str(e)}",
                        provider="ollama"
                    )
                await asyncio.sleep(2 ** attempt)
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ProviderModelError(
                        f"Model '{self.model_name}' not found on Ollama server",
                        provider="ollama"
                    )
                elif e.response.status_code >= 500:
                    if attempt == max_retries - 1:
                        raise ProviderResponseError(
                            f"Ollama server error: {e.response.status_code}",
                            provider="ollama"
                        )
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise ProviderModelError(
                        f"Ollama request failed: {e.response.status_code}",
                        provider="ollama"
                    )
                    
            except httpx.TimeoutException as e:
                if attempt == max_retries - 1:
                    raise ProviderNetworkError(
                        f"Ollama request timeout: {str(e)}",
                        provider="ollama"
                    )
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1)
    
    def _get_full_model_name(self, base_name: Optional[str] = None) -> str:
        """
        Get the full model name with tag for API calls
        
        Args:
            base_name: Base model name (defaults to current model)
            
        Returns:
            Full model name with tag
        """
        target_model = base_name or self.model_name
        return self._full_model_names.get(target_model, target_model)
    
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
                    provider="ollama",
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
        error_handler = get_error_handler()
        error_context = create_error_context(
            provider_name="ollama",
            operation="analyze_intent",
            user_input=user_input
        )
        
        if not self.is_available():
            logger.log_operation(
                logging.WARNING,
                "analyze_intent",
                "Ollama provider unavailable for intent analysis",
                success=False,
                request_id=error_context.request_id
            )
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "action": "error",
                "error": "Ollama provider unavailable"
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
            with error_handler.handle_provider_operation(error_context, FallbackStrategy.RULE_BASED):
                response = await self.generate_response(
                    prompt=intent_prompt,
                    max_tokens=200,
                    temperature=0.1  # Low temperature for consistent JSON output
                )
                
                if response.success:
                    try:
                        intent_data = json.loads(response.response.strip())
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
        Check if Ollama provider is available and configured
        
        Returns:
            True if provider is ready to use, False otherwise
        """
        return (
            self.enabled and 
            self._is_initialized and 
            self.client is not None and
            self._health_status == ProviderStatus.AVAILABLE
        )
    
    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get Ollama provider capabilities and limitations
        
        Returns:
            ProviderCapabilities object with Ollama specifications
        """
        # Capabilities depend on the specific model, these are general estimates
        return ProviderCapabilities(
            max_tokens=4096,  # Most models support at least 4K context
            supports_streaming=True,  # Ollama supports streaming
            supports_functions=False,  # Most local models don't have function calling
            supported_languages=[
                "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
                "ar", "hi", "th", "vi", "id", "ms", "tl", "sw", "nl", "pl"
            ],
            cost_per_token=0.0,  # Local models are free to run
            context_window=4096,  # Varies by model, conservative estimate
            supports_images=False,  # Most text models don't support images
            supports_audio=False,
            rate_limit_rpm=100,  # Local server, generous limits
            rate_limit_tpm=None  # No token-based rate limiting for local
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on Ollama provider
        
        Returns:
            Health check results with standardized format
        """
        start_time = time.time()
        
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "provider": "ollama",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider is disabled in configuration"},
                    "response_time_ms": None,
                    "error": None
                }
            
            if not self._is_initialized:
                return {
                    "status": "unhealthy",
                    "provider": "ollama",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "Provider not initialized"},
                    "response_time_ms": None,
                    "error": "Provider not initialized"
                }
            
            # Check server connectivity
            version_response = await self.client.get("/api/version")
            version_response.raise_for_status()
            version_info = version_response.json()
            
            # Perform a simple test request
            full_model_name = self._get_full_model_name()
            test_payload = {
                "model": full_model_name,
                "prompt": "Health check test",
                "stream": False,
                "options": {"num_predict": 5}
            }
            
            test_response = await self.client.post("/api/generate", json=test_payload)
            test_response.raise_for_status()
            test_data = test_response.json()
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Check if we got a valid response (some models may have empty response but valid thinking)
            response_text = test_data.get('response', '')
            thinking_text = test_data.get('thinking', '')
            has_valid_response = bool(response_text or thinking_text or test_data.get('done'))
            
            if has_valid_response:
                self._update_health_status(ProviderStatus.AVAILABLE)
                return {
                    "status": "healthy",
                    "provider": "ollama",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {
                        "server_version": version_info.get('version'),
                        "base_url": self.base_url,
                        "model": self.model_name,
                        "available_models": len(self._available_models),
                        "test_response_length": len(response_text),
                        "test_thinking_length": len(thinking_text),
                        "model_responded": test_data.get('done', False)
                    },
                    "response_time_ms": response_time,
                    "error": None
                }
            else:
                self._update_health_status(ProviderStatus.ERROR)
                return {
                    "status": "degraded",
                    "provider": "ollama",
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": {"reason": "No valid response from test request"},
                    "response_time_ms": response_time,
                    "error": "No valid response from health check"
                }
                
        except httpx.ConnectError:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Cannot connect to Ollama server at {self.base_url}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": "Ollama server not accessible"
            }
            
        except httpx.HTTPStatusError as e:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Ollama server error: {e.response.status_code}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": f"Server returned {e.response.status_code}"
            }
            
        except Exception as e:
            self._update_health_status(ProviderStatus.ERROR)
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"reason": f"Health check failed: {str(e)}"},
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error": str(e)
            }
    
    async def get_available_models(self) -> List[str]:
        """
        Get list of available models on the Ollama server
        
        Returns:
            List of available model names
        """
        if not self.is_available():
            return []
        
        try:
            await self._discover_models()
            return self._available_models.copy()
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []
    
    async def switch_model(self, model_name: str) -> bool:
        """
        Switch to a different model
        
        Args:
            model_name: Name of the model to switch to
            
        Returns:
            True if switch successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            # Check if model is available
            available_models = await self.get_available_models()
            if model_name not in available_models:
                logger.error(f"Model '{model_name}' not available. Available models: {available_models}")
                return False
            
            # Switch to the new model
            old_model = self.model_name
            self.model_name = model_name
            
            # Test the new model with a simple request
            full_model_name = self._get_full_model_name()
            test_payload = {
                "model": full_model_name,
                "prompt": "Test",
                "stream": False,
                "options": {"num_predict": 1}
            }
            
            response = await self.client.post("/api/generate", json=test_payload)
            response.raise_for_status()
            
            logger.info(f"Successfully switched from model '{old_model}' to '{model_name}'")
            return True
            
        except Exception as e:
            # Revert to old model on failure
            self.model_name = old_model if 'old_model' in locals() else self.model_name
            logger.error(f"Failed to switch to model '{model_name}': {e}")
            return False
    
    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a specific model
        
        Args:
            model_name: Name of the model (defaults to current model)
            
        Returns:
            Model information dictionary
        """
        target_model = model_name or self.model_name
        return self._model_info.get(target_model, {
            "name": target_model,
            "available": target_model in self._available_models
        })
    
    async def cleanup(self):
        """
        Cleanup Ollama provider resources
        
        Close HTTP client and reset state
        """
        if self.client:
            await self.client.aclose()
        
        self.client = None
        self._is_initialized = False
        self._available_models = []
        self._model_info = {}
        self._full_model_names = {}
        self._update_health_status(ProviderStatus.UNAVAILABLE)
        logger.info("Ollama provider cleaned up")