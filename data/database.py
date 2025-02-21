import sqlite3

def create_connection(db_file="direktor.db"):
    """Create a connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("Connected to SQLite")
    except sqlite3.Error as e:
        print("SQLite error:", e)
    return conn

def create_tables(conn):
    """Create or update tables for tournaments and players."""
    try:
        cursor = conn.cursor()
        # Create the tournaments table with a venue column.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT,
                venue TEXT,
                link TEXT
            );
        """)
        # Create the players table with a tournament-specific player ID.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER,
                tournament_player_id INTEGER,
                name TEXT NOT NULL,
                rating INTEGER DEFAULT 1000,
                wins REAL DEFAULT 0,
                losses REAL DEFAULT 0,
                spread INTEGER DEFAULT 0,
                last_result TEXT,
                scorecard TEXT,
                team TEXT,
                FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
                UNIQUE(tournament_id, tournament_player_id)
            );
        """)
        conn.commit()
        print("Tables created/updated successfully")
    except sqlite3.Error as e:
        print("Error creating/updating tables:", e)

def insert_player(conn, name, rating=1000, tournament_id=None, team=""):
    """
    Insert a new player into the players table.
    Computes a tournament-specific player ID that resets for each tournament.
    Returns the tournament-specific ID.
    """
    try:
        cursor = conn.cursor()
        if tournament_id is not None:
            cursor.execute("SELECT COUNT(*) FROM players WHERE tournament_id = ?", (tournament_id,))
            count = cursor.fetchone()[0]
            tournament_player_id = count + 1
        else:
            tournament_player_id = 1
        cursor.execute("""
            INSERT INTO players (tournament_id, tournament_player_id, name, rating, team)
            VALUES (?, ?, ?, ?, ?)
        """, (tournament_id, tournament_player_id, name, rating, team))
        conn.commit()
        return tournament_player_id
    except sqlite3.Error as e:
        print("Error inserting player:", e)
        return None

def insert_tournament(conn, name, date, venue=""):
    """
    Insert a new tournament into the tournaments table.
    Venue is stored along with the name and date.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tournaments (name, date, venue) VALUES (?, ?, ?)
        """, (name, date, venue))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        print("Error inserting tournament:", e)
        return None

def get_all_players(conn):
    """Retrieve all players from the database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM players")
        return cursor.fetchall()
    except sqlite3.Error as e:
        print("Error retrieving players:", e)
        return []

def get_all_tournaments(conn):
    """Retrieve all tournaments from the database."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tournaments")
        return cursor.fetchall()
    except sqlite3.Error as e:
        print("Error retrieving tournaments:", e)
        return []

if __name__ == "__main__":
    conn = create_connection()
    create_tables(conn)
    conn.close()
