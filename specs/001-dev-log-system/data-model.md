# Data Model Specification

**Date**: 2025年11月12日  
**Phase**: 1 - Design & Contracts

## Overview

This document defines the complete data model for PDLS, including entities, relationships, validation rules, and state transitions derived from the feature specification requirements.

## Base Model Pattern

All entities inherit from a common base model with audit fields:

```python
class BaseModel:
    id: UUID (Primary Key)
    created_at: datetime (UTC, auto-generated)
    updated_at: datetime (UTC, auto-updated)
    created_by: UUID (Foreign Key to User)
    deleted_at: Optional[datetime] (Soft delete)
```

## Core Entities

### 1. User Entity

**Purpose**: Represents team members with role-based access control

**Fields**:
- `email`: string (unique, email format validation)
- `password_hash`: string (bcrypt hashed)
- `full_name`: string (max 100 chars)
- `role`: enum (developer, pm, stakeholder, admin)
- `is_active`: boolean (default true)
- `last_login`: Optional[datetime]
- `avatar_url`: Optional[string] (MinIO presigned URL)
- `preferences`: JSON (UI settings, timezone, notifications)

**Relationships**:
- One-to-many: WorkLogs (as logger)
- Many-to-many: Projects (as team member)
- One-to-many: LeaveRequests (as requester)
- One-to-many: HandoverDocuments (as author)

**Validation Rules**:
- Email must be valid format and unique
- Role must be one of defined enum values
- Password must meet complexity requirements (8+ chars, mixed case, numbers)

### 2. Project Entity

**Purpose**: Container for tasks, team members, and reporting scope

**Fields**:
- `name`: string (max 100 chars, unique)
- `description`: text (max 1000 chars)
- `status`: enum (active, paused, completed, archived)
- `start_date`: date
- `end_date`: Optional[date]
- `github_repo_url`: Optional[string] (URL validation)
- `notion_workspace_id`: Optional[string]
- `settings`: JSON (report frequency, notification preferences)

**Relationships**:
- One-to-many: Tasks
- Many-to-many: Users (team members with join table for roles)
- One-to-many: WeeklyReports
- One-to-many: HandoverDocuments

**Validation Rules**:
- Name must be unique across active projects
- End date must be after start date if specified
- GitHub URL must be valid repository format

### 3. Task Entity

**Purpose**: Trackable work unit linked to GitHub issues with progress tracking

**Fields**:
- `title`: string (max 200 chars)
- `description`: text (max 2000 chars)
- `status`: enum (todo, in_progress, review, done, blocked)
- `priority`: enum (low, medium, high, urgent)
- `estimated_hours`: Optional[decimal] (max 999.99)
- `github_issue_number`: Optional[integer]
- `github_issue_url`: Optional[string]
- `assignee_id`: Optional[UUID] (Foreign Key to User)
- `due_date`: Optional[date]
- `tags`: JSON Array[string] (searchable labels)

**Relationships**:
- Many-to-one: Project
- Many-to-one: User (assignee)
- One-to-many: WorkLogs

**Validation Rules**:
- Title required and non-empty
- Estimated hours must be positive if specified
- GitHub issue URL must match repository format

### 4. WorkLog Entity

**Purpose**: Time-stamped entry linking user, task, duration, and description

**Fields**:
- `date`: date (work date, not created date)
- `hours`: decimal (0.25 to 24.0 hours per entry)
- `description`: text (max 1000 chars)
- `user_id`: UUID (Foreign Key to User)
- `task_id`: UUID (Foreign Key to Task)
- `project_id`: UUID (Foreign Key to Project, denormalized)
- `is_billable`: boolean (default true)
- `metadata`: JSON (additional context, tools used)

**Relationships**:
- Many-to-one: User (logger)
- Many-to-one: Task
- Many-to-one: Project

**Validation Rules**:
- Hours must be between 0.25 and 24.0
- Date cannot be future date
- Description required and non-empty
- User must be project team member

