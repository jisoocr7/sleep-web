"""Strict Raw Epoch CSV validation and deterministic model inference."""

from __future__ import annotations

import hashlib
import io
import json
import pickle
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .errors import SafeWebError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_RECORDING_SECONDS = 24 * 60 * 60

BASE_FEATURES = [
    "acc_mean",
    "acc_std",
    "acc_min",
    "acc_max",
    "hr_mean",
    "hr_std",
    "hr_min",
    "hr_max",
    "steps_sum",
]
OPTIONAL_COLUMNS = ["t", "timestamp", "subject_id"]


@lru_cache(maxsize=1)
def load_schema() -> dict:
    with (MODEL_DIR / "feature_schema.json").open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    if schema.get("base_features") != BASE_FEATURES:
        raise RuntimeError("Model schema does not match the safe Raw Epoch contract")
    return schema


@lru_cache(maxsize=1)
def load_model():
    with (MODEL_DIR / "hgb_context_model.pkl").open("rb") as handle:
        return pickle.load(handle)


@lru_cache(maxsize=1)
def model_id() -> str:
    digest = hashlib.sha256((MODEL_DIR / "hgb_context_model.pkl").read_bytes()).hexdigest()
    return digest[:12]


def _error(code: str, details: dict | None = None, status: int = 400):
    raise SafeWebError(code, status=status, details=details)


