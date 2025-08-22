"""
Database CRUD operations for projects and tasks.
Provides synchronous database operations with proper error handling.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from psycopg2 import DatabaseError, IntegrityError
from .connection import get_db_connection

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Handles all database CRUD operations for projects and tasks."""
    
    def __init__(self):
        self.db = get_db_connection()
    
    # Project Operations
    
    def create_project(self, name: str, description: Optional[str] = None, 
                      status: str = "active") -> Dict[str, Any]:
        """
        Create a new project.
        
        Args:
            name: Project name
            description: Optional project description
            status: Project status (default: "active")
            
        Returns:
            Dict containing the created project data
            
        Raises:
            DatabaseError: If project creation fails
        """
        try:
            def _create_project(cursor):
                cursor.execute("""
                    INSERT INTO projects (name, description, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, name, description, status, created_at, updated_at
                """, (name, description, status, datetime.now(), datetime.now()))
                
                return dict(cursor.fetchone())
            
            result = self.db.execute_transaction(_create_project)
            logger.info(f"Created project: {result['name']} (ID: {result['id']})")
            return result
            
        except IntegrityError as e:
            logger.error(f"Project creation failed - integrity error: {e}")
            raise DatabaseError(f"Project with name '{name}' may already exist")
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise DatabaseError(f"Failed to create project: {str(e)}")
    
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Dict containing project data or None if not found
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, description, status, created_at, updated_at
                    FROM projects WHERE id = %s
                """, (project_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            raise DatabaseError(f"Failed to retrieve project: {str(e)}")
    
    def list_projects(self, status: Optional[str] = None, 
                     limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List projects with optional filtering.
        
        Args:
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of project dictionaries
        """
        try:
            with self.db.get_cursor() as cursor:
                if status:
                    cursor.execute("""
                        SELECT id, name, description, status, created_at, updated_at
                        FROM projects WHERE status = %s
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (status, limit, offset))
                else:
                    cursor.execute("""
                        SELECT id, name, description, status, created_at, updated_at
                        FROM projects
                        ORDER BY created_at DESC
                        LIMIT %s OFFSET %s
                    """, (limit, offset))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise DatabaseError(f"Failed to list projects: {str(e)}")
    
    def update_project(self, project_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update a project with provided fields.
        
        Args:
            project_id: Project ID
            **kwargs: Fields to update (name, description, status)
            
        Returns:
            Dict containing updated project data or None if not found
        """
        if not kwargs:
            return self.get_project(project_id)
        
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            for field in ['name', 'description', 'status']:
                if field in kwargs:
                    update_fields.append(f"{field} = %s")
                    values.append(kwargs[field])
            
            if not update_fields:
                return self.get_project(project_id)
            
            update_fields.append("updated_at = %s")
            values.extend([datetime.now(), project_id])
            
            def _update_project(cursor):
                cursor.execute(f"""
                    UPDATE projects 
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                    RETURNING id, name, description, status, created_at, updated_at
                """, values)
                
                result = cursor.fetchone()
                return dict(result) if result else None
            
            result = self.db.execute_transaction(_update_project)
            if result:
                logger.info(f"Updated project {project_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            raise DatabaseError(f"Failed to update project: {str(e)}")
    
    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project and all associated tasks.
        
        Args:
            project_id: Project ID
            
        Returns:
            bool: True if project was deleted, False if not found
        """
        try:
            def _delete_project(cursor):
                # First delete associated tasks
                cursor.execute("DELETE FROM tasks WHERE project_id = %s", (project_id,))
                tasks_deleted = cursor.rowcount
                
                # Then delete the project
                cursor.execute("DELETE FROM projects WHERE id = %s", (project_id,))
                project_deleted = cursor.rowcount > 0
                
                if project_deleted:
                    logger.info(f"Deleted project {project_id} and {tasks_deleted} associated tasks")
                
                return project_deleted
            
            return self.db.execute_transaction(_delete_project)
            
        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            raise DatabaseError(f"Failed to delete project: {str(e)}")
    
    # Task Operations
    
    def create_task(self, title: str, project_id: Optional[int] = None,
                   description: Optional[str] = None, status: str = "pending",
                   priority: str = "medium", assigned_to: Optional[str] = None,
                   due_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Create a new task.
        
        Args:
            title: Task title
            project_id: Optional project ID
            description: Optional task description
            status: Task status (default: "pending")
            priority: Task priority (default: "medium")
            assigned_to: Optional assignee
            due_date: Optional due date
            
        Returns:
            Dict containing the created task data
        """
        try:
            def _create_task(cursor):
                cursor.execute("""
                    INSERT INTO tasks (project_id, title, description, status, 
                                     priority, assigned_to, due_date, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, project_id, title, description, status, 
                             priority, assigned_to, due_date, created_at, updated_at
                """, (project_id, title, description, status, priority, 
                     assigned_to, due_date, datetime.now(), datetime.now()))
                
                return dict(cursor.fetchone())
            
            result = self.db.execute_transaction(_create_task)
            logger.info(f"Created task: {result['title']} (ID: {result['id']})")
            return result
            
        except IntegrityError as e:
            logger.error(f"Task creation failed - integrity error: {e}")
            raise DatabaseError("Invalid project_id or constraint violation")
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise DatabaseError(f"Failed to create task: {str(e)}")
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Dict containing task data or None if not found
        """
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, project_id, title, description, status, 
                           priority, assigned_to, due_date, created_at, updated_at
                    FROM tasks WHERE id = %s
                """, (task_id,))
                
                result = cursor.fetchone()
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            raise DatabaseError(f"Failed to retrieve task: {str(e)}")
    
    def list_tasks(self, project_id: Optional[int] = None, 
                  status: Optional[str] = None, assigned_to: Optional[str] = None,
                  limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List tasks with optional filtering.
        
        Args:
            project_id: Optional project ID filter
            status: Optional status filter
            assigned_to: Optional assignee filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of task dictionaries
        """
        try:
            with self.db.get_cursor() as cursor:
                # Build dynamic WHERE clause
                where_conditions = []
                params = []
                
                if project_id is not None:
                    where_conditions.append("project_id = %s")
                    params.append(project_id)
                
                if status:
                    where_conditions.append("status = %s")
                    params.append(status)
                
                if assigned_to:
                    where_conditions.append("assigned_to = %s")
                    params.append(assigned_to)
                
                where_clause = ""
                if where_conditions:
                    where_clause = "WHERE " + " AND ".join(where_conditions)
                
                params.extend([limit, offset])
                
                cursor.execute(f"""
                    SELECT id, project_id, title, description, status, 
                           priority, assigned_to, due_date, created_at, updated_at
                    FROM tasks {where_clause}
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, params)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            raise DatabaseError(f"Failed to list tasks: {str(e)}")
    
    def update_task(self, task_id: int, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update a task with provided fields.
        
        Args:
            task_id: Task ID
            **kwargs: Fields to update
            
        Returns:
            Dict containing updated task data or None if not found
        """
        if not kwargs:
            return self.get_task(task_id)
        
        try:
            # Build dynamic update query
            update_fields = []
            values = []
            
            valid_fields = ['project_id', 'title', 'description', 'status', 
                          'priority', 'assigned_to', 'due_date']
            
            for field in valid_fields:
                if field in kwargs:
                    update_fields.append(f"{field} = %s")
                    values.append(kwargs[field])
            
            if not update_fields:
                return self.get_task(task_id)
            
            update_fields.append("updated_at = %s")
            values.extend([datetime.now(), task_id])
            
            def _update_task(cursor):
                cursor.execute(f"""
                    UPDATE tasks 
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                    RETURNING id, project_id, title, description, status, 
                             priority, assigned_to, due_date, created_at, updated_at
                """, values)
                
                result = cursor.fetchone()
                return dict(result) if result else None
            
            result = self.db.execute_transaction(_update_task)
            if result:
                logger.info(f"Updated task {task_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            raise DatabaseError(f"Failed to update task: {str(e)}")
    
    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            bool: True if task was deleted, False if not found
        """
        try:
            def _delete_task(cursor):
                cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
                deleted = cursor.rowcount > 0
                
                if deleted:
                    logger.info(f"Deleted task {task_id}")
                
                return deleted
            
            return self.db.execute_transaction(_delete_task)
            
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            raise DatabaseError(f"Failed to delete task: {str(e)}")


# Global database operations instance
db_operations = DatabaseOperations()


def get_db_operations() -> DatabaseOperations:
    """
    Get the global database operations instance.
    
    Returns:
        DatabaseOperations: Global database operations instance
    """
    return db_operations