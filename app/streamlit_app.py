import sys
import os
import time
import socket
import subprocess
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.risk_analysis import calculate_student_risk, save_student_submission
from src.model_utils import load_stress_model
from src.voice_intake import (
    FIELD_NAME_MAP,
    FREE_TEXT_SCORE_FIELDS,
    STRESS_MODEL_PATH,
    check_extraction_quality,
    extract_fields,
    get_missing_fields,
    llm_score_from_text,
    predict_stress,
    RealtimeTranscriber,
    AAI_API_KEY,
)

try:
    from src.ai_recommendation import generate_recommendation
except ImportError:
    generate_recommendation = None

try:
    from src.voice_intake import transcribe_audio_file
except ImportError:
    transcribe_audio_file = None

DATA_PATH = ROOT_DIR / "data" / "raw" / "students_mental_health_survey.csv"
REPORT_PATH = ROOT_DIR / "outputs" / "reports" / "correlation_tests.csv"
RISK_LOG_PATH = ROOT_DIR / "data" / "processed" / "student_risk_records.csv"


# -------------------------------------------------------------------
# Relaxation games
# -------------------------------------------------------------------
# The three games remain independent Flask applications. Streamlit
# launches them locally on separate ports and embeds the selected game.
GAMES_DIR = ROOT_DIR / "games"

GAME_CONFIG = {
    "🎮 Tic Tac Toe": {
        "folder": GAMES_DIR / "tic_tac_toe",
        "port": 5001,
        "description": "A quick, simple game for a short mental break.",
    },
    "🧱 Tetris": {
        "folder": GAMES_DIR / "tetris",
        "port": 5002,
        "description": "A focused puzzle game you can play for a few minutes.",
    },
    "🧞 Mind-Fresh": {
        "folder": GAMES_DIR / "mind_fresh",
        "port": 5003,
        "description": "A light guessing game for a fun change of focus.",
    },
}


