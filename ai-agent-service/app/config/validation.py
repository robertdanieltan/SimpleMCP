"""Provider validation utilities for configuration management."""

import asyncio
import logging
import time
import httpx
from typing import Dict, Any, Optional
from urllib.parse import urljoin

from .manager import ConfigManager, ProviderConfig

logger = logging.getLogger(__name__)


class ProviderValidator:
    """Validates provider availability and configuration."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.timeout = 10  # Default timeout for validation checks
    
    async def validate_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """Validate all configured providers."""
        results = {}
        enabled_providers = self.config_manager.config.get_enabled_providers()
        
        if not enabled_providers:
            logger.warning("No providers are enabled")
            return results
        
        # Run validations concurrently
        tasks = []
        for provider_name in enabled_providers:
            task = asyncio.create_task(
                self._validate_single_provider(provider_name),
                name=f"validate_{provider_name}"
            )
            tasks.append((provider_name, task))
        
        # Wait for all validations to complete
        for provider_name, task in tasks:
            try:
                result = await task
                results[provider_name] = result
            except Exception as e:
                logger.error(f"Validation failed for {provider_name}: {e}")
                results[provider_name] = {
                    'available': False,
                    'error': f'Validation exception: {str(e)}',
                    'response_time_ms': None
                }
        
        return results
    
    async def _validate_single_provider(self, provider_name: str) -> Dict[str, Any]:
        """Validate a single provider's availability."""
        config = self.config_manager.config.get_provider_config(provider_name)
        if not config:
            return {
                'available': False,
                'error': 'Provider not configured',
                'response_time_ms': None
            }
        
        # First check configuration validity
        config_validation = self.config_manager.validate_provider_config(provider_name)
        if not config_validation['valid']:
            return {
                'available': False,
                'error': config_validation['error'],
                'response_time_ms': None
            }
        
        # Then check actual availability
        if provider_name == 'ollama':
            return await self._validate_ollama(config)
        elif provider_name in ['gemini', 'openai', 'anthropic']:
            return await self._validate_api_provider(provider_name, config)
        else:
            return {
                'available': False,
                'error': f'Unknown provider type: {provider_name}',
                'response_time_ms': None
            }
    
    async def _validate_ollama(self, config: ProviderConfig) -> Dict[str, Any]:
        """Validate Ollama provider availability."""
        try:
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Check if Ollama is running
                health_url = urljoin(config.base_url, '/api/tags')
                response = await client.get(health_url)
                
                response_time_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    data = response.json()
                    models = data.get('models', [])
                    
                    # Check if the configured model is available
                    model_names = [model.get('name', '') for model in models]
                    model_available = any(config.model in name for name in model_names)
                    
                    if not model_available and models:
                        return {
                            'available': True,
                            'warning': f'Configured model "{config.model}" not found. Available models: {model_names}',
                            'response_time_ms': response_time_ms,
                            'available_models': model_names
                        }
                    elif not models:
                        return {
                            'available': True,
                            'warning': 'No models are currently loaded in Ollama',
                            'response_time_ms': response_time_ms,
                            'available_models': []
                        }
                    else:
                        return {
                            'available': True,
                            'response_time_ms': response_time_ms,
                            'available_models': model_names
                        }
                else:
                    return {
                        'available': False,
                        'error': f'Ollama health check failed with status {response.status_code}',
                        'response_time_ms': response_time_ms
                    }
        
        except httpx.TimeoutException:
            return {
                'available': False,
                'error': f'Ollama connection timeout after {self.timeout}s',
                'response_time_ms': None
            }
        except httpx.ConnectError:
            return {
                'available': False,
                'error': f'Cannot connect to Ollama at {config.base_url}',
                'response_time_ms': None
            }
        except Exception as e:
            return {
                'available': False,
                'error': f'Ollama validation error: {str(e)}',
                'response_time_ms': None
            }
    
    async def _validate_api_provider(self, provider_name: str, config: ProviderConfig) -> Dict[str, Any]:
        """Validate API-based providers (Gemini, OpenAI, Anthropic)."""
        try:
            start_time = time.time()
            
            # For API providers, we'll do a simple connectivity check
            # without making actual API calls to avoid costs during validation
            
            if provider_name == 'gemini':
                return await self._validate_gemini_connectivity(config, start_time)
            elif provider_name == 'openai':
                return await self._validate_openai_connectivity(config, start_time)
            elif provider_name == 'anthropic':
                return await self._validate_anthropic_connectivity(config, start_time)
            else:
                return {
                    'available': False,
                    'error': f'Unknown API provider: {provider_name}',
                    'response_time_ms': None
                }
        
        except Exception as e:
            return {
                'available': False,
                'error': f'{provider_name.title()} validation error: {str(e)}',
                'response_time_ms': None
            }
    
    async def _validate_gemini_connectivity(self, config: ProviderConfig, start_time: float) -> Dict[str, Any]:
        """Validate Gemini API connectivity."""
        try:
            # For Gemini, we can check if the API key format is valid
            # and potentially make a lightweight API call
            
            if not config.api_key or len(config.api_key.strip()) < 20:
                return {
                    'available': False,
                    'error': 'Gemini API key appears invalid (too short)',
                    'response_time_ms': None
                }
            
            # Basic format validation for Gemini API keys
            if not config.api_key.startswith('AI'):
                return {
                    'available': False,
                    'error': 'Gemini API key format appears invalid',
                    'response_time_ms': None
                }
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'available': True,
                'response_time_ms': response_time_ms,
                'note': 'Configuration validated, actual API connectivity not tested to avoid costs'
            }
        
        except Exception as e:
            return {
                'available': False,
                'error': f'Gemini validation error: {str(e)}',
                'response_time_ms': None
            }
    
    async def _validate_openai_connectivity(self, config: ProviderConfig, start_time: float) -> Dict[str, Any]:
        """Validate OpenAI API connectivity."""
        try:
            # Basic API key format validation for OpenAI
            if not config.api_key or len(config.api_key.strip()) < 20:
                return {
                    'available': False,
                    'error': 'OpenAI API key appears invalid (too short)',
                    'response_time_ms': None
                }
            
            # OpenAI API keys typically start with 'sk-'
            if not config.api_key.startswith('sk-'):
                return {
                    'available': False,
                    'error': 'OpenAI API key format appears invalid (should start with sk-)',
                    'response_time_ms': None
                }
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'available': True,
                'response_time_ms': response_time_ms,
                'note': 'Configuration validated, actual API connectivity not tested to avoid costs'
            }
        
        except Exception as e:
            return {
                'available': False,
                'error': f'OpenAI validation error: {str(e)}',
                'response_time_ms': None
            }
    
    async def _validate_anthropic_connectivity(self, config: ProviderConfig, start_time: float) -> Dict[str, Any]:
        """Validate Anthropic API connectivity."""
        try:
            # Basic API key format validation for Anthropic
            if not config.api_key or len(config.api_key.strip()) < 20:
                return {
                    'available': False,
                    'error': 'Anthropic API key appears invalid (too short)',
                    'response_time_ms': None
                }
            
            # Anthropic API keys typically start with 'sk-ant-'
            if not config.api_key.startswith('sk-ant-'):
                return {
                    'available': False,
                    'error': 'Anthropic API key format appears invalid (should start with sk-ant-)',
                    'response_time_ms': None
                }
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                'available': True,
                'response_time_ms': response_time_ms,
                'note': 'Configuration validated, actual API connectivity not tested to avoid costs'
            }
        
        except Exception as e:
            return {
                'available': False,
                'error': f'Anthropic validation error: {str(e)}',
                'response_time_ms': None
            }
    
    async def quick_health_check(self, provider_name: str) -> bool:
        """Quick health check for a specific provider."""
        try:
            result = await self._validate_single_provider(provider_name)
            return result.get('available', False)
        except Exception as e:
            logger.error(f"Quick health check failed for {provider_name}: {e}")
            return False