# Models

## `calibrated_stress_model.pkl`

A scikit-learn pipeline (preprocessing + classifier) wrapped in a
`TemperatureScaledModel` that predicts `Stress_Level` (an integer 0-5) from
the same survey fields collected elsewhere in MindSense, plus a
temperature-calibrated confidence score per class.

- **Loading it:** always use `src.model_utils.load_stress_model(path)`
  rather than `pickle.load` directly - it installs a small compatibility
  shim so the pickled `__main__.TemperatureScaledModel` reference resolves
  correctly regardless of which script is running.
- **scikit-learn version:** trained/pickled with **scikit-learn 1.5.1**.
  Loading it with a different scikit-learn version can raise
  `AttributeError: Can't get attribute '_RemainderColsList'` (or similar)
  from `ColumnTransformer`. Install the pinned version from
  `requirements.txt` (`pip install scikit-learn==1.5.1`) if you hit this.
- **Input columns:** the model expects a single-row DataFrame with the
  snake_case column names used across MindSense (`age`, `course`, `gender`,
  `cgpa`, `depression_score`, `anxiety_score`, `sleep_quality`,
  `physical_activity`, `diet_quality`, `social_support`,
  `relationship_status`, `substance_use`, `counseling_service_use`,
  `family_history`, `chronic_illness`, `financial_stress`,
  `extracurricular_involvement`, `semester_credit_load`, `residence_type`).
  See `src/voice_intake.py::predict_stress` for the exact mapping and
  fallback defaults for missing fields.
