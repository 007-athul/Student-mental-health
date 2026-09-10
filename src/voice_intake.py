"""
MindSense - Mental Health Assessment Pipeline

Pipeline:
    Text / Audio
        ↓
    AssemblyAI Transcription (optional)
        ↓
    Ollama / Llama Field Extraction
        ↓
    Missing-field Follow-up
        ↓
    Calibrated Stress Model
        ↓
    Stress Level + Probabilities

This module is safe to import from Streamlit even when optional
audio dependencies are not installed.

Audio dependencies are required only when using:
    - Real-time microphone transcription
    - Audio-file transcription

Environment variables:
    ASSEMBLYAI_API_KEY
    OLLAMA_URL
    OLLAMA_MODEL
"""

from __future__ import annotations

import json
import os
import time
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

from src.model_utils import (
    TemperatureScaledModel,
    load_stress_model,
)

load_dotenv()


# ==================================================================
# OPTIONAL AUDIO DEPENDENCIES
# ==================================================================

try:
    import assemblyai as aai
except ImportError:
    aai = None

try:
    import websocket
except ImportError:
    websocket = None

try:
    import pyaudio
except ImportError:
    pyaudio = None


# ==================================================================
# CONFIGURATION
# ==================================================================

ROOT_DIR = Path(__file__).resolve().parent.parent

# AssemblyAI
AAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")

if aai is not None and AAI_API_KEY:
    aai.settings.api_key = AAI_API_KEY

# Ollama
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/chat"
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.1:8b"
)

# Trained model
STRESS_MODEL_PATH = (
    ROOT_DIR
    / "models"
    / "calibrated_stress_model.pkl"
)

# Missing field warning threshold
MISSING_WARNING_THRESHOLD = 0.5

# Audio settings
SAMPLE_RATE = 16000
CHUNK_SIZE = 800
CHANNELS = 1
ENCODING = "pcm_s16le"


# ==================================================================
# FIELD DEFINITIONS
# ==================================================================

FIELD_ORDER = [
    "Age",
    "Course",
    "Gender",
    "CGPA",
    "Depression_Score",
    "Anxiety_Score",
    "Sleep_Quality",
    "Physical_Activity",
    "Diet_Quality",
    "Social_Support",
    "Relationship_Status",
    "Substance_Use",
    "Counseling_Service_Use",
    "Family_History",
    "Chronic_Illness",
    "Financial_Stress",
    "Extracurricular_Involvement",
    "Semester_Credit_Load",
    "Residence_Type",
]


# Extraction field → model column
FIELD_NAME_MAP = {
    "Age": "age",
    "Course": "course",
    "Gender": "gender",
    "CGPA": "cgpa",
    "Depression_Score": "depression_score",
    "Anxiety_Score": "anxiety_score",
    "Sleep_Quality": "sleep_quality",
    "Physical_Activity": "physical_activity",
    "Diet_Quality": "diet_quality",
    "Social_Support": "social_support",
    "Relationship_Status": "relationship_status",
    "Substance_Use": "substance_use",
    "Counseling_Service_Use": "counseling_service_use",
    "Family_History": "family_history",
    "Chronic_Illness": "chronic_illness",
    "Financial_Stress": "financial_stress",
    "Extracurricular_Involvement": "extracurricular_involvement",
    "Semester_Credit_Load": "semester_credit_load",
    "Residence_Type": "residence_type",
}


# ==================================================================
# FALLBACK VALUES
# ==================================================================
# These are used only when a field remains unanswered.
# Prefer collecting missing values through the follow-up questions.

DEFAULT_VALUES = {
    "age": 21,
    "course": "Others",
    "gender": "Male",
    "cgpa": 3.0,
    "depression_score": 2,
    "anxiety_score": 2,
    "sleep_quality": "Average",
    "physical_activity": "Moderate",
    "diet_quality": "Average",
    "social_support": "Moderate",
    "relationship_status": "Single",
    "substance_use": "Never",
    "counseling_service_use": "Never",
    "family_history": "No",
    "chronic_illness": "No",
    "financial_stress": 2,
    "extracurricular_involvement": "Moderate",
    "semester_credit_load": 18,
    "residence_type": "Off-Campus",
}


