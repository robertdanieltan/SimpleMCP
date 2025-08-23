"""Configuration manager for multi-LLM provider support."""

import os
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider."""
    name: str
    enabled: bool
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    timeout: int = 30
    extra_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """Complete LLM configuration for all providers."""
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    default_provider: Optional[str] = None
    session_timeout_hours: int = 24
    max_concurrent_sessions: int = 100
    
    def get_enabled_providers(self) -> List[str]:
        """Get list of enabled provider names."""
        return [name for name, config in self.providers.items() if config.enabled]
    
    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider."""
        return self.providers.get(provider_name)
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a provider is enabled."""
        config = self.get_provider_config(provider_name)
        return config is not None and config.enabled


class ConfigManager:
    """Manages configuration for multi-LLM provider support."""
    
    def __init__(self):
        self._config: Optional[LLMConfig] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        try:
            providers = {}
            
            # Check for new unified configuration first
            unified_config = self._load_unified_config()
            if unified_config:
                providers[unified_config.name] = unified_config
                logger.info(f"Using unified LLM configuration for provider: {unified_config.name}")
            else:
                # Fall back to legacy provider-specific configurations
                logger.info("No unified LLM configuration found, checking legacy provider-specific configs")
                
                # Gemini configuration
                gemini_config = self._load_gemini_config()
                if gemini_config:
                    providers['gemini'] = gemini_config
                
                # OpenAI configuration
                openai_config = self._load_openai_config()
                if openai_config:
                    providers['openai'] = openai_config
                
                # Anthropic configuration
                anthropic_config = self._load_anthropic_config()
                if anthropic_config:
                    providers['anthropic'] = anthropic_config
                
                # Ollama configuration
                ollama_config = self._load_ollama_config()
                if ollama_config:
                    providers['ollama'] = ollama_config
            
            # Determine default provider
            default_provider = self._determine_default_provider(providers)
            
            # Load general settings
            session_timeout = int(os.getenv('LLM_SESSION_TIMEOUT_HOURS', '24'))
            max_sessions = int(os.getenv('LLM_MAX_CONCURRENT_SESSIONS', '100'))
            
            self._config = LLMConfig(
                providers=providers,
                default_provider=default_provider,
                session_timeout_hours=session_timeout,
                max_concurrent_sessions=max_sessions
            )
            
            logger.info(f"Configuration loaded successfully. Enabled providers: {self._config.get_enabled_providers()}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Create minimal config with no providers enabled
            self._config = LLMConfig()
    
    def _load_gemini_config(self) -> Optional[ProviderConfig]:
        """Load Gemini provider configuration."""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.debug("GEMINI_API_KEY not found, Gemini provider disabled")
            return None
        
        return ProviderConfig(
            name='gemini',
            enabled=True,
            api_key=api_key,
            model=os.getenv('GEMINI_MODEL', 'gemini-pro'),
            temperature=float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('GEMINI_MAX_TOKENS', '1000')),
            timeout=int(os.getenv('GEMINI_TIMEOUT', '30')),
            extra_params={
                'safety_settings': os.getenv('GEMINI_SAFETY_SETTINGS', 'default')
            }
        )
    
    def _load_openai_config(self) -> Optional[ProviderConfig]:
        """Load OpenAI provider configuration."""
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.debug("OPENAI_API_KEY not found, OpenAI provider disabled")
            return None
        
        return ProviderConfig(
            name='openai',
            enabled=True,
            api_key=api_key,
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            base_url=os.getenv('OPENAI_BASE_URL'),  # Optional custom endpoint
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '1000')),
            timeout=int(os.getenv('OPENAI_TIMEOUT', '30')),
            extra_params={
                'organization': os.getenv('OPENAI_ORGANIZATION'),
                'max_retries': int(os.getenv('OPENAI_MAX_RETRIES', '3'))
            }
        )
    
    def _load_anthropic_config(self) -> Optional[ProviderConfig]:
        """Load Anthropic provider configuration."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            logger.debug("ANTHROPIC_API_KEY not found, Anthropic provider disabled")
            return None
        
        return ProviderConfig(
            name='anthropic',
            enabled=True,
            api_key=api_key,
            model=os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229'),
            base_url=os.getenv('ANTHROPIC_BASE_URL'),  # Optional custom endpoint
            temperature=float(os.getenv('ANTHROPIC_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('ANTHROPIC_MAX_TOKENS', '1000')),
            timeout=int(os.getenv('ANTHROPIC_TIMEOUT', '30')),
            extra_params={
                'max_retries': int(os.getenv('ANTHROPIC_MAX_RETRIES', '3'))
            }
        )
    
    def _load_ollama_config(self) -> Optional[ProviderConfig]:
        """Load Ollama provider configuration."""
        enabled = os.getenv('OLLAMA_ENABLED', 'false').lower() == 'true'
        if not enabled:
            logger.debug("OLLAMA_ENABLED not set to true, Ollama provider disabled")
            return None
        
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        
        # Validate URL format
        try:
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                logger.warning(f"Invalid OLLAMA_BASE_URL format: {base_url}, Ollama provider disabled")
                return None
        except Exception as e:
            logger.warning(f"Failed to parse OLLAMA_BASE_URL: {e}, Ollama provider disabled")
            return None
        
        return ProviderConfig(
            name='ollama',
            enabled=True,
            api_key=None,  # Ollama doesn't use API keys
            model=os.getenv('OLLAMA_MODEL', 'llama2'),
            base_url=base_url,
            temperature=float(os.getenv('OLLAMA_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('OLLAMA_MAX_TOKENS', '1000')),
            timeout=int(os.getenv('OLLAMA_TIMEOUT', '60')),  # Longer timeout for local models
            extra_params={
                'keep_alive': os.getenv('OLLAMA_KEEP_ALIVE', '5m'),
                'num_predict': int(os.getenv('OLLAMA_NUM_PREDICT', '-1'))
            }
        )
    
    def _load_unified_config(self) -> Optional[ProviderConfig]:
        """Load unified LLM configuration from environment variables."""
        provider_name = os.getenv('LLM_PROVIDER')
        if not provider_name:
            logger.debug("LLM_PROVIDER not set, skipping unified configuration")
            return None
        
        provider_name = provider_name.lower().strip()
        
        # Validate provider name (allow mock for testing)
        supported_providers = ['gemini', 'openai', 'anthropic', 'ollama', 'mock']
        if provider_name not in supported_providers:
            logger.warning(f"Unsupported LLM_PROVIDER: {provider_name}. Supported: {supported_providers}")
            return None
        
        # Get generic LLM configuration
        api_key = os.getenv('LLM_API_KEY')
        model = os.getenv('LLM_MODEL')
        base_url = os.getenv('LLM_BASE_URL')
        temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
        max_tokens = int(os.getenv('LLM_MAX_TOKENS', '1000'))
        timeout = int(os.getenv('LLM_TIMEOUT', '30'))
        
        # Provider-specific validation and defaults
        if provider_name in ['gemini', 'openai', 'anthropic'] and not api_key:
            logger.warning(f"LLM_API_KEY required for {provider_name} but not provided")
            return None
        
        if provider_name == 'ollama' and not base_url:
            base_url = 'http://localhost:11434'  # Default Ollama URL
        
        # Set default models if not specified
        if not model:
            default_models = {
                'gemini': 'gemini-pro',
                'openai': 'gpt-3.5-turbo',
                'anthropic': 'claude-3-sonnet-20240229',
                'ollama': 'llama2',
                'mock': 'mock-model-v1'
            }
            model = default_models.get(provider_name)
        
        # Build extra parameters based on provider
        extra_params = {}
        
        if provider_name == 'gemini':
            extra_params['safety_settings'] = os.getenv('LLM_SAFETY_SETTINGS', 'default')
        
        elif provider_name == 'openai':
            organization = os.getenv('LLM_ORGANIZATION')
            if organization:
                extra_params['organization'] = organization
            extra_params['max_retries'] = int(os.getenv('LLM_MAX_RETRIES', '3'))
        
        elif provider_name == 'anthropic':
            extra_params['max_retries'] = int(os.getenv('LLM_MAX_RETRIES', '3'))
        
        elif provider_name == 'ollama':
            extra_params['keep_alive'] = os.getenv('LLM_KEEP_ALIVE', '5m')
            extra_params['num_predict'] = int(os.getenv('LLM_NUM_PREDICT', '-1'))
            # Longer default timeout for local models
            if timeout == 30:  # If using default timeout
                timeout = 60
        
        elif provider_name == 'mock':
            # Mock provider specific settings
            extra_params['simulate_delay'] = float(os.getenv('LLM_SIMULATE_DELAY', '0.1'))
            extra_params['failure_rate'] = float(os.getenv('LLM_FAILURE_RATE', '0.0'))
        
        return ProviderConfig(
            name=provider_name,
            enabled=True,
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            extra_params=extra_params
        )
    
    def _determine_default_provider(self, providers: Dict[str, ProviderConfig]) -> Optional[str]:
        """Determine the default provider for backward compatibility."""
        # For backward compatibility, prefer Gemini if available
        if 'gemini' in providers and providers['gemini'].enabled:
            return 'gemini'
        
        # Otherwise, use the first enabled provider
        enabled_providers = [name for name, config in providers.items() if config.enabled]
        return enabled_providers[0] if enabled_providers else None
    
    @property
    def config(self) -> LLMConfig:
        """Get the current configuration."""
        if self._config is None:
            raise RuntimeError("Configuration not loaded")
        return self._config
    
    def reload_config(self) -> None:
        """Reload configuration from environment variables."""
        logger.info("Reloading configuration...")
        self._load_config()
    
    def validate_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """Validate configuration for a specific provider."""
        config = self.config.get_provider_config(provider_name)
        if not config:
            return {
                'valid': False,
                'error': f'Provider {provider_name} not configured'
            }
        
        if not config.enabled:
            return {
                'valid': False,
                'error': f'Provider {provider_name} is disabled'
            }
        
        # Provider-specific validation
        validation_result = self._validate_provider_specific(config)
        
        return {
            'valid': validation_result['valid'],
            'error': validation_result.get('error'),
            'warnings': validation_result.get('warnings', []),
            'config_summary': {
                'name': config.name,
                'model': config.model,
                'base_url': config.base_url,
                'timeout': config.timeout,
                'max_tokens': config.max_tokens,
                'temperature': config.temperature
            }
        }
    
    def _validate_provider_specific(self, config: ProviderConfig) -> Dict[str, Any]:
        """Perform provider-specific validation."""
        if config.name in ['gemini', 'openai', 'anthropic']:
            if not config.api_key:
                return {
                    'valid': False,
                    'error': f'{config.name.title()} API key is required but not provided'
                }
            
            if len(config.api_key.strip()) < 10:
                return {
                    'valid': False,
                    'error': f'{config.name.title()} API key appears to be invalid (too short)'
                }
        
        elif config.name == 'ollama':
            if not config.base_url:
                return {
                    'valid': False,
                    'error': 'Ollama base URL is required'
                }
            
            # Additional Ollama-specific validation could be added here
            warnings = []
            if config.timeout < 30:
                warnings.append('Ollama timeout is quite low, consider increasing for better reliability')
        
        # Common validation
        warnings = []
        if config.temperature < 0 or config.temperature > 2:
            warnings.append(f'Temperature {config.temperature} is outside typical range (0-2)')
        
        if config.max_tokens < 1 or config.max_tokens > 100000:
            warnings.append(f'Max tokens {config.max_tokens} is outside typical range (1-100000)')
        
        return {
            'valid': True,
            'warnings': warnings
        }
    
    def get_provider_availability_summary(self) -> Dict[str, Any]:
        """Get a summary of all provider availability and configuration status."""
        # Determine configuration approach
        using_unified = bool(os.getenv('LLM_PROVIDER'))
        
        summary = {
            'configuration_approach': 'unified' if using_unified else 'legacy',
            'total_providers': len(self.config.providers),
            'enabled_providers': len(self.config.get_enabled_providers()),
            'default_provider': self.config.default_provider,
            'providers': {}
        }
        
        if using_unified:
            summary['unified_provider'] = os.getenv('LLM_PROVIDER')
            summary['unified_model'] = os.getenv('LLM_MODEL')
        
        for provider_name in ['gemini', 'openai', 'anthropic', 'ollama']:
            config = self.config.get_provider_config(provider_name)
            if config:
                validation = self.validate_provider_config(provider_name)
                summary['providers'][provider_name] = {
                    'enabled': config.enabled,
                    'configured': True,
                    'valid': validation['valid'],
                    'model': config.model,
                    'error': validation.get('error'),
                    'warnings': validation.get('warnings', []),
                    'config_source': 'unified' if using_unified and provider_name == os.getenv('LLM_PROVIDER') else 'legacy'
                }
            else:
                summary['providers'][provider_name] = {
                    'enabled': False,
                    'configured': False,
                    'valid': False,
                    'model': None,
                    'error': 'Not configured',
                    'config_source': None
                }
        
        return summary
    
    def get_configuration_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for improving configuration."""
        recommendations = {
            'migration_needed': False,
            'suggestions': [],
            'current_approach': 'unified' if os.getenv('LLM_PROVIDER') else 'legacy'
        }
        
        # Check if using legacy configuration
        legacy_vars = ['GEMINI_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'OLLAMA_ENABLED']
        has_legacy = any(os.getenv(var) for var in legacy_vars)
        has_unified = bool(os.getenv('LLM_PROVIDER'))
        
        if has_legacy and not has_unified:
            recommendations['migration_needed'] = True
            recommendations['suggestions'].append(
                "Consider migrating to unified LLM configuration using LLM_PROVIDER and LLM_API_KEY"
            )
            recommendations['suggestions'].append(
                "Unified configuration is simpler and more flexible for switching between providers"
            )
        
        if has_unified and has_legacy:
            recommendations['suggestions'].append(
                "Both unified and legacy configurations detected. Unified takes precedence."
            )
            recommendations['suggestions'].append(
                "Consider removing legacy environment variables to avoid confusion"
            )
        
        if not has_unified and not has_legacy:
            recommendations['suggestions'].append(
                "No LLM provider configuration found. Set LLM_PROVIDER and LLM_API_KEY to get started."
            )
        
        return recommendations