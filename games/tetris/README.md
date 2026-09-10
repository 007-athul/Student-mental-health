# Tetris — Flask + JavaScript

## Requirements
- Python 3.9+
- pip

## Run

```bash
cd tetris
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open:

http://127.0.0.1:5000

## Features
- Classic 10x20 Tetris board
- Seven standard tetrominoes
- Rotation, movement, soft drop, hard drop
- Score, lines and levels
- Next-piece preview
- Pause/restart
- SQLite leaderboard
- Server-created game sessions
- Periodic server-side score updates
- Server-side monotonic/proportional score checks
- Server-side level/line validation
- Final score is limited to the highest score observed by the server

## Important security note

The browser still performs the actual Tetris simulation, so this is a practical student-project anti-cheat implementation, not a fully cheat-proof competitive game. For a production leaderboard, move the authoritative game simulation to the server (or validate a signed event stream/replay) and store sessions in Redis or a database rather than process memory.
