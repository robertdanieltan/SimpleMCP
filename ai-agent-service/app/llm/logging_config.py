"""
Enhanced Logging Configuration for Multi-LLM Provider System

This module provides comprehensive logging configuration with structured logging,
performance metrics, security considerations, and provider-specific logging.
"""

import logging
import logging.handlers
import os
import sys
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from ..llm.utils import sanitize_api_key


class LogLevel(Enum):
    """Available log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Available log formats"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class LogEntry:
    """Structured log entry for consistent logging"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    provider: Optional[str] = None
    operation: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    response_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    model: Optional[str] = None
    error_code: Optional[str] = None
    error_type: Optional[str] = None
    success: Optional[bool] = None
    additional_data: Optional[Dict[str, Any]] = None


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive information from logs"""
    
    def __init__(self):
        super().__init__()
        self.sensitive_patterns = [
            'api_key', 'password', 'token', 'secret', 'auth',
            'bearer', 'authorization', 'credential'
        ]
    
    def filter(self, record):
        """Filter sensitive information from log records"""
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize_message(record.msg)
        
        # Sanitize arguments
        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._sanitize_value(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize sensitive information from message"""
        import re
        
        # Pattern to match API keys and tokens
        patterns = [
            r'(api[_-]?key["\s]*[:=]["\s]*)[a-zA-Z0-9_-]{10,}',
            r'(token["\s]*[:=]["\s]*)[a-zA-Z0-9_.-]{10,}',
            r'(bearer["\s]+)[a-zA-Z0-9_.-]{10,}',
            r'(password["\s]*[:=]["\s]*)[^\s"\']{6,}',
        ]
        
        for pattern in patterns:
            message = re.sub(pattern, r'\1[REDACTED]', message, flags=re.IGNORECASE)
        
        return message
    
    def _sanitize_value(self, value: str) -> str:
        """Sanitize individual values"""
        # If it looks like an API key or token, sanitize it
        if len(value) > 10 and any(pattern in value.lower() for pattern in ['key', 'token', 'secret']):
            return sanitize_api_key(value)
        return value


class ProviderLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds provider context to log records"""
    
    def __init__(self, logger, provider_name: str):
        super().__init__(logger, {"provider": provider_name})
        self.provider_name = provider_name
    
    def process(self, msg, kwargs):
        """Add provider context to log records"""
        # Add provider to extra if not already present
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        kwargs['extra']['provider'] = self.provider_name
        
        return msg, kwargs
    
    def log_operation(
        self,
        level: int,
        operation: str,
        message: str,
        success: Optional[bool] = None,
        response_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        model: Optional[str] = None,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **additional_data
    ):
        """Log provider operation with structured data"""
        extra_data = {
            'provider': self.provider_name,
            'operation': operation,
            'success': success,
            'response_time_ms': response_time_ms,
            'tokens_used': tokens_used,
            'model': model,
            'error_code': error_code,
            'error_type': error_type,
            'request_id': request_id,
            'session_id': session_id,
            **additional_data
        }
        
        # Remove None values
        extra_data = {k: v for k, v in extra_data.items() if v is not None}
        
        self.log(level, message, extra=extra_data)
    
    def log_request(
        self,
        user_input: str,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log incoming request"""
        self.log_operation(
            logging.INFO,
            "request_received",
            f"Processing request: {user_input[:100]}{'...' if len(user_input) > 100 else ''}",
            request_id=request_id,
            session_id=session_id,
            input_length=len(user_input)
        )
    
    def log_response(
        self,
        response: str,
        success: bool,
        response_time_ms: int,
        tokens_used: Optional[int] = None,
        model: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Log response generation"""
        self.log_operation(
            logging.INFO,
            "response_generated",
            f"Generated response: {response[:100]}{'...' if len(response) > 100 else ''}",
            success=success,
            response_time_ms=response_time_ms,
            tokens_used=tokens_used,
            model=model,
            request_id=request_id,
            session_id=session_id,
            response_length=len(response)
        )
    
    def log_error(
        self,
        error: Exception,
        operation: str,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **additional_context
    ):
        """Log error with full context"""
        self.log_operation(
            logging.ERROR,
            operation,
            f"Error in {operation}: {str(error)}",
            success=False,
            error_type=type(error).__name__,
            error_code=getattr(error, 'error_code', None),
            request_id=request_id,
            session_id=session_id,
            **additional_context
        )


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'provider'):
            log_entry['provider'] = record.provider
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'success'):
            log_entry['success'] = record.success
        if hasattr(record, 'response_time_ms'):
            log_entry['response_time_ms'] = record.response_time_ms
        if hasattr(record, 'tokens_used'):
            log_entry['tokens_used'] = record.tokens_used
        if hasattr(record, 'model'):
            log_entry['model'] = record.model
        if hasattr(record, 'error_code'):
            log_entry['error_code'] = record.error_code
        if hasattr(record, 'error_type'):
            log_entry['error_type'] = record.error_type
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, default=str)


class StructuredFormatter(logging.Formatter):
    """Structured formatter for human-readable logs with consistent format"""
    
    def __init__(self):
        super().__init__()
        self.base_format = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    
    def format(self, record):
        """Format log record with structured information"""
        # Start with base format
        formatted = super().format(record)
        
        # Add structured information
        structured_parts = []
        
        if hasattr(record, 'provider'):
            structured_parts.append(f"provider={record.provider}")
        if hasattr(record, 'operation'):
            structured_parts.append(f"operation={record.operation}")
        if hasattr(record, 'success') and record.success is not None:
            structured_parts.append(f"success={record.success}")
        if hasattr(record, 'response_time_ms'):
            structured_parts.append(f"response_time={record.response_time_ms}ms")
        if hasattr(record, 'tokens_used'):
            structured_parts.append(f"tokens={record.tokens_used}")
        if hasattr(record, 'model'):
            structured_parts.append(f"model={record.model}")
        if hasattr(record, 'error_code'):
            structured_parts.append(f"error_code={record.error_code}")
        if hasattr(record, 'request_id'):
            structured_parts.append(f"req_id={record.request_id}")
        if hasattr(record, 'session_id'):
            structured_parts.append(f"session_id={record.session_id}")
        
        if structured_parts:
            formatted += f" | {' | '.join(structured_parts)}"
        
        return formatted


class LoggingConfig:
    """Comprehensive logging configuration for the multi-LLM system"""
    
    def __init__(
        self,
        log_level: LogLevel = LogLevel.INFO,
        log_format: LogFormat = LogFormat.STRUCTURED,
        log_file: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_console: bool = True,
        enable_security_filter: bool = True
    ):
        """
        Initialize logging configuration
        
        Args:
            log_level: Minimum log level to capture
            log_format: Format for log messages
            log_file: Path to log file (optional)
            max_file_size: Maximum size of log file before rotation
            backup_count: Number of backup files to keep
            enable_console: Whether to enable console logging
            enable_security_filter: Whether to enable security filtering
        """
        self.log_level = log_level
        self.log_format = log_format
        self.log_file = log_file
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.enable_console = enable_console
        self.enable_security_filter = enable_security_filter
        
        self.provider_loggers: Dict[str, ProviderLoggerAdapter] = {}
        self._configured = False
    
    def configure_logging(self):
        """Configure logging system with specified settings"""
        if self._configured:
            return
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.value))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = self._create_formatter()
        
        # Add console handler if enabled
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.log_level.value))
            console_handler.setFormatter(formatter)
            
            if self.enable_security_filter:
                console_handler.addFilter(SecurityFilter())
            
            root_logger.addHandler(console_handler)
        
        # Add file handler if specified
        if self.log_file:
            self._add_file_handler(root_logger, formatter)
        
        # Configure specific loggers
        self._configure_specific_loggers()
        
        self._configured = True
        logging.info("Enhanced logging configuration applied successfully")
    
    def _create_formatter(self) -> logging.Formatter:
        """Create appropriate formatter based on configuration"""
        if self.log_format == LogFormat.JSON:
            return JSONFormatter()
        elif self.log_format == LogFormat.STRUCTURED:
            return StructuredFormatter()
        elif self.log_format == LogFormat.DETAILED:
            return logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s:%(lineno)-4d | %(message)s"
            )
        else:  # SIMPLE
            return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    def _add_file_handler(self, logger: logging.Logger, formatter: logging.Formatter):
        """Add rotating file handler"""
        # Ensure log directory exists
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(getattr(logging, self.log_level.value))
        file_handler.setFormatter(formatter)
        
        if self.enable_security_filter:
            file_handler.addFilter(SecurityFilter())
        
        logger.addHandler(file_handler)
    
    def _configure_specific_loggers(self):
        """Configure specific loggers for different components"""
        # Set appropriate levels for different components
        logger_configs = {
            "httpx": logging.WARNING,  # Reduce HTTP client noise
            "urllib3": logging.WARNING,  # Reduce urllib3 noise
            "requests": logging.WARNING,  # Reduce requests noise
            "openai": logging.INFO,  # OpenAI SDK logs
            "anthropic": logging.INFO,  # Anthropic SDK logs
            "google": logging.INFO,  # Google SDK logs
            "app.llm": logging.DEBUG if self.log_level == LogLevel.DEBUG else logging.INFO,
            "app.agent": logging.INFO,
            "app.mcp_client": logging.INFO,
            "app.config": logging.INFO
        }
        
        for logger_name, level in logger_configs.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
    
    def get_provider_logger(self, provider_name: str) -> ProviderLoggerAdapter:
        """
        Get or create a provider-specific logger
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            ProviderLoggerAdapter for the provider
        """
        if provider_name not in self.provider_loggers:
            base_logger = logging.getLogger(f"app.llm.providers.{provider_name}")
            self.provider_loggers[provider_name] = ProviderLoggerAdapter(base_logger, provider_name)
        
        return self.provider_loggers[provider_name]
    
    def log_system_startup(self, config_summary: Dict[str, Any]):
        """Log system startup information"""
        logger = logging.getLogger("app.system")
        logger.info("Multi-LLM Provider System Starting", extra={
            "operation": "system_startup",
            "config_summary": config_summary,
            "log_level": self.log_level.value,
            "log_format": self.log_format.value,
            "security_filter_enabled": self.enable_security_filter
        })
    
    def log_provider_initialization(
        self,
        provider_name: str,
        success: bool,
        initialization_time_ms: int,
        error: Optional[str] = None
    ):
        """Log provider initialization"""
        provider_logger = self.get_provider_logger(provider_name)
        
        if success:
            provider_logger.log_operation(
                logging.INFO,
                "provider_initialization",
                f"Provider {provider_name} initialized successfully",
                success=True,
                response_time_ms=initialization_time_ms
            )
        else:
            provider_logger.log_operation(
                logging.ERROR,
                "provider_initialization",
                f"Provider {provider_name} initialization failed: {error}",
                success=False,
                response_time_ms=initialization_time_ms,
                error_type="InitializationError"
            )
    
    def create_request_logger(self, request_id: str) -> logging.LoggerAdapter:
        """Create a logger for a specific request"""
        base_logger = logging.getLogger("app.request")
        return logging.LoggerAdapter(base_logger, {"request_id": request_id})


# Global logging configuration
_logging_config = None


def get_logging_config() -> LoggingConfig:
    """Get the global logging configuration"""
    global _logging_config
    if _logging_config is None:
        # Default configuration
        log_level = LogLevel(os.getenv("LOG_LEVEL", "INFO"))
        log_format = LogFormat(os.getenv("LOG_FORMAT", "structured"))
        log_file = os.getenv("LOG_FILE")
        
        _logging_config = LoggingConfig(
            log_level=log_level,
            log_format=log_format,
            log_file=log_file
        )
        _logging_config.configure_logging()
    
    return _logging_config


def configure_logging(
    log_level: LogLevel = LogLevel.INFO,
    log_format: LogFormat = LogFormat.STRUCTURED,
    log_file: Optional[str] = None,
    **kwargs
) -> LoggingConfig:
    """
    Configure the global logging system
    
    Args:
        log_level: Minimum log level
        log_format: Log format to use
        log_file: Optional log file path
        **kwargs: Additional configuration options
        
    Returns:
        LoggingConfig instance
    """
    global _logging_config
    _logging_config = LoggingConfig(
        log_level=log_level,
        log_format=log_format,
        log_file=log_file,
        **kwargs
    )
    _logging_config.configure_logging()
    return _logging_config


def get_provider_logger(provider_name: str) -> ProviderLoggerAdapter:
    """Get a provider-specific logger"""
    config = get_logging_config()
    return config.get_provider_logger(provider_name)