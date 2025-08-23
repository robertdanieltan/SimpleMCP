"""
Integration example showing how the configuration management system
integrates with the existing AI Agent architecture.

This demonstrates how the new multi-LLM configuration system can be used
alongside the existing codebase without breaking changes.
"""

import asyncio
import logging
from typing import Dict, Any

from .manager import ConfigManager
from .validation import ProviderValidator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigurationIntegrationDemo:
    """Demonstrates integration of configuration management with existing systems."""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.validator = ProviderValidator(self.config_manager)
    
    def demonstrate_backward_compatibility(self):
        """Show how the system maintains backward compatibility."""
        print("=" * 60)
        print("Backward Compatibility Demonstration")
        print("=" * 60)
        
        # Show that existing Gemini-only setups continue to work
        config = self.config_manager.config
        
        print(f"Default provider: {config.default_provider}")
        print(f"Enabled providers: {config.get_enabled_providers()}")
        
        # Demonstrate how existing code can continue to work
        if config.is_provider_enabled('gemini'):
            gemini_config = config.get_provider_config('gemini')
            print(f"\nGemini configuration (backward compatible):")
            print(f"  API Key configured: {'Yes' if gemini_config.api_key else 'No'}")
            print(f"  Model: {gemini_config.model}")
            print(f"  Temperature: {gemini_config.temperature}")
            print(f"  Max tokens: {gemini_config.max_tokens}")
        
        print("\n✓ Existing Gemini-only configurations work unchanged")
    
    async def demonstrate_multi_provider_support(self):
        """Show multi-provider capabilities."""
        print("\n" + "=" * 60)
        print("Multi-Provider Support Demonstration")
        print("=" * 60)
        
        config = self.config_manager.config
        enabled_providers = config.get_enabled_providers()
        
        if len(enabled_providers) > 1:
            print(f"Multiple providers detected: {enabled_providers}")
            
            # Validate all providers
            validation_results = await self.validator.validate_all_providers()
            
            for provider_name, result in validation_results.items():
                status = "✓" if result['available'] else "✗"
                print(f"{status} {provider_name.upper()}: {result.get('note', result.get('error', 'Available'))}")
        
        elif len(enabled_providers) == 1:
            print(f"Single provider mode: {enabled_providers[0]}")
            print("✓ Ready for multi-provider expansion")
        
        else:
            print("No providers configured")
            print("⚠ Configure at least one provider to use the AI agent")
    
    def demonstrate_configuration_validation(self):
        """Show configuration validation capabilities."""
        print("\n" + "=" * 60)
        print("Configuration Validation Demonstration")
        print("=" * 60)
        
        # Test each provider's configuration
        providers = ['gemini', 'openai', 'anthropic', 'ollama']
        
        for provider_name in providers:
            validation = self.config_manager.validate_provider_config(provider_name)
            status = "✓" if validation['valid'] else "✗"
            
            print(f"{status} {provider_name.upper()}: ", end="")
            
            if validation['valid']:
                config_summary = validation.get('config_summary', {})
                print(f"Valid (model: {config_summary.get('model', 'N/A')})")
                
                warnings = validation.get('warnings', [])
                for warning in warnings:
                    print(f"    ⚠ {warning}")
            else:
                print(f"Invalid - {validation.get('error', 'Unknown error')}")
    
    def demonstrate_environment_based_configuration(self):
        """Show how environment variables control configuration."""
        print("\n" + "=" * 60)
        print("Environment-Based Configuration")
        print("=" * 60)
        
        print("Configuration is loaded from environment variables:")
        print("  GEMINI_API_KEY     - Enables Gemini provider")
        print("  OPENAI_API_KEY     - Enables OpenAI provider")
        print("  ANTHROPIC_API_KEY  - Enables Anthropic provider")
        print("  OLLAMA_ENABLED     - Enables Ollama provider")
        print()
        print("Additional configuration options:")
        print("  *_MODEL           - Specify model for each provider")
        print("  *_TEMPERATURE     - Control response creativity")
        print("  *_MAX_TOKENS      - Limit response length")
        print("  *_TIMEOUT         - Set request timeout")
        print()
        print("Session management:")
        print("  LLM_SESSION_TIMEOUT_HOURS    - Session expiration")
        print("  LLM_MAX_CONCURRENT_SESSIONS  - Concurrent session limit")
    
    def demonstrate_provider_capabilities(self):
        """Show provider-specific capabilities and features."""
        print("\n" + "=" * 60)
        print("Provider Capabilities Overview")
        print("=" * 60)
        
        capabilities = {
            'gemini': {
                'strengths': ['Multimodal', 'Fast responses', 'Good reasoning'],
                'use_cases': ['General chat', 'Code analysis', 'Creative tasks']
            },
            'openai': {
                'strengths': ['Excellent reasoning', 'Function calling', 'Reliable'],
                'use_cases': ['Complex analysis', 'Structured output', 'Professional tasks']
            },
            'anthropic': {
                'strengths': ['Safety-focused', 'Long context', 'Helpful responses'],
                'use_cases': ['Document analysis', 'Ethical reasoning', 'Research tasks']
            },
            'ollama': {
                'strengths': ['Privacy', 'Offline operation', 'Cost-effective'],
                'use_cases': ['Local deployment', 'Sensitive data', 'Development testing']
            }
        }
        
        for provider, info in capabilities.items():
            config = self.config_manager.config.get_provider_config(provider)
            status = "✓ Configured" if config and config.enabled else "✗ Not configured"
            
            print(f"\n{provider.upper()} {status}")
            print(f"  Strengths: {', '.join(info['strengths'])}")
            print(f"  Use cases: {', '.join(info['use_cases'])}")
            
            if config and config.enabled:
                print(f"  Model: {config.model}")
                print(f"  Temperature: {config.temperature}")


async def main():
    """Run the integration demonstration."""
    demo = ConfigurationIntegrationDemo()
    
    # Run all demonstrations
    demo.demonstrate_backward_compatibility()
    await demo.demonstrate_multi_provider_support()
    demo.demonstrate_configuration_validation()
    demo.demonstrate_environment_based_configuration()
    demo.demonstrate_provider_capabilities()
    
    print("\n" + "=" * 60)
    print("Integration Demonstration Complete")
    print("=" * 60)
    print("\nKey Benefits:")
    print("✓ Backward compatibility maintained")
    print("✓ Multi-provider support ready")
    print("✓ Environment-based configuration")
    print("✓ Comprehensive validation")
    print("✓ Provider-specific optimizations")
    print("\nNext Steps:")
    print("1. Configure desired providers via environment variables")
    print("2. Update AI Agent to use provider factory (future task)")
    print("3. Implement session-based provider selection (future task)")


if __name__ == "__main__":
    asyncio.run(main())