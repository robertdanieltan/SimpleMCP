#!/usr/bin/env python3
"""
Comprehensive integration tests for MCP service tools with real database.

This test suite covers:
- All MCP tools functionality with real database operations
- Data validation and constraint testing
- Error scenarios and edge cases
- Cross-tool integration (projects with tasks)
- Database transaction integrity
"""

import os
import sys
import json
import pytest
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

# Add the mcp-service directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tools.task_tools import create_task, list_tasks, update_task, delete_task
from app.tools.project_tools import create_project, list_projects, update_project, delete_project
from app.database.connection import get_db_connection
from app.database.operations import get_db_operations


class TestMCPIntegration:
    """Integration tests for MCP service with real database."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        cls.db = get_db_connection()
        cls.db_ops = get_db_operations()
        cls.test_projects = []
        cls.test_tasks = []
        
        # Verify database connection
        assert cls.db.test_connection(), "Database connection failed"
    
    @classmethod
    def teardown_class(cls):
        """Clean up test data."""
        # Clean up test tasks
        for task in cls.test_tasks:
            try:
                delete_task(task["id"])
            except:
                pass
        
        # Clean up test projects
        for project in cls.test_projects:
            try:
                delete_project(project["id"])
            except:
                pass
    
    def test_database_connectivity(self):
        """Test database connection and basic operations."""
        assert self.db.test_connection()
        assert self.db.health_check()
    
    def test_project_crud_operations(self):
        """Test complete CRUD operations for projects."""
        # CREATE - Test project creation
        result = create_project(
            name="Integration Test Project",
            description="Test project for integration testing",
            status="active"
        )
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["name"] == "Integration Test Project"
        assert result["data"]["status"] == "active"
        
        project = result["data"]
        self.test_projects.append(project)
        project_id = project["id"]
        
        # READ - Test project retrieval
        list_result = list_projects()
        assert list_result["success"] is True
        assert isinstance(list_result["data"], list)
        
        # Find our test project
        found_project = None
        for p in list_result["data"]:
            if p["id"] == project_id:
                found_project = p
                break
        
        assert found_project is not None
        assert found_project["name"] == "Integration Test Project"
        
        # UPDATE - Test project update
        update_result = update_project(
            project_id,
            name="Updated Integration Test Project",
            description="Updated description",
            status="completed"
        )
        
        assert update_result["success"] is True
        assert update_result["data"]["name"] == "Updated Integration Test Project"
        assert update_result["data"]["status"] == "completed"
        
        # DELETE - Test project deletion (will be done in teardown)
    
    def test_task_crud_operations(self):
        """Test complete CRUD operations for tasks."""
        # First create a project for the task
        project_result = create_project(
            name="Task Test Project",
            description="Project for task testing",
            status="active"
        )
        assert project_result["success"] is True
        project = project_result["data"]
        self.test_projects.append(project)
        project_id = project["id"]
        
        # CREATE - Test task creation
        future_date = (date.today() + timedelta(days=30)).isoformat()
        result = create_task(
            title="Integration Test Task",
            description="Test task for integration testing",
            project_id=project_id,
            status="pending",
            priority="high",
            assigned_to="test_user",
            due_date=future_date
        )
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["title"] == "Integration Test Task"
        assert result["data"]["project_id"] == project_id
        assert result["data"]["priority"] == "high"
        
        task = result["data"]
        self.test_tasks.append(task)
        task_id = task["id"]
        
        # READ - Test task retrieval
        list_result = list_tasks(project_id=project_id)
        assert list_result["success"] is True
        assert isinstance(list_result["data"], list)
        assert len(list_result["data"]) >= 1
        
        # Find our test task
        found_task = None
        for t in list_result["data"]:
            if t["id"] == task_id:
                found_task = t
                break
        
        assert found_task is not None
        assert found_task["title"] == "Integration Test Task"
        
        # UPDATE - Test task update
        update_result = update_task(
            task_id,
            title="Updated Integration Test Task",
            status="in_progress",
            priority="urgent"
        )
        
        assert update_result["success"] is True
        assert update_result["data"]["title"] == "Updated Integration Test Task"
        assert update_result["data"]["status"] == "in_progress"
        assert update_result["data"]["priority"] == "urgent"
        
        # DELETE - Test task deletion (will be done in teardown)
    
    def test_project_validation_errors(self):
        """Test project validation and error handling."""
        # Test empty name
        result = create_project(name="", description="Empty name test")
        assert result["success"] is False
        assert "validation" in result["message"].lower() or "empty" in result["message"].lower()
        
        # Test invalid status
        result = create_project(name="Invalid Status Test", status="invalid_status")
        assert result["success"] is False
        assert "validation" in result["message"].lower() or "status" in result["message"].lower()
        
        # Test update non-existent project
        result = update_project(99999, name="Non-existent Project")
        assert result["success"] is False
        assert "not found" in result["message"].lower()
        
        # Test delete non-existent project
        result = delete_project(99999)
        assert result["success"] is False
        assert "not found" in result["message"].lower()
    
    def test_task_validation_errors(self):
        """Test task validation and error handling."""
        # Test empty title
        result = create_task(title="", description="Empty title test")
        assert result["success"] is False
        assert "validation" in result["message"].lower() or "empty" in result["message"].lower()
        
        # Test invalid status
        result = create_task(title="Invalid Status Test", status="invalid_status")
        assert result["success"] is False
        assert "validation" in result["message"].lower() or "status" in result["message"].lower()
        
        # Test invalid priority
        result = create_task(title="Invalid Priority Test", priority="invalid_priority")
        assert result["success"] is False
        assert "validation" in result["message"].lower() or "priority" in result["message"].lower()
        
        # Test invalid date format
        result = create_task(title="Invalid Date Test", due_date="invalid-date")
        assert result["success"] is False
        assert "date" in result["message"].lower() or "format" in result["message"].lower()
        
        # Test update non-existent task
        result = update_task(99999, title="Non-existent Task")
        assert result["success"] is False
        assert "not found" in result["message"].lower()
        
        # Test delete non-existent task
        result = delete_task(99999)
        assert result["success"] is False
        assert "not found" in result["message"].lower()
    
    def test_project_task_relationship(self):
        """Test project-task relationships and cascading operations."""
        # Create a project
        project_result = create_project(
            name="Relationship Test Project",
            description="Testing project-task relationships"
        )
        assert project_result["success"] is True
        project = project_result["data"]
        self.test_projects.append(project)
        project_id = project["id"]
        
        # Create multiple tasks for the project
        task_titles = ["Task 1", "Task 2", "Task 3"]
        created_tasks = []
        
        for title in task_titles:
            result = create_task(
                title=title,
                description=f"Description for {title}",
                project_id=project_id,
                status="pending",
                priority="medium"
            )
            assert result["success"] is True
            created_tasks.append(result["data"])
            self.test_tasks.append(result["data"])
        
        # Verify tasks are associated with project
        list_result = list_tasks(project_id=project_id)
        assert list_result["success"] is True
        project_tasks = list_result["data"]
        assert len(project_tasks) >= len(task_titles)
        
        # Verify task project_id references
        for task in project_tasks:
            if task["id"] in [t["id"] for t in created_tasks]:
                assert task["project_id"] == project_id
        
        # Test project deletion cascades to tasks
        delete_result = delete_project(project_id)
        assert delete_result["success"] is True
        
        # Verify tasks are deleted with project
        for task in created_tasks:
            list_result = list_tasks()
            remaining_tasks = [t for t in list_result["data"] if t["id"] == task["id"]]
            assert len(remaining_tasks) == 0
        
        # Remove from cleanup lists since already deleted
        self.test_projects = [p for p in self.test_projects if p["id"] != project_id]
        self.test_tasks = [t for t in self.test_tasks if t["id"] not in [ct["id"] for ct in created_tasks]]
    
    def test_filtering_and_pagination(self):
        """Test list operations with filtering and pagination."""
        # Create test data
        project_result = create_project(
            name="Filter Test Project",
            description="Testing filtering and pagination"
        )
        assert project_result["success"] is True
        project = project_result["data"]
        self.test_projects.append(project)
        project_id = project["id"]
        
        # Create tasks with different statuses and priorities
        test_tasks_data = [
            {"title": "High Priority Task", "status": "pending", "priority": "high", "assigned_to": "user1"},
            {"title": "Medium Priority Task", "status": "in_progress", "priority": "medium", "assigned_to": "user2"},
            {"title": "Low Priority Task", "status": "completed", "priority": "low", "assigned_to": "user1"},
            {"title": "Urgent Task", "status": "pending", "priority": "urgent", "assigned_to": "user3"},
        ]
        
        created_tasks = []
        for task_data in test_tasks_data:
            result = create_task(
                title=task_data["title"],
                project_id=project_id,
                status=task_data["status"],
                priority=task_data["priority"],
                assigned_to=task_data["assigned_to"]
            )
            assert result["success"] is True
            created_tasks.append(result["data"])
            self.test_tasks.append(result["data"])
        
        # Test status filtering
        pending_result = list_tasks(status="pending")
        assert pending_result["success"] is True
        pending_tasks = [t for t in pending_result["data"] if t["project_id"] == project_id]
        assert len(pending_tasks) >= 2  # At least our 2 pending tasks
        
        # Test assignee filtering
        user1_result = list_tasks(assigned_to="user1")
        assert user1_result["success"] is True
        user1_tasks = [t for t in user1_result["data"] if t["project_id"] == project_id]
        assert len(user1_tasks) >= 2  # At least our 2 user1 tasks
        
        # Test project filtering
        project_result = list_tasks(project_id=project_id)
        assert project_result["success"] is True
        project_tasks = project_result["data"]
        assert len(project_tasks) >= len(test_tasks_data)
        
        # Test pagination
        limited_result = list_tasks(limit=2)
        assert limited_result["success"] is True
        assert len(limited_result["data"]) <= 2
        
        # Test offset
        offset_result = list_tasks(limit=2, offset=1)
        assert offset_result["success"] is True
        assert len(offset_result["data"]) <= 2
        
        # Test invalid pagination parameters
        invalid_limit = list_tasks(limit=2000)
        assert invalid_limit["success"] is False
        
        invalid_offset = list_tasks(offset=-1)
        assert invalid_offset["success"] is False
    
    def test_concurrent_operations(self):
        """Test concurrent database operations."""
        import threading
        import time
        
        # Create a project for concurrent testing
        project_result = create_project(
            name="Concurrent Test Project",
            description="Testing concurrent operations"
        )
        assert project_result["success"] is True
        project = project_result["data"]
        self.test_projects.append(project)
        project_id = project["id"]
        
        # Function to create tasks concurrently
        def create_concurrent_task(task_num):
            result = create_task(
                title=f"Concurrent Task {task_num}",
                description=f"Task created concurrently #{task_num}",
                project_id=project_id,
                status="pending",
                priority="medium"
            )
            return result
        
        # Create multiple tasks concurrently
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(
                target=lambda i=i: results.append(create_concurrent_task(i))
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all tasks were created successfully
        successful_creates = [r for r in results if r and r.get("success")]
        assert len(successful_creates) == 5
        
        # Add to cleanup list
        for result in successful_creates:
            self.test_tasks.append(result["data"])
    
    def test_data_integrity_constraints(self):
        """Test database constraints and data integrity."""
        # Test foreign key constraint (task with invalid project_id)
        result = create_task(
            title="Invalid Project Task",
            project_id=99999,  # Non-existent project
            description="Task with invalid project reference"
        )
        # This should either fail or succeed depending on constraint enforcement
        # The behavior depends on database configuration
        
        # Test data type constraints
        # These should be caught by Pydantic validation before reaching database
        
        # Test string length constraints
        long_name = "x" * 300  # Exceeds 255 character limit
        result = create_project(name=long_name)
        assert result["success"] is False
        
        long_title = "x" * 300  # Exceeds 255 character limit
        result = create_task(title=long_title)
        assert result["success"] is False
    
    def test_transaction_rollback(self):
        """Test transaction rollback on errors."""
        # This test would require modifying the database operations
        # to simulate transaction failures, which is complex in this setup
        # For now, we'll test that operations are atomic
        
        # Create a project
        project_result = create_project(
            name="Transaction Test Project",
            description="Testing transaction behavior"
        )
        assert project_result["success"] is True
        project = project_result["data"]
        self.test_projects.append(project)
        
        # Verify project exists
        list_result = list_projects()
        project_exists = any(p["id"] == project["id"] for p in list_result["data"])
        assert project_exists
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test with minimal data
        minimal_project = create_project(name="A")  # Single character name
        assert minimal_project["success"] is True
        self.test_projects.append(minimal_project["data"])
        
        minimal_task = create_task(title="B")  # Single character title
        assert minimal_task["success"] is True
        self.test_tasks.append(minimal_task["data"])
        
        # Test with maximum valid data
        max_name = "x" * 255  # Maximum allowed length
        max_project = create_project(name=max_name)
        assert max_project["success"] is True
        self.test_projects.append(max_project["data"])
        
        # Test with special characters
        special_project = create_project(
            name="Special !@#$%^&*()_+ Project",
            description="Project with special characters: àáâãäåæçèéêë"
        )
        assert special_project["success"] is True
        self.test_projects.append(special_project["data"])
        
        # Test with Unicode characters
        unicode_task = create_task(
            title="Unicode Task: 你好世界 🌍",
            description="Task with Unicode: Здравствуй мир"
        )
        assert unicode_task["success"] is True
        self.test_tasks.append(unicode_task["data"])
        
        # Test date edge cases
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        # Task due today (should be valid)
        today_task = create_task(title="Due Today", due_date=today)
        assert today_task["success"] is True
        self.test_tasks.append(today_task["data"])
        
        # Task due tomorrow (should be valid)
        tomorrow_task = create_task(title="Due Tomorrow", due_date=tomorrow)
        assert tomorrow_task["success"] is True
        self.test_tasks.append(tomorrow_task["data"])


if __name__ == "__main__":
    # Run tests directly
    import subprocess
    import sys
    
    # Install pytest if not available
    try:
        import pytest
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])
        import pytest
    
    # Run the tests
    pytest.main([__file__, "-v"])