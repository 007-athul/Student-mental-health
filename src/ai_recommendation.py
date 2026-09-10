"""Generates supportive, non-clinical wellbeing recommendations for a student
using Gemini, based on the rule-based risk score from `risk_analysis.py`.

Requires GEMINI_API_KEY in a local .env file (see .env.example). The client
is created lazily so importing this module - and the rest of the app - never
fails just because a Gemini key hasn't been configured yet; you only see an
error if you actually try to generate a recommendation without one.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

_client = None


def _normalize_student_payload(student: Dict[str, Any]) -> Dict[str, Any]:
    """Keep student age as an integer before sending it to Gemini."""
    normalized = dict(student)
    age = normalized.get("age")
    if age is None or age == "":
        return normalized

    try:
        normalized["age"] = int(float(age))
    except (TypeError, ValueError):
        pass

    return normalized


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Add it to a local .env file "
                "(see .env.example)."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _fallback_response(error: Exception) -> Dict[str, Any]:
    return {
        "summary": "The AI recommendation service could not generate a result.",
        "priority_areas": [],
        "recommendations": [],
        "student_message": (
            "The risk assessment was completed, but personalized AI "
            "recommendations are currently unavailable."
        ),
        "professional_support": (
            "Consider contacting a qualified student counselor or "
            "mental-health professional if concerns persist."
        ),
        "error": str(error),
    }


def generate_recommendation(
    student: Dict[str, Any],
    risk_score: float,
    risk_level: str,
) -> Dict[str, Any]:
    normalized_student = _normalize_student_payload(student)
    student_json = json.dumps(normalized_student, indent=2, default=str)

    prompt = f"""
You are a student wellbeing recommendation assistant.

Analyze the following student information.

This is a student wellbeing screening system.
You are NOT a doctor and must NOT diagnose
any mental-health disorder.

STUDENT INFORMATION:

{student_json}

RISK SCORE:

{risk_score}/100

RISK LEVEL:

{risk_level}

Identify the main factors that may be affecting
the student's wellbeing.

Consider:

- Age
- Gender
- Course
- CGPA
- Semester credit load
- Stress
- Anxiety
- Depression-related score
- Financial stress
- Sleep quality
- Physical activity
- Diet quality
- Social support
- Relationship status
- Substance use
- Counseling service use
- Extracurricular involvement
- Residence type

Give practical and supportive recommendations.

Return ONLY valid JSON using this structure:

{{
    "summary": "Short overall assessment",

    "priority_areas": [
        "Priority 1",
        "Priority 2",
        "Priority 3"
    ],

    "recommendations": [
        {{
            "area": "Sleep",
            "problem": "Observed issue",
            "action": "Practical recommendation"
        }},
        {{
            "area": "Academic workload",
            "problem": "Observed issue",
            "action": "Practical recommendation"
        }},
        {{
            "area": "Stress management",
            "problem": "Observed issue",
            "action": "Practical recommendation"
        }}
    ],

    "student_message":
        "Supportive message for the student",

    "professional_support":
        "When the student should consider seeking qualified professional support"
}}

Important rules:

- Do NOT diagnose depression.
- Do NOT diagnose anxiety.
- Do NOT prescribe medication.
- Do NOT recommend changing medication.
- Do NOT make clinical claims.
- Do NOT assume one variable proves a mental-health condition.
- Give practical student-friendly suggestions.
- Use supportive and non-judgmental language.
- For high-risk results, recommend appropriate professional support.
"""

    try:
        client = _get_client()

        # The Interactions API (client.interactions.create) is the current,
        # GA-recommended way to call Gemini models as of 2026 - this matches
        # the original implementation, not the older generate_content path.
        interaction = client.interactions.create(
            model=GEMINI_MODEL,
            input=prompt,
        )

        text = (interaction.output_text or "").strip()

        # Remove markdown JSON fences if Gemini adds them
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        return json.loads(text)

    except Exception as e:
        return _fallback_response(e)