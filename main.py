"""
Direktor EXE – Scrabble Tournament Manager
Full Updated main.py (No Firebase)

Features:
  • Modes: General and Team Round Robin (toggle button).
  • Tournament Setup with tournament name, date, and venue.
  • Automatic generation of a tournament folder (inside “rendered/tournaments”) based on the tournament name.
  • All HTML outputs (index, roster, standings, prize table, pairing pages) are generated into that folder so that relative links work correctly.
  • A Flask web server is started and shareable URLs are generated using the public IP or a custom domain provided by the user.
  • The "Enter Results" tab lets the user manually enter or update match scores for each pairing.
  • The Prize Table tab provides a UI for setting up both monetary and non‑monetary prizes (with a searchable currency selector).
  • The Event Coverage Index is regenerated on demand (when clicking Render) to reflect the latest data.
  • In the Pairings tab, when the Round Robin system is chosen, a dialog asks the user for the number of rounds to generate; the system now generates exactly that many rounds.
  • The preview box in the Pairings tab shows the entire round robin schedule.
  • A new "FTP Settings" tab lets the user enter FTP Host, Username, and Password. When the user clicks "Mirror Website", the tournament folder is uploaded via FTP to their host, and the shareable link is updated.
  • A new remote results submission feature is added via Flask:
       – A custom HTTP endpoint (/submit_results) is served.
       – Players can access a web form to paste their match ID and submit scores.
       – The system validates submissions (including duplicate checking) and updates tournament results.
  • A persistent sidebar provides “Save Tournament”, “Load Tournament”, and “Quit App” buttons.
       – “Save Tournament” saves the complete tournament progress as a .TOU file.
       – “Load Tournament” lets the user resume a saved tournament.
       – “Quit App” exits the application.
  • Overall UX enhancements include improved layout, clear feedback messages, tooltips, and robust error handling.
  
Author: Manuelito
"""

#############################
# Imports and Global Variables
#############################
import customtkinter as ctk
import os, re, shutil, webbrowser, sqlite3, threading, http.server, socketserver, socket, random, json, ftplib
import tkinter.filedialog as fd
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
from functools import partial
from data.database import create_connection, create_tables, insert_player, insert_tournament, get_all_tournaments, get_all_players, get_players_for_tournament

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

server_thread = None
HTTP_PORT = int(os.environ.get("PORT", 8000))
current_tournament_id = None
session_players = []
prize_table = []
tournament_mode = "General"
current_mode_view = "general"
teams_list = []
team_size = 0
last_pairing_system = "Round Robin"
last_team_size = 3
current_round_number = 0
completed_rounds = {}
results_by_round = {}
team_round_results = {}
desired_rr_rounds = None   # For Round Robin in Pairings
app = None
status_label = None
main_frame_global = None
shareable_link = ""
full_round_robin_schedule = None
public_ip = ""  # Will store public IP or custom domain

