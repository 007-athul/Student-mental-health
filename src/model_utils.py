"""Shared ML model helpers for MindSense's calibrated stress-level model.

`models/calibrated_stress_model.pkl` wraps a scikit-learn pipeline in a
``TemperatureScaledModel`` that rescales predicted-class probabilities
("confidence") without changing the predicted class itself.

Two practical gotchas are handled here so the rest of the app doesn't have
to think about them:

1. The model was pickled while ``TemperatureScaledModel`` lived in a
   standalone script running as ``__main__``, so pickle looks the class up
   as ``__main__.TemperatureScaledModel`` at load time. ``load_stress_model``
   installs a small compatibility shim so the file can be unpickled no
   matter which module is actually running as ``__main__`` (Streamlit,
   ``main.py``, a notebook, etc.).
2. The pipeline was trained with scikit-learn 1.5.x. Loading it with a
   different scikit-learn version can raise ``AttributeError`` for internal
   classes (e.g. ``ColumnTransformer``'s ``_RemainderColsList``). Pin
   ``scikit-learn==1.5.1`` in your environment (see requirements.txt) to
   avoid this - `load_stress_model` re-raises with a clearer message if it
   detects this situation.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class TemperatureScaledModel:
    """Wrapper for sklearn models that applies temperature scaling to probabilities.

    Predicted classes are unchanged; only the confidence scores are calibrated.
    """

    def __init__(self, base_model, temperature: float = 1.0):
        self.base_model = base_model
        self.temperature = temperature
        self.classes_ = base_model.classes_
        if hasattr(base_model, "feature_names_in_"):
            self.feature_names_in_ = base_model.feature_names_in_

    def _select_columns(self, X):
        if isinstance(X, dict):
            X = pd.DataFrame([X])
        if isinstance(X, pd.DataFrame) and hasattr(self, "feature_names_in_"):
            if all(col in X.columns for col in self.feature_names_in_):
                X = X[self.feature_names_in_]
        return X

    def predict(self, X):
        X = self._select_columns(X)
        return self.base_model.predict(X)

    def predict_proba(self, X):
        X = self._select_columns(X)

        X_transformed = self.base_model.named_steps["prep"].transform(X)
        model = self.base_model.named_steps["model"]

        if hasattr(model, "decision_function"):
            logits = model.decision_function(X_transformed)
            if len(logits.shape) == 1:
                logits = np.column_stack([-logits, logits])
        else:
            probs = model.predict_proba(X_transformed)
            logits = np.log(probs + 1e-10)

        scaled_logits = logits / self.temperature
        exp_logits = np.exp(scaled_logits - np.max(scaled_logits, axis=1, keepdims=True))
        return exp_logits / np.sum(exp_logits, axis=1, keepdims=True)


def _install_unpickle_shim() -> None:
    """Make TemperatureScaledModel resolvable as __main__.TemperatureScaledModel."""
    main_module = sys.modules.get("__main__")
    if main_module is not None and not hasattr(main_module, "TemperatureScaledModel"):
        main_module.TemperatureScaledModel = TemperatureScaledModel


def load_stress_model(path: str | Path) -> Any:
    """Load the calibrated stress-level model, handling the __main__ shim.

    Raises FileNotFoundError if the path doesn't exist, and a clearer
    RuntimeError (chained from the original AttributeError) if the model
    appears to have been pickled with an incompatible scikit-learn version.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    _install_unpickle_shim()

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except AttributeError as e:
        raise RuntimeError(
            "Could not unpickle the calibrated stress model. This usually means "
            "the installed scikit-learn version doesn't match the version used "
            "to train it. Try `pip install scikit-learn==1.5.1` (see "
            f"requirements.txt) and retry. Original error: {e}"
        ) from e
