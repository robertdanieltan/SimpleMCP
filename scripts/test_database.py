#!/usr/bin/env python3
"""
Database connection test script for the AI Agent MCP Service project.
Tests direct database connectivity and basic operations.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional
import json


class DatabaseTester:
    """Database connectivity and operations tester."""
    
    def __init__(self):
        self.connection = None
        self.connection_params = self._get_connection_params()
    
    def _get_connection_params(self) -> Dict[str, str]:
        """Get database connection parameters from environment or defaults."""
        return {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'aiagent_mcp'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }
    
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            print("🔌 Connecting to PostgreSQL database...")
            print(f"   Host: {self.connection_params['host']}:{self.connection_params['port']}")
            print(f"   Database: {self.connection_params['database']}")
            print(f"   User: {self.connection_params['user']}")
            
            self.connection = psycopg2.connect(**self.connection_params)
            print("✅ Database connection established successfully!")
            return True
            
        except psycopg2.OperationalError as e:
            print(f"❌ Failed to connect to database: {e}")
            print("\n💡 Troubleshooting tips:")
            print("   - Ensure PostgreSQL container is running: docker-compose ps")
            print("   - Check environment variables in .env file")
            print("   - Verify database credentials")
            return False
        except Exception as e:
            print(f"💥 Unexpected error connecting to database: {e}")
            return False
    
    def test_schema(self) -> bool:
        """Test database schema exists and is properly configured."""
        if not self.connection:
            return False
        
        try:
            print("\n📋 Testing database schema...")
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check if tables exist
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                
                tables = [row['table_name'] for row in cursor.fetchall()]
                expected_tables = ['projects', 'tasks']
                
                print(f"   Found tables: {tables}")
                
                missing_tables = [table for table in expected_tables if table not in tables]
                if missing_tables:
                    print(f"❌ Missing tables: {missing_tables}")
                    return False
                
                print("✅ All required tables exist!")
                
                # Check table structures
                for table in expected_tables:
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_name = %s
                        ORDER BY ordinal_position;
                    """, (table,))
                    
                    columns = cursor.fetchall()
                    print(f"   {table} columns: {len(columns)}")
                    for col in columns:
                        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                        print(f"     - {col['column_name']}: {col['data_type']} {nullable}")
                
                return True
                
        except Exception as e:
            print(f"❌ Schema test failed: {e}")
            return False
    
    def test_data_operations(self) -> bool:
        """Test basic CRUD operations on the database."""
        if not self.connection:
            return False
        
        try:
            print("\n🔧 Testing data operations...")
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Test SELECT operations
                cursor.execute("SELECT COUNT(*) as count FROM projects;")
                project_count = cursor.fetchone()['count']
                print(f"   Projects in database: {project_count}")
                
                cursor.execute("SELECT COUNT(*) as count FROM tasks;")
                task_count = cursor.fetchone()['count']
                print(f"   Tasks in database: {task_count}")
                
                # Test INSERT operation (with rollback)
                cursor.execute("""
                    INSERT INTO projects (name, description, status) 
                    VALUES ('Test Project', 'Database test project', 'active')
                    RETURNING id;
                """)
                test_project_id = cursor.fetchone()['id']
                print(f"   ✅ INSERT test successful (project ID: {test_project_id})")
                
                # Test UPDATE operation
                cursor.execute("""
                    UPDATE projects 
                    SET description = 'Updated test project' 
                    WHERE id = %s;
                """, (test_project_id,))
                print(f"   ✅ UPDATE test successful")
                
                # Test SELECT with WHERE
                cursor.execute("""
                    SELECT name, description, status 
                    FROM projects 
                    WHERE id = %s;
                """, (test_project_id,))
                project = cursor.fetchone()
                print(f"   ✅ SELECT test successful: {dict(project)}")
                
                # Test DELETE operation
                cursor.execute("DELETE FROM projects WHERE id = %s;", (test_project_id,))
                print(f"   ✅ DELETE test successful")
                
                # Rollback test changes
                self.connection.rollback()
                print("   🔄 Test changes rolled back")
                
                return True
                
        except Exception as e:
            print(f"❌ Data operations test failed: {e}")
            self.connection.rollback()
            return False
    
    def test_indexes(self) -> bool:
        """Test database indexes exist for performance."""
        if not self.connection:
            return False
        
        try:
            print("\n📊 Testing database indexes...")
            
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname;
                """)
                
                indexes = cursor.fetchall()
                print(f"   Found {len(indexes)} indexes:")
                
                for idx in indexes:
                    print(f"     - {idx['indexname']} on {idx['tablename']}")
                
                # Check for expected indexes
                expected_indexes = [
                    'idx_tasks_project_id',
                    'idx_tasks_status', 
                    'idx_projects_status'
                ]
                
                found_indexes = [idx['indexname'] for idx in indexes]
                missing_indexes = [idx for idx in expected_indexes if idx not in found_indexes]
                
                if missing_indexes:
                    print(f"⚠️  Missing recommended indexes: {missing_indexes}")
                else:
                    print("✅ All recommended indexes exist!")
                
                return True
                
        except Exception as e:
            print(f"❌ Index test failed: {e}")
            return False
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")
    
    def run_all_tests(self) -> bool:
        """Run all database tests."""
        print("🧪 Running database connectivity tests...\n")
        
        success = True
        
        # Test connection
        if not self.connect():
            return False
        
        # Test schema
        if not self.test_schema():
            success = False
        
        # Test data operations
        if not self.test_data_operations():
            success = False
        
        # Test indexes
        if not self.test_indexes():
            success = False
        
        return success


def main():
    """Main function to run database tests."""
    tester = DatabaseTester()
    
    try:
        success = tester.run_all_tests()
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 All database tests passed!")
            print("Database is properly configured and accessible.")
        else:
            print("⚠️  Some database tests failed!")
            print("Check the output above for specific issues.")
        print("=" * 50)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Database tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error during database tests: {e}")
        sys.exit(1)
    finally:
        tester.close()


if __name__ == "__main__":
    main()