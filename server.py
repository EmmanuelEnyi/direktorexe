import http.server
import socketserver
import json
import os
import sqlite3
from urllib.parse import parse_qs

# Configuration
PORT = int(os.environ.get("PORT", 8000))  # Heroku assigns a dynamic port
DB_FILE = "tournament.db"  # SQLite database for tournament data
RENDERED_DIR = os.path.join(os.getcwd(), "rendered")  # Directory for HTML files

# Ensure the directory exists
os.makedirs(RENDERED_DIR, exist_ok=True)

class TournamentRequestHandler(http.server.SimpleHTTPRequestHandler):
    """ Custom HTTP handler to serve event coverage and handle result submissions. """

    def do_GET(self):
        """ Serve static HTML pages or a submission form """
        if self.path == "/submit_results":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.get_submission_form().encode())
        else:
            super().do_GET()

    def do_POST(self):
        """ Handle player result submissions """
        if self.path == "/submit_results":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            fields = parse_qs(post_data.decode())

            match_id = fields.get("match_id", [None])[0]
            score1 = fields.get("score1", [None])[0]
            score2 = fields.get("score2", [None])[0]

            if not match_id or score1 is None or score2 is None:
                self.send_error(400, "Missing required fields")
                return

            try:
                score1, score2 = int(score1), int(score2)
            except ValueError:
                self.send_error(400, "Scores must be numeric")
                return

            # Save results to database
            success = self.save_result(match_id, score1, score2)

            if success:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"Result submitted successfully.")
            else:
                self.send_error(400, "Invalid match ID or match already has a result.")

    def get_submission_form(self):
        """ Returns the HTML form for submitting match results """
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

    def save_result(self, match_id, score1, score2):
        """ Saves match results into the SQLite database """
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Check if the match exists
        cursor.execute("SELECT * FROM match_results WHERE match_id = ?", (match_id,))
        existing_match = cursor.fetchone()

        if existing_match:
            conn.close()
            return False  # Match result already exists

        # Insert the new match result
        cursor.execute("INSERT INTO match_results (match_id, score1, score2) VALUES (?, ?, ?)",
                       (match_id, score1, score2))
        conn.commit()
        conn.close()
        return True

# Start the server
handler = TournamentRequestHandler
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), handler) as httpd:
    print(f"Serving HTTP at port {PORT}")
    httpd.serve_forever()
