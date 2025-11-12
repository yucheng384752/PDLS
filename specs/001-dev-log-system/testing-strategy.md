# Testing Strategy

**Date**: 2025年11月12日  
**Phase**: 1 - Design & Contracts

## Overview

This document defines the comprehensive testing strategy for PDLS, covering unit, integration, contract, and end-to-end testing approaches to ensure system reliability, security, and user experience quality.

## Testing Pyramid

```
    E2E Tests (10%)
   ┌─────────────────┐
  │  Critical Paths  │
 ┌┴─────────────────┴┐
│ Integration Tests   │ (30%)
│   API & Database   │
┌┴─────────────────┴─┐
│   Unit Tests (60%)   │
│  Business Logic &   │
│    Components       │
└─────────────────────┘
```

## 1. Unit Testing (60% - 90% Coverage Target)

### Backend Unit Tests (FastAPI + SQLAlchemy)

#### Test Framework: pytest + pytest-asyncio
```python
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=90
```

#### Service Layer Testing
```python
# tests/unit/services/test_worklog_service.py
import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, AsyncMock
from src.services.worklog_service import WorklogService
from src.models.worklog import WorkLog
from src.core.exceptions import ValidationError, BusinessRuleError

class TestWorklogService:
    @pytest.fixture
    def mock_db_session(self):
        return Mock()
    
    @pytest.fixture
    def worklog_service(self, mock_db_session):
        return WorklogService(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_create_worklog_valid_data(self, worklog_service):
        # Arrange
        worklog_data = {
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "date": date.today(),
            "hours": Decimal("4.5"),
            "description": "Implemented user authentication"
        }
        expected_worklog = WorkLog(**worklog_data)
        worklog_service.repository.create = AsyncMock(return_value=expected_worklog)
        
        # Act
        result = await worklog_service.create_worklog(worklog_data, user_id="user123")
        
        # Assert
        assert result.hours == Decimal("4.5")
        assert result.description == "Implemented user authentication"
        worklog_service.repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_worklog_exceeds_daily_limit(self, worklog_service):
        # Arrange
        worklog_data = {
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "date": date.today(),
            "hours": Decimal("25.0"),  # Exceeds 24-hour limit
            "description": "Invalid long work day"
        }
        
        # Act & Assert
        with pytest.raises(BusinessRuleError, match="exceeds daily limit"):
            await worklog_service.create_worklog(worklog_data, user_id="user123")
    
    @pytest.mark.asyncio
    async def test_get_user_weekly_summary(self, worklog_service):
        # Arrange
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        week_start = date(2025, 11, 10)  # Monday
        mock_worklogs = [
            Mock(hours=Decimal("8.0"), date=date(2025, 11, 10)),
            Mock(hours=Decimal("7.5"), date=date(2025, 11, 11)),
        ]
        worklog_service.repository.get_by_user_and_week = AsyncMock(return_value=mock_worklogs)
        
        # Act
        summary = await worklog_service.get_user_weekly_summary(user_id, week_start)
        
        # Assert
        assert summary["total_hours"] == Decimal("15.5")
        assert summary["days_worked"] == 2
        assert len(summary["daily_breakdown"]) == 2
```

#### Model Validation Testing
```python
# tests/unit/models/test_worklog.py
import pytest
from decimal import Decimal
from datetime import date, datetime
from pydantic import ValidationError
from src.models.worklog import WorkLogCreate, WorkLogUpdate

class TestWorkLogValidation:
    def test_valid_worklog_creation(self):
        # Arrange & Act
        worklog = WorkLogCreate(
            task_id="123e4567-e89b-12d3-a456-426614174000",
            date=date.today(),
            hours=Decimal("4.25"),
            description="Completed feature implementation"
        )
        
        # Assert
        assert worklog.hours == Decimal("4.25")
        assert len(worklog.description) > 0
    
    def test_invalid_hours_below_minimum(self):
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            WorkLogCreate(
                task_id="123e4567-e89b-12d3-a456-426614174000",
                date=date.today(),
                hours=Decimal("0.1"),  # Below 0.25 minimum
                description="Invalid hours"
            )
        assert "hours must be between 0.25 and 24.0" in str(exc_info.value)
    
    def test_future_date_validation(self):
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            WorkLogCreate(
                task_id="123e4567-e89b-12d3-a456-426614174000",
                date=date.today().replace(year=date.today().year + 1),
                hours=Decimal("8.0"),
                description="Future work"
            )
        assert "cannot be in the future" in str(exc_info.value)
```

