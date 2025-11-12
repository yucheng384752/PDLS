# Integration Notes

**Date**: 2025年11月12日  
**Phase**: 1 - Design & Contracts

## Overview

This document provides comprehensive integration specifications for PDLS external system connectivity, including GitHub Issues, Notion workspace integration, SMTP notifications, and MCP (Model Context Protocol) tools for maintaining read/write boundaries.

## 1. GitHub Issues Integration

### 1.1 Authentication & Authorization

**OAuth2 Flow Implementation**:
```python
# src/services/github_service.py
import httpx
from typing import Optional
from src.core.config import settings
from src.models.integration import GitHubIntegration

class GitHubService:
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        
    async def get_oauth_url(self, state: str) -> str:
        """Generate OAuth2 authorization URL for user consent"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": f"{settings.FRONTEND_URL}/auth/github/callback",
            "scope": "repo,read:user",
            "state": state
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://github.com/login/oauth/authorize?{query_string}"
    
    async def exchange_code_for_token(self, code: str) -> Optional[str]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code
                },
                headers={"Accept": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
            return None
```

### 1.2 Bidirectional Synchronization

**Work Log to GitHub Issue Updates**:
```python
class GitHubSyncService:
    def __init__(self, github_service: GitHubService):
        self.github = github_service
        
    async def sync_worklog_to_issue(self, worklog: WorkLog, github_token: str):
        """Update GitHub issue with work log progress"""
        task = worklog.task
        if not task.github_issue_number or not task.project.github_repo_url:
            return
            
        repo_path = self._extract_repo_path(task.project.github_repo_url)
        issue_number = task.github_issue_number
        
        # Calculate task progress
        total_logged = await self._get_total_logged_hours(task.id)
        progress_percentage = 0
        if task.estimated_hours:
            progress_percentage = min(100, (total_logged / task.estimated_hours) * 100)
        
        # Update issue comment
        comment_body = self._format_progress_comment(worklog, total_logged, progress_percentage)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.github.base_url}/repos/{repo_path}/issues/{issue_number}/comments",
                json={"body": comment_body},
                headers={
                    "Authorization": f"token {github_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code == 201:
                # Log successful sync
                await self._log_sync_event(worklog.id, "github", "comment_created", response.json())
                
    def _format_progress_comment(self, worklog: WorkLog, total_hours: float, progress: float) -> str:
        """Format work log update as GitHub comment"""
        return f"""
**PDLS Work Log Update**

📅 **Date**: {worklog.date}  
⏱️ **Hours Logged**: {worklog.hours}  
👤 **Developer**: {worklog.user.full_name}  
📊 **Total Progress**: {total_hours}h ({progress:.1f}%)  

**Description**: {worklog.description}

---
*This update was automatically posted by PDLS*
        """.strip()
```

**GitHub Webhook Handler**:
```python
# src/api/webhooks/github.py
from fastapi import APIRouter, HTTPException, Depends, Request
from src.services.github_webhook_service import GitHubWebhookService
from src.core.security import verify_github_webhook

router = APIRouter()

@router.post("/webhooks/github")
async def handle_github_webhook(
    request: Request,
    webhook_service: GitHubWebhookService = Depends()
):
    """Handle GitHub webhook events for issue updates"""
    # Verify webhook signature
    signature = request.headers.get("X-Hub-Signature-256")
    payload = await request.body()
    
    if not verify_github_webhook(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    event_type = request.headers.get("X-GitHub-Event")
    event_data = await request.json()
    
    # Process different event types
    if event_type == "issues":
        await webhook_service.handle_issue_event(event_data)
    elif event_type == "issue_comment":
        await webhook_service.handle_comment_event(event_data)
    
    return {"status": "processed"}

class GitHubWebhookService:
    async def handle_issue_event(self, event_data: dict):
        """Process GitHub issue events (opened, closed, edited)"""
        action = event_data.get("action")
        issue = event_data.get("issue", {})
        repository = event_data.get("repository", {})
        
        if action in ["opened", "edited"]:
            await self._sync_issue_to_task(issue, repository)
        elif action == "closed":
            await self._mark_task_completed(issue, repository)
    
    async def _sync_issue_to_task(self, issue: dict, repository: dict):
        """Update PDLS task based on GitHub issue changes"""
        issue_number = issue.get("number")
        repo_url = repository.get("html_url")
        
        # Find matching task
        task = await self._find_task_by_github_issue(repo_url, issue_number)
        if not task:
            return
            
        # Update task details
        task.title = issue.get("title", task.title)
        task.description = issue.get("body", task.description)
        
        # Update status based on issue state
        if issue.get("state") == "closed":
            task.status = "done"
        elif issue.get("assignee"):
            task.status = "in_progress"
            
        await self._update_task(task)
```

