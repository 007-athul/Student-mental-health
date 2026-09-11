// ========================================
// GAME VARIABLES
// ========================================

let board = [
    "", "", "",
    "", "", "",
    "", "", ""
];

let currentPlayer = "X";
let gameOver = false;
let aiThinking = false;

let playerX = "Player";
let playerO = "MindSense AI";

let aiDifficulty = "medium";


// ========================================
// HTML ELEMENTS
// ========================================

const cells =
    document.querySelectorAll(".cell");

const turnText =
    document.getElementById("turnText");

const result =
    document.getElementById("result");

const newGameButton =
    document.getElementById("newGame");

const resetScoresButton =
    document.getElementById("resetScores");

const savePlayerButton =
    document.getElementById("savePlayer");

const playerInput =
    document.getElementById("playerName");

const aiDifficultySelect =
    document.getElementById("aiDifficulty");


// ========================================
// WINNING COMBINATIONS
// ========================================

const winningCombinations = [

    [0, 1, 2],

    [3, 4, 5],

    [6, 7, 8],

    [0, 3, 6],

    [1, 4, 7],

    [2, 5, 8],

    [0, 4, 8],

    [2, 4, 6]

];


// ========================================
// LOAD SCORES
// ========================================

async function loadScores() {

    try {

        const response =
            await fetch("/api/scores");

        const data =
            await response.json();


        playerX = data.player_x;

        playerXInputValue();


        document.getElementById(
            "scorePlayerX"
        ).textContent = playerX;


        document.getElementById(
            "scorePlayerO"
        ).textContent = "MindSense AI";


        document.getElementById(
            "xWins"
        ).textContent = data.x_wins;


        document.getElementById(
            "oWins"
        ).textContent = data.o_wins;


        document.getElementById(
            "draws"
        ).textContent = data.draws;


        updateTurnText();

    } catch (error) {

        console.error(
            "Error loading scores:",
            error
        );

    }

}


function playerXInputValue() {

    if (playerInput) {

        playerInput.value = playerX;

    }

}


// ========================================
// CELL CLICK
// ========================================

cells.forEach(cell => {

    cell.addEventListener(
        "click",
        () => {

            const index =
                Number(cell.dataset.index);


            // Don't allow invalid moves
            if (board[index] !== "") {
                return;
            }


            // Don't allow moves after game ends
            if (gameOver) {
                return;
            }


            // User can only play X
            if (
                currentPlayer !== "X" ||
                aiThinking
            ) {
                return;
            }


            makeMove(index);

        }
    );

});


// ========================================
// MAKE HUMAN MOVE
// ========================================

function makeMove(index) {

    if (
        gameOver ||
        board[index] !== "" ||
        currentPlayer !== "X"
    ) {
        return;
    }


    board[index] = "X";


    cells[index].textContent = "X";

    cells[index].classList.add("x");


    const winner =
        checkWinner();


    if (winner) {

        endGame(
            winner.winner,
            winner.combo
        );

        return;
    }


    // Check draw
    if (
        board.every(
            cell => cell !== ""
        )
    ) {

        endDraw();

        return;
    }


    // AI's turn
    currentPlayer = "O";

    aiThinking = true;

    updateTurnText();


    // Small delay makes the AI feel natural
    setTimeout(
        makeAIMove,
        450
    );

}


// ========================================
// AI MOVE
// ========================================

function makeAIMove() {

    if (gameOver) {
        return;
    }


    let move;


    if (
        aiDifficulty === "easy"
    ) {

        move =
            getRandomMove();

    }

    else if (
        aiDifficulty === "medium"
    ) {

        move =
            getMediumMove();

    }

    else {

        move =
            getBestMove();

    }


    if (move === null) {

        aiThinking = false;

        return;

    }


    board[move] = "O";


    cells[move].textContent = "O";

    cells[move].classList.add("o");


    aiThinking = false;


    const winner =
        checkWinner();


    if (winner) {

        endGame(
            winner.winner,
            winner.combo
        );

        return;
    }


    // Check draw
    if (
        board.every(
            cell => cell !== ""
        )
    ) {

        endDraw();

        return;
    }


    // Back to human
    currentPlayer = "X";

    updateTurnText();

}


