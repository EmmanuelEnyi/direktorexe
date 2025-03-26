from database_utils import execute_query

def insert_tournament(name, date, venue):
    """Insert a new tournament into the database."""
    query = """
    INSERT INTO tournaments (name, date, venue)
    VALUES (?, ?, ?)
    RETURNING id
    """
    result = execute_query(query, (name, date, venue), fetch="one")
    return result[0] if result else None

def update_tournament_link(tournament_id, link):
    """Update the shareable link for a tournament."""
    query = """
    UPDATE tournaments
    SET shareable_link = ?
    WHERE id = ?
    """
    execute_query(query, (link, tournament_id))

def get_tournament(tournament_id):
    """Get tournament details by ID."""
    query = """
    SELECT id, name, date, venue, shareable_link
    FROM tournaments
    WHERE id = ?
    """
    return execute_query(query, (tournament_id,), fetch="one")

def get_all_tournaments():
    """Get all tournaments."""
    query = """
    SELECT id, name, date, venue, shareable_link
    FROM tournaments
    ORDER BY date DESC
    """
    return execute_query(query, fetch="all")

def insert_player(name, rating, tournament_id, team="", country=""):
    """Insert a new player into the database."""
    query = """
    INSERT INTO players (name, rating, tournament_id, team, country)
    VALUES (?, ?, ?, ?, ?)
    RETURNING id
    """
    result = execute_query(query, (name, rating, tournament_id, team, country), fetch="one")
    return result[0] if result else None

def get_players_for_tournament(tournament_id):
    """Get all players for a specific tournament."""
    query = """
    SELECT id, name, rating, wins, losses, spread, last_result, scorecard, team, player_number, country
    FROM players
    WHERE tournament_id = ?
    ORDER BY name
    """
    return execute_query(query, (tournament_id,), fetch="all")

def update_player_stats(player_id, wins, losses, spread, last_result, scorecard):
    """Update player statistics."""
    query = """
    UPDATE players
    SET wins = ?, losses = ?, spread = ?, last_result = ?, scorecard = ?
    WHERE id = ?
    """
    execute_query(query, (wins, losses, spread, last_result, scorecard, player_id))