def _port_is_open(port):
    """Return True when a local service is already listening on the port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _start_game_server(game_name):
    """Start a game Flask server only when it is not already running."""
    config = GAME_CONFIG[game_name]
    folder = config["folder"]
    port = config["port"]

    if not folder.exists():
        return False, f"Game files not found: {folder}"

    if _port_is_open(port):
        return True, None

    app_file = folder / "app.py"
    if not app_file.exists():
        return False, f"Game entry point not found: {app_file}"

    env = os.environ.copy()
    env["PORT"] = str(port)

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        process = subprocess.Popen(
            [sys.executable, str(app_file)],
            cwd=str(folder),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except Exception as exc:
        return False, str(exc)

    # Give Flask a short moment to bind its port.
    for _ in range(20):
        time.sleep(0.15)
        if _port_is_open(port):
            st.session_state.setdefault("game_processes", {})[game_name] = process
            return True, None

    return False, f"{game_name} did not start on port {port}."


def render_relaxation_tab():
    """Render the Mind Break / relaxation games screen."""
    st.markdown('<div class="section-title">🌿 Mind Break</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="primary-intro"><p style="color:#6b8179; font-size:1rem; line-height:1.55;">'
        'Take a short break from the assessment. Choose a small game for relaxation and '
        'entertainment, then return to MindSense whenever you are ready.'
        '</p></div>',
        unsafe_allow_html=True,
    )

    st.info(
        "These activities are for relaxation and entertainment. They are not a medical "
        "treatment or a substitute for professional mental-health support."
    )

    game_name = st.selectbox(
        "Choose an activity",
        list(GAME_CONFIG.keys()),
        key="selected_relaxation_game",
    )

    config = GAME_CONFIG[game_name]

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{game_name}**")
        st.caption(config["description"])
    with col2:
        launch = st.button(
            "▶️ Play",
            use_container_width=True,
            key=f"launch_{game_name}",
        )

    if launch:
        with st.spinner(f"Starting {game_name}..."):
            ok, error = _start_game_server(game_name)
        if not ok:
            st.error(
                f"Could not start {game_name}. Make sure its files are present "
                f"inside `games/`. Details: {error}"
            )
        else:
            st.session_state.active_game = game_name
            st.rerun()

    active_game = st.session_state.get("active_game")

    if active_game:
        active_config = GAME_CONFIG[active_game]
        game_url = f"http://127.0.0.1:{active_config['port']}"

        if _port_is_open(active_config["port"]):
            st.markdown(f"### {active_game}")
            components.iframe(
                game_url,
                height=720,
                scrolling=True,
            )
        else:
            st.warning("The game server is not running. Click Play to start it.")


TEAL = "#0F766E"
CORAL = "#C45C4A"
GOLD = "#C9842A"
NAVY = "#163A3A"


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )

    rename_map = {
        "stress_level": "stress_level",
        "depression_score": "depression_score",
        "anxiety_score": "anxiety_score",
        "cgpa": "cgpa",
        "semester_credit_load": "semester_credit_load",
        "gender": "gender",
        "course": "course",
        "age": "age",
        "sleep_quality": "sleep_quality",
        "physical_activity": "physical_activity",
        "diet_quality": "diet_quality",
        "social_support": "social_support",
        "relationship_status": "relationship_status",
        "substance_use": "substance_use",
        "counseling_service_use": "counseling_service_use",
        "financial_stress": "financial_stress",
        "extracurricular_involvement": "extracurricular_involvement",
        "residence_type": "residence_type",
    }

    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    numeric_columns = [
        "age",
        "cgpa",
        "stress_level",
        "depression_score",
        "anxiety_score",
        "semester_credit_load",
        "financial_stress",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in df.select_dtypes(include="object").columns:
        df[column] = df[column].fillna("Unknown")

    for column in df.select_dtypes(include="number").columns:
        df[column] = df[column].fillna(df[column].median())

    return df


@st.cache_data
def load_correlation_report():
    if REPORT_PATH.exists():
        return pd.read_csv(REPORT_PATH)
    return pd.DataFrame()


def load_risk_log():
    if RISK_LOG_PATH.exists():
        return pd.read_csv(RISK_LOG_PATH)
    return pd.DataFrame()


@st.cache_resource
def load_cached_stress_model():
    """Load the calibrated stress model once per session. Returns
    (model, error_message) - error_message is None on success."""
    try:
        return load_stress_model(STRESS_MODEL_PATH), None
    except Exception as e:
        return None, str(e)


def inject_styles():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

            html, body, [class*="css"] {
                font-family: "Source Sans 3", sans-serif;
            }

            .stApp {
                background:
                    radial-gradient(1200px 500px at -10% -20%, #d7efe8 0%, transparent 55%),
                    radial-gradient(900px 420px at 110% 0%, #f3e6d4 0%, transparent 50%),
                    #f3f6f4;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #102826 0%, #163a3a 100%);
            }

            [data-testid="stSidebar"] * {
                color: #e8f4f0 !important;
            }

            [data-testid="stSidebar"] .stMarkdown p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] span {
                color: #d7ece6 !important;
            }

            [data-testid="stHeader"] {
                background: transparent;
            }

            .block-container {
                padding-top: 1.4rem;
                max-width: 1280px;
            }

            .hero {
                background: linear-gradient(135deg, #102826 0%, #1b5c56 58%, #c9842a 160%);
                border-radius: 28px;
                padding: 2rem 2.2rem;
                color: white;
                margin-bottom: 1.4rem;
                box-shadow: 0 18px 40px rgba(16, 40, 38, 0.22);
            }

            .hero h1 {
                font-family: Fraunces, Georgia, serif;
                font-size: 2.5rem;
                margin: 0 0 0.35rem 0;
                letter-spacing: -0.03em;
            }

            .hero p {
                margin: 0;
                max-width: 720px;
                color: #d9efe9;
                font-size: 1.05rem;
                line-height: 1.55;
            }

            .eyebrow {
                display: inline-block;
                background: rgba(255,255,255,0.12);
                border: 1px solid rgba(255,255,255,0.16);
                border-radius: 999px;
                padding: 0.25rem 0.75rem;
                font-size: 0.78rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                margin-bottom: 0.8rem;
            }

            .metric-card {
                background: white;
                border: 1px solid #dce7e2;
                border-radius: 20px;
                padding: 1.05rem 1.15rem 1.1rem;
                box-shadow: 0 8px 24px rgba(20, 36, 31, 0.05);
                min-height: 126px;
            }

            .metric-card .label {
                font-size: 0.78rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: #5e736c;
                font-weight: 600;
            }

            .metric-card .value {
                font-family: Fraunces, Georgia, serif;
                font-size: 2rem;
                color: #14241f;
                margin-top: 0.35rem;
                line-height: 1.1;
            }

            .metric-card .hint {
                color: #6b8179;
                font-size: 0.85rem;
                margin-top: 0.3rem;
            }

            .panel {
                background: white;
                border: 1px solid #dce7e2;
                border-radius: 22px;
                padding: 1.2rem 1.3rem 0.4rem;
                box-shadow: 0 8px 24px rgba(20, 36, 31, 0.05);
                margin-bottom: 1rem;
            }

            .risk-banner {
                border-radius: 22px;
                padding: 1.3rem 1.4rem;
                color: white;
                margin: 0.6rem 0 1.2rem;
            }

            .risk-banner.high { background: linear-gradient(135deg, #8f3a32, #c45c4a); }
            .risk-banner.moderate { background: linear-gradient(135deg, #8a5a18, #c9842a); }
            .risk-banner.low { background: linear-gradient(135deg, #0f5f58, #1a9b8e); }

            .risk-banner h3 {
                font-family: Fraunces, Georgia, serif;
                margin: 0 0 0.4rem 0;
                font-size: 1.7rem;
            }

            .gauge-track {
                width: 100%;
                height: 12px;
                background: rgba(255,255,255,0.25);
                border-radius: 999px;
                overflow: hidden;
                margin: 0.8rem 0 0.5rem;
            }

            .gauge-fill {
                height: 100%;
                background: #fff;
                border-radius: 999px;
            }

            .section-title {
                font-family: Fraunces, Georgia, serif;
                font-size: 1.45rem;
                color: #14241f;
                margin: 0.3rem 0 0.8rem;
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.4rem;
                background: transparent;
            }

            .stTabs [data-baseweb="tab"] {
                background: white;
                border-radius: 999px;
                padding: 0.55rem 1.1rem;
                border: 1px solid #dce7e2;
            }

            .stTabs [aria-selected="true"] {
                background: #102826;
                color: white;
                font-weight: 600;
            }

            .primary-intro {
                max-width: 900px;
                margin-bottom: 0.6rem;
            }
            .game-card {
                background: white;
                border: 1px solid #dce7e2;
                border-radius: 20px;
                padding: 1rem 1.1rem;
                box-shadow: 0 8px 24px rgba(20, 36, 31, 0.05);
            }


            div[data-testid="stForm"] {
                background: white;
                border: 1px solid #dce7e2;
                border-radius: 22px;
                padding: 1.2rem 1.1rem 0.8rem;
                box-shadow: 0 8px 24px rgba(20, 36, 31, 0.05);
            }

            .stButton > button {
                background: #0f766e;
                color: white;
                border: 0;
                border-radius: 999px;
                padding: 0.55rem 1.3rem;
                font-weight: 600;
            }

            .stButton > button:hover {
                background: #0b5e58;
                color: white;
            }

            .footnote {
                color: #6b8179;
                font-size: 0.85rem;
                margin-top: 1.5rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(title, value, subtitle):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="label">{title}</div>
            <div class="value">{value}</div>
            <div class="hint">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_ai_recommendation(ai_result: dict):
    """Render the JSON returned by src.ai_recommendation.generate_recommendation."""
    if ai_result.get("error"):
        st.warning(
            "AI recommendation is temporarily unavailable, showing a default "
            f"message instead. ({ai_result['error']})"
        )

    st.markdown('<div class="section-title">AI wellbeing recommendation</div>', unsafe_allow_html=True)

    if ai_result.get("summary"):
        st.markdown(f"**{ai_result['summary']}**")

    priority_areas = ai_result.get("priority_areas") or []
    if priority_areas:
        st.markdown("**Priority areas:** " + " · ".join(priority_areas))

    for item in ai_result.get("recommendations") or []:
        with st.container(border=True):
            st.markdown(f"**{item.get('area', 'Recommendation')}**")
            if item.get("problem"):
                st.caption(f"Observed: {item['problem']}")
            if item.get("action"):
                st.write(item["action"])

    if ai_result.get("student_message"):
        st.info(ai_result["student_message"])

    if ai_result.get("professional_support"):
        st.caption(f"When to seek professional support: {ai_result['professional_support']}")


def altair_theme(chart):
    return (
        chart.configure_view(strokeWidth=0)
        .configure_axis(gridColor="#e6eeea", labelColor="#4d635c", titleColor="#163a3a")
        .configure_legend(labelColor="#163a3a", titleColor="#163a3a")
        .properties(height=320)
    )


def render_hero():
    st.markdown(
        """
        <div class="hero">
            <div class="eyebrow">Student wellbeing intelligence</div>
            <h1>MindSense</h1>
            <p>
                A calm, focused workspace for exploring student mental-health patterns,
                academic load, and individual risk signals. Filter the cohort, assess a student,
                and read the evidence without leaving this screen.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title="MindSense",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_styles()