// ========================================
// EASY AI
// Random legal move
// ========================================

function getRandomMove() {

    const available = [];


    board.forEach(
        (value, index) => {

            if (value === "") {

                available.push(index);

            }

        }
    );


    if (
        available.length === 0
    ) {

        return null;

    }


    return available[
        Math.floor(
            Math.random() *
            available.length
        )
    ];

}


// ========================================
// MEDIUM AI
// ========================================

function getMediumMove() {

    // 1. Try to win
    const winningMove =
        findWinningMove("O");


    if (
        winningMove !== null
    ) {

        return winningMove;

    }


    // 2. Block the player
    const blockingMove =
        findWinningMove("X");


    if (
        blockingMove !== null
    ) {

        return blockingMove;

    }


    // 3. Take center
    if (
        board[4] === ""
    ) {

        return 4;

    }


    // 4. Take a corner
    const corners =
        [0, 2, 6, 8]
            .filter(
                index =>
                    board[index] === ""
            );


    if (
        corners.length > 0
    ) {

        return corners[
            Math.floor(
                Math.random() *
                corners.length
            )
        ];

    }


    // 5. Random move
    return getRandomMove();

}


// ========================================
// FIND WINNING MOVE
// ========================================

function findWinningMove(symbol) {

    for (
        let i = 0;
        i < board.length;
        i++
    ) {

        if (
            board[i] !== ""
        ) {

            continue;

        }


        board[i] = symbol;


        const winner =
            checkWinner();


        board[i] = "";


        if (
            winner &&
            winner.winner === symbol
        ) {

            return i;

        }

    }


    return null;

}


// ========================================
// HARD AI - MINIMAX
// ========================================

function getBestMove() {

    let bestScore =
        -Infinity;

    let bestMove =
        null;


    for (
        let i = 0;
        i < board.length;
        i++
    ) {

        if (
            board[i] !== ""
        ) {

            continue;

        }


        board[i] = "O";


        const score =
            minimax(
                board,
                0,
                false
            );


        board[i] = "";


        if (
            score > bestScore
        ) {

            bestScore = score;

            bestMove = i;

        }

    }


    return bestMove;

}


function minimax(
    state,
    depth,
    maximizing
) {

    const winner =
        getStateWinner(state);


    if (
        winner === "O"
    ) {

        return 10 - depth;

    }


    if (
        winner === "X"
    ) {

        return depth - 10;

    }


    if (
        winner === "draw"
    ) {

        return 0;

    }


    // AI's turn
    if (maximizing) {

        let bestScore =
            -Infinity;


        for (
            let i = 0;
            i < state.length;
            i++
        ) {

            if (
                state[i] !== ""
            ) {

                continue;

            }


            state[i] = "O";


            const score =
                minimax(
                    state,
                    depth + 1,
                    false
                );


            state[i] = "";


            bestScore =
                Math.max(
                    bestScore,
                    score
                );

        }


        return bestScore;

    }


    // Human's turn
    let bestScore =
        Infinity;


    for (
        let i = 0;
        i < state.length;
        i++
    ) {

        if (
            state[i] !== ""
        ) {

            continue;

        }


        state[i] = "X";


        const score =
            minimax(
                state,
                depth + 1,
                true
            );


        state[i] = "";


        bestScore =
            Math.min(
                bestScore,
                score
            );

    }


    return bestScore;

}


// ========================================
// STATE WINNER
// ========================================

function getStateWinner(state) {

    for (
        const combination
        of winningCombinations
    ) {

        const [a, b, c] =
            combination;


        if (
            state[a] &&
            state[a] === state[b] &&
            state[a] === state[c]
        ) {

            return state[a];

        }

    }


    if (
        state.every(
            cell => cell !== ""
        )
    ) {

        return "draw";

    }


    return null;

}


