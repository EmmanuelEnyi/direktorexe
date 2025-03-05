import os
from flask import Flask, send_from_directory, abort, redirect

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8000))

def get_latest_tournament_folder():
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

@app.route("/")
def index():
    latest = get_latest_tournament_folder()
    if latest:
        # Redirect to a URL that includes the tournament folder name
        return redirect(f"/tournament/{latest}")
    else:
        abort(404, "No tournament coverage found.")

@app.route("/tournament/<tournament_name>")
def tournament_index(tournament_name):
    folder = os.path.join("rendered", "tournaments", tournament_name)
    index_path = os.path.join(folder, "index.html")
    if os.path.exists(index_path):
        return send_from_directory(folder, "index.html")
    else:
        abort(404, f"Tournament '{tournament_name}' not found.")

# This route will serve any static file from the tournament folder,
# so that relative links in index.html will work.
@app.route("/tournament/<tournament_name>/<path:filename>")
def tournament_files(tournament_name, filename):
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, filename)):
        return send_from_directory(folder, filename)
    else:
        abort(404, f"File '{filename}' not found in tournament '{tournament_name}'.")

@app.route("/submit_results", methods=["GET", "POST"])
def submit_results():
    if app.request.method == "GET":
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
        # Process POST submission here (you can implement your logic)
        return "Result submitted successfully", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
