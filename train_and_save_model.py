"""Train HGB + Context model on full Sleep-Accel data and save artifacts for web MVP."""
import json
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = (
    BASE_DIR.parent / "01_code_open_source_package"
    / "data" / "processed" / "all_subjects_epoch_features_context.csv"
)
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

BASE_FEATURES = [
    "acc_mean", "acc_std", "acc_min", "acc_max",
    "hr_mean", "hr_std", "hr_min", "hr_max",
    "steps_sum",
]

CONTEXT_FEATURES = []
for feat in BASE_FEATURES:
    CONTEXT_FEATURES.extend([
        feat, f"{feat}_prev1", f"{feat}_prev2",
        f"{feat}_next1", f"{feat}_next2",
    ])

CLASS_NAMES = {0: "Wake", 1: "NREM", 2: "REM"}

def main():
    print("Loading context feature table...")
    df = pd.read_csv(DATA_PATH)
    print(f"  Shape: {df.shape}")

    X = df[CONTEXT_FEATURES].copy()
    y = df["y"].astype(int).values

    print(f"\nClass distribution:")
    for cls, name in CLASS_NAMES.items():
        print(f"  {name}: {(y == cls).sum()}")

    # Train on full dataset
    print("\nTraining HGB + Context on full dataset...")
    model = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=200,
        max_depth=6,
        min_samples_leaf=20,
        random_state=42,
    )
    sample_weight = compute_sample_weight(class_weight="balanced", y=y)
    model.fit(X, y, sample_weight=sample_weight)

    train_acc = model.score(X, y)
    print(f"  Training accuracy: {train_acc:.4f}")

    # Save model
    model_path = MODEL_DIR / "hgb_context_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    print(f"\nSaved model to: {model_path}")

    # Save feature schema
    schema = {
        "base_features": BASE_FEATURES,
        "context_features": CONTEXT_FEATURES,
        "n_features": len(CONTEXT_FEATURES),
        "class_names": CLASS_NAMES,
    }
    schema_path = MODEL_DIR / "feature_schema.json"
    with open(schema_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    print(f"Saved schema to: {schema_path}")

    # Compute SHAP explainer on a balanced subset
    print("\nComputing SHAP explainer...")
    rng = np.random.RandomState(42)
    indices = []
    for cls in [0, 1, 2]:
        cls_idx = np.where(y == cls)[0]
        n_sample = min(200, len(cls_idx))
        indices.extend(rng.choice(cls_idx, size=n_sample, replace=False))
    X_sample = X.iloc[indices]
    print(f"  Background sample: {X_sample.shape[0]} rows")

    explainer = shap.TreeExplainer(model, X_sample)
    shap_path = MODEL_DIR / "shap_explainer.pkl"
    with open(shap_path, "wb") as f:
        pickle.dump(explainer, f)
    print(f"Saved SHAP explainer to: {shap_path}")

    # Save global SHAP values for pre-computed feature importance
    shap_values = explainer.shap_values(X_sample, check_additivity=False)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]  # class 1 for multi-class

    global_importance = pd.DataFrame({
        "feature": CONTEXT_FEATURES,
        "importance": np.abs(shap_values).mean(axis=0),
    }).sort_values("importance", ascending=False)

    importance_path = MODEL_DIR / "global_shap_importance.csv"
    global_importance.to_csv(importance_path, index=False)
    print(f"Saved SHAP importance to: {importance_path}")

    print("\nDone! All artifacts saved to models/")
    print(f"  - hgb_context_model.pkl")
    print(f"  - feature_schema.json")
    print(f"  - shap_explainer.pkl")
    print(f"  - global_shap_importance.csv")

if __name__ == "__main__":
    main()
