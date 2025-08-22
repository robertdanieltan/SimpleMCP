-- Test data for AI Agent MCP Service Learning Project
-- Provides sample projects and tasks for development and testing

-- Insert sample projects
INSERT INTO projects (name, description, status) VALUES
('AI Agent MCP Service Learning', 'Educational project for learning AI agent development with MCP services', 'active'),
('Task Management Demo', 'Demonstration of task management capabilities', 'active'),
('Database Integration Project', 'Learning PostgreSQL integration patterns', 'completed'),
('Future Enhancement Ideas', 'Collection of potential improvements and features', 'on_hold');

-- Insert sample tasks for the learning project
INSERT INTO tasks (project_id, title, description, status, priority, assigned_to, due_date) VALUES
-- AI Agent MCP Service Learning Project tasks
(1, 'Setup Infrastructure', 'Create Docker containers and database schema', 'completed', 'high', 'developer', '2024-01-15'),
(1, 'Implement MCP Service', 'Build FastMCP-based service with task management tools', 'in_progress', 'high', 'developer', '2024-01-20'),
(1, 'Create AI Agent Service', 'Develop FastAPI agent with Gemini integration', 'pending', 'high', 'developer', '2024-01-25'),
(1, 'Add Service Communication', 'Implement HTTP client for MCP service calls', 'pending', 'medium', 'developer', '2024-01-30'),
(1, 'Write Documentation', 'Create comprehensive setup and usage documentation', 'pending', 'medium', 'developer', '2024-02-05'),

-- Task Management Demo tasks
(2, 'Create Sample Project', 'Demonstrate project creation functionality', 'completed', 'medium', 'demo_user', '2024-01-10'),
(2, 'Add Multiple Tasks', 'Show task creation with different priorities', 'completed', 'medium', 'demo_user', '2024-01-12'),
(2, 'Update Task Status', 'Demonstrate task status transitions', 'in_progress', 'low', 'demo_user', '2024-01-18'),
(2, 'Test Task Filtering', 'Verify task filtering by status and priority', 'pending', 'low', 'demo_user', '2024-01-22'),

-- Database Integration Project tasks
(3, 'Design Database Schema', 'Create tables for projects and tasks', 'completed', 'high', 'db_admin', '2024-01-05'),
(3, 'Implement CRUD Operations', 'Build database operations for all entities', 'completed', 'high', 'db_admin', '2024-01-08'),
(3, 'Add Performance Indexes', 'Optimize database queries with proper indexing', 'completed', 'medium', 'db_admin', '2024-01-10'),
(3, 'Test Data Integrity', 'Verify foreign key constraints and data validation', 'completed', 'medium', 'db_admin', '2024-01-12'),

-- Future Enhancement Ideas tasks
(4, 'Add User Authentication', 'Implement user management and authentication', 'pending', 'medium', null, null),
(4, 'Create Web Dashboard', 'Build web interface for task management', 'pending', 'low', null, null),
(4, 'Add Email Notifications', 'Send notifications for task updates', 'pending', 'low', null, null),
(4, 'Implement Task Dependencies', 'Add support for task relationships', 'pending', 'medium', null, null);

-- Insert additional tasks to demonstrate various scenarios
INSERT INTO tasks (project_id, title, description, status, priority, assigned_to, due_date) VALUES
(1, 'Performance Testing', 'Test system performance under load', 'pending', 'medium', 'tester', '2024-02-10'),
(1, 'Security Review', 'Review security implications and best practices', 'pending', 'high', 'security_team', '2024-02-15'),
(2, 'User Experience Testing', 'Gather feedback on task management workflow', 'pending', 'medium', 'ux_designer', '2024-01-25'),
(3, 'Database Backup Strategy', 'Implement automated backup procedures', 'pending', 'high', 'db_admin', '2024-01-20');

-- Verify data insertion with some basic statistics
-- This will be visible in the PostgreSQL logs during initialization
DO $$
DECLARE
    project_count INTEGER;
    task_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO project_count FROM projects;
    SELECT COUNT(*) INTO task_count FROM tasks;
    
    RAISE NOTICE 'Test data insertion completed:';
    RAISE NOTICE '  Projects: %', project_count;
    RAISE NOTICE '  Tasks: %', task_count;
END $$;