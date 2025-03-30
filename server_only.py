"""
server_only.py - Standalone Flask server for Render deployment

This module provides a simplified version of the Direktor EXE Scrabble Tournament Manager
that runs only the Flask web server component without the GUI.
"""

import os
import sys

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Print the current directory and Python path for debugging
print("Current directory:", os.getcwd())
print("Python path:", sys.path)

# List files in the current directory for debugging
print("Files in current directory:", os.listdir('.'))

try:
    # Try to import the necessary modules
    from database_utils import execute_query, get_db_connection
    from schema import initialize_database
    from server import run_flask_app
    
    print("Imports successful!")
except ImportError as e:
    print(f"Import error: {e}")
    # Try alternative imports
    try:
        print("Trying alternative imports...")
        import server
        
        run_flask_app = server.run_flask_app
        print("Alternative imports successful!")
    except ImportError as e2:
        print(f"Alternative import error: {e2}")
        sys.exit(1)

if __name__ == "__main__":
    print("Initializing database...")
    try:
        # Try to initialize the database
        initialize_database()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        # Try to create tables directly
        try:
            print("Trying to create tables directly...")
            conn = get_db_connection()
            
            # Define the queries based on database type
            database_url = os.environ.get("DATABASE_URL")
            if database_url:
                # PostgreSQL queries
                queries = [
                    """
                    CREATE TABLE IF NOT EXISTS tournaments (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        date TEXT NOT NULL,
                        venue TEXT,
                        shareable_link TEXT
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS players (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        rating INTEGER,
                        tournament_id INTEGER,
                        wins REAL DEFAULT 0,
                        losses REAL DEFAULT 0,
                        spread INTEGER DEFAULT 0,
                        last_result TEXT,
                        scorecard TEXT,
                        team TEXT,
                        player_number INTEGER DEFAULT 1,
                        country TEXT,
                        FOREIGN KEY (tournament_id) REFERENCES tournaments (id)
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS results (
                        id SERIAL PRIMARY KEY,
                        match_id TEXT NOT NULL,
                        player1_score INTEGER NOT NULL,
                        player2_score INTEGER NOT NULL,
                        tournament TEXT NOT NULL,
                        submission_time TEXT NOT NULL
                    )
                    """
                ]
            else:
                # SQLite queries
                queries = [
                    """
                    CREATE TABLE IF NOT EXISTS tournaments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        date TEXT NOT NULL,
                        venue TEXT,
                        shareable_link TEXT
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS players (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        rating INTEGER,
                        tournament_id INTEGER,
                        wins REAL DEFAULT 0,
                        losses REAL DEFAULT 0,
                        spread INTEGER DEFAULT 0,
                        last_result TEXT,
                        scorecard TEXT,
                        team TEXT,
                        player_number INTEGER DEFAULT 1,
                        country TEXT,
                        FOREIGN KEY (tournament_id) REFERENCES tournaments (id)
                    )
                    """,
                    """
                    CREATE TABLE IF NOT EXISTS results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id TEXT NOT NULL,
                        player1_score INTEGER NOT NULL,
                        player2_score INTEGER NOT NULL,
                        tournament TEXT NOT NULL,
                        submission_time TEXT NOT NULL
                    )
                    """
                ]
            
            # Execute the queries
            for query in queries:
                execute_query(query)
                
            print("Tables created successfully!")
        except Exception as e3:
            print(f"Error creating tables: {e3}")
    
    print("Starting Flask server...")
    try:
        # Instead of running in a thread, run directly
        run_flask_app()
    except Exception as e:
        print(f"Error running Flask server: {e}")

