"""
database.py - Database operations for Direktor EXE Scrabble Tournament Manager

This module provides functions for interacting with the tournament database.
"""

from database_utils import execute_query

def create_connection():
    """Legacy function for backward compatibility."""
    from database_utils import get_db_connection
    return get_db_connection()

def create_tables(conn):
    """Legacy function for backward compatibility."""
    from schema import initialize_database
    initialize_database()

def insert_tournament(conn, name, date, venue):
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

def insert_player(conn, name, rating, tournament_id, team="", country=""):
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

