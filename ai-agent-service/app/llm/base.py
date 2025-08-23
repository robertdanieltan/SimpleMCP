"""
Base LLM Provider Interface and Data Models

This module defines the abstract base class and data models that all LLM providers
must implement to ensure consistent behavior across different AI services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProviderStatus(Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class LLMResponse:
    """Standardized response format for all LLM providers"""
    success: bool
    response: str
    source: str  # Provider name (e.g., 'gemini', 'openai', 'anthropic', 'ollama')
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ProviderCapabilities:
    """Provider capabilities and limitations"""
    max_tokens: int
    supports_streaming: bool
    supports_functions: bool
    supported_languages: List[str]
    cost_per_token: Optional[float] = None
    context_window: Optional[int] = None
    supports_images: bool = False
    supports_audio: bool = False
    rate_limit_rpm: Optional[int] = None  # Requests per minute
    rate_limit_tpm: Optional[int] = None  # Tokens per minute


@dataclass
class ErrorResponse:
    """Standardized error response format"""
    error_code: str
    message: str
    provider: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers
    
    This interface ensures consistent behavior across different AI services
    while allowing for provider-specific optimizations and features.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration
        
        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.provider_name = self.__class__.__name__.lower().replace('provider', '')
        self._is_initialized = False
        self._last_health_check = None
        self._health_status = ProviderStatus.UNAVAILABLE
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider with its configuration
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response from the LLM
        
        Args:
            prompt: Input prompt for the LLM
            context: Optional context information
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0.0-1.0)
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with generated content or error information
        """
        pass
    
    @abstractmethod
    async def analyze_intent(
        self, 
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze user intent for task management
        
        Args:
            user_input: User's natural language input
            context: Optional context information
            
        Returns:
            Intent analysis results with standardized format:
            {
                "intent": str,
                "confidence": float,
                "entities": Dict[str, Any],
                "action": str,
                "error": Optional[str]
            }
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is available and configured
        
        Returns:
            True if provider is ready to use, False otherwise
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """
        Get provider capabilities and limitations
        
        Returns:
            ProviderCapabilities object with provider specifications
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on the provider
        
        Returns:
            Health check results with standardized format:
            {
                "status": str,  # "healthy", "unhealthy", "degraded"
                "provider": str,
                "timestamp": str,
                "details": Dict[str, Any],
                "response_time_ms": Optional[int],
                "error": Optional[str]
            }
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the provider name"""
        return self.provider_name
    
    def is_initialized(self) -> bool:
        """Check if provider has been initialized"""
        return self._is_initialized
    
    def get_last_health_check(self) -> Optional[datetime]:
        """Get timestamp of last health check"""
        return self._last_health_check
    
    def get_health_status(self) -> ProviderStatus:
        """Get current health status"""
        return self._health_status
    
    def _update_health_status(self, status: ProviderStatus):
        """Update health status and timestamp"""
        self._health_status = status
        self._last_health_check = datetime.utcnow()
    
    def _create_error_response(
        self, 
        error_message: str, 
        error_code: str = "PROVIDER_ERROR"
    ) -> LLMResponse:
        """
        Create standardized error response
        
        Args:
            error_message: Human-readable error message
            error_code: Error classification code
            
        Returns:
            LLMResponse with error information
        """
        return LLMResponse(
            success=False,
            response=f"I apologize, but I encountered an error: {error_message}",
            source=self.provider_name,
            error=f"{error_code}: {error_message}"
        )
    
    def _create_fallback_response(self, message: str) -> LLMResponse:
        """
        Create fallback response when provider is unavailable
        
        Args:
            message: Fallback message
            
        Returns:
            LLMResponse with fallback content
        """
        return LLMResponse(
            success=True,
            response=message,
            source=f"{self.provider_name}_fallback",
            error="Provider unavailable - using fallback response"
        )
    
    def _validate_config(self, required_keys: List[str]) -> bool:
        """
        Validate that required configuration keys are present
        
        Args:
            required_keys: List of required configuration keys
            
        Returns:
            True if all required keys are present, False otherwise
        """
        return all(key in self.config and self.config[key] for key in required_keys)
    
    async def cleanup(self):
        """
        Cleanup provider resources
        
        Override this method if the provider needs to clean up resources
        like connections, sessions, etc.
        """
        pass