# ==================================================================
# STRESS LEVEL LABELS
# ==================================================================

STRESS_LEVEL_LABELS = {
    0: "Minimal",
    1: "Low",
    2: "Mild",
    3: "Moderate",
    4: "High",
    5: "Severe",
}


# ==================================================================
# FIELD METADATA
# ==================================================================

FIELD_METADATA = {

    "Age": {
        "type": "number",
        "label": "What is your age?",
        "min": 18,
        "max": 35,
    },

    "Course": {
        "type": "select",
        "label": "What is your course/major?",
        "options": [
            "Business",
            "Computer Science",
            "Engineering",
            "Law",
            "Medical",
            "Others",
        ],
    },

    "Gender": {
        "type": "select",
        "label": "What is your gender?",
        "options": [
            "Female",
            "Male",
        ],
    },

    "CGPA": {
        "type": "number",
        "label": "What is your current CGPA?",
        "min": 0,
        "max": 10,
    },

    "Depression_Score": {
        "type": "select",
        "label": (
            "Depressive Symptoms lately"
        ),
        "options": [0, 1, 2, 3, 4, 5],
    },

    "Anxiety_Score": {
        "type": "select",
        "label": (
            "Anxiety Symptoms lately"
        ),
        "options": [0, 1, 2, 3, 4, 5],
    },

    "Sleep_Quality": {
        "type": "select",
        "label": "How would you describe your sleep quality?",
        "options": [
            "Good",
            "Average",
            "Poor",
        ],
        "option_descriptions": {
            "Good": (
                "Consistently 7-9 hours, "
                "wake up feeling rested"
            ),
            "Average": (
                "Somewhat irregular, 5-7 hours, "
                "sometimes tired"
            ),
            "Poor": (
                "Under 5 hours or very disrupted, "
                "frequently exhausted"
            ),
        },
    },

    "Physical_Activity": {
        "type": "select",
        "label": "How physically active are you?",
        "options": [
            "High",
            "Moderate",
            "Low",
        ],
        "option_descriptions": {
            "High": "Exercise/sports 4+ times a week",
            "Moderate": "Exercise 1-3 times a week",
            "Low": "Rarely or never exercise",
        },
    },

    "Diet_Quality": {
        "type": "select",
        "label": "How would you describe your diet?",
        "options": [
            "Good",
            "Average",
            "Poor",
        ],
        "option_descriptions": {
            "Good": (
                "Regular balanced meals, "
                "home-cooked most of the time"
            ),
            "Average": (
                "Mixed - some balanced meals, "
                "some fast food/skipped meals"
            ),
            "Poor": (
                "Mostly fast food, instant meals, "
                "or frequently skipping meals"
            ),
        },
    },

    "Social_Support": {
        "type": "select",
        "label": (
            "How much social support do you feel you have?"
        ),
        "options": [
            "High",
            "Moderate",
            "Low",
        ],
        "option_descriptions": {
            "High": (
                "Close friends/family I can talk "
                "to regularly and rely on"
            ),
            "Moderate": (
                "A few people I can talk to, "
                "but not always available"
            ),
            "Low": (
                "Few or no people I feel "
                "comfortable turning to"
            ),
        },
    },

    "Relationship_Status": {
        "type": "select",
        "label": "What is your relationship status?",
        "options": [
            "Single",
            "In a Relationship",
            "Married",
        ],
    },

    "Substance_Use": {
        "type": "select",
        "label": (
            "How often do you use alcohol/substances?"
        ),
        "options": [
            "Never",
            "Occasionally",
            "Frequently",
        ],
    },

    "Counseling_Service_Use": {
        "type": "select",
        "label": (
            "How often do you use counseling services?"
        ),
        "options": [
            "Never",
            "Occasionally",
            "Frequently",
        ],
    },

    "Family_History": {
        "type": "select",
        "label": (
            "Is there a family history of "
            "mental health issues?"
        ),
        "options": [
            "No",
            "Yes",
        ],
    },

    "Chronic_Illness": {
        "type": "select",
        "label": "Do you have any chronic illness?",
        "options": [
            "No",
            "Yes",
        ],
    },

    "Financial_Stress": {
        "type": "select",
        "label": (
            "Financial Stress"
        ),
        "options": [0, 1, 2, 3, 4, 5],
    },

    "Extracurricular_Involvement": {
        "type": "select",
        "label": (
            "How involved are you in "
            "extracurricular activities?"
        ),
        "options": [
            "High",
            "Moderate",
            "Low",
        ],
        "option_descriptions": {
            "High": (
                "Active member of one or more "
                "clubs/teams, regular participation"
            ),
            "Moderate": (
                "Occasionally join events or activities"
            ),
            "Low": (
                "Rarely or never participate "
                "in extracurriculars"
            ),
        },
    },

    "Semester_Credit_Load": {
        "type": "number",
        "label": (
            "How many credits are you taking "
            "this semester?"
        ),
        "min": 15,
        "max": 29,
    },

    "Residence_Type": {
        "type": "select",
        "label": "Where do you currently live?",
        "options": [
            "On-Campus",
            "Off-Campus",
            "With Family",
        ],
    },
}


