import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="MindSense", page_icon="🧠", layout="wide")

st.markdown(
    """
    <style>
        .main {
            background: linear-gradient(180deg, #f5f7ff 0%, #eef5ff 100%);
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
        }
        div[data-testid="stSidebar"] {
            background: #101828;
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "checkins" not in st.session_state:
    st.session_state.checkins = [
        {"date": "2026-08-01", "mood": 4, "stress": 3, "sleep": 7, "focus": 5},
        {"date": "2026-08-02", "mood": 3, "stress": 5, "sleep": 6, "focus": 4},
        {"date": "2026-08-03", "mood": 4, "stress": 2, "sleep": 8, "focus": 6},
        {"date": "2026-08-04", "mood": 5, "stress": 2, "sleep": 8, "focus": 7},
    ]

mood_labels = ["Very low", "Low", "Okay", "Good", "Great"]


def add_checkin(mood, stress, sleep, focus, note):
    st.session_state.checkins.append(
        {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "mood": mood,
            "stress": stress,
            "sleep": sleep,
            "focus": focus,
            "note": note,
        }
    )


with st.sidebar:
    st.markdown("# 🧠 MindSense")
    st.caption("Your emotional clarity companion")
    menu = st.radio(
        "Navigation",
        ["Overview", "Daily Check-In", "Insights", "Journal"],
        index=0,
    )
    st.markdown("---")
    st.markdown("### Daily intention")
    st.info("Pause, notice, and respond with kindness.")


if menu == "Overview":
    st.title("Welcome back")
    st.subheader("Your mental wellness snapshot")

    if st.session_state.checkins:
        df = pd.DataFrame(st.session_state.checkins)
        mood_avg = round(df["mood"].mean(), 1)
        stress_avg = round(df["stress"].mean(), 1)
        sleep_avg = round(df["sleep"].mean(), 1)
        focus_avg = round(df["focus"].mean(), 1)
    else:
        mood_avg, stress_avg, sleep_avg, focus_avg = 0, 0, 0, 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mood", f"{mood_avg}/5")
    col2.metric("Stress", f"{stress_avg}/5")
    col3.metric("Sleep", f"{sleep_avg}h")
    col4.metric("Focus", f"{focus_avg}/7")

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        st.subheader("Recent check-ins")
        recent = pd.DataFrame(st.session_state.checkins)[-3:][::-1]
        st.dataframe(
            recent[["date", "mood", "stress", "sleep", "focus"]].rename(
                columns={
                    "date": "Date",
                    "mood": "Mood",
                    "stress": "Stress",
                    "sleep": "Sleep (h)",
                    "focus": "Focus",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    with right:
        st.subheader("Wellness highlights")
        st.success("✅ Your mood trend is improving over recent days.")
        st.warning("⚠️ Stress peaked earlier this week—recovery habits are helping.")
        st.info("💡 Your strongest performance is when sleep is above 7.5 hours.")

elif menu == "Daily Check-In":
    st.title("Daily check-in")
    st.caption("A short reflection can help you notice patterns and feel more grounded.")

    with st.form("checkin_form"):
        mood = st.slider("How do you feel today?", 1, 5, 3, format="%d")
        stress = st.slider("Stress level", 1, 5, 2, format="%d")
        sleep = st.slider("Sleep last night (hours)", 4, 10, 7, 1)
        focus = st.slider("Focus level today", 1, 7, 4, 1)
        note = st.text_area("Quick note", placeholder="What stood out today?")
        submitted = st.form_submit_button("Save check-in")

    if submitted:
        add_checkin(mood, stress, sleep, focus, note)
        st.success("Check-in saved successfully.")

    st.markdown("---")
    st.subheader("Current mood summary")
    st.write(f"Mood: {mood_labels[mood - 1]}")
    st.write(f"Stress: {stress}/5")
    st.write(f"Sleep: {sleep} hours")
    st.write(f"Focus: {focus}/7")

elif menu == "Insights":
    st.title("Insights")
    st.caption("Patterns, trends, and signals from your recent check-ins.")

    if st.session_state.checkins:
        df = pd.DataFrame(st.session_state.checkins)
        trend_df = df[["date", "mood", "stress", "focus"]].copy()
        trend_df["date"] = pd.to_datetime(trend_df["date"])
        trend_df = trend_df.sort_values("date")

        st.subheader("Mood & stress trend")
        st.line_chart(trend_df.set_index("date"), y=["mood", "stress"], color=["#4c6fff", "#ff7f7f"])

        st.subheader("Focus pattern")
        st.bar_chart(trend_df.set_index("date")["focus"], color="#4cc9f0")

        st.markdown("---")
        st.subheader("Suggested reflection")
        avg_stress = round(df["stress"].mean(), 1)
        avg_mood = round(df["mood"].mean(), 1)
        if avg_stress > 3:
            st.warning("Stress is elevated compared to your recent average. Consider a reset break, breathing exercise, or a short walk.")
        else:
            st.success("Your stress load is balanced. Keep building on the routine that is helping you feel steady.")

        if avg_mood >= 4:
            st.info("Your mood is trending positively. Try to protect the habits that are supporting your energy.")
        else:
            st.info("Focus on one small win today—sleep, hydration, or a reset activity can support mood recovery.")
    else:
        st.info("Add a few daily check-ins to unlock personalized insights.")

else:
    st.title("Journal")
    st.caption("Capture your thoughts without judgment.")

    if st.session_state.checkins:
        notes = [entry.get("note", "") for entry in st.session_state.checkins if entry.get("note")]
        if notes:
            st.subheader("Recent reflections")
            for note in notes[-5:][::-1]:
                st.markdown(f"- {note}")
        else:
            st.info("No journal notes yet. Try adding one in your next check-in.")
    else:
        st.info("Your journal entries will appear here after you save a check-in.")

    st.markdown("---")
    journal_entry = st.text_area("Write a thought for today", height=180, placeholder="What is on my mind right now?")
    if st.button("Save entry"):
        if journal_entry.strip():
            st.session_state.checkins.append(
                {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "mood": 3,
                    "stress": 3,
                    "sleep": 7,
                    "focus": 4,
                    "note": journal_entry,
                }
            )
            st.success("Journal entry saved.")
        else:
            st.warning("Please write something before saving.")

st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)
