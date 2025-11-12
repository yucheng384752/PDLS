# Research & Technical Decisions

**Date**: 2025年11月12日  
**Phase**: 0 - Research & Analysis

## Overview

This document consolidates research findings and technical decisions for PDLS implementation, resolving all technical unknowns and establishing best practices for the chosen technology stack.

## Key Technical Decisions

### 1. Backend Framework: FastAPI

**Decision**: FastAPI with SQLAlchemy ORM and Alembic migrations

**Rationale**: 
- Automatic OpenAPI documentation generation aligns with contract-first development
- Built-in async support for concurrent user handling
- Type hints improve code quality and IDE support
- SQLAlchemy provides robust ORM with relationship management
- Alembic offers version-controlled database migrations

**Alternatives considered**:
- Django REST: More heavyweight, less async-optimized
- Flask: Requires more boilerplate for modern features
- Express.js: Would require Node.js stack consistency

### 2. Frontend Framework: React + Vite + PrimeReact

**Decision**: Vite build tool with React 18, TypeScript, and PrimeReact component library

**Rationale**:
- Vite provides fast development builds and hot reloading
- PrimeReact offers comprehensive UI components (DataTable, Calendar, FileUpload)
- TypeScript ensures type safety across frontend-backend boundary
- React 18 concurrent features support responsive UI during report generation

**Alternatives considered**:
- Next.js: Overkill for SPA without SSR requirements
- Vue.js: Less ecosystem support for complex data tables
- Angular: More complex setup for small team development

### 3. Authentication & Authorization: JWT + RBAC

**Decision**: JWT tokens with Role-Based Access Control using FastAPI dependencies

**Rationale**:
- Stateless authentication scales horizontally
- RBAC provides fine-grained permission control
- JWT payload can include role information for client-side routing
- FastAPI dependency injection simplifies route protection

**Implementation pattern**:
```python
@router.get("/admin-only")
async def admin_endpoint(user: User = Depends(require_role("admin"))):
    pass
```

### 4. File Storage: MinIO with Presigned URLs

**Decision**: MinIO S3-compatible storage with presigned URL generation

**Rationale**:
- S3-compatible API provides migration path to AWS S3
- Presigned URLs offload file transfer from application server
- Built-in security with time-limited access
- Self-hosted option maintains data sovereignty

**Security pattern**:
- 24-hour presigned URL expiry for downloads
- 1-hour presigned URL expiry for uploads
- File type validation before presigned URL generation

### 5. Task Scheduling: Celery with Redis

**Decision**: Celery task queue with Redis broker for automated reports

**Rationale**:
- Reliable task scheduling for Friday 23:59 report generation
- Retry mechanisms for failed integrations (GitHub, Notion)
- Monitoring and logging capabilities
- Horizontal scaling for background processing

**Cron schedule**: `0 23 * * 5` (Every Friday at 23:59 UTC)

### 6. Database Design Patterns

**Decision**: SQLAlchemy with relationship-based design and soft deletes

**Key patterns**:
- Audit fields (`created_at`, `updated_at`, `created_by`) on all entities
- Soft delete with `deleted_at` timestamp
- Foreign key relationships with cascading rules
- JSON fields for flexible metadata storage

**Example model structure**:
```python
class BaseModel:
    id: UUID = Field(primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
```

### 7. API Design Standards

**Decision**: RESTful API with OpenAPI 3.0 specification

**Conventions**:
- Resource-based URLs (`/api/v1/worklogs/`)
- HTTP status codes for response semantics
- Consistent error response format
- Pagination for list endpoints
- Filtering and sorting query parameters

**Response envelope pattern**:
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150
  },
  "meta": {
    "generated_at": "2025-11-12T23:59:00Z"
  }
}
```

### 8. Integration Architecture

**Decision**: Plugin-based integration system with async processing

**Pattern**: 
- Abstract `IntegrationService` base class
- Concrete implementations for GitHub, Notion, SMTP
- Event-driven updates using database triggers
- Retry policies with exponential backoff

**Error handling**:
- Circuit breaker pattern for external API failures
- Graceful degradation when integrations unavailable
- User notification system for integration status

### 9. Testing Strategy

**Decision**: Multi-layer testing with contract verification

**Levels**:
- Unit tests: Service logic and model validation
- Integration tests: Database operations and API endpoints
- Contract tests: OpenAPI specification compliance
- E2E tests: Critical user workflows with Playwright

**Coverage targets**:
- Unit tests: 90% code coverage
- Integration tests: All API endpoints
- E2E tests: Core user journeys (P1 priority scenarios)

### 10. Developer Mode Implementation

**Decision**: Feature flag-based developer interface with role simulation

**Implementation**:
- Separate router with `developer` role requirement
- Mock data generators for testing scenarios
- API proxy for toggling between mock/real backends
- User role impersonation with audit logging

**Security considerations**:
- Developer mode disabled in production environment
- Audit trail for all developer actions
- Separate database schema for mock data

## Performance Optimizations

### Database Indexing Strategy
- Composite indexes on frequently queried combinations
- Partial indexes for soft-deleted records
- Full-text search indexes for report content

### Caching Strategy
- Redis caching for user sessions and permissions
- Application-level caching for static reference data
- Browser caching for static assets with versioning

### File Upload Optimization
- Chunked upload for large files (>1MB)
- Client-side file validation before upload
- Asynchronous file processing for virus scanning

## Security Considerations

### Data Protection
- Database encryption at rest
- HTTPS enforcement for all communications
- Input validation and SQL injection prevention
- CORS configuration for frontend-backend communication

### Access Control
- JWT token rotation strategy
- Session timeout enforcement
- Role-based menu and feature access
- API rate limiting by user role

### Audit Trail
- Comprehensive logging for all user actions
- Immutable audit log storage
- Regular audit log analysis and reporting
- Compliance with data retention policies

## Deployment Architecture

### Environment Strategy
- Development: Local Docker containers
- Staging: Cloud-hosted with production-like data
- Production: High-availability deployment with backups

### CI/CD Pipeline
- Automated testing on pull requests
- Database migration validation
- Security scanning for dependencies
- Blue-green deployment for zero-downtime updates

## Integration Specifications

### GitHub Integration
- OAuth2 authentication for user repositories
- Webhook endpoints for real-time issue updates
- Rate limiting compliance with GitHub API limits
- Selective repository access with user consent

### Notion Integration
- API key-based authentication
- Page creation with structured content
- Template-based document formatting
- Error handling for Notion API limitations

### SMTP Configuration
- Support for multiple email providers
- Template-based email notifications
- Queue management for bulk notifications
- Bounce handling and retry logic

## Conclusion

All technical decisions prioritize maintainability, security, and scalability while supporting the core PDLS requirements. The chosen architecture enables independent frontend-backend development, reliable background processing, and extensible integration capabilities.