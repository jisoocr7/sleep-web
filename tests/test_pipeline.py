import hashlib
import io

import pandas as pd
import pytest

from src.errors import SafeWebError
from src.metrics import summarize_predictions
from src.pipeline import parse_raw_epoch_csv, predict_raw_epochs


def _error_code(frame, filename="night.csv"):
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    with pytest.raises(SafeWebError) as captured:
        parse_raw_epoch_csv(buffer.getvalue().encode("utf-8"), filename)
    return captured.value.code


def test_fixed_sample_is_complete_and_deterministic(sample_bytes):
    frame, metadata = parse_raw_epoch_csv(sample_bytes, "sample_raw_epoch.csv")
    hashes = []
    results = []
    for _index in range(3):
        result = predict_raw_epochs(frame)
        hashes.append(hashlib.sha256(bytes(result["stages"])).hexdigest())
        results.append(result)

    assert metadata["input_epochs"] == 961
    assert results[0]["analyzed_epochs"] == 957
    assert len(set(hashes)) == 1
    assert hashes[0] == "fb8bdb4a0f376e1eae6ce9f71a621a4160bb4e3125a78d356e53295f3e839097"

    summary = summarize_predictions(results[0]["stages"], metadata["input_epochs"])
    assert sum(item["count"] for item in summary["stage_summary"].values()) == 957
    assert summary["stage_summary"]["Wake"]["count"] == 130
    assert summary["stage_summary"]["NREM"]["count"] == 470
    assert summary["stage_summary"]["REM"]["count"] == 357


def test_missing_required_column_is_rejected(sample_bytes):
    frame = pd.read_csv(io.BytesIO(sample_bytes), nrows=12).drop(columns=["hr_mean"])
    assert _error_code(frame) == "MISSING_COLUMNS"


def test_missing_value_is_rejected(sample_bytes):
    frame = pd.read_csv(io.BytesIO(sample_bytes), nrows=12)
    frame.loc[4, "acc_mean"] = float("nan")
    assert _error_code(frame) == "MISSING_VALUES"


def test_non_numeric_value_is_rejected(sample_bytes):
    frame = pd.read_csv(io.BytesIO(sample_bytes), nrows=12)
    frame["hr_mean"] = frame["hr_mean"].astype(object)
    frame.loc[4, "hr_mean"] = "not-a-number"
    assert _error_code(frame) == "NON_NUMERIC_VALUES"


def test_infinite_value_is_rejected(sample_bytes):
    frame = pd.read_csv(io.BytesIO(sample_bytes), nrows=12)
    frame.loc[4, "hr_mean"] = float("inf")
    assert _error_code(frame) == "NON_FINITE_VALUES"


def test_multiple_subjects_are_rejected(sample_bytes):
    frame = pd.read_csv(io.BytesIO(sample_bytes), nrows=12)
    frame["subject_id"] = ["A"] * 6 + ["B"] * 6
    assert _error_code(frame) == "MULTIPLE_SUBJECTS"


def test_non_30_second_timeline_is_rejected(sample_bytes):
    frame = pd.read_csv(io.BytesIO(sample_bytes), nrows=12)
    frame.loc[6, "t"] += 5
    assert _error_code(frame) == "TIME_INTERVAL_INVALID"


def test_non_csv_extension_is_rejected(sample_bytes):
    with pytest.raises(SafeWebError) as captured:
        parse_raw_epoch_csv(sample_bytes, "export.xml")
    assert captured.value.code == "UNSUPPORTED_FILE_TYPE"
