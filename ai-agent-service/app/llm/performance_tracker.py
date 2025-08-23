"""
Performance Tracking for LLM Providers

This module provides utilities for tracking provider performance metrics,
response times, and health statistics for monitoring and optimization.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
import asyncio
import threading

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Individual performance metric record"""
    timestamp: datetime
    provider_name: str
    operation: str  # 'generate_response', 'analyze_intent', 'health_check'
    response_time_ms: int
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    model: Optional[str] = None


@dataclass
class ProviderStats:
    """Aggregated statistics for a provider"""
    provider_name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: int = 0
    max_response_time_ms: int = 0
    total_tokens_used: int = 0
    last_request_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_error_time: Optional[datetime] = None
    last_error: Optional[str] = None
    uptime_percentage: float = 100.0
    recent_metrics: deque = field(default_factory=lambda: deque(maxlen=100))


class PerformanceTracker:
    """
    Tracks performance metrics for LLM providers
    
    This class provides comprehensive performance tracking including response times,
    success rates, error tracking, and health metrics for all LLM providers.
    """
    
    def __init__(self, max_metrics_per_provider: int = 1000):
        """
        Initialize the performance tracker
        
        Args:
            max_metrics_per_provider: Maximum number of metrics to keep per provider
        """
        self.max_metrics_per_provider = max_metrics_per_provider
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metrics_per_provider))
        self._provider_stats: Dict[str, ProviderStats] = {}
        self._lock = threading.RLock()
        self._start_time = datetime.utcnow()
        
        logger.info("Performance tracker initialized")
    
    def start_operation(self, provider_name: str, operation: str) -> 'OperationTimer':
        """
        Start timing an operation
        
        Args:
            provider_name: Name of the provider
            operation: Type of operation being performed
            
        Returns:
            OperationTimer context manager
        """
        return OperationTimer(self, provider_name, operation)
    
    def record_metric(
        self,
        provider_name: str,
        operation: str,
        response_time_ms: int,
        success: bool,
        error: Optional[str] = None,
        tokens_used: Optional[int] = None,
        model: Optional[str] = None
    ):
        """
        Record a performance metric
        
        Args:
            provider_name: Name of the provider
            operation: Type of operation
            response_time_ms: Response time in milliseconds
            success: Whether the operation was successful
            error: Error message if operation failed
            tokens_used: Number of tokens used (if applicable)
            model: Model name used (if applicable)
        """
        with self._lock:
            metric = PerformanceMetric(
                timestamp=datetime.utcnow(),
                provider_name=provider_name,
                operation=operation,
                response_time_ms=response_time_ms,
                success=success,
                error=error,
                tokens_used=tokens_used,
                model=model
            )
            
            # Store the metric
            self._metrics[provider_name].append(metric)
            
            # Update provider statistics
            self._update_provider_stats(provider_name, metric)
            
            # Log performance information
            status = "SUCCESS" if success else "FAILED"
            logger.info(
                f"Performance: {provider_name} {operation} {status} "
                f"({response_time_ms}ms)"
                f"{f' tokens={tokens_used}' if tokens_used else ''}"
                f"{f' error={error}' if error else ''}"
            )
    
    def _update_provider_stats(self, provider_name: str, metric: PerformanceMetric):
        """
        Update aggregated statistics for a provider
        
        Args:
            provider_name: Name of the provider
            metric: New metric to incorporate
        """
        if provider_name not in self._provider_stats:
            self._provider_stats[provider_name] = ProviderStats(provider_name=provider_name)
        
        stats = self._provider_stats[provider_name]
        
        # Update counters
        stats.total_requests += 1
        if metric.success:
            stats.successful_requests += 1
            stats.last_success_time = metric.timestamp
        else:
            stats.failed_requests += 1
            stats.last_error_time = metric.timestamp
            stats.last_error = metric.error
        
        stats.last_request_time = metric.timestamp
        
        # Update response time statistics
        if stats.total_requests == 1:
            stats.min_response_time_ms = metric.response_time_ms
            stats.max_response_time_ms = metric.response_time_ms
            stats.avg_response_time_ms = float(metric.response_time_ms)
        else:
            stats.min_response_time_ms = min(stats.min_response_time_ms, metric.response_time_ms)
            stats.max_response_time_ms = max(stats.max_response_time_ms, metric.response_time_ms)
            
            # Update running average
            old_avg = stats.avg_response_time_ms
            stats.avg_response_time_ms = (
                (old_avg * (stats.total_requests - 1) + metric.response_time_ms) / 
                stats.total_requests
            )
        
        # Update token usage
        if metric.tokens_used:
            stats.total_tokens_used += metric.tokens_used
        
        # Calculate uptime percentage
        if stats.total_requests > 0:
            stats.uptime_percentage = (stats.successful_requests / stats.total_requests) * 100
        
        # Add to recent metrics
        stats.recent_metrics.append(metric)
    
    def get_provider_stats(self, provider_name: str) -> Optional[ProviderStats]:
        """
        Get statistics for a specific provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            ProviderStats if available, None otherwise
        """
        with self._lock:
            return self._provider_stats.get(provider_name)
    
    def get_all_provider_stats(self) -> Dict[str, ProviderStats]:
        """
        Get statistics for all providers
        
        Returns:
            Dictionary mapping provider names to their statistics
        """
        with self._lock:
            return self._provider_stats.copy()
    
    def get_provider_metrics(
        self, 
        provider_name: str, 
        limit: Optional[int] = None,
        since: Optional[datetime] = None
    ) -> List[PerformanceMetric]:
        """
        Get metrics for a specific provider
        
        Args:
            provider_name: Name of the provider
            limit: Maximum number of metrics to return
            since: Only return metrics after this timestamp
            
        Returns:
            List of performance metrics
        """
        with self._lock:
            if provider_name not in self._metrics:
                return []
            
            metrics = list(self._metrics[provider_name])
            
            # Filter by timestamp if specified
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            # Sort by timestamp (most recent first)
            metrics.sort(key=lambda m: m.timestamp, reverse=True)
            
            # Apply limit if specified
            if limit:
                metrics = metrics[:limit]
            
            return metrics
    
    def get_recent_performance(
        self, 
        provider_name: str, 
        minutes: int = 5
    ) -> Dict[str, Any]:
        """
        Get recent performance summary for a provider
        
        Args:
            provider_name: Name of the provider
            minutes: Number of minutes to look back
            
        Returns:
            Recent performance summary
        """
        since = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = self.get_provider_metrics(provider_name, since=since)
        
        if not recent_metrics:
            return {
                "provider_name": provider_name,
                "time_window_minutes": minutes,
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_response_time_ms": 0,
                "success_rate": 0.0
            }
        
        successful = sum(1 for m in recent_metrics if m.success)
        failed = len(recent_metrics) - successful
        avg_response_time = sum(m.response_time_ms for m in recent_metrics) / len(recent_metrics)
        success_rate = (successful / len(recent_metrics)) * 100 if recent_metrics else 0
        
        return {
            "provider_name": provider_name,
            "time_window_minutes": minutes,
            "total_requests": len(recent_metrics),
            "successful_requests": successful,
            "failed_requests": failed,
            "avg_response_time_ms": round(avg_response_time, 2),
            "success_rate": round(success_rate, 2),
            "last_request": recent_metrics[0].timestamp.isoformat() if recent_metrics else None
        }
    
    def get_system_performance_summary(self) -> Dict[str, Any]:
        """
        Get overall system performance summary
        
        Returns:
            System-wide performance summary
        """
        with self._lock:
            total_requests = sum(stats.total_requests for stats in self._provider_stats.values())
            total_successful = sum(stats.successful_requests for stats in self._provider_stats.values())
            total_failed = sum(stats.failed_requests for stats in self._provider_stats.values())
            
            # Calculate weighted average response time
            total_response_time = 0
            total_weight = 0
            for stats in self._provider_stats.values():
                if stats.total_requests > 0:
                    total_response_time += stats.avg_response_time_ms * stats.total_requests
                    total_weight += stats.total_requests
            
            avg_response_time = total_response_time / total_weight if total_weight > 0 else 0
            overall_success_rate = (total_successful / total_requests * 100) if total_requests > 0 else 0
            
            uptime = datetime.utcnow() - self._start_time
            
            return {
                "system_uptime_seconds": int(uptime.total_seconds()),
                "total_requests": total_requests,
                "successful_requests": total_successful,
                "failed_requests": total_failed,
                "overall_success_rate": round(overall_success_rate, 2),
                "avg_response_time_ms": round(avg_response_time, 2),
                "active_providers": len(self._provider_stats),
                "providers": list(self._provider_stats.keys())
            }
    
    def get_provider_health_metrics(self, provider_name: str) -> Dict[str, Any]:
        """
        Get health-focused metrics for a provider
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Health metrics for monitoring endpoints
        """
        stats = self.get_provider_stats(provider_name)
        recent_perf = self.get_recent_performance(provider_name, minutes=5)
        
        if not stats:
            return {
                "provider_name": provider_name,
                "available": False,
                "total_requests": 0,
                "success_rate": 0.0,
                "avg_response_time_ms": 0,
                "last_request": None,
                "last_success": None,
                "last_error": None
            }
        
        return {
            "provider_name": provider_name,
            "available": stats.uptime_percentage > 0,
            "total_requests": stats.total_requests,
            "success_rate": round(stats.uptime_percentage, 2),
            "avg_response_time_ms": round(stats.avg_response_time_ms, 2),
            "recent_avg_response_time_ms": recent_perf["avg_response_time_ms"],
            "recent_success_rate": recent_perf["success_rate"],
            "last_request": stats.last_request_time.isoformat() if stats.last_request_time else None,
            "last_success": stats.last_success_time.isoformat() if stats.last_success_time else None,
            "last_error": stats.last_error_time.isoformat() if stats.last_error_time else None,
            "last_error_message": stats.last_error,
            "total_tokens_used": stats.total_tokens_used
        }
    
    def clear_provider_metrics(self, provider_name: str):
        """
        Clear metrics for a specific provider
        
        Args:
            provider_name: Name of the provider
        """
        with self._lock:
            if provider_name in self._metrics:
                self._metrics[provider_name].clear()
            if provider_name in self._provider_stats:
                del self._provider_stats[provider_name]
            
            logger.info(f"Cleared metrics for provider: {provider_name}")
    
    def clear_all_metrics(self):
        """Clear all metrics and statistics"""
        with self._lock:
            self._metrics.clear()
            self._provider_stats.clear()
            self._start_time = datetime.utcnow()
            
            logger.info("Cleared all performance metrics")
    
    def export_metrics(
        self, 
        provider_name: Optional[str] = None,
        format: str = "dict"
    ) -> Dict[str, Any]:
        """
        Export metrics for analysis or storage
        
        Args:
            provider_name: Specific provider to export (None for all)
            format: Export format ('dict' only for now)
            
        Returns:
            Exported metrics data
        """
        with self._lock:
            if provider_name:
                providers = [provider_name] if provider_name in self._metrics else []
            else:
                providers = list(self._metrics.keys())
            
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "system_uptime_seconds": int((datetime.utcnow() - self._start_time).total_seconds()),
                "providers": {}
            }
            
            for prov_name in providers:
                metrics = list(self._metrics[prov_name])
                stats = self._provider_stats.get(prov_name)
                
                export_data["providers"][prov_name] = {
                    "statistics": {
                        "total_requests": stats.total_requests if stats else 0,
                        "successful_requests": stats.successful_requests if stats else 0,
                        "failed_requests": stats.failed_requests if stats else 0,
                        "avg_response_time_ms": stats.avg_response_time_ms if stats else 0,
                        "uptime_percentage": stats.uptime_percentage if stats else 0,
                        "total_tokens_used": stats.total_tokens_used if stats else 0
                    },
                    "recent_metrics": [
                        {
                            "timestamp": m.timestamp.isoformat(),
                            "operation": m.operation,
                            "response_time_ms": m.response_time_ms,
                            "success": m.success,
                            "error": m.error,
                            "tokens_used": m.tokens_used,
                            "model": m.model
                        }
                        for m in metrics[-50:]  # Last 50 metrics
                    ]
                }
            
            return export_data