def parse_raw_epoch_csv(file_bytes: bytes, filename: str) -> tuple[pd.DataFrame, dict]:
    """Parse and strictly validate one single-night Raw Epoch CSV."""
    if not filename or Path(filename).suffix.lower() != ".csv":
        _error("UNSUPPORTED_FILE_TYPE", {"expected": ".csv"}, status=415)
    if not file_bytes:
        _error("FILE_REQUIRED")
    if len(file_bytes) > MAX_FILE_BYTES:
        _error("FILE_TOO_LARGE", {"max_mb": MAX_FILE_BYTES // (1024 * 1024)}, status=413)

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        _error("CSV_ENCODING_INVALID", {"expected": "UTF-8"})

    try:
        frame = pd.read_csv(io.StringIO(text))
    except Exception:
        _error("CSV_PARSE_FAILED")

    if frame.empty:
        _error("INSUFFICIENT_EPOCHS", {"minimum": 5, "received": 0})

    missing_columns = [column for column in BASE_FEATURES if column not in frame.columns]
    if missing_columns:
        _error("MISSING_COLUMNS", {"columns": missing_columns})

    if len(frame) < 5:
        _error("INSUFFICIENT_EPOCHS", {"minimum": 5, "received": int(len(frame))})

    missing_values = {
        column: int(frame[column].isna().sum())
        for column in BASE_FEATURES
        if frame[column].isna().any()
    }
    if missing_values:
        _error("MISSING_VALUES", {"columns": missing_values})

    for column in BASE_FEATURES:
        converted = pd.to_numeric(frame[column], errors="coerce")
        invalid_count = int(converted.isna().sum())
        if invalid_count:
            _error("NON_NUMERIC_VALUES", {"column": column, "count": invalid_count})
        values = converted.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            _error("NON_FINITE_VALUES", {"column": column})
        frame[column] = converted.astype(float)

    if "subject_id" in frame.columns:
        subject_values = frame["subject_id"].dropna().astype(str).str.strip()
        subject_values = subject_values[subject_values != ""]
        if subject_values.nunique() > 1:
            _error("MULTIPLE_SUBJECTS")

    frame = _sort_and_validate_time(frame)
    _validate_feature_ranges(frame)

    accepted = set(BASE_FEATURES + OPTIONAL_COLUMNS)
    ignored_columns = [column for column in frame.columns if column not in accepted and column != "_time_seconds"]
    safe_frame = frame[BASE_FEATURES + ["_time_seconds"]].copy()

    metadata = {
        "input_epochs": int(len(safe_frame)),
        "ignored_columns": ignored_columns,
        "ordering": "t" if "t" in frame.columns else "timestamp" if "timestamp" in frame.columns else "row_order",
    }
    return safe_frame, metadata


def _sort_and_validate_time(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "t" in frame.columns:
        times = pd.to_numeric(frame["t"], errors="coerce")
        if times.isna().any() or not np.isfinite(times.to_numpy(dtype=float)).all():
            _error("TIME_INTERVAL_INVALID", {"column": "t"})
        frame["_sort_time"] = times.astype(float)
        frame = frame.sort_values("_sort_time", kind="stable").reset_index(drop=True)
        seconds = frame["_sort_time"].to_numpy(dtype=float)
    elif "timestamp" in frame.columns:
        parsed = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
        if parsed.isna().any():
            _error("TIME_INTERVAL_INVALID", {"column": "timestamp"})
        frame["_sort_timestamp"] = parsed
        frame = frame.sort_values("_sort_timestamp", kind="stable").reset_index(drop=True)
        first = frame["_sort_timestamp"].iloc[0]
        seconds = (frame["_sort_timestamp"] - first).dt.total_seconds().to_numpy(dtype=float)
    else:
        frame = frame.reset_index(drop=True)
        seconds = np.arange(len(frame), dtype=float) * 30.0

    if len(seconds) > 1:
        intervals = np.diff(seconds)
        if not np.allclose(intervals, 30.0, rtol=0.0, atol=1e-6):
            bad_index = int(np.flatnonzero(~np.isclose(intervals, 30.0, rtol=0.0, atol=1e-6))[0])
            _error("TIME_INTERVAL_INVALID", {"after_row": bad_index + 1, "expected_seconds": 30})
        if float(seconds[-1] - seconds[0]) > MAX_RECORDING_SECONDS:
            _error("RECORDING_TOO_LONG", {"max_hours": 24})

    frame["_time_seconds"] = seconds
    return frame


def _validate_feature_ranges(frame: pd.DataFrame) -> None:
    checks = {
        "acc_std": frame["acc_std"] < 0,
        "hr_std": frame["hr_std"] < 0,
        "steps_sum": frame["steps_sum"] < 0,
        "acc_order": (frame["acc_min"] > frame["acc_mean"]) | (frame["acc_mean"] > frame["acc_max"]),
        "hr_order": (frame["hr_min"] > frame["hr_mean"]) | (frame["hr_mean"] > frame["hr_max"]),
        "heart_rate": (frame["hr_min"] < 20) | (frame["hr_max"] > 250),
    }
    failed = {name: int(mask.sum()) for name, mask in checks.items() if bool(mask.any())}
    if failed:
        _error("INVALID_FEATURE_RANGE", {"checks": failed})


def build_context_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the exact 45-feature offline context representation."""
    context = frame.copy()
    for feature in BASE_FEATURES:
        context[f"{feature}_prev1"] = context[feature].shift(1)
        context[f"{feature}_prev2"] = context[feature].shift(2)
        context[f"{feature}_next1"] = context[feature].shift(-1)
        context[f"{feature}_next2"] = context[feature].shift(-2)

    context_features = load_schema()["context_features"]
    context = context.dropna(subset=context_features).reset_index(drop=True)
    if context.empty:
        _error("INSUFFICIENT_EPOCHS", {"minimum": 5})
    return context


def predict_raw_epochs(frame: pd.DataFrame) -> dict:
    """Run deterministic inference and return the complete analyzed timeline."""
    schema = load_schema()
    context = build_context_features(frame)
    features = context[schema["context_features"]]
    model = load_model()

    try:
        labels = np.asarray(model.predict(features), dtype=int)
    except Exception as exc:
        raise SafeWebError("PREDICTION_FAILED", status=500) from exc

    if labels.shape[0] != len(context):
        raise SafeWebError("PREDICTION_FAILED", status=500)

    return {
        "stages": labels.tolist(),
        "times_seconds": context["_time_seconds"].astype(float).tolist(),
        "analyzed_epochs": int(len(labels)),
    }