# ==================================================================
# LLM FIELD SCHEMA
# ==================================================================

FIELD_SCHEMA = {
    "type": "object",
    "properties": {
        "Age": {
            "type": ["integer", "null"],
            "minimum": 18,
            "maximum": 35,
        },

        "Course": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Course"]["options"] + [None],
        },

        "Gender": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Gender"]["options"] + [None],
        },

        "CGPA": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 10,
        },

        "Depression_Score": {
            "type": ["integer", "null"],
            "minimum": 0,
            "maximum": 5,
        },

        "Anxiety_Score": {
            "type": ["integer", "null"],
            "minimum": 0,
            "maximum": 5,
        },

        "Sleep_Quality": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Sleep_Quality"]["options"] + [None],
        },

        "Physical_Activity": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Physical_Activity"]["options"] + [None],
        },

        "Diet_Quality": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Diet_Quality"]["options"] + [None],
        },

        "Social_Support": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Social_Support"]["options"] + [None],
        },

        "Relationship_Status": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Relationship_Status"]["options"] + [None],
        },

        "Substance_Use": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Substance_Use"]["options"] + [None],
        },

        "Counseling_Service_Use": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Counseling_Service_Use"]["options"] + [None],
        },

        "Family_History": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Family_History"]["options"] + [None],
        },

        "Chronic_Illness": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA["Chronic_Illness"]["options"] + [None],
        },

        "Financial_Stress": {
            "type": ["integer", "null"],
            "minimum": 0,
            "maximum": 5,
        },

        "Extracurricular_Involvement": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA[
                "Extracurricular_Involvement"
            ]["options"] + [None],
        },

        "Semester_Credit_Load": {
            "type": ["integer", "null"],
            "minimum": 15,
            "maximum": 29,
        },

        "Residence_Type": {
            "type": ["string", "null"],
            "enum": FIELD_METADATA[
                "Residence_Type"
            ]["options"] + [None],
        },
    },

    "required": FIELD_ORDER,
}


# ==================================================================
# SYSTEM PROMPT
# ==================================================================

SYSTEM_PROMPT = """
You extract structured survey fields from a student's
free-text reflection about their life, mood, and habits.

Rules:

- Only fill a field if the text actually implies a value.
  If it is not mentioned or you are unsure, return null.
  Do not guess.

- Depression_Score, Anxiety_Score and Financial_Stress
  are self-report scales from 0 (none) to 5 (severe).
  Infer a score only when the student's description
  provides enough information.

- CGPA must be returned on the 0-10 scale.

  If the student mentions a CGPA on the 0-4 scale,
  convert it to the 0-10 scale.

  Example:
      3.4 / 4.0 → 8.5 / 10

  If the student gives a value above 4, assume it is
  already on the 0-10 scale.

- Do not infer sensitive information that was not stated.

- Return ONLY the JSON object.
"""