render_hero()

df = load_data()
correlation_df = load_correlation_report()

with st.sidebar:
    st.markdown("### Cohort filters")
    st.caption("Narrow the dashboard to the groups you want to compare.")

    gender_options = sorted(df["gender"].dropna().unique().tolist()) if "gender" in df.columns else []
    course_options = sorted(df["course"].dropna().unique().tolist()) if "course" in df.columns else []

    gender_filter = st.multiselect("Gender", options=gender_options, default=gender_options)
    course_filter = st.multiselect("Course", options=course_options, default=course_options)

    if "age" in df.columns:
        age_min, age_max = int(df["age"].min()), int(df["age"].max())
        age_range = st.slider("Age range", min_value=age_min, max_value=age_max, value=(age_min, age_max))
    else:
        age_range = None

    if "gender" in df.columns and gender_filter:
        df = df[df["gender"].isin(gender_filter)]
    if "course" in df.columns and course_filter:
        df = df[df["course"].isin(course_filter)]
    if age_range is not None and "age" in df.columns:
        df = df[(df["age"] >= age_range[0]) & (df["age"] <= age_range[1])]

    st.markdown("---")
    st.markdown("**How to use this**")
    st.caption(
        "Use Stress Predictor for an assessment, Mind Break for optional relaxation games, "
        "Overview for cohort signals, and Prediction History for saved assessments."
    )

