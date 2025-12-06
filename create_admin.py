# create_admin.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.crud.user import user as user_crud
from app.schemas.user import UserCreate
from app.core.config import settings

def create_admin_user():
    db = SessionLocal()
    try:
        if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
            print("❌ ADMIN_EMAIL and ADMIN_PASSWORD not set in .env file")
            return
        
        # Check if admin already exists
        admin_user = user_crud.get_by_email(db, email=settings.ADMIN_EMAIL)
        if admin_user:
            print(f"✅ Admin user already exists: {admin_user.email}")
            return
        
        # Create admin user
        admin_data = UserCreate(
            email=settings.ADMIN_EMAIL,
            username="admin",
            full_name="System Administrator",
            password=settings.ADMIN_PASSWORD
        )
        
        admin_user = user_crud.create(db, admin_data)
        admin_user.is_admin = True
        db.commit()
        
        print("✅ Admin user created successfully!")
        print(f"   Email: {admin_user.email}")
        print(f"   Username: {admin_user.username}")
        print(f"   Is Admin: {admin_user.is_admin}")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin_user()