class OperationTimer:
    """
    Context manager for timing operations
    
    Usage:
        with tracker.start_operation("gemini", "generate_response") as timer:
            # Perform operation
            result = await provider.generate_response(prompt)
            timer.set_success(True, tokens_used=result.tokens_used)
    """
    
    def __init__(self, tracker: PerformanceTracker, provider_name: str, operation: str):
        """
        Initialize the operation timer
        
        Args:
            tracker: Performance tracker instance
            provider_name: Name of the provider
            operation: Type of operation
        """
        self.tracker = tracker
        self.provider_name = provider_name
        self.operation = operation
        self.start_time = None
        self.success = False
        self.error = None
        self.tokens_used = None
        self.model = None
    
    def __enter__(self):
        """Start timing the operation"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish timing and record the metric"""
        if self.start_time is None:
            return
        
        end_time = time.time()
        response_time_ms = int((end_time - self.start_time) * 1000)
        
        # If an exception occurred and success wasn't explicitly set, mark as failed
        if exc_type is not None and not self.success:
            self.success = False
            self.error = str(exc_val) if exc_val else str(exc_type)
        
        self.tracker.record_metric(
            provider_name=self.provider_name,
            operation=self.operation,
            response_time_ms=response_time_ms,
            success=self.success,
            error=self.error,
            tokens_used=self.tokens_used,
            model=self.model
        )
    
    def set_success(
        self, 
        success: bool, 
        tokens_used: Optional[int] = None, 
        model: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Set operation result details
        
        Args:
            success: Whether the operation was successful
            tokens_used: Number of tokens used (if applicable)
            model: Model name used (if applicable)
            error: Error message if operation failed
        """
        self.success = success
        self.tokens_used = tokens_used
        self.model = model
        if error:
            self.error = error


# Global performance tracker instance
_performance_tracker: Optional[PerformanceTracker] = None


def get_performance_tracker() -> PerformanceTracker:
    """
    Get the global performance tracker instance
    
    Returns:
        PerformanceTracker instance
    """
    global _performance_tracker
    
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker()
    
    return _performance_tracker


def cleanup_performance_tracker():
    """
    Cleanup the global performance tracker
    
    This function should be called during application shutdown.
    """
    global _performance_tracker
    
    if _performance_tracker:
        _performance_tracker.clear_all_metrics()
        _performance_tracker = None