stress_predictor_tab, mind_break_tab, overview_tab, prediction_history_tab = st.tabs(
    ["Stress Predictor", "🌿 Mind Break", "Overview", "Prediction History"]
)

with overview_tab:
    st.markdown('<div class="section-title">Cohort snapshot</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Students", f"{len(df):,}", "Records in the current view")
    with col2:
        metric_card(
            "Avg stress",
            f"{df['stress_level'].mean():.2f}" if "stress_level" in df.columns else "—",
            "Mean stress score",
        )
    with col3:
        metric_card(
            "Avg anxiety",
            f"{df['anxiety_score'].mean():.2f}" if "anxiety_score" in df.columns else "—",
            "Mean anxiety score",
        )
    with col4:
        metric_card(
            "Avg depression",
            f"{df['depression_score'].mean():.2f}" if "depression_score" in df.columns else "—",
            "Mean depression score",
        )

    st.markdown("")
    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("**Stress distribution**")
        if "stress_level" in df.columns:
            hist_df = df[["stress_level"]].copy()
            chart = (
                alt.Chart(hist_df)
                .mark_bar(color=TEAL, cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
                .encode(
                    x=alt.X("stress_level:Q", bin=alt.Bin(maxbins=10), title="Stress level"),
                    y=alt.Y("count()", title="Students"),
                    tooltip=["count()"],
                )
            )
            st.altair_chart(altair_theme(chart), use_container_width=True)
        else:
            st.warning("Stress level is not available in this dataset.")

    with right_col:
        st.markdown("**Average stress by gender**")
        if "gender" in df.columns and "stress_level" in df.columns:
            gender_summary = (
                df.groupby("gender", as_index=False)["stress_level"]
                .mean()
                .rename(columns={"stress_level": "avg_stress"})
            )
            chart = (
                alt.Chart(gender_summary)
                .mark_bar(color="#1B5C56", cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("gender:N", title="Gender", sort="-y"),
                    y=alt.Y("avg_stress:Q", title="Average stress"),
                    tooltip=["gender", alt.Tooltip("avg_stress:Q", format=".2f")],
                )
            )
            st.altair_chart(altair_theme(chart), use_container_width=True)
        else:
            st.warning("Gender is not available in this dataset.")

    extra_left, extra_right = st.columns(2)
    with extra_left:
        st.markdown("**Sleep quality vs stress**")
        if {"sleep_quality", "stress_level"}.issubset(df.columns):
            sleep_summary = (
                df.groupby("sleep_quality", as_index=False)["stress_level"]
                .mean()
                .rename(columns={"stress_level": "avg_stress"})
            )
            chart = (
                alt.Chart(sleep_summary)
                .mark_bar(color=GOLD, cornerRadiusTopLeft=8, cornerRadiusTopRight=8)
                .encode(
                    x=alt.X("sleep_quality:N", title="Sleep quality", sort=["Poor", "Fair", "Average", "Good"]),
                    y=alt.Y("avg_stress:Q", title="Average stress"),
                    tooltip=["sleep_quality", alt.Tooltip("avg_stress:Q", format=".2f")],
                )
            )
            st.altair_chart(altair_theme(chart), use_container_width=True)
        else:
            st.info("Sleep quality is not available for this chart.")

    with extra_right:
        st.markdown("**Course mix in view**")
        if "course" in df.columns:
            course_counts = df["course"].value_counts().reset_index()
            course_counts.columns = ["course", "students"]
            chart = (
                alt.Chart(course_counts)
                .mark_arc(innerRadius=68, stroke="#fff", strokeWidth=2)
                .encode(
                    theta="students:Q",
                    color=alt.Color("course:N", scale=alt.Scale(scheme="tealblues"), legend=alt.Legend(title="Course")),
                    tooltip=["course", "students"],
                )
            )
            st.altair_chart(chart.properties(height=320), use_container_width=True)
        else:
            st.info("Course is not available for this chart.")


def init_voice_state():
    """Initialize persistent state for the local real-time microphone session."""
    defaults = {
        "realtime_transcriber": None,
        "realtime_thread": None,
        "realtime_running": False,
        "realtime_error": None,
        "realtime_transcript": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def start_realtime_transcription():
    """Start the existing AssemblyAI/PyAudio transcriber in a background thread.

    The transcriber itself lives in session_state so Streamlit reruns do not
    lose the microphone/websocket session.
    """
    if RealtimeTranscriber is None:
        raise ImportError(
            "Real-time transcription requires the realtime voice support in "
            "`src.voice_intake.py`."
        )

    if not AAI_API_KEY:
        raise ValueError(
            "ASSEMBLYAI_API_KEY is not configured. Add it to your local .env file."
        )

    if st.session_state.get("realtime_running"):
        return

    transcriber = RealtimeTranscriber()
    st.session_state.realtime_transcriber = transcriber
    st.session_state.realtime_running = True
    st.session_state.realtime_error = None
    st.session_state.realtime_transcript = ""

    def run():
        try:
            transcriber.start_transcription()
        except Exception as exc:
            st.session_state.realtime_error = str(exc)
        finally:
            st.session_state.realtime_running = False
            st.session_state.realtime_transcript = transcriber.get_final_text()

    import threading
    thread = threading.Thread(target=run, daemon=True)
    st.session_state.realtime_thread = thread
    thread.start()


def stop_realtime_transcription():
    """Stop the current websocket/microphone session cleanly."""
    transcriber = st.session_state.get("realtime_transcriber")
    if transcriber is None:
        return

    try:
        transcriber.is_running = False
        if transcriber.ws:
            transcriber.ws.close()
    except Exception as exc:
        st.session_state.realtime_error = str(exc)

    # Give the worker a moment to receive the websocket close event.
    thread = st.session_state.get("realtime_thread")
    if thread and thread.is_alive():
        thread.join(timeout=1.5)

    st.session_state.realtime_running = False
    st.session_state.realtime_transcript = transcriber.get_final_text()


def clear_realtime_session():
    st.session_state.realtime_transcriber = None
    st.session_state.realtime_thread = None
    st.session_state.realtime_running = False
    st.session_state.realtime_error = None
    st.session_state.realtime_transcript = ""


init_voice_state()

with stress_predictor_tab:
    st.markdown('<div class="section-title">Stress Predictor</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="primary-intro"><p style="color:#6b8179; font-size:1rem; line-height:1.55;">'
        'Share how you have been feeling and doing recently. You can type your response, '
        'upload an audio recording, or speak in real time. MindSense will extract the relevant '
        'details and estimate your stress level.'
        '</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    input_mode = st.radio(
        "Input method",
        ["📝 Text", "🎵 Audio file", "🎙️ Real-time speech"],
        horizontal=True,
    )

    intake_text = ""

    # --------------------------------------------------------------
    # 1. TEXT INPUT
    # --------------------------------------------------------------
    if input_mode == "📝 Text":
        # Stop any old microphone session when switching modes.
        if st.session_state.get("realtime_running"):
            stop_realtime_transcription()

        intake_text = st.text_area(
            "Your reflection",
            placeholder=(
                "e.g. I'm 21, studying Computer Science. Sleep has been rough this "
                "semester, maybe 5 hours a night, and I'm carrying 21 credits. "
                "Money's been tight and I don't really have anyone to talk to about it..."
            ),
            height=160,
        )

    # --------------------------------------------------------------
    # 2. AUDIO FILE INPUT
    # --------------------------------------------------------------
    elif input_mode == "🎵 Audio file":
        if st.session_state.get("realtime_running"):
            stop_realtime_transcription()

        st.caption("Upload a short recording. AssemblyAI will convert it to text.")

        if transcribe_audio_file is None:
            st.warning(
                "Audio-file transcription is unavailable. Install the "
                "`assemblyai` package."
            )

        audio_file = st.file_uploader(
            "Upload an audio recording",
            type=["wav", "mp3", "m4a", "ogg", "webm"],
            key="audio_file_input",
        )

        if audio_file is not None and transcribe_audio_file is not None:
            # Store the transcript in session state so a Streamlit rerun does
            # not force another AssemblyAI transcription.
            file_id = f"{audio_file.name}:{audio_file.size}"

            if st.session_state.get("audio_file_id") != file_id:
                with st.spinner("Transcribing audio file..."):
                    tmp_dir = ROOT_DIR / "data" / "processed"
                    tmp_dir.mkdir(parents=True, exist_ok=True)
                    tmp_path = tmp_dir / f"_tmp_{audio_file.name}"

                    try:
                        tmp_path.write_bytes(audio_file.getbuffer())
                        transcript = transcribe_audio_file(str(tmp_path))

                        st.session_state.audio_file_id = file_id
                        st.session_state.audio_file_transcript = transcript or ""
                    except Exception as exc:
                        st.session_state.audio_file_id = None
                        st.session_state.audio_file_transcript = ""
                        st.error(f"Transcription failed: {exc}")
                    finally:
                        tmp_path.unlink(missing_ok=True)

            intake_text = st.session_state.get("audio_file_transcript", "")

            if intake_text:
                st.audio(audio_file)
                st.text_area(
                    "Transcript",
                    value=intake_text,
                    height=140,
                    key="audio_transcript_display",
                )

    # --------------------------------------------------------------
    # 3. REAL-TIME MICROPHONE INPUT
    # --------------------------------------------------------------
    else:
        st.caption(
            "Speak through your computer microphone. MindSense sends the live "
            "audio stream to AssemblyAI and uses the final transcript for analysis."
        )

        if not AAI_API_KEY:
            st.warning(
                "Real-time speech is disabled because `ASSEMBLYAI_API_KEY` is "
                "not set in your `.env` file."
            )
        elif RealtimeTranscriber is None:
            st.warning(
                "Real-time speech requires `websocket-client` and `pyaudio`. "
                "Install them with `pip install websocket-client pyaudio`."
            )
        else:
            col_start, col_stop, col_clear = st.columns(3)

            with col_start:
                start_live = st.button(
                    "🎙️ Start speaking",
                    disabled=st.session_state.realtime_running,
                    use_container_width=True,
                )

            with col_stop:
                stop_live = st.button(
                    "⏹️ Stop",
                    disabled=not st.session_state.realtime_running,
                    use_container_width=True,
                )

            with col_clear:
                clear_live = st.button(
                    "🗑️ Clear",
                    disabled=st.session_state.realtime_running,
                    use_container_width=True,
                )

            if start_live:
                try:
                    start_realtime_transcription()
                    st.rerun()
                except Exception as exc:
                    st.session_state.realtime_running = False
                    st.session_state.realtime_error = str(exc)

            if stop_live:
                stop_realtime_transcription()
                st.rerun()

            if clear_live:
                clear_realtime_session()
                st.rerun()

            if st.session_state.get("realtime_running"):
                st.info(
                    "🔴 Microphone is active. Speak naturally, then press "
                    "**Stop** when you have finished."
                )

                transcriber = st.session_state.get("realtime_transcriber")
                if transcriber is not None:
                    live_text = transcriber.get_final_text()
                    if live_text:
                        st.text_area(
                            "Live transcript",
                            value=live_text,
                            height=140,
                            disabled=True,
                            key="live_transcript_running",
                        )

                # Refresh the displayed transcript while the background
                # websocket/microphone thread is running.
                time.sleep(0.5)
                st.rerun()

            if st.session_state.get("realtime_error"):
                st.error(
                    f"Real-time transcription failed: "
                    f"{st.session_state.realtime_error}"
                )

            if not st.session_state.get("realtime_running"):
                intake_text = st.session_state.get("realtime_transcript", "")

                if intake_text:
                    st.success("Real-time recording finished.")
                    st.text_area(
                        "Final transcript",
                        value=intake_text,
                        height=140,
                        key="live_transcript_final",
                    )
                else:
                    st.caption(
                        "Click **Start speaking**, give your response, then "
                        "click **Stop**."
                    )

    st.markdown("")
    analyze_clicked = st.button(
        "🔎 Extract fields from this response",
        disabled=not intake_text.strip(),
        use_container_width=True,
    )

    if analyze_clicked:
        try:
            with st.spinner("Extracting survey fields with the local LLM (Ollama)..."):
                extracted = extract_fields(intake_text)
            check_extraction_quality(extracted)

            # Age is an integer-valued field in the survey/model.
            if extracted.get("Age") is not None:
                try:
                    extracted["Age"] = int(round(float(extracted["Age"])))
                except (TypeError, ValueError):
                    extracted["Age"] = None

            st.session_state.ai_intake_fields = extracted
            st.session_state.pop("ai_intake_result", None)
        except Exception as e:
            st.error(
                "Couldn't reach the local field-extraction model. Make sure Ollama "
                f"is running (`ollama serve`) and the model is pulled. ({e})"
            )

    extracted_fields = st.session_state.get("ai_intake_fields")
    if extracted_fields:
        missing = get_missing_fields(extracted_fields)
        if missing:
            st.markdown(f"**{len(missing)} field(s) need a manual answer:**")
            with st.form("ai_intake_missing_form"):
                manual_answers = {}
                for m in missing:
                    field_name = m["field"]
                    if field_name in FREE_TEXT_SCORE_FIELDS:
                        manual_answers[field_name] = st.text_input(
                            f"{m['label']} (describe in your own words, e.g. 'pretty stressed about money,academic load etc.')",
                            key=f"missing_{field_name}",
                        )
                    elif m["type"] == "select":
                        manual_answers[field_name] = st.selectbox(m["label"], options=m["options"], key=f"missing_{field_name}")
                    else:
                        if field_name == "Age":
                            manual_answers[field_name] = st.number_input(
                                m["label"],
                                min_value=int(m["min"]),
                                max_value=int(m["max"]),
                                value=int(m["min"]),
                                step=1,
                                format="%d",
                                key=f"missing_{field_name}",
                            )
                        else:
                            manual_answers[field_name] = st.number_input(
                                m["label"],
                                min_value=float(m["min"]),
                                max_value=float(m["max"]),
                                step=0.1,
                                key=f"missing_{field_name}",
                            )
                fill_submitted = st.form_submit_button("Save answers")
            if fill_submitted:
                for field_name in FREE_TEXT_SCORE_FIELDS:
                    raw_text = manual_answers.get(field_name, "")
                    if isinstance(raw_text, str):
                        if raw_text.strip():
                            with st.spinner(f"Interpreting your {field_name.replace('_', ' ').lower()} description..."):
                                manual_answers[field_name] = llm_score_from_text(field_name, raw_text.strip())['score']
                        else:
                            manual_answers[field_name] = None
                extracted_fields.update(manual_answers)
                st.session_state.ai_intake_fields = extracted_fields
                st.success("Answers saved. You can now predict stress below.")
        else:
            st.success("All fields were understood from your input.")

        st.dataframe(
            pd.DataFrame([extracted_fields]).T.rename(columns={0: "value"}),
            use_container_width=True,
        )

        predict_clicked = st.button("🧠 Predict stress & get recommendation", use_container_width=True)
        if predict_clicked:
            model, model_error = load_cached_stress_model()
            if model_error:
                st.error(f"Couldn't load the stress model: {model_error}")
            else:
                result = predict_stress(model, extracted_fields)
                student_payload = {v: extracted_fields.get(k) for k, v in FIELD_NAME_MAP.items()}
                student_payload["stress_level"] = result["stress_level"]

                risk = calculate_student_risk(student_payload)
                save_student_submission(student_payload)

                st.session_state.ai_intake_result = {
                    "ml_result": result,
                    "risk": risk,
                    "student_payload": student_payload,
                }
                st.session_state.pop("ai_intake_recommendation", None)

    intake_result = st.session_state.get("ai_intake_result")
    if intake_result:
        ml_result = intake_result["ml_result"]
        risk = intake_result["risk"]

        col_ml, _ = st.columns(2)
        with col_ml:
            metric_card(
                "Predicted stress",
                f"{ml_result['stress_label']} risk",
                "",
            )

        st.caption(risk["recommendation"])

        if generate_recommendation is not None:
            if "ai_intake_recommendation" not in st.session_state:
                with st.spinner("Generating AI wellbeing recommendation..."):
                    st.session_state.ai_intake_recommendation = generate_recommendation(
                        intake_result["student_payload"], risk["score"], risk["level"]
                    )
            render_ai_recommendation(st.session_state.ai_intake_recommendation)
        else:
            st.info(
                "Install `google-genai` and set `GEMINI_API_KEY` in `.env` to also "
                "get an AI-generated, personalized recommendation here."
            )

with mind_break_tab:
    render_relaxation_tab()

with prediction_history_tab:
    st.markdown('<div class="section-title">Prediction history</div>', unsafe_allow_html=True)
    st.caption("Review prior student assessments and prediction details.")

    risk_log = load_risk_log()
    if risk_log.empty:
        st.info("No saved prediction history yet. Run a prediction in the Stress Predictor tab to generate the first record.")
    else:
        history_cols = [
            c for c in [
                "student_name",
                "course",
                "gender",
                "age",
                "stress_level",
                "depression_score",
                "anxiety_score",
                "financial_stress",
                "risk_score",
                "risk_level",
                "recommendation",
            ]
            if c in risk_log.columns
        ]
        history_df = risk_log[history_cols].copy()
        if "student_name" in history_df.columns:
            history_df["student_name"] = history_df["student_name"].fillna("Unknown student")
        st.dataframe(history_df.tail(20).iloc[::-1], use_container_width=True, hide_index=True)

    st.markdown(
        """
        <p class="footnote">
            MindSense is an exploratory screening tool, not a clinical diagnosis.
            High-risk flags should be followed up by qualified counselling and academic support staff.
        </p>
        """,
        unsafe_allow_html=True,
    )