### 1.3 Rate Limiting & Error Handling

**Rate Limiting Compliance**:
```python
import asyncio
from datetime import datetime, timedelta
from typing import Optional

class GitHubRateLimiter:
    def __init__(self):
        self.requests_remaining = 5000  # GitHub API limit
        self.reset_time: Optional[datetime] = None
        self.secondary_rate_remaining = 100  # Search API limit
        
    async def check_rate_limit(self, response_headers: dict):
        """Update rate limit info from GitHub response headers"""
        self.requests_remaining = int(response_headers.get("X-RateLimit-Remaining", 0))
        reset_timestamp = int(response_headers.get("X-RateLimit-Reset", 0))
        self.reset_time = datetime.fromtimestamp(reset_timestamp)
        
        # Handle secondary rate limits
        if "X-RateLimit-Resource" in response_headers:
            resource_type = response_headers["X-RateLimit-Resource"]
            if resource_type == "search":
                self.secondary_rate_remaining = int(
                    response_headers.get("X-RateLimit-Remaining", 0)
                )
    
    async def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        if self.requests_remaining <= 10:  # Safety buffer
            if self.reset_time and self.reset_time > datetime.now():
                wait_seconds = (self.reset_time - datetime.now()).total_seconds()
                await asyncio.sleep(wait_seconds)

class GitHubServiceWithRetry(GitHubService):
    def __init__(self):
        super().__init__()
        self.rate_limiter = GitHubRateLimiter()
        
    async def make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make GitHub API request with rate limiting and retry logic"""
        max_retries = 3
        backoff_factor = 2
        
        for attempt in range(max_retries):
            try:
                await self.rate_limiter.wait_if_needed()
                
                async with httpx.AsyncClient() as client:
                    response = await client.request(method, url, **kwargs)
                    
                    # Update rate limit info
                    await self.rate_limiter.check_rate_limit(response.headers)
                    
                    if response.status_code == 429:  # Rate limit exceeded
                        retry_after = int(response.headers.get("Retry-After", 60))
                        await asyncio.sleep(retry_after)
                        continue
                    
                    if response.status_code >= 500:  # Server error
                        if attempt < max_retries - 1:
                            await asyncio.sleep(backoff_factor ** attempt)
                            continue
                    
                    return response
                    
            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(backoff_factor ** attempt)
        
        raise Exception("Max retries exceeded")
```

## 2. Notion Integration

### 2.1 API Configuration

**Notion Client Setup**:
```python
# src/services/notion_service.py
import httpx
from typing import Dict, Any, List
from src.core.config import settings

class NotionService:
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {settings.NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
    
    async def create_page(self, parent_id: str, title: str, content: List[Dict]) -> Dict[str, Any]:
        """Create a new page in Notion workspace"""
        payload = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
            "children": content
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/pages",
                json=payload,
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Notion API error: {response.status_code} - {response.text}")
```

### 2.2 Report Export to Notion

