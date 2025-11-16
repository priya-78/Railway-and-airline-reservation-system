from app import app, db
from models import User

def create_admin_user():
    """Create an admin user if none exists"""
    with app.app_context():
        try:
            # Check if admin already exists
            admin = User.query.filter_by(is_admin=True).first()
            if admin:
                print(f"Admin user already exists: {admin.username}")
                print(f"Email: {admin.email}")
                return
            
            # Create new admin user
            admin = User(
                username="admin",
                email="admin@goVoyage.com",
                first_name="Admin",
                last_name="User",
                phone="1234567890",
                is_admin=True
            )
            admin.set_password("admin123")
            
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user created successfully!")
            print("Username: admin")
            print("Email: admin@goVoyage.com")
            print("Password: admin123")
            print("You can now log in using these credentials.")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {str(e)}")

if __name__ == "__main__":
    create_admin_user()