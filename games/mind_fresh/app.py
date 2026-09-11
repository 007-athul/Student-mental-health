from flask import Flask, render_template, request, jsonify
import akinator
import sqlite3
import uuid
import os
import requests
from datetime import datetime

app = Flask(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

DATABASE = "game_history.db"

games = {}

IMAGE_FOLDER = "character_images"

os.makedirs(IMAGE_FOLDER, exist_ok=True)


# ============================================================
# DATABASE
# ============================================================

def init_db():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_name TEXT,
            description TEXT,
            pseudo TEXT,
            photo TEXT,
            questions INTEGER,
            progress REAL,
            played_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# SAVE GAME
# ============================================================

def save_game(
    character_name,
    description,
    pseudo,
    photo,
    questions,
    progress
):

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO game_history
        (
            character_name,
            description,
            pseudo,
            photo,
            questions,
            progress,
            played_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        character_name,
        description,
        pseudo,
        photo,
        questions,
        progress,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# ============================================================
# DOWNLOAD IMAGE
# ============================================================

def download_image(photo_url, character_name):

    if not photo_url:
        return None

    try:

        print("\n================================")
        print("DOWNLOADING CHARACTER PHOTO")
        print("================================")

        print("Character:", character_name)
        print("Photo URL:", photo_url)

        response = requests.get(
            photo_url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        print(
            "HTTP Status:",
            response.status_code
        )

        if response.status_code != 200:

            return None

        content_type = response.headers.get(
            "Content-Type",
            ""
        )

        print(
            "Content Type:",
            content_type
        )

        if not content_type.startswith("image"):

            print(
                "The returned content is not an image."
            )

            return None

        safe_name = "".join(
            c if c.isalnum() else "_"
            for c in character_name
        )

        filename = safe_name + ".jpg"

        filepath = os.path.join(
            IMAGE_FOLDER,
            filename
        )

        with open(
            filepath,
            "wb"
        ) as file:

            file.write(
                response.content
            )

        print(
            "Image saved:",
            filepath
        )

        return "/character-image/" + filename

    except Exception as e:

        print(
            "IMAGE DOWNLOAD ERROR:",
            e
        )

        return None


# ============================================================
# SERVE CHARACTER IMAGE
# ============================================================

@app.route(
    "/character-image/<filename>"
)
def character_image(filename):

    filepath = os.path.join(
        IMAGE_FOLDER,
        filename
    )

    if not os.path.exists(filepath):

        return "Image not found", 404

    from flask import send_file

    return send_file(
        filepath
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# START GAME
# ============================================================

@app.route(
    "/api/start",
    methods=["POST"]
)
def start_game():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        theme = data.get(
            "theme",
            "c"
        )

        print("\n================================")
        print("START GAME")
        print("================================")

        print(
            "Theme:",
            theme
        )

        aki = akinator.Akinator()

        aki.start_game(
            language="en",
            child_mode=False,
            theme=theme
        )

        game_id = str(
            uuid.uuid4()
        )

        games[game_id] = {

            "aki": aki,

            "questions": 0,

            "theme": theme

        }

        return jsonify({

            "success": True,

            "game_id": game_id,

            "question": str(aki),

            "progress": getattr(
                aki,
                "progression",
                0
            ),

            "questions": 0

        })

    except Exception as e:

        print(
            "START ERROR:",
            e
        )

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# ============================================================
# GET FINAL RESULT
# ============================================================

def get_final_result(game):

    aki = game["aki"]

    # Current package exposes these
    # directly as properties.

    name = getattr(
        aki,
        "name_proposition",
        ""
    )

    description = getattr(
        aki,
        "description_proposition",
        ""
    )

    pseudo = getattr(
        aki,
        "pseudo",
        ""
    )

    photo = getattr(
        aki,
        "photo",
        ""
    )

    progress = getattr(
        aki,
        "progression",
        0
    )

    questions = game[
        "questions"
    ]


    print("\n================================")
    print("FINAL RESULT")
    print("================================")

    print(
        "Name:",
        name
    )

    print(
        "Description:",
        description
    )

    print(
        "Pseudo:",
        pseudo
    )

    print(
        "Photo:",
        photo
    )

    print(
        "Progress:",
        progress
    )


    # ========================================================
    # DOWNLOAD PHOTO
    # ========================================================

    local_photo = None

    if photo:

        local_photo = download_image(
            photo,
            name
        )


    # Use local image if possible
    # otherwise use original Akinator URL.

    final_photo = (
        local_photo
        if local_photo
        else photo
    )


    # ========================================================
    # SAVE HISTORY
    # ========================================================

    save_game(

        character_name=name,

        description=description,

        pseudo=pseudo,

        photo=final_photo,

        questions=questions,

        progress=progress

    )


    return {

        "name": name,

        "description": description,

        "pseudo": pseudo,

        "photo": final_photo,

        "progress": progress

    }


# ============================================================
# ANSWER
# ============================================================

@app.route(
    "/api/answer",
    methods=["POST"]
)
def answer():

    try:

        data = request.get_json()

        game_id = data.get(
            "game_id"
        )

        answer_value = data.get(
            "answer"
        )


        if game_id not in games:

            return jsonify({

                "success": False,

                "error":
                "Game not found."

            }), 404


        game = games[game_id]

        aki = game["aki"]


        valid_answers = [
            "y",
            "n",
            "i",
            "p",
            "pn"
        ]


        if answer_value not in valid_answers:

            return jsonify({

                "success": False,

                "error":
                "Invalid answer."

            }), 400


        # ====================================================
        # IMPORTANT:
        # CHECK WHETHER AKINATOR IS CURRENTLY GUESSING
        # ====================================================

        aki_is_guessing = bool(
            getattr(
                aki,
                "win",
                False
            )
        )


        # ====================================================
        # FINAL PROPOSITION
        # ====================================================

        if aki_is_guessing:

            print("\n================================")
            print("AKINATOR MADE A PROPOSITION")
            print("================================")

            print(
                "Character:",
                aki.name_proposition
            )

            print(
                "User answer:",
                answer_value
            )


            # ------------------------------------------------
            # USER SAID YES
            # ------------------------------------------------

            if answer_value == "y":

                print(
                    "User accepted the guess."
                )

                # IMPORTANT:
                # Do NOT call aki.win()
                #
                # aki.win is a BOOLEAN.
                #
                # choose() accepts the proposition.

                aki.choose()


                result = get_final_result(
                    game
                )


                return jsonify({

                    "success": True,

                    "finished": True,

                    "questions":
                    game["questions"],

                    "guess":
                    result

                })


            # ------------------------------------------------
            # USER SAID NO
            # ------------------------------------------------

            elif answer_value == "n":

                print(
                    "User rejected the guess."
                )

                # Exclude current proposition
                # and continue the game.

                aki.exclude()


                return jsonify({

                    "success": True,

                    "finished": False,

                    "question":
                    str(aki),

                    "progress":
                    getattr(
                        aki,
                        "progression",
                        0
                    ),

                    "questions":
                    game["questions"]

                })


            # ------------------------------------------------
            # OTHER ANSWERS DURING PROPOSITION
            # ------------------------------------------------

            else:

                return jsonify({

                    "success": False,

                    "error":
                    "Please answer Yes or No to the final guess."

                }), 400


        # ====================================================
        # NORMAL QUESTION
        # ====================================================

        print("\n================================")
        print("NORMAL QUESTION")
        print("================================")

        print(
            "Question:",
            str(aki)
        )

        print(
            "Answer:",
            answer_value
        )


        aki.answer(
            answer_value
        )


        game["questions"] += 1


        # ====================================================
        # DID AKINATOR MAKE A GUESS?
        # ====================================================

        if bool(
            getattr(
                aki,
                "win",
                False
            )
        ):

            print(
                "Akinator is now proposing:"
            )

            print(
                aki.name_proposition
            )


        # ====================================================
        # RETURN NEXT QUESTION
        # ====================================================

        return jsonify({

            "success": True,

            "finished": False,

            "question":
            str(aki),

            "progress":
            getattr(
                aki,
                "progression",
                0
            ),

            "questions":
            game["questions"],

            "is_guess":
            bool(
                getattr(
                    aki,
                    "win",
                    False
                )
            )

        })


    except Exception as e:

        print("\n================================")
        print("ANSWER ERROR")
        print("================================")

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# ============================================================
# BACK
# ============================================================

@app.route(
    "/api/back",
    methods=["POST"]
)
def back():

    try:

        data = request.get_json()

        game_id = data.get(
            "game_id"
        )


        if game_id not in games:

            return jsonify({

                "success": False,

                "error":
                "Game not found."

            }), 404


        game = games[game_id]

        aki = game["aki"]


        # Cannot go back after final result
        if bool(
            getattr(
                aki,
                "win",
                False
            )
        ):

            return jsonify({

                "success": False,

                "error":
                "Please answer the current guess first."

            }), 400


        aki.back()


        if game["questions"] > 0:

            game["questions"] -= 1


        return jsonify({

            "success": True,

            "finished": False,

            "question":
            str(aki),

            "progress":
            getattr(
                aki,
                "progression",
                0
            ),

            "questions":
            game["questions"]

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# ============================================================
# HISTORY
# ============================================================

@app.route(
    "/api/history",
    methods=["GET"]
)
def history():

    try:

        conn = sqlite3.connect(
            DATABASE
        )

        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                character_name,
                description,
                pseudo,
                photo,
                questions,
                progress,
                played_at
            FROM game_history
            ORDER BY id DESC
            LIMIT 20
        """)

        rows = cursor.fetchall()

        conn.close()


        history_data = []


        for row in rows:

            history_data.append({

                "name": row[0],

                "description": row[1],

                "pseudo": row[2],

                "photo": row[3],

                "questions": row[4],

                "progress": row[5],

                "played_at": row[6]

            })


        return jsonify({

            "success": True,

            "history":
            history_data

        })


    except Exception as e:

        return jsonify({

            "success": False,

            "error": str(e)

        }), 500


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    init_db()

    app.run(debug=False, host="127.0.0.1", port=int(os.getenv("PORT", "5003")))