from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


ROOT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
RISK_LOG_PATH = PROCESSED_DIR / "student_risk_records.csv"


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_choice(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _category_score(value: Any, mapping: Dict[str, int]) -> int:
    normalized = _normalize_choice(value)
    return mapping.get(normalized, 0)


def calculate_student_risk(student: Dict[str, Any]) -> Dict[str, Any]:
    stress = _as_float(student.get("stress_level"), 0.0)
    depression = _as_float(student.get("depression_score"), 0.0)
    anxiety = _as_float(student.get("anxiety_score"), 0.0)
    financial_stress = _as_float(student.get("financial_stress"), 0.0)
    credit_load = _as_float(student.get("semester_credit_load"), 0.0)
    cgpa = _as_float(student.get("cgpa"), 0.0)

    sleep_score = _category_score(student.get("sleep_quality"), {
        "poor": 18,
        "fair": 10,
        "average": 10,
        "good": 0,
    })
    activity_score = _category_score(student.get("physical_activity"), {
        "low": 15,
        "moderate": 8,
        "high": 0,
    })
    diet_score = _category_score(student.get("diet_quality"), {
        "poor": 15,
        "fair": 8,
        "average": 8,
        "good": 0,
    })
    support_score = _category_score(student.get("social_support"), {
        "low": 20,
        "moderate": 10,
        "fair": 10,
        "strong": 0,
    })

    score = (
        stress * 4.5
        + depression * 4.5
        + anxiety * 4.5
        + financial_stress * 3
        + max(0, credit_load - 15) * 2
        + max(0, 4.0 - cgpa) * 18
        + sleep_score
        + activity_score
        + diet_score
        + support_score
    )
    score = min(100, round(score))

    if score >= 60:
        level = "High"
        recommendation = "Immediate support is recommended. Arrange counselling, academic advising, and a follow-up check-in within the next week."
    elif score >= 35:
        level = "Moderate"
        recommendation = "This student needs close monitoring. Encourage regular counselling, sleep and routine support, and a check-in with academic support services."
    else:
        level = "Low"
        recommendation = "Current indicators are stable. Encourage healthy routines and periodic monitoring to prevent escalation."

    return {
        "score": int(score),
        "level": level,
        "recommendation": recommendation,
    }


def save_student_submission(student_data: Dict[str, Any]) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    record = dict(student_data)
    risk = calculate_student_risk(record)
    record["risk_score"] = risk["score"]
    record["risk_level"] = risk["level"]
    record["recommendation"] = risk["recommendation"]

    if RISK_LOG_PATH.exists():
        import pandas as pd

        df = pd.read_csv(RISK_LOG_PATH)
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        df.to_csv(RISK_LOG_PATH, index=False)
    else:
        import pandas as pd

        pd.DataFrame([record]).to_csv(RISK_LOG_PATH, index=False)

    return RISK_LOG_PATH