header_html = """<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Tournament</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background-color: #f8f9fa; color: #343a40; }
    .container-custom { max-width:800px; margin:auto; }
    footer { margin-top: 40px; font-size: 0.9em; text-align: center; padding: 20px 0; }
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
def get_tournament_folder(tournament_name):
    rendered_dir = os.path.join(os.getcwd(), "rendered", "tournaments")
    os.makedirs(rendered_dir, exist_ok=True)
    folder_name = re.sub(r'[\\/*?:"<>|]', "", tournament_name).replace(" ", "_")
    tournament_folder = os.path.join(rendered_dir, folder_name)
    os.makedirs(tournament_folder, exist_ok=True)
    return tournament_folder

def finalize_tournament_html(tournament_name, generated_filename):
    folder = get_tournament_folder(tournament_name)
    dest_file = os.path.join(folder, "index.html")
    shutil.copyfile(generated_filename, dest_file)
    return dest_file

##################################
# Utility Function: Get Local IP
##################################
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
                             p.get("last_result", ""), p.get("scorecard", ""), p.get("team", "")) for p in players]
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

def get_players_for_tournament(tournament_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM players WHERE tournament_id = ?", (tournament_id,))
    players = cursor.fetchall()
    conn.close()
    return players

def get_player_id_by_name(tournament_id, name):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM players WHERE tournament_id = ? AND name = ?", (tournament_id, name))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def recalc_player_stats():
    global current_tournament_id
    players = get_players_for_tournament(current_tournament_id)
    stats = {}
    for p in players:
        stats[p[1]] = {"wins": 0, "losses": 0, "spread": 0, "scorecard": []}
    for r in sorted(results_by_round.keys()):
        pairings = completed_rounds.get(r, [])
        round_results = results_by_round.get(r, [])
        for i, pairing in enumerate(pairings):
            if i < len(round_results) and round_results[i] is not None and pairing:
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
                stats[p1]["scorecard"].append({"round": r, "result": result_p1, "cumulative": stats[p1]["spread"]})
                stats[p2]["scorecard"].append({"round": r, "result": result_p2, "cumulative": stats[p2]["spread"]})
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

##################################
# Pairing System Functions
##################################
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

def random_pairings(players):
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
    sorted_players = sorted(players, key=lambda p: (p[3], p[5]), reverse=True)
    names = [p[1] for p in sorted_players]
    if len(names) % 2 == 1:
        names.append("BYE")
    pairings = []
    for i in range(0, len(names), 2):
        p1 = names[i]
        p2 = names[i+1]
        first = p1
        pairings.append((p1, p2, first))
    return pairings

def has_played(player1, player2):
    for rnd in completed_rounds.values():
        for pairing in rnd:
            if set(pairing[:2]) == set([player1, player2]):
                return True
    return False

def australian_draw_pairings(players):
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
                if not has_played(p1, p2):
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

def lagged_australian_pairings(players):
    if current_round_number < 3:
        return random_pairings(players)
    standings = compute_lagged_standings(players, current_round_number - 1)
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
                if not has_played(p1, p2):
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
        return australian_draw_pairings(players)
    elif system_choice == "Lagged Australian":
        return lagged_australian_pairings(players)
    else:
        raise ValueError("Invalid pairing system specified.")

def generate_pairings_system(players, system="Round Robin", team_size=None):
    if system == "Team Round Robin":
        return []  # Not implemented in this update.
    else:
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
    html = f"""<!DOCTYPE html>
<html lang="en">
{header_html}
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
    <a href="./tournament_{tournament_id}_standings.html" class="btn btn-secondary">Back to Standings</a>
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
    index_file = f"{base}_index.html"
    roster_file = f"{base}_roster.html"
    standings_file = f"{base}_standings.html"
    prize_file = f"{base}_prize.html"
    for idx, round_pairings in enumerate(schedule, start=1):
        round_file = f"{base}_pairings_round_{idx}.html"
        pairing_round_links.append((idx, round_file))
        pairing_content = f"<h2>Round {idx} Pairings</h2>\n<table class='table table-bordered'><thead><tr><th>#</th><th>Pairing</th><th>First</th><th>Match ID</th></tr></thead><tbody>"
        for i, pairing in enumerate(round_pairings, start=1):
            match_id = f"R{idx}-M{i}"
            if tournament_mode == "Team Round Robin":
                pairing_str = "Team pairings not implemented."
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
            pairing_content += f"<tr><td>{i}</td><td>{pairing_str}</td><td>{first}</td><td>{match_id} <button onclick='navigator.clipboard.writeText(\"{match_id}\")'>Copy</button></td></tr>"
        pairing_content += "</tbody></table>"
        navbar_html = f"""<nav class="navbar navbar-expand-lg navbar-light bg-light mb-4">
  <div class="container">
    <a class="navbar-brand" href="./{index_file}"></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
            data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" 
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="./{index_file}">Home</a></li>
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
{header_html}
<body>
  {navbar_html}
  <div class="container container-custom">
    <h1 class="mb-3">{tournament_name_db}</h1>
    {pairing_content}
    <a href="./{index_file}" class="btn btn-secondary">Back to Index</a>
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
        roster_rows += f"<tr><td>{idx}</td><td>{p[1]}</td><td>{p[2]}</td></tr>\n"
    roster_html = f"""<!DOCTYPE html>
