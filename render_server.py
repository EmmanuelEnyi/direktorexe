"""
render_server.py - Headless server for Render deployment

This module provides a headless version of the Direktor EXE Scrabble Tournament Manager
that runs only the Flask web server component without the GUI.
"""

import os
from schema import initialize_database
from server import run_flask_app

if __name__ == "__main__":
    print("Initializing database...")
    initialize_database()
    
    print("Starting Flask server...")
    # Instead of running in a thread, run directly
    run_flask_app()

