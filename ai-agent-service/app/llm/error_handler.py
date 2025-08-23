"""
Comprehensive Error Handler for LLM Providers

This module provides centralized error handling, logging, and fallback mechanisms
for the multi-LLM provider system, ensuring graceful degradation and detailed
error reporting across all providers.
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from contextlib import contextmanager

from .base import LLMResponse, ErrorResponse, ProviderStatus
from .exceptions import (
    LLMProviderError,
    ProviderInitializationError,
    ProviderConfigurationError,
    ProviderAuthenticationError,
    ProviderRateLimitError,
    ProviderNetworkError,
    ProviderModelError,
    ProviderResponseError,
    ProviderUnavailableError
)

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization and handling"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FallbackStrategy(Enum):
    """Available fallback strategies when providers fail"""
    NONE = "none"
    RULE_BASED = "rule_based"
    CACHED_RESPONSE = "cached_response"
    ALTERNATIVE_PROVIDER = "alternative_provider"


@dataclass
class ErrorContext:
    """Context information for error handling and logging"""
    provider_name: str
    operation: str
    user_input: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    additional_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorMetrics:
    """Metrics tracking for error analysis and monitoring"""
    error_count: int = 0
    last_error_time: Optional[datetime] = None
    error_types: Dict[str, int] = field(default_factory=dict)
    consecutive_failures: int = 0
    total_requests: int = 0
    success_rate: float = 1.0


class ErrorHandler:
    """
    Centralized error handler for LLM provider operations
    
    Provides comprehensive error handling, logging, metrics tracking,
    and fallback mechanisms for all provider operations.
    """
    
    def __init__(self):
        """Initialize the error handler with metrics tracking"""
        self.provider_metrics: Dict[str, ErrorMetrics] = {}
        self.global_metrics = ErrorMetrics()
        self.fallback_responses = self._initialize_fallback_responses()
        self.error_patterns = self._initialize_error_patterns()
        
        # Circuit breaker settings
        self.circuit_breaker_threshold = 5  # failures before opening circuit
        self.circuit_breaker_timeout = timedelta(minutes=5)  # time before retry
        self.circuit_breaker_states: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Error handler initialized with comprehensive logging and fallback support")
    
    def _initialize_fallback_responses(self) -> Dict[str, str]:
        """Initialize fallback responses for different error scenarios"""
        return {
            "authentication_error": "I'm experiencing authentication issues with the AI service. Please check the configuration and try again.",
            "rate_limit_error": "The AI service is currently rate limited. Please wait a moment and try again.",
            "network_error": "I'm having trouble connecting to the AI service. Please check your network connection and try again.",
            "model_error": "There's an issue with the AI model configuration. Please contact support if this persists.",
            "provider_unavailable": "The AI service is temporarily unavailable. I'll try to help with basic responses.",
            "general_error": "I encountered an unexpected error. Let me try to help you with a basic response.",
            "configuration_error": "There's a configuration issue with the AI service. Please check the setup.",
            "initialization_error": "The AI service failed to initialize properly. Please restart the service.",
            "response_error": "The AI service returned an invalid response. Please try rephrasing your request."
        }
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize error patterns for classification and handling"""
        return {
            "authentication": {
                "keywords": ["auth", "unauthorized", "invalid key", "forbidden", "401", "403"],
                "severity": ErrorSeverity.HIGH,
                "fallback": FallbackStrategy.RULE_BASED,
                "retry": False
            },
            "rate_limit": {
                "keywords": ["rate limit", "quota", "429", "too many requests"],
                "severity": ErrorSeverity.MEDIUM,
                "fallback": FallbackStrategy.CACHED_RESPONSE,
                "retry": True,
                "retry_delay": 60
            },
            "network": {
                "keywords": ["connection", "timeout", "network", "dns", "502", "503", "504"],
                "severity": ErrorSeverity.MEDIUM,
                "fallback": FallbackStrategy.ALTERNATIVE_PROVIDER,
                "retry": True,
                "retry_delay": 5
            },
            "model": {
                "keywords": ["model", "invalid request", "bad request", "400"],
                "severity": ErrorSeverity.HIGH,
                "fallback": FallbackStrategy.RULE_BASED,
                "retry": False
            },
            "server": {
                "keywords": ["internal server", "500", "502", "503"],
                "severity": ErrorSeverity.HIGH,
                "fallback": FallbackStrategy.ALTERNATIVE_PROVIDER,
                "retry": True,
                "retry_delay": 30
            }
        }
    
    @contextmanager
    def handle_provider_operation(
        self, 
        context: ErrorContext,
        fallback_strategy: FallbackStrategy = FallbackStrategy.RULE_BASED
    ):
        """
        Context manager for handling provider operations with comprehensive error handling
        
        Args:
            context: Error context information
            fallback_strategy: Strategy to use if operation fails
            
        Yields:
            Operation context for the provider operation
        """
        start_time = time.time()
        operation_success = False
        error_info = None
        
        try:
            # Check circuit breaker
            if self._is_circuit_breaker_open(context.provider_name):
                raise ProviderUnavailableError(
                    f"Circuit breaker is open for provider {context.provider_name}",
                    provider=context.provider_name
                )
            
            # Update request metrics
            self._update_request_metrics(context.provider_name)
            
            yield self
            
            operation_success = True
            self._record_success(context.provider_name)
            
        except LLMProviderError as e:
            error_info = e
            self._handle_provider_error(e, context, fallback_strategy)
            raise
            
        except Exception as e:
            error_info = e
            # Convert generic exceptions to provider errors
            provider_error = LLMProviderError(
                message=str(e),
                provider=context.provider_name,
                error_code="UNEXPECTED_ERROR",
                details={"original_exception": type(e).__name__}
            )
            self._handle_provider_error(provider_error, context, fallback_strategy)
            raise provider_error
            
        finally:
            # Record operation metrics
            operation_time = time.time() - start_time
            self._record_operation_metrics(
                context, 
                operation_success, 
                operation_time, 
                error_info
            )
    
    def _handle_provider_error(
        self, 
        error: LLMProviderError, 
        context: ErrorContext,
        fallback_strategy: FallbackStrategy
    ):
        """
        Handle provider errors with comprehensive logging and metrics
        
        Args:
            error: The provider error that occurred
            context: Error context information
            fallback_strategy: Strategy for handling the error
        """
        # Classify error
        error_classification = self._classify_error(error)
        
        # Update error metrics
        self._update_error_metrics(context.provider_name, error, error_classification)
        
        # Log error with full context
        self._log_error(error, context, error_classification)
        
        # Update circuit breaker if needed
        self._update_circuit_breaker(context.provider_name, error_classification)
        
        # Handle fallback if configured
        if fallback_strategy != FallbackStrategy.NONE:
            self._prepare_fallback_response(error, context, fallback_strategy)
    
    def _classify_error(self, error: LLMProviderError) -> Dict[str, Any]:
        """
        Classify error based on type and message content
        
        Args:
            error: The error to classify
            
        Returns:
            Error classification information
        """
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Check for specific error types first
        if isinstance(error, ProviderAuthenticationError):
            return {
                "category": "authentication",
                "severity": ErrorSeverity.HIGH,
                "retry_recommended": False,
                "fallback_strategy": FallbackStrategy.RULE_BASED
            }
        elif isinstance(error, ProviderRateLimitError):
            return {
                "category": "rate_limit",
                "severity": ErrorSeverity.MEDIUM,
                "retry_recommended": True,
                "retry_delay": getattr(error, 'retry_after', 60),
                "fallback_strategy": FallbackStrategy.CACHED_RESPONSE
            }
        elif isinstance(error, ProviderNetworkError):
            return {
                "category": "network",
                "severity": ErrorSeverity.MEDIUM,
                "retry_recommended": True,
                "retry_delay": 5,
                "fallback_strategy": FallbackStrategy.ALTERNATIVE_PROVIDER
            }
        elif isinstance(error, ProviderModelError):
            return {
                "category": "model",
                "severity": ErrorSeverity.HIGH,
                "retry_recommended": False,
                "fallback_strategy": FallbackStrategy.RULE_BASED
            }
        elif isinstance(error, ProviderConfigurationError):
            return {
                "category": "configuration",
                "severity": ErrorSeverity.CRITICAL,
                "retry_recommended": False,
                "fallback_strategy": FallbackStrategy.RULE_BASED
            }
        elif isinstance(error, ProviderInitializationError):
            return {
                "category": "initialization",
                "severity": ErrorSeverity.CRITICAL,
                "retry_recommended": False,
                "fallback_strategy": FallbackStrategy.RULE_BASED
            }
        
        # Pattern-based classification for generic errors
        for category, pattern_info in self.error_patterns.items():
            if any(keyword in error_message for keyword in pattern_info["keywords"]):
                return {
                    "category": category,
                    "severity": pattern_info["severity"],
                    "retry_recommended": pattern_info.get("retry", False),
                    "retry_delay": pattern_info.get("retry_delay", 5),
                    "fallback_strategy": pattern_info["fallback"]
                }
        
        # Default classification
        return {
            "category": "unknown",
            "severity": ErrorSeverity.MEDIUM,
            "retry_recommended": True,
            "retry_delay": 5,
            "fallback_strategy": FallbackStrategy.RULE_BASED
        }
    
    def _log_error(
        self, 
        error: LLMProviderError, 
        context: ErrorContext,
        classification: Dict[str, Any]
    ):
        """
        Log error with comprehensive context and classification
        
        Args:
            error: The error that occurred
            context: Error context information
            classification: Error classification results
        """
        log_data = {
            "provider": context.provider_name,
            "operation": context.operation,
            "error_type": type(error).__name__,
            "error_code": error.error_code,
            "error_message": error.message,
            "classification": classification["category"],
            "severity": classification["severity"].value,
            "retry_recommended": classification["retry_recommended"],
            "timestamp": context.timestamp.isoformat(),
            "request_id": context.request_id,
            "session_id": context.session_id
        }
        
        # Add user input if available (sanitized)
        if context.user_input:
            log_data["user_input_length"] = len(context.user_input)
            log_data["user_input_preview"] = context.user_input[:100] + "..." if len(context.user_input) > 100 else context.user_input
        
        # Add error details if available
        if hasattr(error, 'details') and error.details:
            log_data["error_details"] = error.details
        
        # Add additional context
        if context.additional_context:
            log_data["additional_context"] = context.additional_context
        
        # Log at appropriate level based on severity
        if classification["severity"] == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical provider error: {log_data}")
        elif classification["severity"] == ErrorSeverity.HIGH:
            logger.error(f"High severity provider error: {log_data}")
        elif classification["severity"] == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity provider error: {log_data}")
        else:
            logger.info(f"Low severity provider error: {log_data}")
        
        # Log stack trace for debugging if available
        if hasattr(error, '__traceback__') and error.__traceback__:
            logger.debug(f"Error stack trace for {context.provider_name}: {traceback.format_exception(type(error), error, error.__traceback__)}")
    
    def _update_error_metrics(
        self, 
        provider_name: str, 
        error: LLMProviderError,
        classification: Dict[str, Any]
    ):
        """
        Update error metrics for monitoring and analysis
        
        Args:
            provider_name: Name of the provider
            error: The error that occurred
            classification: Error classification results
        """
        # Initialize provider metrics if not exists
        if provider_name not in self.provider_metrics:
            self.provider_metrics[provider_name] = ErrorMetrics()
        
        metrics = self.provider_metrics[provider_name]
        
        # Update error counts
        metrics.error_count += 1
        metrics.last_error_time = datetime.utcnow()
        metrics.consecutive_failures += 1
        
        # Update error type counts
        error_type = type(error).__name__
        if error_type not in metrics.error_types:
            metrics.error_types[error_type] = 0
        metrics.error_types[error_type] += 1
        
        # Update success rate
        if metrics.total_requests > 0:
            success_count = metrics.total_requests - metrics.error_count
            metrics.success_rate = success_count / metrics.total_requests
        
        # Update global metrics
        self.global_metrics.error_count += 1
        self.global_metrics.last_error_time = datetime.utcnow()
        
        if error_type not in self.global_metrics.error_types:
            self.global_metrics.error_types[error_type] = 0
        self.global_metrics.error_types[error_type] += 1
    
    def _update_request_metrics(self, provider_name: str):
        """Update request metrics for a provider"""
        if provider_name not in self.provider_metrics:
            self.provider_metrics[provider_name] = ErrorMetrics()
        
        self.provider_metrics[provider_name].total_requests += 1
        self.global_metrics.total_requests += 1
    
    def _record_success(self, provider_name: str):
        """Record a successful operation for a provider"""
        if provider_name in self.provider_metrics:
            metrics = self.provider_metrics[provider_name]
            metrics.consecutive_failures = 0  # Reset consecutive failures
            
            # Update success rate
            if metrics.total_requests > 0:
                success_count = metrics.total_requests - metrics.error_count
                metrics.success_rate = success_count / metrics.total_requests
    
    def _record_operation_metrics(
        self,
        context: ErrorContext,
        success: bool,
        operation_time: float,
        error_info: Optional[Exception] = None
    ):
        """
        Record comprehensive operation metrics
        
        Args:
            context: Operation context
            success: Whether operation was successful
            operation_time: Time taken for operation
            error_info: Error information if operation failed
        """
        metrics_data = {
            "provider": context.provider_name,
            "operation": context.operation,
            "success": success,
            "operation_time_ms": int(operation_time * 1000),
            "timestamp": context.timestamp.isoformat(),
            "request_id": context.request_id,
            "session_id": context.session_id
        }
        
        if not success and error_info:
            metrics_data["error_type"] = type(error_info).__name__
            metrics_data["error_message"] = str(error_info)
        
        # Log metrics for monitoring systems
        logger.info(f"Operation metrics: {metrics_data}")
    
    def _is_circuit_breaker_open(self, provider_name: str) -> bool:
        """
        Check if circuit breaker is open for a provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            True if circuit breaker is open, False otherwise
        """
        if provider_name not in self.circuit_breaker_states:
            return False
        
        breaker_state = self.circuit_breaker_states[provider_name]
        
        if not breaker_state.get("is_open", False):
            return False
        
        # Check if timeout has passed
        open_time = breaker_state.get("opened_at")
        if open_time and datetime.utcnow() - open_time > self.circuit_breaker_timeout:
            # Reset circuit breaker
            breaker_state["is_open"] = False
            breaker_state["failure_count"] = 0
            logger.info(f"Circuit breaker reset for provider {provider_name}")
            return False
        
        return True
    
    def _update_circuit_breaker(self, provider_name: str, classification: Dict[str, Any]):
        """
        Update circuit breaker state based on error classification
        
        Args:
            provider_name: Name of the provider
            classification: Error classification results
        """
        if provider_name not in self.circuit_breaker_states:
            self.circuit_breaker_states[provider_name] = {
                "is_open": False,
                "failure_count": 0,
                "opened_at": None
            }
        
        breaker_state = self.circuit_breaker_states[provider_name]
        
        # Only count certain types of errors for circuit breaker
        if classification["category"] in ["network", "server", "rate_limit"]:
            breaker_state["failure_count"] += 1
            
            if breaker_state["failure_count"] >= self.circuit_breaker_threshold:
                breaker_state["is_open"] = True
                breaker_state["opened_at"] = datetime.utcnow()
                logger.warning(f"Circuit breaker opened for provider {provider_name} after {breaker_state['failure_count']} failures")
    
    def _prepare_fallback_response(
        self,
        error: LLMProviderError,
        context: ErrorContext,
        fallback_strategy: FallbackStrategy
    ) -> Optional[str]:
        """
        Prepare fallback response based on error and strategy
        
        Args:
            error: The error that occurred
            context: Error context
            fallback_strategy: Fallback strategy to use
            
        Returns:
            Fallback response string if available
        """
        if fallback_strategy == FallbackStrategy.RULE_BASED:
            return self._get_rule_based_fallback(error, context)
        elif fallback_strategy == FallbackStrategy.CACHED_RESPONSE:
            return self._get_cached_fallback(context)
        elif fallback_strategy == FallbackStrategy.ALTERNATIVE_PROVIDER:
            # This would be handled at a higher level
            return None
        
        return None
    
    def _get_rule_based_fallback(self, error: LLMProviderError, context: ErrorContext) -> str:
        """Get rule-based fallback response"""
        error_type = type(error).__name__.lower()
        
        # Map error types to fallback response keys
        fallback_key_map = {
            "providerauthenticationerror": "authentication_error",
            "providerratelimiterror": "rate_limit_error",
            "providernetworkerror": "network_error",
            "providermodelerror": "model_error",
            "providerunavailableerror": "provider_unavailable",
            "providerconfigurationerror": "configuration_error",
            "providerinitializationerror": "initialization_error",
            "providerresponseerror": "response_error"
        }
        
        fallback_key = fallback_key_map.get(error_type, "general_error")
        return self.fallback_responses.get(fallback_key, self.fallback_responses["general_error"])
    
    def _get_cached_fallback(self, context: ErrorContext) -> Optional[str]:
        """Get cached fallback response (placeholder for future implementation)"""
        # This could be implemented to return cached responses for similar requests
        return None
    
    def create_error_response(
        self,
        error: LLMProviderError,
        context: ErrorContext,
        include_fallback: bool = True
    ) -> LLMResponse:
        """
        Create a standardized error response
        
        Args:
            error: The error that occurred
            context: Error context
            include_fallback: Whether to include fallback response
            
        Returns:
            LLMResponse with error information and optional fallback
        """
        fallback_message = None
        if include_fallback:
            fallback_message = self._get_rule_based_fallback(error, context)
        
        return LLMResponse(
            success=False,
            response=fallback_message or "I apologize, but I encountered an error processing your request.",
            source=f"{context.provider_name}_error",
            error=f"{error.error_code}: {error.message}",
            timestamp=context.timestamp
        )
    
    def get_provider_error_summary(self, provider_name: str) -> Dict[str, Any]:
        """
        Get error summary for a specific provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Error summary information
        """
        if provider_name not in self.provider_metrics:
            return {
                "provider": provider_name,
                "error_count": 0,
                "success_rate": 1.0,
                "last_error": None,
                "error_types": {},
                "consecutive_failures": 0,
                "circuit_breaker_open": False
            }
        
        metrics = self.provider_metrics[provider_name]
        circuit_breaker_open = self._is_circuit_breaker_open(provider_name)
        
        return {
            "provider": provider_name,
            "error_count": metrics.error_count,
            "success_rate": metrics.success_rate,
            "last_error": metrics.last_error_time.isoformat() if metrics.last_error_time else None,
            "error_types": metrics.error_types.copy(),
            "consecutive_failures": metrics.consecutive_failures,
            "total_requests": metrics.total_requests,
            "circuit_breaker_open": circuit_breaker_open
        }
    
    def get_global_error_summary(self) -> Dict[str, Any]:
        """
        Get global error summary across all providers
        
        Returns:
            Global error summary information
        """
        return {
            "total_errors": self.global_metrics.error_count,
            "total_requests": self.global_metrics.total_requests,
            "global_success_rate": (
                (self.global_metrics.total_requests - self.global_metrics.error_count) / 
                self.global_metrics.total_requests
            ) if self.global_metrics.total_requests > 0 else 1.0,
            "last_error": self.global_metrics.last_error_time.isoformat() if self.global_metrics.last_error_time else None,
            "error_types": self.global_metrics.error_types.copy(),
            "provider_summaries": {
                provider: self.get_provider_error_summary(provider)
                for provider in self.provider_metrics.keys()
            }
        }
    
    def reset_provider_metrics(self, provider_name: str):
        """Reset metrics for a specific provider"""
        if provider_name in self.provider_metrics:
            self.provider_metrics[provider_name] = ErrorMetrics()
        
        if provider_name in self.circuit_breaker_states:
            self.circuit_breaker_states[provider_name] = {
                "is_open": False,
                "failure_count": 0,
                "opened_at": None
            }
        
        logger.info(f"Reset error metrics for provider {provider_name}")
    
    def reset_all_metrics(self):
        """Reset all error metrics"""
        self.provider_metrics.clear()
        self.global_metrics = ErrorMetrics()
        self.circuit_breaker_states.clear()
        logger.info("Reset all error metrics")


# Global error handler instance
_error_handler = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler


def create_error_context(
    provider_name: str,
    operation: str,
    user_input: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **additional_context
) -> ErrorContext:
    """
    Create an error context for provider operations
    
    Args:
        provider_name: Name of the provider
        operation: Operation being performed
        user_input: User input if available
        request_id: Request ID if available
        session_id: Session ID if available
        **additional_context: Additional context information
        
    Returns:
        ErrorContext instance
    """
    return ErrorContext(
        provider_name=provider_name,
        operation=operation,
        user_input=user_input,
        request_id=request_id,
        session_id=session_id,
        additional_context=additional_context
    )