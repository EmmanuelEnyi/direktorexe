"""
server.py - Flask web server for Direktor EXE Scrabble Tournament Manager

This module provides a Flask web server for hosting tournament websites and
handling remote result submissions.
"""

import os
import sqlite3
from flask import Flask, send_from_directory, request, abort, redirect, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8000))
DATABASE_FILE = "direktor.db"

# Simple in-memory admin credentials (replace with database in production)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")  # Default password, should be changed

def get_latest_tournament_folder():
    """Get the most recently modified tournament folder."""
    tournaments_dir = os.path.join("rendered", "tournaments")
    if not os.path.exists(tournaments_dir):
        return None
    
    # Get a list of tournament folders
    folders = [d for d in os.listdir(tournaments_dir)
               if os.path.isdir(os.path.join(tournaments_dir, d))]
    if not folders:
        return None
    
    # Sort folders by modification time (latest first)
    folders.sort(key=lambda d: os.path.getmtime(os.path.join(tournaments_dir, d)), reverse=True)
    return folders[0]

def get_all_tournament_folders():
    """Get all tournament folders sorted by modification time (latest first)."""
    tournaments_dir = os.path.join("rendered", "tournaments")
    if not os.path.exists(tournaments_dir):
        return []
    
    # Get a list of tournament folders
    folders = [d for d in os.listdir(tournaments_dir)
               if os.path.isdir(os.path.join(tournaments_dir, d))]
    
    # Sort folders by modification time (latest first)
    folders.sort(key=lambda d: os.path.getmtime(os.path.join(tournaments_dir, d)), reverse=True)
    return folders

def create_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