// ========================================
// CHECK WINNER
// ========================================

function checkWinner() {

    for (
        const combination
        of winningCombinations
    ) {

        const [a, b, c] =
            combination;


        if (
            board[a] &&
            board[a] === board[b] &&
            board[a] === board[c]
        ) {

            return {
                winner: board[a],
                combo: combination
            };

        }

    }


    return null;

}


// ========================================
// END GAME
// ========================================

async function endGame(
    winner,
    winningCombo
) {

    gameOver = true;

    aiThinking = false;


    // Highlight winning cells
    winningCombo.forEach(
        index => {

            cells[index]
                .classList.add(
                    "winner"
                );

        }
    );


    const winnerName =
        winner === "X"
            ? playerX
            : "MindSense AI";


    result.textContent =
        `${winnerName} Wins!`;


    turnText.textContent =
        "Game Over";


    try {

        await fetch(
            "/api/win",
            {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    winner: winner
                })

            }
        );


        await loadScores();


    } catch (error) {

        console.error(
            "Error saving score:",
            error
        );

    }

}


// ========================================
// DRAW
// ========================================

async function endDraw() {

    gameOver = true;

    aiThinking = false;


    result.textContent =
        "It's a Draw!";


    turnText.textContent =
        "Game Over";


    try {

        await fetch(
            "/api/draw",
            {
                method: "POST"
            }
        );


        await loadScores();


    } catch (error) {

        console.error(
            "Error saving draw:",
            error
        );

    }

}


// ========================================
// UPDATE TURN
// ========================================

function updateTurnText() {

    if (gameOver) {

        return;

    }


    if (
        currentPlayer === "O"
    ) {

        turnText.textContent =
            "MindSense AI is thinking...";

        return;

    }


    turnText.textContent =
        `${playerX}'s Turn (X)`;

}


// ========================================
// NEW GAME
// ========================================

newGameButton.addEventListener(
    "click",
    startNewGame
);


function startNewGame() {

    board = [
        "", "", "",
        "", "", "",
        "", "", ""
    ];


    currentPlayer = "X";

    gameOver = false;

    aiThinking = false;


    result.textContent = "";


    cells.forEach(
        cell => {

            cell.textContent = "";

            cell.classList.remove(
                "x",
                "o",
                "winner"
            );

        }
    );


    updateTurnText();

}


// ========================================
// SAVE PLAYER NAME
// ========================================

savePlayerButton.addEventListener(
    "click",
    async () => {

        const newPlayer =
            playerInput.value.trim()
            || "Player";


        try {

            const response =
                await fetch(
                    "/api/players",
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            player_x:
                                newPlayer,

                            player_o:
                                "MindSense AI"

                        })

                    }
                );


            const data =
                await response.json();


            playerX =
                data.player_x;


            playerInput.value =
                playerX;


            document.getElementById(
                "scorePlayerX"
            ).textContent =
                playerX;


            updateTurnText();


        } catch (error) {

            console.error(
                "Error saving player:",
                error
            );

        }

    }
);


// ========================================
// AI DIFFICULTY
// ========================================

aiDifficultySelect.addEventListener(
    "change",
    () => {

        aiDifficulty =
            aiDifficultySelect.value;

    }
);


// ========================================
// RESET SCORES
// ========================================

resetScoresButton.addEventListener(
    "click",
    async () => {

        const confirmReset =
            confirm(
                "Are you sure you want to reset all scores?"
            );


        if (!confirmReset) {

            return;

        }


        try {

            await fetch(
                "/api/reset",
                {
                    method: "POST"
                }
            );


            await loadScores();

            startNewGame();


            alert(
                "Scores have been reset!"
            );


        } catch (error) {

            console.error(
                "Error resetting scores:",
                error
            );

        }

    }
);


// ========================================
// START APPLICATION
// ========================================

loadScores();