**Weekly Report Export**:
```python
class NotionExportService:
    def __init__(self, notion_service: NotionService):
        self.notion = notion_service
    
    async def export_weekly_report(self, report: WeeklyReport, parent_page_id: str) -> str:
        """Export weekly report to Notion page"""
        # Convert markdown content to Notion blocks
        notion_blocks = await self._markdown_to_notion_blocks(report.content_markdown)
        
        # Create page title
        title = f"Weekly Report - {report.week_start_date} to {report.week_end_date}"
        
        # Add metadata block
        metadata_block = {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"Project: {report.project.name}\n"}}
                    {"type": "text", "text": {"content": f"Total Hours: {report.total_hours}\n"}},
                    {"type": "text", "text": {"content": f"Tasks Completed: {report.total_tasks_completed}\n"}},
                    {"type": "text", "text": {"content": f"Team Size: {report.team_member_count}"}}
                ],
                "icon": {"type": "emoji", "emoji": "📊"}
            }
        }
        
        # Combine metadata and content
        all_blocks = [metadata_block] + notion_blocks
        
        # Create Notion page
        page = await self.notion.create_page(parent_page_id, title, all_blocks)
        return page["url"]
    
    async def _markdown_to_notion_blocks(self, markdown_content: str) -> List[Dict]:
        """Convert markdown content to Notion block format"""
        import markdown
        from markdown.extensions import codehilite
        
        # Parse markdown
        md = markdown.Markdown(extensions=['codehilite', 'tables', 'fenced_code'])
        html = md.convert(markdown_content)
        
        # Convert HTML to Notion blocks (simplified conversion)
        blocks = []
        
        # Split by major sections (headers)
        sections = html.split('<h')
        
        for section in sections:
            if not section.strip():
                continue
                
            if section.startswith('1>') or section.startswith('2>') or section.startswith('3>'):
                # Header block
                level = int(section[0])
                header_text = self._extract_text_from_html(section)
                blocks.append({
                    "object": "block",
                    "type": f"heading_{level}",
                    f"heading_{level}": {
                        "rich_text": [{"type": "text", "text": {"content": header_text}}]
                    }
                })
            else:
                # Paragraph or other content
                text_content = self._extract_text_from_html(section)
                if text_content:
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": text_content}}]
                        }
                    })
        
        return blocks
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML content"""
        import re
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', html)
        # Clean up whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text
```

### 2.3 Handover Document Export

**Structured Handover Export**:
```python
async def export_handover_to_notion(self, handover: HandoverDocument, parent_page_id: str) -> str:
    """Export handover document with structured format"""
    
    # Create structured blocks for handover content
    blocks = [
        # Header with handover metadata
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"Handover Type: {handover.handover_type}\n"}},
                    {"type": "text", "text": {"content": f"From: {handover.from_user.full_name}\n"}},
                    {"type": "text", "text": {"content": f"To: {handover.to_user.full_name if handover.to_user else 'TBD'}\n"}},
                    {"type": "text", "text": {"content": f"Effective Date: {handover.effective_date}"}}
                ],
                "icon": {"type": "emoji", "emoji": "🔄"}
            }
        },
        
        # Project Summary Section
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Project Summary"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": handover.project_summary}}]
            }
        },
        
        # Pending Tasks Table
        {
            "object": "block",
            "type": "heading_2", 
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "Pending Tasks"}}]
            }
        }
    ]
    
    # Add pending tasks as a table
    if handover.pending_tasks:
        table_block = {
            "object": "block",
            "type": "table",
            "table": {
                "table_width": 4,
                "has_column_header": True,
                "children": []
            }
        }
        
        # Header row
        header_row = {
            "object": "block",
            "type": "table_row",
            "table_row": {
                "cells": [
                    [{"type": "text", "text": {"content": "Task"}}],
                    [{"type": "text", "text": {"content": "Priority"}}],
                    [{"type": "text", "text": {"content": "Status"}}],
                    [{"type": "text", "text": {"content": "Notes"}}]
                ]
            }
        }
        table_block["table"]["children"].append(header_row)
        
        # Task rows
        for task in handover.pending_tasks:
            task_row = {
                "object": "block",
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"type": "text", "text": {"content": task.get("title", "")}}],
                        [{"type": "text", "text": {"content": task.get("priority", "")}}],
                        [{"type": "text", "text": {"content": task.get("status", "")}}],
                        [{"type": "text", "text": {"content": task.get("notes", "")}}]
                    ]
                }
            }
            table_block["table"]["children"].append(task_row)
        
        blocks.append(table_block)
    
    # Create and return page
    title = f"Handover - {handover.title}"
    page = await self.notion.create_page(parent_page_id, title, blocks)
    return page["url"]
```

