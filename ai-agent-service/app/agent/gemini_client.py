"""
Gemini API Client

This module provides a wrapper for the Gemini API to handle natural language
processing and AI agent capabilities with proper error handling and graceful degradation.
"""

import os
import logging
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Gemini API client with error handling and graceful degradation
    """
    
    def __init__(self):
        """Initialize Gemini client with API key from environment"""
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        self.is_configured = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                self.is_configured = True
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.is_configured = False
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables")
    
    def is_available(self) -> bool:
        """Check if Gemini API is available and configured"""
        return self.is_configured and self.model is not None
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate response using Gemini API with error handling
        
        Args:
            prompt: The input prompt for the AI
            context: Optional context information
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict containing response or error information
        """
        if not self.is_available():
            return self._fallback_response(
                "Gemini API is not available. Please check your API key configuration."
            )
        
        try:
            # Prepare the full prompt with context if provided
            full_prompt = self._prepare_prompt(prompt, context)
            
            # Configure safety settings
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                safety_settings=safety_settings
            )
            
            if response.text:
                return {
                    "success": True,
                    "response": response.text.strip(),
                    "source": "gemini",
                    "tokens_used": len(response.text.split())  # Approximate token count
                }
            else:
                logger.warning("Gemini returned empty response")
                return self._fallback_response("AI service returned an empty response")
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback_response(f"AI service temporarily unavailable: {str(e)}")
    
    def _prepare_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Prepare the full prompt with context and system instructions
        
        Args:
            prompt: User's input prompt
            context: Optional context information
            
        Returns:
            Formatted prompt string
        """
        system_prompt = """You are an AI assistant that helps with task and project management. 
You can create, update, list, and delete tasks and projects through an MCP service.

Key capabilities:
- Natural language understanding for task management requests
- Project organization and planning
- Task prioritization and status tracking
- Clear, helpful responses

Always be helpful, concise, and focused on task/project management activities."""
        
        context_str = ""
        if context:
            context_str = f"\nContext: {context}"
        
        return f"{system_prompt}\n\nUser request: {prompt}{context_str}"
    
    def _fallback_response(self, error_message: str) -> Dict[str, Any]:
        """
        Generate fallback response when Gemini API is unavailable
        
        Args:
            error_message: Error description
            
        Returns:
            Fallback response dictionary
        """
        return {
            "success": False,
            "response": f"I apologize, but the AI service is currently unavailable. {error_message}",
            "source": "fallback",
            "error": error_message
        }
    
    async def analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """
        Analyze user intent for task/project management operations
        
        Args:
            user_input: User's natural language input
            
        Returns:
            Intent analysis results
        """
        if not self.is_available():
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "action": "error",
                "error": "AI service unavailable"
            }
        
        intent_prompt = f"""
Analyze this user request for task/project management intent:
"{user_input}"

Identify:
1. Primary intent (create_task, list_tasks, update_task, delete_task, create_project, list_projects, general_query)
2. Confidence level (0.0-1.0)
3. Key entities (task names, project names, priorities, statuses, dates)
4. Required action

Respond in this exact JSON format:
{{
    "intent": "intent_name",
    "confidence": 0.9,
    "entities": {{"key": "value"}},
    "action": "action_to_take"
}}
"""
        
        try:
            response = await self.generate_response(intent_prompt)
            if response["success"]:
                # Try to parse JSON from response
                import json
                try:
                    intent_data = json.loads(response["response"])
                    return intent_data
                except json.JSONDecodeError:
                    logger.warning("Failed to parse intent analysis JSON")
                    return self._fallback_intent_analysis(user_input)
            else:
                return self._fallback_intent_analysis(user_input)
                
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return self._fallback_intent_analysis(user_input)
    
    def _fallback_intent_analysis(self, user_input: str) -> Dict[str, Any]:
        """
        Simple rule-based intent analysis fallback
        
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
                    "action": "create_project"
                }
            else:
                return {
                    "intent": "create_task",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "create_task"
                }
        elif any(word in user_lower for word in ["list", "show", "get", "view"]):
            if "project" in user_lower:
                return {
                    "intent": "list_projects",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "list_projects"
                }
            else:
                return {
                    "intent": "list_tasks",
                    "confidence": 0.7,
                    "entities": {},
                    "action": "list_tasks"
                }
        elif any(word in user_lower for word in ["update", "modify", "change", "edit"]):
            return {
                "intent": "update_task",
                "confidence": 0.6,
                "entities": {},
                "action": "update_task"
            }
        elif any(word in user_lower for word in ["delete", "remove", "cancel"]):
            return {
                "intent": "delete_task",
                "confidence": 0.6,
                "entities": {},
                "action": "delete_task"
            }
        else:
            return {
                "intent": "general_query",
                "confidence": 0.5,
                "entities": {},
                "action": "general_response"
            }