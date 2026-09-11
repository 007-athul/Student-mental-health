const COLS = 10;
const ROWS = 20;
const BLOCK = 30;

const boardCanvas = document.getElementById("board");
const ctx = boardCanvas.getContext("2d");
const nextCanvas = document.getElementById("next");
const nextCtx = nextCanvas.getContext("2d");

const scoreEl = document.getElementById("score");
const linesEl = document.getElementById("lines");
const levelEl = document.getElementById("level");
const leaderboardEl = document.getElementById("leaderboard");

const overlay = document.getElementById("overlay");
const overlayTitle = document.getElementById("overlayTitle");
const overlayText = document.getElementById("overlayText");
const nameArea = document.getElementById("nameArea");
const playerName = document.getElementById("playerName");
const startBtn = document.getElementById("startBtn");
const continueBtn = document.getElementById("continueBtn");
const restartBtn = document.getElementById("restartBtn");

const COLORS = {
    I: "#38bdf8",
    O: "#facc15",
    T: "#c084fc",
    S: "#4ade80",
    Z: "#fb7185",
    J: "#60a5fa",
    L: "#fb923c"
};

const SHAPES = {
    I: [[1,1,1,1]],
    O: [[1,1],[1,1]],
    T: [[0,1,0],[1,1,1]],
    S: [[0,1,1],[1,1,0]],
    Z: [[1,1,0],[0,1,1]],
    J: [[1,0,0],[1,1,1]],
    L: [[0,0,1],[1,1,1]]
};

let board;
let current;
let next;
let score = 0;
let lines = 0;
let level = 1;
let dropCounter = 0;
let lastTime = 0;
let running = false;
let paused = false;
let gameId = null;
let player = "";
let animationId = null;
let serverTimer = null;

function makeBoard() {
    return Array.from({ length: ROWS }, () => Array(COLS).fill(null));
}

function randomPiece() {
    const types = Object.keys(SHAPES);
    const type = types[Math.floor(Math.random() * types.length)];
    return {
        type,
        matrix: SHAPES[type].map(row => [...row]),
        x: Math.floor(COLS / 2) - 1,
        y: 0
    };
}

function drawCell(context, x, y, color, size = BLOCK) {
    context.fillStyle = color;
    context.fillRect(x * size + 1, y * size + 1, size - 2, size - 2);
}

function draw() {
    ctx.fillStyle = "#111827";
    ctx.fillRect(0, 0, boardCanvas.width, boardCanvas.height);

    for (let y = 0; y < ROWS; y++) {
        for (let x = 0; x < COLS; x++) {
            if (board[y][x]) drawCell(ctx, x, y, COLORS[board[y][x]]);
        }
    }

    if (current) {
        current.matrix.forEach((row, dy) => {
            row.forEach((value, dx) => {
                if (value) {
                    drawCell(ctx, current.x + dx, current.y + dy, COLORS[current.type]);
                }
            });
        });
    }
}

function drawNext() {
    nextCtx.fillStyle = "#f3f4f6";
    nextCtx.fillRect(0, 0, 120, 120);

    const matrix = next.matrix;
    const size = 24;
    const offsetX = Math.floor((5 - matrix[0].length) / 2);
    const offsetY = Math.floor((5 - matrix.length) / 2);

    matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value) drawCell(nextCtx, x + offsetX, y + offsetY, COLORS[next.type], size);
        });
    });
}

function collide(piece = current) {
    for (let y = 0; y < piece.matrix.length; y++) {
        for (let x = 0; x < piece.matrix[y].length; x++) {
            if (!piece.matrix[y][x]) continue;
            const px = piece.x + x;
            const py = piece.y + y;

            if (px < 0 || px >= COLS || py >= ROWS) return true;
            if (py >= 0 && board[py][px]) return true;
        }
    }
    return false;
}

function merge() {
    current.matrix.forEach((row, y) => {
        row.forEach((value, x) => {
            if (value && current.y + y >= 0) {
                board[current.y + y][current.x + x] = current.type;
            }
        });
    });
}

function rotateMatrix(matrix) {
    return matrix[0].map((_, index) =>
        matrix.map(row => row[index]).reverse()
    );
}

function rotate() {
    if (!running || paused) return;
    const old = current.matrix;
    const oldX = current.x;
    current.matrix = rotateMatrix(current.matrix);

    let offset = 1;
    while (collide()) {
        current.x += offset;
        offset = -(offset + (offset > 0 ? 1 : -1));
        if (Math.abs(offset) > 4) {
            current.matrix = old;
            current.x = oldX;
            return;
        }
    }
}

function move(dx) {
    if (!running || paused) return;
    current.x += dx;
    if (collide()) current.x -= dx;
}

function softDrop() {
    if (!running || paused) return;
    current.y++;
    if (collide()) {
        current.y--;
        lockPiece();
    }
    dropCounter = 0;
}

function hardDrop() {
    if (!running || paused) return;
    while (!collide()) current.y++;
    current.y--;
    lockPiece();
}

function lockPiece() {
    merge();
    clearLines();
    current = next;
    current.x = Math.floor(COLS / 2) - 1;
    current.y = 0;
    next = randomPiece();
    drawNext();

    if (collide()) endGame();
    draw();
}