**Business Rules**:
- Maximum 24 hours per user per day across all projects
- Cannot log time on completed or archived projects

### 5. WeeklyReport Entity

**Purpose**: Automated summary of project progress and team activity

**Fields**:
- `week_start_date`: date (Monday of report week)
- `week_end_date`: date (Friday of report week)
- `project_id`: UUID (Foreign Key to Project)
- `status`: enum (generating, completed, failed)
- `total_hours`: decimal (sum of all work logs)
- `total_tasks_completed`: integer
- `team_member_count`: integer (active members)
- `content_markdown`: text (report body in Markdown)
- `content_html`: text (rendered HTML version)
- `generated_at`: datetime (completion timestamp)
- `metrics`: JSON (additional KPIs and statistics)

**Relationships**:
- Many-to-one: Project
- One-to-many: FileUploads (exported versions)

**Validation Rules**:
- Week dates must be Monday to Friday
- Cannot have duplicate reports for same project/week
- Content must be non-empty when status is completed

**Auto-generation Rules**:
- Triggered every Friday at 23:59 UTC via Celery
- Includes all work logs from Monday-Friday of current week
- Calculates team productivity metrics and task completion rates

### 6. HandoverDocument Entity

**Purpose**: Standardized knowledge transfer documentation

**Fields**:
- `title`: string (max 200 chars)
- `project_id`: UUID (Foreign Key to Project)
- `handover_type`: enum (project_leave, role_change, temporary_absence)
- `from_user_id`: UUID (Foreign Key to User)
- `to_user_id`: Optional[UUID] (Foreign Key to User)
- `effective_date`: date (when handover takes effect)
- `status`: enum (draft, pending_review, approved, completed)
- `project_summary`: text (current state overview)
- `pending_tasks`: JSON Array (task details and priorities)
- `key_contacts`: JSON Array (important stakeholders)
- `knowledge_items`: JSON Array (processes, passwords, access)
- `recommendations`: text (suggestions for successor)
- `content_markdown`: text (full document in Markdown)

**Relationships**:
- Many-to-one: Project
- Many-to-one: User (from_user)
- Many-to-one: User (to_user, optional)
- One-to-many: FileUploads (attachments)

**Validation Rules**:
- Effective date cannot be in the past
- From user must be project team member
- To user must be different from from_user

**State Transitions**:
- Draft → Pending Review (when submitted)
- Pending Review → Approved (PM/Admin approval)
- Approved → Completed (effective date reached)

### 7. LeaveRequest Entity

**Purpose**: Time-bound absence record with supporting documentation

**Fields**:
- `user_id`: UUID (Foreign Key to User)
- `leave_type`: enum (vacation, sick, personal, emergency, conference)
- `start_date`: date
- `end_date`: date
- `total_days`: integer (calculated field)
- `reason`: text (max 500 chars, optional for some types)
- `status`: enum (pending, approved, rejected, cancelled)
- `approved_by`: Optional[UUID] (Foreign Key to User)
- `approved_at`: Optional[datetime]
- `manager_notes`: Optional[text] (max 1000 chars)
- `emergency_contact`: Optional[JSON] (name, phone, relationship)

**Relationships**:
- Many-to-one: User (requester)
- Many-to-one: User (approver, optional)
- One-to-many: FileUploads (supporting documents)

**Validation Rules**:
- End date must be same or after start date
- Cannot overlap with existing approved leave for same user
- Emergency and sick leave require reason
- File attachments limited to PDF/JPG/PNG, max 10MB each

**Business Rules**:
- Auto-approval for single-day personal leave (if configured)
- Manager notification within 24 hours of submission
- Cannot cancel approved leave less than 48 hours before start

### 8. FileUpload Entity

**Purpose**: Secure document storage with MinIO integration

