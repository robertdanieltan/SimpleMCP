"""
LLM Provider Selector

This module implements simple provider selection via environment variables,
allowing users to choose which LLM provider to use through the LLM_PROVIDER
environment variable.
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime

from .factory import LLMProviderFactory
from .base import LLMProvider
from .exceptions import ProviderConfigurationError, ProviderUnavailableError
from .performance_tracker import get_performance_tracker
from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


class ProviderSelector:
    """
    Handles LLM provider selection based on environment variables
    
    This class provides a simple interface for selecting and initializing
    LLM providers based on the LLM_PROVIDER environment variable.
    """
    
    def __init__(self):
        """Initialize the provider selector"""
        self.config_manager = ConfigManager()
        self.factory = LLMProviderFactory(self.config_manager)
        self._selected_provider: Optional[LLMProvider] = None
        self._provider_name: Optional[str] = None
        self._performance_tracker = get_performance_tracker()
        self._last_health_check: Optional[datetime] = None
        self._last_health_status: Optional[Dict[str, Any]] = None
        
        logger.info("Provider selector initialized")
    
    async def initialize_selected_provider(self) -> bool:
        """
        Initialize the selected provider based on environment configuration
        
        Returns:
            True if provider was successfully initialized, False otherwise
        """
        try:
            # Get provider selection from environment
            provider_name = self._get_selected_provider_name()
            
            if not provider_name:
                logger.error("No LLM provider selected. Set LLM_PROVIDER environment variable.")
                return False
            
            # Validate provider is supported
            if not self._is_provider_supported(provider_name):
                logger.error(f"Unsupported provider: {provider_name}")
                return False
            
            # Initialize providers through factory
            init_results = await self.factory.initialize_providers()
            
            if not init_results.get(provider_name, False):
                logger.error(f"Failed to initialize provider: {provider_name}")
                return False
            
            # Get the initialized provider
            self._selected_provider = self.factory.get_provider(provider_name)
            self._provider_name = provider_name
            
            if not self._selected_provider:
                logger.error(f"Provider {provider_name} not available after initialization")
                return False
            
            logger.info(f"Successfully initialized provider: {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing selected provider: {e}")
            return False
    
    def get_selected_provider(self) -> Optional[LLMProvider]:
        """
        Get the currently selected and initialized provider
        
        Returns:
            LLMProvider instance if available, None otherwise
        """
        return self._selected_provider
    
    def get_selected_provider_name(self) -> Optional[str]:
        """
        Get the name of the currently selected provider
        
        Returns:
            Provider name if selected, None otherwise
        """
        return self._provider_name
    
    def is_provider_available(self) -> bool:
        """
        Check if the selected provider is available and ready to use
        
        Returns:
            True if provider is available, False otherwise
        """
        return (
            self._selected_provider is not None and 
            self._selected_provider.is_available()
        )
    
    def get_provider_status(self) -> Dict[str, Any]:
        """
        Get comprehensive status of the selected provider with performance metrics
        
        Returns:
            Status information dictionary with performance data
        """
        if not self._selected_provider:
            return {
                "provider_name": self._provider_name,
                "available": False,
                "initialized": False,
                "error": "No provider initialized",
                "performance_metrics": None
            }
        
        try:
            capabilities = self._selected_provider.get_capabilities()
            
            # Get performance metrics
            perf_metrics = self._performance_tracker.get_provider_health_metrics(self._provider_name)
            recent_perf = self._performance_tracker.get_recent_performance(self._provider_name, minutes=5)
            
            return {
                "provider_name": self._provider_name,
                "available": self._selected_provider.is_available(),
                "initialized": self._selected_provider.is_initialized(),
                "model": getattr(self._selected_provider, 'model_name', 'unknown'),
                "health_status": self._selected_provider.get_health_status().value,
                "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
                "capabilities": {
                    "max_tokens": capabilities.max_tokens,
                    "supports_streaming": capabilities.supports_streaming,
                    "supports_functions": capabilities.supports_functions,
                    "supported_languages": capabilities.supported_languages,
                    "context_window": capabilities.context_window,
                    "supports_images": capabilities.supports_images,
                    "supports_audio": capabilities.supports_audio,
                    "cost_per_token": capabilities.cost_per_token,
                    "rate_limit_rpm": capabilities.rate_limit_rpm,
                    "rate_limit_tpm": capabilities.rate_limit_tpm
                },
                "performance_metrics": {
                    "total_requests": perf_metrics.get("total_requests", 0),
                    "success_rate": perf_metrics.get("success_rate", 0.0),
                    "avg_response_time_ms": perf_metrics.get("avg_response_time_ms", 0),
                    "recent_avg_response_time_ms": recent_perf.get("avg_response_time_ms", 0),
                    "recent_success_rate": recent_perf.get("success_rate", 0.0),
                    "total_tokens_used": perf_metrics.get("total_tokens_used", 0),
                    "last_request": perf_metrics.get("last_request"),
                    "last_success": perf_metrics.get("last_success"),
                    "last_error": perf_metrics.get("last_error"),
                    "last_error_message": perf_metrics.get("last_error_message")
                }
            }
        except Exception as e:
            logger.error(f"Error getting provider status: {e}")
            return {
                "provider_name": self._provider_name,
                "available": False,
                "initialized": True,
                "error": str(e),
                "performance_metrics": self._performance_tracker.get_provider_health_metrics(self._provider_name)
            }
    
    async def get_provider_health(self) -> Dict[str, Any]:
        """
        Get health check results for the selected provider with performance tracking
        
        Returns:
            Health check results with performance metrics
        """
        if not self._selected_provider:
            return {
                "status": "unhealthy",
                "provider": self._provider_name or "none",
                "error": "No provider initialized",
                "timestamp": datetime.utcnow().isoformat(),
                "response_time_ms": None
            }
        
        # Use performance tracker to time the health check
        with self._performance_tracker.start_operation(self._provider_name, "health_check") as timer:
            try:
                health_result = await self._selected_provider.health_check()
                timer.set_success(True)
                
                # Cache the result
                self._last_health_check = datetime.utcnow()
                self._last_health_status = health_result
                
                # Add performance metrics to the result
                perf_metrics = self._performance_tracker.get_provider_health_metrics(self._provider_name)
                health_result["performance_metrics"] = perf_metrics
                
                return health_result
                
            except Exception as e:
                timer.set_success(False, error=str(e))
                logger.error(f"Health check failed: {e}")
                
                error_result = {
                    "status": "unhealthy",
                    "provider": self._provider_name,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Add performance metrics even for failed health checks
                perf_metrics = self._performance_tracker.get_provider_health_metrics(self._provider_name)
                error_result["performance_metrics"] = perf_metrics
                
                return error_result
    
    def _get_selected_provider_name(self) -> Optional[str]:
        """
        Get the selected provider name from environment variables
        
        Returns:
            Provider name if set, None otherwise
        """
        # Check unified configuration first
        provider_name = os.getenv('LLM_PROVIDER')
        if provider_name:
            return provider_name.lower().strip()
        
        # Fall back to legacy configuration detection
        if os.getenv('GEMINI_API_KEY'):
            logger.info("Using Gemini provider (detected from GEMINI_API_KEY)")
            return 'gemini'
        elif os.getenv('OPENAI_API_KEY'):
            logger.info("Using OpenAI provider (detected from OPENAI_API_KEY)")
            return 'openai'
        elif os.getenv('ANTHROPIC_API_KEY'):
            logger.info("Using Anthropic provider (detected from ANTHROPIC_API_KEY)")
            return 'anthropic'
        elif os.getenv('OLLAMA_ENABLED', '').lower() == 'true':
            logger.info("Using Ollama provider (detected from OLLAMA_ENABLED)")
            return 'ollama'
        
        # Default to Gemini for backward compatibility
        logger.warning("No provider specified, defaulting to Gemini")
        return 'gemini'
    
    def _is_provider_supported(self, provider_name: str) -> bool:
        """
        Check if a provider is supported
        
        Args:
            provider_name: Name of the provider to check
            
        Returns:
            True if provider is supported, False otherwise
        """
        supported_providers = ['gemini', 'openai', 'anthropic', 'ollama', 'mock']
        return provider_name in supported_providers
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration
        
        Returns:
            Configuration summary
        """
        config_summary = self.config_manager.get_provider_availability_summary()
        
        return {
            "selected_provider": self._provider_name,
            "configuration_approach": config_summary.get('configuration_approach'),
            "available_providers": config_summary.get('enabled_providers', []),
            "provider_initialized": self._selected_provider is not None,
            "provider_available": self.is_provider_available(),
            "recommendations": self.config_manager.get_configuration_recommendations()
        }
    
    async def cleanup(self):
        """
        Cleanup provider resources
        
        This method should be called when shutting down the application.
        """
        try:
            if self._selected_provider:
                await self._selected_provider.cleanup()
                logger.info(f"Cleaned up provider: {self._provider_name}")
            
            await self.factory.cleanup_all_providers()
            
            self._selected_provider = None
            self._provider_name = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global provider selector instance
_provider_selector: Optional[ProviderSelector] = None


async def get_provider_selector() -> ProviderSelector:
    """
    Get the global provider selector instance
    
    Returns:
        ProviderSelector instance
    """
    global _provider_selector
    
    if _provider_selector is None:
        _provider_selector = ProviderSelector()
        await _provider_selector.initialize_selected_provider()
    
    return _provider_selector


async def get_selected_provider() -> Optional[LLMProvider]:
    """
    Get the currently selected LLM provider
    
    Returns:
        LLMProvider instance if available, None otherwise
    """
    selector = await get_provider_selector()
    return selector.get_selected_provider()


async def cleanup_provider_selector():
    """
    Cleanup the global provider selector
    
    This function should be called during application shutdown.
    """
    global _provider_selector
    
    if _provider_selector:
        await _provider_selector.cleanup()
        _provider_selector = None