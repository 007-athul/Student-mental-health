from flask import Flask, render_template, request, jsonify
import os
import sqlite3
from pathlib import Path

app = Flask(__name__)

DATABASE = Path(__file__).with_name("tic_tac_toe.db")


# ---------------------------------------
# DATABASE CONNECTION
# ---------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------
# CREATE DATABASE TABLE
# ---------------------------------------
def initialize_database():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_x TEXT NOT NULL,
            player_o TEXT NOT NULL,
            x_wins INTEGER DEFAULT 0,
            o_wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0
        )
    """)

    # Create one default score record
    existing = conn.execute(
        "SELECT * FROM scores WHERE id = 1"
    ).fetchone()

    if existing is None:
        conn.execute("""
            INSERT INTO scores
            (id, player_x, player_o, x_wins, o_wins, draws)
            VALUES (1, 'Player X', 'Player O', 0, 0, 0)
        """)

    conn.commit()
    conn.close()


# ---------------------------------------
# HOME PAGE
# ---------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------
# GET SCORES
# ---------------------------------------
@app.route("/api/scores", methods=["GET"])
def get_scores():

    conn = get_db_connection()

    score = conn.execute(
        "SELECT * FROM scores WHERE id = 1"
    ).fetchone()

    conn.close()

    return jsonify({
        "player_x": score["player_x"],
        "player_o": score["player_o"],
        "x_wins": score["x_wins"],
        "o_wins": score["o_wins"],
        "draws": score["draws"]
    })


# ---------------------------------------
# UPDATE PLAYER NAMES
# ---------------------------------------
@app.route("/api/players", methods=["POST"])
def update_players():

    data = request.get_json()

    player_x = data.get("player_x", "Player X").strip()
    player_o = data.get("player_o", "Player O").strip()

    if not player_x:
        player_x = "Player X"

    if not player_o:
        player_o = "Player O"

    conn = get_db_connection()

    conn.execute("""
        UPDATE scores
        SET player_x = ?, player_o = ?
        WHERE id = 1
    """, (player_x, player_o))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Players updated successfully",
        "player_x": player_x,
        "player_o": player_o
    })


# ---------------------------------------
# ADD WIN
# ---------------------------------------
@app.route("/api/win", methods=["POST"])
def add_win():

    data = request.get_json()
    winner = data.get("winner")

    conn = get_db_connection()

    if winner == "X":
        conn.execute("""
            UPDATE scores
            SET x_wins = x_wins + 1
            WHERE id = 1
        """)

    elif winner == "O":
        conn.execute("""
            UPDATE scores
            SET o_wins = o_wins + 1
            WHERE id = 1
        """)

    else:
        conn.close()
        return jsonify({
            "error": "Invalid winner"
        }), 400

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Score updated"
    })


# ---------------------------------------
# ADD DRAW
# ---------------------------------------
@app.route("/api/draw", methods=["POST"])
def add_draw():

    conn = get_db_connection()

    conn.execute("""
        UPDATE scores
        SET draws = draws + 1
        WHERE id = 1
    """)

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Draw recorded"
    })


# ---------------------------------------
# RESET SCORES
# ---------------------------------------
@app.route("/api/reset", methods=["POST"])
def reset_scores():

    conn = get_db_connection()

    conn.execute("""
        UPDATE scores
        SET x_wins = 0,
            o_wins = 0,
            draws = 0
        WHERE id = 1
    """)

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Scores reset successfully"
    })


# ---------------------------------------
# RUN APPLICATION
# ---------------------------------------
initialize_database()

if __name__ == "__main__":

    app.run(debug=False, host="127.0.0.1", port=int(os.getenv("PORT", "5001")))