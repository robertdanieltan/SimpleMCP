"""
Fallback Manager for Multi-LLM Provider System

This module provides comprehensive fallback mechanisms when providers fail,
including rule-based responses, cached responses, and graceful degradation.
"""

import logging
import json
import time
import os
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from .base import LLMResponse, ProviderCapabilities
from .exceptions import LLMProviderError, ProviderUnavailableError
from .logging_config import get_provider_logger

logger = logging.getLogger(__name__)


class FallbackTrigger(Enum):
    """Triggers that activate fallback mechanisms"""
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    NETWORK_ERROR = "network_error"
    MODEL_ERROR = "model_error"
    TIMEOUT_ERROR = "timeout_error"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    ALL_PROVIDERS_FAILED = "all_providers_failed"


class FallbackType(Enum):
    """Types of fallback responses available"""
    RULE_BASED = "rule_based"
    TEMPLATE_BASED = "template_based"
    CACHED_RESPONSE = "cached_response"
    SIMPLE_ACKNOWLEDGMENT = "simple_acknowledgment"
    ERROR_EXPLANATION = "error_explanation"
    HELP_GUIDANCE = "help_guidance"


@dataclass
class FallbackRule:
    """Rule for determining fallback responses"""
    trigger: FallbackTrigger
    fallback_type: FallbackType
    priority: int
    conditions: Dict[str, Any] = field(default_factory=dict)
    response_template: Optional[str] = None
    custom_handler: Optional[Callable] = None


