# This is the main entry point for the application
# All configuration is in app.py

# Import the app instance from app.py
from app import app

# Run the app if this script is executed directly
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