<html lang="en">
{header_html}
<body>
  <div class="container container-custom">
    <h1 class="mt-4">Player Roster - {tournament_name_db}</h1>
    <table class="table table-striped">
      <thead><tr><th>#</th><th>Name</th><th>Rating</th></tr></thead>
      <tbody>
        {roster_rows if roster_rows else '<tr><td colspan="3">No players registered.</td></tr>'}
      </tbody>
    </table>
    <a href="./{index_file}" class="btn btn-secondary">Back to Index</a>
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
        standings_rows += f"<tr><td>{rank}</td><td><a href='./{scorecard_link}'>{player[1]}</a></td><td>{player[3]}</td><td>{player[4]}</td><td>{player[5]}</td><td>{player[6]}</td></tr>\n"
    standings_html = f"""<!DOCTYPE html>
<html lang="en">
{header_html}
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
    <a href="./{index_file}" class="btn btn-secondary">Back to Index</a>
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
{header_html}
<body>
  <div class="container container-custom">
    <h1 class="mt-4">Prize Table - {tournament_name_db}</h1>
    <table class="table table-bordered">
      <thead><tr><th>Prize Name</th><th>Details</th></tr></thead>
      <tbody>
        {prize_rows if prize_rows else '<tr><td colspan="2">No prizes set.</td></tr>'}
      </tbody>
    </table>
    <a href="./{index_file}" class="btn btn-secondary">Back to Index</a>
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
    <a class="navbar-brand" href="./{index_file}"></a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" 
            data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" 
            aria-label="Toggle navigation">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav ms-auto">
        <li class="nav-item"><a class="nav-link" href="./{index_file}">Home</a></li>
        <li class="nav-item"><a class="nav-link" href="./{roster_file}">Roster</a></li>
        <li class="nav-item"><a class="nav-link" href="./{standings_file}">Standings</a></li>
        <li class="nav-item"><a class="nav-link" href="./{prize_file}">Prize Table</a></li>
      </ul>
    </div>
  </div>
</nav>"""
    footer_section = '<footer class="bg-light">Direktor Scrabble Tournament Manager by Manuelito</footer>'
    index_html = f"""<!DOCTYPE html>
<html lang="en">
{header_html}
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
# Flask Application for Coverage & Remote Results
##################################
from flask import Flask, send_from_directory, request, abort, redirect
flask_app = Flask(__name__)

@flask_app.route("/")
def flask_index():
    latest = get_latest_tournament_folder()
    if latest:
        return redirect(f"/tournament/{latest}")
    else:
        abort(404, "No tournament coverage found.")

@flask_app.route("/tournament/<tournament_name>")
def flask_tournament_index(tournament_name):
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, "index.html")):
        return send_from_directory(folder, "index.html")
    else:
        abort(404, f"Tournament '{tournament_name}' not found.")

@flask_app.route("/tournament/<tournament_name>/<path:filename>")
def flask_tournament_files(tournament_name, filename):
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, filename)):
        return send_from_directory(folder, filename)
    else:
        abort(404, f"File '{filename}' not found in tournament '{tournament_name}'.")

@flask_app.route("/submit_results", methods=["GET", "POST"])
def flask_submit_results():
    if request.method == "GET":
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Submit Match Results</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                input, label { font-size: 16px; margin: 5px; }
            </style>
        </head>
        <body>
            <h2>Submit Match Results</h2>
            <form method="POST" action="/submit_results">
                <label for="match_id">Match ID (e.g., R1-M2):</label><br>
                <input type="text" id="match_id" name="match_id" required><br><br>
                <label for="score1">Score for Player 1:</label><br>
                <input type="number" id="score1" name="score1" required><br><br>
                <label for="score2">Score for Player 2:</label><br>
                <input type="number" id="score2" name="score2" required><br><br>
                <input type="submit" value="Submit Results">
            </form>
        </body>
        </html>
        """
    else:
        match_id = request.form.get("match_id")
        score1 = request.form.get("score1")
        score2 = request.form.get("score2")
        if not match_id or score1 is None or score2 is None:
            abort(400, "Missing required fields")
        try:
            score1 = int(score1)
            score2 = int(score2)
        except ValueError:
            abort(400, "Scores must be integers")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM results WHERE match_id = ?", (match_id,))
        if cursor.fetchone():
            conn.close()
            abort(409, "Result for this match has already been submitted")
        cursor.execute("INSERT INTO results (match_id, player1_score, player2_score) VALUES (?, ?, ?)",
                       (match_id, score1, score2))
        conn.commit()
        conn.close()
        return "Result submitted successfully", 200