@dataclass
class FallbackResponse:
    """Fallback response with metadata"""
    response: str
    fallback_type: FallbackType
    confidence: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class IntentBasedFallback:
    """Rule-based fallback system based on user intent analysis"""
    
    def __init__(self):
        """Initialize intent-based fallback system"""
        self.intent_patterns = self._initialize_intent_patterns()
        self.response_templates = self._initialize_response_templates()
        
    def _initialize_intent_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize patterns for intent recognition"""
        return {
            "create_task": {
                "keywords": ["create", "add", "new", "make", "task"],
                "patterns": [
                    r"create.*task",
                    r"add.*task",
                    r"new.*task",
                    r"make.*task"
                ],
                "confidence_threshold": 0.6
            },
            "list_tasks": {
                "keywords": ["list", "show", "display", "get", "view", "tasks"],
                "patterns": [
                    r"list.*tasks?",
                    r"show.*tasks?",
                    r"view.*tasks?",
                    r"get.*tasks?"
                ],
                "confidence_threshold": 0.7
            },
            "update_task": {
                "keywords": ["update", "modify", "change", "edit", "task"],
                "patterns": [
                    r"update.*task",
                    r"modify.*task",
                    r"change.*task",
                    r"edit.*task"
                ],
                "confidence_threshold": 0.6
            },
            "delete_task": {
                "keywords": ["delete", "remove", "cancel", "task"],
                "patterns": [
                    r"delete.*task",
                    r"remove.*task",
                    r"cancel.*task"
                ],
                "confidence_threshold": 0.6
            },
            "create_project": {
                "keywords": ["create", "add", "new", "make", "project"],
                "patterns": [
                    r"create.*project",
                    r"add.*project",
                    r"new.*project",
                    r"make.*project"
                ],
                "confidence_threshold": 0.6
            },
            "list_projects": {
                "keywords": ["list", "show", "display", "get", "view", "projects"],
                "patterns": [
                    r"list.*projects?",
                    r"show.*projects?",
                    r"view.*projects?",
                    r"get.*projects?"
                ],
                "confidence_threshold": 0.7
            },
            "help": {
                "keywords": ["help", "how", "what", "can", "do"],
                "patterns": [
                    r"help",
                    r"what.*can.*do",
                    r"how.*work",
                    r"what.*possible"
                ],
                "confidence_threshold": 0.5
            },
            "status": {
                "keywords": ["status", "health", "working", "available"],
                "patterns": [
                    r"status",
                    r"health",
                    r"working",
                    r"available"
                ],
                "confidence_threshold": 0.6
            }
        }
    
    def _initialize_response_templates(self) -> Dict[str, List[str]]:
        """Initialize response templates for different intents"""
        return {
            "create_task": [
                "I understand you want to create a task. While I'm experiencing technical difficulties, I can guide you through the process. Please provide the task title and any details you'd like to include.",
                "I'd be happy to help you create a task. Due to current service limitations, please specify the task name and description, and I'll assist you with the next steps.",
                "To create a task, I'll need some information from you. Please tell me the task title and any relevant details, and I'll help you organize it."
            ],
            "list_tasks": [
                "I understand you want to see your tasks. While I'm currently unable to access the task database, I recommend checking your task management interface directly or trying again in a few moments.",
                "You're looking for your task list. Due to technical limitations right now, please try refreshing your task view or check back shortly.",
                "I'd like to show you your tasks, but I'm experiencing connectivity issues. Please try accessing your tasks directly through the interface."
            ],
            "update_task": [
                "I see you want to update a task. While I'm having technical difficulties, please specify which task you'd like to modify and what changes you want to make.",
                "To help you update a task, I'll need to know the task identifier and what changes you'd like to make. Due to current limitations, please provide these details.",
                "I understand you want to modify a task. Please tell me which task and what updates you need, and I'll guide you through the process."
            ],
            "delete_task": [
                "I understand you want to delete a task. While I'm experiencing service issues, please specify which task you'd like to remove, and I'll help you with the process.",
                "To help you delete a task, please provide the task identifier or description. Due to current technical limitations, I'll guide you through the steps.",
                "I see you want to remove a task. Please specify which task, and I'll assist you with the deletion process despite current service limitations."
            ],
            "create_project": [
                "I understand you want to create a project. While I'm having technical difficulties, please provide the project name and description, and I'll help you organize it.",
                "I'd be happy to help you create a project. Due to current service limitations, please specify the project details, and I'll guide you through the setup.",
                "To create a project, please tell me the project name and any relevant information, and I'll assist you with the organization."
            ],
            "list_projects": [
                "I understand you want to see your projects. While I'm currently unable to access the project database, please try checking your project interface directly.",
                "You're looking for your project list. Due to technical limitations, please try accessing your projects through the main interface or check back shortly.",
                "I'd like to show you your projects, but I'm experiencing connectivity issues. Please try accessing your project view directly."
            ],
            "help": [
                "I'm here to help with task and project management! I can assist you with creating tasks, organizing projects, updating task statuses, and managing your workflow. What would you like to do?",
                "I can help you manage tasks and projects. You can ask me to create new tasks, list existing ones, update task details, create projects, or organize your work. How can I assist you today?",
                "I'm your task and project management assistant. I can help you create, update, list, and organize tasks and projects. What would you like to work on?"
            ],
            "status": [
                "I'm currently experiencing some technical difficulties with my AI services, but I'm still here to help you with basic task and project management guidance.",
                "My AI capabilities are temporarily limited due to service issues, but I can still provide guidance and help you organize your tasks and projects.",
                "I'm operating in limited mode due to technical issues, but I'm available to help you with task and project management questions and guidance."
            ],
            "general": [
                "I'm here to help with task and project management. While I'm experiencing some technical difficulties, I can still provide guidance and assistance. What would you like to work on?",
                "I understand you have a request. Due to current technical limitations, I may not be able to provide my full AI capabilities, but I'm here to help with task and project management. Can you tell me more about what you need?",
                "I'm available to assist you with task and project management. While my AI services are temporarily limited, I can still provide guidance and help you organize your work. How can I help?"
            ]
        }
    
    def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user intent using rule-based pattern matching
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Intent analysis results
        """
        import re
        
        user_lower = user_input.lower()
        intent_scores = {}
        
        # Score each intent based on keyword and pattern matching
        for intent, config in self.intent_patterns.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in config["keywords"] if keyword in user_lower)
            if keyword_matches > 0:
                score += (keyword_matches / len(config["keywords"])) * 0.6
            
            # Pattern matching
            pattern_matches = sum(1 for pattern in config["patterns"] if re.search(pattern, user_lower))
            if pattern_matches > 0:
                score += (pattern_matches / len(config["patterns"])) * 0.4
            
            if score >= config["confidence_threshold"]:
                intent_scores[intent] = score
        
        # Find best matching intent
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            return {
                "intent": best_intent[0],
                "confidence": best_intent[1],
                "entities": self._extract_entities(user_input, best_intent[0]),
                "action": self._map_intent_to_action(best_intent[0]),
                "source": "fallback_rule_based"
            }
        else:
            return {
                "intent": "general",
                "confidence": 0.3,
                "entities": {},
                "action": "general_response",
                "source": "fallback_rule_based"
            }
    
    def _extract_entities(self, user_input: str, intent: str) -> Dict[str, Any]:
        """Extract entities based on intent"""
        entities = {}
        
        # Simple entity extraction based on intent
        if intent in ["create_task", "update_task", "delete_task"]:
            # Try to extract task-related entities
            import re
            
            # Look for quoted strings as task names
            quoted_matches = re.findall(r'"([^"]*)"', user_input)
            if quoted_matches:
                entities["task_name"] = quoted_matches[0]
            
            # Look for priority indicators
            if any(word in user_input.lower() for word in ["high", "urgent", "important"]):
                entities["priority"] = "high"
            elif any(word in user_input.lower() for word in ["low", "minor"]):
                entities["priority"] = "low"
            else:
                entities["priority"] = "medium"
        
        elif intent in ["create_project"]:
            # Try to extract project-related entities
            import re
            
            quoted_matches = re.findall(r'"([^"]*)"', user_input)
            if quoted_matches:
                entities["project_name"] = quoted_matches[0]
        
        return entities
    
    def _map_intent_to_action(self, intent: str) -> str:
        """Map intent to action"""
        action_map = {
            "create_task": "create_task",
            "list_tasks": "list_tasks",
            "update_task": "update_task",
            "delete_task": "delete_task",
            "create_project": "create_project",
            "list_projects": "list_projects",
            "help": "help_response",
            "status": "status_response",
            "general": "general_response"
        }
        return action_map.get(intent, "general_response")
    
    def generate_response(self, intent: str, confidence: float) -> str:
        """
        Generate appropriate fallback response based on intent
        
        Args:
            intent: Detected intent
            confidence: Confidence score
            
        Returns:
            Fallback response string
        """
        import random
        
        templates = self.response_templates.get(intent, self.response_templates["general"])
        
        # Select response based on confidence
        if confidence > 0.8:
            # High confidence - use specific response
            return random.choice(templates)
        elif confidence > 0.5:
            # Medium confidence - use specific response with uncertainty
            response = random.choice(templates)
            return f"I think {response.lower()}"
        else:
            # Low confidence - use general response
            return random.choice(self.response_templates["general"])


