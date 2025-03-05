import os
import sqlite3
from flask import Flask, request, send_from_directory, abort

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8000))

# Route to serve your event coverage index.
# Assumes that the current tournament’s index is at rendered/index.html.
@app.route("/")
def index():
    # You could also add logic here to choose which tournament index to serve.
    return send_from_directory("rendered", "index.html")

# Remote results submission endpoint
@app.route("/submit_results", methods=["GET", "POST"])
def submit_results():
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
        # Handle form submission via POST
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
        
        # Attempt to save the result into the database.
        if not save_result(match_id, score1, score2):
            abort(409, "Result for this match has already been submitted or match ID is invalid")
        
        return "Result submitted successfully", 200

def save_result(match_id, score1, score2):
    """
    Save the match result to a SQLite database.
    This example assumes you have a table named 'match_results'
    with columns 'match_id', 'score1', and 'score2'.
    """
    db_file = "tournament.db"  # Adjust this if your database is located elsewhere.
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Check if a result for this match_id already exists.
    cursor.execute("SELECT * FROM match_results WHERE match_id = ?", (match_id,))
    if cursor.fetchone():
        conn.close()
        return False

    # Insert the result
    cursor.execute("INSERT INTO match_results (match_id, score1, score2) VALUES (?, ?, ?)",
                   (match_id, score1, score2))
    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
