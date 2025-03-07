import sqlite3

def create_connection(db_file="direktor.db"):
    """Create a database connection to the SQLite database specified by db_file."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print("Error connecting to database:", e)
    return conn

def create_tables(conn):
    """Create tables in the database if they do not exist."""
    try:
        cursor = conn.cursor()
        # Create the tournaments table with a shareable_link column.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                date TEXT,
                venue TEXT,
                shareable_link TEXT
            )
        """)
        # Create the players table with a player_number column.
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
                tournament_id INTEGER,
                player_number INTEGER,
                FOREIGN KEY(tournament_id) REFERENCES tournaments(id)
            )
        """)
        # Create a results table (for remote submissions)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE,
                player1_score INTEGER,
                player2_score INTEGER
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        print("Error creating tables:", e)

def insert_tournament(conn, name, date, venue):
    """Insert a new tournament into the tournaments table."""
    try:
        sql = "INSERT INTO tournaments (name, date, venue) VALUES (?, ?, ?)"
        cur = conn.cursor()
        cur.execute(sql, (name, date, venue))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print("Error inserting tournament:", e)
        return None

def insert_player(conn, name, rating, tournament_id, team, player_number):
    """
    Insert a new player into the players table.
    The player_number parameter ensures that player numbering resets for each tournament.
    """
    try:
        sql = """INSERT INTO players (name, rating, tournament_id, team, player_number)
                 VALUES (?, ?, ?, ?, ?)"""
        cur = conn.cursor()
        cur.execute(sql, (name, rating, tournament_id, team, player_number))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print("Error inserting player:", e)
        return None

def get_all_tournaments(conn):
    """Return all tournaments from the tournaments table."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM tournaments")
    return cur.fetchall()

def get_all_players(conn):
    """Return all players from the players table."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM players")
    return cur.fetchall()

def get_players_for_tournament(tournament_id):
    """Return all players for a given tournament_id."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE tournament_id = ?", (tournament_id,))
    players = cur.fetchall()
    conn.close()
    return players

if __name__ == "__main__":
    # For testing purposes, create a connection and initialize tables.
    conn = create_connection()
    if conn is not None:
        create_tables(conn)
        print("Tables created/updated successfully")
        conn.close()
    else:
        print("Error! Cannot create the database connection.")