### Frontend Unit Tests (React + TypeScript)

#### Test Framework: Vitest + React Testing Library
```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*'
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 90,
          statements: 90
        }
      }
    }
  }
})
```

#### Component Testing
```typescript
// tests/components/WorkLogForm.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { WorkLogForm } from '@/components/WorkLogForm'
import { WorkLogService } from '@/services/workLogService'

// Mock the service
vi.mock('@/services/workLogService')

describe('WorkLogForm', () => {
  const mockOnSubmit = vi.fn()
  const mockWorkLogService = vi.mocked(WorkLogService)
  
  beforeEach(() => {
    vi.clearAllMocks()
  })
  
  it('should render all required form fields', () => {
    render(<WorkLogForm onSubmit={mockOnSubmit} />)
    
    expect(screen.getByLabelText(/task/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/date/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/hours/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument()
  })
  
  it('should validate hours input range', async () => {
    const user = userEvent.setup()
    render(<WorkLogForm onSubmit={mockOnSubmit} />)
    
    const hoursInput = screen.getByLabelText(/hours/i)
    await user.type(hoursInput, '25')
    
    expect(screen.getByText(/hours must be between 0.25 and 24/i)).toBeInTheDocument()
  })
  
  it('should submit valid form data', async () => {
    const user = userEvent.setup()
    mockWorkLogService.prototype.createWorkLog = vi.fn().mockResolvedValue({
      id: '123',
      success: true
    })
    
    render(<WorkLogForm onSubmit={mockOnSubmit} />)
    
    // Fill form
    await user.selectOptions(screen.getByLabelText(/task/i), 'task-123')
    await user.type(screen.getByLabelText(/hours/i), '4.5')
    await user.type(screen.getByLabelText(/description/i), 'Completed feature')
    
    // Submit
    await user.click(screen.getByRole('button', { name: /submit/i }))
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task-123',
          hours: 4.5,
          description: 'Completed feature'
        })
      )
    })
  })
})
```

#### Hook Testing
```typescript
// tests/hooks/useWorkLogs.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { useWorkLogs } from '@/hooks/useWorkLogs'
import { WorkLogService } from '@/services/workLogService'

vi.mock('@/services/workLogService')

describe('useWorkLogs', () => {
  const mockWorkLogService = vi.mocked(WorkLogService)
  
  beforeEach(() => {
    vi.clearAllMocks()
  })
  
  it('should fetch work logs on mount', async () => {
    const mockWorkLogs = [
      { id: '1', hours: 8, description: 'Work 1' },
      { id: '2', hours: 4, description: 'Work 2' }
    ]
    
    mockWorkLogService.prototype.getWorkLogs = vi.fn().mockResolvedValue(mockWorkLogs)
    
    const { result } = renderHook(() => useWorkLogs({ userId: 'user123' }))
    
    await waitFor(() => {
      expect(result.current.workLogs).toEqual(mockWorkLogs)
      expect(result.current.loading).toBe(false)
    })
  })
  
  it('should handle error states', async () => {
    const errorMessage = 'Failed to fetch work logs'
    mockWorkLogService.prototype.getWorkLogs = vi.fn().mockRejectedValue(
      new Error(errorMessage)
    )
    
    const { result } = renderHook(() => useWorkLogs({ userId: 'user123' }))
    
    await waitFor(() => {
      expect(result.current.error).toBe(errorMessage)
      expect(result.current.loading).toBe(false)
    })
  })
})
```

## 2. Integration Testing (30% - API + Database)

