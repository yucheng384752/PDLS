# Database Migration Plan

**Date**: 2025年11月12日  
**Phase**: 1 - Design & Contracts

## Overview

This document outlines the database migration strategy for PDLS implementation using Alembic with SQLAlchemy, ensuring zero-downtime deployments and data integrity throughout the development lifecycle.

## Migration Strategy

### 1. Alembic Configuration

**Environment Setup**:
```python
# alembic/env.py
from sqlalchemy import engine_from_config, pool
from pdls.core.config import settings
from pdls.models import Base

target_metadata = Base.metadata

def get_url():
    return settings.DATABASE_URL

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

### 2. Migration Phases

#### Phase 1: Foundation Tables (Week 1)
**Migration 001**: Create core user and authentication tables
```sql
-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('developer', 'pm', 'stakeholder', 'admin')),
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP WITH TIME ZONE,
    avatar_url TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_role ON users(role) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_active ON users(is_active) WHERE deleted_at IS NULL;
```

**Migration 002**: Create projects and project membership tables
```sql
-- Create projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
    start_date DATE NOT NULL,
    end_date DATE,
    github_repo_url TEXT,
    notion_workspace_id TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT check_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

-- Create project membership table (many-to-many)
CREATE TABLE project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_role VARCHAR(50) DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(project_id, user_id)
);

