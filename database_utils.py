"""
database_utils.py - Database utility functions for Direktor EXE Scrabble Tournament Manager

This module provides database connection and query execution utilities.
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import DictCursor

def create_connection_postgres(database_url):
    """Create a database connection to a PostgreSQL database."""
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        return None

def get_db_connection():
    """Get the appropriate database connection based on environment."""
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # We're on Render, use PostgreSQL
        return create_connection_postgres(database_url)
    else:
        # We're local, use SQLite
        return sqlite3.connect("direktor.db")

def execute_query(query, params=None, fetch=None):
    """Execute a query with proper connection handling."""
    conn = get_db_connection()
    try:
        if isinstance(conn, sqlite3.Connection):
            cursor = conn.cursor()
            # For SQLite, replace RETURNING with a separate SELECT
            if "RETURNING" in query:
                # Execute the insert without RETURNING
                insert_query = query.split("RETURNING")[0]
                cursor.execute(insert_query, params)
                # Get the last inserted ID
                cursor.execute("SELECT last_insert_rowid()")
                result = cursor.fetchone()
                conn.commit()
                return result
        else:
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute(query, params)
            
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            result = None
            conn.commit()
            
        cursor.close()
        return result
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if conn:
            conn.close()

