"""
Mock LLM Provider Implementation

This module provides a mock implementation of the LLMProvider interface
for testing and demonstration purposes.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ..base import LLMProvider, LLMResponse, ProviderCapabilities, ProviderStatus
from ..exceptions import ProviderConfigurationError
from ..utils import create_health_check_response, log_provider_interaction

logger = logging.getLogger(__name__)


class MockProvider(LLMProvider):
    """
    Mock LLM Provider implementation for testing
    
    This provider simulates LLM functionality without requiring external APIs,
    making it useful for testing the factory pattern and provider lifecycle.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Mock provider with configuration"""
        super().__init__(config)
        self.model_name = config.get('model', 'mock-model-v1')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 1000)
        self.timeout = config.get('timeout', 30)
        
        # Mock-specific settings
        self.simulate_delay = config.get('simulate_delay', 0.1)  # Simulate API delay
        self.failure_rate = config.get('failure_rate', 0.0)  # Simulate failures (0.0-1.0)
        
        self._request_count = 0
    
    async def initialize(self) -> bool:
        """Initialize the Mock provider"""
        try:
            # Simulate initialization delay
            await asyncio.sleep(0.1)
            
            # Mock providers are always available
            self._is_initialized = True
            self._update_health_status(ProviderStatus.AVAILABLE)
            
            logger.info(f"Mock provider initialized successfully with model: {self.model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Mock provider: {e}")
            self._update_health_status(ProviderStatus.ERROR)
            return False
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate mock response"""
        start_time = time.time()
        self._request_count += 1
        
        if not self.is_available():
            return self._create_error_response(
                "Mock provider is not available",
                "PROVIDER_UNAVAILABLE"
            )
        
        try:
            # Simulate API delay
            await asyncio.sleep(self.simulate_delay)
            
            # Simulate occasional failures
            import random
            if random.random() < self.failure_rate:
                raise Exception("Simulated API failure")
            
            # Generate mock response based on prompt
            mock_response = self._generate_mock_response(prompt, context)
            
            duration_ms = int((time.time() - start_time) * 1000)
            tokens_used = len(mock_response.split())
            
            log_provider_interaction(
                self.provider_name,
                "generate_response",
                True,
                duration_ms,
                tokens_used=tokens_used
            )
            
            return LLMResponse(
                success=True,
                response=mock_response,
                source=self.provider_name,
                tokens_used=tokens_used,
                model=self.model_name
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            log_provider_interaction(
                self.provider_name,
                "generate_response",
                False,
                duration_ms,
                error=error_msg
            )
            
            return self._create_error_response(
                f"Mock API error: {error_msg}",
                "API_ERROR"
            )
    
    async def analyze_intent(
        self, 
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze user intent using mock logic"""
        if not self.is_available():
            from ..utils import create_fallback_intent_analysis
            return create_fallback_intent_analysis(user_input)
        
        # Simulate processing delay
        await asyncio.sleep(self.simulate_delay * 0.5)
        
        # Simple mock intent analysis
        user_lower = user_input.lower()
        
        if "create" in user_lower and "task" in user_lower:
            return {
                "intent": "create_task",
                "confidence": 0.9,
                "entities": {"task_type": "general"},
                "action": "create_task",
                "source": "mock_analysis"
            }
        elif "list" in user_lower and "task" in user_lower:
            return {
                "intent": "list_tasks",
                "confidence": 0.8,
                "entities": {},
                "action": "list_tasks",
                "source": "mock_analysis"
            }
        elif "create" in user_lower and "project" in user_lower:
            return {
                "intent": "create_project",
                "confidence": 0.9,
                "entities": {"project_type": "general"},
                "action": "create_project",
                "source": "mock_analysis"
            }
        else:
            return {
                "intent": "general_query",
                "confidence": 0.6,
                "entities": {},
                "action": "general_response",
                "source": "mock_analysis"
            }
    
    def is_available(self) -> bool:
        """Check if Mock provider is available"""
        return (
            self._is_initialized and 
            self._health_status == ProviderStatus.AVAILABLE
        )
    
    def get_capabilities(self) -> ProviderCapabilities:
        """Get Mock provider capabilities"""
        return ProviderCapabilities(
            max_tokens=4096,
            supports_streaming=True,
            supports_functions=True,
            supported_languages=['en', 'es', 'fr', 'de'],
            cost_per_token=0.0,  # Mock is free
            context_window=4096,
            supports_images=False,
            supports_audio=False,
            rate_limit_rpm=1000,  # High limits for testing
            rate_limit_tpm=100000
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on Mock provider"""
        start_time = time.time()
        
        try:
            if not self._is_initialized:
                return create_health_check_response(
                    self.provider_name,
                    "unhealthy",
                    {"reason": "not_initialized"},
                    "Provider not initialized"
                )
            
            # Simulate health check delay
            await asyncio.sleep(0.05)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            self._update_health_status(ProviderStatus.AVAILABLE)
            return create_health_check_response(
                self.provider_name,
                "healthy",
                {
                    "model": self.model_name,
                    "request_count": self._request_count,
                    "capabilities": "text_generation, intent_analysis, streaming",
                    "simulated_delay": self.simulate_delay,
                    "failure_rate": self.failure_rate
                },
                response_time_ms=duration_ms
            )
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self._update_health_status(ProviderStatus.ERROR)
            return create_health_check_response(
                self.provider_name,
                "unhealthy",
                {"reason": "health_check_error"},
                str(e),
                response_time_ms=duration_ms
            )
    
    def _generate_mock_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a mock response based on the prompt"""
        prompt_lower = prompt.lower()
        
        # Task management responses
        if "create" in prompt_lower and "task" in prompt_lower:
            return "I'll help you create a new task. What would you like to name it and what priority should it have?"
        
        elif "list" in prompt_lower and "task" in prompt_lower:
            return "Here are your current tasks:\n1. Sample Task 1 (High Priority)\n2. Sample Task 2 (Medium Priority)\n3. Sample Task 3 (Low Priority)"
        
        elif "create" in prompt_lower and "project" in prompt_lower:
            return "I'll help you create a new project. What's the project name and description?"
        
        elif "list" in prompt_lower and "project" in prompt_lower:
            return "Here are your current projects:\n1. Sample Project A\n2. Sample Project B\n3. Sample Project C"
        
        # General responses
        elif "hello" in prompt_lower or "hi" in prompt_lower:
            return "Hello! I'm a mock AI assistant ready to help you with task and project management."
        
        elif "help" in prompt_lower:
            return "I can help you with:\n- Creating and managing tasks\n- Creating and managing projects\n- Listing your tasks and projects\n- General task management questions"
        
        else:
            return f"I understand you're asking about: '{prompt[:50]}...'. As a mock provider, I can simulate responses for task and project management. How can I help you organize your work?"
    
    async def cleanup(self):
        """Cleanup Mock provider resources"""
        try:
            # Reset state
            self._is_initialized = False
            self._update_health_status(ProviderStatus.UNAVAILABLE)
            self._request_count = 0
            
            logger.info("Mock provider cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during Mock provider cleanup: {e}")