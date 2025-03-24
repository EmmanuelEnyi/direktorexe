"""
utils.py - Utility functions for Direktor EXE Scrabble Tournament Manager

This module provides utility functions used throughout the application.
"""

import os
import re
import socket
import random
import string
import json
from datetime import datetime

def get_local_ip():
    """
    Get the local IP address of the machine.
    
    Returns:
        str: Local IP address
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def sanitize_filename(filename):
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    return re.sub(r'[\\/*?:"<>|]', "", filename).replace(" ", "_")

def get_tournament_folder(tournament_name):
    """
    Get the folder path for a tournament.
    
    Args:
        tournament_name (str): Tournament name
        
    Returns:
        str: Path to tournament folder
    """
    rendered_dir = os.path.join(os.getcwd(), "rendered", "tournaments")
    os.makedirs(rendered_dir, exist_ok=True)
    folder_name = sanitize_filename(tournament_name)
    tournament_folder = os.path.join(rendered_dir, folder_name)
    os.makedirs(tournament_folder, exist_ok=True)
    return tournament_folder

def generate_match_id(round_number, match_number):
    """
    Generate a match ID.
    
    Args:
        round_number (int): Round number
        match_number (int): Match number
        
    Returns:
        str: Match ID in format "R{round_number}-M{match_number}"
    """
    return f"R{round_number}-M{match_number}"

def generate_random_id(length=8):
    """
    Generate a random ID.
    
    Args:
        length (int): Length of the ID
        
    Returns:
        str: Random ID
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def format_datetime(dt=None):
    """
    Format a datetime object as a string.
    
    Args:
        dt (datetime, optional): Datetime object. Defaults to current time.
        
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def load_json_file(file_path, default=None):
    """
    Load a JSON file.
    
    Args:
        file_path (str): Path to JSON file
        default (any, optional): Default value if file doesn't exist. Defaults to None.
        
    Returns:
        dict: Loaded JSON data or default value
    """
    if not os.path.exists(file_path):
        return default if default is not None else {}
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save_json_file(file_path, data):
    """
    Save data to a JSON file.
    
    Args:
        file_path (str): Path to JSON file
        data (dict): Data to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def recalculate_player_stats(players, completed_rounds, results_by_round):
    """
    Recalculate player statistics based on match results.
    
    Args:
        players (list): List of player tuples
        completed_rounds (dict): Dictionary of completed rounds
        results_by_round (dict): Dictionary of results by round
        
    Returns:
        list: Updated player list with recalculated stats
    """
    # Reset player stats
    player_stats = {}
    for player in players:
        player_name = player[1]
        player_stats[player_name] = {
            "wins": 0,
            "losses": 0,
            "spread": 0,
            "last_result": "",
            "scorecard": []
        }
    
    # Process results by round
    for round_num in sorted(results_by_round.keys()):
        round_pairings = completed_rounds.get(round_num, [])
        round_results = results_by_round.get(round_num, [])
        
        for i, pairing in enumerate(round_pairings):
            if i >= len(round_results) or round_results[i] is None:
                continue
                
            p1, p2, _ = pairing
            score1, score2 = round_results[i]
            
            # Skip BYE pairings
            if p1 == "BYE" or p2 == "BYE":
                continue
                
            # Update player 1 stats
            if score1 > score2:
                player_stats[p1]["wins"] += 1
                player_stats[p1]["spread"] += (score1 - score2)
                player_stats[p1]["last_result"] = f"W {score1}-{score2}"
                player_stats[p1]["scorecard"].append({
                    "round": round_num,
                    "opponent": p2,
                    "result": f"W {score1}-{score2}",
                    "cumulative": player_stats[p1]["spread"]
                })
            elif score1 < score2:
                player_stats[p1]["losses"] += 1
                player_stats[p1]["spread"] -= (score2 - score1)
                player_stats[p1]["last_result"] = f"L {score1}-{score2}"
                player_stats[p1]["scorecard"].append({
                    "round": round_num,
                    "opponent": p2,
                    "result": f"L {score1}-{score2}",
                    "cumulative": player_stats[p1]["spread"]
                })
            else:  # Tie
                player_stats[p1]["wins"] += 0.5
                player_stats[p1]["losses"] += 0.5
                player_stats[p1]["last_result"] = f"T {score1}-{score2}"
                player_stats[p1]["scorecard"].append({
                    "round": round_num,
                    "opponent": p2,
                    "result": f"T {score1}-{score2}",
                    "cumulative": player_stats[p1]["spread"]
                })
                
            # Update player 2 stats
            if score2 > score1:
                player_stats[p2]["wins"] += 1
                player_stats[p2]["spread"] += (score2 - score1)
                player_stats[p2]["last_result"] = f"W {score2}-{score1}"
                player_stats[p2]["scorecard"].append({
                    "round": round_num,
                    "opponent": p1,
                    "result": f"W {score2}-{score1}",
                    "cumulative": player_stats[p2]["spread"]
                })
            elif score2 < score1:
                player_stats[p2]["losses"] += 1
                player_stats[p2]["spread"] -= (score1 - score2)
                player_stats[p2]["last_result"] = f"L {score2}-{score1}"
                player_stats[p2]["scorecard"].append({
                    "round": round_num,
                    "opponent": p1,
                    "result": f"L {score2}-{score1}",
                    "cumulative": player_stats[p2]["spread"]
                })
            else:  # Tie
                player_stats[p2]["wins"] += 0.5
                player_stats[p2]["losses"] += 0.5
                player_stats[p2]["last_result"] = f"T {score2}-{score1}"
                player_stats[p2]["scorecard"].append({
                    "round": round_num,
                    "opponent": p1,
                    "result": f"T {score2}-{score1}",
                    "cumulative": player_stats[p2]["spread"]
                })
    
    # Update player tuples with new stats
    updated_players = []
    for player in players:
        player_name = player[1]
        stats = player_stats.get(player_name, {"wins": 0, "losses": 0, "spread": 0, "last_result": "", "scorecard": []})
        
        # Create a new player tuple with updated stats
        # (id, name, rating, wins, losses, spread, last_result, scorecard, team, player_number, country)
        updated_player = (
            player[0],  # id
            player[1],  # name
            player[2],  # rating
            stats["wins"],  # wins
            stats["losses"],  # losses
            stats["spread"],  # spread
            stats["last_result"],  # last_result
            json.dumps(stats["scorecard"]),  # scorecard
            player[8] if len(player) > 8 else "",  # team
            player[9] if len(player) > 9 else 1,  # player_number
            player[10] if len(player) > 10 else ""  # country
        )
        updated_players.append(updated_player)
    
    return updated_players

