"""Load model and predict sleep stages."""
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"


def load_model():
    """Load trained HGB model with numpy version compatibility."""
    class _DummyRandomState:
        """Dummy to replace incompatible numpy random state during unpickling."""
        def __init__(self, *args, **kwargs):
            pass

    class SafeUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            if 'numpy.random' in module:
                return _DummyRandomState
            return super().find_class(module, name)

    with open(MODEL_DIR / "hgb_context_model.pkl", "rb") as f:
        try:
            model = pickle.load(f)
        except Exception:
            f.seek(0)
            model = SafeUnpickler(f).load()
    return model


def load_schema():
    """Load feature schema."""
    import json
    with open(MODEL_DIR / "feature_schema.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_explainer():
    """Load pre-computed SHAP explainer."""
    try:
        with open(MODEL_DIR / "shap_explainer.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None


def predict(df_context: pd.DataFrame) -> pd.DataFrame:
    """Run sleep stage prediction on context features.

    Args:
        df_context: DataFrame with 45 context feature columns

    Returns:
        DataFrame with columns: predicted_label, predicted_stage,
            prob_Wake, prob_NREM, prob_REM
    """
    schema = load_schema()
    model = load_model()

    X = df_context[schema["context_features"]].copy()

    pred_labels = model.predict(X)
    pred_proba = model.predict_proba(X)

    results = pd.DataFrame({
        "predicted_label": pred_labels,
        "predicted_stage": [schema["class_names"][str(l)] for l in pred_labels],
        "prob_Wake": pred_proba[:, 0],
        "prob_NREM": pred_proba[:, 1],
        "prob_REM": pred_proba[:, 2],
    })

    # Merge with original metadata if available
    meta_cols = [c for c in ["t", "subject_id", "stage_raw", "y"] if c in df_context.columns]
    if meta_cols:
        results = pd.concat([df_context[meta_cols].reset_index(drop=True), results], axis=1)

    return results