# ==================================================================
# ASSEMBLYAI KEY CHECK
# ==================================================================

def check_assemblyai_key() -> bool:
    """
    Check whether an AssemblyAI API key is available.
    """

    if not AAI_API_KEY:
        print("\nWARNING: ASSEMBLYAI_API_KEY is not set.")
        print(
            "Add it to your local .env file."
        )
        return False

    return True


# ==================================================================
# REAL-TIME TRANSCRIPTION
# ==================================================================

class RealtimeTranscriber:

    def __init__(
        self,
        on_transcript_callback: Optional[
            Callable[[str], None]
        ] = None,
    ):

        if websocket is None or pyaudio is None:
            raise ImportError(
                "Real-time transcription requires "
                "'websocket-client' and 'pyaudio'.\n"
                "Install them using:\n"
                "pip install websocket-client pyaudio"
            )

        self.ws = None
        self.on_transcript_callback = (
            on_transcript_callback
        )
        self.final_text = ""
        self.is_running = False
        self.audio_stream = None
        self.audio_thread = None

    def on_open(self, ws):

        print(
            "Connected to AssemblyAI real-time streaming"
        )

        print(
            "Speak now... "
            "(Press Ctrl+C to stop)"
        )

        self.is_running = True

        self.audio_thread = threading.Thread(
            target=self.stream_audio,
            daemon=True,
        )

        self.audio_thread.start()

    def on_message(self, ws, message):

        try:

            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "Begin":

                print(
                    f"Session ID: {data.get('id')}"
                )

            elif msg_type == "Turn":

                text = data.get(
                    "transcript",
                    "",
                )

                end_of_turn = data.get(
                    "end_of_turn",
                    False,
                )

                if text:

                    if end_of_turn:

                        print(
                            f"\nFinal: {text}"
                        )

                        self.final_text += (
                            " " + text
                        )

                        if self.on_transcript_callback:
                            self.on_transcript_callback(
                                text
                            )

                    else:

                        print(
                            f"\rPartial: {text}",
                            end="",
                            flush=True,
                        )

            elif msg_type == "Termination":

                print(
                    "\nSession terminated. "
                    f"Audio duration: "
                    f"{data.get('audio_duration_seconds', 0)}s"
                )

        except json.JSONDecodeError:
            pass

    def on_error(self, ws, error):

        print(
            f"\nAssemblyAI error: {error}"
        )

    def on_close(
        self,
        ws,
        close_code,
        close_msg,
    ):

        print(
            "\nTranscription stopped "
            f"(code={close_code}, "
            f"msg={close_msg})"
        )

        self.is_running = False

        if self.audio_stream:

            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception:
                pass

            self.audio_stream = None

    def stream_audio(self):

        try:

            audio = pyaudio.PyAudio()

            device_index = None

            for i in range(
                audio.get_device_count()
            ):

                device_info = (
                    audio.get_device_info_by_index(i)
                )

                if device_info.get(
                    "maxInputChannels",
                    0,
                ) > 0:

                    device_index = i
                    break

            if device_index is None:

                print(
                    "No microphone input device found."
                )

                return

            self.audio_stream = audio.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK_SIZE,
            )

            print(
                "Audio streaming started..."
            )

            while (
                self.is_running
                and self.ws
            ):

                try:

                    data = self.audio_stream.read(
                        CHUNK_SIZE,
                        exception_on_overflow=False,
                    )

                    self.ws.send(
                        data,
                        websocket.ABNF.OPCODE_BINARY,
                    )

                except Exception as e:

                    print(
                        f"Audio streaming error: {e}"
                    )

                    break

        except Exception as e:

            print(
                f"Failed to initialize audio: {e}"
            )

        finally:

            try:
                audio.terminate()
            except Exception:
                pass

    def start_transcription(self):

        if not check_assemblyai_key():

            raise ValueError(
                "ASSEMBLYAI_API_KEY is not configured."
            )

        ws_url = (
            "wss://streaming.assemblyai.com/v3/ws"
            f"?sample_rate={SAMPLE_RATE}"
            f"&encoding={ENCODING}"
            "&format_turns=true"
        )

        print(
            "Connecting to AssemblyAI..."
        )

        self.ws = websocket.WebSocketApp(
            ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            header={
                "Authorization": AAI_API_KEY
            },
        )

        self.ws.run_forever()

    def get_final_text(self) -> str:

        return self.final_text.strip()