### Database Integration Tests
```python
# tests/integration/test_database.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.core.database import Base
from src.models import User, Project, Task, WorkLog

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db():
    # Create test database
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost/pdls_test")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture
async def db_session(test_db):
    async_session = sessionmaker(test_db, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()

class TestDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_create_user_and_project(self, db_session):
        # Create user
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
            role="developer"
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create project
        project = Project(
            name="Test Project",
            description="Test project description",
            start_date=date.today(),
            created_by=user.id
        )
        db_session.add(project)
        await db_session.commit()
        
        # Verify relationships
        assert user.id is not None
        assert project.created_by == user.id
    
    @pytest.mark.asyncio
    async def test_worklog_daily_limit_constraint(self, db_session):
        # Setup user, project, and task
        user = User(email="test@example.com", password_hash="hash", 
                   full_name="Test", role="developer")
        project = Project(name="Test", description="Test", 
                         start_date=date.today(), created_by=user.id)
        task = Task(title="Test Task", description="Test", 
                   project=project, created_by=user.id)
        
        db_session.add_all([user, project, task])
        await db_session.commit()
        
        # Create work logs totaling more than 24 hours
        worklog1 = WorkLog(user=user, task=task, project=project,
                          date=date.today(), hours=Decimal("20.0"),
                          description="Long day 1")
        worklog2 = WorkLog(user=user, task=task, project=project,
                          date=date.today(), hours=Decimal("5.0"),
                          description="Exceeds limit")
        
        db_session.add(worklog1)
        await db_session.commit()
        
        db_session.add(worklog2)
        
        # Should raise constraint violation
        with pytest.raises(Exception) as exc_info:
            await db_session.commit()
        assert "daily work hours" in str(exc_info.value).lower()
```

### API Integration Tests
```python
# tests/integration/test_api.py
import pytest
from httpx import AsyncClient
from src.main import app
from src.core.dependencies import get_current_user
from src.models import User

@pytest.fixture
def mock_current_user():
    return User(
        id="123e4567-e89b-12d3-a456-426614174000",
        email="test@example.com",
        full_name="Test User",
        role="developer",
        is_active=True
    )

@pytest.fixture
async def authenticated_client(mock_current_user):
    app.dependency_overrides[get_current_user] = lambda: mock_current_user
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

class TestWorkLogAPI:
    @pytest.mark.asyncio
    async def test_create_worklog_success(self, authenticated_client):
        worklog_data = {
            "task_id": "123e4567-e89b-12d3-a456-426614174001",
            "date": "2025-11-12",
            "hours": 4.5,
            "description": "Implemented authentication"
        }
        
        response = await authenticated_client.post("/api/v1/worklogs", json=worklog_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["hours"] == 4.5
        assert data["description"] == "Implemented authentication"
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_worklog_validation_error(self, authenticated_client):
        invalid_data = {
            "task_id": "invalid-uuid",
            "date": "2025-11-12",
            "hours": 25.0,  # Exceeds limit
            "description": ""  # Empty description
        }
        
        response = await authenticated_client.post("/api/v1/worklogs", json=invalid_data)
        
        assert response.status_code == 422
        error_data = response.json()
        assert "validation error" in error_data["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_worklogs_with_filters(self, authenticated_client):
        # First create some work logs
        # ... (setup code)
        
        # Test date range filtering
        response = await authenticated_client.get(
            "/api/v1/worklogs",
            params={
                "date_from": "2025-11-10",
                "date_to": "2025-11-12",
                "page": 1,
                "per_page": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
```

## 3. Contract Testing (OpenAPI Compliance)

