from database_utils import get_db_connection, execute_query
import os

def init_sqlite_schema():
    """Initialize SQLite schema."""
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
        """
    ]
    
    for query in queries:
        execute_query(query)

def init_postgres_schema():
    """Initialize PostgreSQL schema."""
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
        """
    ]
    
    for query in queries:
        execute_query(query)

def initialize_database():
    """Initialize the appropriate database schema."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # We're on Render, use PostgreSQL
        init_postgres_schema()
    else:
        # We're local, use SQLite
        init_sqlite_schema()