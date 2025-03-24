"""
Direktor EXE – Scrabble Tournament Manager
Updated main.py with improved organization and features

Features:
  • General mode only (team mode removed).
  • Tournament Setup with tournament name, date, venue, connection type selection (Local IP, Render URL, FTP),
    and sponsor logo upload.
  • Automatic generation of a tournament folder (inside "rendered/tournaments") based on the tournament name.
  • All HTML outputs (index, roster, standings, prize table, pairing pages) are generated into that folder so that relative links work correctly.
  • A Flask web server is started and shareable URLs are generated using the public IP or a custom domain provided by the user.
  • The "Enter Results" tab lets the user manually enter or update match scores for each pairing.
  • The Prize Table tab provides a UI for setting up both monetary and non‑monetary prizes (with a searchable currency selector).
  • The Event Coverage Index is regenerated on demand (when clicking Render) to reflect the latest data.
  • Pairings are generated using several pairing systems (Round Robin, Random Pairing, King of the Hills, Australian Draw, Lagged Australian).
  • A new "FTP Settings" tab lets the user enter FTP Host, Username, and Password. When the user clicks "Mirror Website", the tournament folder is uploaded via FTP to their host, and the shareable link is updated.
  • A new remote results submission feature is added via Flask:
       – A custom HTTP endpoint (/submit_results) is served.
       – Players can access a web form to paste their match ID and submit scores.
       – The system validates submissions (including duplicate checking) and updates tournament results.
  • A persistent sidebar provides "Save Tournament", "Load Tournament", and "Quit App" buttons.
       – "Save Tournament" saves the complete tournament progress as a .TOU file.
       – "Load Tournament" lets the user resume a saved tournament.
       – "Quit App" exits the application.
  • New: When a new tournament is created, player numbering resets (the first player added gets player_number 1 for that tournament).
  • The generated HTML pages now include a <base> tag (with base_href set to "./") for proper relative URL resolution.
  • Sponsor Logos can be uploaded via their own tab.
  • Local IP, Render URL, and FTP mirroring are available for connection.
  • A Stats feature is available via the Reports tab (with a "Show Current Stats" button stubbed to update stats).
  • Overall UX enhancements include improved layout, clear feedback messages, tooltips, and robust error handling.

Author: Manuelito
"""

##################################
# Imports and Global Variables
##################################
import customtkinter as ctk
import os, re, shutil, webbrowser, sqlite3, threading, socket, random, json, ftplib
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
from functools import partial
from data.database import create_connection, create_tables, insert_player, insert_tournament, get_all_tournaments, get_all_players, get_players_for_tournament
from pairings import round_robin_rounds, assign_firsts, random_pairings, king_of_the_hills_pairings, australian_draw_pairings, lagged_australian_pairings
from theme import set_theme_mode, apply_theme
from utils import get_local_ip, get_tournament_folder, recalculate_player_stats
from server import run_flask_app

# Import all currencies
all_currencies = [
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY",
    "COP", "CRC", "CUC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD",
    "EGP", "ERN", "ETB", "EUR", "FJD", "FKP", "FOK", "GBP", "GEL", "GGP",
    "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG",
    "HUF", "IDR", "ILS", "IMP", "INR", "IQD", "IRR", "ISK", "JEP", "JMD",
    "JOD", "JPY", "KES", "KGS", "KHR", "KID", "KMF", "KRW", "KWD", "KYD",
    "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD", "MAD", "MDL", "MGA",
    "MKD", "MMK", "MNT", "MOP", "MRU", "MUR", "MVR", "MWK", "MXN", "MYR",
    "MZN", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "OMR", "PAB", "PEN",
    "PGK", "PHP", "PKR", "PLN", "PYG", "QAR", "RON", "RSD", "RUB", "RWF",
    "SAR", "SBD", "SCR", "SDG", "SEK", "SGD", "SHP", "SLL", "SOS", "SRD",
    "SSP", "STN", "SYP", "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY",
    "TTD", "TVD", "TWD", "TZS", "UAH", "UGX", "USD", "UYU", "UZS", "VES",
    "VND", "VUV", "WST", "XAF", "XCD", "XDR", "XOF", "XPF", "YER", "ZAR",
    "ZMW", "ZWL"
]

# Global variables
server_thread = None
HTTP_PORT = int(os.environ.get("PORT", 8000))
current_tournament_id = None
session_players = []
prize_table = []
tournament_mode = "General"
teams_list = []       # Not used in general mode
team_size = 0         # Not used in general mode
last_pairing_system = "Round Robin"
last_team_size = 3    # Not used
current_round_number = 0
completed_rounds = {}
results_by_round = {}
team_round_results = {}   # Not used
desired_rr_rounds = None
app = None
status_label = None
main_frame_global = None
shareable_link = ""
full_round_robin_schedule = None
public_ip = ""  # Will store public IP or custom domain
sponsor_logos = ""  # Holds sponsor logo file paths

# HTML header with <base> tag – base_href will be injected via .format()
#header_html = """<head>
#  <meta charset="UTF-8">
#  <meta name="viewport" content="width=device-width, initial-scale=1">
#  <base href="{0}">
#  <title>Tournament</title>
#  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
#  <style>
#    body { background-color: #f8f9fa; color: #343a40; }
#    .container-custom { max-width:800px; margin:auto; }
#    footer { margin-top: 40px; font-size: 0.9em; text-align: center; padding: 20px 0; }
#  </style>
#</head>"""

# Replace the header_html variable definition with this function
def get_header_html(base_href):
    return f"""<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <base href="{base_href}">
  <title>Tournament</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background-color: #f8f9fa; color: #343a40; }}
    .container-custom {{ max-width:800px; margin:auto; }}
    footer {{ margin-top: 40px; font-size: 0.9em; text-align: center; padding: 20px 0; }}
  </style>
</head>"""

##################################
# Toast Notification Function
##################################
def show_toast(parent, message, duration=2000):
    toast = ctk.CTkToplevel(parent)
    toast.geometry("300x50+500+300")
    toast.overrideredirect(True)
    label = ctk.CTkLabel(toast, text=message, font=("Arial", 12))
    label.pack(expand=True, fill="both")
    toast.after(duration, toast.destroy)

##################################
# Folder & File Helpers
##################################
def finalize_tournament_html(tournament_name, generated_filename):
    folder = get_tournament_folder(tournament_name)
    dest_file = os.path.join(folder, "index.html")
    if os.path.abspath(generated_filename) != os.path.abspath(dest_file):
        shutil.copyfile(generated_filename, dest_file)
    return dest_file

##################################
# Database & Save/Load Functions
##################################
def update_tournament_link(tournament_id, link):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tournaments SET shareable_link = ? WHERE id = ?", (link, tournament_id))
    conn.commit()
    conn.close()

