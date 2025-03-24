"""
pairings.py - Pairing algorithms for Direktor EXE Scrabble Tournament Manager

This module contains all the pairing algorithms used in the tournament manager,
including Round Robin, Random Pairing, King of the Hills, Australian Draw, and
Lagged Australian.
"""

import random

def round_robin(players):
    """
    Given a list of player names, generate a round-robin pairing list.
    Each player will play against every other player once.
    
    Args:
        players (list): List of player names
        
    Returns:
        list: List of tuples containing player pairings
    """
    pairings = []
    num_players = len(players)
    for i in range(num_players):
        for j in range(i + 1, num_players):
            pairings.append((players[i], players[j]))
    return pairings

def round_robin_rounds(players):
    """
    Generate a round-robin schedule where each round contains pairings
    such that each player plays exactly once per round.
    
    Args:
        players (list): List of player names
        
    Returns:
        list: List of rounds, where each round is a list of pairings
    """
    players = players[:]
    if len(players) % 2 == 1:
        players.append("BYE")
    n = len(players)
    rounds = []
    for i in range(n - 1):
        round_pairs = []
        for j in range(n // 2):
            round_pairs.append((players[j], players[n - 1 - j]))
        players.insert(1, players.pop())
        rounds.append(round_pairs)
    return rounds

def assign_firsts(rounds):
    """
    Assign which player goes first in each pairing, trying to balance
    the number of times each player goes first.
    
    Args:
        rounds (list): List of rounds with pairings
        
    Returns:
        list: List of rounds with pairings and first player assigned
    """
    first_count = {}
    for rnd in rounds:
        for p1, p2 in rnd:
            if p1 != "BYE":
                first_count[p1] = first_count.get(p1, 0)
            if p2 != "BYE":
                first_count[p2] = first_count.get(p2, 0)
    
    assigned_rounds = []
    for rnd in rounds:
        assigned = []
        for p1, p2 in rnd:
            if p1 == "BYE" or p2 == "BYE":
                assigned.append((p1, p2, p1 if p1 != "BYE" else p2))
            else:
                count1 = first_count.get(p1, 0)
                count2 = first_count.get(p2, 0)
                if count1 < count2:
                    first = p1
                elif count2 < count1:
                    first = p2
                else:
                    first = random.choice([p1, p2])
                first_count[first] += 1
                assigned.append((p1, p2, first))
        assigned_rounds.append(assigned)
    return assigned_rounds

def random_pairings(players):
    """
    Generate random pairings for a list of players.
    
    Args:
        players (list): List of player tuples (id, name, rating, etc.)
        
    Returns:
        list: List of tuples containing player pairings and first player
    """
    names = [p[1] for p in players]
    random.shuffle(names)
    if len(names) % 2 == 1:
        names.append("BYE")
    pairings = []
    for i in range(0, len(names), 2):
        p1 = names[i]
        p2 = names[i+1]
        if p1 == "BYE" or p2 == "BYE":
            first = p1 if p1 != "BYE" else p2
        else:
            first = random.choice([p1, p2])
        pairings.append((p1, p2, first))
    return pairings

def king_of_the_hills_pairings(players):
    """
    Generate pairings based on player standings (King of the Hills).
    
    Args:
        players (list): List of player tuples (id, name, rating, wins, losses, spread, etc.)
        
    Returns:
        list: List of tuples containing player pairings and first player
    """
    sorted_players = sorted(players, key=lambda p: (p[3], p[5]), reverse=True)
    names = [p[1] for p in sorted_players]
    if len(names) % 2 == 1:
        names.append("BYE")
    pairings = []
    for i in range(0, len(names), 2):
        p1 = names[i]
        p2 = names[i+1]
        first = p1  # Top player goes first
        pairings.append((p1, p2, first))
    return pairings

def has_played(player1, player2, completed_rounds):
    """
    Check if two players have already played against each other.
    
    Args:
        player1 (str): First player's name
        player2 (str): Second player's name
        completed_rounds (dict): Dictionary of completed rounds
        
    Returns:
        bool: True if players have played, False otherwise
    """
    for rnd in completed_rounds.values():
        for pairing in rnd:
            if set(pairing[:2]) == set([player1, player2]):
                return True
    return False

def australian_draw_pairings(players, completed_rounds):
    """
    Generate pairings using the Australian Draw system.
    
    Args:
        players (list): List of player tuples
        completed_rounds (dict): Dictionary of completed rounds
        
    Returns:
        list: List of tuples containing player pairings and first player
    """
    sorted_players = sorted(players, key=lambda p: (p[3], p[5]), reverse=True)
    pairings = []
    used = [False] * len(sorted_players)
    i = 0
    while i < len(sorted_players):
        if used[i]:
            i += 1
            continue
        p1 = sorted_players[i][1]
        paired = False
        for j in range(i+1, len(sorted_players)):
            if not used[j]:
                p2 = sorted_players[j][1]
                if not has_played(p1, p2, completed_rounds):
                    pairings.append((p1, p2, random.choice([p1, p2])))
                    used[i] = True
                    used[j] = True
                    paired = True
                    break
        if not paired:
            for j in range(i+1, len(sorted_players)):
                if not used[j]:
                    p2 = sorted_players[j][1]
                    pairings.append((p1, p2, random.choice([p1, p2])))
                    used[i] = True
                    used[j] = True
                    break
        i += 1
    return pairings

def compute_lagged_standings(players, results_by_round, completed_rounds, round_limit):
    """
    Compute standings based on results up to a certain round.
    
    Args:
        players (list): List of player tuples
        results_by_round (dict): Dictionary of results by round
        completed_rounds (dict): Dictionary of completed rounds
        round_limit (int): Maximum round to consider
        
    Returns:
        list: Sorted list of players based on lagged standings
    """
    stats = {}
    for p in players:
        stats[p[1]] = {"wins": 0, "spread": 0}
    
    for r in sorted(results_by_round.keys()):
        if r > round_limit:
            break
        pairings = completed_rounds.get(r, [])
        round_results = results_by_round.get(r, [])
        for i, pairing in enumerate(pairings):
            if i < len(round_results) and round_results[i] is not None and pairing:
                score1, score2 = round_results[i]
                p1, p2, _ = pairing
                if score1 > score2:
                    stats[p1]["wins"] += 1
                    stats[p1]["spread"] += (score1 - score2)
                    stats[p2]["spread"] -= (score1 - score2)
                elif score2 > score1:
                    stats[p2]["wins"] += 1
                    stats[p2]["spread"] += (score2 - score1)
                    stats[p1]["spread"] -= (score2 - score1)
                else:
                    stats[p1]["wins"] += 0.5
                    stats[p2]["wins"] += 0.5
    
    sorted_players = sorted(players, key=lambda p: (stats[p[1]]["wins"], stats[p[1]]["spread"]), reverse=True)
    return sorted_players

def lagged_australian_pairings(players, current_round_number, results_by_round, completed_rounds):
    """
    Generate pairings using the Lagged Australian system.
    
    Args:
        players (list): List of player tuples
        current_round_number (int): Current round number
        results_by_round (dict): Dictionary of results by round
        completed_rounds (dict): Dictionary of completed rounds
        
    Returns:
        list: List of tuples containing player pairings and first player
    """
    if current_round_number < 3:
        return random_pairings(players)
    
    standings = compute_lagged_standings(players, results_by_round, completed_rounds, current_round_number - 1)
    pairings = []
    used = [False] * len(standings)
    i = 0
    while i < len(standings):
        if used[i]:
            i += 1
            continue
        p1 = standings[i][1]
        paired = False
        for j in range(i+1, len(standings)):
            if not used[j]:
                p2 = standings[j][1]
                if not has_played(p1, p2, completed_rounds):
                    pairings.append((p1, p2, random.choice([p1, p2])))
                    used[i] = True
                    used[j] = True
                    paired = True
                    break
        if not paired:
            for j in range(i+1, len(standings)):
                if not used[j]:
                    p2 = standings[j][1]
                    pairings.append((p1, p2, random.choice([p1, p2])))
                    used[i] = True
                    used[j] = True
                    break
        i += 1
    return pairings

def generate_pairings_system(players, system="Round Robin", completed_rounds=None, current_round_number=0, results_by_round=None):
    """
    Generate pairings based on the selected system.
    
    Args:
        players (list): List of player tuples
        system (str): Pairing system to use
        completed_rounds (dict): Dictionary of completed rounds
        current_round_number (int): Current round number
        results_by_round (dict): Dictionary of results by round
        
    Returns:
        list: List of tuples containing player pairings and first player
    """
    if completed_rounds is None:
        completed_rounds = {}
    if results_by_round is None:
        results_by_round = {}
        
    if system == "Round Robin":
        names = [p[1] for p in players]
        full_round_robin_schedule = assign_firsts(round_robin_rounds(names))
        return full_round_robin_schedule
    elif system == "Random Pairing":
        return random_pairings(players)
    elif system == "King of the Hills Pairing":
        return king_of_the_hills_pairings(players)
    elif system == "Australian Draw":
        return australian_draw_pairings(players, completed_rounds)
    elif system == "Lagged Australian":
        return lagged_australian_pairings(players, current_round_number, results_by_round, completed_rounds)
    else:
        raise ValueError("Invalid pairing system specified.")