# ==================================================================
# TRANSCRIPTION HELPERS
# ==================================================================

def transcribe_realtime(
    on_transcript_callback: Optional[
        Callable[[str], None]
    ] = None,
) -> str:

    transcriber = RealtimeTranscriber(
        on_transcript_callback
    )

    try:

        transcriber.start_transcription()

    except KeyboardInterrupt:

        print(
            "\nStopping... finishing "
            "your last sentence."
        )

        transcriber.is_running = False

        deadline = time.time() + 2.0

        last_len = len(
            transcriber.final_text
        )

        while time.time() < deadline:

            time.sleep(0.2)

            if len(
                transcriber.final_text
            ) != last_len:

                break

        if transcriber.ws:
            transcriber.ws.close()

    return transcriber.get_final_text()


def transcribe_audio_file(
    file_path: str,
) -> str:

    if aai is None:

        raise ImportError(
            "Audio file transcription requires "
            "the 'assemblyai' package.\n"
            "Install it using:\n"
            "pip install assemblyai"
        )

    if not os.path.exists(file_path):

        raise FileNotFoundError(
            f"Audio file not found: {file_path}"
        )

    if not check_assemblyai_key():

        raise ValueError(
            "ASSEMBLYAI_API_KEY is not configured."
        )

    print(
        f"Transcribing audio file: {file_path}"
    )

    config = aai.TranscriptionConfig(
        language_code="en",
        speech_model=aai.SpeechModel.best,
        punctuate=True,
        format_text=True,
    )

    transcriber = aai.Transcriber(
        config=config
    )

    transcript = transcriber.transcribe(
        file_path
    )

    if (
        transcript.status
        == aai.TranscriptStatus.error
    ):

        raise RuntimeError(
            f"Transcription failed: "
            f"{transcript.error}"
        )

    text = transcript.text or ""

    print(
        f"Transcription complete: "
        f"{len(text)} characters"
    )

    return text


# ==================================================================
# CGPA NORMALIZATION
# ==================================================================

def normalize_cgpa_to_model_scale(
    cgpa_10: Optional[float],
) -> Optional[float]:

    """
    Convert CGPA from the user-facing 0-10 scale
    to the model's original 0-4 scale.
    """

    if cgpa_10 is None:
        return None

    if cgpa_10 > 4.0:

        return round(
            cgpa_10 * (4.0 / 10.0),
            2,
        )

    return float(cgpa_10)


# ==================================================================
# LLM SCORE EXTRACTION
# ==================================================================

FREE_TEXT_SCORE_FIELDS = {
    "Depression_Score",
    "Anxiety_Score",
    "Financial_Stress",
}


