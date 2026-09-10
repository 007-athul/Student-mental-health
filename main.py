"""MindSense CLI: speak or type a free-text reflection, extract survey
fields with a local LLM (Ollama), predict a calibrated Stress_Level, compute
the rule-based wellbeing risk score, and (optionally) get a Gemini-generated
supportive recommendation.

Usage:
    python main.py

See README.md for setup (Ollama, AssemblyAI key, Gemini key).
"""

from __future__ import annotations

from src.model_utils import load_stress_model
from src.risk_analysis import calculate_student_risk, save_student_submission
from src.voice_intake import (
    STRESS_MODEL_PATH,
    ask_missing_fields_cli,
    check_assemblyai_key,
    check_extraction_quality,
    extract_fields,
    get_missing_fields,
    predict_stress,
    print_results,
    transcribe_audio_file,
    transcribe_realtime,
)

try:
    from src.ai_recommendation import generate_recommendation
except ImportError:
    generate_recommendation = None


def print_ai_recommendation(recommendation: dict) -> None:
    print("\n" + "=" * 40)
    print("AI WELLBEING RECOMMENDATION")
    print("=" * 40)
    print(f"\n{recommendation.get('summary', '')}")

    priority_areas = recommendation.get("priority_areas") or []
    if priority_areas:
        print("\nPriority areas:")
        for area in priority_areas:
            print(f"  - {area}")

    recommendations = recommendation.get("recommendations") or []
    if recommendations:
        print("\nRecommendations:")
        for item in recommendations:
            print(f"  [{item.get('area', '')}]")
            print(f"    Problem: {item.get('problem', '')}")
            print(f"    Action:  {item.get('action', '')}")

    if recommendation.get("student_message"):
        print(f"\nMessage for you: {recommendation['student_message']}")

    if recommendation.get("professional_support"):
        print(f"\nWhen to seek professional support: {recommendation['professional_support']}")

    if recommendation.get("error"):
        print(f"\n(Note: AI recommendation fell back to a default response - {recommendation['error']})")


def main() -> None:
    print("=" * 60)
    print("MIND SENSE - Mental Health Assessment")
    print("=" * 60)

    has_key = check_assemblyai_key()

    print("\nChoose input method:")
    print("1. Real-time microphone transcription (AssemblyAI)")
    print("2. Audio file transcription (AssemblyAI)")
    print("3. Text input (manual)")

    choice = input("\nSelect an option (1-3): ").strip()

    try:
        if choice == "1":
            if not has_key:
                print("\nCannot use real-time transcription without an AssemblyAI API key.")
                print("Set ASSEMBLYAI_API_KEY in your .env file and try again.")
                return

            print("\nStarting real-time transcription...")
            print("Speak clearly about your mental health, lifestyle, and stress levels.")
            print("Press Ctrl+C when you're done speaking.\n")

            text = transcribe_realtime()

        elif choice == "2":
            if not has_key:
                print("\nCannot use audio file transcription without an AssemblyAI API key.")
                print("Set ASSEMBLYAI_API_KEY in your .env file and try again.")
                return

            audio_path = input("Enter path to audio file: ").strip()
            if not audio_path:
                raise ValueError("No file path provided")
            text = transcribe_audio_file(audio_path)

        elif choice == "3":
            text = input("\nEnter your text description: ").strip()
            if not text:
                raise ValueError("No text provided")

        else:
            raise ValueError("Invalid choice. Please select 1, 2, or 3.")

        if not text:
            print("\nNo text was captured. Please try again.")
            return

        print(f"\nTranscribed/Input text:\n{text}\n")

        print("Extracting survey fields from text...")
        fields = extract_fields(text)

        check_extraction_quality(fields)

        missing = get_missing_fields(fields)
        if missing:
            answers = ask_missing_fields_cli(missing)
            fields.update(answers)

        print("\nLoading stress prediction model...")
        stress_model = load_stress_model(STRESS_MODEL_PATH)

        print("Predicting stress level...")
        result = predict_stress(stress_model, fields)

        print_results(result, fields)

        # Fold the ML prediction into the rule-based risk profile and log it.
        student_payload = {v: fields.get(k) for k, v in _field_name_map().items()}
        student_payload["stress_level"] = result["stress_level"]

        risk = calculate_student_risk(student_payload)
        save_student_submission(student_payload)

        print("\n" + "=" * 40)
        print(f"OVERALL RISK: {risk['level']} ({risk['score']} / 100)")
        print("=" * 40)
        print(risk["recommendation"])

        if generate_recommendation is not None:
            print("\nGenerating AI wellbeing recommendation...")
            recommendation = generate_recommendation(student_payload, risk["score"], risk["level"])
            print_ai_recommendation(recommendation)

    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user.")
    except FileNotFoundError as e:
        print(f"\nFile error: {e}")
        print("Check that the file path is correct.")
    except ValueError as e:
        print(f"\nInput error: {e}")
    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure Ollama is running: ollama serve")
        print("  2. Verify you have the configured Ollama model pulled (see .env)")
        print("  3. Check ASSEMBLYAI_API_KEY / GEMINI_API_KEY are set correctly in .env")
        print("  4. Ensure the stress model file exists: models/calibrated_stress_model.pkl")
        print("  5. For real-time transcription: check microphone permissions")


def _field_name_map() -> dict:
    from src.voice_intake import FIELD_NAME_MAP

    return FIELD_NAME_MAP


if __name__ == "__main__":
    main()
