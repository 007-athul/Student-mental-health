// ============================================================
// GLOBAL VARIABLES
// ============================================================

let gameId = null;

let selectedTheme = "c";

let questionCount = 0;

let isProcessing = false;


// ============================================================
// ELEMENTS
// ============================================================

const startScreen =
    document.getElementById("startScreen");

const gameScreen =
    document.getElementById("gameScreen");

const resultScreen =
    document.getElementById("resultScreen");

const startBtn =
    document.getElementById("startBtn");

const questionText =
    document.getElementById("questionText");

const questionNumber =
    document.getElementById("questionNumber");

const progressBar =
    document.getElementById("progressBar");

const progressText =
    document.getElementById("progressText");

const backBtn =
    document.getElementById("backBtn");

const restartBtn =
    document.getElementById("restartBtn");

const tryAgainBtn =
    document.getElementById("tryAgainBtn");

const correctBtn =
    document.getElementById("correctBtn");

const guessName =
    document.getElementById("guessName");

const guessDescription =
    document.getElementById("guessDescription");

const guessPseudo =
    document.getElementById("guessPseudo");

const guessImage =
    document.getElementById("guessImage");

const guessImageContainer =
    document.getElementById(
        "guessImageContainer"
    );

const totalQuestions =
    document.getElementById("totalQuestions");

const progressValue =
    document.getElementById("progressValue");

const errorMessage =
    document.getElementById("errorMessage");


// ============================================================
// CATEGORY BUTTONS
// ============================================================

const categoryButtons =
    document.querySelectorAll(
        ".category-btn"
    );


categoryButtons.forEach(button => {

    button.addEventListener(
        "click",
        function () {

            // Don't change theme during a game
            if (gameId) {

                showError(
                    "Please restart the game before changing category."
                );

                return;

            }


            categoryButtons.forEach(btn => {

                btn.classList.remove(
                    "active"
                );

            });


            this.classList.add(
                "active"
            );


            selectedTheme =
                this.dataset.theme;


            console.log(
                "Selected theme:",
                selectedTheme
            );

        }
    );

});


// ============================================================
// SHOW SCREEN
// ============================================================

function showScreen(screen) {

    startScreen.classList.remove(
        "active"
    );

    gameScreen.classList.remove(
        "active"
    );

    resultScreen.classList.remove(
        "active"
    );


    screen.classList.add(
        "active"
    );

}


// ============================================================
// ERROR
// ============================================================

function showError(message) {

    errorMessage.textContent =
        message;

    errorMessage.style.display =
        "block";


    setTimeout(
        () => {

            errorMessage.style.display =
                "none";

        },
        5000
    );

}


// ============================================================
// UPDATE GAME UI
// ============================================================

function updateGameUI(
    question,
    progress,
    questions
) {

    questionText.textContent =
        question ||
        "Loading...";


    questionCount =
        questions || 0;


    questionNumber.textContent =
        questionCount;


    let percentage =
        Number(progress) || 0;


    percentage =
        Math.max(
            0,
            Math.min(
                100,
                percentage
            )
        );


    progressBar.style.width =
        percentage + "%";


    progressText.textContent =
        Math.round(
            percentage
        ) + "%";

}


// ============================================================
// START GAME
// ============================================================

startBtn.addEventListener(
    "click",
    startGame
);


async function startGame() {

    if (isProcessing) {
        return;
    }


    isProcessing = true;


    try {

        startBtn.disabled =
            true;


        const response =
            await fetch(
                "/api/start",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            theme:
                                selectedTheme

                        })

                }
            );


        const data =
            await response.json();


        console.log(
            "START:",
            data
        );


        if (!data.success) {

            throw new Error(
                data.error ||
                "Unable to start game."
            );

        }


        gameId =
            data.game_id;


        questionCount =
            0;


        updateGameUI(

            data.question,

            data.progress,

            data.questions

        );


        showScreen(
            gameScreen
        );


    } catch (error) {

        console.error(
            error
        );

        showError(
            error.message
        );


    } finally {

        isProcessing =
            false;

        startBtn.disabled =
            false;

    }

}


// ============================================================
// ANSWER BUTTONS
// ============================================================

const answerButtons =
    document.querySelectorAll(
        ".answer-btn"
    );


answerButtons.forEach(button => {

    button.addEventListener(
        "click",
        () => {

            sendAnswer(
                button.dataset.answer
            );

        }
    );

});


