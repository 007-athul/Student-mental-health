from pathlib import Path
import pandas as pd

# PROJECT PATH

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"

# DATASET PATHS

MAIN_DATASET = (
    RAW_DATA_DIR /
    "students_mental_health_synthetic_v2.csv"
)

SURVEY_DATASET = (
    RAW_DATA_DIR /
    "collecteddata.csv"
)


def load_main_data():
    if not MAIN_DATASET.exists():
        raise FileNotFoundError(
            f"Main dataset not found:\n{MAIN_DATASET}"
        )

    df = pd.read_csv(
        MAIN_DATASET
    )

    return df


# LOAD PRIMARY SURVEY


def load_survey_data():
    if not SURVEY_DATASET.exists():
        raise FileNotFoundError(
            f"Survey dataset not found:\n{SURVEY_DATASET}"
        )

    # cp1252 handles Windows-encoded CSV files
    try:

        df = pd.read_csv(
            SURVEY_DATASET,
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        df = pd.read_csv(
            SURVEY_DATASET,
            encoding="cp1252"
        )

    return df