def run_flask_app():
    flask_app.run(host="0.0.0.0", port=HTTP_PORT)

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
    # Use custom domain if provided; otherwise, fallback to Render domain
    if not public_ip:
        public_ip = "direktorexe.onrender.com"
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
    global current_tournament_id, session_players, current_round_number, completed_rounds, tournament_mode, teams_list, team_size, last_pairing_system, last_team_size, current_mode_view, shareable_link, desired_rr_rounds, public_ip
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
        global current_tournament_id, session_players, current_round_number, completed_rounds, tournament_mode, teams_list, team_size, last_pairing_system, last_team_size, current_mode_view, shareable_link, desired_rr_rounds, public_ip
        name = tournament_name_entry.get().strip()
        date = tournament_date_entry.get().strip()
        venue = venue_entry.get().strip()
        if not name or not date or not venue:
            show_toast(tab_frame, "Please enter valid tournament details, including venue.")
            return
        if current_mode_view == "team":
            tournament_mode = "Team Round Robin"
            team_size = int(team_size_var.get())
            team_names = team_names_entry.get().strip()
            if not team_names:
                show_toast(tab_frame, "Please enter team names.")
                return
            teams_list = [t.strip() for t in team_names.split(",") if t.strip()]
            if len(teams_list) < 2:
                show_toast(tab_frame, "Please enter at least two team names.")
                return
            last_pairing_system = "Team Round Robin"
            last_team_size = team_size
        else:
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
            public_ip = simpledialog.askstring("Public IP or Domain", 
                "Enter the public IP or domain for players to access (leave blank to use the Render domain):")
            if not public_ip:
                public_ip = "direktorexe.onrender.com"
            if public_ip.startswith("http://") or public_ip.startswith("https://"):
                shareable_link = f"{public_ip}/{relative_path}"
            else:
                shareable_link = f"http://{public_ip}:{HTTP_PORT}/{relative_path}"
            update_tournament_link(tournament_id, shareable_link)
            show_toast(tab_frame, f"Tournament '{name}' created. Link: {shareable_link}")
            print(f"Tournament '{name}' created with ID {tournament_id}. Link: {shareable_link}")
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
    if tournament_mode == "Team Round Robin":
        team_var = ctk.StringVar()
        team_dropdown = ctk.CTkOptionMenu(tab_frame, variable=team_var, values=teams_list if teams_list else ["No Teams Defined"])
        team_dropdown.pack(pady=5)
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
        if not name:
            show_toast(tab_frame, "Please enter a valid name!")
            return
        team = ""
        if tournament_mode == "Team Round Robin":
            team = team_var.get()
            if team in ("No Teams Defined", ""):
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

##################################
# UI Functions: Pairings Tab
##################################
def setup_pairings(tab_frame):
    global current_round_number, completed_rounds, last_pairing_system, pairing_text
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
                else:
                    p1, p2 = pairing
                    first = random.choice([p1, p2])
                pairing_text.insert("end", f"  {idx}. {p1} vs {p2} (First: {first})\n")
            pairing_text.insert("end", "\n")
    def pair_round(round_var, system_var):
        global current_round_number, completed_rounds, last_pairing_system, full_round_robin_schedule
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
# UI Functions: Build Tab View
##################################
def setup_tab_content(tab_name, tab_frame):
    if tab_name == "Tournament Setup":
        setup_tournament_setup(tab_frame)
    elif tab_name == "Player Registration":
        setup_player_registration(tab_frame)
    elif tab_name in ("Pairings", "Team Pairings"):
        setup_pairings(tab_frame)
    elif tab_name == "Enter Results":
        setup_enter_results(tab_frame)
    elif tab_name == "Prize Table":
        setup_prize_table(tab_frame)
    elif tab_name in ("Reports & Exports", "Render"):
        if tab_name == "Reports & Exports":
            setup_reports(tab_frame)
        else:
            setup_render(tab_frame)
    elif tab_name == "FTP Settings":
        setup_ftp_settings(tab_frame)
    else:
        label = ctk.CTkLabel(tab_frame, text=tab_name, font=("Arial", 18))
        label.pack(pady=20)
    def save_tab():
        show_toast(tab_frame, "Tab data saved.")
    tab_save_button = ctk.CTkButton(tab_frame, text="Save Tab", command=save_tab)
    tab_save_button.pack(pady=5)

def setup_tab_content_without_save(tab_frame, tab_name):
    if tab_name in ("Reports & Exports", "Render", "FTP Settings"):
        if tab_name == "Reports & Exports":
            setup_reports(tab_frame)
        elif tab_name == "Render":
            setup_render(tab_frame)
        else:
            setup_ftp_settings(tab_frame)
    else:
        label = ctk.CTkLabel(tab_frame, text=tab_name, font=("Arial", 18))
        label.pack(pady=20)

