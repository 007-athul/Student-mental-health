from src.ai_recommendation import _normalize_student_payload
from src.risk_analysis import calculate_student_risk


def test_normalize_student_payload_keeps_age_as_int():
    payload = {
        "age": "21.0",
        "gender": "Female",
        "course": "Computer Science",
        "stress_level": 5,
    }

    normalized = _normalize_student_payload(payload)

    assert isinstance(normalized["age"], int)
    assert normalized["age"] == 21


def test_calculate_student_risk_returns_low_for_healthy_profile():
    payload = {
        "stress_level": 2,
        "depression_score": 1,
        "anxiety_score": 2,
        "sleep_quality": "Good",
        "physical_activity": "High",
        "diet_quality": "Good",
        "social_support": "Strong",
        "financial_stress": 1,
        "semester_credit_load": 12,
        "cgpa": 3.8,
    }

    risk = calculate_student_risk(payload)

    assert risk["score"] < 30
    assert risk["level"] == "Low"


def test_calculate_student_risk_returns_high_for_at_risk_profile():
    payload = {
        "stress_level": 9,
        "depression_score": 8,
        "anxiety_score": 9,
        "sleep_quality": "Poor",
        "physical_activity": "Low",
        "diet_quality": "Poor",
        "social_support": "Low",
        "financial_stress": 9,
        "semester_credit_load": 22,
        "cgpa": 1.8,
    }

    risk = calculate_student_risk(payload)

    assert risk["score"] >= 60
    assert risk["level"] in {"High", "Moderate"}


def test_calculate_student_risk_caps_if_total_exceeds_hundred():
    payload = {
        "stress_level": 10,
        "depression_score": 10,
        "anxiety_score": 10,
        "sleep_quality": "Poor",
        "physical_activity": "Low",
        "diet_quality": "Poor",
        "social_support": "Low",
        "financial_stress": 10,
        "semester_credit_load": 30,
        "cgpa": 0.0,
    }

    risk = calculate_student_risk(payload)

    assert risk["score"] <= 100
