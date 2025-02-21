"""
Direktor EXE – Scrabble Tournament Manager
Full Updated main.py

New Features:
  1. A single toggle button now switches between General (default) and Team Round Robin modes.
  2. In General mode, if “Round Robin” is selected, the user is informed of the full schedule size and is prompted for how many rounds to play. The pairing schedule is then generated accordingly.
  3. The HTML output index page now lists separate links for each paired round (instead of one pairings link).
  4. The “Next game” column has been removed from the standings.
  5. The player scorecard now shows a table with round number, result, and cumulative spread.
  6. In General mode, the team dropdown is hidden on the player registration screen.

Author: Manuelito
"""

#####################################
# Imports and Dependencies
#####################################
import customtkinter as ctk
import os
import webbrowser
import sqlite3
import threading
import http.server
import socketserver
import socket
import random
from functools import partial
import json
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog

from ui.theme import apply_theme
from data.database import (
    create_connection, create_tables, insert_player,
    insert_tournament, get_all_tournaments, get_all_players
)

#####################################
# Global Variables and Mode Settings
#####################################
server_thread = None
HTTP_PORT = 8000

current_tournament_id = None      # Active tournament's DB ID
session_players = []              # For UI display
prize_table = []                  # List of prizes

# Modes: Only "General" and "Team Round Robin" exist; default is General.
tournament_mode = "General"
current_mode_view = "general"      # "general" or "team"

teams_list = []                   # For team mode only
team_size = 0                     # For team mode only (3 or 5)

# For pairing in General mode, the dropdown now includes "Round Robin", "Random Pairing", and "King of the Hills Pairing"
last_pairing_system = "Round Robin"
last_team_size = 3              

current_round_number = 0    # Latest round paired
completed_rounds = {}       # Dict mapping round number -> list of pairings for that round
results_by_round = {}       # Dict mapping round number -> list of (score1, score2) for each pairing

team_round_results = {}     # For team mode (if needed)

app = None                  # Main application window
status_label = None         # Status bar label
main_frame_global = None    # Main frame for tab view

#####################################
# Utility Functions
#####################################
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def run_http_server(port=HTTP_PORT):
    rendered_dir = os.path.join(os.getcwd(), "rendered")
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=rendered_dir)
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving HTTP at port {port}")
        httpd.serve_forever()

def start_http_server(port=HTTP_PORT):
    global server_thread
    if server_thread is None:
        server_thread = threading.Thread(target=run_http_server, args=(port,), daemon=True)
        server_thread.start()

def show_toast(parent, message, duration=2000):
    toast = ctk.CTkToplevel(parent)
    toast.geometry("300x50+500+300")
    toast.overrideredirect(True)
    label = ctk.CTkLabel(toast, text=message, font=("Arial", 12))
    label.pack(expand=True, fill="both")
    toast.after(duration, toast.destroy)

def update_status():
    global status_label, current_tournament_id
    if status_label:
        if current_tournament_id is not None:
            conn = create_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM tournaments WHERE id = ?", (current_tournament_id,))
            result = cursor.fetchone()
            conn.close()
            status_label.configure(text=result[0] if result else "No tournament loaded.")
        else:
            status_label.configure(text="No tournament loaded.")

def confirm_discard():
    global current_tournament_id, app
    if current_tournament_id is not None:
        answer = messagebox.askyesnocancel("Confirm", "Do you want to save the current tournament before proceeding?")
        if answer is None:
            return False
        if answer:
            save_current_tournament()
    return True

def quit_app():
    global app
    if messagebox.askyesno("Confirm Quit", "Are you sure you want to quit?"):
        app.destroy()

#####################################
# Database Functions
#####################################
def initialize_database():
    conn = create_connection()
    create_tables(conn)
    conn.close()