## 3. SMTP Email Integration

### 3.1 Email Configuration

**Multi-Provider SMTP Setup**:
```python
# src/services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict
from src.core.config import settings

class EmailService:
    def __init__(self):
        self.smtp_config = {
            "host": settings.SMTP_HOST,
            "port": settings.SMTP_PORT,
            "username": settings.SMTP_USERNAME,
            "password": settings.SMTP_PASSWORD,
            "use_tls": settings.SMTP_USE_TLS
        }
        self.from_address = settings.SMTP_FROM_ADDRESS
        
    async def send_email(
        self, 
        to_addresses: List[str],
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None,
        attachments: Optional[List[Dict]] = None,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None
    ) -> bool:
        """Send email with optional attachments"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_address
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = subject
            
            if cc_addresses:
                msg['Cc'] = ', '.join(cc_addresses)
            
            # Add plain text version if not provided
            if not plain_content:
                plain_content = self._html_to_plain_text(html_content)
            
            # Attach text parts
            msg.attach(MIMEText(plain_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    msg.attach(part)
            
            # Send email
            all_recipients = to_addresses + (cc_addresses or []) + (bcc_addresses or [])
            
            with smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port']) as server:
                if self.smtp_config['use_tls']:
                    server.starttls()
                
                server.login(self.smtp_config['username'], self.smtp_config['password'])
                server.sendmail(self.from_address, all_recipients, msg.as_string())
            
            return True
            
        except Exception as e:
            # Log error and handle gracefully
            print(f"Email sending failed: {e}")
            return False
    
    def _html_to_plain_text(self, html_content: str) -> str:
        """Convert HTML to plain text"""
        import re
        # Remove HTML tags
        plain = re.sub(r'<[^>]+>', '', html_content)
        # Clean up whitespace
        plain = re.sub(r'\s+', ' ', plain).strip()
        return plain
```

### 3.2 Email Templates

**Template Management System**:
```python
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

class EmailTemplateService:
    def __init__(self):
        template_dir = Path("src/templates/email")
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def render_weekly_report_notification(self, report: WeeklyReport, recipient: User) -> Dict[str, str]:
        """Render weekly report notification email"""
        template = self.env.get_template("weekly_report_notification.html")
        
        context = {
            "recipient_name": recipient.full_name,
            "project_name": report.project.name,
            "week_start": report.week_start_date.strftime("%B %d, %Y"),
            "week_end": report.week_end_date.strftime("%B %d, %Y"),
            "total_hours": report.total_hours,
            "tasks_completed": report.total_tasks_completed,
            "team_size": report.team_member_count,
            "report_url": f"{settings.FRONTEND_URL}/reports/{report.id}"
        }
        
        html_content = template.render(**context)
        
        # Generate subject
        subject = f"Weekly Report Ready - {report.project.name} ({report.week_start_date.strftime('%m/%d')} - {report.week_end_date.strftime('%m/%d')})"
        
        return {
            "subject": subject,
            "html_content": html_content
        }
    
    def render_leave_request_notification(self, leave_request: LeaveRequest, manager: User) -> Dict[str, str]:
        """Render leave request approval notification"""
        template = self.env.get_template("leave_request_notification.html")
        
        context = {
            "manager_name": manager.full_name,
            "requester_name": leave_request.user.full_name,
            "leave_type": leave_request.leave_type.replace("_", " ").title(),
            "start_date": leave_request.start_date.strftime("%B %d, %Y"),
            "end_date": leave_request.end_date.strftime("%B %d, %Y"),
            "total_days": leave_request.total_days,
            "reason": leave_request.reason,
            "approval_url": f"{settings.FRONTEND_URL}/leaves/{leave_request.id}/approve"
        }
        
        html_content = template.render(**context)
        subject = f"Leave Request - {leave_request.user.full_name} ({leave_request.start_date.strftime('%m/%d')} - {leave_request.end_date.strftime('%m/%d')})"
        
        return {
            "subject": subject,
            "html_content": html_content
        }
```

