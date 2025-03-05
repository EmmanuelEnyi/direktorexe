import os
from flask import Flask, send_from_directory, abort

app = Flask(__name__)
PORT = int(os.environ.get("PORT", 8000))

def get_latest_tournament_folder():
    tournaments_dir = os.path.join("rendered", "tournaments")
    if not os.path.exists(tournaments_dir):
        return None
    # Get a list of all tournament folders
    folders = [d for d in os.listdir(tournaments_dir) if os.path.isdir(os.path.join(tournaments_dir, d))]
    if not folders:
        return None
    # Sort folders by modification time (latest first)
    folders.sort(key=lambda d: os.path.getmtime(os.path.join(tournaments_dir, d)), reverse=True)
    return folders[0]

@app.route("/")
def index():
    latest = get_latest_tournament_folder()
    if latest:
        # Serve the index.html from the latest tournament folder
        return send_from_directory(os.path.join("rendered", "tournaments", latest), "index.html")
    else:
        abort(404, "No tournament coverage found.")

@app.route("/tournament/<tournament_name>")
def tournament_index(tournament_name):
    folder = os.path.join("rendered", "tournaments", tournament_name)
    if os.path.exists(os.path.join(folder, "index.html")):
        return send_from_directory(folder, "index.html")
    else:
        abort(404, f"Tournament '{tournament_name}' not found.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
