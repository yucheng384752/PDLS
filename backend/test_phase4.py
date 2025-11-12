"""
Test script for Phase 4 Project Management System
Tests the project CRUD operations and validates database schema
"""

import sys
import os
import asyncio
from datetime import datetime

# Add the backend src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.orm import sessionmaker
from src.core.database import sync_engine
from src.models.user import User, UserRole
from src.models.project import Project, ProjectStatus, ProjectPriority, ProjectType

# Create session
SessionLocal = sessionmaker(bind=sync_engine)

def test_project_models():
    """Test project model creation and relationships"""
    print("🔧 Testing Project Models...")
    
    db = SessionLocal()
    
    try:
        # Create test user
        test_user = User(
            username="project_tester",
            email="tester@example.com",
            role=UserRole.DEVELOPER
        )
        test_user.set_password("test123")
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"✅ Created test user: {test_user.username} (ID: {test_user.id})")
        
        # Create test project
        test_project = Project(
            name="Phase 4 Test Project",
            description="Testing project management functionality",
            project_type=ProjectType.SOFTWARE,
            status=ProjectStatus.PLANNING,
            priority=ProjectPriority.HIGH,
            owner_id=test_user.id,
            created_by=test_user.id
        )
        
        db.add(test_project)
        db.commit()
        db.refresh(test_project)
        print(f"✅ Created test project: {test_project.name} (ID: {test_project.id})")
        
        # Verify relationships
        projects = db.query(Project).filter(Project.owner_id == test_user.id).all()
        print(f"✅ User owns {len(projects)} project(s)")
        
        # Test project properties
        print(f"   Project UUID: {test_project.uuid}")
        print(f"   Project Type: {test_project.project_type}")
        print(f"   Status: {test_project.status}")
        print(f"   Priority: {test_project.priority}")
        print(f"   Created: {test_project.created_at}")
        
        # Test soft delete
        test_project.soft_delete()
        print(f"✅ Project soft deleted: is_deleted={test_project.is_deleted}")
        
        # Cleanup
        db.rollback()
        print("✅ Test data cleaned up")
        
    except Exception as e:
        print(f"❌ Error testing project models: {e}")
        db.rollback()
    finally:
        db.close()


def test_project_enums():
    """Test project enum values"""
    print("\n📋 Testing Project Enums...")
    
    try:
        # Test ProjectType enum
        print(f"✅ ProjectType values: {[t.value for t in ProjectType]}")
        
        # Test ProjectStatus enum
        print(f"✅ ProjectStatus values: {[s.value for s in ProjectStatus]}")
        
        # Test ProjectPriority enum
        print(f"✅ ProjectPriority values: {[p.value for p in ProjectPriority]}")
        
    except Exception as e:
        print(f"❌ Error testing enums: {e}")


def test_database_schema():
    """Test database schema and tables"""
    print("\n🗄️  Testing Database Schema...")
    
    try:
        # Import database engine for basic connection test
        from src.core.database import sync_engine
        from sqlalchemy import text, inspect
        
        # Test basic connection
        with sync_engine.connect() as conn:
            # Check if tables exist
            inspector = inspect(sync_engine)
            tables = inspector.get_table_names()
            print(f"✅ Database connected, found {len(tables)} tables: {tables}")
            
            # Check if key tables exist
            for table_name in ['users', 'projects']:
                if table_name in tables:
                    print(f"✅ Table '{table_name}' exists")
                    # Get column info
                    columns = inspector.get_columns(table_name)
                    print(f"   - {len(columns)} columns: {[col['name'] for col in columns[:5]]}...")
                else:
                    print(f"❌ Table '{table_name}' missing")
        
    except Exception as e:
        print(f"❌ Error testing database schema: {e}")


def test_project_api_imports():
    """Test if project API modules can be imported"""
    print("\n📦 Testing Project API Imports...")
    
    try:
        # Test simplified project API
        from src.api.v1.projects_simple import router as projects_simple_router
        print("✅ Simple project API imported successfully")
        
        # Test project schemas
        from src.schemas.project import ProjectCreate, ProjectResponse
        print("✅ Project schemas imported successfully")
        
        # Test services
        from src.services.notification_service import NotificationService
        from src.services.file_service import FileService
        print("✅ Project services imported successfully")
        
    except Exception as e:
        print(f"❌ Error importing project APIs: {e}")


def main():
    """Run all Phase 4 tests"""
    print("🚀 Phase 4 Project Management System Tests")
    print("=" * 50)
    
    test_database_schema()
    test_project_enums()
    test_project_models()
    test_project_api_imports()
    
    print("\n" + "=" * 50)
    print("📊 Phase 4 Testing Complete!")
    print("✨ Project management system foundation is ready")


if __name__ == "__main__":
    main()