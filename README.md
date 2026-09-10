# MindSense

A data-science project for screening student wellbeing risk from academic
and lifestyle survey data, with an interactive Streamlit dashboard.

MindSense is an exploratory screening tool, not a clinical diagnosis.
High-risk flags should always be followed up by qualified counselling and
academic support staff.

## Features

- **Overview / Patterns / Data tabs** - cohort-level dashboards over the raw
  survey dataset (stress, anxiety, depression, sleep, academic load, etc).
- **Risk intake tab** - fill in a student's profile and get a rule-based
  composite risk score (0-100), risk level, and recommendation
  (`src/risk_analysis.py`).
- **AI intake tab** - type or upload a short audio reflection; MindSense
  extracts structured survey fields with a local LLM, predicts a calibrated
  `Stress_Level` (0-5) with a trained scikit-learn model, folds that into the
  rule-based risk score, and (optionally) generates a supportive,
  non-clinical recommendation with Gemini.
- **CLI (`main.py`)** - the same voice/text -> extraction -> prediction ->
  recommendation pipeline from the command line, including real-time
  microphone transcription.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your own API keys
```

`requirements.txt` pins `scikit-learn==1.5.1` - the calibrated stress model
in `models/calibrated_stress_model.pkl` was trained with that version and
may fail to unpickle with a different one (see `models/README.md`).

### Optional integrations

| Feature | Requirement |
|---|---|
| AI wellbeing recommendations | `GEMINI_API_KEY` in `.env` (Gemini API) |
| Audio transcription (file upload or CLI) | `ASSEMBLYAI_API_KEY` in `.env`, `pip install assemblyai` |
| Real-time microphone transcription (CLI only) | AssemblyAI key + `pip install websocket-client pyaudio` |
| Local field extraction from free text | [Ollama](https://ollama.com/download) running locally with a model pulled (default `llama3.1:8b`) |

Every integration above degrades gracefully: the app still runs and the
other tabs still work if a given key or package isn't configured.

## Running the dashboard

```bash
streamlit run app/streamlit_app.py
```

## Running the CLI

```bash
python main.py
```

## Project layout

```
app/                Streamlit dashboard
src/                Shared logic: data loading/cleaning, risk scoring,
                    voice/text intake, ML model helpers, AI recommendations
models/             Trained model artifacts
data/               Raw and processed datasets
notebooks/          EDA / preprocessing / statistical analysis scripts
outputs/            Saved figures and reports
main.py             CLI entry point
```
