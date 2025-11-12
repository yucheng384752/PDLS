"""
Test Phase 4 Project API endpoints
Tests the actual API functionality using FastAPI TestClient
"""

import sys
import os
import json
from datetime import datetime

# Add the backend src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from main import app

# Create test client
client = TestClient(app)


def get_test_token():
    """Get authentication token for testing"""
    print("🔐 Getting authentication token...")
    
    try:
        # Try to register a test user first
        register_data = {
            "username": "phase4_tester",
            "email": "test@test.com",
            "password": "test1234",  # 8 characters
            "role": "developer"
        }
        
        response = client.post("/api/v1/auth/register", json=register_data)
        if response.status_code == 201:
            print("✅ Test user registered successfully")
        elif response.status_code == 400 and "already exists" in response.text:
            print("ℹ️  Test user already exists, continuing...")
        else:
            print(f"⚠️  Registration response: {response.status_code} - {response.text}")
        
        # Login to get token
        login_data = {
            "username_or_email": "phase4_tester",
            "password": "test1234"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get("access_token")
            print(f"✅ Authentication successful, token length: {len(token) if token else 0}")
            return token
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error getting auth token: {e}")
        return None


def test_simple_project_api(token):
    """Test the simple project API endpoints"""
    print("\n📋 Testing Simple Project API...")
    
    if not token:
        print("❌ No authentication token available")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Test creating a project
        project_data = {
            "name": "Phase 4 Test Project",
            "description": "Testing project creation in Phase 4",
            "project_type": "software"
        }
        
        response = client.post("/api/v1/projects/simple", json=project_data, headers=headers)
        
        if response.status_code == 201:
            project = response.json()
            project_id = project.get("id")
            print(f"✅ Project created successfully: '{project['name']}' (ID: {project_id})")
            
            # Test getting the project
            response = client.get(f"/api/v1/projects/simple/{project_id}", headers=headers)
            
            if response.status_code == 200:
                retrieved_project = response.json()
                print(f"✅ Project retrieved: '{retrieved_project['name']}'")
                
                # Test updating the project
                update_data = {
                    "description": "Updated description for Phase 4 testing"
                }
                
                response = client.put(f"/api/v1/projects/simple/{project_id}", json=update_data, headers=headers)
                
                if response.status_code == 200:
                    updated_project = response.json()
                    print(f"✅ Project updated: '{updated_project['description']}'")
                    
                    # Test listing projects
                    response = client.get("/api/v1/projects/simple", headers=headers)
                    
                    if response.status_code == 200:
                        projects = response.json()
                        print(f"✅ Projects listed: {len(projects)} project(s) found")
                        
                        # Test deleting the project
                        response = client.delete(f"/api/v1/projects/simple/{project_id}", headers=headers)
                        
                        if response.status_code == 200:
                            print("✅ Project deleted successfully")
                            return True
                        else:
                            print(f"❌ Failed to delete project: {response.status_code}")
                    else:
                        print(f"❌ Failed to list projects: {response.status_code}")
                else:
                    print(f"❌ Failed to update project: {response.status_code}")
            else:
                print(f"❌ Failed to retrieve project: {response.status_code}")
        else:
            print(f"❌ Failed to create project: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing simple project API: {e}")
        
    return False


def test_health_check():
    """Test basic health check endpoint"""
    print("\n🏥 Testing Health Check...")
    
    try:
        response = client.get("/health")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error testing health check: {e}")
        
    return False


def main():
    """Run Phase 4 API tests"""
    print("🚀 Phase 4 Project Management API Tests")
    print("=" * 60)
    
    results = []
    
    # Test health check first
    results.append(test_health_check())
    
    # Get authentication token
    token = get_test_token()
    
    if token:
        # Test simple project API
        results.append(test_simple_project_api(token))
    else:
        print("❌ Cannot test project API without authentication")
        results.append(False)
    
    print("\n" + "=" * 60)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} API tests passed!")
        print("🎉 Phase 4 API is working correctly!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("🔧 Some API issues need to be resolved")
    
    print("=" * 60)


if __name__ == "__main__":
    main()