def save_current_tournament():
    global current_tournament_id, app, tournament_mode, teams_list, team_size, current_round_number, completed_rounds, results_by_round, last_pairing_system, last_team_size
    if current_tournament_id is None:
        show_toast(app, "No tournament to save.")
        return
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, date, venue, shareable_link FROM tournaments WHERE id = ?", (current_tournament_id,))
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
             "last_result": p[6], "scorecard": p[7], "team": p[8], "player_number": p[9]} for p in players
        ],
        "progress": {
            "current_round_number": current_round_number,
            "completed_rounds": completed_rounds,
            "results_by_round": results_by_round,
            "last_pairing_system": last_pairing_system,
            "last_team_size": last_team_size
        }
    }
    tournament_name = tournament_data[1]
    folder = get_tournament_folder(tournament_name)
    filename = os.path.join(folder, f"{tournament_name}_progress.tou")
    with open(filename, "w") as f:
        json.dump(data, f)
    show_toast(app, f"Tournament saved successfully at {filename}.")

def load_tournament():
    global current_tournament_id, session_players, app, tournament_mode, teams_list, team_size, current_round_number, completed_rounds, results_by_round, last_pairing_system, last_team_size
    if not confirm_discard():
        return
    initial_dir = os.path.join(os.getcwd(), "rendered", "tournaments")
    filename = fd.askopenfilename(initialdir=initial_dir, filetypes=[("Tournament Files", "*.tou")])
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
        session_players = [(p["name"], p["rating"], p["wins"], p["losses"], p["spread"],
                             p.get("last_result", ""), p.get("scorecard", ""), p.get("team", ""), p.get("player_number", 1)) for p in players]
        current_round_number = progress.get("current_round_number", 0)
        completed_rounds = progress.get("completed_rounds", {})
        results_by_round = progress.get("results_by_round", {})
        last_pairing_system = progress.get("last_pairing_system", "Round Robin")
        last_team_size = progress.get("last_team_size", 3)
        show_toast(app, "Tournament loaded successfully.")
        update_status()

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
        ans = messagebox.askyesnocancel("Confirm", "Do you want to save the current tournament before proceeding?")
        if ans is None:
            return False
        if ans:
            save_current_tournament()
    return True

def quit_app():
    global app
    if messagebox.askyesnocancel("Confirm Quit", "Are you sure you want to quit?"):
        app.destroy()

def initialize_database():
    conn = create_connection()
    create_tables(conn)
    conn.close()

##################################
# Pairing System Functions (General Mode Only)
##################################
def has_played(player1, player2):
    for rnd in completed_rounds.values():
        for pairing in rnd:
            if set(pairing[:2]) == set([player1, player2]):
                return True
    return False

def compute_lagged_standings(players, round_limit):
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

def generate_general_pairings(players, system_choice):
    if system_choice == "Round Robin":
        names = [p[1] for p in players]
        full_round_robin_schedule = assign_firsts(round_robin_rounds(names))
        global desired_rr_rounds, current_round_number, completed_rounds
        max_rounds = len(full_round_robin_schedule)
        desired_rr_rounds = simpledialog.askinteger(
            "Round Robin Schedule",
            f"A full round robin schedule for {len(players)} players is completed in {max_rounds} rounds.\nHow many rounds do you want to generate?",
            minvalue=1,
            maxvalue=max_rounds
        )
        for r in range(1, desired_rr_rounds + 1):
            completed_rounds[r] = full_round_robin_schedule[r - 1]
        current_round_number = desired_rr_rounds
        return full_round_robin_schedule[desired_rr_rounds - 1]
    elif system_choice == "Random Pairing":
        return random_pairings(players)
    elif system_choice == "King of the Hills Pairing":
        return king_of_the_hills_pairings(players)
    elif system_choice == "Australian Draw":
        return australian_draw_pairings(players, completed_rounds)
    elif system_choice == "Lagged Australian":
        return lagged_australian_pairings(players, current_round_number, results_by_round, completed_rounds)
    else:
        raise ValueError("Invalid pairing system specified.")

def generate_pairings_system(players, system="Round Robin", team_size=None):
    return generate_general_pairings(players, system)

##################################
# HTML Generation Functions
##################################
def generate_player_scorecard_html(player, tournament_id, out_folder):
    player_id = player[0]
    try:
        scorecard = json.loads(player[7]) if player[7] else []
    except Exception:
        scorecard = []
    rows = ""
    for entry in scorecard:
        rows += f"<tr><td>{entry.get('round', 'N/A')}</td><td>{entry.get('result', 'N/A')}</td><td>{entry.get('cumulative', 'N/A')}</td></tr>\n"
    base_href = "./"
    html = f"""<!DOCTYPE html>
<html lang="en">
{get_header_html(base_href)}
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
    <a href="./index.html" class="btn btn-secondary">Back to Standings</a>
  </div>
  <footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    out_path = os.path.join(out_folder, f"tournament_{tournament_id}_player_{player_id}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"tournament_{tournament_id}_player_{player_id}.html"

def generate_tournament_html(tournament_id, tournament_name, tournament_date):
    out_folder = get_tournament_folder(tournament_name)
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
        schedule = []
    pairing_round_links = []
    base = f"tournament_{tournament_id}"
    index_file = "index.html"
    roster_file = f"tournament_{tournament_id}_roster.html"
    standings_file = f"tournament_{tournament_id}_standings.html"
    prize_file = f"tournament_{tournament_id}_prize.html"
    base_href = "./"
    for idx, round_pairings in enumerate(schedule, start=1):
        round_file = f"tournament_{tournament_id}_pairings_round_{idx}.html"
        pairing_round_links.append((idx, round_file))
        pairing_content = f"<h2>Round {idx} Pairings</h2>\n<table class='table table-bordered'><thead><tr><th>#</th><th>Pairing</th><th>First</th><th>Match ID</th></tr></thead><tbody>"
        for i, pairing in enumerate(round_pairings, start=1):
            match_id = f"R{idx}-M{i}"
            if len(pairing) == 3:
                p1, p2, first = pairing
            elif len(pairing) == 2:
                p1, p2 = pairing
                first = random.choice([p1, p2])
            else:
                p1, p2, first = "???", "???", "???"
            pairing_str = f"{p1} vs {p2}"
            pairing_content += f"<tr><td>{i}</td><td>{pairing_str}</td><td>{first}</td><td>{match_id} <button onclick='navigator.clipboard.writeText(\"{match_id}\")'>Copy</button></td></tr>"
        pairing_content += "</tbody></table>"
        
        navbar_html = f"""<nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
  <div class="container">
    <a class="navbar-brand" href="./index.html"></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
            data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" 
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="./index.html">Home</a></li>
        <li class="nav-item"><a class="nav-link" href="./{roster_file}">Roster</a></li>
        <li class="nav-item"><a class="nav-link" href="./{standings_file}">Standings</a></li>
        <li class="nav-item"><a class="nav-link" href="./{prize_file}">Prize Table</a></li>
      </ul>
    </div>
  </div>
