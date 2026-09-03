import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.risk_analysis import calculate_student_risk, save_student_submission
DATA_PATH = ROOT_DIR / "data" / "raw" / "students_mental_health_survey.csv"
REPORT_PATH = ROOT_DIR / "outputs" / "reports" / "correlation_tests.csv"
RISK_LOG_PATH = ROOT_DIR / "data" / "processed" / "student_risk_records.csv"

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
        "Start on Overview for cohort signals. Use Risk intake to score a student. "
        "Patterns and Data explain the relationships behind the scores."
    )

overview_tab, risk_tab, patterns_tab, data_tab = st.tabs(
    ["Overview", "Risk intake", "Patterns", "Data & notes"]
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

with risk_tab:
    st.markdown('<div class="section-title">Individual risk assessment</div>', unsafe_allow_html=True)
    st.caption("Enter a student profile to estimate wellbeing risk from academic and lifestyle signals.")

    with st.form("student_risk_form"):
        identity_1, identity_2, identity_3 = st.columns(3)
        with identity_1:
            student_name = st.text_input("Student name")
        with identity_2:
            student_course = st.selectbox(
                "Course",
                options=course_options or ["General", "Computer Science", "Business", "Engineering", "Arts"],
            )
        with identity_3:
            student_gender = st.selectbox("Gender", options=gender_options or ["Male", "Female", "Other"])

        row_a1, row_a2, row_a3 = st.columns(3)
        with row_a1:
            age = st.number_input("Age", min_value=15, max_value=40, value=20)
        with row_a2:
            cgpa = st.slider("CGPA", min_value=0.0, max_value=4.0, value=3.0, step=0.1)
        with row_a3:
            semester_credit_load = st.number_input("Semester credit load", min_value=0, max_value=30, value=15)

        st.markdown("**Mental health scores**")
        row_b1, row_b2, row_b3, row_b4 = st.columns(4)
        with row_b1:
            stress_level = st.slider("Stress (1-10)", min_value=1, max_value=10, value=5)
        with row_b2:
            depression_score = st.slider("Depression (1-10)", min_value=1, max_value=10, value=3)
        with row_b3:
            anxiety_score = st.slider("Anxiety (1-10)", min_value=1, max_value=10, value=4)
        with row_b4:
            financial_stress = st.slider("Financial stress (1-10)", min_value=1, max_value=10, value=3)

        st.markdown("**Protective factors**")
        row_c1, row_c2, row_c3, row_c4 = st.columns(4)
        with row_c1:
            sleep_quality = st.selectbox("Sleep quality", options=["Poor", "Fair", "Good"])
        with row_c2:
            physical_activity = st.selectbox("Physical activity", options=["Low", "Moderate", "High"])
        with row_c3:
            diet_quality = st.selectbox("Diet quality", options=["Poor", "Fair", "Good"])
        with row_c4:
            social_support = st.selectbox("Social support", options=["Low", "Moderate", "Strong"])

        submitted = st.form_submit_button("Analyze risk")

    if submitted:
        student_payload = {
            "student_name": student_name,
            "course": student_course,
            "gender": student_gender,
            "age": age,
            "cgpa": cgpa,
            "stress_level": stress_level,
            "depression_score": depression_score,
            "anxiety_score": anxiety_score,
            "sleep_quality": sleep_quality,
            "physical_activity": physical_activity,
            "diet_quality": diet_quality,
            "social_support": social_support,
            "financial_stress": financial_stress,
            "semester_credit_load": semester_credit_load,
        }
        risk_result = calculate_student_risk(student_payload)
        save_student_submission(student_payload)
        st.session_state.last_risk = {
            "name": student_name.strip() or "This student",
            **risk_result,
        }

    last_risk = st.session_state.get("last_risk")
    if last_risk:
        st.markdown(
            f"""
            <div class="risk-banner {last_risk['level'].lower()}">
                <h3>{last_risk['name']}: {last_risk['level']} risk</h3>
                <div>Composite score {last_risk['score']} / 100</div>
                <div class="gauge-track">
                    <div class="gauge-fill" style="width: {last_risk['score']}%;"></div>
                </div>
                <p>{last_risk['recommendation']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.success("Assessment saved to the local risk log.")

    risk_log = load_risk_log()
    if not risk_log.empty:
        st.markdown("**Recent assessments**")
        preview_cols = [c for c in ["student_name", "course", "risk_score", "risk_level"] if c in risk_log.columns]
        st.dataframe(risk_log[preview_cols].tail(8).iloc[::-1], use_container_width=True, hide_index=True)

with patterns_tab:
    st.markdown('<div class="section-title">Academic and wellbeing patterns</div>', unsafe_allow_html=True)

    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown("**Academic load vs stress**")
        if {"semester_credit_load", "stress_level"}.issubset(df.columns):
            sample = df.sample(min(len(df), 800), random_state=7)
            points = (
                alt.Chart(sample)
                .mark_circle(size=48, opacity=0.35, color=TEAL)
                .encode(
                    x=alt.X("semester_credit_load:Q", title="Semester credit load"),
                    y=alt.Y("stress_level:Q", title="Stress level"),
                    tooltip=["semester_credit_load", "stress_level"],
                )
            )
            trend = points.transform_regression("semester_credit_load", "stress_level").mark_line(color=CORAL, size=3)
            st.altair_chart(altair_theme(points + trend), use_container_width=True)
        else:
            st.warning("Required columns are missing for this chart.")

    with right_col:
        st.markdown("**CGPA vs stress**")
        if {"cgpa", "stress_level"}.issubset(df.columns):
            sample = df.sample(min(len(df), 800), random_state=11)
            encode_kwargs = {
                "x": alt.X("cgpa:Q", title="CGPA"),
                "y": alt.Y("stress_level:Q", title="Stress level"),
                "tooltip": ["cgpa", "stress_level"],
            }
            if "gender" in sample.columns:
                encode_kwargs["color"] = alt.Color("gender:N", scale=alt.Scale(scheme="category10"), title="Gender")
                encode_kwargs["tooltip"] = ["cgpa", "stress_level", "gender"]
            chart = alt.Chart(sample).mark_circle(size=55, opacity=0.55).encode(**encode_kwargs)
            st.altair_chart(altair_theme(chart), use_container_width=True)
        else:
            st.warning("Required columns are missing for this chart.")

    st.markdown("**Correlation summary**")
    if not correlation_df.empty:
        pretty_corr = correlation_df.copy()
        for column in pretty_corr.select_dtypes(include="number").columns:
            pretty_corr[column] = pretty_corr[column].map(lambda value: f"{value:.4f}" if abs(value) < 10 else f"{value:.0f}")
        st.dataframe(pretty_corr, use_container_width=True, hide_index=True)
    else:
        st.info("No saved correlation report was found. The app will show the raw dataset view instead.")

    st.markdown("**What this suggests**")
    if not correlation_df.empty:
        st.write(
            "The correlation findings indicate that academic factors such as semester workload and CGPA "
            "show very little association with stress in this dataset. The strongest observable patterns "
            "are weak associations involving stress, anxiety, and depression scores, which suggests that "
            "mental-health measures are related but not strongly predictive."
        )
    else:
        st.write(
            "The dashboard highlights student-level patterns in mental health and academic performance. "
            "Use these visualizations to explore relationships before drawing conclusions."
        )

with data_tab:
    st.markdown('<div class="section-title">Dataset preview</div>', unsafe_allow_html=True)
    st.caption("First 20 rows of the currently filtered cohort.")
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)

    st.markdown(
        """
        <p class="footnote">
            MindSense is an exploratory screening tool, not a clinical diagnosis.
            High-risk flags should be followed up by qualified counselling and academic support staff.
        </p>
        """,
        unsafe_allow_html=True,
    )
