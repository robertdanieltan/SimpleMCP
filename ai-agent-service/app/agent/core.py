"""
AI Agent Core Logic

This module contains the main agent processing logic that coordinates between
natural language understanding (via selected LLM provider) and MCP service operations.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..llm.provider_selector import get_provider_selector, get_selected_provider
from ..llm.performance_tracker import get_performance_tracker
from ..llm.error_handler import get_error_handler, create_error_context
from ..llm.fallback_manager import get_fallback_manager
from ..llm.logging_config import get_logging_config
from ..mcp_client.http_client import MCPClient

logger = logging.getLogger(__name__)


class AIAgent:
    """
    Main AI Agent class that processes user requests and coordinates
    between selected LLM provider and MCP service operations
    """
    
    def __init__(self):
        """Initialize the AI agent with provider selector and MCP client"""
        self.mcp_client = MCPClient()
        self.session_context = {}
        self._provider_selector = None
        self._llm_provider = None
        self._performance_tracker = get_performance_tracker()
        
        logger.info("AI Agent initialized")
    
    async def _ensure_provider_initialized(self):
        """Ensure the LLM provider is initialized"""
        if self._provider_selector is None:
            self._provider_selector = await get_provider_selector()
        
        if self._llm_provider is None:
            self._llm_provider = await get_selected_provider()
    
    def _check_mcp_availability(self) -> Dict[str, Any]:
        """Check if MCP service is available with performance tracking"""
        start_time = time.time()
        try:
            health = self.mcp_client.health_check()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            is_healthy = health.get("status") == "healthy"
            
            return {
                "available": is_healthy,
                "url": self.mcp_client.base_url,
                "response_time_ms": response_time_ms,
                "last_check": datetime.utcnow().isoformat(),
                "status": health.get("status", "unknown"),
                "error": None if is_healthy else health.get("error", "Service unhealthy")
            }
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            logger.error(f"MCP service health check failed: {e}")
            return {
                "available": False,
                "url": self.mcp_client.base_url,
                "response_time_ms": response_time_ms,
                "last_check": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status including all service dependencies with performance metrics
        
        Returns:
            Status information dictionary with performance data
        """
        await self._ensure_provider_initialized()
        
        # Get LLM provider status with performance metrics
        current_provider = None
        if self._provider_selector:
            provider_status = self._provider_selector.get_provider_status()
            
            if provider_status.get("available", False):
                current_provider = {
                    "provider_name": provider_status.get("provider_name", "unknown"),
                    "model": provider_status.get("model", "unknown"),
                    "available": provider_status.get("available", False),
                    "initialized": provider_status.get("initialized", False),
                    "health_status": provider_status.get("health_status", "unknown"),
                    "capabilities": provider_status.get("capabilities", {}),
                    "performance": provider_status.get("performance_metrics", {})
                }
        
        # Get MCP service status with performance tracking
        mcp_status = self._check_mcp_availability()
        
        # Get system performance metrics
        system_perf = self._performance_tracker.get_system_performance_summary()
        
        # Determine overall agent status
        agent_status = "ready"
        if not current_provider or not current_provider["available"]:
            agent_status = "degraded"
        elif not mcp_status["available"]:
            agent_status = "degraded"
        
        return {
            "agent_status": agent_status,
            "timestamp": datetime.utcnow().isoformat(),
            "current_provider": current_provider,
            "services": {
                "mcp_service": mcp_status
            },
            "capabilities": [
                "natural_language_processing",
                "task_management", 
                "project_management",
                "intent_analysis"
            ],
            "configuration": self._provider_selector.get_configuration_summary() if self._provider_selector else None,
            "performance_metrics": {
                "system_uptime_seconds": system_perf.get("system_uptime_seconds", 0),
                "total_requests": system_perf.get("total_requests", 0),
                "overall_success_rate": system_perf.get("overall_success_rate", 0.0),
                "avg_response_time_ms": system_perf.get("avg_response_time_ms", 0.0),
                "active_providers": system_perf.get("active_providers", 0)
            }
        }
    
    async def process_request(
        self, 
        user_input: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request through the complete AI agent pipeline
        
        Args:
            user_input: Natural language input from user
            context: Optional additional context
            
        Returns:
            Processed response with action results
        """
        error_handler = get_error_handler()
        fallback_manager = get_fallback_manager()
        
        # Create error context for the entire request
        error_context = create_error_context(
            provider_name=self._provider_selector.get_selected_provider_name() if self._provider_selector else "unknown",
            operation="process_request",
            user_input=user_input,
            additional_context=context or {}
        )
        
        try:
            logger.info(f"Processing user request: {user_input[:100]}...")
            
            # Ensure LLM provider is initialized
            await self._ensure_provider_initialized()
            
            # Check if we have any available provider
            if not self._llm_provider or not self._llm_provider.is_available():
                logger.warning("No LLM provider available, using fallback system")
                
                # Use fallback manager for complete request handling
                from ..llm.exceptions import ProviderUnavailableError
                fallback_error = ProviderUnavailableError(
                    "No LLM provider available",
                    provider="system"
                )
                
                fallback_response = fallback_manager.handle_provider_failure(
                    user_input, fallback_error, "system", context
                )
                
                return {
                    "success": True,  # Fallback is considered successful
                    "user_input": user_input,
                    "intent": {"intent": "fallback", "confidence": 0.5, "source": "fallback"},
                    "action_result": {"success": True, "message": "Using fallback system"},
                    "response": fallback_response.response,
                    "provider": "fallback_system",
                    "timestamp": datetime.utcnow().isoformat(),
                    "fallback_used": True
                }
            
            # Step 1: Analyze user intent with error handling
            intent_analysis = await self._analyze_intent_with_fallback(user_input)
            logger.info(f"Intent analysis: {intent_analysis.get('intent', 'unknown')}")
            
            # Step 2: Execute appropriate action based on intent
            action_result = await self._execute_action(intent_analysis, user_input, context)
            
            # Step 3: Generate natural language response with error handling
            response = await self._generate_response_with_fallback(
                user_input, 
                intent_analysis, 
                action_result, 
                context
            )
            
            return {
                "success": True,
                "user_input": user_input,
                "intent": intent_analysis,
                "action_result": action_result,
                "response": response,
                "provider": self._provider_selector.get_selected_provider_name() if self._provider_selector else "unknown",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            # Log the error with full context
            logger.error(f"Error processing request: {e}", extra={
                "user_input": user_input[:100],
                "error_type": type(e).__name__,
                "request_id": error_context.request_id
            })
            
            # Try to provide a meaningful fallback response
            try:
                from ..llm.exceptions import LLMProviderError
                if isinstance(e, LLMProviderError):
                    fallback_response = fallback_manager.handle_provider_failure(
                        user_input, e, error_context.provider_name, context
                    )
                    response_text = fallback_response.response
                else:
                    response_text = "I apologize, but I encountered an error processing your request. Please try again."
            except Exception:
                response_text = "I apologize, but I encountered an error processing your request. Please try again."
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "response": response_text,
                "timestamp": datetime.utcnow().isoformat(),
                "fallback_used": True
            }
    
    async def _analyze_intent_with_fallback(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user intent using the selected LLM provider with comprehensive fallback
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Intent analysis results
        """
        if self._llm_provider and self._llm_provider.is_available():
            provider_name = self._provider_selector.get_selected_provider_name()
            
            with self._performance_tracker.start_operation(provider_name, "analyze_intent") as timer:
                try:
                    result = await self._llm_provider.analyze_intent(user_input)
                    timer.set_success(True)
                    return result
                except Exception as e:
                    timer.set_success(False, error=str(e))
                    logger.error(f"Intent analysis failed with provider: {e}")
                    
                    # Use fallback manager for intent analysis
                    fallback_manager = get_fallback_manager()
                    fallback_intent = fallback_manager.intent_fallback.analyze_intent(user_input)
                    return fallback_intent
        else:
            logger.warning("No LLM provider available, using fallback intent analysis")
            fallback_manager = get_fallback_manager()
            return fallback_manager.intent_fallback.analyze_intent(user_input)
    
    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user intent using the selected LLM provider with performance tracking
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Intent analysis results
        """
        return await self._analyze_intent_with_fallback(user_input)
    
    def _fallback_intent_analysis(self, user_input: str) -> Dict[str, Any]:
        """
        Simple fallback intent analysis when no LLM provider is available
        
        Args:
            user_input: User's input
            
        Returns:
            Basic intent analysis
        """
        user_lower = user_input.lower()
        
        # Simple keyword matching
        if any(word in user_lower for word in ["create", "add", "new"]):
            if "project" in user_lower:
                return {
                    "intent": "create_project",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "create_project",
                    "source": "fallback"
                }
            else:
                return {
                    "intent": "create_task",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "create_task",
                    "source": "fallback"
                }
        elif any(word in user_lower for word in ["list", "show", "get", "view"]):
            if "project" in user_lower:
                return {
                    "intent": "list_projects",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "list_projects",
                    "source": "fallback"
                }
            else:
                return {
                    "intent": "list_tasks",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "list_tasks",
                    "source": "fallback"
                }
        elif any(word in user_lower for word in ["update", "modify", "change", "edit"]):
            return {
                "intent": "update_task",
                "confidence": 0.6,
                "entities": {},
                "action": "update_task",
                "source": "fallback"
            }
        elif any(word in user_lower for word in ["delete", "remove", "cancel"]):
            return {
                "intent": "delete_task",
                "confidence": 0.6,
                "entities": {},
                "action": "delete_task",
                "source": "fallback"
            }
        else:
            return {
                "intent": "general_query",
                "confidence": 0.5,
                "entities": {},
                "action": "general_response",
                "source": "fallback"
            }

    async def _execute_action(
        self, 
        intent_analysis: Dict[str, Any], 
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the appropriate action based on intent analysis
        
        Args:
            intent_analysis: Results from intent analysis
            user_input: Original user input
            context: Optional context
            
        Returns:
            Action execution results
        """
        action = intent_analysis.get("action", "general_response")
        entities = intent_analysis.get("entities", {})
        
        try:
            if action == "create_task":
                return await self._handle_create_task(user_input, entities)
            elif action == "list_tasks":
                return await self._handle_list_tasks(entities)
            elif action == "update_task":
                return await self._handle_update_task(user_input, entities)
            elif action == "delete_task":
                return await self._handle_delete_task(user_input, entities)
            elif action == "create_project":
                return await self._handle_create_project(user_input, entities)
            elif action == "list_projects":
                return await self._handle_list_projects(entities)
            else:
                return await self._handle_general_query(user_input, context)
                
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to execute the requested action"
            }
    
    async def _handle_create_task(self, user_input: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task creation requests"""
        # Extract task details from user input using selected LLM provider if available
        if self._llm_provider and self._llm_provider.is_available():
            provider_name = self._provider_selector.get_selected_provider_name()
            extraction_prompt = f"""
Extract task details from this request: "{user_input}"

Provide a JSON response with:
{{
    "title": "task title",
    "description": "task description",
    "priority": "high|medium|low",
    "project_id": null,
    "assigned_to": "person name if mentioned",
    "due_date": "YYYY-MM-DD if mentioned"
}}
"""
            
            with self._performance_tracker.start_operation(provider_name, "generate_response") as timer:
                try:
                    llm_response = await self._llm_provider.generate_response(extraction_prompt)
                    timer.set_success(llm_response.success, tokens_used=llm_response.tokens_used, model=llm_response.model)
                    
                    if llm_response.success:
                        try:
                            import json
                            # Try to extract JSON from the response
                            from ..llm.utils import extract_json_from_response
                            task_data = extract_json_from_response(llm_response.response)
                            if not task_data:
                                # Fallback to basic extraction
                                task_data = {"title": user_input, "description": "", "priority": "medium"}
                        except Exception:
                            # Fallback to basic extraction
                            task_data = {"title": user_input, "description": "", "priority": "medium"}
                    else:
                        task_data = {"title": user_input, "description": "", "priority": "medium"}
                except Exception as e:
                    timer.set_success(False, error=str(e))
                    logger.error(f"Task extraction failed: {e}")
                    task_data = {"title": user_input, "description": "", "priority": "medium"}
        else:
            # Simple fallback extraction
            task_data = {"title": user_input, "description": "", "priority": "medium"}
        
        # Create task via MCP service
        try:
            result = self.mcp_client.create_task(
                title=task_data.get("title", ""),
                description=task_data.get("description"),
                project_id=task_data.get("project_id"),
                priority=task_data.get("priority", "medium"),
                assigned_to=task_data.get("assigned_to"),
                due_date=task_data.get("due_date")
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create task"
            }
    
    async def _handle_list_tasks(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task listing requests"""
        # Extract filters from entities if available
        filters = {}
        if "status" in entities:
            filters["status"] = entities["status"]
        if "project_id" in entities:
            filters["project_id"] = entities["project_id"]
        
        try:
            result = self.mcp_client.list_tasks(
                project_id=filters.get("project_id"),
                status=filters.get("status")
            )
            return result
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list tasks"
            }
    
    async def _handle_update_task(self, user_input: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task update requests"""
        # This would need more sophisticated parsing to identify which task to update
        # For now, return a helpful message
        return {
            "success": False,
            "message": "Task updates require more specific information. Please specify the task ID and what you'd like to change.",
            "suggestion": "Try: 'Update task 1 status to completed' or 'Change task 2 priority to high'"
        }
    
    async def _handle_delete_task(self, user_input: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task deletion requests"""
        # This would need task ID extraction
        return {
            "success": False,
            "message": "Task deletion requires a specific task ID. Please specify which task to delete.",
            "suggestion": "Try: 'Delete task 1' or 'Remove task with ID 5'"
        }
    
    async def _handle_create_project(self, user_input: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project creation requests"""
        # Extract project details using selected LLM provider if available
        if self._llm_provider and self._llm_provider.is_available():
            provider_name = self._provider_selector.get_selected_provider_name()
            extraction_prompt = f"""
Extract project details from this request: "{user_input}"

Provide a JSON response with:
{{
    "name": "project name",
    "description": "project description",
    "status": "active"
}}
"""
            
            with self._performance_tracker.start_operation(provider_name, "generate_response") as timer:
                try:
                    llm_response = await self._llm_provider.generate_response(extraction_prompt)
                    timer.set_success(llm_response.success, tokens_used=llm_response.tokens_used, model=llm_response.model)
                    
                    if llm_response.success:
                        try:
                            from ..llm.utils import extract_json_from_response
                            project_data = extract_json_from_response(llm_response.response)
                            if not project_data:
                                project_data = {"name": user_input, "description": "", "status": "active"}
                        except Exception:
                            project_data = {"name": user_input, "description": "", "status": "active"}
                    else:
                        project_data = {"name": user_input, "description": "", "status": "active"}
                except Exception as e:
                    timer.set_success(False, error=str(e))
                    logger.error(f"Project extraction failed: {e}")
                    project_data = {"name": user_input, "description": "", "status": "active"}
        else:
            project_data = {"name": user_input, "description": "", "status": "active"}
        
        try:
            result = self.mcp_client.create_project(
                name=project_data.get("name", ""),
                description=project_data.get("description"),
                status=project_data.get("status", "active")
            )
            return result
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create project"
            }
    
    async def _handle_list_projects(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle project listing requests"""
        try:
            result = self.mcp_client.list_projects()
            return result
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to list projects"
            }
    
    async def _handle_general_query(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle general queries and conversations"""
        if self._llm_provider and self._llm_provider.is_available():
            provider_name = self._provider_selector.get_selected_provider_name()
            
            with self._performance_tracker.start_operation(provider_name, "generate_response") as timer:
                try:
                    response = await self._llm_provider.generate_response(user_input, context)
                    timer.set_success(response.success, tokens_used=response.tokens_used, model=response.model)
                    
                    return {
                        "success": True,
                        "type": "general_response",
                        "message": response.response
                    }
                except Exception as e:
                    timer.set_success(False, error=str(e))
                    logger.error(f"General query failed: {e}")
                    return {
                        "success": True,
                        "type": "general_response",
                        "message": "I'm here to help with task and project management. You can ask me to create tasks, list projects, or manage your work items."
                    }
        else:
            return {
                "success": True,
                "type": "general_response",
                "message": "I'm here to help with task and project management. You can ask me to create tasks, list projects, or manage your work items."
            }
    
    async def _generate_response_with_fallback(
        self,
        user_input: str,
        intent_analysis: Dict[str, Any],
        action_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a natural language response with comprehensive fallback handling
        
        Args:
            user_input: Original user input
            intent_analysis: Intent analysis results
            action_result: Results from action execution
            context: Optional context
            
        Returns:
            Natural language response string
        """
        if not (self._llm_provider and self._llm_provider.is_available()):
            return self._generate_fallback_response(intent_analysis, action_result)
        
        # Create a prompt for response generation
        response_prompt = f"""
Generate a helpful, natural response for this interaction:

User asked: "{user_input}"
Intent: {intent_analysis.get('intent', 'unknown')}
Action result: {action_result}

Provide a conversational response that:
1. Acknowledges what the user requested
2. Explains what happened (success or failure)
3. Provides relevant information from the results
4. Offers next steps if appropriate

Keep it concise and helpful.
"""
        
        provider_name = self._provider_selector.get_selected_provider_name()
        
        with self._performance_tracker.start_operation(provider_name, "generate_response") as timer:
            try:
                llm_response = await self._llm_provider.generate_response(response_prompt)
                timer.set_success(llm_response.success, tokens_used=llm_response.tokens_used, model=llm_response.model)
                
                if llm_response.success:
                    return llm_response.response
                else:
                    # Use enhanced fallback system
                    return self._generate_enhanced_fallback_response(
                        user_input, intent_analysis, action_result
                    )
            except Exception as e:
                timer.set_success(False, error=str(e))
                logger.error(f"Response generation failed: {e}")
                return self._generate_enhanced_fallback_response(
                    user_input, intent_analysis, action_result
                )
    
    async def _generate_response(
        self,
        user_input: str,
        intent_analysis: Dict[str, Any],
        action_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a natural language response based on the action results
        
        Args:
            user_input: Original user input
            intent_analysis: Intent analysis results
            action_result: Results from action execution
            context: Optional context
            
        Returns:
            Natural language response string
        """
        return await self._generate_response_with_fallback(
            user_input, intent_analysis, action_result, context
        )
    
    def _generate_enhanced_fallback_response(
        self,
        user_input: str,
        intent_analysis: Dict[str, Any], 
        action_result: Dict[str, Any]
    ) -> str:
        """
        Generate enhanced fallback response using fallback manager
        
        Args:
            user_input: Original user input
            intent_analysis: Intent analysis results
            action_result: Action execution results
            
        Returns:
            Enhanced fallback response string
        """
        fallback_manager = get_fallback_manager()
        
        # If action was successful, generate success response
        if action_result.get("success"):
            intent = intent_analysis.get("intent", "unknown")
            
            # Use intent-based response generation
            if intent in ["create_task", "create_project"]:
                base_response = fallback_manager.intent_fallback.generate_response(intent, 0.8)
                # Customize based on action result
                if "data" in action_result and action_result["data"]:
                    item_name = action_result["data"].get("title") or action_result["data"].get("name", "item")
                    return f"Great! I've successfully created '{item_name}' for you."
                else:
                    return base_response
            
            elif intent in ["list_tasks", "list_projects"]:
                items = action_result.get("data", [])
                item_type = "tasks" if intent == "list_tasks" else "projects"
                if len(items) == 0:
                    return f"You don't have any {item_type} yet. Would you like to create one?"
                elif len(items) == 1:
                    return f"You have 1 {item_type[:-1]}."
                else:
                    return f"You have {len(items)} {item_type}."
            
            else:
                return "Operation completed successfully!"
        
        else:
            # Generate error response with helpful guidance
            error_msg = action_result.get("message", "An error occurred")
            intent = intent_analysis.get("intent", "unknown")
            
            # Provide intent-specific guidance
            if intent == "create_task":
                return f"I couldn't create the task: {error_msg}. Please try specifying the task name more clearly."
            elif intent == "list_tasks":
                return f"I couldn't retrieve your tasks: {error_msg}. Please try again in a moment."
            elif intent == "create_project":
                return f"I couldn't create the project: {error_msg}. Please try specifying the project name more clearly."
            elif intent == "list_projects":
                return f"I couldn't retrieve your projects: {error_msg}. Please try again in a moment."
            else:
                return f"Sorry, I couldn't complete that request: {error_msg}. Please try rephrasing your request."
    
    def _generate_fallback_response(
        self, 
        intent_analysis: Dict[str, Any], 
        action_result: Dict[str, Any]
    ) -> str:
        """
        Generate a simple fallback response when LLM is unavailable
        
        Args:
            intent_analysis: Intent analysis results
            action_result: Action execution results
            
        Returns:
            Simple response string
        """
        # Use enhanced fallback for better responses
        return self._generate_enhanced_fallback_response("", intent_analysis, action_result)