### 3.3 Email Queue Management

**Async Email Queue with Celery**:
```python
# src/tasks/email_tasks.py
from celery import Celery
from src.services.email_service import EmailService, EmailTemplateService
from src.models import WeeklyReport, LeaveRequest, User

celery_app = Celery('pdls_email')

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_weekly_report_notifications(self, report_id: str):
    """Send weekly report notifications to project stakeholders"""
    try:
        # Load report and stakeholders
        report = WeeklyReport.get_by_id(report_id)
        stakeholders = report.project.get_stakeholders()
        
        email_service = EmailService()
        template_service = EmailTemplateService()
        
        for stakeholder in stakeholders:
            if stakeholder.preferences.get("email_notifications", {}).get("weekly_reports", True):
                email_content = template_service.render_weekly_report_notification(report, stakeholder)
                
                success = email_service.send_email(
                    to_addresses=[stakeholder.email],
                    subject=email_content["subject"],
                    html_content=email_content["html_content"]
                )
                
                if not success:
                    raise Exception(f"Failed to send email to {stakeholder.email}")
                    
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)

@celery_app.task
def send_leave_request_notification(leave_request_id: str):
    """Send leave request notification to managers"""
    leave_request = LeaveRequest.get_by_id(leave_request_id)
    managers = User.get_by_role("pm") + User.get_by_role("admin")
    
    email_service = EmailService()
    template_service = EmailTemplateService()
    
    for manager in managers:
        email_content = template_service.render_leave_request_notification(leave_request, manager)
        
        email_service.send_email(
            to_addresses=[manager.email],
            subject=email_content["subject"],
            html_content=email_content["html_content"]
        )
```

## 4. MCP (Model Context Protocol) Tools

### 4.1 Read/Write Boundary Implementation

**MCP Server Setup**:
```python
# src/mcp/server.py
from mcp import Server, types
from typing import Any, Sequence
from src.models import User, Project, WorkLog, WeeklyReport
from src.core.security import verify_mcp_permissions

app = Server("pdls-mcp")

# Read-only tools (AI can access)
@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available MCP tools with read/write boundaries"""
    return [
        types.Tool(
            name="read_work_logs",
            description="Read work log entries for analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "project_id": {"type": "string"},
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"}
                        }
                    }
                }
            }
        ),
        types.Tool(
            name="read_project_summary",
            description="Read project statistics and summary information",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {"type": "string", "format": "uuid"}
                },
                "required": ["project_id"]
            }
        ),
        types.Tool(
            name="generate_report_draft",
            description="Generate draft content for weekly reports (read-only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_id": {"type": "string", "format": "uuid"}
                },
                "required": ["report_id"]
            }
        ),
        # Write operations require human approval
        types.Tool(
            name="request_leave_approval",
            description="Request leave approval (requires human confirmation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "leave_request_id": {"type": "string", "format": "uuid"},
                    "action": {"type": "string", "enum": ["approve", "reject"]},
                    "notes": {"type": "string"}
                },
                "required": ["leave_request_id", "action"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle MCP tool calls with appropriate permissions"""
    
    if name == "read_work_logs":
        return await read_work_logs_handler(arguments)
    elif name == "read_project_summary":
        return await read_project_summary_handler(arguments)
    elif name == "generate_report_draft":
        return await generate_report_draft_handler(arguments)
    elif name == "request_leave_approval":
        return await request_leave_approval_handler(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def read_work_logs_handler(arguments: dict) -> list[types.TextContent]:
    """Read work logs with read-only access"""
    user_id = arguments.get("user_id")
    project_id = arguments.get("project_id")
    date_range = arguments.get("date_range", {})
    
    # Query work logs (read-only operation)
    work_logs = await WorkLog.query_by_filters(
        user_id=user_id,
        project_id=project_id,
        start_date=date_range.get("start_date"),
        end_date=date_range.get("end_date")
    )
    
    # Format response
    summary = {
        "total_entries": len(work_logs),
        "total_hours": sum(log.hours for log in work_logs),
        "date_range": f"{date_range.get('start_date')} to {date_range.get('end_date')}",
        "entries": [
            {
                "date": log.date.isoformat(),
                "hours": float(log.hours),
                "description": log.description,
                "task_title": log.task.title
            }
            for log in work_logs
        ]
    }
    
    return [types.TextContent(
        type="text",
        text=f"Work Log Summary:\n{json.dumps(summary, indent=2)}"
    )]

async def request_leave_approval_handler(arguments: dict) -> list[types.TextContent]:
    """Handle leave approval requests (requires human confirmation)"""
    leave_request_id = arguments["leave_request_id"]
    action = arguments["action"]
    notes = arguments.get("notes", "")
    
    # This is a write operation - create approval request for human
    approval_request = {
        "type": "leave_approval",
        "leave_request_id": leave_request_id,
        "requested_action": action,
        "ai_notes": notes,
        "status": "pending_human_approval",
        "created_at": datetime.now().isoformat()
    }
    
    # Store approval request (not execute the action)
    await store_approval_request(approval_request)
    
    # Notify relevant humans
    await notify_humans_of_approval_request(approval_request)
    
    return [types.TextContent(
        type="text", 
        text=f"Leave {action} request submitted for human approval. Request ID: {approval_request['id']}"
    )]
```

