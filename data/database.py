"""
database.py

This module contains functions to connect to and set up the SQLite database
for Direktor EXE – Scrabble Tournament Manager.

Tables:
  - tournaments: Stores tournament details.
  - players: Stores player information associated with a tournament.
  - results: Stores match results submitted via the remote endpoint.
  
Note:
  - The players table includes extra fields: 'player_number' (which resets
    per tournament) and 'country' (for flag display).
  - Adjust the table schemas and field types as needed.
"""

import sqlite3
import os

DATABASE_FILE = "direktor.db"

def create_connection():
    """Create and return a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_FILE)
    return conn

def create_tables(conn):
    """Create the necessary tables if they do not already exist."""
    cursor = conn.cursor()

    # Create tournaments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            venue TEXT NOT NULL,
            shareable_link TEXT,
            mode TEXT,
            teams TEXT,
            team_size INTEGER
        )
    """)

    # Create players table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            rating INTEGER,
            wins REAL DEFAULT 0,
            losses REAL DEFAULT 0,
            spread INTEGER DEFAULT 0,
            last_result TEXT,
            scorecard TEXT,
            team TEXT,
            player_number INTEGER,
            country TEXT,
            tournament_id INTEGER,
            FOREIGN KEY(tournament_id) REFERENCES tournaments(id)
        )
    """)

    # Create results table for remote match submissions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT UNIQUE,
            player1_score INTEGER,
            player2_score INTEGER
        )
    """)

    conn.commit()

def insert_tournament(conn, name, date, venue):
    """
    Insert a new tournament into the tournaments table.
    
    Returns:
      The tournament ID of the newly inserted tournament.
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tournaments (name, date, venue, shareable_link, mode, teams, team_size)
        VALUES (?, ?, ?, '', '', '', 0)
    """, (name, date, venue))
    conn.commit()
    return cursor.lastrowid

def insert_player(conn, name, rating, tournament_id, team="", country=""):
    """
    Insert a new player into the players table.
    The player's number is set based on the count of players already registered in the tournament.
    
    Returns:
      The player ID of the newly inserted player.
    """
    cursor = conn.cursor()
    # Count the number of players already in this tournament to determine player_number
    cursor.execute("SELECT COUNT(*) FROM players WHERE tournament_id = ?", (tournament_id,))
    count = cursor.fetchone()[0]
    player_number = count + 1

    cursor.execute("""
        INSERT INTO players 
        (name, rating, wins, losses, spread, last_result, scorecard, team, player_number, country, tournament_id)
        VALUES (?, ?, 0, 0, 0, '', '', ?, ?, ?, ?)
    """, (name, rating, team, player_number, country, tournament_id))
    conn.commit()
    return cursor.lastrowid

def get_all_tournaments(conn):
    """Return a list of all tournaments."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tournaments")
    return cursor.fetchall()

def get_all_players(conn):
    """Return a list of all players."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players")
    return cursor.fetchall()

def get_players_for_tournament(tournament_id):
    """Return a list of players for a specific tournament."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE tournament_id = ?", (tournament_id,))
    players = cursor.fetchall()
    conn.close()
    return players

if __name__ == "__main__":
    # For testing purposes: create the database and tables.
    conn = create_connection()
    create_tables(conn)
    conn.close()
    print("Database and tables created successfully.")