</nav>"""
        footer_section = '<footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>'
        pairing_page = f"""<!DOCTYPE html>
<html lang="en">
{get_header_html(base_href)}
<body>
  {navbar_html}
  <div class="container container-custom">
    <h1 class="mb-3">{tournament_name_db}</h1>
    {pairing_content}
    <a href="./index.html" class="btn btn-secondary">Back to Index</a>
  </div>
  {footer_section}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
        with open(os.path.join(out_folder, round_file), "w", encoding="utf-8") as f:
            f.write(pairing_page)
    roster_rows = ""
    for idx, p in enumerate(players, start=1):
        if len(p) > 10 and p[10]:
            country = p[10].strip().lower()
            flag_html = f'<img src="https://flagcdn.com/16x12/{country}.png">'
        else:
            flag_html = ""
        roster_rows += f"<tr><td>{idx}</td><td>{p[1]} {flag_html}</td><td>{p[2]}</td></tr>\n"
    roster_html = f"""<!DOCTYPE html>
<html lang="en">
{get_header_html(base_href)}
<body>
  <div class="container container-custom">
    <h1 class="mt-4">Player Roster - {tournament_name_db}</h1>
    <table class="table table-striped">
      <thead><tr><th>#</th><th>Name</th><th>Rating</th></tr></thead>
      <tbody>
        {roster_rows if roster_rows else '<tr><td colspan="3">No players registered.</td></tr>'}
      </tbody>
    </table>
    <a href="./index.html" class="btn btn-secondary">Back to Index</a>
  </div>
  <footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    roster_path = os.path.join(out_folder, roster_file)
    with open(roster_path, "w", encoding="utf-8") as f:
        f.write(roster_html)
    sorted_players = sorted(players, key=lambda x: (x[3], x[5]), reverse=True)
    standings_rows = ""
    for rank, player in enumerate(sorted_players, start=1):
        scorecard_link = generate_player_scorecard_html(player, tournament_id, out_folder)
        if len(player) > 10 and player[10]:
            country = player[10].strip().lower()
            flag_html = f'<img src="https://flagcdn.com/16x12/{country}.png">'
        else:
            flag_html = ""
        standings_rows += f"<tr><td>{rank}</td><td><a href='./{scorecard_link}'>{player[1]} {flag_html}</a></td><td>{player[3]}</td><td>{player[4]}</td><td>{player[5]}</td><td>{player[6]}</td></tr>\n"
    standings_html = f"""<!DOCTYPE html>
<html lang="en">
{get_header_html(base_href)}
<body>
  <div class="container container-custom">
    <h1 class="mt-4">Standings - {tournament_name_db}</h1>
    <table class="table table-hover">
      <thead>
        <tr><th>Rank</th><th>Name</th><th>Wins</th><th>Losses</th><th>Spread</th><th>Last Result</th></tr>
      </thead>
      <tbody>
        {standings_rows if standings_rows else '<tr><td colspan="6">No standings available.</td></tr>'}
      </tbody>
    </table>
    <a href="./index.html" class="btn btn-secondary">Back to Index</a>
  </div>
  <footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    standings_path = os.path.join(out_folder, standings_file)
    with open(standings_path, "w", encoding="utf-8") as f:
        f.write(standings_html)
    prize_rows = ""
    for prize in prize_table:
        if prize["prize_type"] == "Monetary":
            prize_rows += f"<tr><td>{prize['prize_name']}</td><td>{prize['currency']} {prize['amount']}</td></tr>\n"
        else:
            prize_rows += f"<tr><td>{prize['prize_name']}</td><td>{prize['prize_description']}</td></tr>\n"
    prize_html = f"""<!DOCTYPE html>
<html lang="en">
{get_header_html(base_href)}
<body>
  <div class="container container-custom">
    <h1 class="mt-4">Prize Table - {tournament_name_db}</h1>
    <table class="table table-bordered">
      <thead><tr><th>Prize Name</th><th>Details</th></tr></thead>
      <tbody>
        {prize_rows if prize_rows else '<tr><td colspan="2">No prizes set.</td></tr>'}
      </tbody>
    </table>
    <a href="./index.html" class="btn btn-secondary">Back to Index</a>
  </div>
  <footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    prize_path = os.path.join(out_folder, prize_file)
    with open(prize_path, "w", encoding="utf-8") as f:
        f.write(prize_html)
    round_links_html = ""
    for r, link in pairing_round_links:
        round_links_html += f"<li class='list-group-item'><a href='./{link}'>Round {r} Pairings</a></li>\n"
    navbar_html = f"""<nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
  <div class="container">
    <a class="navbar-brand" href="./index.html"></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
            data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" 
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="./index.html">Home</a></li>
        <li class="nav-item"><a class="nav-link" href="./{roster_file}">Roster</a></li>
        <li class="nav-item"><a class="nav-link" href="./{standings_file}">Standings</a></li>
        <li class="nav-item"><a class="nav-link" href="./{prize_file}">Prize Table</a></li>
      </ul>
    </div>
  </div>
</nav>"""
    footer_section = '<footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>'
    folder_name = re.sub(r'[\\/*?:"<>|]', "", tournament_name).replace(" ", "_")
    # If public_ip starts with http:// or https://, do not append the port.
    if public_ip.startswith("http://") or public_ip.startswith("https://"):
        shareable = f"{public_ip}/tournaments/{folder_name}"
    else:
        shareable = f"http://{public_ip}:{HTTP_PORT}/tournaments/{folder_name}"
    index_html = f"""<!DOCTYPE html>
<html lang="en">
{get_header_html(base_href)}
<body>
  {navbar_html}
  <div class="container container-custom">
    <h1 class="mb-3">{tournament_name_db}</h1>
    <p class="lead">{tournament_date_db} | {tournament_venue}</p>
    <h2 class="mt-4">Event Coverage Index</h2>
    <ul class="list-group">
      <li class="list-group-item"><a href="./{roster_file}">Player Roster</a></li>
      {round_links_html}
      <li class="list-group-item"><a href="./{standings_file}">Standings</a></li>
      <li class="list-group-item"><a href="./{prize_file}">Prize Table</a></li>
    </ul>
    <br>
    <a href="/submit_results" class="btn btn-primary">Submit Results</a>
    <br><br>
    <p>Shareable URL: <a href="{shareable}">{shareable}</a></p>
  </div>
  {footer_section}
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    index_path = os.path.join(out_folder, index_file)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    return index_path