### 4.2 Permission Verification

**MCP Security Layer**:
```python
# src/core/mcp_security.py
from enum import Enum
from typing import Set, Dict, Any
from src.models import User

class MCPPermissionLevel(Enum):
    READ_ONLY = "read_only"
    DRAFT_GENERATION = "draft_generation"  
    REQUEST_APPROVAL = "request_approval"
    ADMIN_ONLY = "admin_only"

class MCPPermissionManager:
    # Define tool permissions
    TOOL_PERMISSIONS: Dict[str, MCPPermissionLevel] = {
        "read_work_logs": MCPPermissionLevel.READ_ONLY,
        "read_project_summary": MCPPermissionLevel.READ_ONLY,
        "read_user_profile": MCPPermissionLevel.READ_ONLY,
        "generate_report_draft": MCPPermissionLevel.DRAFT_GENERATION,
        "generate_handover_draft": MCPPermissionLevel.DRAFT_GENERATION,
        "request_leave_approval": MCPPermissionLevel.REQUEST_APPROVAL,
        "request_user_creation": MCPPermissionLevel.REQUEST_APPROVAL,
        "request_data_deletion": MCPPermissionLevel.ADMIN_ONLY
    }
    
    # Role-based access
    ROLE_PERMISSIONS: Dict[str, Set[MCPPermissionLevel]] = {
        "developer": {MCPPermissionLevel.READ_ONLY, MCPPermissionLevel.DRAFT_GENERATION},
        "pm": {MCPPermissionLevel.READ_ONLY, MCPPermissionLevel.DRAFT_GENERATION, MCPPermissionLevel.REQUEST_APPROVAL},
        "stakeholder": {MCPPermissionLevel.READ_ONLY},
        "admin": {MCPPermissionLevel.READ_ONLY, MCPPermissionLevel.DRAFT_GENERATION, MCPPermissionLevel.REQUEST_APPROVAL, MCPPermissionLevel.ADMIN_ONLY}
    }
    
    @classmethod
    def verify_tool_access(cls, tool_name: str, user: User) -> bool:
        """Verify if user can access specific MCP tool"""
        required_permission = cls.TOOL_PERMISSIONS.get(tool_name)
        if not required_permission:
            return False
            
        user_permissions = cls.ROLE_PERMISSIONS.get(user.role, set())
        return required_permission in user_permissions
    
    @classmethod
    def get_allowed_tools(cls, user: User) -> List[str]:
        """Get list of tools user can access"""
        user_permissions = cls.ROLE_PERMISSIONS.get(user.role, set())
        
        allowed_tools = []
        for tool_name, required_permission in cls.TOOL_PERMISSIONS.items():
            if required_permission in user_permissions:
                allowed_tools.append(tool_name)
        
        return allowed_tools

# Audit logging for MCP operations
class MCPAuditLogger:
    @staticmethod
    async def log_mcp_operation(
        tool_name: str,
        arguments: Dict[Any, Any],
        user: User,
        result_summary: str,
        execution_time_ms: int
    ):
        """Log MCP tool usage for audit purposes"""
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "user_id": user.id,
            "user_role": user.role,
            "arguments": arguments,
            "result_summary": result_summary,
            "execution_time_ms": execution_time_ms,
            "ip_address": "127.0.0.1",  # Would be actual IP in real implementation
            "session_id": "session_123"  # Would be actual session ID
        }
        
        # Store in audit log (separate from main database)
        await store_audit_log(audit_entry)
```

