"""Validate uploaded CSV data for sleep staging prediction."""
import pandas as pd

REQUIRED_BASE_FEATURES = [
    "acc_mean", "acc_std", "acc_min", "acc_max",
    "hr_mean", "hr_std", "hr_min", "hr_max",
    "steps_sum",
]

REQUIRED_COLUMNS = REQUIRED_BASE_FEATURES.copy()
OPTIONAL_COLUMNS = ["subject_id", "t", "timestamp", "stage_raw", "y"]


def validate_csv(df: pd.DataFrame) -> dict:
    """Check uploaded CSV and return a validation report.

    Returns:
        dict with keys: valid (bool), missing (list), extra (list),
            row_count (int), warnings (list), stats (dict)
    """
    report = {
        "valid": True,
        "missing": [],
        "extra": [],
        "row_count": len(df),
        "warnings": [],
        "stats": {},
    }

    # Check required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            report["missing"].append(col)
            report["valid"] = False

    # Check for extra useful columns
    for col in OPTIONAL_COLUMNS:
        if col in df.columns and col not in report["missing"]:
            report["extra"].append(col)

    if not report["valid"]:
        return report

    # Check for NaN in required columns
    na_cols = [c for c in REQUIRED_COLUMNS if df[c].isna().any()]
    if na_cols:
        na_count = {c: int(df[c].isna().sum()) for c in na_cols}
        report["warnings"].append(f"Missing values found in: {na_count}")

    # Check data types and ranges
    stats = {}
    for col in REQUIRED_COLUMNS:
        try:
            col_data = pd.to_numeric(df[col], errors="coerce")
            stats[col] = {
                "min": round(float(col_data.min()), 4),
                "max": round(float(col_data.max()), 4),
                "mean": round(float(col_data.mean()), 4),
            }
        except Exception:
            report["warnings"].append(f"Cannot convert column '{col}' to numeric")

    # Specific range checks
    if "hr_mean" in df.columns:
        hr = pd.to_numeric(df["hr_mean"], errors="coerce")
        if hr.min() < 30 or hr.max() > 220:
            report["warnings"].append(
                f"心率范围异常: {hr.min():.1f} - {hr.max():.1f} bpm"
            )

    if "steps_sum" in df.columns:
        steps = pd.to_numeric(df["steps_sum"], errors="coerce")
        if steps.max() > 200:
            report["warnings"].append(
                f"步数最大值 {steps.max()} 偏高，请确认是否为30秒窗口"
            )

    # Check minimum rows for context construction
    if report["row_count"] < 5:
        report["warnings"].append(
            f"仅 {report['row_count']} 行数据，构建 ±2 上下文需要至少 5 行"
        )

    report["stats"] = stats
    return report
