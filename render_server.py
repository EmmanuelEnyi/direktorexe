"""
render_server.py - Headless server for Render deployment

This module provides a headless version of the Direktor EXE Scrabble Tournament Manager
that runs only the Flask web server component without the GUI.
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Try to locate the database_utils module
possible_paths = [
    '.',
    './data',
    './utils',
    './database'
]

for path in possible_paths:
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), path))

# Print the current directory and Python path for debugging
print("Current directory:", os.getcwd())
print("Python path:", sys.path)

# List files in the current directory for debugging
print("Files in current directory:", os.listdir('.'))

try:
    # Try to import the necessary modules
    from schema import initialize_database
    from server import run_flask_app
    
    print("Imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
    # Try alternative imports
    try:
        print("Trying alternative imports...")
        import schema
        import server
        
        initialize_database = schema.initialize_database
        run_flask_app = server.run_flask_app
        print("Alternative imports successful!")
    except ImportError as e2:
        print(f"Alternative import error: {e2}")
        sys.exit(1)

if __name__ == "__main__":
    print("Initializing database...")
    try:
        initialize_database()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
    
    print("Starting Flask server...")
    try:
        # Instead of running in a thread, run directly
        run_flask_app()
    except Exception as e:
        print(f"Error running Flask server: {e}")