@app.route("/")
def index():
    """Redirect to the latest tournament or show a list of tournaments."""
    latest = get_latest_tournament_folder()
    if latest:
        # Redirect to a URL that includes the tournament folder name
        return redirect(f"/tournament/{latest}")
    else:
        # Show a list of all tournaments if no latest tournament is found
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Direktor EXE - Tournament List</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #3B82F6; }
                ul { list-style-type: none; padding: 0; }
                li { margin: 10px 0; }
                a { color: #3B82F6; text-decoration: none; }
                a:hover { text-decoration: underline; }
                .no-tournaments { color: #6B7280; font-style: italic; }
            </style>
        </head>
        <body>
            <h1>Direktor EXE - Tournament List</h1>
            {% if tournaments %}
                <ul>
                {% for tournament in tournaments %}
                    <li><a href="/tournament/{{ tournament }}">{{ tournament.replace('_', ' ') }}</a></li>
                {% endfor %}
                </ul>
            {% else %}
                <p class="no-tournaments">No tournaments found.</p>
            {% endif %}
        </body>
        </html>
        """, tournaments=get_all_tournament_folders())

@app.route("/tournament/<tournament_name>")
def tournament_index(tournament_name):
    """Serve the tournament index page."""
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, "index.html")):
        return send_from_directory(folder, "index.html")
    else:
        abort(404, f"Tournament '{tournament_name}' not found.")

@app.route("/tournament/<tournament_name>/<path:filename>")
def tournament_files(tournament_name, filename):
    """Serve tournament files."""
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, filename)):
        return send_from_directory(folder, filename)
    else:
        abort(404, f"File '{filename}' not found in tournament '{tournament_name}'.")

@app.route("/tournaments/<tournament_name>")
def tournaments_index(tournament_name):
    """Alternative route for tournament index."""
    return tournament_index(tournament_name)

@app.route("/tournaments/<tournament_name>/<path:filename>")
def tournaments_files(tournament_name, filename):
    """Alternative route for tournament files."""
    return tournament_files(tournament_name, filename)

@app.route("/submit_results", methods=["GET", "POST"])
def submit_results():
    """Handle result submission form."""
    if request.method == "GET":
        # Get a list of active tournaments for the dropdown
        tournaments = get_all_tournament_folders()
        tournament_names = [t.replace("_", " ") for t in tournaments]
        
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Submit Match Results</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; max-width: 600px; margin: 0 auto; padding: 20px; }
                h2 { color: #3B82F6; }
                input, select, label { font-size: 16px; margin: 5px 0; display: block; width: 100%; padding: 8px; box-sizing: border-box; }
                button { background-color: #3B82F6; color: white; border: none; padding: 10px 15px; font-size: 16px; cursor: pointer; margin-top: 10px; }
                button:hover { background-color: #2563EB; }
                .error { color: #EF4444; margin-top: 10px; }
                .success { color: #10B981; margin-top: 10px; }
            </style>
        </head>
        <body>
            <h2>Submit Match Results</h2>
            <form method="POST" action="/submit_results" id="resultForm">
                <label for="tournament">Tournament:</label>
                <select id="tournament" name="tournament" required>
                    <option value="">Select Tournament</option>
                    {% for tournament in tournaments %}
                    <option value="{{ tournament }}">{{ tournament }}</option>
                    {% endfor %}
                </select>
                
                <label for="match_id">Match ID (e.g., R1-M2):</label>
                <input type="text" id="match_id" name="match_id" required>
                
                <label for="score1">Score for Player 1:</label>
                <input type="number" id="score1" name="score1" required>
                
                <label for="score2">Score for Player 2:</label>
                <input type="number" id="score2" name="score2" required>
                
                <button type="submit">Submit Results</button>
            </form>
            
            <div id="message"></div>
            
            <script>
                document.getElementById('resultForm').addEventListener('submit', function(e) {
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    
                    fetch('/submit_results', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        const messageDiv = document.getElementById('message');
                        if (data.success) {
                            messageDiv.className = 'success';
                            messageDiv.textContent = data.message;
                            document.getElementById('resultForm').reset();
                        } else {
                            messageDiv.className = 'error';
                            messageDiv.textContent = data.message;
                        }
                    })
                    .catch(error => {
                        document.getElementById('message').className = 'error';
                        document.getElementById('message').textContent = 'An error occurred. Please try again.';
                    });
                });
            </script>
        </body>
        </html>
        """, tournaments=tournament_names)
    else:
        # Process POST submission
        tournament = request.form.get("tournament")
        match_id = request.form.get("match_id")
        score1 = request.form.get("score1")
        score2 = request.form.get("score2")
        
        if not tournament or not match_id or score1 is None or score2 is None:
            return jsonify({"success": False, "message": "Missing required fields"})
        
        try:
            score1 = int(score1)
            score2 = int(score2)
        except ValueError:
            return jsonify({"success": False, "message": "Scores must be integers"})
        
        # Connect to database
        conn = create_connection()
        cursor = conn.cursor()
        
        # Check if result already exists
        cursor.execute("SELECT * FROM results WHERE match_id = ?", (match_id,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "Result for this match has already been submitted"})
        
        # Insert the result
        try:
            cursor.execute(
                "INSERT INTO results (match_id, player1_score, player2_score, tournament, submission_time) VALUES (?, ?, ?, ?, ?)",
                (match_id, score1, score2, tournament, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
            return jsonify({"success": True, "message": "Result submitted successfully"})
        except Exception as e:
            conn.close()
            return jsonify({"success": False, "message": f"Database error: {str(e)}"})

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    """Admin login page."""
    if request.method == "GET":
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Direktor EXE - Admin Login</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; max-width: 400px; margin: 0 auto; padding: 20px; }
                h2 { color: #3B82F6; }
                input, label { font-size: 16px; margin: 5px 0; display: block; width: 100%; padding: 8px; box-sizing: border-box; }
                button { background-color: #3B82F6; color: white; border: none; padding: 10px 15px; font-size: 16px; cursor: pointer; margin-top: 10px; }
                button:hover { background-color: #2563EB; }
                .error { color: #EF4444; margin-top: 10px; }
            </style>
        </head>
        <body>
            <h2>Admin Login</h2>
            <form method="POST" action="/admin">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required>
                
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" required>
                
                <button type="submit">Login</button>
            </form>
            
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
        </body>
        </html>
        """, error=request.args.get("error"))
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            # In a real app, you would set a session cookie here
            return redirect("/admin/dashboard")
        else:
            return redirect("/admin?error=Invalid+username+or+password")

@app.route("/admin/dashboard")
def admin_dashboard():
    """Admin dashboard."""
    # In a real app, you would check for a valid session here
    
    # Get recent submissions
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT match_id, player1_score, player2_score, tournament, submission_time FROM results ORDER BY submission_time DESC LIMIT 20"
    )
    submissions = cursor.fetchall()
    conn.close()
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Direktor EXE - Admin Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h2 { color: #3B82F6; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f2f2f2; }
            .no-data { color: #6B7280; font-style: italic; }
        </style>
    </head>
    <body>
        <h2>Admin Dashboard</h2>
        
        <h3>Recent Submissions</h3>
        {% if submissions %}
        <table>
            <thead>
                <tr>
                    <th>Match ID</th>
                    <th>Tournament</th>
                    <th>Player 1 Score</th>
                    <th>Player 2 Score</th>
                    <th>Submission Time</th>
                </tr>
            </thead>
            <tbody>
                {% for submission in submissions %}
                <tr>
                    <td>{{ submission.match_id }}</td>
                    <td>{{ submission.tournament }}</td>
                    <td>{{ submission.player1_score }}</td>
                    <td>{{ submission.player2_score }}</td>
                    <td>{{ submission.submission_time }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p class="no-data">No submissions found.</p>
        {% endif %}
    </body>
    </html>
    """, submissions=submissions)

@app.route("/api/results", methods=["GET"])
def api_results():
    """API endpoint to get results."""
    tournament = request.args.get("tournament")
    
    conn = create_connection()
    cursor = conn.cursor()
    
    if tournament:
        cursor.execute(
            "SELECT match_id, player1_score, player2_score, submission_time FROM results WHERE tournament = ? ORDER BY submission_time DESC",
            (tournament,)
        )
    else:
        cursor.execute(
            "SELECT match_id, player1_score, player2_score, tournament, submission_time FROM results ORDER BY submission_time DESC"
        )
    
    results = cursor.fetchall()
    conn.close()
    
    # Convert to list of dictionaries for JSON response
    results_list = []
    for result in results:
        result_dict = dict(result)
        results_list.append(result_dict)
    
    return jsonify({"results": results_list})

def run_flask_app():
    """Run the Flask application."""
    app.run(host="0.0.0.0", port=PORT, debug=False)

if __name__ == "__main__":
    print("Starting Flask server directly...")
    # Try to initialize the database if possible
    try:
        from schema import initialize_database
        print("Initializing database...")
        initialize_database()
    except ImportError:
        print("Could not import initialize_database, skipping database initialization")
    
    # Run the Flask app directly
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)