##################################
# FTP Functions
##################################
def ftp_upload_dir(ftp, local_dir, remote_dir):
    try:
        ftp.mkd(remote_dir)
    except Exception:
        pass
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        if os.path.isfile(local_path):
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_path}", f)
        elif os.path.isdir(local_path):
            ftp_upload_dir(ftp, local_path, remote_path)

def mirror_website_via_ftp(ftp_host, ftp_user, ftp_pass):
    try:
        ftp = ftplib.FTP(ftp_host)
        ftp.login(ftp_user, ftp_pass)
    except Exception as e:
        messagebox.showerror("FTP Error", f"FTP login failed: {e}")
        return None
    if current_tournament_id is None:
        messagebox.showerror("Error", "No tournament loaded.")
        return None
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM tournaments WHERE id = ?", (current_tournament_id,))
    result = cursor.fetchone()
    conn.close()
    if not result:
        messagebox.showerror("Error", "Tournament not found.")
        return None
    tournament_name = result[0]
    local_dir = get_tournament_folder(tournament_name)
    remote_dir = tournament_name.replace(" ", "_")
    ftp_upload_dir(ftp, local_dir, remote_dir)
    ftp.quit()
    new_link = f"http://{ftp_host}/{remote_dir}/index.html"
    return new_link

##################################
# Player Stats Recalculation
##################################
def recalc_player_stats():
    global current_tournament_id, completed_rounds, results_by_round
    if current_tournament_id is None:
        return
    
    conn = create_connection()
    cursor = conn.cursor()
    
    # Get all players for the current tournament
    players = get_players_for_tournament(current_tournament_id)
    
    # Reset player stats
    for player in players:
        player_id = player[0]
        cursor.execute("""
            UPDATE players 
            SET wins = 0, losses = 0, spread = 0, last_result = '', scorecard = '[]'
            WHERE id = ?
        """, (player_id,))
    
    # Process results by round
    for round_num in sorted(results_by_round.keys()):
        round_pairings = completed_rounds.get(round_num, [])
        round_results = results_by_round.get(round_num, [])
        
        for i, pairing in enumerate(round_pairings):
            if i >= len(round_results) or round_results[i] is None:
                continue
                
            p1_name, p2_name, _ = pairing
            score1, score2 = round_results[i]
            
            # Skip BYE pairings
            if p1_name == "BYE" or p2_name == "BYE":
                continue
                
            # Find player IDs
            cursor.execute("SELECT id FROM players WHERE name = ? AND tournament_id = ?", (p1_name, current_tournament_id))
            p1_id_result = cursor.fetchone()
            cursor.execute("SELECT id FROM players WHERE name = ? AND tournament_id = ?", (p2_name, current_tournament_id))
            p2_id_result = cursor.fetchone()
            
            if not p1_id_result or not p2_id_result:
                continue
                
            p1_id = p1_id_result[0]
            p2_id = p2_id_result[0]
            
            # Update player 1 stats
            if score1 > score2:
                # Win
                cursor.execute("""
                    UPDATE players 
                    SET wins = wins + 1, spread = spread + ?, last_result = ?
                    WHERE id = ?
                """, (score1 - score2, f"W {score1}-{score2}", p1_id))
            elif score1 < score2:
                # Loss
                cursor.execute("""
                    UPDATE players 
                    SET losses = losses + 1, spread = spread - ?, last_result = ?
                    WHERE id = ?
                """, (score2 - score1, f"L {score1}-{score2}", p1_id))
            else:
                # Tie
                cursor.execute("""
                    UPDATE players 
                    SET wins = wins + 0.5, losses = losses + 0.5, last_result = ?
                    WHERE id = ?
                """, (f"T {score1}-{score2}", p1_id))
                
            # Update player 2 stats
            if score2 > score1:
                # Win
                cursor.execute("""
                    UPDATE players 
                    SET wins = wins + 1, spread = spread + ?, last_result = ?
                    WHERE id = ?
                """, (score2 - score1, f"W {score2}-{score1}", p2_id))
            elif score2 < score1:
                # Loss
                cursor.execute("""
                    UPDATE players 
                    SET losses = losses + 1, spread = spread - ?, last_result = ?
                    WHERE id = ?
                """, (score1 - score2, f"L {score2}-{score1}", p2_id))
            else:
                # Tie
                cursor.execute("""
                    UPDATE players 
                    SET wins = wins + 0.5, losses = losses + 0.5, last_result = ?
                    WHERE id = ?
                """, (f"T {score2}-{score1}", p2_id))
    
    # Update scorecards
    for player in players:
        player_id = player[0]
        player_name = player[1]
        
        scorecard = []
        cumulative_spread = 0
        
        for round_num in sorted(results_by_round.keys()):
            round_pairings = completed_rounds.get(round_num, [])
            round_results = results_by_round.get(round_num, [])
            
            for i, pairing in enumerate(round_pairings):
                if i >= len(round_results) or round_results[i] is None:
                    continue
                    
                p1_name, p2_name, _ = pairing
                score1, score2 = round_results[i]
                
                # Skip BYE pairings
                if p1_name == "BYE" or p2_name == "BYE":
                    continue
                    
                if player_name == p1_name:
                    opponent = p2_name
                    if score1 > score2:
                        result = f"W {score1}-{score2}"
                        cumulative_spread += (score1 - score2)
                    elif score1 < score2:
                        result = f"L {score1}-{score2}"
                        cumulative_spread -= (score2 - score1)
                    else:
                        result = f"T {score1}-{score2}"
                    
                    scorecard.append({
                        "round": round_num,
                        "opponent": opponent,
                        "result": result,
                        "cumulative": cumulative_spread
                    })
                    
                elif player_name == p2_name:
                    opponent = p1_name
                    if score2 > score1:
                        result = f"W {score2}-{score1}"
                        cumulative_spread += (score2 - score1)
                    elif score2 < score1:
                        result = f"L {score2}-{score1}"
                        cumulative_spread -= (score1 - score2)
                    else:
                        result = f"T {score2}-{score1}"
                    
                    scorecard.append({
                        "round": round_num,
                        "opponent": opponent,
                        "result": result,
                        "cumulative": cumulative_spread
                    })
        
        # Update scorecard in database
        cursor.execute("""
            UPDATE players 
            SET scorecard = ?
            WHERE id = ?
        """, (json.dumps(scorecard), player_id))
    
    conn.commit()
    conn.close()

