"""Build ±2 context features from base 9-feature epoch table."""
import pandas as pd

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


def build_context_features(df: pd.DataFrame) -> pd.DataFrame:
    """Expand base features into ±2 context representation.

    Args:
        df: DataFrame with at minimum the 9 BASE_FEATURES columns.
            If 'subject_id' column exists, context windows are built per-subject.
            If 't' column exists, it is used for sorting.

    Returns:
        DataFrame with 45 context feature columns (after dropping boundary rows).
    """
    df = df.copy()

    # Ensure all base features are numeric
    for feat in BASE_FEATURES:
        if feat in df.columns:
            df[feat] = pd.to_numeric(df[feat], errors="coerce")

    # Drop rows with NaN in base features
    before = len(df)
    df = df.dropna(subset=BASE_FEATURES)
    if len(df) < before:
        print(f"  Dropped {before - len(df)} rows with NaN base features")

    # Sort: by subject if available, then by time
    if "subject_id" in df.columns:
        if "t" in df.columns:
            df = df.sort_values(["subject_id", "t"]).reset_index(drop=True)
        else:
            df = df.sort_values("subject_id").reset_index(drop=True)
    elif "t" in df.columns:
        df = df.sort_values("t").reset_index(drop=True)

    # Build context features
    group_col = "subject_id" if "subject_id" in df.columns else None

    for feat in BASE_FEATURES:
        if group_col:
            df[f"{feat}_prev1"] = df.groupby(group_col)[feat].shift(1)
            df[f"{feat}_prev2"] = df.groupby(group_col)[feat].shift(2)
            df[f"{feat}_next1"] = df.groupby(group_col)[feat].shift(-1)
            df[f"{feat}_next2"] = df.groupby(group_col)[feat].shift(-2)
        else:
            df[f"{feat}_prev1"] = df[feat].shift(1)
            df[f"{feat}_prev2"] = df[feat].shift(2)
            df[f"{feat}_next1"] = df[feat].shift(-1)
            df[f"{feat}_next2"] = df[feat].shift(-2)

    before_drop = len(df)
    df = df.dropna(subset=CONTEXT_FEATURES).copy()

    return df
