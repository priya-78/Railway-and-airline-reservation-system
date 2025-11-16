from app import app, db
from models import User

def delete_admin_user():
    """Delete existing admin users"""
    with app.app_context():
        try:
            admin = User.query.filter_by(is_admin=True).first()
            if admin:
                print(f"Deleting admin user: {admin.username} ({admin.email})")
                db.session.delete(admin)
                db.session.commit()
                print("Admin user deleted successfully")
            else:
                print("No admin user found to delete")
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting admin user: {str(e)}")

if __name__ == "__main__":
    delete_admin_user()