def llm_score_from_text(
    field_name: str,
    user_text: str,
) -> dict:

    readable = (
        field_name
        .replace("_", " ")
        .lower()
    )

    prompt = f"""
A student described their {readable}
in their own words.

Student description:
"{user_text}"

Convert this into a score from 0 to 5.

Scoring guide:

0 = none, no issue
1 = very mild
2 = mild
3 = moderate
4 = high
5 = severe

Return ONLY valid JSON:

{{
    "score": <integer 0-5>,
    "reason": "<one short sentence>"
}}
"""

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "format": {
                    "type": "object",
                    "properties": {
                        "score": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 5,
                        },
                        "reason": {
                            "type": "string"
                        },
                    },
                    "required": [
                        "score",
                        "reason",
                    ],
                },
                "options": {
                    "temperature": 0
                },
                "stream": False,
            },
            timeout=30,
        )

        response.raise_for_status()

        result = json.loads(
            response.json()["message"]["content"]
        )

        score = int(result["score"])

        if not 0 <= score <= 5:
            raise ValueError(
                "LLM returned an invalid score."
            )

        return result

    except Exception as e:

        print(
            "Could not process text with Ollama. "
            f"Error: {e}"
        )

        return {
            "score": 2,
            "reason": "Neutral fallback value used.",
        }


# ==================================================================
# FIELD EXTRACTION
# ==================================================================

def extract_fields(
    text: str,
) -> dict:

    if not text or not text.strip():

        raise ValueError(
            "No text was provided for extraction."
        )

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": text,
                    },
                ],
                "format": FIELD_SCHEMA,
                "options": {
                    "temperature": 0,
                    "num_gpu": -1,
                    "num_ctx": 2048,
                },
                "keep_alive": 0,
                "stream": False,
            },
            timeout=100,
        )

        response.raise_for_status()

        content = response.json()[
            "message"
        ]["content"]

        fields = json.loads(content)

        return fields

    except requests.exceptions.ConnectionError:

        raise ConnectionError(
            "Could not connect to Ollama.\n"
            "Make sure Ollama is running and "
            f"'{OLLAMA_MODEL}' is installed."
        )

    except requests.exceptions.Timeout:

        raise TimeoutError(
            "Ollama took too long to respond. "
            "Try again or use a smaller model."
        )

    except Exception as e:

        print(
            f"Field extraction error: {e}"
        )

        raise


# ==================================================================
# MISSING FIELD HANDLING
# ==================================================================

def get_missing_fields(
    fields: dict,
) -> List[dict]:

    return [
        {
            "field": name,
            **FIELD_METADATA[name],
        }
        for name in FIELD_ORDER
        if fields.get(name) is None
    ]


def check_extraction_quality(
    fields: dict,
) -> bool:

    missing_count = sum(
        1
        for name in FIELD_ORDER
        if fields.get(name) is None
    )

    missing_ratio = (
        missing_count / len(FIELD_ORDER)
    )

    if (
        missing_ratio
        > MISSING_WARNING_THRESHOLD
    ):

        print(
            f"\nWarning: Only "
            f"{len(FIELD_ORDER) - missing_count}/"
            f"{len(FIELD_ORDER)} fields were "
            "extracted from the reflection."
        )

        return False

    return True


# ==================================================================
# CLI FOLLOW-UP QUESTIONS
# ==================================================================

