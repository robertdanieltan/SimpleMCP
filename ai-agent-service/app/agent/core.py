"""
AI Agent Core Logic

This module contains the main agent processing logic that coordinates between
natural language understanding (via Gemini) and MCP service operations.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .gemini_client import GeminiClient
from ..mcp_client.http_client import MCPClient

logger = logging.getLogger(__name__)


class AIAgent:
    """
    Main AI Agent class that processes user requests and coordinates
    between Gemini API and MCP service operations
    """
    
    def __init__(self):
        """Initialize the AI agent with Gemini and MCP clients"""
        self.gemini_client = GeminiClient()
        self.mcp_client = MCPClient()
        self.session_context = {}
        
        logger.info("AI Agent initialized")
    
    def _check_mcp_availability(self) -> bool:
        """Check if MCP service is available"""
        try:
            health = self.mcp_client.health_check()
            return health.get("status") == "healthy"
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive agent status including all service dependencies
        
        Returns:
            Status information dictionary
        """
        return {
            "agent_status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "gemini": {
                    "available": self.gemini_client.is_available(),
                    "configured": self.gemini_client.is_configured
                },
                "mcp_service": {
                    "available": self._check_mcp_availability(),
                    "url": self.mcp_client.base_url
                }
            },
            "capabilities": [
                "natural_language_processing",
                "task_management",
                "project_management",
                "intent_analysis"
            ]
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
        try:
            logger.info(f"Processing user request: {user_input[:100]}...")
            
            # Step 1: Analyze user intent
            intent_analysis = await self.gemini_client.analyze_intent(user_input)
            logger.info(f"Intent analysis: {intent_analysis.get('intent', 'unknown')}")
            
            # Step 2: Execute appropriate action based on intent
            action_result = await self._execute_action(intent_analysis, user_input, context)
            
            # Step 3: Generate natural language response
            response = await self._generate_response(
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
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "timestamp": datetime.utcnow().isoformat()
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
        # Extract task details from user input using Gemini if available
        if self.gemini_client.is_available():
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
            gemini_response = await self.gemini_client.generate_response(extraction_prompt)
            if gemini_response["success"]:
                try:
                    import json
                    task_data = json.loads(gemini_response["response"])
                except json.JSONDecodeError:
                    # Fallback to basic extraction
                    task_data = {"title": user_input, "description": "", "priority": "medium"}
            else:
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
        # Extract project details
        if self.gemini_client.is_available():
            extraction_prompt = f"""
Extract project details from this request: "{user_input}"

Provide a JSON response with:
{{
    "name": "project name",
    "description": "project description",
    "status": "active"
}}
"""
            gemini_response = await self.gemini_client.generate_response(extraction_prompt)
            if gemini_response["success"]:
                try:
                    import json
                    project_data = json.loads(gemini_response["response"])
                except json.JSONDecodeError:
                    project_data = {"name": user_input, "description": "", "status": "active"}
            else:
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
        if self.gemini_client.is_available():
            response = await self.gemini_client.generate_response(user_input, context)
            return {
                "success": True,
                "type": "general_response",
                "message": response["response"]
            }
        else:
            return {
                "success": True,
                "type": "general_response",
                "message": "I'm here to help with task and project management. You can ask me to create tasks, list projects, or manage your work items."
            }
    
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
        if not self.gemini_client.is_available():
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
        
        try:
            gemini_response = await self.gemini_client.generate_response(response_prompt)
            if gemini_response["success"]:
                return gemini_response["response"]
            else:
                return self._generate_fallback_response(intent_analysis, action_result)
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return self._generate_fallback_response(intent_analysis, action_result)
    
    def _generate_fallback_response(
        self, 
        intent_analysis: Dict[str, Any], 
        action_result: Dict[str, Any]
    ) -> str:
        """
        Generate a simple fallback response when Gemini is unavailable
        
        Args:
            intent_analysis: Intent analysis results
            action_result: Action execution results
            
        Returns:
            Simple response string
        """
        if action_result.get("success"):
            intent = intent_analysis.get("intent", "unknown")
            if intent == "create_task":
                return "Task created successfully!"
            elif intent == "list_tasks":
                tasks = action_result.get("data", [])
                return f"Found {len(tasks)} tasks."
            elif intent == "create_project":
                return "Project created successfully!"
            elif intent == "list_projects":
                projects = action_result.get("data", [])
                return f"Found {len(projects)} projects."
            else:
                return "Operation completed successfully."
        else:
            error_msg = action_result.get("message", "An error occurred")
            return f"Sorry, I couldn't complete that request: {error_msg}"