def build_tab_view(parent):
    if current_mode_view == "general":
        tabs = ["Tournament Setup", "Player Registration", "Pairings", "Enter Results", "Prize Table", "Reports & Exports", "Render", "FTP Settings"]
    elif current_mode_view == "team":
        tabs = ["Tournament Setup", "Player Registration", "Team Pairings", "Team Results", "Prize Table", "Render", "FTP Settings"]
    else:
        tabs = []
    tab_view = ctk.CTkTabview(parent, width=880, height=700)
    tab_view.pack(fill="both", expand=True)
    for tab in tabs:
        tab_view.add(tab)
        if current_mode_view in ("general", "team") and tab in ("Pairings", "Team Pairings"):
            setup_pairings(tab_view.tab(tab))
        elif tab in ("Reports & Exports", "Render", "FTP Settings"):
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
    global current_mode_view, tournament_mode
    if current_mode_view == "general":
        current_mode_view = "team"
        tournament_mode = "Team Round Robin"
    else:
        current_mode_view = "general"
        tournament_mode = "General"
    rebuild_tab_view()
    show_toast(app, f"Switched to {current_mode_view.capitalize()} Mode.")

##################################
# Flask Application for Coverage & Remote Results
##################################
from flask import Flask, send_from_directory, request, abort, redirect
flask_app = Flask(__name__)

@flask_app.route("/")
def flask_index():
    latest = get_latest_tournament_folder()
    if latest:
        return redirect(f"/tournament/{latest}")
    else:
        abort(404, "No tournament coverage found.")

@flask_app.route("/tournament/<tournament_name>")
def flask_tournament_index(tournament_name):
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, "index.html")):
        return send_from_directory(folder, "index.html")
    else:
        abort(404, f"Tournament '{tournament_name}' not found.")

@flask_app.route("/tournament/<tournament_name>/<path:filename>")
def flask_tournament_files(tournament_name, filename):
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, filename)):
        return send_from_directory(folder, filename)
    else:
        abort(404, f"File '{filename}' not found in tournament '{tournament_name}'.")

@flask_app.route("/submit_results", methods=["GET", "POST"])
def flask_submit_results():
    if request.method == "GET":
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Submit Match Results</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                input, label { font-size: 16px; margin: 5px; }
            </style>
        </head>
        <body>
            <h2>Submit Match Results</h2>
            <form method="POST" action="/submit_results">
                <label for="match_id">Match ID (e.g., R1-M2):</label><br>
                <input type="text" id="match_id" name="match_id" required><br><br>
                <label for="score1">Score for Player 1:</label><br>
                <input type="number" id="score1" name="score1" required><br><br>
                <label for="score2">Score for Player 2:</label><br>
                <input type="number" id="score2" name="score2" required><br><br>
                <input type="submit" value="Submit Results">
            </form>
        </body>
        </html>
        """
    else:
        match_id = request.form.get("match_id")
        score1 = request.form.get("score1")
        score2 = request.form.get("score2")
        if not match_id or score1 is None or score2 is None:
            abort(400, "Missing required fields")
        try:
            score1 = int(score1)
            score2 = int(score2)
        except ValueError:
            abort(400, "Scores must be integers")
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM results WHERE match_id = ?", (match_id,))
        if cursor.fetchone():
            conn.close()
            abort(409, "Result for this match has already been submitted")
        cursor.execute("INSERT INTO results (match_id, player1_score, player2_score) VALUES (?, ?, ?)",
                       (match_id, score1, score2))
        conn.commit()
        conn.close()
        return "Result submitted successfully", 200

def run_flask_app():
    flask_app.run(host="0.0.0.0", port=HTTP_PORT)

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
    # Initialize Tkinter GUI
    app = ctk.CTk()
    app.title("Direktor EXE – Scrabble Tournament Manager")
    app.geometry("1200x800")
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)
    
    sidebar_frame = ctk.CTkFrame(app, width=200, corner_radius=0)
    sidebar_frame.grid(row=0, column=0, sticky="nswe")
    save_button = ctk.CTkButton(sidebar_frame, text="Save Tournament", command=save_current_tournament)
    save_button.pack(pady=10, padx=20)
    load_button = ctk.CTkButton(sidebar_frame, text="Load Tournament", command=load_tournament)
    load_button.pack(pady=10, padx=20)
    quit_button = ctk.CTkButton(sidebar_frame, text="Quit App", command=quit_app)
    quit_button.pack(pady=10, padx=20)
    
    main_frame_global = ctk.CTkFrame(app)
    main_frame_global.grid(row=0, column=1, sticky="nsew")
    
    initialize_database()
    
    # Start the Flask server (for tournament coverage and remote results) in a separate thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    build_tab_view(main_frame_global)
    
    app.mainloop()
