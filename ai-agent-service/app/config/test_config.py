"""Test script for configuration management system."""

import os
import asyncio
import logging
from typing import Dict, Any

from .manager import ConfigManager
from .validation import ProviderValidator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_configuration_system():
    """Test the configuration management system."""
    print("=" * 60)
    print("Testing Multi-LLM Configuration Management System")
    print("=" * 60)
    
    # Initialize configuration manager
    print("\n1. Initializing Configuration Manager...")
    config_manager = ConfigManager()
    
    # Display configuration summary
    print("\n2. Configuration Summary:")
    summary = config_manager.get_provider_availability_summary()
    print(f"   Total providers: {summary['total_providers']}")
    print(f"   Enabled providers: {summary['enabled_providers']}")
    print(f"   Default provider: {summary['default_provider']}")
    
    print("\n3. Provider Details:")
    for provider_name, details in summary['providers'].items():
        status = "✓" if details['enabled'] and details['configured'] else "✗"
        print(f"   {status} {provider_name.upper()}: "
              f"configured={details['configured']}, "
              f"enabled={details['enabled']}, "
              f"model={details['model']}")
        
        if details.get('error'):
            print(f"     Error: {details['error']}")
        
        if details.get('warnings'):
            for warning in details['warnings']:
                print(f"     Warning: {warning}")
    
    # Test provider validation
    print("\n4. Testing Provider Validation...")
    validator = ProviderValidator(config_manager)
    
    enabled_providers = config_manager.config.get_enabled_providers()
    if enabled_providers:
        print(f"   Validating {len(enabled_providers)} enabled providers...")
        validation_results = await validator.validate_all_providers()
        
        for provider_name, result in validation_results.items():
            status = "✓" if result['available'] else "✗"
            response_time = result.get('response_time_ms', 'N/A')
            print(f"   {status} {provider_name.upper()}: "
                  f"available={result['available']}, "
                  f"response_time={response_time}ms")
            
            if result.get('error'):
                print(f"     Error: {result['error']}")
            
            if result.get('warning'):
                print(f"     Warning: {result['warning']}")
            
            if result.get('note'):
                print(f"     Note: {result['note']}")
    else:
        print("   No providers are enabled for validation")
    
    # Test configuration validation
    print("\n5. Testing Configuration Validation...")
    for provider_name in ['gemini', 'openai', 'anthropic', 'ollama']:
        validation = config_manager.validate_provider_config(provider_name)
        status = "✓" if validation['valid'] else "✗"
        print(f"   {status} {provider_name.upper()}: valid={validation['valid']}")
        
        if validation.get('error'):
            print(f"     Error: {validation['error']}")
        
        if validation.get('warnings'):
            for warning in validation['warnings']:
                print(f"     Warning: {warning}")
    
    print("\n" + "=" * 60)
    print("Configuration Management System Test Complete")
    print("=" * 60)


def test_environment_variables():
    """Test environment variable detection."""
    print("\nEnvironment Variables Detected:")
    
    env_vars = [
        'GEMINI_API_KEY', 'GEMINI_MODEL',
        'OPENAI_API_KEY', 'OPENAI_MODEL',
        'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL',
        'OLLAMA_ENABLED', 'OLLAMA_BASE_URL', 'OLLAMA_MODEL'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Mask API keys for security
            if 'API_KEY' in var:
                masked_value = value[:8] + '...' + value[-4:] if len(value) > 12 else '***'
                print(f"   {var}: {masked_value}")
            else:
                print(f"   {var}: {value}")
        else:
            print(f"   {var}: Not set")


if __name__ == "__main__":
    # Test environment variables first
    test_environment_variables()
    
    # Then test the configuration system
    asyncio.run(test_configuration_system())