### 4.3 Human-AI Collaboration Workflow

**Approval Request System**:
```python
# src/services/approval_service.py
from enum import Enum
from typing import Dict, Any, List
from src.models import User, ApprovalRequest

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

class ApprovalService:
    async def create_approval_request(
        self,
        request_type: str,
        requested_by_ai: bool,
        context_data: Dict[str, Any],
        requires_role: str = "pm"
    ) -> ApprovalRequest:
        """Create new approval request for human review"""
        
        request = ApprovalRequest(
            request_type=request_type,
            requested_by_ai=requested_by_ai,
            context_data=context_data,
            requires_role=requires_role,
            status=ApprovalStatus.PENDING.value,
            expires_at=datetime.now() + timedelta(hours=24)  # 24-hour expiry
        )
        
        await request.save()
        
        # Notify appropriate users
        await self._notify_approvers(request)
        
        return request
    
    async def process_approval(
        self,
        request_id: str,
        approver: User,
        decision: str,
        notes: str = ""
    ) -> bool:
        """Process human approval decision"""
        
        request = await ApprovalRequest.get_by_id(request_id)
        if not request or request.status != ApprovalStatus.PENDING.value:
            raise ValueError("Invalid or already processed request")
        
        # Verify approver has required role
        if not self._verify_approver_permissions(approver, request):
            raise PermissionError("Insufficient permissions to approve this request")
        
        # Update request
        request.status = decision
        request.approved_by = approver.id
        request.approval_notes = notes
        request.processed_at = datetime.now()
        await request.save()
        
        # Execute approved action
        if decision == ApprovalStatus.APPROVED.value:
            await self._execute_approved_action(request)
        
        return True
    
    async def _execute_approved_action(self, request: ApprovalRequest):
        """Execute the action after human approval"""
        
        if request.request_type == "leave_approval":
            leave_service = LeaveService()
            await leave_service.process_leave_decision(
                leave_request_id=request.context_data["leave_request_id"],
                decision=request.context_data["requested_action"],
                approved_by=request.approved_by,
                notes=request.approval_notes
            )
        
        elif request.request_type == "user_creation":
            user_service = UserService()
            await user_service.create_user(
                user_data=request.context_data["user_data"],
                created_by=request.approved_by
            )
        
        # Add more action types as needed
        
    def _verify_approver_permissions(self, approver: User, request: ApprovalRequest) -> bool:
        """Verify approver has necessary permissions"""
        required_roles = {
            "leave_approval": ["pm", "admin"],
            "user_creation": ["admin"],
            "data_deletion": ["admin"]
        }
        
        allowed_roles = required_roles.get(request.request_type, ["admin"])
        return approver.role in allowed_roles
```

This comprehensive integration framework ensures secure, reliable, and compliant connectivity between PDLS and external systems while maintaining proper AI boundaries and human oversight for critical operations.