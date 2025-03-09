import sqlite3

def create_connection(db_file="direktor.db"):
    """Create and return a connection to the SQLite database."""
    conn = sqlite3.connect(db_file)
    return conn

def create_tables(conn):
    """Create the required tables if they do not already exist."""
    cursor = conn.cursor()
    # Create the tournaments table with a shareable_link column.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            venue TEXT NOT NULL,
            shareable_link TEXT
        );
    """)
    # Create the players table with tournament_id, player_number, and country columns.
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
        );
    """)
    # Create a results table for remote result submissions.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            match_id TEXT PRIMARY KEY,
            player1_score INTEGER,
            player2_score INTEGER
        );
    """)
    conn.commit()

def insert_tournament(conn, name, date, venue):
    """Insert a new tournament and return its database-generated ID."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tournaments (name, date, venue)
        VALUES (?, ?, ?)
    """, (name, date, venue))
    conn.commit()
    return cursor.lastrowid

def insert_player(conn, name, rating, tournament_id, team, player_number, country):
    """
    Insert a new player with the given data.
    player_number should be the sequential number for this tournament.
    """
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO players (name, rating, tournament_id, team, player_number, country)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, rating, tournament_id, team, player_number, country))
    conn.commit()
    return cursor.lastrowid

def get_all_tournaments(conn):
    """Return all tournaments in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tournaments")
    return cursor.fetchall()

def get_all_players(conn):
    """Return all players in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players")
    return cursor.fetchall()

def get_players_for_tournament(tournament_id):
    """Return all players registered for a given tournament."""
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE tournament_id = ?", (tournament_id,))
    players = cursor.fetchall()
    conn.close()
    return players

# If this file is run as a script, create the database and tables.
if __name__ == "__main__":
    conn = create_connection()
    create_tables(conn)
    conn.close()
    print("Database and tables created successfully.")