##################################
# UI Functions: Sponsor Logos Tab
##################################
def setup_sponsor_logos(tab_frame):
    global sponsor_logos
    for widget in tab_frame.winfo_children():
        widget.destroy()
    label = ctk.CTkLabel(tab_frame, text="Sponsor Logos", font=("Arial", 18))
    label.pack(pady=10)
    def upload_logo():
        file_path = fd.askopenfilename(title="Select Sponsor Logo", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
        if file_path:
            logos_dir = os.path.join(os.getcwd(), "rendered", "sponsor_logos")
            os.makedirs(logos_dir, exist_ok=True)
            base_name = os.path.basename(file_path)
            dest_path = os.path.join(logos_dir, base_name)
            shutil.copy(file_path, dest_path)
            if sponsor_logos:
                sponsor_logos += "," + dest_path
            else:
                sponsor_logos = dest_path
            messagebox.showinfo("Success", "Logo uploaded successfully.")
    upload_button = ctk.CTkButton(tab_frame, text="Upload Sponsor Logo", command=upload_logo)
    upload_button.pack(pady=10)
    logos_label = ctk.CTkLabel(tab_frame, text="Uploaded Logos:")
    logos_label.pack(pady=5)
    logos_text = ctk.CTkTextbox(tab_frame, width=400, height=100)
    logos_text.pack(pady=5)
    def refresh_logos():
        logos_text.configure(state="normal")
        logos_text.delete("1.0", "end")
        if sponsor_logos:
            for logo in sponsor_logos.split(","):
                logos_text.insert("end", logo.strip() + "\n")
        else:
            logos_text.insert("end", "No sponsor logos uploaded.")
        logos_text.configure(state="disabled")
    refresh_logos()

##################################
# UI Functions: Prize Table Tab
##################################
def setup_prize_table(tab_frame):
    for widget in tab_frame.winfo_children():
        widget.destroy()
    label = ctk.CTkLabel(tab_frame, text="Prize Table Setup", font=("Arial", 18))
    label.pack(pady=10)
    entry_frame = ctk.CTkFrame(tab_frame)
    entry_frame.pack(pady=10)
    prize_name_label = ctk.CTkLabel(entry_frame, text="Prize Name:")
    prize_name_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    prize_name_entry = ctk.CTkEntry(entry_frame)
    prize_name_entry.grid(row=0, column=1, padx=5, pady=5)
    prize_type_label = ctk.CTkLabel(entry_frame, text="Prize Type:")
    prize_type_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
    prize_type_var = ctk.StringVar(value="Monetary")
    prize_type_menu = ctk.CTkOptionMenu(entry_frame, variable=prize_type_var, values=["Monetary", "Non-monetary"])
    prize_type_menu.grid(row=1, column=1, padx=5, pady=5)
    def update_prize_type(*args):
        if prize_type_var.get() == "Non-monetary":
            currency_label.grid_remove()
            currency_menu.grid_remove()
            amount_label.grid_remove()
            amount_entry.grid_remove()
        else:
            currency_label.grid()
            currency_menu.grid()
            amount_label.grid()
            amount_entry.grid()
    prize_type_var.trace("w", update_prize_type)
    currency_label = ctk.CTkLabel(entry_frame, text="Currency:")
    currency_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
    currency_var = ctk.StringVar(value="USD")
    currency_menu = ctk.CTkOptionMenu(entry_frame, variable=currency_var, values=all_currencies)
    currency_menu.grid(row=2, column=1, padx=5, pady=5)
    amount_label = ctk.CTkLabel(entry_frame, text="Amount:")
    amount_label.grid(row=3, column=0, padx=5, pady=5, sticky="w")
    amount_entry = ctk.CTkEntry(entry_frame)
    amount_entry.grid(row=3, column=1, padx=5, pady=5)
    description_label = ctk.CTkLabel(entry_frame, text="Description:")
    description_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")
    description_entry = ctk.CTkEntry(entry_frame)
    description_entry.grid(row=4, column=1, padx=5, pady=5)
    search_label = ctk.CTkLabel(entry_frame, text="Search Currency:")
    search_label.grid(row=5, column=0, padx=5, pady=5, sticky="w")
    search_entry = ctk.CTkEntry(entry_frame)
    search_entry.grid(row=5, column=1, padx=5, pady=5)
    def update_currency_menu(*args):
        term = search_entry.get().upper()
        filtered = [cur for cur in all_currencies if term in cur.upper()]
        if not filtered:
            filtered = ["USD"]
        currency_menu.configure(values=filtered)
        currency_var.set(filtered[0])
    search_entry.bind("<KeyRelease>", update_currency_menu)
    def add_prize():
        name = prize_name_entry.get().strip()
        ptype = prize_type_var.get()
        if not name:
            messagebox.showerror("Error", "Prize name is required.")
            return
        if ptype == "Monetary":
            currency = currency_var.get()
            try:
                amount = float(amount_entry.get().strip())
            except ValueError:
                messagebox.showerror("Error", "Enter a valid amount.")
                return
            prize = {"prize_name": name, "prize_type": "Monetary", "currency": currency, "amount": amount}
        else:
            desc = description_entry.get().strip()
            prize = {"prize_name": name, "prize_type": "Non-monetary", "prize_description": desc}
        prize_table.append(prize)
        messagebox.showinfo("Success", "Prize added.")
        prize_name_entry.delete(0, "end")
        amount_entry.delete(0, "end")
        description_entry.delete(0, "end")
        update_prize_list()
    add_button = ctk.CTkButton(tab_frame, text="Add Prize", command=add_prize)
    add_button.pack(pady=5)
    prize_list_label = ctk.CTkLabel(tab_frame, text="Current Prizes:", font=("Arial", 14))
    prize_list_label.pack(pady=5)
    prize_list_text = ctk.CTkTextbox(tab_frame, width=400, height=150)
    prize_list_text.pack(pady=5)
    def update_prize_list():
        prize_list_text.configure(state="normal")
        prize_list_text.delete("1.0", "end")
        if prize_table:
            for idx, prize in enumerate(prize_table, start=1):
                if prize["prize_type"] == "Monetary":
                    prize_list_text.insert("end", f"{idx}. {prize['prize_name']} - {prize['currency']} {prize['amount']}\n")
                else:
                    prize_list_text.insert("end", f"{idx}. {prize['prize_name']} - {prize['prize_description']}\n")
        else:
            prize_list_text.insert("end", "No prizes set.")
        prize_list_text.configure(state="disabled")
    update_prize_list()

##################################
# UI Functions: Reports & Render Tabs
##################################
def setup_reports(tab_frame):
    label = ctk.CTkLabel(tab_frame, text="Reports & Exports", font=("Arial", 18))
    label.pack(pady=10)
    stats_button = ctk.CTkButton(tab_frame, text="Show Current Stats", command=lambda: messagebox.showinfo("Stats", "Stats updated (stub)."))
    stats_button.pack(pady=5)
    info = ctk.CTkLabel(tab_frame, text="Reports functionality coming soon!", font=("Arial", 14))
    info.pack(pady=10)

def setup_render(tab_frame):
    label = ctk.CTkLabel(tab_frame, text="Render Event Coverage Index", font=("Arial", 18))
    label.pack(pady=10)
    info = ctk.CTkLabel(tab_frame, text="Click the button below to view the updated event coverage index in your browser.", font=("Arial", 14))
    info.pack(pady=10)
    render_button = ctk.CTkButton(tab_frame, text="Open Event Coverage Index", command=open_event_index)
    render_button.pack(pady=10)

def open_event_index():
    global public_ip
    if current_tournament_id is None:
        messagebox.showerror("Error", "No tournament loaded. Please create a tournament first.")
        return
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, date FROM tournaments WHERE id = ?", (current_tournament_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        tname, tdate = result
    else:
        tname, tdate = "Tournament", ""
    generated_index = generate_tournament_html(current_tournament_id, tname, tdate)
    final_index = finalize_tournament_html(tname, generated_index)
    rendered_dir = os.path.join(os.getcwd(), "rendered")
    relative_path = os.path.relpath(final_index, rendered_dir).replace(os.sep, '/')
    # If public_ip already starts with "http://" or "https://", do not append a port.
    if public_ip.startswith("http://") or public_ip.startswith("https://"):
        url = f"{public_ip}/{relative_path}"
    else:
        url = f"http://{public_ip}:{HTTP_PORT}/{relative_path}"
    webbrowser.open(url)

##################################
# UI Functions: Enter Results Tab
##################################
def setup_enter_results(tab_frame):
    label_ind = ctk.CTkLabel(tab_frame, text="Enter Results", font=("Arial", 18))
    label_ind.pack(pady=10)
    def refresh_rounds():
        rnums = sorted(completed_rounds.keys())
        if rnums:
            rvals = [f"Round {r}" for r in rnums]
        else:
            rvals = []
        round_dropdown.configure(values=rvals)
        if rvals:
            round_var.set(rvals[0])
            load_current_pairing()
        else:
            round_var.set("")
            pairing_label.configure(text="No rounds available.")
    round_var = ctk.StringVar()
    round_dropdown = ctk.CTkOptionMenu(tab_frame, variable=round_var, values=[])
    round_dropdown.pack(pady=5)
    refresh_button = ctk.CTkButton(tab_frame, text="Refresh Rounds", command=refresh_rounds)
    refresh_button.pack(pady=5)
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
    pairing_index = {"current": 0}
    def load_current_pairing():
        if round_var.get().startswith("Round "):
            sel = int(round_var.get().split()[1])
            current = completed_rounds.get(sel, [])
            idx = pairing_index["current"]
            if not current or idx < 0 or idx >= len(current):
                pairing_label.configure(text="No pairing")
            else:
                p1, p2, first = current[idx]
                pairing_label.configure(text=f"Pairing {idx+1}/{len(current)}: {p1} vs {p2} (First: {first})")
                score1_entry.delete(0, "end")
                score2_entry.delete(0, "end")
                if sel in results_by_round and len(results_by_round[sel]) > idx and results_by_round[sel][idx] is not None:
                    s1, s2 = results_by_round[sel][idx]
                    score1_entry.insert(0, str(s1))
                    score2_entry.insert(0, str(s2))
    def on_round_selected(*args):
        pairing_index["current"] = 0
        load_current_pairing()
    round_var.trace("w", on_round_selected)
    def prev_pairing():
        if pairing_index["current"] > 0:
            pairing_index["current"] -= 1
            load_current_pairing()
    def next_pairing():
        sel = int(round_var.get().split()[1])
        current = completed_rounds.get(sel, [])
        if pairing_index["current"] < len(current) - 1:
            pairing_index["current"] += 1
            load_current_pairing()
    prev_button.configure(command=prev_pairing)
    next_button.configure(command=next_pairing)
    def submit_result():
        if not round_var.get().startswith("Round "):
            return
        sel = int(round_var.get().split()[1])
        current = completed_rounds.get(sel, [])
        idx = pairing_index["current"]
        if idx < 0 or idx >= len(current):
            return
        p1, p2, first = current[idx]
        if p1 == "BYE" or p2 == "BYE":
            show_toast(tab_frame, "BYE pairing. No result needed.")
            next_pairing()
            return
        try:
            s1 = int(score1_entry.get().strip())
            s2 = int(score2_entry.get().strip())
        except ValueError:
            show_toast(tab_frame, "Please enter valid numeric scores.")
            return
        if sel not in results_by_round:
            results_by_round[sel] = [None] * len(current)
        results_by_round[sel][idx] = (s1, s2)
        recalc_player_stats()
        if s1 > s2:
            spread_diff = s1 - s2
            msg = f"Result submitted. {p1} wins by {spread_diff}."
        elif s2 > s1:
            spread_diff = s2 - s1
            msg = f"Result submitted. {p2} wins by {spread_diff}."
        else:
            msg = "Result submitted. It's a tie."
        show_toast(tab_frame, msg)
    submit_button.configure(command=submit_result)
    refresh_rounds()

##################################
# UI Functions: Tournament Setup Tab
##################################
def setup_tournament_setup(tab_frame):
    global current_tournament_id, session_players, current_round_number, completed_rounds, tournament_mode, teams_list, team_size, last_pairing_system, last_team_size, public_ip, shareable_link
    label = ctk.CTkLabel(tab_frame, text="Set Up a New Tournament", font=("Arial", 18))
    label.pack(pady=10)
    tournament_name_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter tournament name")
    tournament_name_entry.pack(pady=5)
    tournament_date_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter tournament date (YYYY-MM-DD)")
    tournament_date_entry.pack(pady=5)
    venue_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter tournament venue")
    venue_entry.pack(pady=5)
    connection_type_var = ctk.StringVar(value="Render URL")
    connection_type_menu = ctk.CTkOptionMenu(tab_frame, variable=connection_type_var, values=["Local IP", "Render URL", "FTP"])
    connection_type_menu.pack(pady=5)
    sponsor_logos  # sponsor_logos remains a global variable
    def create_tournament():
        global current_tournament_id, session_players, current_round_number, completed_rounds, tournament_mode, teams_list, team_size, last_pairing_system, last_team_size, public_ip, shareable_link
        name = tournament_name_entry.get().strip()
        date = tournament_date_entry.get().strip()
        venue = venue_entry.get().strip()
        if not name or not date or not venue:
            show_toast(tab_frame, "Please enter valid tournament details, including venue.")
            return
        tournament_mode = "General"
        teams_list = []
        team_size = 0
        last_pairing_system = "Round Robin"
        desired_rr_rounds = None
        conn = create_connection()
        tournament_id = insert_tournament(conn, name, date, venue)
        conn.close()
        if tournament_id:
            current_tournament_id = tournament_id
            session_players = []
            current_round_number = 0
            completed_rounds.clear()
            results_by_round.clear()
            generated_file = generate_tournament_html(tournament_id, name, date)
            final_file = finalize_tournament_html(name, generated_file)
            rendered_dir = os.path.join(os.getcwd(), "rendered")
            relative_path = os.path.relpath(final_file, rendered_dir).replace(os.sep, '/')
            if connection_type_var.get() == "Local IP":
                public_ip = get_local_ip()
                shareable_link = f"http://{public_ip}:{HTTP_PORT}/{relative_path}"
            elif connection_type_var.get() == "Render URL":
                render_domain = simpledialog.askstring("Render Domain", "Enter your Render domain (e.g., myapp.onrender.com):")
                if render_domain:
                    public_ip = f"https://{render_domain}"
                    # Make sure the URL doesn't have double slashes
                    shareable_link = f"{public_ip}/tournament/{folder_name}"
                    messagebox.showinfo("Render URL", f"Using Render URL: {shareable_link}\n\nMake sure your Render service is configured to serve static files and the files are uploaded to the correct location.")
                else:
                    # Fallback to local IP if no domain provided
                    public_ip = get_local_ip()
                    shareable_link = f"http://{public_ip}:{HTTP_PORT}/{relative_path}"
            elif connection_type_var.get() == "FTP":
                ftp_host = simpledialog.askstring("FTP Host", "Enter FTP host:")
                ftp_user = simpledialog.askstring("FTP Username", "Enter FTP username:")
                ftp_pass = simpledialog.askstring("FTP Password", "Enter FTP password:", show="*")
                if ftp_host and ftp_user and ftp_pass:
                    new_link = mirror_website_via_ftp(ftp_host, ftp_user, ftp_pass)
                    if new_link:
                        shareable_link = new_link
                    else:
                        public_ip = "http://direktorexe.onrender.com"
                        shareable_link = f"{public_ip}/{relative_path}"
                else:
                    public_ip = "http://direktorexe.onrender.com"
                    shareable_link = f"{public_ip}/{relative_path}"
            update_tournament_link(tournament_id, shareable_link)
            show_toast(tab_frame, f"Tournament '{name}' created. Link: {shareable_link}")
            update_status()
        else:
            show_toast(tab_frame, "Failed to create tournament.")
        tournament_name_entry.delete(0, 'end')
        tournament_date_entry.delete(0, 'end')
        venue_entry.delete(0, 'end')
    create_button = ctk.CTkButton(tab_frame, text="Create Tournament", command=create_tournament)
    create_button.pack(pady=10)

##################################
# UI Functions: Player Registration Tab
##################################
def setup_player_registration(tab_frame):
    global current_tournament_id, session_players, tournament_mode, teams_list
    label = ctk.CTkLabel(tab_frame, text="Register a New Player", font=("Arial", 18))
    label.pack(pady=10)
    name_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter player name")
    name_entry.pack(pady=5)
    rating_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter rating (or 000 if unrated)")
    rating_entry.pack(pady=5)
    rating_entry.insert(0, "000")
    country_entry = ctk.CTkEntry(tab_frame, placeholder_text="Enter country name")
    country_entry.pack(pady=5)
    dropdown_team = None  # In general mode, team selection is not used.
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
            if len(player) > 10 and player[10]:
                flag_html = f' <img src="https://flagcdn.com/16x12/{player[10].strip().lower()}.png">'
            else:
                flag_html = ""
            team = player[8] if len(player) > 8 and player[8] else ""
            display_name = f"{player[1]}{flag_html}" if not team else f"{player[1]} ({team}){flag_html}"
            player_list_text.insert("end", f"{display_name} (Rating: {player[2]})\n")
        player_list_text.configure(state="disabled")
    def register_player():
        global current_tournament_id, session_players
        if current_tournament_id is None:
            show_toast(tab_frame, "Please create a tournament first!")
            return
        name = name_entry.get().strip()
        rating_str = rating_entry.get().strip()
        country = country_entry.get().strip()
        try:
            rating = int(rating_str) if rating_str and rating_str.isdigit() else 0
        except ValueError:
            rating = 0
        if not name:
            show_toast(tab_frame, "Please enter a valid name!")
            return
        team = ""
        conn = create_connection()
        # Updated insert_player to accept country (as full country name)
        tournament_specific_id = insert_player(conn, name, rating, current_tournament_id, team, country)
        conn.close()
        show_toast(tab_frame, f"Player '{name}' registered with tournament ID {tournament_specific_id}.")
        name_entry.delete(0, 'end')
        rating_entry.delete(0, 'end')
        rating_entry.insert(0, "000")
        country_entry.delete(0, 'end')
        update_player_list()
    register_button = ctk.CTkButton(tab_frame, text="Register Player", command=register_player)
    register_button.pack(pady=10)

##################################
# UI Functions: Pairings Tab
##################################
def setup_pairings(tab_frame):
    global current_round_number, completed_rounds, last_pairing_system
    for widget in tab_frame.winfo_children():
        widget.destroy()
    label = ctk.CTkLabel(tab_frame, text="Pairings", font=("Arial", 18))
    label.pack(pady=10)
    round_options = ["New Round"] + [f"Round {i}" for i in sorted(completed_rounds.keys())]
    round_selection_var = ctk.StringVar(value="New Round")
    round_dropdown = ctk.CTkOptionMenu(tab_frame, variable=round_selection_var, values=round_options)
    round_dropdown.pack(pady=5)
    pairing_systems = ["Round Robin", "Random Pairing", "King of the Hills Pairing", "Australian Draw", "Lagged Australian"]
    system_var = ctk.StringVar(value=last_pairing_system)
    system_menu = ctk.CTkOptionMenu(tab_frame, variable=system_var, values=pairing_systems)
    system_menu.pack(pady=5)
    button_frame = ctk.CTkFrame(tab_frame)
    button_frame.pack(pady=5)
    pair_button = ctk.CTkButton(button_frame, text="Pair Round", command=lambda: pair_round(round_selection_var, system_var))
    pair_button.grid(row=0, column=0, padx=5)
    unpair_button = ctk.CTkButton(button_frame, text="Unpair Round", command=lambda: unpair_round(round_selection_var))
    unpair_button.grid(row=0, column=1, padx=5)
    pairing_text = ctk.CTkTextbox(tab_frame, width=400, height=250)
    pairing_text.pack(pady=10)
    def update_round_options():
        opts = ["New Round"] + [f"Round {i}" for i in sorted(completed_rounds.keys())]
        round_dropdown.configure(values=opts)
        if round_selection_var.get() not in opts:
            round_selection_var.set("New Round")
    def display_full_schedule():
        pairing_text.delete("1.0", "end")
        for r in sorted(completed_rounds.keys()):
            pairing_text.insert("end", f"Round {r}:\n")
            for idx, pairing in enumerate(completed_rounds[r], start=1):
                if len(pairing) == 3:
                    p1, p2, first = pairing
                elif len(pairing) == 2:
                    p1, p2 = pairing
                    first = random.choice([p1, p2])
                else:
                    p1, p2, first = "???", "???", "???"
                pairing_text.insert("end", f"  {idx}. {p1} vs {p2} (First: {first})\n")
            pairing_text.insert("end", "\n")
    def pair_round(round_var, system_var):
        global current_round_number, completed_rounds, last_pairing_system
        if current_tournament_id is None:
            messagebox.showerror("Error", "No tournament loaded.")
            return
        if round_var.get() != "New Round":
            messagebox.showerror("Error", "Selected round already exists.")
            return
        last_pairing_system = system_var.get()
        players = get_players_for_tournament(current_tournament_id)
        new_pairings = generate_pairings_system(players, system=last_pairing_system)
        current_round_number += 1
        completed_rounds[current_round_number] = new_pairings
        update_round_options()
        display_full_schedule()
    def unpair_round(round_var):
        if round_var.get() == "New Round":
            messagebox.showerror("Error", "No round selected for unpairing.")
            return
        round_num = int(round_var.get().split()[1])
        if round_num in completed_rounds:
            del completed_rounds[round_num]
            update_round_options()
            pairing_text.delete("1.0", "end")
    update_round_options()

##################################
# UI Functions: FTP Settings Tab
##################################
def setup_ftp_settings(tab_frame):
    label = ctk.CTkLabel(tab_frame, text="FTP Settings", font=("Arial", 18))
    label.pack(pady=10)
    host_label = ctk.CTkLabel(tab_frame, text="FTP Host:")
    host_label.pack(pady=5)
    host_entry = ctk.CTkEntry(tab_frame)
    host_entry.pack(pady=5)
    user_label = ctk.CTkLabel(tab_frame, text="FTP Username:")
    user_label.pack(pady=5)
    user_entry = ctk.CTkEntry(tab_frame)
    user_entry.pack(pady=5)
    pass_label = ctk.CTkLabel(tab_frame, text="FTP Password:")
    pass_label.pack(pady=5)
    pass_entry = ctk.CTkEntry(tab_frame, show="*")
    pass_entry.pack(pady=5)
    def mirror_action():
        ftp_host = host_entry.get().strip()
        ftp_user = user_entry.get().strip()
        ftp_pass = pass_entry.get().strip()
        if not ftp_host or not ftp_user or not ftp_pass:
            messagebox.showerror("Error", "Please fill in all FTP fields.")
            return
        new_link = mirror_website_via_ftp(ftp_host, ftp_user, ftp_pass)
        if new_link:
            messagebox.showinfo("Success", f"Website mirrored successfully!\nShareable link: {new_link}")
    mirror_button = ctk.CTkButton(tab_frame, text="Mirror Website", command=mirror_action)
    mirror_button.pack(pady=10)

##################################
# Build Tab View and Rebuild Functions
##################################
def setup_tab_content(tab_name, tab_frame):
    if tab_name == "Tournament Setup":
        setup_tournament_setup(tab_frame)
    elif tab_name == "Player Registration":
        setup_player_registration(tab_frame)
    elif tab_name == "Pairings":
        setup_pairings(tab_frame)
    elif tab_name == "Enter Results":
        setup_enter_results(tab_frame)
    elif tab_name == "Prize Table":
        setup_prize_table(tab_frame)
    elif tab_name == "Sponsor Logos":
        setup_sponsor_logos(tab_frame)
    elif tab_name == "FTP Settings":
        setup_ftp_settings(tab_frame)
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

def build_tab_view(parent):
    tabs = ["Tournament Setup", "Player Registration", "Pairings", "Enter Results", "Prize Table", "Sponsor Logos", "FTP Settings", "Reports & Exports", "Render"]
    tab_view = ctk.CTkTabview(parent, width=880, height=700)
    tab_view.pack(fill="both", expand=True)
    for tab in tabs:
        tab_view.add(tab)
        setup_tab_content(tab, tab_view.tab(tab))
    return tab_view

def rebuild_tab_view():
    global main_frame_global
    for widget in main_frame_global.winfo_children():
        widget.destroy()
    return build_tab_view(main_frame_global)

##################################
# Main Application Entry Point with Sidebar
##################################
def setup_sidebar(root):
    sidebar = ctk.CTkFrame(root, width=200, corner_radius=0)
    sidebar.grid(row=0, column=0, sticky="nswe")
    save_button = ctk.CTkButton(sidebar, text="Save Tournament", command=save_current_tournament)
    save_button.pack(pady=10, padx=20)
    load_button = ctk.CTkButton(sidebar, text="Load Tournament", command=load_tournament)
    load_button.pack(pady=10, padx=20)
    quit_button = ctk.CTkButton(sidebar, text="Quit App", command=quit_app)
    quit_button.pack(pady=10, padx=20)

if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Direktor EXE – Scrabble Tournament Manager")
    app.geometry("1200x800")
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)
    
    # Apply theme
    set_theme_mode("system")
    apply_theme(app)
    
    sidebar_frame = ctk.CTkFrame(app, width=200, corner_radius=0)
    sidebar_frame.grid(row=0, column=0, sticky="nswe")
    save_button = ctk.CTkButton(sidebar_frame, text="Save Tournament", command=save_current_tournament)
    save_button.pack(pady=10, padx=20)
    load_button = ctk.CTkButton(sidebar_frame, text="Load Tournament", command=load_tournament)
    load_button.pack(pady=10, padx=20)
    quit_button = ctk.CTkButton(sidebar_frame, text="Quit App", command=quit_app)
    quit_button.pack(pady=10, padx=20)
    
    # Add status label to sidebar
    status_label = ctk.CTkLabel(sidebar_frame, text="No tournament loaded.")
    status_label.pack(pady=20, padx=20)
    
    main_frame_global = ctk.CTkFrame(app)
    main_frame_global.grid(row=0, column=1, sticky="nsew")
    
    initialize_database()
    
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    build_tab_view(main_frame_global)
    
    app.mainloop()

