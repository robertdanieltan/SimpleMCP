# Implementation Plan

**Note: All changes are confined to the AI Agent Service layer only. The MCP service layer remains completely unchanged and unaffected by this enhancement.**

- [x] 1. Create LLM provider abstraction layer in AI Agent Service
  - Create base LLM provider interface and data models in `ai-agent-service/app/llm/`
  - Define standardized response formats and error handling for AI Agent layer only
  - Implement provider capabilities and health check interfaces
  - **Note: MCP service layer remains unchanged**
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Set up configuration management system in AI Agent Service
  - Create configuration manager for multi-provider setup in `ai-agent-service/app/config/`
  - Implement environment variable loading for all providers (Gemini, OpenAI, Anthropic, Ollama)
  - Add provider validation and availability checking within AI Agent Service only
  - **Note: MCP service configuration and environment variables remain unchanged**
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Implement provider factory pattern
  - Create LLM provider factory for dynamic provider instantiation
  - Implement provider registration and discovery mechanisms
  - Add provider lifecycle management (initialization, cleanup)
  - _Requirements: 2.1, 2.4, 4.1, 4.2_

- [x] 4. Refactor existing Gemini client to new provider interface
  - Extract current GeminiClient into new provider structure
  - Implement LLMProvider interface for Gemini
  - Ensure backward compatibility with existing functionality
  - Add comprehensive error handling and logging
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 5. Implement OpenAI provider
  - Create OpenAI provider class implementing LLMProvider interface
  - Integrate OpenAI Python SDK for API communication
  - Implement intent analysis and response generation for OpenAI
  - Add OpenAI-specific error handling and rate limiting
  - _Requirements: 1.1, 2.1, 2.2, 7.3, 7.4_

- [x] 6. Implement Anthropic provider
  - Create Anthropic provider class implementing LLMProvider interface
  - Integrate Anthropic Python SDK for API communication
  - Implement intent analysis and response generation for Anthropic
  - Add Anthropic-specific error handling and message formatting
  - _Requirements: 1.1, 2.1, 2.2, 7.3, 7.4_

- [x] 7. Implement Ollama provider for local LLM support
  - Create Ollama provider class with HTTP client for local communication
  - Implement model discovery and selection for available local models
  - Add dynamic model switching capabilities within provider
  - Implement offline functionality and local connectivity handling
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 8. Implement simple provider selection via environment variables
  - Add `LLM_PROVIDER` environment variable to specify which provider to use (gemini, openai, anthropic, ollama)
  - Implement provider selection logic in AIAgent initialization
  - Default to 'gemini' for backward compatibility when `LLM_PROVIDER` is not set
  - Add validation to ensure selected provider is properly configured
  - _Requirements: 9.1, 9.2, 9.5, 9.6_

- [x] 9. Update AI agent core to use provider factory
  - Refactor AIAgent class in `ai-agent-service/app/agent/core.py` to use LLM provider factory instead of direct Gemini client
  - Implement provider selection based on `LLM_PROVIDER` environment variable
  - Update intent analysis and response generation to work with selected provider
  - Maintain existing MCP client integration unchanged - all MCP communication remains identical
  - **Note: MCP service interaction patterns remain completely unchanged**
  - _Requirements: 2.1, 2.2, 5.3, 5.4_

- [x] 10. Enhance health check and monitoring endpoints
  - Update /health endpoint to include selected provider status
  - Update /agent/status endpoint to show current provider and its capabilities
  - Add provider-specific health metrics and response time tracking
  - Implement comprehensive logging for provider selection and performance
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 7.1, 7.2_

- [x] 11. Update environment configuration and Docker setup for AI Agent Service only
  - Update .env.example with all new provider environment variables and `LLM_PROVIDER` selection
  - Add new Python dependencies to `ai-agent-service/requirements.txt` (openai, anthropic, ollama)
  - Update docker-compose.yml to pass new environment variables to ai-agent service only
  - Update `ai-agent-service/Dockerfile` to ensure all dependencies are installed
  - **Note: MCP service Docker configuration, requirements, and environment remain unchanged**
  - _Requirements: 1.1, 1.2_

- [x] 12. Implement comprehensive error handling and logging
  - Add provider-specific error handling with standardized error responses
  - Implement detailed logging for provider interactions and failures
  - Add clear error messages when selected provider is unavailable
  - Create fallback mechanisms for graceful degradation
  - _Requirements: 3.4, 7.1, 7.2, 7.3, 7.4, 7.5, 9.4, 9.6_

- [x] 13. Write comprehensive unit tests for Anthropic provider
  - Create unit tests for base LLM provider interface
  - Write provider-specific tests for Anthropic provider only
  - Test provider factory functionality with Anthropic integration
  - Create mock tests for Anthropic API interactions
  - _Requirements: 2.1, 2.2, 2.3, 7.1, 7.2_

- [x] 14. Write integration tests for Anthropic provider selection
  - Create end-to-end tests for Anthropic provider selection via environment variables
  - Test switching to Anthropic provider by setting LLM_PROVIDER=anthropic
  - Write tests for Anthropic provider validation and error handling
  - Test that existing functionality works with Anthropic provider
  - _Requirements: 9.1, 9.2, 9.5, 9.6_

- [x] 15. Create configuration validation and migration utilities for Anthropic
  - Implement configuration validation for Anthropic provider setup
  - Create migration utilities for switching from Gemini to Anthropic configurations
  - Add configuration testing and validation tools for Anthropic
  - Write documentation for Anthropic configuration setup and troubleshooting
  - _Requirements: 1.2, 1.3, 5.1, 5.2_

- [x] 16. Update API documentation and response models
  - Update Pydantic models to include current provider information in responses
  - Update existing endpoint documentation with provider-aware examples
  - Create comprehensive documentation for environment-based provider selection
  - Add troubleshooting guide for provider configuration
  - _Requirements: 5.4, 10.1_

- [x] 17. Implement backward compatibility validation
  - Create tests to ensure existing Gemini-only configurations work unchanged
  - Validate that existing API endpoints maintain identical behavior
  - Test migration path from single-provider to multi-provider setup
  - Ensure no breaking changes in public API
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 18. Add performance monitoring and optimization
  - Implement response time tracking for selected provider
  - Add memory usage monitoring for provider instances
  - Create performance comparison tools between providers
  - Optimize provider initialization and request processing
  - _Requirements: 4.3, 4.5, 10.4_

## Implementation Scope Clarification

**AI Agent Service Changes:**
- All LLM provider logic and simple environment-based provider selection
- Enhanced configuration with `LLM_PROVIDER` environment variable
- Updated dependencies and Docker configuration
- No new API endpoints - existing endpoints work with any provider

**MCP Service - NO CHANGES:**
- All MCP tools remain identical (`/mcp/tools/*`)
- Database operations unchanged
- MCP service API endpoints unchanged (`/mcp/*`)
- MCP service configuration unchanged
- MCP service Docker setup unchanged

**Communication Pattern:**
- AI Agent Service ↔ Multiple LLM Providers (NEW)
- AI Agent Service ↔ MCP Service (UNCHANGED)
- MCP Service ↔ PostgreSQL (UNCHANGED)