def ask_missing_fields_cli(
    missing: list,
) -> dict:

    answers = {}

    if not missing:
        return answers

    print(
        f"\n{len(missing)} field(s) "
        "could not be extracted."
    )

    print(
        "Press Enter to skip any question "
        "you would rather not answer.\n"
    )

    for m in missing:

        field_name = m["field"]

        descriptions = m.get(
            "option_descriptions",
            {},
        )

        # ----------------------------------------------------------
        # SCORE FIELDS
        # ----------------------------------------------------------

        if (
            field_name
            in FREE_TEXT_SCORE_FIELDS
        ):

            print(
                f"--- {field_name.replace('_', ' ')} ---"
            )

            print(
                "Describe how you've been feeling "
                "in your own words."
            )

            raw = input(
                "Your description "
                "(or Enter to skip): "
            ).strip()

            if raw == "":

                answers[field_name] = None
                continue

            result = llm_score_from_text(
                field_name,
                raw,
            )

            answers[field_name] = (
                result["score"]
            )

            print(
                f"Recorded as "
                f"{result['score']}/5.\n"
            )

            continue

        # ----------------------------------------------------------
        # SELECT FIELDS
        # ----------------------------------------------------------

        if m["type"] == "select":

            while True:

                print(m["label"])

                for option in m["options"]:

                    hint = ""

                    if option in descriptions:

                        hint = (
                            f" - "
                            f"{descriptions[option]}"
                        )

                    print(
                        f"  {option}{hint}"
                    )

                raw = input(
                    "Your choice "
                    "(or Enter to skip): "
                ).strip()

                if raw == "":

                    answers[field_name] = None
                    break

                match = next(
                    (
                        option
                        for option in m["options"]
                        if str(option).lower()
                        == raw.lower()
                    ),
                    None,
                )

                if match is not None:

                    answers[field_name] = match
                    break

                print(
                    "Invalid option. Please "
                    "choose one of the listed options.\n"
                )

        # ----------------------------------------------------------
        # NUMBER FIELDS
        # ----------------------------------------------------------

        else:

            allow_decimal = (
                field_name == "CGPA"
            )

            while True:

                raw = input(
                    f"{m['label']} "
                    f"({m['min']}-{m['max']}, "
                    "or Enter to skip): "
                ).strip()

                if raw == "":

                    answers[field_name] = None
                    break

                try:

                    if allow_decimal:

                        value = float(raw)

                    else:

                        value = int(
                            float(raw)
                        )

                except ValueError:

                    print(
                        "Please enter a valid number."
                    )

                    continue

                if not (
                    m["min"]
                    <= value
                    <= m["max"]
                ):

                    print(
                        f"Value must be between "
                        f"{m['min']} and {m['max']}."
                    )

                    continue

                answers[field_name] = value
                break

    return answers


# ==================================================================
# MODEL INPUT
# ==================================================================

def to_model_input(
    fields: dict,
) -> pd.DataFrame:

    return pd.DataFrame(
        [
            {
                name: fields.get(name)
                for name in FIELD_ORDER
            }
        ]
    )


# ==================================================================
# STRESS PREDICTION
# ==================================================================

def predict_stress(
    model: Any,
    fields: Dict[str, Any],
) -> Dict[str, Any]:

    row = {}

    for (
        extraction_name,
        model_col,
    ) in FIELD_NAME_MAP.items():

        value = fields.get(
            extraction_name
        )

        if value is None:

            value = DEFAULT_VALUES[
                model_col
            ]

        if model_col == "cgpa":

            value = (
                normalize_cgpa_to_model_scale(
                    value
                )
            )

        row[model_col] = value

    X_new = pd.DataFrame([row])

    # Respect the exact feature ordering used
    # when the model was trained.
    if hasattr(
        model,
        "feature_names_in_",
    ):

        X_new = X_new[
            model.feature_names_in_
        ]

    prediction = int(
        model.predict(X_new)[0]
    )

    result = {
        "stress_level": prediction,

        "stress_label": STRESS_LEVEL_LABELS.get(
            prediction,
            str(prediction),
        ),

        "input_row": row,
    }

    if hasattr(
        model,
        "predict_proba",
    ):

        proba = model.predict_proba(
            X_new
        )[0]

        result["probabilities"] = {
            STRESS_LEVEL_LABELS.get(
                index,
                f"Class {index}",
            ): float(probability)

            for index, probability
            in enumerate(proba)
        }

        result["confidence"] = (
            float(np.max(proba) * 100)
        )

    return result


# ==================================================================
# RESULT DISPLAY
# ==================================================================

def print_results(
    result: dict,
    fields: dict,
) -> None:

    print("\nFinal extracted fields:")
    print(
        to_model_input(fields).T
    )

    print("\n" + "=" * 50)

    print(
        "PREDICTED STRESS LEVEL: "
        f"{result['stress_label']} "
        f"({result['stress_level']} / 5)"
    )

    print("=" * 50)

    if "probabilities" in result:

        print(
            "\nPredicted probability by class:"
        )

        sorted_probs = sorted(
            result["probabilities"].items(),
            key=lambda x: -x[1],
        )

        for cls, probability in sorted_probs:

            bar_length = int(
                probability * 40
            )

            bar = (
                "█" * bar_length
                + "░" * (
                    40 - bar_length
                )
            )

            print(
                f"  {cls:<10} "
                f"{bar} "
                f"{probability * 100:5.1f}%"
            )

        print(
            f"\nHighest predicted probability: "
            f"{result['confidence']:.1f}%"
        )


