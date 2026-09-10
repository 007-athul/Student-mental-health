from flask import Flask, render_template, request, jsonify
import os
import sqlite3
import secrets
import time
from pathlib import Path

app = Flask(__name__)
DB = Path(__file__).with_name("tetris.db")

# In-memory game sessions. For a multi-server production app, use Redis/database.
sessions = {}

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL,
            score INTEGER NOT NULL,
            lines INTEGER NOT NULL,
            level INTEGER NOT NULL,
            duration REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def valid_name(name):
    return isinstance(name, str) and 1 <= len(name.strip()) <= 20

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/game/start")
def start_game():
    data = request.get_json(silent=True) or {}
    player = data.get("player", "").strip()

    if not valid_name(player):
        return jsonify({"error": "Player name must contain 1-20 characters."}), 400

    game_id = secrets.token_urlsafe(18)
    sessions[game_id] = {
        "player": player,
        "started": time.time(),
        "last_update": time.time(),
        "max_score": 0,
        "max_lines": 0,
        "max_level": 1,
        "updates": 0
    }

    return jsonify({
        "game_id": game_id,
        "message": "Game session started"
    })

@app.post("/api/game/update")
def update_game():
    data = request.get_json(silent=True) or {}
    game_id = data.get("game_id")
    session = sessions.get(game_id)

    if not session:
        return jsonify({"error": "Invalid or expired game session."}), 400

    try:
        score = int(data.get("score", 0))
        lines = int(data.get("lines", 0))
        level = int(data.get("level", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid game statistics."}), 400

    if score < 0 or lines < 0 or level < 1:
        return jsonify({"error": "Invalid game statistics."}), 400

    # Tetris score/line values must never decrease during a session.
    if score < session["max_score"] or lines < session["max_lines"] or level < session["max_level"]:
        return jsonify({"error": "Game statistics moved backwards."}), 400

    # Basic server-side plausibility limits.
    elapsed = max(time.time() - session["started"], 1)
    # Deliberately generous: prevents absurd fabricated scores while allowing fast play.
    if score > elapsed * 2500:
        return jsonify({"error": "Score is not plausible for this session."}), 400

    session["max_score"] = score
    session["max_lines"] = lines
    session["max_level"] = level
    session["last_update"] = time.time()
    session["updates"] += 1

    return jsonify({"ok": True})

@app.post("/api/game/end")
def end_game():
    data = request.get_json(silent=True) or {}
    game_id = data.get("game_id")
    session = sessions.get(game_id)

    if not session:
        return jsonify({"error": "Invalid or expired game session."}), 400

    try:
        score = int(data.get("score", 0))
        lines = int(data.get("lines", 0))
        level = int(data.get("level", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid game statistics."}), 400

    duration = time.time() - session["started"]

    # Never trust the final browser values beyond the highest values
    # already observed by the server.
    score = min(score, session["max_score"])
    lines = min(lines, session["max_lines"])
    level = min(level, session["max_level"])

    # Standard Tetris line progression is 10 lines per level.
    expected_level = max(1, lines // 10 + 1)
    if level > expected_level + 1:
        return jsonify({"error": "Invalid level progression."}), 400

    # Require a minimally realistic session for non-zero scores.
    if score > 0 and duration < 1.5:
        return jsonify({"error": "Game ended too quickly."}), 400

    conn = db()
    conn.execute(
        "INSERT INTO scores(player, score, lines, level, duration) VALUES (?, ?, ?, ?, ?)",
        (session["player"], score, lines, level, duration)
    )
    conn.commit()
    conn.close()

    del sessions[game_id]

    return jsonify({
        "ok": True,
        "score": score,
        "lines": lines,
        "level": level,
        "duration": round(duration, 2)
    })

@app.get("/api/leaderboard")
def leaderboard():
    conn = db()
    rows = conn.execute("""
        SELECT player, score, lines, level, duration, created_at
        FROM scores
        ORDER BY score DESC, lines DESC, duration ASC
        LIMIT 10
    """).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])

@app.post("/api/game/abandon")
def abandon():
    data = request.get_json(silent=True) or {}
    game_id = data.get("game_id")
    if game_id:
        sessions.pop(game_id, None)
    return jsonify({"ok": True})

init_db()

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=int(os.getenv("PORT", "5001")))