// ============================================================
// SEND ANSWER
// ============================================================

async function sendAnswer(answer) {

    if (
        isProcessing ||
        !gameId
    ) {
        return;
    }


    isProcessing =
        true;


    answerButtons.forEach(button => {

        button.disabled =
            true;

    });


    try {

        const response =
            await fetch(
                "/api/answer",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            game_id:
                                gameId,

                            answer:
                                answer

                        })

                }
            );


        const data =
            await response.json();


        console.log(
            "ANSWER:",
            data
        );


        if (!data.success) {

            throw new Error(
                data.error ||
                "Unable to submit answer."
            );

        }


        // ====================================================
        // FINAL RESULT
        // ====================================================

        if (data.finished) {

            displayGuess(

                data.guess,

                data.questions

            );

            return;

        }


        // ====================================================
        // NEXT QUESTION
        // ====================================================

        updateGameUI(

            data.question,

            data.progress,

            data.questions

        );


    } catch (error) {

        console.error(
            error
        );

        showError(
            error.message
        );


    } finally {

        isProcessing =
            false;


        answerButtons.forEach(button => {

            button.disabled =
                false;

        });

    }

}


// ============================================================
// DISPLAY RESULT
// ============================================================

function displayGuess(
    guess,
    questions
) {

    if (!guess) {

        showError(
            "No result was returned."
        );

        return;

    }


    console.log(
        "FINAL GUESS:",
        guess
    );


    // NAME

    guessName.textContent =
        guess.name ||
        "Unknown";


    // DESCRIPTION

    guessDescription.textContent =
        guess.description ||
        "No description available.";


    // PSEUDO

    if (guess.pseudo) {

        guessPseudo.textContent =
            "Akinator ID: " +
            guess.pseudo;

        guessPseudo.style.display =
            "block";

    } else {

        guessPseudo.style.display =
            "none";

    }


    // QUESTIONS

    totalQuestions.textContent =
        questions || 0;


    // PROGRESS

    const progress =
        Number(
            guess.progress
        ) || 0;


    progressValue.textContent =
        Math.round(
            progress
        );


    // ========================================================
    // PHOTO
    // ========================================================

    if (
        guess.photo &&
        guess.photo.trim() !== ""
    ) {

        guessImageContainer.classList.remove(
            "hidden"
        );


        guessImage.src =
            guess.photo;


        guessImage.alt =
            guess.name ||
            "Result";


        guessImage.onerror =
            function () {

                console.error(
                    "Image failed:",
                    guess.photo
                );


                guessImageContainer.classList.add(
                    "hidden"
                );

            };

    } else {

        guessImageContainer.classList.add(
            "hidden"
        );

    }


    // SHOW RESULT

    showScreen(
        resultScreen
    );

}


// ============================================================
// BACK
// ============================================================

backBtn.addEventListener(
    "click",
    goBack
);


async function goBack() {

    if (
        isProcessing ||
        !gameId
    ) {
        return;
    }


    isProcessing =
        true;


    try {

        const response =
            await fetch(
                "/api/back",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            game_id:
                                gameId

                        })

                }
            );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.error ||
                "Unable to go back."
            );

        }


        updateGameUI(

            data.question,

            data.progress,

            data.questions

        );


    } catch (error) {

        console.error(
            error
        );

        showError(
            error.message
        );


    } finally {

        isProcessing =
            false;

    }

}


// ============================================================
// RESTART
// ============================================================

restartBtn.addEventListener(
    "click",
    restartGame
);


tryAgainBtn.addEventListener(
    "click",
    restartGame
);


correctBtn.addEventListener(
    "click",
    restartGame
);


function restartGame() {

    gameId =
        null;


    questionCount =
        0;


    updateGameUI(
        "",
        0,
        0
    );


    showScreen(
        startScreen
    );

}


// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================

document.addEventListener(
    "keydown",
    event => {

        if (
            !gameScreen.classList.contains(
                "active"
            )
        ) {
            return;
        }


        if (isProcessing) {
            return;
        }


        switch (
        event.key.toLowerCase()
        ) {

            case "y":

                sendAnswer("y");

                break;


            case "n":

                sendAnswer("n");

                break;


            case "i":

                sendAnswer("i");

                break;


            case "p":

                sendAnswer("p");

                break;

        }

    }
);