-- Create indexes
CREATE INDEX idx_projects_status ON projects(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_projects_dates ON projects(start_date, end_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);
```

#### Phase 2: Task Management (Week 2)
**Migration 003**: Create tasks and work logs tables
```sql
-- Create tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'blocked')),
    priority VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    estimated_hours DECIMAL(5,2) CHECK (estimated_hours > 0 AND estimated_hours <= 999.99),
    github_issue_number INTEGER,
    github_issue_url TEXT,
    assignee_id UUID REFERENCES users(id),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    due_date DATE,
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create work logs table
CREATE TABLE work_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    hours DECIMAL(4,2) NOT NULL CHECK (hours >= 0.25 AND hours <= 24.0),
    description TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    is_billable BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX idx_tasks_project_status ON tasks(project_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_github_issue ON tasks(github_issue_number) WHERE github_issue_number IS NOT NULL;
CREATE INDEX idx_work_logs_user_date ON work_logs(user_id, date) WHERE deleted_at IS NULL;
CREATE INDEX idx_work_logs_task ON work_logs(task_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_work_logs_project_date ON work_logs(project_id, date) WHERE deleted_at IS NULL;
```

#### Phase 3: Reporting System (Week 3)
**Migration 004**: Create weekly reports table
```sql
-- Create weekly reports table
CREATE TABLE weekly_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_start_date DATE NOT NULL, -- Monday
    week_end_date DATE NOT NULL,   -- Friday
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'generating' CHECK (status IN ('generating', 'completed', 'failed')),
    total_hours DECIMAL(8,2) DEFAULT 0,
    total_tasks_completed INTEGER DEFAULT 0,
    team_member_count INTEGER DEFAULT 0,
    content_markdown TEXT,
    content_html TEXT,
    generated_at TIMESTAMP WITH TIME ZONE,
    metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(project_id, week_start_date),
    CONSTRAINT check_week_dates CHECK (week_end_date = week_start_date + INTERVAL '4 days')
);

-- Create indexes
CREATE INDEX idx_weekly_reports_project_week ON weekly_reports(project_id, week_start_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_weekly_reports_status ON weekly_reports(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_weekly_reports_generated ON weekly_reports(generated_at) WHERE generated_at IS NOT NULL;
```

#### Phase 4: Knowledge Transfer (Week 4)
**Migration 005**: Create handover documents table
```sql
-- Create handover documents table
CREATE TABLE handover_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    handover_type VARCHAR(30) NOT NULL CHECK (handover_type IN ('project_leave', 'role_change', 'temporary_absence')),
    from_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id UUID REFERENCES users(id),
    effective_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_review', 'approved', 'completed')),
    project_summary TEXT,
    pending_tasks JSONB DEFAULT '[]',
    key_contacts JSONB DEFAULT '[]',
    knowledge_items JSONB DEFAULT '[]',
    recommendations TEXT,
    content_markdown TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT check_different_users CHECK (from_user_id != to_user_id),
    CONSTRAINT check_future_date CHECK (effective_date >= CURRENT_DATE)
);

-- Create indexes
CREATE INDEX idx_handovers_project_status ON handover_documents(project_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_handovers_from_user ON handover_documents(from_user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_handovers_effective_date ON handover_documents(effective_date) WHERE deleted_at IS NULL;
```

#### Phase 5: Leave Management (Week 5)
**Migration 006**: Create leave requests table
```sql
-- Create leave requests table
CREATE TABLE leave_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    leave_type VARCHAR(20) NOT NULL CHECK (leave_type IN ('vacation', 'sick', 'personal', 'emergency', 'conference')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_days INTEGER GENERATED ALWAYS AS (end_date - start_date + 1) STORED,
    reason TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    manager_notes TEXT,
    emergency_contact JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT check_leave_dates CHECK (end_date >= start_date),
    CONSTRAINT check_reason_required CHECK (
        leave_type NOT IN ('emergency', 'sick') OR reason IS NOT NULL
    )
);

-- Create indexes
CREATE INDEX idx_leave_requests_user_dates ON leave_requests(user_id, start_date, end_date) WHERE deleted_at IS NULL;
CREATE INDEX idx_leave_requests_status ON leave_requests(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_leave_requests_approval ON leave_requests(approved_by, approved_at) WHERE approved_by IS NOT NULL;

-- Create function to check overlapping leaves
CREATE OR REPLACE FUNCTION check_leave_overlap()
RETURNS TRIGGER AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM leave_requests 
        WHERE user_id = NEW.user_id 
        AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid)
        AND status = 'approved'
        AND deleted_at IS NULL
        AND (start_date, end_date) OVERLAPS (NEW.start_date, NEW.end_date)
    ) THEN
        RAISE EXCEPTION 'Leave request overlaps with existing approved leave';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for overlap checking
CREATE TRIGGER trigger_check_leave_overlap
    BEFORE INSERT OR UPDATE ON leave_requests
    FOR EACH ROW
    EXECUTE FUNCTION check_leave_overlap();
```

#### Phase 6: File Management (Week 6)
**Migration 007**: Create file uploads table
```sql
-- Create file uploads table
CREATE TABLE file_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL CHECK (file_size > 0 AND file_size <= 10485760), -- 10MB limit
    mime_type VARCHAR(100) NOT NULL,
    minio_bucket VARCHAR(100) NOT NULL,
    minio_object_key VARCHAR(500) NOT NULL UNIQUE,
    upload_purpose VARCHAR(30) NOT NULL CHECK (upload_purpose IN ('leave_document', 'handover_attachment', 'report_export', 'avatar')),
    parent_entity_type VARCHAR(50),
    parent_entity_id UUID,
    is_public BOOLEAN DEFAULT false,
    virus_scan_status VARCHAR(20) DEFAULT 'pending' CHECK (virus_scan_status IN ('pending', 'clean', 'infected', 'failed')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(id),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes
CREATE INDEX idx_file_uploads_parent ON file_uploads(parent_entity_type, parent_entity_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_file_uploads_purpose ON file_uploads(upload_purpose) WHERE deleted_at IS NULL;
CREATE INDEX idx_file_uploads_scan_status ON file_uploads(virus_scan_status);
CREATE INDEX idx_file_uploads_minio ON file_uploads(minio_bucket, minio_object_key);
```

#### Phase 7: Integration Tables (Week 7)
**Migration 008**: Create integration tracking tables
```sql
-- Create integration sync logs
CREATE TABLE integration_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integration_type VARCHAR(20) NOT NULL CHECK (integration_type IN ('github', 'notion', 'smtp')),
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    sync_action VARCHAR(20) NOT NULL CHECK (sync_action IN ('create', 'update', 'delete', 'export')),
    external_id VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed', 'skipped')),
    error_message TEXT,
    request_payload JSONB,
    response_payload JSONB,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_integration_sync_type_status ON integration_sync_logs(integration_type, status);
CREATE INDEX idx_integration_sync_entity ON integration_sync_logs(entity_type, entity_id);
CREATE INDEX idx_integration_sync_retry ON integration_sync_logs(next_retry_at) WHERE next_retry_at IS NOT NULL;
CREATE INDEX idx_integration_sync_external ON integration_sync_logs(integration_type, external_id) WHERE external_id IS NOT NULL;
```

### 3. Data Validation Rules

#### Constraint Functions
```sql
-- Function to validate email format
CREATE OR REPLACE FUNCTION validate_email(email TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to validate GitHub URL format
CREATE OR REPLACE FUNCTION validate_github_url(url TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN url IS NULL OR url ~* '^https://github\.com/[^/]+/[^/]+/?$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Add validation constraints
ALTER TABLE users ADD CONSTRAINT check_email_format 
CHECK (validate_email(email));

ALTER TABLE projects ADD CONSTRAINT check_github_url_format 
CHECK (validate_github_url(github_repo_url));
```

#### Business Rule Constraints
```sql
-- Function to check daily work log limits
CREATE OR REPLACE FUNCTION check_daily_work_limit()
RETURNS TRIGGER AS $$
DECLARE
    daily_total DECIMAL(5,2);
BEGIN
    SELECT COALESCE(SUM(hours), 0) INTO daily_total
    FROM work_logs 
    WHERE user_id = NEW.user_id 
    AND date = NEW.date 
    AND deleted_at IS NULL
    AND id != COALESCE(NEW.id, '00000000-0000-0000-0000-000000000000'::uuid);
    
    IF (daily_total + NEW.hours) > 24.0 THEN
        RAISE EXCEPTION 'Total daily work hours cannot exceed 24 hours. Current: %, Attempted: %', 
            daily_total, NEW.hours;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for work log validation
CREATE TRIGGER trigger_check_daily_work_limit
    BEFORE INSERT OR UPDATE ON work_logs
    FOR EACH ROW
    EXECUTE FUNCTION check_daily_work_limit();
```

### 4. Performance Optimization

#### Partitioning Strategy
```sql
-- Partition work_logs by date for better query performance
CREATE TABLE work_logs_partitioned (
    LIKE work_logs INCLUDING ALL
) PARTITION BY RANGE (date);

-- Create monthly partitions for current and future months
CREATE TABLE work_logs_2025_01 PARTITION OF work_logs_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE work_logs_2025_02 PARTITION OF work_logs_partitioned
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- Function to automatically create partitions
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name TEXT, start_date DATE)
RETURNS VOID AS $$
DECLARE
    partition_name TEXT;
    end_date DATE;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + INTERVAL '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I
                   FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

#### Materialized Views for Reporting
```sql
-- Materialized view for project statistics
CREATE MATERIALIZED VIEW project_stats AS
SELECT 
    p.id,
    p.name,
    p.status,
    COUNT(DISTINCT pm.user_id) as team_size,
    COUNT(DISTINCT t.id) as total_tasks,
    COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
    COALESCE(SUM(wl.hours), 0) as total_logged_hours,
    MAX(wl.date) as last_activity_date
FROM projects p
LEFT JOIN project_members pm ON p.id = pm.project_id
LEFT JOIN tasks t ON p.id = t.project_id AND t.deleted_at IS NULL
LEFT JOIN work_logs wl ON p.id = wl.project_id AND wl.deleted_at IS NULL
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name, p.status;

-- Create unique index for concurrent refresh
CREATE UNIQUE INDEX idx_project_stats_id ON project_stats(id);

-- Function to refresh project stats
CREATE OR REPLACE FUNCTION refresh_project_stats()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY project_stats;
END;
$$ LANGUAGE plpgsql;
```

### 5. Migration Rollback Strategy

#### Rollback Scripts
```sql
-- Each migration includes corresponding rollback
-- Migration 001 Rollback
DROP TABLE IF EXISTS users CASCADE;

-- Migration 002 Rollback  
DROP TABLE IF EXISTS project_members CASCADE;
DROP TABLE IF EXISTS projects CASCADE;

-- Migration 003 Rollback
DROP TABLE IF EXISTS work_logs CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP FUNCTION IF EXISTS check_daily_work_limit() CASCADE;

-- Migration 004 Rollback
DROP TABLE IF EXISTS weekly_reports CASCADE;

-- Migration 005 Rollback
DROP TABLE IF EXISTS handover_documents CASCADE;

-- Migration 006 Rollback
DROP TABLE IF EXISTS leave_requests CASCADE;
DROP FUNCTION IF EXISTS check_leave_overlap() CASCADE;

-- Migration 007 Rollback
DROP TABLE IF EXISTS file_uploads CASCADE;

-- Migration 008 Rollback
DROP TABLE IF EXISTS integration_sync_logs CASCADE;
```

### 6. Data Seeding Strategy

#### Initial Data Setup
```sql
-- Create admin user (to be run after migration 001)
INSERT INTO users (id, email, password_hash, full_name, role, created_by) VALUES 
('00000000-0000-0000-0000-000000000001', 'admin@pdls.local', '$2b$12$...', 'System Administrator', 'admin', '00000000-0000-0000-0000-000000000001');

-- Create sample project (to be run after migration 002)
INSERT INTO projects (id, name, description, start_date, created_by) VALUES
('00000000-0000-0000-0000-000000000002', 'PDLS Development', 'Project Development Log System Implementation', CURRENT_DATE, '00000000-0000-0000-0000-000000000001');
```

### 7. Backup and Recovery

#### Pre-Migration Backup
```bash
# Create full backup before each migration
pg_dump -h localhost -U pdls_user -d pdls_db -F c -b -v -f "backup_pre_migration_$(date +%Y%m%d_%H%M%S).backup"

# Create schema-only backup for structure verification
pg_dump -h localhost -U pdls_user -d pdls_db -s -f "schema_pre_migration_$(date +%Y%m%d_%H%M%S).sql"
```

#### Point-in-Time Recovery Setup
```bash
# Enable WAL archiving in postgresql.conf
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
wal_level = replica
max_wal_senders = 3
```

### 8. Migration Testing

#### Test Environment Setup
```python
# conftest.py for pytest
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

@pytest.fixture(scope="session")
def test_db():
    # Create test database
    engine = create_engine("postgresql://test_user:test_pass@localhost/pdls_test")
    
    # Run migrations
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    command.upgrade(alembic_cfg, "head")
    
    yield engine
    
    # Cleanup
    engine.dispose()
```

#### Migration Validation Tests
```python
def test_migration_001_users_table(test_db):
    """Test users table creation and constraints"""
    with test_db.connect() as conn:
        # Test table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            )
        """))
        assert result.scalar() == True
        
        # Test constraints
        result = conn.execute(text("""
            SELECT constraint_name FROM information_schema.table_constraints 
            WHERE table_name = 'users' AND constraint_type = 'CHECK'
        """))
        constraints = [row[0] for row in result]
        assert any('role' in constraint for constraint in constraints)
```

### 9. Performance Monitoring

#### Migration Performance Tracking
```sql
-- Create migration performance log
CREATE TABLE migration_performance (
    migration_name VARCHAR(100) PRIMARY KEY,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    rows_affected BIGINT,
    success BOOLEAN DEFAULT false,
    error_message TEXT
);

-- Function to log migration performance
CREATE OR REPLACE FUNCTION log_migration_start(migration_name TEXT)
RETURNS VOID AS $$
BEGIN
    INSERT INTO migration_performance (migration_name, start_time)
    VALUES (migration_name, CURRENT_TIMESTAMP)
    ON CONFLICT (migration_name) DO UPDATE SET
        start_time = CURRENT_TIMESTAMP,
        end_time = NULL,
        success = false;
END;
$$ LANGUAGE plpgsql;
```

### 10. Deployment Checklist

#### Pre-Migration Checklist
- [ ] Full database backup completed
- [ ] Migration scripts reviewed and approved
- [ ] Test environment migration successful
- [ ] Performance impact assessed
- [ ] Rollback plan prepared and tested

#### Post-Migration Checklist  
- [ ] All constraints and indexes created successfully
- [ ] Data integrity validation passed
- [ ] Application connectivity verified
- [ ] Performance benchmarks within acceptable range
- [ ] Monitoring alerts configured

#### Emergency Procedures
1. **Migration Failure**: Execute immediate rollback using prepared scripts
2. **Performance Degradation**: Activate read replicas and investigate slow queries
3. **Data Corruption**: Restore from pre-migration backup and re-run migration with fixes
4. **Application Errors**: Enable maintenance mode and rollback to previous application version

This comprehensive migration plan ensures systematic, safe, and reversible database schema evolution throughout the PDLS development lifecycle.