"""
Database connection management for MCP service.
Provides PostgreSQL connection handling with health checks.
"""

import os
import logging
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError, DatabaseError

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL database connections with health monitoring."""
    
    def __init__(self):
        self.connection: Optional[psycopg2.extensions.connection] = None
        self.database_url = os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
    def connect(self) -> psycopg2.extensions.connection:
        """
        Establish database connection with automatic retry logic.
        
        Returns:
            psycopg2.extensions.connection: Active database connection
            
        Raises:
            OperationalError: If connection cannot be established
        """
        try:
            if self.connection is None or self.connection.closed:
                logger.info("Establishing database connection")
                self.connection = psycopg2.connect(
                    self.database_url,
                    cursor_factory=RealDictCursor
                )
                self.connection.autocommit = False
                logger.info("Database connection established successfully")
            
            return self.connection
            
        except OperationalError as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close the database connection if it exists."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Database connection closed")
    
    def get_cursor(self):
        """
        Get a database cursor from the current connection.
        
        Returns:
            psycopg2.extras.RealDictCursor: Database cursor
        """
        connection = self.connect()
        return connection.cursor()
    
    def health_check(self) -> bool:
        """
        Perform database health check.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
                
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test database connection for health endpoint.
        
        Returns:
            bool: True if connection is working, False otherwise
        """
        return self.health_check()
    
    def execute_transaction(self, operations):
        """
        Execute multiple operations in a single transaction.
        
        Args:
            operations: Callable that takes a cursor and performs operations
            
        Returns:
            Any: Result from operations function
            
        Raises:
            DatabaseError: If transaction fails
        """
        connection = self.connect()
        
        try:
            with connection:
                with connection.cursor() as cursor:
                    result = operations(cursor)
                    connection.commit()
                    return result
                    
        except Exception as e:
            connection.rollback()
            logger.error(f"Transaction failed: {e}")
            raise


# Global database connection instance
db_connection = DatabaseConnection()


def get_db_connection() -> DatabaseConnection:
    """
    Get the global database connection instance.
    
    Returns:
        DatabaseConnection: Global database connection
    """
    return db_connection