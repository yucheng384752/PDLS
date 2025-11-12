"""
Simple test script for Phase 4 Project Management System
Tests basic imports and enum functionality without database operations
"""

import sys
import os

# Add the backend src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_project_enums():
    """Test project enum values"""
    print("📋 Testing Project Enums...")
    
    try:
        from src.models.project import ProjectStatus, ProjectPriority, ProjectType, ProjectMemberRole, InvitationStatus
        
        # Test ProjectType enum
        print(f"✅ ProjectType values: {[t.value for t in ProjectType]}")
        
        # Test ProjectStatus enum
        print(f"✅ ProjectStatus values: {[s.value for s in ProjectStatus]}")
        
        # Test ProjectPriority enum
        print(f"✅ ProjectPriority values: {[p.value for p in ProjectPriority]}")
        
        # Test ProjectMemberRole enum
        print(f"✅ ProjectMemberRole values: {[r.value for r in ProjectMemberRole]}")
        
        # Test InvitationStatus enum
        print(f"✅ InvitationStatus values: {[s.value for s in InvitationStatus]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enums: {e}")
        return False


def test_project_models_import():
    """Test if project models can be imported"""
    print("\n🔧 Testing Project Models Import...")
    
    try:
        from src.models.project import Project, ProjectMember, ProjectFile, ProjectInvitation
        print("✅ All project models imported successfully")
        
        # Test model attributes
        print(f"   Project model: {Project.__name__}")
        print(f"   ProjectMember model: {ProjectMember.__name__}")
        print(f"   ProjectFile model: {ProjectFile.__name__}")
        print(f"   ProjectInvitation model: {ProjectInvitation.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error importing project models: {e}")
        return False


def test_project_schemas():
    """Test if project schemas can be imported"""
    print("\n📄 Testing Project Schemas...")
    
    try:
        from src.schemas.project import (
            ProjectCreate, ProjectUpdate, ProjectResponse, 
            ProjectMemberResponse, ProjectInvitationCreate, ProjectInvitationResponse
        )
        print("✅ All project schemas imported successfully")
        
        # Test creating a schema instance
        project_create_data = {
            "name": "Test Project",
            "description": "A test project",
            "project_type": "software"
        }
        
        project_create = ProjectCreate(**project_create_data)
        print(f"✅ ProjectCreate schema works: {project_create.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing project schemas: {e}")
        return False


def test_project_api_imports():
    """Test if project API modules can be imported"""
    print("\n📦 Testing Project API Imports...")
    
    try:
        # Test simplified project API
        from src.api.v1.projects_simple import router as projects_simple_router
        print("✅ Simple project API imported successfully")
        
        # Test services
        from src.services.notification_service import NotificationService
        from src.services.file_service import FileService
        print("✅ Project services imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error importing project APIs: {e}")
        return False


def main():
    """Run all Phase 4 basic tests"""
    print("🚀 Phase 4 Project Management System - Simple Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(test_project_enums())
    results.append(test_project_models_import())
    results.append(test_project_schemas())
    results.append(test_project_api_imports())
    
    print("\n" + "=" * 60)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} tests passed!")
        print("🎉 Phase 4 foundation is ready for development!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("🔧 Some issues need to be resolved")
    
    print("=" * 60)


if __name__ == "__main__":
    main()