**Fields**:
- `filename`: string (original filename)
- `file_size`: integer (bytes)
- `mime_type`: string (validated content type)
- `minio_bucket`: string (storage bucket name)
- `minio_object_key`: string (unique object identifier)
- `upload_purpose`: enum (leave_document, handover_attachment, report_export, avatar)
- `parent_entity_type`: string (User, LeaveRequest, HandoverDocument, etc.)
- `parent_entity_id`: UUID (polymorphic reference)
- `is_public`: boolean (affects presigned URL generation)
- `virus_scan_status`: enum (pending, clean, infected, failed)
- `metadata`: JSON (exif data, document properties)

**Relationships**:
- Polymorphic: Parent entity (User, LeaveRequest, HandoverDocument, WeeklyReport)

**Validation Rules**:
- File size must not exceed 10MB
- MIME type must be in allowed list (PDF, JPG, PNG, DOCX, etc.)
- Filename must not contain path traversal characters

**Security Rules**:
- Presigned URLs expire after 24 hours (download) or 1 hour (upload)
- Virus scanning required before file is accessible
- Access control based on parent entity permissions

## Relationship Matrix

| Entity | User | Project | Task | WorkLog | WeeklyReport | HandoverDocument | LeaveRequest | FileUpload |
|--------|------|---------|------|---------|--------------|------------------|--------------|------------|
| User | - | M:M | 1:M | 1:M | - | 1:M | 1:M | 1:M |
| Project | M:M | - | 1:M | 1:M | 1:M | 1:M | - | 1:M |
| Task | M:1 | M:1 | - | 1:M | - | - | - | - |
| WorkLog | M:1 | M:1 | M:1 | - | - | - | - | - |
| WeeklyReport | - | M:1 | - | - | - | - | - | 1:M |
| HandoverDocument | M:1 | M:1 | - | - | - | - | - | 1:M |
| LeaveRequest | M:1 | - | - | - | - | - | - | 1:M |
| FileUpload | M:1* | M:1* | - | - | M:1* | M:1* | M:1* | - |

*Polymorphic relationships based on parent_entity_type/id

## Database Indexes

### Primary Indexes
- All primary keys (UUID) with B-tree index
- Foreign key columns for relationship lookups

### Composite Indexes
- `(user_id, date)` on WorkLog for user daily summaries
- `(project_id, week_start_date)` on WeeklyReport for report queries
- `(project_id, status)` on Task for project dashboards
- `(user_id, status, start_date)` on LeaveRequest for calendar views

### Partial Indexes
- `WHERE deleted_at IS NULL` on all entities for active record queries
- `WHERE status = 'pending'` on LeaveRequest for approval workflows

### Full-Text Search Indexes
- `content_markdown` on WeeklyReport for report search
- `description` on Task for task search
- `title, description` on HandoverDocument for knowledge search

## Data Migration Strategy

### Phase 1: Core Tables
1. User, Project, Task (foundation entities)
2. WorkLog (time tracking functionality)
3. Basic indexes and constraints

### Phase 2: Automation Features
1. WeeklyReport (automated reporting)
2. HandoverDocument (knowledge transfer)
3. Background job tables

### Phase 3: Enhanced Features
1. LeaveRequest (HR functionality)
2. FileUpload (document management)
3. Integration tables (GitHub, Notion sync)

### Phase 4: Optimization
1. Performance indexes
2. Audit tables
3. Analytics views

## Data Retention Policy

- **Work Logs**: Retain indefinitely for billing and historical analysis
- **Weekly Reports**: Retain for 2 years, then archive to cold storage
- **Handover Documents**: Retain for 1 year after project completion
- **Leave Requests**: Retain for 7 years for compliance purposes
- **File Uploads**: Follow parent entity retention rules
- **Audit Logs**: Retain for 3 years for security analysis

## Backup Strategy

- **Full Backup**: Daily at 2:00 AM UTC
- **Incremental Backup**: Every 6 hours
- **Point-in-Time Recovery**: 30-day retention
- **Cross-Region Replication**: Critical data replicated to secondary region
- **Backup Testing**: Monthly restore verification