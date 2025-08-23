"""
LLM Provider Factory

This module implements the factory pattern for creating and managing LLM providers,
enabling dynamic provider instantiation and lifecycle management.
"""

import logging
import importlib
import inspect
from typing import Dict, Any, Optional, List, Type
from datetime import datetime, timedelta

from .base import LLMProvider, ProviderStatus, ErrorResponse
from .exceptions import (
    ProviderInitializationError,
    ProviderConfigurationError,
    ProviderUnavailableError
)

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for creating and managing LLM providers
    
    This class handles provider registration, instantiation, health monitoring,
    and lifecycle management for all supported LLM providers.
    """
    
    def __init__(self, config_manager=None):
        """
        Initialize the provider factory
        
        Args:
            config_manager: Configuration manager instance (optional)
        """
        self.config_manager = config_manager
        self._providers: Dict[str, LLMProvider] = {}
        self._provider_classes: Dict[str, Type[LLMProvider]] = {}
        self._initialization_status: Dict[str, bool] = {}
        self._health_check_interval = timedelta(minutes=5)
        self._last_health_checks: Dict[str, datetime] = {}
        self._discovery_paths = [
            'app.llm.providers',
            'ai-agent-service.app.llm.providers'
        ]
        
        # Auto-discover and register providers on initialization
        self._discover_providers()
        
        logger.info("LLM Provider Factory initialized")
    
    def register_provider(self, provider_name: str, provider_class: Type[LLMProvider]):
        """
        Register a provider class with the factory
        
        Args:
            provider_name: Unique name for the provider (e.g., 'gemini', 'openai')
            provider_class: Provider class that implements LLMProvider interface
        """
        if not issubclass(provider_class, LLMProvider):
            raise ValueError(f"Provider class {provider_class} must inherit from LLMProvider")
        
        if provider_name in self._provider_classes:
            logger.warning(f"Provider {provider_name} is already registered, overwriting")
        
        self._provider_classes[provider_name] = provider_class
        logger.info(f"Registered provider: {provider_name}")
    
    def _discover_providers(self):
        """
        Automatically discover and register provider classes
        
        This method searches for provider implementations in known locations
        and automatically registers them with the factory.
        """
        discovered_count = 0
        
        for module_path in self._discovery_paths:
            try:
                discovered_count += self._discover_providers_in_module(module_path)
            except ImportError:
                logger.debug(f"Provider discovery path not found: {module_path}")
            except Exception as e:
                logger.warning(f"Error during provider discovery in {module_path}: {e}")
        
        logger.info(f"Provider discovery complete. Found {discovered_count} providers")
    
    def _discover_providers_in_module(self, module_path: str) -> int:
        """
        Discover providers in a specific module path
        
        Args:
            module_path: Python module path to search for providers
            
        Returns:
            Number of providers discovered and registered
        """
        try:
            module = importlib.import_module(module_path)
            discovered_count = 0
            
            # Look for classes that inherit from LLMProvider
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, LLMProvider) and 
                    obj != LLMProvider and 
                    hasattr(obj, '__module__') and 
                    obj.__module__.startswith(module_path)):
                    
                    # Extract provider name from class name
                    provider_name = self._extract_provider_name(name)
                    
                    if provider_name:
                        self.register_provider(provider_name, obj)
                        discovered_count += 1
            
            return discovered_count
            
        except ImportError:
            # Module doesn't exist, which is fine
            return 0
        except Exception as e:
            logger.error(f"Error discovering providers in {module_path}: {e}")
            return 0
    
    def _extract_provider_name(self, class_name: str) -> Optional[str]:
        """
        Extract provider name from class name
        
        Args:
            class_name: Name of the provider class
            
        Returns:
            Provider name or None if not a valid provider class name
        """
        # Convert class names like "GeminiProvider" to "gemini"
        if class_name.endswith('Provider'):
            provider_name = class_name[:-8].lower()  # Remove 'Provider' suffix
            return provider_name if provider_name else None
        
        # Handle other naming patterns if needed
        return None
    
    def register_provider_from_config(self, provider_name: str, provider_config: Dict[str, Any]):
        """
        Register a provider using configuration-based discovery
        
        Args:
            provider_name: Name of the provider
            provider_config: Provider configuration dictionary
        """
        if not self.config_manager:
            logger.warning("Cannot register provider from config: no config manager available")
            return
        
        # Try to find and register the provider class
        provider_class = self._find_provider_class(provider_name)
        if provider_class:
            self.register_provider(provider_name, provider_class)
        else:
            logger.warning(f"Provider class not found for: {provider_name}")
    
    def _find_provider_class(self, provider_name: str) -> Optional[Type[LLMProvider]]:
        """
        Find provider class by name using various naming conventions
        
        Args:
            provider_name: Name of the provider to find
            
        Returns:
            Provider class if found, None otherwise
        """
        # Try different naming conventions
        possible_names = [
            f"{provider_name.title()}Provider",
            f"{provider_name.upper()}Provider",
            f"{provider_name.capitalize()}Provider"
        ]
        
        for module_path in self._discovery_paths:
            try:
                module = importlib.import_module(module_path)
                
                for class_name in possible_names:
                    if hasattr(module, class_name):
                        provider_class = getattr(module, class_name)
                        if issubclass(provider_class, LLMProvider):
                            return provider_class
                            
            except ImportError:
                continue
            except Exception as e:
                logger.debug(f"Error searching for provider {provider_name} in {module_path}: {e}")
        
        return None
    
    async def initialize_providers(self, provider_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Initialize all configured providers
        
        Args:
            provider_configs: Dictionary mapping provider names to their configurations.
                            If None, will use config_manager if available.
            
        Returns:
            Dictionary mapping provider names to initialization success status
        """
        # Use config manager if no explicit configs provided
        if provider_configs is None and self.config_manager:
            provider_configs = self._get_configs_from_manager()
        elif provider_configs is None:
            logger.warning("No provider configurations available for initialization")
            return {}
        
        initialization_results = {}
        
        for provider_name, config in provider_configs.items():
            initialization_results[provider_name] = await self._initialize_single_provider(
                provider_name, config
            )
        
        logger.info(f"Provider initialization complete. Results: {initialization_results}")
        return initialization_results
    
    def _get_configs_from_manager(self) -> Dict[str, Dict[str, Any]]:
        """
        Get provider configurations from the config manager
        
        Returns:
            Dictionary mapping provider names to their configurations
        """
        if not self.config_manager:
            return {}
        
        configs = {}
        for provider_name in self.config_manager.config.providers.keys():
            provider_config = self.config_manager.config.get_provider_config(provider_name)
            if provider_config and provider_config.enabled:
                # Convert ProviderConfig to dictionary
                configs[provider_name] = {
                    'name': provider_config.name,
                    'api_key': provider_config.api_key,
                    'model': provider_config.model,
                    'base_url': provider_config.base_url,
                    'temperature': provider_config.temperature,
                    'max_tokens': provider_config.max_tokens,
                    'timeout': provider_config.timeout,
                    **provider_config.extra_params
                }
        
        return configs
    
    async def _initialize_single_provider(self, provider_name: str, config: Dict[str, Any]) -> bool:
        """
        Initialize a single provider
        
        Args:
            provider_name: Name of the provider to initialize
            config: Provider configuration
            
        Returns:
            True if initialization successful, False otherwise
        """
        if provider_name not in self._provider_classes:
            logger.warning(f"Provider {provider_name} not registered, attempting discovery")
            self.register_provider_from_config(provider_name, config)
            
            if provider_name not in self._provider_classes:
                logger.error(f"Provider {provider_name} not found after discovery")
                self._initialization_status[provider_name] = False
                return False
        
        try:
            # Create provider instance
            provider_class = self._provider_classes[provider_name]
            provider_instance = provider_class(config)
            
            # Initialize the provider
            success = await provider_instance.initialize()
            
            if success:
                self._providers[provider_name] = provider_instance
                self._initialization_status[provider_name] = True
                logger.info(f"Successfully initialized provider: {provider_name}")
            else:
                self._initialization_status[provider_name] = False
                logger.error(f"Failed to initialize provider: {provider_name}")
            
            return success
            
        except ProviderConfigurationError as e:
            logger.error(f"Configuration error for provider {provider_name}: {e}")
            self._initialization_status[provider_name] = False
            return False
        except ProviderInitializationError as e:
            logger.error(f"Initialization error for provider {provider_name}: {e}")
            self._initialization_status[provider_name] = False
            return False
        except Exception as e:
            logger.error(f"Unexpected error initializing provider {provider_name}: {e}")
            self._initialization_status[provider_name] = False
            return False
    
    def get_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """
        Get a specific provider instance
        
        Args:
            provider_name: Name of the provider to retrieve
            
        Returns:
            Provider instance if available, None otherwise
        """
        if provider_name not in self._providers:
            logger.warning(f"Provider {provider_name} not found or not initialized")
            return None
        
        provider = self._providers[provider_name]
        if not provider.is_available():
            logger.warning(f"Provider {provider_name} is not available")
            return None
        
        return provider
    
    def list_available_providers(self) -> List[str]:
        """
        List all available and configured providers
        
        Returns:
            List of provider names that are available for use
        """
        available_providers = []
        
        for provider_name, provider in self._providers.items():
            if provider.is_available():
                available_providers.append(provider_name)
        
        return available_providers
    
    def list_registered_providers(self) -> List[str]:
        """
        List all registered provider classes
        
        Returns:
            List of all registered provider names
        """
        return list(self._provider_classes.keys())
    
    def list_initialized_providers(self) -> List[str]:
        """
        List all initialized providers (regardless of availability)
        
        Returns:
            List of provider names that have been initialized
        """
        return list(self._providers.keys())
    
    async def validate_provider(self, provider_name: str) -> bool:
        """
        Validate that a provider is available and working
        
        Args:
            provider_name: Name of the provider to validate
            
        Returns:
            True if provider is available and healthy, False otherwise
        """
        provider = self.get_provider(provider_name)
        if not provider:
            return False
        
        try:
            health_result = await provider.health_check()
            return health_result.get("status") == "healthy"
        except Exception as e:
            logger.error(f"Health check failed for provider {provider_name}: {e}")
            return False
    
    async def health_check_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health checks on all initialized providers
        
        Returns:
            Dictionary mapping provider names to their health check results
        """
        health_results = {}
        
        for provider_name, provider in self._providers.items():
            try:
                health_result = await provider.health_check()
                health_results[provider_name] = health_result
                self._last_health_checks[provider_name] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Health check failed for provider {provider_name}: {e}")
                health_results[provider_name] = {
                    "status": "unhealthy",
                    "provider": provider_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                    "details": {"exception": type(e).__name__}
                }
        
        return health_results
    
    def get_provider_capabilities(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """
        Get capabilities for a specific provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider capabilities as dictionary, None if provider not found
        """
        provider = self.get_provider(provider_name)
        if not provider:
            return None
        
        try:
            capabilities = provider.get_capabilities()
            return {
                "max_tokens": capabilities.max_tokens,
                "supports_streaming": capabilities.supports_streaming,
                "supports_functions": capabilities.supports_functions,
                "supported_languages": capabilities.supported_languages,
                "cost_per_token": capabilities.cost_per_token,
                "context_window": capabilities.context_window,
                "supports_images": capabilities.supports_images,
                "supports_audio": capabilities.supports_audio,
                "rate_limit_rpm": capabilities.rate_limit_rpm,
                "rate_limit_tpm": capabilities.rate_limit_tpm
            }
        except Exception as e:
            logger.error(f"Failed to get capabilities for provider {provider_name}: {e}")
            return None
    
    def get_factory_status(self) -> Dict[str, Any]:
        """
        Get comprehensive factory status including all providers
        
        Returns:
            Factory status information
        """
        return {
            "factory_status": "operational",
            "timestamp": datetime.utcnow().isoformat(),
            "registered_providers": self.list_registered_providers(),
            "initialized_providers": self.list_initialized_providers(),
            "available_providers": self.list_available_providers(),
            "initialization_status": self._initialization_status.copy(),
            "last_health_checks": {
                name: timestamp.isoformat() if timestamp else None
                for name, timestamp in self._last_health_checks.items()
            }
        }
    
    async def reinitialize_provider(self, provider_name: str) -> bool:
        """
        Reinitialize a specific provider
        
        Args:
            provider_name: Name of the provider to reinitialize
            
        Returns:
            True if reinitialization successful, False otherwise
        """
        if provider_name not in self._provider_classes:
            logger.error(f"Cannot reinitialize unregistered provider: {provider_name}")
            return False
        
        # Cleanup existing instance if it exists
        if provider_name in self._providers:
            try:
                await self._providers[provider_name].cleanup()
            except Exception as e:
                logger.warning(f"Error during cleanup of {provider_name}: {e}")
            
            del self._providers[provider_name]
        
        # Get configuration and reinitialize
        if self.config_manager:
            provider_config = self.config_manager.config.get_provider_config(provider_name)
            if provider_config and provider_config.enabled:
                config_dict = {
                    'name': provider_config.name,
                    'api_key': provider_config.api_key,
                    'model': provider_config.model,
                    'base_url': provider_config.base_url,
                    'temperature': provider_config.temperature,
                    'max_tokens': provider_config.max_tokens,
                    'timeout': provider_config.timeout,
                    **provider_config.extra_params
                }
                
                return await self._initialize_single_provider(provider_name, config_dict)
        
        logger.error(f"No configuration available for provider: {provider_name}")
        return False
    
    async def shutdown_provider(self, provider_name: str) -> bool:
        """
        Shutdown and remove a specific provider
        
        Args:
            provider_name: Name of the provider to shutdown
            
        Returns:
            True if shutdown successful, False otherwise
        """
        if provider_name not in self._providers:
            logger.warning(f"Provider {provider_name} not found for shutdown")
            return False
        
        try:
            await self._providers[provider_name].cleanup()
            del self._providers[provider_name]
            self._initialization_status[provider_name] = False
            
            if provider_name in self._last_health_checks:
                del self._last_health_checks[provider_name]
            
            logger.info(f"Successfully shutdown provider: {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error shutting down provider {provider_name}: {e}")
            return False
    
    async def reload_providers(self) -> Dict[str, bool]:
        """
        Reload all providers from current configuration
        
        Returns:
            Dictionary mapping provider names to reload success status
        """
        logger.info("Reloading all providers...")
        
        # Cleanup existing providers
        await self.cleanup_all_providers()
        
        # Reload configuration if config manager is available
        if self.config_manager:
            self.config_manager.reload_config()
        
        # Reinitialize providers
        return await self.initialize_providers()
    
    def get_provider_lifecycle_status(self, provider_name: str) -> Dict[str, Any]:
        """
        Get lifecycle status for a specific provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider lifecycle status information
        """
        status = {
            'provider_name': provider_name,
            'registered': provider_name in self._provider_classes,
            'initialized': provider_name in self._providers,
            'available': False,
            'last_health_check': None,
            'initialization_status': self._initialization_status.get(provider_name, False)
        }
        
        if provider_name in self._providers:
            provider = self._providers[provider_name]
            status['available'] = provider.is_available()
            status['health_status'] = provider.get_health_status().value
            
            last_check = provider.get_last_health_check()
            if last_check:
                status['last_health_check'] = last_check.isoformat()
        
        return status
    
    def get_all_lifecycle_status(self) -> Dict[str, Any]:
        """
        Get lifecycle status for all providers
        
        Returns:
            Complete lifecycle status information
        """
        return {
            'factory_status': 'operational',
            'timestamp': datetime.utcnow().isoformat(),
            'registered_providers': list(self._provider_classes.keys()),
            'initialized_providers': list(self._providers.keys()),
            'available_providers': self.list_available_providers(),
            'provider_details': {
                name: self.get_provider_lifecycle_status(name)
                for name in self._provider_classes.keys()
            }
        }
    
    async def cleanup_all_providers(self):
        """
        Cleanup all provider resources
        
        This method should be called when shutting down the application
        to ensure proper cleanup of provider resources.
        """
        logger.info("Cleaning up all providers...")
        
        cleanup_results = {}
        for provider_name, provider in self._providers.items():
            try:
                await provider.cleanup()
                cleanup_results[provider_name] = True
                logger.info(f"Cleaned up provider: {provider_name}")
            except Exception as e:
                cleanup_results[provider_name] = False
                logger.error(f"Error cleaning up provider {provider_name}: {e}")
        
        self._providers.clear()
        self._initialization_status.clear()
        self._last_health_checks.clear()
        
        logger.info(f"Provider cleanup complete. Results: {cleanup_results}")
        return cleanup_results
    
    def _should_perform_health_check(self, provider_name: str) -> bool:
        """
        Check if a health check should be performed for a provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            True if health check should be performed, False otherwise
        """
        if provider_name not in self._last_health_checks:
            return True
        
        last_check = self._last_health_checks[provider_name]
        return datetime.utcnow() - last_check > self._health_check_interval
    
    async def periodic_health_check(self):
        """
        Perform periodic health checks on providers that need it
        
        This method can be called periodically to maintain provider health status.
        """
        providers_to_check = [
            name for name in self._providers.keys()
            if self._should_perform_health_check(name)
        ]
        
        if providers_to_check:
            logger.info(f"Performing periodic health checks for: {providers_to_check}")
            
            for provider_name in providers_to_check:
                try:
                    provider = self._providers[provider_name]
                    await provider.health_check()
                    self._last_health_checks[provider_name] = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Periodic health check failed for {provider_name}: {e}")