def get_players_for_tournament(tournament_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, rating, wins, losses, spread, last_result, scorecard, team FROM players WHERE tournament_id = ?", (tournament_id,))
    players = cursor.fetchall()
    conn.close()
    return players

def update_tournament_link(tournament_id, link):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournaments SET link = ? WHERE id = ?", (link, tournament_id))
    conn.commit()
    conn.close()

#####################################
# Save/Load Tournament Functions
#####################################
def save_current_tournament():
    global current_tournament_id, app, tournament_mode, teams_list, team_size, current_round_number, completed_rounds, results_by_round, last_pairing_system, last_team_size
    if current_tournament_id is None:
        show_toast(app, "No tournament to save.")
        return
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, venue, link FROM tournaments WHERE id = ?", (current_tournament_id,))
    tournament_data = cursor.fetchone()
    players = get_players_for_tournament(current_tournament_id)
    conn.close()
    if tournament_data is None:
        show_toast(app, "Tournament not found in database.")
        return
    data = {
        "tournament": {
            "id": tournament_data[0],
            "name": tournament_data[1],
            "date": tournament_data[2],
            "venue": tournament_data[3],
            "link": tournament_data[4],
            "mode": tournament_mode,
            "teams": teams_list,
            "team_size": team_size
        },
        "players": [
            {"id": p[0], "name": p[1], "rating": p[2], "wins": p[3], "losses": p[4], "spread": p[5],
             "last_result": p[6], "scorecard": p[7], "team": p[8]} for p in players
        ],
        "progress": {
            "current_round_number": current_round_number,
            "completed_rounds": completed_rounds,
            "results_by_round": results_by_round,
            "last_pairing_system": last_pairing_system,
            "last_team_size": last_team_size
        }
    }
    filename = fd.asksaveasfilename(defaultextension=".tou", filetypes=[("Tournament Files", "*.tou")])
    if filename:
        with open(filename, "w") as f:
            json.dump(data, f)
        show_toast(app, "Tournament saved successfully.")

def load_tournament():
    global current_tournament_id, session_players, app, tournament_mode, teams_list, team_size, current_round_number, completed_rounds, results_by_round, last_pairing_system, last_team_size
    if not confirm_discard():
        return
    filename = fd.askopenfilename(filetypes=[("Tournament Files", "*.tou")])
    if filename:
        with open(filename, "r") as f:
            data = json.load(f)
        tournament = data.get("tournament", {})
        players = data.get("players", [])
        progress = data.get("progress", {})
        if not tournament:
            show_toast(app, "Invalid tournament file.")
            return
        current_tournament_id = tournament.get("id")
        tournament_mode = tournament.get("mode", "General")
        teams_list = tournament.get("teams", [])
        team_size = tournament.get("team_size", 0)
        session_players = [
            (p["name"], p["rating"], p["wins"], p["losses"], p["spread"],
             p.get("last_result", ""), p.get("scorecard", ""), p.get("team", ""))
            for p in players
        ]
        current_round_number = progress.get("current_round_number", 0)
        completed_rounds = progress.get("completed_rounds", {})
        results_by_round = progress.get("results_by_round", {})
        last_pairing_system = progress.get("last_pairing_system", "Round Robin")
        last_team_size = progress.get("last_team_size", 3)
        show_toast(app, "Tournament loaded successfully.")
        update_status()

#####################################
# Helper Functions for Scorecard & Results
#####################################
def get_player_id_by_name(tournament_id, name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM players WHERE tournament_id = ? AND name = ?", (tournament_id, name))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def recalc_player_stats():
    """
    Recalculate all player stats and rebuild scorecards based on results_by_round and completed_rounds.
    """
    global current_tournament_id
    players = get_players_for_tournament(current_tournament_id)
    stats = {}
    for p in players:
        stats[p[1]] = {"wins": 0, "losses": 0, "spread": 0, "scorecard": []}
    for r in sorted(results_by_round.keys()):
        pairings = completed_rounds.get(r, [])
        round_results = results_by_round.get(r, [])
        for i, pairing in enumerate(pairings):
            if i < len(round_results) and pairing:
                score1, score2 = round_results[i]
                p1, p2, first = pairing
                if score1 == score2:
                    stats[p1]["wins"] += 0.5
                    stats[p2]["wins"] += 0.5
                    result_p1 = f"Tie ({score1}-{score2}) vs ({p2})"
                    result_p2 = f"Tie ({score2}-{score1}) vs ({p1})"
                elif score1 > score2:
                    stats[p1]["wins"] += 1
                    diff = score1 - score2
                    stats[p1]["spread"] += diff
                    stats[p2]["losses"] += 1
                    stats[p2]["spread"] -= diff
                    result_p1 = f"Win ({score1}-{score2}) vs ({p2})"
                    result_p2 = f"Loss ({score2}-{score1}) vs ({p1})"
                else:
                    stats[p2]["wins"] += 1
                    diff = score2 - score1
                    stats[p2]["spread"] += diff
                    stats[p1]["losses"] += 1
                    stats[p1]["spread"] -= diff
                    result_p2 = f"Win ({score2}-{score1}) vs ({p1})"
                    result_p1 = f"Loss ({score1}-{score2}) vs ({p2})"
                cum1 = stats[p1]["spread"]
                cum2 = stats[p2]["spread"]
                stats[p1]["scorecard"].append({"round": r, "result": result_p1, "cumulative": cum1})
                stats[p2]["scorecard"].append({"round": r, "result": result_p2, "cumulative": cum2})
    conn = create_connection()
    cursor = conn.cursor()
    for p in players:
        name = p[1]
        new_wins = stats[name]["wins"]
        new_losses = stats[name]["losses"]
        new_spread = stats[name]["spread"]
        new_scorecard = json.dumps(stats[name]["scorecard"])
        new_last_result = stats[name]["scorecard"][-1]["result"] if stats[name]["scorecard"] else ""
        cursor.execute("UPDATE players SET wins=?, losses=?, spread=?, last_result=?, scorecard=? WHERE tournament_id=? AND name=?",
                       (new_wins, new_losses, new_spread, new_last_result, new_scorecard, current_tournament_id, name))
    conn.commit()
    conn.close()

#####################################
# Pairing System Functions
#####################################
def round_robin_rounds(players):
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

def team_round_robin_pairings(players, team_size):
    teams = {}
    for p in players:
        team = p[8]
        if team not in teams:
            teams[team] = []
        teams[team].append(p[1])
    teams_ordered = []
    for team_name in teams_list:
        members = teams.get(team_name, [])
        if len(members) >= team_size:
            teams_ordered.append(members[:team_size])
        else:
            print(f"Warning: Team '{team_name}' has only {len(members)} players; skipping pairing for this team.")
    if len(teams_ordered) < 2:
        print("Not enough teams with full rosters for pairing.")
        return []
    rounds = round_robin_rounds(teams_ordered)
    team_rounds = []
    for rnd in rounds:
        round_info = []
        for teamA, teamB in rnd:
            starting = random.choice(["first", "second"])
            round_info.append((teamA, teamB, starting))
        team_rounds.append(round_info)
    return team_rounds

def random_pairings(players):
    names = [p[1] for p in players]
    random.shuffle(names)
    if len(names) % 2 == 1:
        names.append("BYE")
    pairings = []
    for i in range(0, len(names), 2):
        p1 = names[i]
        p2 = names[i+1]
        first = random.choice([p1, p2]) if p1 != "BYE" and p2 != "BYE" else (p1 if p1 != "BYE" else p2)
        pairings.append((p1, p2, first))
    return pairings

def king_of_the_hills_pairings(players):
    sorted_players = sorted(players, key=lambda x: (x[3], x[5]), reverse=True)
    names = [p[1] for p in sorted_players]
    if len(names) % 2 == 1:
        names.append("BYE")
    pairings = []
    for i in range(0, len(names), 2):
        p1 = names[i]
        p2 = names[i+1]
        pairings.append((p1, p2, p1))
    return pairings

def generate_general_pairings(players, system_choice):
    if system_choice == "Round Robin":
        names = [p[1] for p in players]
        rounds = round_robin_rounds(names)
        return assign_firsts(rounds)
    elif system_choice == "Random Pairing":
        return random_pairings(players)
    elif system_choice == "King of the Hills Pairing":
        return king_of_the_hills_pairings(players)
    else:
        raise ValueError("Invalid general pairing system choice.")

def generate_pairings_system(players, system="Round Robin", team_size=None):
    if system == "Team Round Robin":
        if team_size is None:
            raise ValueError("Team size must be specified for team round robin.")
        return team_round_robin_pairings(players, team_size)
    else:
        if system == "Round Robin":
            names = [p[1] for p in players]
            rounds = round_robin_rounds(names)
            return assign_firsts(rounds)
        elif system == "Random Pairing":
            return random_pairings(players)
        elif system == "King of the Hills Pairing":
            return king_of_the_hills_pairings(players)
        else:
            raise ValueError("Invalid pairing system specified.")

#####################################
# New: Generate Player Scorecard HTML (with cumulative spread)
#####################################
def generate_player_scorecard_html(player, tournament_id):
    """
    Generates an HTML page for a player's scorecard.
    The table includes round, result, and cumulative spread.
    """
    rendered_dir = os.path.join(os.getcwd(), "rendered")
    player_id = player[0]
    try:
        scorecard = json.loads(player[7]) if player[7] else []
    except Exception:
        scorecard = []
    rows = ""
    for entry in scorecard:
        rows += f"<tr><td>{entry.get('round', 'N/A')}</td><td>{entry.get('result', 'N/A')}</td><td>{entry.get('cumulative', 'N/A')}</td></tr>\n"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Scorecard - {player[1]}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background-color: #f8f9fa; color: #343a40; }}
    .container-custom {{ max-width:800px; margin:auto; }}
    footer {{ margin-top: 40px; font-size: 0.9em; text-align: center; padding: 20px 0; }}
  </style>
</head>
<body>
  <div class="container container-custom">
    <h1 class="mt-4">Scorecard</h1>
    <h3>{player[1]} (Rating: {player[2]})</h3>
    <table class="table table-striped">
      <thead>
        <tr><th>Round</th><th>Result</th><th>Cumulative Spread</th></tr>
      </thead>
      <tbody>
        {rows if rows else '<tr><td colspan="3">No scorecard data available.</td></tr>'}
      </tbody>
    </table>
    <a href="tournament_{tournament_id}_standings.html" class="btn btn-secondary">Back to Standings</a>
  </div>
  <footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    filename = os.path.join(rendered_dir, f"tournament_{tournament_id}_player_{player_id}.html")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return f"tournament_{tournament_id}_player_{player_id}.html"

#####################################
# HTML Generation Function (Rebranded with Bootstrap 5)
#####################################
def generate_tournament_html(tournament_id, tournament_name, tournament_date):
    """
    Generates rebranded HTML pages using Bootstrap 5.
    Pairing round pages are generated individually, and the index lists links for each paired round.
    """
    rendered_dir = os.path.join(os.getcwd(), "rendered")
    if not os.path.exists(rendered_dir):
        os.makedirs(rendered_dir)
    
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, date, venue FROM tournaments WHERE id = ?", (tournament_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        tournament_name_db, tournament_date_db, tournament_venue = result
    else:
        tournament_name_db, tournament_date_db, tournament_venue = tournament_name, tournament_date, ""
    
    players = get_players_for_tournament(tournament_id)
    
    if completed_rounds:
        schedule = [completed_rounds[r] for r in sorted(completed_rounds.keys())]
    else:
        schedule = generate_pairings_system(players, system=last_pairing_system)
    
    # Build pairing round pages and collect links
    pairing_round_links = []
    base = f"tournament_{tournament_id}"
    index_file = f"{base}_index.html"
    roster_file = f"{base}_roster.html"
    standings_file = f"{base}_standings.html"
    prize_file = f"{base}_prize.html"
    for idx, round_pairings in enumerate(schedule, start=1):
        round_file = f"{base}_pairings_round_{idx}.html"
        pairing_round_links.append((idx, round_file))
        pairing_content = f"<h2>Round {idx}</h2>\n<table class='table table-bordered'><thead><tr><th>#</th><th>Pairing</th><th>First</th></tr></thead><tbody>"
        for i, pairing in enumerate(round_pairings, start=1):
            if tournament_mode == "Team Round Robin":
                if len(pairing) >= 3:
                    teamA, teamB, first = pairing[0], pairing[1], pairing[2]
                    pairing_str = f"Team A: {', '.join(teamA)} vs Team B: {', '.join(teamB)}"
                else:
                    pairing_str = "Invalid team pairing"
                    first = "N/A"
            else:
                if len(pairing) == 3:
                    p1, p2, first = pairing
                elif len(pairing) == 2:
                    p1, p2 = pairing
                    first = random.choice([p1, p2])
                else:
                    p1, p2, first = "???", "???", "???"
                pairing_str = f"{p1} vs {p2}"
            pairing_content += f"<tr><td>{i}</td><td>{pairing_str}</td><td>{first}</td></tr>\n"
        pairing_content += "</tbody></table>"
        # Define header, navbar, footer as local functions
        def header_html():
            return f"""
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{tournament_name_db}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body {{ background-color: #f8f9fa; color: #343a40; }}
        .container-custom {{ max-width:800px; margin:auto; }}
        footer {{ margin-top: 40px; font-size: 0.9em; text-align: center; padding: 20px 0; }}
      </style>
    </head>
    """
        def navbar_html(index, roster, standings, prize):
            return f"""
    <nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
      <div class="container">
        <a class="navbar-brand" href="{index}"></a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
                data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" 
                aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav ms-auto">
            <li class="nav-item"><a class="nav-link" href="{index}">Home</a></li>
            <li class="nav-item"><a class="nav-link" href="{roster}">Roster</a></li>
            <li class="nav-item"><a class="nav-link" href="{standings}">Standings</a></li>
            <li class="nav-item"><a class="nav-link" href="{prize}">Prize Table</a></li>
          </ul>
        </div>
      </div>
    </nav>
    """
        def footer_section():
            return '<footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>'
        pairing_page = f"""<!DOCTYPE html>
<html lang="en">
{header_html()}
<body>
  {navbar_html(index_file, roster_file, standings_file, prize_file)}
  <div class="container container-custom">
    <h1 class="mb-3">Pairings - {tournament_name_db} - Round {idx}</h1>
    {pairing_content}
    <a href="{index_file}" class="btn btn-secondary">Back to Index</a>
  </div>
  {footer_section()}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
        with open(os.path.join(rendered_dir, round_file), "w", encoding="utf-8") as f:
            f.write(pairing_page)
    
    # Build header, navbar, footer for other pages
    def header_html():
        return f"""
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{tournament_name_db}</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <style>
        body {{ background-color: #f8f9fa; color: #343a40; }}
        .container-custom {{ max-width:800px; margin:auto; }}
        footer {{ margin-top: 40px; font-size: 0.9em; text-align: center; padding: 20px 0; }}
      </style>
    </head>
    """
    def navbar_html(index, roster, standings, prize):
        return f"""
    <nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
      <div class="container">
        <a class="navbar-brand" href="{index}"></a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
                data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" 
                aria-label="Toggle navigation">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav ms-auto">
            <li class="nav-item"><a class="nav-link" href="{index}">Home</a></li>
            <li class="nav-item"><a class="nav-link" href="{roster}">Roster</a></li>
            <li class="nav-item"><a class="nav-link" href="{standings}">Standings</a></li>
            <li class="nav-item"><a class="nav-link" href="{prize}">Prize Table</a></li>
          </ul>
        </div>
      </div>
    </nav>
    """
    def footer_section():
        return '<footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>'
    
    # INDEX PAGE: List links for each pairing round
    round_links_html = ""
    for r, link in pairing_round_links:
        round_links_html += f"<li class='list-group-item'><a href='{link}'>Pairings: Round {r}</a></li>\n"
    index_html = f"""<!DOCTYPE html>
<html lang="en">
{header_html()}
<body>
  {navbar_html(index_file, roster_file, standings_file, prize_file)}
  <div class="container container-custom">
    <h1 class="mb-3">{tournament_name_db}</h1>
    <p class="lead">{tournament_date_db} | {tournament_venue}</p>
    <h2 class="mt-4">Event Coverage Index</h2>
    <ul class="list-group">
      <li class="list-group-item"><a href="{roster_file}">Player Roster</a></li>
      {round_links_html}
      <li class="list-group-item"><a href="{standings_file}">Standings</a></li>
      <li class="list-group-item"><a href="{prize_file}">Prize Table</a></li>
    </ul>
  </div>
  {footer_section()}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    with open(os.path.join(rendered_dir, index_file), "w", encoding="utf-8") as f:
        f.write(index_html)
    
    # PLAYER ROSTER PAGE
    roster_rows = ""
    for idx, p in enumerate(players, start=1):
        roster_rows += f"<tr><td>{idx}</td><td>{p[1]}</td><td>{p[2]}</td></tr>\n"
    roster_html = f"""<!DOCTYPE html>
<html lang="en">
{header_html()}
<body>
  {navbar_html(index_file, roster_file, standings_file, prize_file)}
  <div class="container container-custom">
    <h1 class="mb-3">Player Roster - {tournament_name_db}</h1>
    <table class="table table-striped">
      <thead><tr><th>Rank</th><th>Name</th><th>Rating</th></tr></thead>
      <tbody>{roster_rows}</tbody>
    </table>
    <a href="{index_file}" class="btn btn-secondary">Back to Index</a>
  </div>
  {footer_section()}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    with open(os.path.join(rendered_dir, roster_file), "w", encoding="utf-8") as f:
        f.write(roster_html)
    
    # STANDINGS PAGE (no Next game column)
    standings_rows = ""
    sorted_players = sorted(players, key=lambda x: (x[3], x[5]), reverse=True)
    for rank, player in enumerate(sorted_players, start=1):
        scorecard_link = generate_player_scorecard_html(player, tournament_id)
        standings_rows += f"<tr><td>{rank}</td><td><a href='{scorecard_link}'>{player[1]}</a></td><td>{player[3]}</td><td>{player[4]}</td><td>{player[5]}</td><td>{player[6]}</td></tr>\n"
    standings_html = f"""<!DOCTYPE html>
<html lang="en">
{header_html()}
<body>
  {navbar_html(index_file, roster_file, standings_file, prize_file)}
  <div class="container container-custom">
    <h1 class="mb-3">Standings - {tournament_name_db}</h1>
    <table class="table table-hover">
      <thead><tr><th>Rank</th><th>Name</th><th>Wins</th><th>Losses</th><th>Spread</th><th>Last result</th></tr></thead>
      <tbody>{standings_rows}</tbody>
    </table>
    <a href="{index_file}" class="btn btn-secondary">Back to Index</a>
  </div>
  {footer_section()}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    with open(os.path.join(rendered_dir, standings_file), "w", encoding="utf-8") as f:
        f.write(standings_html)
    
    # PRIZE TABLE PAGE
    prize_rows = ""
    for prize in prize_table:
        if prize["prize_type"] == "Monetary":
            prize_rows += f"<tr><td>{prize['prize_name']}</td><td>{prize['currency']} {prize['amount']}</td></tr>\n"
        else:
            prize_rows += f"<tr><td>{prize['prize_name']}</td><td>{prize['prize_description']}</td></tr>\n"
    prize_html = f"""<!DOCTYPE html>
<html lang="en">
{header_html()}
<body>
  {navbar_html(index_file, roster_file, standings_file, prize_file)}
  <div class="container container-custom">
    <h1 class="mb-3">Prize Table - {tournament_name_db}</h1>
    <table class="table table-bordered">
      <thead><tr><th>Prize Name</th><th>Details</th></tr></thead>
      <tbody>{prize_rows}</tbody>
    </table>
    <a href="{index_file}" class="btn btn-secondary">Back to Index</a>
  </div>
  {footer_section()}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    with open(os.path.join(rendered_dir, prize_file), "w", encoding="utf-8") as f:
        f.write(prize_html)
    
    start_http_server(HTTP_PORT)
    ip = get_local_ip()
    url = f"http://{ip}:{HTTP_PORT}/{index_file}"
    return url

#####################################
# Unified Results Entry (with Edit Capability)
#####################################
def setup_enter_results(tab_frame):
    if last_pairing_system == "Team Round Robin":
        # Placeholder for team results
        setup_team_results_ui(tab_frame)
        return
    label_ind = ctk.CTkLabel(tab_frame, text="Individual Round Result Entry", font=("Arial", 18))
    label_ind.pack(pady=10)
    round_var = ctk.StringVar()
    round_options = sorted([f"Round {r}" for r in completed_rounds.keys()]) if completed_rounds else []
    round_dropdown = ctk.CTkOptionMenu(tab_frame, variable=round_var, values=round_options)
    round_dropdown.pack(pady=5)
    result_frame = ctk.CTkFrame(tab_frame)
    result_frame.pack(pady=10)
    pairing_label = ctk.CTkLabel(result_frame, text="Pairing: ", font=("Arial", 14))
    pairing_label.grid(row=0, column=0, columnspan=2, pady=5)
    score1_entry = ctk.CTkEntry(result_frame, placeholder_text="Score for Player 1")
    score1_entry.grid(row=1, column=0, padx=5, pady=5)
    score2_entry = ctk.CTkEntry(result_frame, placeholder_text="Score for Player 2")
    score2_entry.grid(row=1, column=1, padx=5, pady=5)
    nav_frame = ctk.CTkFrame(tab_frame)
    nav_frame.pack(pady=5)
    prev_button = ctk.CTkButton(nav_frame, text="Previous", width=100)
    prev_button.grid(row=0, column=0, padx=5)
    next_button = ctk.CTkButton(nav_frame, text="Next", width=100)
    next_button.grid(row=0, column=1, padx=5)
    submit_button = ctk.CTkButton(tab_frame, text="Submit/Update Result", width=200)
    submit_button.pack(pady=5)
    result_rounds = []
    current_round_index = 0
    current_pairing_index = 0
    def load_rounds():
        nonlocal result_rounds, current_round_index, current_pairing_index
        if current_tournament_id is None:
            show_toast(tab_frame, "No tournament available.")
            return
        rounds_sorted = sorted(completed_rounds.keys())
        result_rounds = [completed_rounds[r] for r in rounds_sorted]
        round_values = [f"Round {r}" for r in rounds_sorted]
        round_dropdown.configure(values=round_values)
        if round_values:
            round_var.set(round_values[0])
        else:
            round_var.set("--Select Round--")
        current_round_index = 0
        current_pairing_index = 0
        pairing_label.configure(text="Pairing: ")
        score1_entry.delete(0, "end")
        score2_entry.delete(0, "end")
        load_current_pairing()
    def on_round_selected(*args):
        nonlocal current_round_index, current_pairing_index
        sel = round_var.get()
        if sel.startswith("Round "):
            r = int(sel.split()[1])
            rounds_sorted = sorted(completed_rounds.keys())
            if r in rounds_sorted:
                current_round_index = rounds_sorted.index(r)
                current_pairing_index = 0
                load_current_pairing()
    def load_current_pairing():
        nonlocal current_round_index, current_pairing_index
        if not result_rounds:
            pairing_label.configure(text="No round paired yet.")
            return
        current_round = result_rounds[current_round_index]
        if current_pairing_index < 0 or current_pairing_index >= len(current_round):
            pairing_label.configure(text="No pairing")
            return
        p1, p2, first = current_round[current_pairing_index]
        pairing_label.configure(text=f"Pairing {current_pairing_index+1}/{len(current_round)}: {p1} vs {p2} (First: {first})")
        score1_entry.delete(0, "end")
        score2_entry.delete(0, "end")
        round_num = sorted(completed_rounds.keys())[current_round_index]
        if round_num in results_by_round and len(results_by_round[round_num]) > current_pairing_index:
            res = results_by_round[round_num][current_pairing_index]
            if res:
                s1, s2 = res
                score1_entry.insert(0, str(s1))
                score2_entry.insert(0, str(s2))
    def prev_pairing():
        nonlocal current_pairing_index
        if current_pairing_index > 0:
            current_pairing_index -= 1
            load_current_pairing()
    def next_pairing():
        nonlocal current_pairing_index
        if result_rounds and current_pairing_index < len(result_rounds[current_round_index]) - 1:
            current_pairing_index += 1
            load_current_pairing()
    round_var.trace("w", on_round_selected)
    prev_button.configure(command=prev_pairing)
    next_button.configure(command=next_pairing)
    def get_player_id_by_name_ind(tournament_id, name):
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM players WHERE tournament_id = ? AND name = ?", (tournament_id, name))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    def submit_result():
        nonlocal current_pairing_index
        if not result_rounds:
            return
        current_round = result_rounds[current_round_index]
        pairing = current_round[current_pairing_index]
        p1, p2, first = pairing
        if p1 == "BYE" or p2 == "BYE":
            show_toast(tab_frame, "BYE pairing. No result needed.")
            next_pairing()
            return
        try:
            score1 = int(score1_entry.get().strip())
            score2 = int(score2_entry.get().strip())
        except ValueError:
            show_toast(tab_frame, "Please enter valid numeric scores.")
            return
        round_num = sorted(completed_rounds.keys())[current_round_index]
        if round_num not in results_by_round:
            results_by_round[round_num] = [None] * len(current_round)
        results_by_round[round_num][current_pairing_index] = (score1, score2)
        recalc_player_stats()
        show_toast(tab_frame, f"Result submitted/updated for pairing {current_pairing_index+1}.")
    submit_button.configure(command=submit_result)
    load_rounds()
    refresh_button = ctk.CTkButton(tab_frame, text="Reload Rounds", command=load_rounds)
    refresh_button.pack(pady=5)

#####################################
# Prize Table Function
#####################################
def setup_prize_table(tab_frame):
    global prize_table
    label = ctk.CTkLabel(tab_frame, text="Prize Table", font=("Arial", 18))
    label.pack(pady=10)
    prize_name_entry = ctk.CTkEntry(tab_frame, placeholder_text="Prize Name")
    prize_name_entry.pack(pady=5)
    prize_type_var = ctk.StringVar(value="Monetary")
    prize_type_menu = ctk.CTkOptionMenu(tab_frame, variable=prize_type_var, values=["Monetary", "Non-Monetary"])
    prize_type_menu.pack(pady=5)
    currency_entry = ctk.CTkEntry(tab_frame, placeholder_text="Currency (e.g., USD)")
    currency_entry.pack(pady=5)
    amount_entry = ctk.CTkEntry(tab_frame, placeholder_text="Amount or Description")
    amount_entry.pack(pady=5)
    prize_list_text = ctk.CTkTextbox(tab_frame, width=400, height=200)
    prize_list_text.pack(pady=10)
    prize_list_text.insert("end", "Current Prizes:\n")
    prize_list_text.configure(state="disabled")
    def update_prize_list():
        prize_list_text.configure(state="normal")
        prize_list_text.delete("1.0", "end")
        prize_list_text.insert("end", "Current Prizes:\n")
        for prize in prize_table:
            if prize["prize_type"] == "Monetary":
                prize_list_text.insert("end", f'{prize["prize_name"]}: {prize["currency"]} {prize["amount"]}\n')
            else:
                prize_list_text.insert("end", f'{prize["prize_name"]}: {prize["prize_description"]}\n')
        prize_list_text.configure(state="disabled")
    def add_prize():
        name = prize_name_entry.get().strip()
        ptype = prize_type_var.get()
        if name == "":
            show_toast(tab_frame, "Enter prize name.")
            return
        if ptype == "Monetary":
            currency = currency_entry.get().strip()
            amount = amount_entry.get().strip()
            if currency == "" or amount == "":
                show_toast(tab_frame, "Enter currency and amount.")
                return
            try:
                amount = float(amount)
            except ValueError:
                show_toast(tab_frame, "Invalid amount.")
                return
            prize_table.append({"prize_name": name, "prize_type": ptype, "currency": currency, "amount": amount})
        else:
            description = amount_entry.get().strip()
            prize_table.append({"prize_name": name, "prize_type": ptype, "prize_description": description})
        update_prize_list()
        prize_name_entry.delete(0, "end")
        currency_entry.delete(0, "end")
        amount_entry.delete(0, "end")
    add_prize_button = ctk.CTkButton(tab_frame, text="Add Prize", command=add_prize)
    add_prize_button.pack(pady=5)
    def save_tab():
        show_toast(tab_frame, "Tab data saved.")
    tab_save_button = ctk.CTkButton(tab_frame, text="Save Tab", command=save_tab)
    tab_save_button.pack(pady=5)

#####################################
# Reports Function
#####################################
def setup_reports(tab_frame):
    label = ctk.CTkLabel(tab_frame, text="Reports & Exports", font=("Arial", 18))
    label.pack(pady=10)
    info_label = ctk.CTkLabel(tab_frame, text="Report generation functionality coming soon!", font=("Arial", 14))
    info_label.pack(pady=10)

#####################################
# Render Function
#####################################
def setup_render(tab_frame):
    global current_tournament_id, app
    label = ctk.CTkLabel(tab_frame, text="Render Current Tournament", font=("Arial", 18))
    label.pack(pady=10)
    def render_current_tournament():
        if current_tournament_id is None:
            show_toast(tab_frame, "No current tournament available.")
            return
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, date, venue FROM tournaments WHERE id = ?", (current_tournament_id,))
        result = cursor.fetchone()
        conn.close()
        if result is None:
            show_toast(tab_frame, "Tournament details not found.")
            return
        tournament_name, tournament_date, tournament_venue = result
        try:
            url = generate_tournament_html(current_tournament_id, tournament_name, tournament_date)
        except Exception as e:
            messagebox.showerror("Render Error", f"An error occurred during rendering: {e}")
            return
        webbrowser.open(url)
    render_button = ctk.CTkButton(tab_frame, text="Render Current Tournament", command=render_current_tournament)
    render_button.pack(pady=10)

#####################################
# Placeholder for Team Results UI
#####################################
def setup_team_results_ui(tab_frame):
    label = ctk.CTkLabel(tab_frame, text="Team Results Entry (Placeholder)", font=("Arial", 18))
    label.pack(pady=10)
    info = ctk.CTkLabel(tab_frame, text="Team results entry functionality coming soon!", font=("Arial", 14))
    info.pack(pady=10)

#####################################
# UI Tab Building Functions
#####################################
def build_tab_view(parent):
    if current_mode_view == "general":
        tabs = ["Tournament Setup", "Player Registration", "Pairings", "Enter Results", "Prize Table", "Reports & Exports", "Render"]
    elif current_mode_view == "team":
        tabs = ["Tournament Setup", "Player Registration", "Team Pairings", "Team Results", "Prize Table", "Render"]
    else:
        tabs = []
    tab_view = ctk.CTkTabview(parent, width=880, height=700)
    tab_view.pack(fill="both", expand=True)
    for tab in tabs:
        tab_view.add(tab)
        if current_mode_view == "general" and tab == "Pairings":
            setup_pairings(tab_view.tab(tab))
        elif current_mode_view == "general":
            if tab in ("Reports & Exports", "Render"):
                setup_tab_content_without_save(tab_view.tab(tab), tab)
            else:
                setup_tab_content(tab, tab_view.tab(tab))
        elif current_mode_view == "team":
            if tab == "Team Pairings":
                setup_pairings(tab_view.tab(tab))
            elif tab == "Team Results":
                setup_team_results_ui(tab_view.tab(tab))
            else:
                if tab in ("Reports & Exports", "Render"):
                    setup_tab_content_without_save(tab_view.tab(tab), tab)
                else:
                    setup_tab_content(tab, tab_view.tab(tab))
    return tab_view

def rebuild_tab_view():
    global main_frame_global
    for widget in main_frame_global.winfo_children():
        widget.destroy()
    return build_tab_view(main_frame_global)

def switch_mode_toggle():
    """
    Toggle between General and Team Round Robin modes.
    """
    global current_mode_view, tournament_mode
    if current_mode_view == "general":
        current_mode_view = "team"
        tournament_mode = "Team Round Robin"
    else:
        current_mode_view = "general"
        tournament_mode = "General"
    rebuild_tab_view()
    show_toast(app, f"Switched to {current_mode_view.capitalize()} Mode.")

def setup_tab_content(tab_name, tab_frame):
    if tab_name == "Tournament Setup":
        setup_tournament_setup(tab_frame)
    elif tab_name == "Player Registration":
        setup_player_registration(tab_frame)
    elif tab_name == "Pairings" or tab_name == "Team Pairings":
        setup_pairings(tab_frame)
    elif tab_name == "Enter Results":
        setup_enter_results(tab_frame)
    elif tab_name == "Team Results":
        setup_team_results_ui(tab_frame)
    elif tab_name == "Prize Table":
        setup_prize_table(tab_frame)
    elif tab_name == "Reports & Exports":
        setup_reports(tab_frame)
    elif tab_name == "Render":
        setup_render(tab_frame)
    else:
        label = ctk.CTkLabel(tab_frame, text=tab_name, font=("Arial", 18))
        label.pack(pady=20)
    def save_tab():
        show_toast(tab_frame, "Tab data saved.")
    tab_save_button = ctk.CTkButton(tab_frame, text="Save Tab", command=save_tab)
    tab_save_button.pack(pady=5)

def setup_tab_content_without_save(tab_frame, tab_name):
    if tab_name == "Reports & Exports":
        setup_reports(tab_frame)
    elif tab_name == "Render":
        setup_render(tab_frame)
    else:
        label = ctk.CTkLabel(tab_frame, text=tab_name, font=("Arial", 18))
        label.pack(pady=20)

#####################################
# Tournament Setup Function
#####################################
def setup_tournament_setup(tab_frame):
    global current_tournament_id, session_players, current_round_number, completed_rounds, tournament_mode, teams_list, team_size, last_pairing_system, last_team_size, current_mode_view
    label = ctk.CTkLabel(tab_frame, text="Set Up a New Tournament", font=("Arial", 18))
    label.pack(pady=10)
    tournament_name_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter tournament name")
    tournament_name_entry.pack(pady=5)
    tournament_date_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter tournament date (YYYY-MM-DD)")
    tournament_date_entry.pack(pady=5)
    venue_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter tournament venue")
    venue_entry.pack(pady=5)
    if current_mode_view == "team":
        team_size_var = ctk.StringVar(value="3")
        team_size_menu = ctk.CTkOptionMenu(tab_frame, variable=team_size_var, values=["3", "5"])
        team_size_menu.pack(pady=5)
        team_names_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter team names (comma-separated)")
        team_names_entry.pack(pady=5)
    def create_tournament():
        global current_tournament_id, session_players, current_round_number, completed_rounds, tournament_mode, teams_list, team_size, last_pairing_system, last_team_size, current_mode_view
        name = tournament_name_entry.get().strip()
        date = tournament_date_entry.get().strip()
        venue = venue_entry.get().strip()
        if name == "" or date == "" or venue == "":
            show_toast(tab_frame, "Please enter valid tournament details, including venue.")
            return
        if current_mode_view == "team":
            tournament_mode = "Team Round Robin"
            team_size = int(team_size_var.get())
            team_names = team_names_entry.get().strip()
            if team_names == "":
                show_toast(tab_frame, "Please enter team names.")
                return
            teams_list = [t.strip() for t in team_names.split(",") if t.strip() != ""]
            if len(teams_list) < 2:
                show_toast(tab_frame, "Please enter at least two team names.")
                return
            last_pairing_system = "Team Round Robin"
            last_team_size = team_size
        elif current_mode_view == "general":
            tournament_mode = "General"
            teams_list = []
            team_size = 0
            last_pairing_system = "Round Robin"
        conn = create_connection()
        tournament_id = insert_tournament(conn, name, date, venue)
        conn.close()
        if tournament_id:
            current_tournament_id = tournament_id
            session_players = []
            current_round_number = 0
            completed_rounds.clear()
            results_by_round.clear()
            link = generate_tournament_html(tournament_id, name, date)
            update_tournament_link(tournament_id, link)
            show_toast(tab_frame, f"Tournament '{name}' created. Link: {link}")
            print(f"Tournament '{name}' created with ID {tournament_id}. Link: {link}")
            update_status()
        else:
            show_toast(tab_frame, "Failed to create tournament.")
            print("Failed to create tournament.")
        tournament_name_entry.delete(0, 'end')
        tournament_date_entry.delete(0, 'end')
        venue_entry.delete(0, 'end')
        if current_mode_view == "team":
            team_names_entry.delete(0, 'end')
    create_button = ctk.CTkButton(tab_frame, text="Create Tournament", command=create_tournament)
    create_button.pack(pady=10)

#####################################
# Team Results Placeholder
#####################################
def setup_team_results_ui(tab_frame):
    label = ctk.CTkLabel(tab_frame, text="Team Results Entry (Placeholder)", font=("Arial", 18))
    label.pack(pady=10)
    info = ctk.CTkLabel(tab_frame, text="Team results entry functionality coming soon!", font=("Arial", 14))
    info.pack(pady=10)

#####################################
# Player Registration Function
#####################################
def setup_player_registration(tab_frame):
    global current_tournament_id, session_players, tournament_mode, teams_list
    label = ctk.CTkLabel(tab_frame, text="Register a New Player", font=("Arial", 18))
    label.pack(pady=10)
    name_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter player name")
    name_entry.pack(pady=5)
    rating_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter rating (or 000 if unrated)")
    rating_entry.pack(pady=5)
    rating_entry.insert(0, "000")
    if tournament_mode == "Team Round Robin":
        team_var = ctk.StringVar()
        team_dropdown_frame = ctk.CTkFrame(tab_frame)
        team_dropdown_frame.pack(pady=5)
        team_dropdown = ctk.CTkOptionMenu(tab_frame, variable=team_var, values=teams_list if teams_list else ["No Teams Defined"])
        team_dropdown.pack()
    player_list_text = ctk.CTkTextbox(tab_frame, width=400, height=200)
    player_list_text.pack(pady=10)
    player_list_text.insert("end", "Registered Players (This Tournament):\n")
    player_list_text.configure(state="disabled")
    def update_player_list():
        if current_tournament_id is None:
            return
        players = get_players_for_tournament(current_tournament_id)
        player_list_text.configure(state="normal")
        player_list_text.delete("1.0", "end")
        player_list_text.insert("end", "Registered Players (This Tournament):\n")
        for player in players:
            team = player[8] if len(player) > 8 and player[8] else ""
            display_name = f"{player[1]}, ({team})" if team else player[1]
            player_list_text.insert("end", f"{display_name} (Rating: {player[2]})\n")
        player_list_text.configure(state="disabled")
    def register_player():
        global current_tournament_id, session_players
        if current_tournament_id is None:
            show_toast(tab_frame, "Please create a tournament first!")
            return
        name = name_entry.get().strip()
        rating_str = rating_entry.get().strip()
        try:
            rating = int(rating_str) if rating_str and rating_str.isdigit() else 0
        except ValueError:
            rating = 0
        if name == "":
            show_toast(tab_frame, "Please enter a valid name!")
            return
        team = ""
        if tournament_mode == "Team Round Robin":
            team = team_var.get()
            if team == "No Teams Defined" or team == "":
                show_toast(tab_frame, "Please select a team.")
                return
        conn = create_connection()
        tournament_specific_id = insert_player(conn, name, rating, current_tournament_id, team)
        conn.close()
        show_toast(tab_frame, f"Player '{name}' registered with tournament ID {tournament_specific_id}.")
        print(f"Player '{name}' registered with tournament ID {tournament_specific_id}.")
        name_entry.delete(0, 'end')
        rating_entry.delete(0, 'end')
        rating_entry.insert(0, "000")
        update_player_list()
    register_button = ctk.CTkButton(tab_frame, text="Register Player", command=register_player)
    register_button.pack(pady=10)

#####################################
# Unified Pairings Tab Function
#####################################
def setup_pairings(tab_frame):
    """
    In General mode, the pairing system dropdown includes "Round Robin",
    "Random Pairing", and "King of the Hills Pairing".
    """
    global current_round_number, completed_rounds, last_pairing_system, last_team_size
    label = ctk.CTkLabel(tab_frame, text="Pairings", font=("Arial", 18))
    label.pack(pady=10)
    round_number_var = ctk.StringVar(value=str(current_round_number + 1))
    round_number_menu = ctk.CTkOptionMenu(tab_frame, variable=round_number_var,
                                         values=[str(i) for i in range(1, current_round_number+2)])
    round_number_menu.pack(pady=5)
    if tournament_mode == "Team Round Robin":
        pairing_system_values = ["Team Round Robin"]
    elif tournament_mode == "General":
        pairing_system_values = ["Round Robin", "Random Pairing", "King of the Hills Pairing"]
    else:
        pairing_system_values = []
    pairing_system_var = ctk.StringVar(value=pairing_system_values[0] if pairing_system_values else "")
    pairing_system_menu = ctk.CTkOptionMenu(tab_frame, variable=pairing_system_var, values=pairing_system_values)
    pairing_system_menu.pack(pady=5)
    if tournament_mode == "Team Round Robin":
        team_size_var = ctk.StringVar(value="3")
        team_size_menu = ctk.CTkOptionMenu(tab_frame, variable=team_size_var, values=["3", "5"])
        team_size_menu.pack(pady=5)
    pairing_output = ctk.CTkTextbox(tab_frame, width=600, height=300)
    pairing_output.pack(pady=10)
    def pair_round():
        global current_round_number, completed_rounds, last_pairing_system, last_team_size
        if current_tournament_id is None:
            messagebox.showerror("Error", "No tournament available.")
            return
        selected_round = int(round_number_var.get())
        if selected_round != current_round_number + 1:
            messagebox.showerror("Error", "You can only pair the next unpaired round.")
            return
        last_pairing_system = pairing_system_var.get()
        players = get_players_for_tournament(current_tournament_id)
        if tournament_mode == "Team Round Robin":
            last_team_size = int(team_size_var.get())
            try:
                pairing = generate_pairings_system(players, system="Team Round Robin", team_size=last_team_size)
            except ValueError as e:
                messagebox.showerror("Error", str(e))
                return
            completed_rounds[selected_round] = pairing
            current_round_number = selected_round
        elif tournament_mode == "General":
            if last_pairing_system == "Round Robin":
                full_schedule = generate_pairings_system(players, system="Round Robin")
                total_rounds = len(full_schedule)
                msg = f"Based on {len(players)} players, a full round robin schedule has {total_rounds} rounds.\nHow many rounds do you want to play?"
                desired_rounds = simpledialog.askinteger("Round Robin Schedule", msg, minvalue=1, maxvalue=total_rounds)
                if desired_rounds is None:
                    return
                for r in range(1, desired_rounds+1):
                    completed_rounds[r] = full_schedule[r-1]
                current_round_number = desired_rounds
                pairing = full_schedule[desired_rounds-1]
            elif last_pairing_system in ["Random Pairing", "King of the Hills Pairing"]:
                pairing = generate_general_pairings(players, last_pairing_system)
                completed_rounds[selected_round] = pairing
                current_round_number = selected_round
            else:
                pairing = []
        else:
            pairing = []
        new_options = [str(i) for i in range(1, current_round_number+2)]
        round_number_menu.configure(values=new_options)
        round_number_var.set(str(current_round_number + 1))
        pairing_output.configure(state="normal")
        pairing_output.delete("0.0", "end")
        pairing_output.insert("end", f"Round {selected_round} ({last_pairing_system}):\n")
        if tournament_mode == "Team Round Robin":
            for j, pr in enumerate(pairing, start=1):
                teamA, teamB, starting = pr
                pairing_output.insert("end", f"Team Pairing {j}:\n")
                pairing_output.insert("end", f"  Team A: {', '.join(teamA)}\n")
                pairing_output.insert("end", f"  Team B: {', '.join(teamB)}\n")
                pairing_output.insert("end", f"  Starting: {starting}\n")
                board = 1
                pairing_output.insert("end", "  Boards:\n")
                for pA in teamA:
                    for pB in teamB:
                        pairing_output.insert("end", f"    Board {board}: {pA} vs {pB}\n")
                        board += 1
        else:
            for j, pr in enumerate(pairing, start=1):
                if len(pr) >= 3:
                    p1, p2, first = pr
                elif len(pr) == 2:
                    p1, p2 = pr
                    first = random.choice([p1, p2])
                else:
                    p1, p2, first = "???", "???", "???"
                pairing_output.insert("end", f"  Board {j}: {p1} vs {p2} (First: {first})\n")
        pairing_output.configure(state="disabled")
        if selected_round not in results_by_round:
            results_by_round[selected_round] = [None] * len(pairing)
    pair_button = ctk.CTkButton(tab_frame, text="Pair Round", command=pair_round)
    pair_button.pack(pady=5)
    def unpair_round():
        global current_round_number, completed_rounds
        selected_round = int(round_number_var.get())
        if selected_round not in completed_rounds:
            messagebox.showerror("Error", "Selected round has not been paired yet.")
            return
        if selected_round != current_round_number:
            messagebox.showerror("Error", "Only the last completed round can be unpaired.")
            return
        del completed_rounds[selected_round]
        if selected_round in results_by_round:
            del results_by_round[selected_round]
        current_round_number -= 1
        new_options = [str(i) for i in range(1, current_round_number+2)]
        round_number_menu.configure(values=new_options)
        round_number_var.set(str(current_round_number + 1))
        pairing_output.configure(state="normal")
        pairing_output.delete("0.0", "end")
        pairing_output.configure(state="disabled")
        show_toast(tab_frame, f"Round {selected_round} has been unpaired.")
    unpair_button = ctk.CTkButton(tab_frame, text="Unpair Round", command=unpair_round)
    unpair_button.pack(pady=5)
    def save_tab():
        show_toast(tab_frame, "Tab data saved.")
    tab_save_button = ctk.CTkButton(tab_frame, text="Save Tab", command=save_tab)
    tab_save_button.pack(pady=5)

#####################################
# Unified Results Entry (with Edit Capability)
#####################################
def setup_enter_results(tab_frame):
    if last_pairing_system == "Team Round Robin":
        setup_team_results_ui(tab_frame)
        return
    label_ind = ctk.CTkLabel(tab_frame, text="Individual Round Result Entry", font=("Arial", 18))
    label_ind.pack(pady=10)
    round_var = ctk.StringVar()
    round_options = sorted([f"Round {r}" for r in completed_rounds.keys()]) if completed_rounds else []
    round_dropdown = ctk.CTkOptionMenu(tab_frame, variable=round_var, values=round_options)
    round_dropdown.pack(pady=5)
    result_frame = ctk.CTkFrame(tab_frame)
    result_frame.pack(pady=10)
    pairing_label = ctk.CTkLabel(result_frame, text="Pairing: ", font=("Arial", 14))
    pairing_label.grid(row=0, column=0, columnspan=2, pady=5)
    score1_entry = ctk.CTkEntry(result_frame, placeholder_text="Score for Player 1")
    score1_entry.grid(row=1, column=0, padx=5, pady=5)
    score2_entry = ctk.CTkEntry(result_frame, placeholder_text="Score for Player 2")
    score2_entry.grid(row=1, column=1, padx=5, pady=5)
    nav_frame = ctk.CTkFrame(tab_frame)
    nav_frame.pack(pady=5)
    prev_button = ctk.CTkButton(nav_frame, text="Previous", width=100)
    prev_button.grid(row=0, column=0, padx=5)
    next_button = ctk.CTkButton(nav_frame, text="Next", width=100)
    next_button.grid(row=0, column=1, padx=5)
    submit_button = ctk.CTkButton(tab_frame, text="Submit/Update Result", width=200)
    submit_button.pack(pady=5)
    result_rounds = []
    current_round_index = 0
    current_pairing_index = 0
    def load_rounds():
        nonlocal result_rounds, current_round_index, current_pairing_index
        if current_tournament_id is None:
            show_toast(tab_frame, "No tournament available.")
            return
        rounds_sorted = sorted(completed_rounds.keys())
        result_rounds = [completed_rounds[r] for r in rounds_sorted]
        round_values = [f"Round {r}" for r in rounds_sorted]
        round_dropdown.configure(values=round_values)
        if round_values:
            round_var.set(round_values[0])
        else:
            round_var.set("--Select Round--")
        current_round_index = 0
        current_pairing_index = 0
        pairing_label.configure(text="Pairing: ")
        score1_entry.delete(0, "end")
        score2_entry.delete(0, "end")
        load_current_pairing()
    def on_round_selected(*args):
        nonlocal current_round_index, current_pairing_index
        sel = round_var.get()
        if sel.startswith("Round "):
            r = int(sel.split()[1])
            rounds_sorted = sorted(completed_rounds.keys())
            if r in rounds_sorted:
                current_round_index = rounds_sorted.index(r)
                current_pairing_index = 0
                load_current_pairing()
    def load_current_pairing():
        nonlocal current_round_index, current_pairing_index
        if not result_rounds:
            pairing_label.configure(text="No round paired yet.")
            return
        current_round = result_rounds[current_round_index]
        if current_pairing_index < 0 or current_pairing_index >= len(current_round):
            pairing_label.configure(text="No pairing")
            return
        p1, p2, first = current_round[current_pairing_index]
        pairing_label.configure(text=f"Pairing {current_pairing_index+1}/{len(current_round)}: {p1} vs {p2} (First: {first})")
        score1_entry.delete(0, "end")
        score2_entry.delete(0, "end")
        round_num = sorted(completed_rounds.keys())[current_round_index]
        if round_num in results_by_round and len(results_by_round[round_num]) > current_pairing_index:
            res = results_by_round[round_num][current_pairing_index]
            if res:
                s1, s2 = res
                score1_entry.insert(0, str(s1))
                score2_entry.insert(0, str(s2))
    def prev_pairing():
        nonlocal current_pairing_index
        if current_pairing_index > 0:
            current_pairing_index -= 1
            load_current_pairing()
    def next_pairing():
        nonlocal current_pairing_index
        if result_rounds and current_pairing_index < len(result_rounds[current_round_index]) - 1:
            current_pairing_index += 1
            load_current_pairing()
    round_var.trace("w", on_round_selected)
    prev_button.configure(command=prev_pairing)
    next_button.configure(command=next_pairing)
    def get_player_id_by_name_ind(tournament_id, name):
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM players WHERE tournament_id = ? AND name = ?", (tournament_id, name))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    def submit_result():
        nonlocal current_pairing_index
        if not result_rounds:
            return
        current_round = result_rounds[current_round_index]
        pairing = current_round[current_pairing_index]
        p1, p2, first = pairing
        if p1 == "BYE" or p2 == "BYE":
            show_toast(tab_frame, "BYE pairing. No result needed.")
            next_pairing()
            return
        try:
            score1 = int(score1_entry.get().strip())
            score2 = int(score2_entry.get().strip())
        except ValueError:
            show_toast(tab_frame, "Please enter valid numeric scores.")
            return
        round_num = sorted(completed_rounds.keys())[current_round_index]
        if round_num not in results_by_round:
            results_by_round[round_num] = [None] * len(current_round)
        results_by_round[round_num][current_pairing_index] = (score1, score2)
        recalc_player_stats()
        show_toast(tab_frame, f"Result submitted/updated for pairing {current_pairing_index+1}.")
    submit_button.configure(command=submit_result)
    load_rounds()
    refresh_button = ctk.CTkButton(tab_frame, text="Reload Rounds", command=load_rounds)
    refresh_button.pack(pady=5)

#####################################
# Prize Table Function
#####################################
def setup_prize_table(tab_frame):
    global prize_table
    label = ctk.CTkLabel(tab_frame, text="Prize Table", font=("Arial", 18))
    label.pack(pady=10)
    prize_name_entry = ctk.CTkEntry(tab_frame, placeholder_text="Prize Name")
    prize_name_entry.pack(pady=5)
    prize_type_var = ctk.StringVar(value="Monetary")
    prize_type_menu = ctk.CTkOptionMenu(tab_frame, variable=prize_type_var, values=["Monetary", "Non-Monetary"])
    prize_type_menu.pack(pady=5)
    currency_entry = ctk.CTkEntry(tab_frame, placeholder_text="Currency (e.g., USD)")
    currency_entry.pack(pady=5)
    amount_entry = ctk.CTkEntry(tab_frame, placeholder_text="Amount or Description")
    amount_entry.pack(pady=5)
    prize_list_text = ctk.CTkTextbox(tab_frame, width=400, height=200)
    prize_list_text.pack(pady=10)
    prize_list_text.insert("end", "Current Prizes:\n")
    prize_list_text.configure(state="disabled")
    def update_prize_list():
        prize_list_text.configure(state="normal")
        prize_list_text.delete("1.0", "end")
        prize_list_text.insert("end", "Current Prizes:\n")
        for prize in prize_table:
            if prize["prize_type"] == "Monetary":
                prize_list_text.insert("end", f'{prize["prize_name"]}: {prize["currency"]} {prize["amount"]}\n')
            else:
                prize_list_text.insert("end", f'{prize["prize_name"]}: {prize["prize_description"]}\n')
        prize_list_text.configure(state="disabled")
    def add_prize():
        name = prize_name_entry.get().strip()
        ptype = prize_type_var.get()
        if name == "":
            show_toast(tab_frame, "Enter prize name.")
            return
        if ptype == "Monetary":
            currency = currency_entry.get().strip()
            amount = amount_entry.get().strip()
            if currency == "" or amount == "":
                show_toast(tab_frame, "Enter currency and amount.")
                return
            try:
                amount = float(amount)
            except ValueError:
                show_toast(tab_frame, "Invalid amount.")
                return
            prize_table.append({"prize_name": name, "prize_type": ptype, "currency": currency, "amount": amount})
        else:
            description = amount_entry.get().strip()
            prize_table.append({"prize_name": name, "prize_type": ptype, "prize_description": description})
        update_prize_list()
        prize_name_entry.delete(0, "end")
        currency_entry.delete(0, "end")
        amount_entry.delete(0, "end")
    add_prize_button = ctk.CTkButton(tab_frame, text="Add Prize", command=add_prize)
    add_prize_button.pack(pady=5)
    def save_tab():
        show_toast(tab_frame, "Tab data saved.")
    tab_save_button = ctk.CTkButton(tab_frame, text="Save Tab", command=save_tab)
    tab_save_button.pack(pady=5)

#####################################
# Reports Function
#####################################
def setup_reports(tab_frame):
    label = ctk.CTkLabel(tab_frame, text="Reports & Exports", font=("Arial", 18))
    label.pack(pady=10)
    info_label = ctk.CTkLabel(tab_frame, text="Report generation functionality coming soon!", font=("Arial", 14))
    info_label.pack(pady=10)

#####################################
# Render Function
#####################################
def setup_render(tab_frame):
    global current_tournament_id, app
    label = ctk.CTkLabel(tab_frame, text="Render Current Tournament", font=("Arial", 18))
    label.pack(pady=10)
    def render_current_tournament():
        if current_tournament_id is None:
            show_toast(tab_frame, "No current tournament available.")
            return
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name, date, venue FROM tournaments WHERE id = ?", (current_tournament_id,))
        result = cursor.fetchone()
        conn.close()
        if result is None:
            show_toast(tab_frame, "Tournament details not found.")
            return
        tournament_name, tournament_date, tournament_venue = result
        try:
            url = generate_tournament_html(current_tournament_id, tournament_name, tournament_date)
        except Exception as e:
            messagebox.showerror("Render Error", f"An error occurred during rendering: {e}")
            return
        webbrowser.open(url)
    render_button = ctk.CTkButton(tab_frame, text="Render Current Tournament", command=render_current_tournament)
    render_button.pack(pady=10)

#####################################
# UI Tab Building Functions
#####################################
def build_tab_view(parent):
    if current_mode_view == "general":
        tabs = ["Tournament Setup", "Player Registration", "Pairings", "Enter Results", "Prize Table", "Reports & Exports", "Render"]
    elif current_mode_view == "team":
        tabs = ["Tournament Setup", "Player Registration", "Team Pairings", "Team Results", "Prize Table", "Render"]
    else:
        tabs = []
    tab_view = ctk.CTkTabview(parent, width=880, height=700)
    tab_view.pack(fill="both", expand=True)
    for tab in tabs:
        tab_view.add(tab)
        if current_mode_view == "general" and tab == "Pairings":
            setup_pairings(tab_view.tab(tab))
        elif current_mode_view == "general":
            if tab in ("Reports & Exports", "Render"):
                setup_tab_content_without_save(tab_view.tab(tab), tab)
            else:
                setup_tab_content(tab, tab_view.tab(tab))
        elif current_mode_view == "team":
            if tab == "Team Pairings":
                setup_pairings(tab_view.tab(tab))
            elif tab == "Team Results":
                setup_team_results_ui(tab_view.tab(tab))
            else:
                if tab in ("Reports & Exports", "Render"):
                    setup_tab_content_without_save(tab_view.tab(tab), tab)
                else:
                    setup_tab_content(tab, tab_view.tab(tab))
    return tab_view

def rebuild_tab_view():
    global main_frame_global
    for widget in main_frame_global.winfo_children():
        widget.destroy()
    return build_tab_view(main_frame_global)

def switch_mode_toggle():
    """
    Toggle between General and Team Round Robin modes.
    """
    global current_mode_view, tournament_mode
    if current_mode_view == "general":
        current_mode_view = "team"
        tournament_mode = "Team Round Robin"
    else:
        current_mode_view = "general"
        tournament_mode = "General"
    rebuild_tab_view()
    show_toast(app, f"Switched to {current_mode_view.capitalize()} Mode.")

def setup_tab_content(tab_name, tab_frame):
    if tab_name == "Tournament Setup":
        setup_tournament_setup(tab_frame)
    elif tab_name == "Player Registration":
        setup_player_registration(tab_frame)
    elif tab_name == "Pairings" or tab_name == "Team Pairings":
        setup_pairings(tab_frame)
    elif tab_name == "Enter Results":
        setup_enter_results(tab_frame)
    elif tab_name == "Team Results":
        setup_team_results_ui(tab_frame)
    elif tab_name == "Prize Table":
        setup_prize_table(tab_frame)
    elif tab_name == "Reports & Exports":
        setup_reports(tab_frame)
    elif tab_name == "Render":
        setup_render(tab_frame)
    else:
        label = ctk.CTkLabel(tab_frame, text=tab_name, font=("Arial", 18))
        label.pack(pady=20)
    def save_tab():
        show_toast(tab_frame, "Tab data saved.")
    tab_save_button = ctk.CTkButton(tab_frame, text="Save Tab", command=save_tab)
    tab_save_button.pack(pady=5)

def setup_tab_content_without_save(tab_frame, tab_name):
    if tab_name == "Reports & Exports":
        setup_reports(tab_frame)
    elif tab_name == "Render":
        setup_render(tab_frame)
    else:
        label = ctk.CTkLabel(tab_frame, text=tab_name, font=("Arial", 18))
        label.pack(pady=20)

#####################################
# Main Application
#####################################
def main():
    global app, status_label, main_frame_global
    initialize_database()
    ctk.set_appearance_mode("dark")
    app = ctk.CTk()
    app.geometry("1200x900")
    app.title("Direktor EXE")
    apply_theme(app)
    
    sidebar_frame = ctk.CTkFrame(app, width=200, corner_radius=0)
    sidebar_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
    
    save_button = ctk.CTkButton(sidebar_frame, text="Save Tournament", command=save_current_tournament)
    save_button.pack(pady=10, padx=10)
    
    load_button = ctk.CTkButton(sidebar_frame, text="Load Tournament", command=load_tournament)
    load_button.pack(pady=10, padx=10)
    
    toggle_button = ctk.CTkButton(sidebar_frame, text="Toggle Mode (General/Team)", command=switch_mode_toggle)
    toggle_button.pack(pady=10, padx=10)
    
    quit_button = ctk.CTkButton(sidebar_frame, text="Quit App", command=quit_app)
    quit_button.pack(pady=10, padx=10)
    
    main_frame_global = ctk.CTkFrame(app)
    main_frame_global.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)
    
    build_tab_view(main_frame_global)
    
    status_label = ctk.CTkLabel(app, text="No tournament loaded.", font=("Arial", 12))
    status_label.grid(row=1, column=0, columnspan=2, sticky="we", padx=10, pady=5)
    update_status()
    
    app.mainloop()

if __name__ == "__main__":
    main()