### API Contract Validation
```python
# tests/contract/test_openapi_compliance.py
import pytest
from openapi_spec_validator import validate_spec
from openapi_spec_validator.readers import read_from_filename
import json
from pathlib import Path

class TestOpenAPICompliance:
    def test_openapi_spec_is_valid(self):
        """Validate that our OpenAPI spec is syntactically correct"""
        spec_path = Path("specs/001-dev-log-system/contracts/api-spec.json")
        
        with open(spec_path) as f:
            spec = json.load(f)
        
        # This will raise an exception if the spec is invalid
        validate_spec(spec)
    
    @pytest.mark.asyncio
    async def test_api_responses_match_schema(self, authenticated_client):
        """Test that actual API responses match OpenAPI schema"""
        from openapi_core import create_spec
        from openapi_core.validation.request import openapi_request_validator
        from openapi_core.validation.response import openapi_response_validator
        
        # Load OpenAPI spec
        spec_path = Path("specs/001-dev-log-system/contracts/api-spec.json")
        spec = create_spec(spec_path)
        
        # Make API call
        response = await authenticated_client.get("/api/v1/worklogs")
        
        # Validate response against schema
        validator = openapi_response_validator.ResponseValidator(spec)
        result = validator.validate(response)
        
        assert not result.errors, f"API response validation failed: {result.errors}"
```

### Schema Evolution Testing
```python
# tests/contract/test_schema_evolution.py
import pytest
from deepdiff import DeepDiff
import json

class TestSchemaEvolution:
    def test_backward_compatibility(self):
        """Ensure API changes don't break existing clients"""
        # Load current and previous API specs
        current_spec = self._load_spec("current")
        previous_spec = self._load_spec("v1.0.0")  # From version control
        
        # Check for breaking changes
        diff = DeepDiff(previous_spec["paths"], current_spec["paths"])
        
        # Allow additions but not removals or type changes
        breaking_changes = []
        
        if "dictionary_item_removed" in diff:
            breaking_changes.extend(diff["dictionary_item_removed"])
        
        if "type_changes" in diff:
            breaking_changes.extend(diff["type_changes"])
        
        assert not breaking_changes, f"Breaking API changes detected: {breaking_changes}"
    
    def _load_spec(self, version):
        # Implementation to load spec from file or version control
        pass
```

## 4. End-to-End Testing (10% - Critical Paths)

### E2E Test Framework: Playwright
```typescript
// tests/e2e/playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    }
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  }
})
```

### Critical User Journey Tests
```typescript
// tests/e2e/worklog-flow.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Work Log Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('[data-testid=email]', 'developer@pdls.local')
    await page.fill('[data-testid=password]', 'password123')
    await page.click('[data-testid=login-button]')
    
    // Wait for dashboard
    await expect(page.locator('[data-testid=dashboard]')).toBeVisible()
  })
  
  test('should create and view work log entry', async ({ page }) => {
    // Navigate to work logs
    await page.click('[data-testid=nav-worklogs]')
    await expect(page.locator('h1')).toContainText('Work Logs')
    
    // Create new work log
    await page.click('[data-testid=new-worklog-button]')
    
    // Fill form
    await page.selectOption('[data-testid=task-select]', 'task-123')
    await page.fill('[data-testid=hours-input]', '4.5')
    await page.fill('[data-testid=description-input]', 'Completed user authentication feature')
    
    // Submit
    await page.click('[data-testid=submit-worklog]')
    
    // Verify success
    await expect(page.locator('[data-testid=success-message]')).toBeVisible()
    await expect(page.locator('[data-testid=worklog-list]')).toContainText('4.5 hours')
    await expect(page.locator('[data-testid=worklog-list]')).toContainText('Completed user authentication feature')
  })
  
  test('should validate work log hours limit', async ({ page }) => {
    await page.goto('/worklogs/new')
    
    // Try to enter invalid hours
    await page.fill('[data-testid=hours-input]', '25')
    await page.blur('[data-testid=hours-input]')
    
    // Should show validation error
    await expect(page.locator('[data-testid=error-message]'))
      .toContainText('Hours must be between 0.25 and 24')
    
    // Submit button should be disabled
    await expect(page.locator('[data-testid=submit-worklog]')).toBeDisabled()
  })
})

test.describe('Weekly Report Generation', () => {
  test('should automatically generate weekly report', async ({ page }) => {
    // Mock time to be Friday 23:59
    await page.addInitScript(() => {
      Date.now = () => new Date('2025-11-14T23:59:00Z').getTime()
    })
    
    await page.goto('/reports')
    
    // Wait for automatic report generation (this would be triggered by cron in real scenario)
    await expect(page.locator('[data-testid=report-generating]')).toBeVisible()
    
    // Wait for completion (with timeout)
    await expect(page.locator('[data-testid=report-completed]')).toBeVisible({ timeout: 30000 })
    
    // Verify report content
    await expect(page.locator('[data-testid=report-title]'))
      .toContainText('Weekly Report - November 10-14, 2025')
    
    // Check export options are available
    await expect(page.locator('[data-testid=export-pdf]')).toBeVisible()
    await expect(page.locator('[data-testid=export-markdown]')).toBeVisible()
    await expect(page.locator('[data-testid=export-notion]')).toBeVisible()
  })
})
```