# ==================================================================
# OPTIONAL CLI INPUT
# ==================================================================

def get_user_text() -> str:

    print("\nChoose input method:")

    print(
        "1. Real-time microphone "
        "transcription"
    )

    print(
        "2. Audio file transcription"
    )

    print(
        "3. Text input"
    )

    choice = input(
        "\nSelect an option (1-3): "
    ).strip()

    # --------------------------------------------------------------
    # REAL-TIME AUDIO
    # --------------------------------------------------------------

    if choice == "1":

        if not check_assemblyai_key():

            return ""

        print(
            "\nStarting real-time transcription..."
        )

        return transcribe_realtime()

    # --------------------------------------------------------------
    # AUDIO FILE
    # --------------------------------------------------------------

    if choice == "2":

        if not check_assemblyai_key():

            return ""

        audio_path = input(
            "Enter audio file path: "
        ).strip()

        if not audio_path:

            raise ValueError(
                "No audio file path provided."
            )

        return transcribe_audio_file(
            audio_path
        )

    # --------------------------------------------------------------
    # TEXT
    # --------------------------------------------------------------

    if choice == "3":

        text = input(
            "\nEnter your reflection:\n"
        ).strip()

        if not text:

            raise ValueError(
                "No text was provided."
            )

        return text

    raise ValueError(
        "Invalid choice. Please select 1, 2, or 3."
    )


# ==================================================================
# OPTIONAL CLI MAIN
# ==================================================================

def main():

    print("=" * 60)
    print(
        "MIND SENSE - Mental Health Assessment"
    )
    print("=" * 60)

    try:

        # ----------------------------------------------------------
        # INPUT
        # ----------------------------------------------------------

        text = get_user_text()

        if not text:

            print(
                "\nNo text was captured."
            )

            return

        print(
            f"\nInput text:\n{text}\n"
        )

        # ----------------------------------------------------------
        # FIELD EXTRACTION
        # ----------------------------------------------------------

        print(
            "Extracting survey fields "
            "using Ollama..."
        )

        fields = extract_fields(text)

        check_extraction_quality(
            fields
        )

        # ----------------------------------------------------------
        # MISSING FIELDS
        # ----------------------------------------------------------

        missing = get_missing_fields(
            fields
        )

        if missing:

            answers = ask_missing_fields_cli(
                missing
            )

            fields.update(answers)

        # ----------------------------------------------------------
        # MODEL
        # ----------------------------------------------------------

        print(
            "\nLoading stress prediction model..."
        )

        stress_model = load_stress_model(
            STRESS_MODEL_PATH
        )

        print(
            "Predicting stress level..."
        )

        result = predict_stress(
            stress_model,
            fields,
        )

        # ----------------------------------------------------------
        # RESULTS
        # ----------------------------------------------------------

        print_results(
            result,
            fields,
        )

        print(
            "\nMindSense provides a "
            "non-clinical risk assessment "
            "and is not a medical diagnosis."
        )

    except KeyboardInterrupt:

        print(
            "\n\nProcess interrupted."
        )

    except Exception as e:

        print(
            f"\nError: {e}"
        )

        print(
            "\nTroubleshooting:"
        )

        print(
            "  1. Make sure Ollama is running."
        )

        print(
            f"  2. Verify {OLLAMA_MODEL} "
            "is installed."
        )

        print(
            "  3. Check ASSEMBLYAI_API_KEY "
            "in .env if using audio."
        )

        print(
            "  4. Verify the trained model exists at:"
        )

        print(
            f"     {STRESS_MODEL_PATH}"
        )


# ==================================================================
# SCRIPT ENTRY POINT
# ==================================================================

if __name__ == "__main__":
    main()