function clearLines() {
    let cleared = 0;

    outer:
    for (let y = ROWS - 1; y >= 0; y--) {
        for (let x = 0; x < COLS; x++) {
            if (!board[y][x]) continue outer;
        }
        board.splice(y, 1);
        board.unshift(Array(COLS).fill(null));
        y++;
        cleared++;
    }

    if (cleared > 0) {
        const points = [0, 100, 300, 500, 800];
        score += points[cleared] * level;
        lines += cleared;
        level = Math.floor(lines / 10) + 1;
        updateStats();
        sendUpdate();
    }
}

function updateStats() {
    scoreEl.textContent = score;
    linesEl.textContent = lines;
    levelEl.textContent = level;
}

function dropInterval() {
    return Math.max(90, 850 - (level - 1) * 70);
}

function update(time = 0) {
    if (!running) return;

    const delta = time - lastTime;
    lastTime = time;

    if (!paused) {
        dropCounter += delta;
        if (dropCounter > dropInterval()) softDrop();
        draw();
    }

    animationId = requestAnimationFrame(update);
}

async function startGame() {
    const name = playerName.value.trim();
    if (!name) {
        playerName.focus();
        return;
    }

    try {
        const response = await fetch("/api/game/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ player: name })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not start game.");

        player = name;
        gameId = data.game_id;
        board = makeBoard();
        score = 0;
        lines = 0;
        level = 1;
        current = randomPiece();
        next = randomPiece();
        running = true;
        paused = false;
        updateStats();
        drawNext();

        overlay.classList.add("hidden");
        clearInterval(serverTimer);
        serverTimer = setInterval(sendUpdate, 3000);

        cancelAnimationFrame(animationId);
        lastTime = performance.now();
        animationId = requestAnimationFrame(update);
    } catch (error) {
        overlayText.textContent = error.message;
    }
}

async function sendUpdate() {
    if (!running || !gameId) return;

    try {
        await fetch("/api/game/update", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                game_id: gameId,
                score,
                lines,
                level
            })
        });
    } catch (_) {
        // Temporary network errors should not stop local gameplay.
    }
}

async function endGame() {
    if (!running) return;

    running = false;
    clearInterval(serverTimer);
    cancelAnimationFrame(animationId);

    let result = { score, lines, level };

    try {
        const response = await fetch("/api/game/end", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                game_id: gameId,
                score,
                lines,
                level
            })
        });
        const data = await response.json();
        if (response.ok) result = data;
    } catch (_) {}

    overlayTitle.textContent = "Game Over";
    overlayText.textContent =
        `${player}, your score is ${result.score}. Want another round?`;
    nameArea.classList.add("hidden");
    continueBtn.classList.remove("hidden");
    overlay.classList.remove("hidden");

    loadLeaderboard();
}

function restart() {
    if (running && gameId) {
        fetch("/api/game/abandon", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ game_id: gameId })
        }).catch(() => {});
    }

    running = false;
    clearInterval(serverTimer);
    cancelAnimationFrame(animationId);

    overlayTitle.textContent = "Tetris";
    overlayText.textContent = "Enter your name to start.";
    nameArea.classList.remove("hidden");
    continueBtn.classList.add("hidden");
    overlay.classList.remove("hidden");
}

function togglePause() {
    if (!running) return;
    paused = !paused;
    if (paused) {
        overlayTitle.textContent = "Paused";
        overlayText.textContent = "Take a breath. Continue when ready.";
        nameArea.classList.add("hidden");
        continueBtn.classList.remove("hidden");
        overlay.classList.remove("hidden");
    } else {
        overlay.classList.add("hidden");
        lastTime = performance.now();
    }
}

document.addEventListener("keydown", event => {
    if (event.key === "ArrowLeft") move(-1);
    else if (event.key === "ArrowRight") move(1);
    else if (event.key === "ArrowDown") softDrop();
    else if (event.key === "ArrowUp") rotate();
    else if (event.code === "Space") {
        event.preventDefault();
        hardDrop();
    }
    else if (event.key.toLowerCase() === "p") togglePause();
});

startBtn.addEventListener("click", startGame);
continueBtn.addEventListener("click", () => {
    if (overlayTitle.textContent === "Game Over") {
        restart();
    } else {
        paused = false;
        overlay.classList.add("hidden");
        lastTime = performance.now();
    }
});
restartBtn.addEventListener("click", restart);

playerName.addEventListener("keydown", e => {
    if (e.key === "Enter") startGame();
});

async function loadLeaderboard() {
    try {
        const response = await fetch("/api/leaderboard");
        const data = await response.json();

        leaderboardEl.innerHTML = "";
        if (!data.length) {
            leaderboardEl.innerHTML = "<li>No scores yet</li>";
            return;
        }

        data.forEach(row => {
            const li = document.createElement("li");
            li.textContent = `${row.player} — ${row.score}`;
            leaderboardEl.appendChild(li);
        });
    } catch (_) {
        leaderboardEl.innerHTML = "<li>Leaderboard unavailable</li>";
    }
}

board = makeBoard();
draw();
loadLeaderboard();