### Performance E2E Tests
```typescript
// tests/e2e/performance.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Performance Tests', () => {
  test('should load dashboard within 2 seconds', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto('/login')
    await page.fill('[data-testid=email]', 'test@pdls.local')
    await page.fill('[data-testid=password]', 'password123')
    await page.click('[data-testid=login-button]')
    
    await expect(page.locator('[data-testid=dashboard]')).toBeVisible()
    
    const loadTime = Date.now() - startTime
    expect(loadTime).toBeLessThan(2000) // 2 seconds
  })
  
  test('should handle 50 work log entries efficiently', async ({ page }) => {
    await page.goto('/worklogs')
    
    // Simulate large dataset
    await page.route('/api/v1/worklogs*', route => {
      const mockData = Array.from({ length: 50 }, (_, i) => ({
        id: `worklog-${i}`,
        hours: Math.random() * 8,
        description: `Work log entry ${i}`,
        date: new Date().toISOString().split('T')[0]
      }))
      
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: mockData,
          pagination: { page: 1, per_page: 50, total: 50, pages: 1 }
        })
      })
    })
    
    const startTime = Date.now()
    await page.reload()
    await expect(page.locator('[data-testid=worklog-list] tr')).toHaveCount(50)
    
    const renderTime = Date.now() - startTime
    expect(renderTime).toBeLessThan(1000) // 1 second for 50 items
  })
})
```

## 5. Security Testing

### Authentication & Authorization Tests
```python
# tests/security/test_auth.py
import pytest
from httpx import AsyncClient
from src.main import app

class TestSecurityControls:
    @pytest.mark.asyncio
    async def test_unauthenticated_access_denied(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/worklogs")
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_role_based_access_control(self, authenticated_client):
        # Test developer cannot access admin endpoints
        response = await authenticated_client.get("/api/v1/admin/users")
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_sql_injection_prevention(self, authenticated_client):
        # Attempt SQL injection in query parameters
        malicious_input = "'; DROP TABLE users; --"
        response = await authenticated_client.get(
            f"/api/v1/worklogs?user_id={malicious_input}"
        )
        # Should return validation error, not execute SQL
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_jwt_token_expiry(self):
        # Test with expired JWT token
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."  # Expired token
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/worklogs",
                headers={"Authorization": f"Bearer {expired_token}"}
            )
            assert response.status_code == 401
```

## 6. Load Testing

### Locust Performance Tests
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between
import json
import random

class PDLSUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Login and get auth token"""
        response = self.client.post("/api/v1/auth/login", json={
            "email": "load_test@pdls.local",
            "password": "password123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
    
    @task(3)
    def view_worklogs(self):
        """Most common operation - view work logs"""
        self.client.get("/api/v1/worklogs?page=1&per_page=20")
    
    @task(2)
    def create_worklog(self):
        """Create new work log entry"""
        worklog_data = {
            "task_id": "123e4567-e89b-12d3-a456-426614174000",
            "date": "2025-11-12",
            "hours": round(random.uniform(0.25, 8.0), 2),
            "description": f"Load test work entry {random.randint(1, 1000)}"
        }
        self.client.post("/api/v1/worklogs", json=worklog_data)
    
    @task(1)
    def view_reports(self):
        """View weekly reports"""
        self.client.get("/api/v1/reports/weekly?page=1&per_page=10")

class AdminUser(HttpUser):
    wait_time = between(2, 8)
    weight = 1  # Lower weight = fewer admin users
    
    @task
    def view_all_users(self):
        self.client.get("/api/v1/admin/users")
    
    @task
    def approve_leave_requests(self):
        self.client.get("/api/v1/leaves?status=pending")
```

## 7. Test Data Management

### Test Fixtures and Factories
```python
# tests/factories.py
import factory
from faker import Faker
from datetime import date, timedelta
from decimal import Decimal
from src.models import User, Project, Task, WorkLog

fake = Faker()

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeZUi3P8C9.8JhYsO"  # "password"
    full_name = factory.Faker('name')
    role = factory.Iterator(['developer', 'pm', 'stakeholder'])
    is_active = True

class ProjectFactory(factory.Factory):
    class Meta:
        model = Project
    
    name = factory.Faker('catch_phrase')
    description = factory.Faker('text', max_nb_chars=500)
    status = "active"
    start_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=90))

class WorkLogFactory(factory.Factory):
    class Meta:
        model = WorkLog
    
    date = factory.LazyFunction(lambda: fake.date_between(start_date='-30d', end_date='today'))
    hours = factory.LazyFunction(lambda: Decimal(str(round(fake.random.uniform(0.25, 8.0), 2))))
    description = factory.Faker('sentence', nb_words=8)
    is_billable = True
```

## 8. Test Environment Setup

### Docker Test Environment
```dockerfile
# docker-compose.test.yml
version: '3.8'
services:
  test-db:
    image: postgres:15
    environment:
      POSTGRES_DB: pdls_test
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_pass
    ports:
      - "5433:5432"
    volumes:
      - test_db_data:/var/lib/postgresql/data

  test-redis:
    image: redis:7-alpine
    ports:
      - "6380:6379"

  test-minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: testuser
      MINIO_ROOT_PASSWORD: testpass123
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - test_minio_data:/data

volumes:
  test_db_data:
  test_minio_data:
```

### GitHub Actions CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: pdls_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit --cov=src --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: pdls_test
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v4
    - name: Run integration tests
      run: |
        pytest tests/integration

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '18'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Install Playwright
      run: npx playwright install --with-deps
    
    - name: Start services
      run: |
        docker-compose -f docker-compose.test.yml up -d
        npm run dev &
    
    - name: Run E2E tests
      run: npx playwright test
    
    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: playwright-report
        path: playwright-report/

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Run security scan
      uses: pypa/gh-action-pip-audit@v1.0.8
    
    - name: Run Bandit security linter
      run: |
        pip install bandit
        bandit -r src/
```

## 9. Test Reporting and Monitoring

### Coverage Reporting
```python
# .coveragerc
[run]
source = src
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

### Test Metrics Dashboard
```python
# tests/metrics/test_metrics.py
import json
from datetime import datetime
from pathlib import Path

class TestMetricsCollector:
    def __init__(self):
        self.metrics = {
            "timestamp": datetime.now().isoformat(),
            "coverage": {},
            "performance": {},
            "reliability": {}
        }
    
    def collect_coverage_metrics(self, coverage_report):
        self.metrics["coverage"] = {
            "lines": coverage_report.get("lines_percent", 0),
            "branches": coverage_report.get("branches_percent", 0),
            "functions": coverage_report.get("functions_percent", 0)
        }
    
    def collect_performance_metrics(self, test_results):
        self.metrics["performance"] = {
            "avg_response_time": sum(r.duration for r in test_results) / len(test_results),
            "slowest_test": max(test_results, key=lambda x: x.duration).name,
            "total_execution_time": sum(r.duration for r in test_results)
        }
    
    def save_metrics(self):
        metrics_file = Path("test-reports/metrics.json")
        metrics_file.parent.mkdir(exist_ok=True)
        
        with open(metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)
```

This comprehensive testing strategy ensures PDLS system reliability, security, and performance across all layers while maintaining efficient development workflows and continuous quality assurance.