class CachedResponseManager:
    """Manager for cached responses to provide fallback content"""
    
    def __init__(self, cache_file: Optional[str] = None):
        """
        Initialize cached response manager
        
        Args:
            cache_file: Path to cache file (optional)
        """
        self.cache_file = cache_file
        self.response_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "total_entries": 0
        }
        
        if cache_file:
            self._load_cache()
    
    def _load_cache(self):
        """Load cached responses from file"""
        try:
            if self.cache_file and Path(self.cache_file).exists():
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.response_cache = data.get("responses", {})
                    self.cache_stats = data.get("stats", self.cache_stats)
                logger.info(f"Loaded {len(self.response_cache)} cached responses")
        except Exception as e:
            logger.warning(f"Failed to load response cache: {e}")
    
    def _save_cache(self):
        """Save cached responses to file"""
        try:
            if self.cache_file:
                cache_data = {
                    "responses": self.response_cache,
                    "stats": self.cache_stats,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Ensure directory exists
                Path(self.cache_file).parent.mkdir(parents=True, exist_ok=True)
                
                with open(self.cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save response cache: {e}")
    
    def get_cached_response(self, user_input: str, intent: str) -> Optional[str]:
        """
        Get cached response for similar input
        
        Args:
            user_input: User's input
            intent: Detected intent
            
        Returns:
            Cached response if found, None otherwise
        """
        # Create cache key based on input and intent
        cache_key = self._create_cache_key(user_input, intent)
        
        if cache_key in self.response_cache:
            self.cache_stats["hits"] += 1
            cached_entry = self.response_cache[cache_key]
            
            # Check if cache entry is still valid (not too old)
            cache_age = datetime.utcnow() - datetime.fromisoformat(cached_entry["timestamp"])
            if cache_age < timedelta(hours=24):  # Cache valid for 24 hours
                return cached_entry["response"]
        
        self.cache_stats["misses"] += 1
        return None
    
    def cache_response(self, user_input: str, intent: str, response: str):
        """
        Cache a response for future use
        
        Args:
            user_input: User's input
            intent: Detected intent
            response: Response to cache
        """
        cache_key = self._create_cache_key(user_input, intent)
        
        self.response_cache[cache_key] = {
            "response": response,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat(),
            "input_length": len(user_input)
        }
        
        self.cache_stats["total_entries"] = len(self.response_cache)
        
        # Save cache periodically
        if self.cache_stats["total_entries"] % 10 == 0:
            self._save_cache()
    
    def _create_cache_key(self, user_input: str, intent: str) -> str:
        """Create cache key from input and intent"""
        import hashlib
        
        # Normalize input
        normalized_input = user_input.lower().strip()
        
        # Create hash of normalized input + intent
        cache_string = f"{normalized_input}:{intent}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = (
            self.cache_stats["hits"] / (self.cache_stats["hits"] + self.cache_stats["misses"])
            if (self.cache_stats["hits"] + self.cache_stats["misses"]) > 0 else 0.0
        )
        
        return {
            **self.cache_stats,
            "hit_rate": hit_rate
        }


class FallbackManager:
    """
    Comprehensive fallback manager for handling provider failures
    
    Provides multiple fallback strategies including rule-based responses,
    cached responses, and graceful degradation mechanisms.
    """
    
    def __init__(self, cache_file: Optional[str] = None):
        """
        Initialize fallback manager
        
        Args:
            cache_file: Path to cache file for storing responses
        """
        self.intent_fallback = IntentBasedFallback()
        self.cache_manager = CachedResponseManager(cache_file)
        self.fallback_rules = self._initialize_fallback_rules()
        self.fallback_stats = {
            "total_fallbacks": 0,
            "fallback_types": {},
            "success_rate": 0.0
        }
        
        logger.info("Fallback manager initialized with comprehensive fallback strategies")
    
    def _initialize_fallback_rules(self) -> List[FallbackRule]:
        """Initialize fallback rules in priority order"""
        return [
            FallbackRule(
                trigger=FallbackTrigger.AUTHENTICATION_ERROR,
                fallback_type=FallbackType.ERROR_EXPLANATION,
                priority=1,
                response_template="I'm experiencing authentication issues with the AI service. Please check the configuration and try again in a few moments."
            ),
            FallbackRule(
                trigger=FallbackTrigger.RATE_LIMIT_EXCEEDED,
                fallback_type=FallbackType.ERROR_EXPLANATION,
                priority=2,
                response_template="The AI service is currently rate limited. Please wait a moment and try again."
            ),
            FallbackRule(
                trigger=FallbackTrigger.NETWORK_ERROR,
                fallback_type=FallbackType.ERROR_EXPLANATION,
                priority=3,
                response_template="I'm having trouble connecting to the AI service. Please check your network connection and try again."
            ),
            FallbackRule(
                trigger=FallbackTrigger.PROVIDER_UNAVAILABLE,
                fallback_type=FallbackType.RULE_BASED,
                priority=4
            ),
            FallbackRule(
                trigger=FallbackTrigger.ALL_PROVIDERS_FAILED,
                fallback_type=FallbackType.RULE_BASED,
                priority=5
            )
        ]
    
    def handle_provider_failure(
        self,
        user_input: str,
        error: LLMProviderError,
        provider_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> LLMResponse:
        """
        Handle provider failure with appropriate fallback strategy
        
        Args:
            user_input: User's original input
            error: The error that occurred
            provider_name: Name of the failed provider
            context: Optional context information
            
        Returns:
            LLMResponse with fallback content
        """
        # Determine trigger based on error type
        trigger = self._determine_trigger(error)
        
        # Find appropriate fallback rule
        fallback_rule = self._find_fallback_rule(trigger)
        
        # Generate fallback response
        fallback_response = self._generate_fallback_response(
            user_input, fallback_rule, provider_name, context
        )
        
        # Update statistics
        self._update_fallback_stats(fallback_rule.fallback_type)
        
        # Log fallback usage
        logger.warning(f"Using fallback for provider {provider_name}: {trigger.value} -> {fallback_rule.fallback_type.value}")
        
        return LLMResponse(
            success=True,  # Fallback is considered successful
            response=fallback_response.response,
            source=f"{provider_name}_fallback",
            error=f"Fallback used due to: {error.error_code}",
            timestamp=datetime.utcnow()
        )
    
    def _determine_trigger(self, error: LLMProviderError) -> FallbackTrigger:
        """Determine fallback trigger based on error type"""
        from .exceptions import (
            ProviderAuthenticationError,
            ProviderRateLimitError,
            ProviderNetworkError,
            ProviderModelError,
            ProviderUnavailableError
        )
        
        if isinstance(error, ProviderAuthenticationError):
            return FallbackTrigger.AUTHENTICATION_ERROR
        elif isinstance(error, ProviderRateLimitError):
            return FallbackTrigger.RATE_LIMIT_EXCEEDED
        elif isinstance(error, ProviderNetworkError):
            return FallbackTrigger.NETWORK_ERROR
        elif isinstance(error, ProviderModelError):
            return FallbackTrigger.MODEL_ERROR
        elif isinstance(error, ProviderUnavailableError):
            return FallbackTrigger.PROVIDER_UNAVAILABLE
        else:
            return FallbackTrigger.PROVIDER_UNAVAILABLE
    
    def _find_fallback_rule(self, trigger: FallbackTrigger) -> FallbackRule:
        """Find appropriate fallback rule for trigger"""
        # Find rule with matching trigger
        for rule in self.fallback_rules:
            if rule.trigger == trigger:
                return rule
        
        # Default fallback rule
        return FallbackRule(
            trigger=FallbackTrigger.PROVIDER_UNAVAILABLE,
            fallback_type=FallbackType.RULE_BASED,
            priority=999
        )
    
    def _generate_fallback_response(
        self,
        user_input: str,
        fallback_rule: FallbackRule,
        provider_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> FallbackResponse:
        """Generate fallback response based on rule"""
        
        if fallback_rule.fallback_type == FallbackType.ERROR_EXPLANATION:
            # Use predefined error explanation
            response = fallback_rule.response_template or "I'm experiencing technical difficulties. Please try again later."
            return FallbackResponse(
                response=response,
                fallback_type=FallbackType.ERROR_EXPLANATION,
                confidence=0.9,
                source="error_template"
            )
        
        elif fallback_rule.fallback_type == FallbackType.CACHED_RESPONSE:
            # Try to get cached response first
            intent_analysis = self.intent_fallback.analyze_intent(user_input)
            cached_response = self.cache_manager.get_cached_response(
                user_input, intent_analysis["intent"]
            )
            
            if cached_response:
                return FallbackResponse(
                    response=cached_response,
                    fallback_type=FallbackType.CACHED_RESPONSE,
                    confidence=0.8,
                    source="cache"
                )
            
            # Fall back to rule-based if no cache
            return self._generate_rule_based_response(user_input)
        
        elif fallback_rule.fallback_type == FallbackType.RULE_BASED:
            return self._generate_rule_based_response(user_input)
        
        else:
            # Default simple acknowledgment
            return FallbackResponse(
                response="I understand your request, but I'm experiencing technical difficulties. Please try again later.",
                fallback_type=FallbackType.SIMPLE_ACKNOWLEDGMENT,
                confidence=0.5,
                source="default"
            )
    
    def _generate_rule_based_response(self, user_input: str) -> FallbackResponse:
        """Generate rule-based fallback response"""
        # Analyze intent using rule-based system
        intent_analysis = self.intent_fallback.analyze_intent(user_input)
        
        # Generate response based on intent
        response = self.intent_fallback.generate_response(
            intent_analysis["intent"],
            intent_analysis["confidence"]
        )
        
        return FallbackResponse(
            response=response,
            fallback_type=FallbackType.RULE_BASED,
            confidence=intent_analysis["confidence"],
            source="rule_based",
            metadata={
                "intent": intent_analysis["intent"],
                "entities": intent_analysis["entities"]
            }
        )
    
    def _update_fallback_stats(self, fallback_type: FallbackType):
        """Update fallback usage statistics"""
        self.fallback_stats["total_fallbacks"] += 1
        
        if fallback_type.value not in self.fallback_stats["fallback_types"]:
            self.fallback_stats["fallback_types"][fallback_type.value] = 0
        
        self.fallback_stats["fallback_types"][fallback_type.value] += 1
    
    def get_fallback_capabilities(self) -> Dict[str, Any]:
        """Get information about fallback capabilities"""
        return {
            "available_fallback_types": [ft.value for ft in FallbackType],
            "supported_intents": list(self.intent_fallback.intent_patterns.keys()),
            "cache_stats": self.cache_manager.get_cache_stats(),
            "fallback_stats": self.fallback_stats.copy(),
            "fallback_rules_count": len(self.fallback_rules)
        }
    
    def test_fallback_system(self, test_inputs: List[str]) -> Dict[str, Any]:
        """
        Test fallback system with sample inputs
        
        Args:
            test_inputs: List of test input strings
            
        Returns:
            Test results
        """
        test_results = []
        
        for test_input in test_inputs:
            try:
                # Simulate provider failure
                fake_error = ProviderUnavailableError("Test error", provider="test")
                
                # Generate fallback response
                fallback_response = self.handle_provider_failure(
                    test_input, fake_error, "test_provider"
                )
                
                test_results.append({
                    "input": test_input,
                    "success": fallback_response.success,
                    "response": fallback_response.response,
                    "source": fallback_response.source
                })
                
            except Exception as e:
                test_results.append({
                    "input": test_input,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "test_count": len(test_inputs),
            "success_count": sum(1 for r in test_results if r.get("success", False)),
            "results": test_results
        }


# Global fallback manager instance
_fallback_manager = None


def get_fallback_manager() -> FallbackManager:
    """Get the global fallback manager instance"""
    global _fallback_manager
    if _fallback_manager is None:
        cache_file = os.getenv("FALLBACK_CACHE_FILE", "data/fallback_cache.json")
        _fallback_manager = FallbackManager(cache_file)
    return _fallback_manager