"""
Create a test user manually to bypass bcrypt issues
"""

import sys
import os
from datetime import datetime

# Add the backend src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.orm import sessionmaker
from src.core.database import sync_engine
from src.models.user import User, UserRole

# Create session
SessionLocal = sessionmaker(bind=sync_engine)

def create_test_user():
    """Create a simple test user for Phase 4 testing"""
    print("Creating test user for Phase 4...")
    
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == "testuser").first()
        
        if existing_user:
            print(f"✅ Test user already exists: {existing_user.username} (ID: {existing_user.id})")
            return existing_user.id
        
        # Create new test user with simple password
        test_user = User(
            username="testuser",
            email="testuser@example.com",
            role=UserRole.DEVELOPER,
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/0lNWW9a9y0xUKD6pu",  # "password"
            is_email_verified=True
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"✅ Created test user: {test_user.username} (ID: {test_user.id})")
        print("   Username: testuser")
        print("   Password: password")
        
        return test_user.id
        
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        db.rollback()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    user_id = create_test_user()
    if user_id:
        print(f"\n✅ Test user ready (ID: {user_id})")
        print("You can now use username: testuser, password: password for testing")
    else:
        print("\n❌ Failed to create test user")