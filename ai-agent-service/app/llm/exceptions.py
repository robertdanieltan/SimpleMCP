"""
LLM Provider Exceptions

This module defines custom exceptions for the LLM provider system,
enabling better error handling and debugging across different providers.
"""

from typing import Optional, Dict, Any


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors"""
    
    def __init__(
        self, 
        message: str, 
        provider: Optional[str] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code or "PROVIDER_ERROR"
        self.details = details or {}


class ProviderInitializationError(LLMProviderError):
    """Raised when a provider fails to initialize"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            provider=provider,
            error_code="INITIALIZATION_ERROR",
            details=details
        )


class ProviderConfigurationError(LLMProviderError):
    """Raised when provider configuration is invalid"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            provider=provider,
            error_code="CONFIGURATION_ERROR",
            details=details
        )


class ProviderAuthenticationError(LLMProviderError):
    """Raised when provider authentication fails"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            provider=provider,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class ProviderRateLimitError(LLMProviderError):
    """Raised when provider rate limits are exceeded"""
    
    def __init__(
        self, 
        message: str, 
        provider: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            provider=provider,
            error_code="RATE_LIMIT_ERROR",
            details=details
        )
        self.retry_after = retry_after


class ProviderNetworkError(LLMProviderError):
    """Raised when network communication with provider fails"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            provider=provider,
            error_code="NETWORK_ERROR",
            details=details
        )


class ProviderModelError(LLMProviderError):
    """Raised when there are issues with the specified model"""
    
    def __init__(
        self, 
        message: str, 
        provider: Optional[str] = None,
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            provider=provider,
            error_code="MODEL_ERROR",
            details=details
        )
        self.model = model


class ProviderResponseError(LLMProviderError):
    """Raised when provider returns an invalid or unexpected response"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            provider=provider,
            error_code="RESPONSE_ERROR",
            details=details
        )


class ProviderUnavailableError(LLMProviderError):
    """Raised when provider is temporarily unavailable"""
    
    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            provider=provider,
            error_code="PROVIDER_UNAVAILABLE",
            details=details
        )