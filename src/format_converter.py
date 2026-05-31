"""Multi-format sleep data detection and conversion to 30s epoch features."""
import io
from datetime import datetime, timedelta
from xml.etree.ElementTree import iterparse
import pandas as pd
import numpy as np

REQUIRED_FEATURES = [
    "acc_mean", "acc_std", "acc_min", "acc_max",
    "hr_mean", "hr_std", "hr_min", "hr_max",
    "steps_sum",
]

# Population-average accelerometer stats per sleep stage (from Sleep-Accel dataset)
STAGE_ACC_STATS = {
    "Wake": {"acc_mean": 1.000, "acc_std": 0.042, "acc_min": 0.880, "acc_max": 1.160},
    "NREM": {"acc_mean": 0.993, "acc_std": 0.003, "acc_min": 0.985, "acc_max": 1.005},
    "REM":  {"acc_mean": 0.997, "acc_std": 0.009, "acc_min": 0.978, "acc_max": 1.025},
    "Unknown": {"acc_mean": 0.997, "acc_std": 0.010, "acc_min": 0.978, "acc_max": 1.025},
}

# Mapping from Apple Health sleep analysis values to our 3-class stages
APPLE_STAGE_MAP = {
    "HKCategoryValueSleepAnalysisInBed": "Wake",
    "HKCategoryValueSleepAnalysisAwake": "Wake",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "NREM",
    "HKCategoryValueSleepAnalysisAsleepCore": "NREM",
    "HKCategoryValueSleepAnalysisAsleepDeep": "NREM",
    "HKCategoryValueSleepAnalysisAsleepREM": "REM",
    "HKCategoryValueSleepAnalysisAsleep": "NREM",
}

UNKNOWN_STAGE = "Unknown"

FORMAT_LABELS = {
    "apple_health_xml": "Apple Health XML (手表原生导出)",
    "autosleep_csv": "AutoSleep CSV",
    "sleep_cycle_csv": "Sleep Cycle CSV",
    "health_auto_export_csv": "Health Auto Export CSV",
    "raw_epoch": "Raw Epoch CSV (原始特征数据)",
}


def _parse_apple_datetime(dt_str: str):
    """Parse Apple Health date strings like '2024-03-15 22:00:00 +0000'."""
    if dt_str is None:
        return None
    try:
        return datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.fromisoformat(dt_str.replace(" ", "T"))
        except Exception:
            return None


def _stage_value_to_label(val: str) -> str:
    """Convert Apple HKCategoryValue to our stage label."""
    if val is None:
        return UNKNOWN_STAGE
    return APPLE_STAGE_MAP.get(val, UNKNOWN_STAGE)


def _synthesize_acc(stage: str) -> dict:
    """Return synthetic accelerometer features for a given sleep stage."""
    stats = STAGE_ACC_STATS.get(stage, STAGE_ACC_STATS["Unknown"])
    return {
        "acc_mean": stats["acc_mean"] + np.random.normal(0, 0.002),
        "acc_std": max(0.0001, stats["acc_std"] * abs(np.random.normal(1, 0.15))),
        "acc_min": stats["acc_min"] - abs(np.random.normal(0, 0.005)),
        "acc_max": stats["acc_max"] + abs(np.random.normal(0, 0.005)),
    }


def _coerce_timestamp(value):
    """Return a naive pandas Timestamp or NaT for mixed timestamp inputs."""
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return pd.NaT
    try:
        if getattr(ts, "tzinfo", None) is not None:
            ts = ts.tz_convert(None)
    except Exception:
        try:
            ts = ts.tz_localize(None)
        except Exception:
            pass
    return ts


def _sleep_night_date(ts) -> str:
    """Group early-morning sleep into the previous night."""
    ts = _coerce_timestamp(ts)
    if pd.isna(ts):
        return ""
    return (ts.to_pydatetime() - timedelta(hours=12)).date().isoformat()


def _window_id(start, end) -> str:
    start_ts = _coerce_timestamp(start)
    end_ts = _coerce_timestamp(end)
    if pd.isna(start_ts) or pd.isna(end_ts):
        return ""
    return f"{_sleep_night_date(start_ts)}|{start_ts.isoformat()}|{end_ts.isoformat()}"


def _window_label(start, end) -> str:
    start_ts = _coerce_timestamp(start)
    end_ts = _coerce_timestamp(end)
    if pd.isna(start_ts) or pd.isna(end_ts):
        return "未知时间段"
    duration_hours = max(0, (end_ts - start_ts).total_seconds() / 3600)
    return (
        f"{_sleep_night_date(start_ts)} 晚 "
        f"{start_ts.strftime('%H:%M')}-{end_ts.strftime('%H:%M')} "
        f"({duration_hours:.1f} 小时)"
    )


def _window_record(start, end, source: str, row_count: int = 0) -> dict:
    return {
        "id": _window_id(start, end),
        "date": _sleep_night_date(start),
        "label": _window_label(start, end),
        "start": _coerce_timestamp(start).isoformat(),
        "end": _coerce_timestamp(end).isoformat(),
        "source": source,
        "row_count": int(row_count),
    }


def _dedupe_windows(windows: list) -> list:
    seen = set()
    result = []
    for w in windows:
        if not w.get("id") or w["id"] in seen:
            continue
        seen.add(w["id"])
        result.append(w)
    result.sort(key=lambda w: w.get("start", ""), reverse=True)
    return result


def _selected_window_set(selected_window_ids=None):
    if not selected_window_ids:
        return None
    return {w for w in selected_window_ids if w}


def detect_format(file_bytes: bytes, filename: str) -> tuple:
    """Detect the format of an uploaded sleep data file.

    Returns:
        (format_name, confidence) where format_name is one of:
        'apple_health_xml', 'autosleep_csv', 'sleep_cycle_csv',
        'health_auto_export_csv', 'raw_epoch', 'unknown'
    """
    text = None
    try:
        text = file_bytes[:8192].decode("utf-8", errors="ignore")
    except Exception:
        pass

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    # XML detection
    if ext == "xml" or (text and text.lstrip("\ufeff \t\r\n").startswith("<?xml")):
        if text and ("<HealthData" in text or "<!DOCTYPE HealthData" in text):
            return ("apple_health_xml", 0.95)
        return ("unknown", 0.0)

    if not text:
        return ("unknown", 0.0)

    first_lines = text[:2000].strip()

    # Sleep Cycle: semicolon-delimited with specific columns
    if ";" in first_lines.split("\n")[0] if first_lines else False:
        header = first_lines.split("\n")[0].lower()
        if any(col in header for col in ["sleep quality", "heart rate", "awake (seconds)", "dream (seconds)"]):
            return ("sleep_cycle_csv", 0.92)
        # If semicolons but not Sleep Cycle, still likely Sleep Cycle
        if any(col in header for col in ["start", "end", "sleep"]):
            return ("sleep_cycle_csv", 0.75)

    # AutoSleep: comma-delimited with Bedtime/Waketime/Asleep columns
    headers_lower = first_lines.split("\n")[0].lower().replace(",", " ").replace(";", " ")
    autosleep_markers = ["bedtime", "waketime", "asleep", "awake", "inbed", "sleepbpm"]
    autosleep_hits = sum(1 for m in autosleep_markers if m in headers_lower)
    if autosleep_hits >= 3:
        return ("autosleep_csv", min(0.95, 0.6 + autosleep_hits * 0.08))

    # Health Auto Export: columns like StartDate, Value, Units, SourceName
    hae_markers = ["startdate", "value", "units", "sourcename", "devicename"]
    hae_hits = sum(1 for m in hae_markers if m in headers_lower)
    if hae_hits >= 4:
        return ("health_auto_export_csv", min(0.95, 0.6 + hae_hits * 0.08))

    # Raw epoch: has all 9 required feature columns
    req_hits = sum(1 for f in REQUIRED_FEATURES if f in headers_lower)
    if req_hits >= 7:
        return ("raw_epoch", min(0.95, 0.5 + req_hits * 0.05))

    return ("unknown", 0.0)


def _split_sleep_sessions(sleep_records: list) -> list:
    """Split Apple Health sleep records into contiguous sleep sessions."""
    valid = [
        r for r in sleep_records
        if r.get("start") and r.get("end")
        and r["end"] > r["start"]
        and _stage_value_to_label(r.get("value")) != UNKNOWN_STAGE
    ]
    if not valid:
        return []

    valid.sort(key=lambda r: (r["start"], r["end"]))
    sessions = []
    current = []
    current_end = None
    max_gap = timedelta(hours=4)

    for rec in valid:
        if current and rec["start"] - current_end > max_gap:
            sessions.append(current)
            current = []
        current.append(rec)
        current_end = max(current_end, rec["end"]) if current_end else rec["end"]

    if current:
        sessions.append(current)

    def session_bounds(session):
        start = min(r["start"] for r in session)
        end = max(r["end"] for r in session)
        return start, end

    useful_sessions = [
        s for s in sessions
        if (session_bounds(s)[1] - session_bounds(s)[0]) >= timedelta(minutes=20)
    ] or sessions

    return useful_sessions


def _session_bounds(session):
    start = min(r["start"] for r in session)
    end = max(r["end"] for r in session)
    return start, end


def _pick_latest_sleep_session(sleep_records: list) -> list:
    """Return the latest contiguous Apple Health sleep session."""
    useful_sessions = _split_sleep_sessions(sleep_records)
    if not useful_sessions:
        return []

    def session_bounds(session):
        return _session_bounds(session)

    return max(useful_sessions, key=lambda s: session_bounds(s)[1])


def _extract_apple_records(file_bytes: bytes) -> tuple:
    """Extract Apple Health sleep intervals and heart-rate records."""
    sleep_records = []
    hr_records = []
    try:
        context = iterparse(io.BytesIO(file_bytes), events=("end",))
        for _, elem in context:
            if elem.tag != "Record":
                elem.clear()
                continue
            rec_type = elem.get("type", "")
            if rec_type == "HKCategoryTypeIdentifierSleepAnalysis":
                sleep_records.append({
                    "start": _parse_apple_datetime(elem.get("startDate")),
                    "end": _parse_apple_datetime(elem.get("endDate")),
                    "value": elem.get("value", ""),
                })
            elif rec_type == "HKQuantityTypeIdentifierHeartRate":
                start = _parse_apple_datetime(elem.get("startDate"))
                val = elem.get("value")
                if start and val:
                    try:
                        hr_records.append({"time": start, "hr": float(val)})
                    except ValueError:
                        pass
            elem.clear()
    except Exception as e:
        raise ValueError(f"Apple Health XML 解析失败: {str(e)}") from e
    return sleep_records, hr_records


def _apple_session_windows(sleep_records: list) -> list:
    windows = []
    for session in _split_sleep_sessions(sleep_records):
        start, end = _session_bounds(session)
        windows.append(_window_record(start, end, "Apple Health sleep session", len(session)))
    return _dedupe_windows(windows)


def _build_apple_session_epochs(session: list, hr_records: list, subject_id: str) -> pd.DataFrame:
    """Build one Apple Health sleep session into 30-second epoch features."""
    all_starts = [r["start"] for r in session if r["start"]]
    all_ends = [r["end"] for r in session if r["end"]]
    if not all_starts:
        raise ValueError("No valid timestamps found in sleep data.")

    t_min = min(all_starts)
    t_max = max(all_ends)
    epoch_sec = 30
    n_epochs = int((t_max - t_min).total_seconds() / epoch_sec)
    if n_epochs < 5:
        raise ValueError(f"Only {n_epochs} epochs found. Minimum 5 required for analysis.")

    stages = [UNKNOWN_STAGE] * n_epochs
    for rec in session:
        if rec["start"] is None or rec["end"] is None:
            continue
        stage_label = _stage_value_to_label(rec["value"])
        start_idx = max(0, int((rec["start"] - t_min).total_seconds() / epoch_sec))
        end_idx = min(n_epochs, int((rec["end"] - t_min).total_seconds() / epoch_sec))
        for i in range(start_idx, end_idx):
            stages[i] = stage_label

    # Fill unknown epochs from nearest known neighbors.
    last_stage = UNKNOWN_STAGE
    for i in range(n_epochs):
        if stages[i] == UNKNOWN_STAGE and last_stage != UNKNOWN_STAGE:
            stages[i] = last_stage
        elif stages[i] != UNKNOWN_STAGE:
            last_stage = stages[i]

    next_stage = UNKNOWN_STAGE
    for i in range(n_epochs - 1, -1, -1):
        if stages[i] == UNKNOWN_STAGE and next_stage != UNKNOWN_STAGE:
            stages[i] = next_stage
        elif stages[i] != UNKNOWN_STAGE:
            next_stage = stages[i]

    hr_records = sorted(hr_records, key=lambda r: r["time"])
    epoch_hr_vals = [[] for _ in range(n_epochs)]
    for hr in hr_records:
        idx = int((hr["time"] - t_min).total_seconds() / epoch_sec)
        if 0 <= idx < n_epochs:
            epoch_hr_vals[idx].append(hr["hr"])

    stage_default_hr = {"Wake": 65, "NREM": 58, "REM": 62, UNKNOWN_STAGE: 60}
    rows = []
    for i in range(n_epochs):
        stage = stages[i]
        acc = _synthesize_acc(stage)

        hr_list = epoch_hr_vals[i]
        if hr_list:
            hr_mean = float(np.mean(hr_list))
            hr_std = float(np.std(hr_list)) if len(hr_list) > 1 else 1.0
            hr_min = float(np.min(hr_list))
            hr_max = float(np.max(hr_list))
        else:
            default = stage_default_hr.get(stage, 60)
            hr_mean = default + np.random.normal(0, 2)
            hr_std = 2.0 + abs(np.random.normal(0, 0.5))
            hr_min = hr_mean - hr_std
            hr_max = hr_mean + hr_std

        rows.append({
            "acc_mean": round(acc["acc_mean"], 5),
            "acc_std": round(acc["acc_std"], 5),
            "acc_min": round(acc["acc_min"], 5),
            "acc_max": round(acc["acc_max"], 5),
            "hr_mean": round(hr_mean, 4),
            "hr_std": round(hr_std, 4),
            "hr_min": round(hr_min, 4),
            "hr_max": round(hr_max, 4),
            "steps_sum": 0,
            "t": i * epoch_sec,
            "timestamp": (t_min + timedelta(seconds=i * epoch_sec)).isoformat(),
            "subject_id": subject_id,
        })

    return pd.DataFrame(rows)


def parse_apple_health_xml(file_bytes: bytes, selected_window_ids=None) -> pd.DataFrame:
    """Parse Apple Health export.xml to 30-second epoch features.

    Extracts sleep stage intervals and heart rate records, then resamples
    to 30-second epochs. Accelerometer features are synthesized from
    sleep stage labels (Apple Health does not export raw acc data).
    """
    sleep_records, hr_records = _extract_apple_records(file_bytes)

    if not sleep_records:
        raise ValueError("No sleep data found in Apple Health XML. Ensure your watch tracks sleep stages.")

    sessions = _split_sleep_sessions(sleep_records)
    if not sessions:
        raise ValueError("No usable sleep stage records found in Apple Health XML.")

    selected = _selected_window_set(selected_window_ids)
    if selected:
        sessions = [
            session for session in sessions
            if _window_id(*_session_bounds(session)) in selected
        ]
    else:
        sessions = [_pick_latest_sleep_session(sleep_records)]

    if not sessions:
        raise ValueError("所选日期范围内没有可用的 Apple Health 睡眠记录。")

    frames = []
    first_start = None
    for session in sessions:
        start, end = _session_bounds(session)
        first_start = start if first_start is None else min(first_start, start)
        subject_id = f"apple_{_window_id(start, end)}"
        frames.append(_build_apple_session_epochs(session, hr_records, subject_id))

    return pd.concat(frames, ignore_index=True), first_start


def parse_autosleep_csv(file_bytes: bytes, selected_window_ids=None) -> pd.DataFrame:
    """Parse AutoSleep CSV export to 30-second epoch features.

    AutoSleep exports nightly summary data. We generate synthetic epochs
    matching the summary statistics.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))

    # Normalize column names — order matters: specific > generic
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if "sleepbpm" in cl or "sleep bpm" in cl or "heart rate" in cl:
            col_map[c] = "sleep_bpm"
        elif "hrv" in cl:
            col_map[c] = "hrv"
        elif "bedtime" in cl or "bed time" in cl:
            col_map[c] = "bedtime"
        elif "waketime" in cl or "wake time" in cl:
            col_map[c] = "waketime"
        elif cl == "awake" or "time awake" in cl:
            col_map[c] = "awake"
        elif "deep" in cl:
            col_map[c] = "deep"
        elif "rem" in cl:
            col_map[c] = "rem"
        elif cl == "asleep" or "time asleep" in cl:
            col_map[c] = "asleep"
    df = df.rename(columns=col_map)

    rows = []
    first_bedtime = None
    selected = _selected_window_set(selected_window_ids)
    for _, night in df.iterrows():
        if pd.isna(night.get("asleep")) or pd.isna(night.get("bedtime")):
            continue

        # Parse times
        bedtime = pd.Timestamp(night.get("bedtime"))
        waketime = pd.Timestamp(night.get("waketime", bedtime + pd.Timedelta(hours=8)))
        if waketime <= bedtime:
            waketime = bedtime + pd.Timedelta(hours=8)
        current_window_id = _window_id(bedtime, waketime)
        if selected and current_window_id not in selected:
            continue
        if first_bedtime is None:
            first_bedtime = bedtime

        total_sec = (waketime - bedtime).total_seconds()
        if total_sec <= 0 or total_sec > 24 * 3600:
            total_sec = 8 * 3600

        epoch_sec = 30
        n_epochs = int(total_sec / epoch_sec)

        # Parse durations (hours or minutes)
        asleep_hrs = float(night.get("asleep", 6))
        awake_hrs = float(night.get("awake", total_sec / 3600 - asleep_hrs))
        deep_hrs = float(night.get("deep", asleep_hrs * 0.2))
        rem_hrs = float(night.get("rem", asleep_hrs * 0.22))

        # Ensure consistency
        if asleep_hrs + awake_hrs > total_sec / 3600:
            asleep_hrs = total_sec / 3600 - awake_hrs
        if asleep_hrs < 0:
            asleep_hrs = total_sec / 3600 * 0.85
            awake_hrs = total_sec / 3600 * 0.15

        # Convert hours to epoch counts
        nrem_epochs = max(0, int((asleep_hrs - rem_hrs) * 3600 / epoch_sec))
        rem_epochs = max(0, int(rem_hrs * 3600 / epoch_sec))
        wake_epochs = max(0, int(awake_hrs * 3600 / epoch_sec))
        remaining = n_epochs - nrem_epochs - rem_epochs - wake_epochs
        if remaining > 0:
            nrem_epochs += remaining

        # Build stage sequence (simplified: start with wake, cycle through NREM/REM)
        labels = []
        # Distribute: wake initially, then alternating NREM/REM cycles
        wake_front = max(5, int(n_epochs * 0.02))  # ~2% wake at start
        labels.extend([0] * wake_front)
        pos = wake_front
        rem_start = max(wake_front, int(n_epochs * 0.25))  # First REM ~90min in
        rem_dur = min(rem_epochs, int(n_epochs * 0.06))  # ~15-20min REM
        for i in range(pos, n_epochs):
            if rem_epochs > 0 and i >= rem_start and (i - rem_start) % 90 < 20:
                labels.append(2)  # REM
                rem_epochs -= 1
            elif wake_epochs > 0 and np.random.random() < 0.05:
                labels.append(0)  # Wake intrusion
                wake_epochs -= 1
            else:
                labels.append(1)  # NREM
        # Ensure correct length
        while len(labels) < n_epochs:
            labels.append(1)
        labels = labels[:n_epochs]

        # Build epochs
        hr_base = float(night.get("sleep_bpm", 60))
        for i in range(n_epochs):
            lbl = labels[i]
            stage = {0: "Wake", 1: "NREM", 2: "REM"}[lbl]
            acc = _synthesize_acc(stage)
            hr_mean = hr_base + np.random.normal(0, 1.5)
            hr_std = 2.0 + abs(np.random.normal(0, 0.5))
            rows.append({
                "acc_mean": round(acc["acc_mean"], 5),
                "acc_std": round(acc["acc_std"], 5),
                "acc_min": round(acc["acc_min"], 5),
                "acc_max": round(acc["acc_max"], 5),
                "hr_mean": round(hr_mean, 4),
                "hr_std": round(hr_std, 4),
                "hr_min": round(hr_mean - hr_std, 4),
                "hr_max": round(hr_mean + hr_std, 4),
                "steps_sum": 0,
                "t": i * epoch_sec,
                "timestamp": (bedtime + pd.Timedelta(seconds=i * epoch_sec)).isoformat(),
                "subject_id": f"autosleep_{current_window_id}",
            })

    if not rows:
        raise ValueError("No sleep records found in AutoSleep file.")

    return pd.DataFrame(rows), first_bedtime


def parse_sleep_cycle_csv(file_bytes: bytes, selected_window_ids=None) -> pd.DataFrame:
    """Parse Sleep Cycle CSV export to 30-second epoch features."""
    text = file_bytes.decode("utf-8", errors="ignore")
    delimiter = ";" if ";" in text[:500] else ","

    df = pd.read_csv(io.BytesIO(file_bytes), sep=delimiter)

    # Normalize column names
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if "start" == cl:
            col_map[c] = "start"
        elif "end" == cl:
            col_map[c] = "end"
        elif "sleep quality" in cl:
            col_map[c] = "quality"
        elif "heart rate" in cl or "heartrate" in cl:
            col_map[c] = "hr"
        elif "steps" in cl:
            col_map[c] = "steps"
        elif "awake" in cl:
            col_map[c] = "awake_sec"
        elif "dream" in cl or "rem" in cl:
            col_map[c] = "rem_sec"
        elif "light" in cl:
            col_map[c] = "light_sec"
        elif "deep" in cl:
            col_map[c] = "deep_sec"
    df = df.rename(columns=col_map)

    rows = []
    epoch_sec = 30
    first_start = None
    selected = _selected_window_set(selected_window_ids)

    for _, night in df.iterrows():
        if pd.isna(night.get("start")) or pd.isna(night.get("end")):
            continue

        start = pd.Timestamp(night["start"])
        end = pd.Timestamp(night["end"])
        if end <= start:
            continue
        current_window_id = _window_id(start, end)
        if selected and current_window_id not in selected:
            continue
        if first_start is None:
            first_start = start

        total_sec = (end - start).total_seconds()
        if total_sec <= 0:
            continue
        n_epochs = int(total_sec / epoch_sec)

        hr = float(night.get("hr", 60)) if pd.notna(night.get("hr")) else 60
        steps = float(night.get("steps", 0)) if pd.notna(night.get("steps")) else 0

        # Estimate stage proportions
        awake_sec = float(night.get("awake_sec", 0)) if pd.notna(night.get("awake_sec")) else total_sec * 0.1
        rem_sec = float(night.get("rem_sec", total_sec * 0.22)) if pd.notna(night.get("rem_sec")) else total_sec * 0.22
        deep_sec = float(night.get("deep_sec", total_sec * 0.18)) if pd.notna(night.get("deep_sec")) else total_sec * 0.18
        light_sec = total_sec - awake_sec - rem_sec - deep_sec
        if light_sec < 0:
            light_sec = total_sec * 0.4
            awake_sec = total_sec * 0.1
            rem_sec = total_sec * 0.2
            deep_sec = total_sec * 0.3

        # Build epoch labels
        labels = []
        awake_ep = max(1, int(awake_sec / epoch_sec))
        deep_ep = max(1, int(deep_sec / epoch_sec))
        rem_ep = max(0, int(rem_sec / epoch_sec))
        light_ep = max(0, int(light_sec / epoch_sec))

        # Distribute: wake at start, then cycles of light→deep→light→REM
        labels.extend([0] * min(awake_ep, max(3, n_epochs // 30)))
        remaining = n_epochs - len(labels)
        if remaining > 0:
            cycle = ([1] * max(1, light_ep // 4) + [1] * max(1, deep_ep // 3) +
                     [1] * max(1, light_ep // 4) + [2] * max(1, rem_ep // 3))
            while len(labels) < n_epochs:
                labels.extend(cycle)
        labels = labels[:n_epochs]

        steps_per_epoch = steps / max(n_epochs, 1)
        for i in range(n_epochs):
            lbl = labels[i]
            stage = {0: "Wake", 1: "NREM", 2: "REM"}[lbl]
            acc = _synthesize_acc(stage)

            hr_mean = hr + np.random.normal(0, 1.5) + (3 if lbl == 2 else -2 if lbl == 1 else 0)
            hr_std = 2.0 + abs(np.random.normal(0, 0.5))
            rows.append({
                "acc_mean": round(acc["acc_mean"], 5),
                "acc_std": round(acc["acc_std"], 5),
                "acc_min": round(acc["acc_min"], 5),
                "acc_max": round(acc["acc_max"], 5),
                "hr_mean": round(hr_mean, 4),
                "hr_std": round(hr_std, 4),
                "hr_min": round(hr_mean - hr_std, 4),
                "hr_max": round(hr_mean + hr_std, 4),
                "steps_sum": round(steps_per_epoch + np.random.exponential(0.1), 2),
                "t": i * epoch_sec,
                "timestamp": (start + pd.Timedelta(seconds=i * epoch_sec)).isoformat(),
                "subject_id": f"sleepcycle_{current_window_id}",
            })

    if not rows:
        raise ValueError("No sleep records found in Sleep Cycle file.")

    return pd.DataFrame(rows), first_start


def parse_health_auto_export_csv(file_bytes: bytes, selected_window_ids=None) -> pd.DataFrame:
    """Parse Health Auto Export CSV to 30-second epoch features.

    This format has diverse data types. We extract heart rate records
    and resample, synthesizing accelerometer features.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))

    # Normalize columns
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if "startdate" in cl or "start date" in cl:
            col_map[c] = "start_date"
        elif "value" == cl:
            col_map[c] = "value"
        elif "units" == cl:
            col_map[c] = "units"
        elif "type" in cl:
            col_map[c] = "type"
        elif "sourcename" in cl or "source name" in cl:
            col_map[c] = "source"
    df = df.rename(columns=col_map)

    if "start_date" not in df.columns:
        raise ValueError("Health Auto Export CSV must have a StartDate column.")

    # Filter for heart rate records
    hr_col = None
    if "type" in df.columns:
        hr_mask = df["type"].str.lower().str.contains("heart", na=False)
    elif "units" in df.columns:
        hr_mask = df["units"].str.lower().str.contains("bpm|count/min|beat", na=False)
    else:
        hr_mask = pd.Series(True, index=df.index)

    hr_df = df[hr_mask].copy()
    if hr_df.empty:
        hr_df = df.copy()  # Assume all rows are HR if no type/units filter

    # Parse timestamps and values
    hr_df["parsed_time"] = pd.to_datetime(hr_df["start_date"], errors="coerce")
    hr_df["val"] = pd.to_numeric(hr_df["value"], errors="coerce")
    hr_df = hr_df.dropna(subset=["parsed_time", "val"])
    hr_df = hr_df.sort_values("parsed_time")

    if hr_df.empty:
        raise ValueError("No valid heart rate records found.")

    selected = _selected_window_set(selected_window_ids)
    if selected:
        keep_mask = pd.Series(False, index=hr_df.index)
        for _, group in hr_df.groupby(hr_df["parsed_time"].apply(_sleep_night_date)):
            start = group["parsed_time"].min()
            end = group["parsed_time"].max()
            current_window_id = _window_id(start, end)
            if current_window_id in selected:
                keep_mask.loc[group.index] = True
        hr_df = hr_df[keep_mask].copy()
        if hr_df.empty:
            raise ValueError("所选日期范围内没有可用的 Health Auto Export 心率记录。")

    epoch_sec = 30
    rows = []
    first_start = None
    for night_key, group in hr_df.groupby(hr_df["parsed_time"].apply(_sleep_night_date)):
        group = group.sort_values("parsed_time")
        t_min = group["parsed_time"].min()
        t_max = group["parsed_time"].max()
        first_start = t_min if first_start is None else min(first_start, t_min)
        n_epochs = int((t_max - t_min).total_seconds() / epoch_sec)
        if n_epochs < 5:
            continue

        epoch_times = [t_min + timedelta(seconds=i * epoch_sec) for i in range(n_epochs)]
        for i, et in enumerate(epoch_times):
            t_start = et
            t_end = et + timedelta(seconds=epoch_sec)
            mask = (group["parsed_time"] >= t_start) & (group["parsed_time"] < t_end)
            vals = group.loc[mask, "val"]

            if len(vals) > 0:
                hr_mean = float(vals.mean())
                hr_std = float(vals.std()) if len(vals) > 1 else 1.0
                hr_min = float(vals.min())
                hr_max = float(vals.max())
            else:
                hr_mean = 60 + np.random.normal(0, 2)
                hr_std = 2.0
                hr_min = hr_mean - hr_std
                hr_max = hr_mean + hr_std

            # Estimate stage from HR: lower HR -> NREM, mid -> REM, higher -> Wake
            if hr_mean < 55:
                stage = "NREM"
            elif hr_mean > 70:
                stage = "Wake"
            else:
                stage = "REM" if np.random.random() < 0.25 else "NREM"
            acc = _synthesize_acc(stage)

            rows.append({
                "acc_mean": round(acc["acc_mean"], 5),
                "acc_std": round(acc["acc_std"], 5),
                "acc_min": round(acc["acc_min"], 5),
                "acc_max": round(acc["acc_max"], 5),
                "hr_mean": round(hr_mean, 4),
                "hr_std": round(hr_std, 4),
                "hr_min": round(hr_min, 4),
                "hr_max": round(hr_max, 4),
                "steps_sum": 0,
                "t": i * epoch_sec,
                "timestamp": et.isoformat(),
                "subject_id": f"health_export_{night_key}",
            })

    if not rows:
        raise ValueError("所选日期范围内有效 epoch 不足，至少需要 5 个。")

    return pd.DataFrame(rows), first_start


def _timestamp_column(df: pd.DataFrame):
    for col in ["timestamp", "start_date", "start", "datetime", "date_time", "time"]:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            if parsed.notna().sum() >= max(1, min(5, len(df))):
                return col
    return None


def parse_raw_epoch_csv(file_bytes: bytes, selected_window_ids=None) -> tuple:
    """Parse raw epoch CSV and optionally filter by detected timestamp windows."""
    df = pd.read_csv(io.BytesIO(file_bytes))
    ts_col = _timestamp_column(df)
    selected = _selected_window_set(selected_window_ids)

    if ts_col:
        df = df.copy()
        df["_parsed_timestamp"] = pd.to_datetime(df[ts_col], errors="coerce")
        df = df.dropna(subset=["_parsed_timestamp"])
        if selected:
            keep_mask = pd.Series(False, index=df.index)
            for _, group in df.groupby(df["_parsed_timestamp"].apply(_sleep_night_date)):
                start = group["_parsed_timestamp"].min()
                end = group["_parsed_timestamp"].max()
                current_window_id = _window_id(start, end)
                if current_window_id in selected:
                    keep_mask.loc[group.index] = True
            df = df[keep_mask].copy()
            if df.empty:
                raise ValueError("所选日期范围内没有可用的原始 epoch 数据。")

        if "timestamp" not in df.columns:
            df["timestamp"] = df["_parsed_timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S")
        if "subject_id" not in df.columns:
            df["subject_id"] = df["_parsed_timestamp"].apply(lambda ts: f"raw_{_sleep_night_date(ts)}")
        if "t" not in df.columns:
            df["t"] = (
                df.groupby("subject_id")["_parsed_timestamp"]
                .transform(lambda s: (s - s.min()).dt.total_seconds())
                .astype(int)
            )
        first_ts = df["_parsed_timestamp"].min()
        df = df.drop(columns=["_parsed_timestamp"])
        return df, first_ts

    return df, None


def inspect_sleep_windows(file_bytes: bytes, filename: str) -> dict:
    """Detect file format and return selectable date/sleep windows."""
    format_name, confidence = detect_format(file_bytes, filename)
    result = {
        "success": True,
        "format_detected": format_name,
        "format_label": FORMAT_LABELS.get(format_name, "未知格式"),
        "confidence": round(confidence, 2),
        "windows": [],
        "default_window_ids": [],
        "can_filter": False,
        "message": "",
    }

    try:
        if format_name == "apple_health_xml":
            sleep_records, _ = _extract_apple_records(file_bytes)
            windows = _apple_session_windows(sleep_records)
        elif format_name == "autosleep_csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
            col_map = {}
            for c in df.columns:
                cl = c.lower().strip()
                if "bedtime" in cl or "bed time" in cl:
                    col_map[c] = "bedtime"
                elif "waketime" in cl or "wake time" in cl:
                    col_map[c] = "waketime"
                elif cl == "asleep" or "time asleep" in cl:
                    col_map[c] = "asleep"
            df = df.rename(columns=col_map)
            windows = []
            for _, night in df.iterrows():
                if pd.isna(night.get("asleep")) or pd.isna(night.get("bedtime")):
                    continue
                bedtime = pd.Timestamp(night.get("bedtime"))
                waketime = pd.Timestamp(night.get("waketime", bedtime + pd.Timedelta(hours=8)))
                if waketime <= bedtime:
                    waketime = bedtime + pd.Timedelta(hours=8)
                windows.append(_window_record(bedtime, waketime, "AutoSleep nightly row", 1))
        elif format_name == "sleep_cycle_csv":
            text = file_bytes.decode("utf-8", errors="ignore")
            delimiter = ";" if ";" in text[:500] else ","
            df = pd.read_csv(io.BytesIO(file_bytes), sep=delimiter)
            col_map = {}
            for c in df.columns:
                cl = c.lower().strip()
                if "start" == cl:
                    col_map[c] = "start"
                elif "end" == cl:
                    col_map[c] = "end"
            df = df.rename(columns=col_map)
            windows = []
            for _, night in df.iterrows():
                if pd.isna(night.get("start")) or pd.isna(night.get("end")):
                    continue
                start = pd.Timestamp(night["start"])
                end = pd.Timestamp(night["end"])
                if end > start:
                    windows.append(_window_record(start, end, "Sleep Cycle nightly row", 1))
        elif format_name == "health_auto_export_csv":
            df = pd.read_csv(io.BytesIO(file_bytes))
            col_map = {}
            for c in df.columns:
                cl = c.lower().strip()
                if "startdate" in cl or "start date" in cl:
                    col_map[c] = "start_date"
                elif "value" == cl:
                    col_map[c] = "value"
                elif "units" == cl:
                    col_map[c] = "units"
                elif "type" in cl:
                    col_map[c] = "type"
            df = df.rename(columns=col_map)
            if "start_date" not in df.columns:
                windows = []
            else:
                if "type" in df.columns:
                    mask = df["type"].str.lower().str.contains("heart|sleep", na=False)
                elif "units" in df.columns:
                    mask = df["units"].str.lower().str.contains("bpm|count/min|beat", na=False)
                else:
                    mask = pd.Series(True, index=df.index)
                df = df[mask].copy()
                df["_parsed_timestamp"] = pd.to_datetime(df["start_date"], errors="coerce")
                df = df.dropna(subset=["_parsed_timestamp"])
                windows = []
                for _, group in df.groupby(df["_parsed_timestamp"].apply(_sleep_night_date)):
                    start = group["_parsed_timestamp"].min()
                    end = group["_parsed_timestamp"].max()
                    windows.append(_window_record(start, end, "Health Auto Export day", len(group)))
        elif format_name == "raw_epoch":
            df = pd.read_csv(io.BytesIO(file_bytes))
            ts_col = _timestamp_column(df)
            windows = []
            if ts_col:
                df["_parsed_timestamp"] = pd.to_datetime(df[ts_col], errors="coerce")
                df = df.dropna(subset=["_parsed_timestamp"])
                for _, group in df.groupby(df["_parsed_timestamp"].apply(_sleep_night_date)):
                    start = group["_parsed_timestamp"].min()
                    end = group["_parsed_timestamp"].max()
                    windows.append(_window_record(start, end, "Raw epoch timestamp group", len(group)))
        else:
            result["success"] = False
            result["message"] = "无法识别文件格式。"
            return result
    except Exception as e:
        result["success"] = False
        result["message"] = f"日期范围识别失败: {str(e)}"
        return result

    windows = _dedupe_windows(windows)
    result["windows"] = windows
    result["can_filter"] = len(windows) > 0
    if windows:
        result["default_window_ids"] = [windows[0]["id"]]
        result["message"] = f"识别到 {len(windows)} 个睡眠窗口，已按最新优先排序；请选择其中一晚分析。"
    else:
        result["message"] = "未识别到可选择的日期范围，将分析整个文件。"
    return result


def convert_to_epoch_features(file_bytes: bytes, filename: str, selected_window_ids=None) -> dict:
    """Detect format and convert uploaded file to epoch feature DataFrame.

    Returns:
        dict with keys: success, df, format_detected, format_label,
        preview_rows, warnings, metadata, error
    """
    result = {
        "success": False,
        "df": None,
        "format_detected": "unknown",
        "format_label": "未知格式",
        "preview_rows": [],
        "warnings": [],
        "metadata": {
            "source_format": "unknown",
            "conversion_notes": [],
            "features_real": [],
            "features_synthesized": [],
        },
        "error": None,
    }

    try:
        format_name, confidence = detect_format(file_bytes, filename)
        result["format_detected"] = format_name
        result["metadata"]["source_format"] = format_name
    except Exception as e:
        result["error"] = f"Format detection failed: {str(e)}"
        return result

    parser_map = {
        "apple_health_xml": parse_apple_health_xml,
        "autosleep_csv": parse_autosleep_csv,
        "sleep_cycle_csv": parse_sleep_cycle_csv,
        "health_auto_export_csv": parse_health_auto_export_csv,
        "raw_epoch": parse_raw_epoch_csv,
    }

    result["format_label"] = FORMAT_LABELS.get(format_name, "未知格式")

    if format_name == "unknown":
        result["error"] = (
            "无法识别文件格式。支持的格式：\n"
            "1. Apple Health 导出 (export.xml)\n"
            "2. AutoSleep App CSV 导出\n"
            "3. Sleep Cycle App CSV 导出\n"
            "4. Health Auto Export App CSV\n"
            "5. 原始 Epoch 特征 CSV（含 acc_mean/acc_std/hr_mean 等列）\n\n"
            "请确认文件来自以上来源之一。"
        )
        return result

    if format_name not in parser_map:
        result["error"] = f"Format '{format_name}' not yet supported."
        return result

    try:
        df, sleep_start_time = parser_map[format_name](file_bytes, selected_window_ids=selected_window_ids)
    except ValueError as e:
        result["error"] = str(e)
        return result
    except Exception as e:
        result["error"] = f"文件解析失败: {str(e)}"
        return result

    if df.empty:
        result["error"] = "转换后无有效数据。请检查文件是否包含睡眠记录。"
        return result

    # Store sleep start time for hypnogram clock display
    if sleep_start_time is not None:
        result["metadata"]["sleep_start_time"] = sleep_start_time.isoformat() if hasattr(sleep_start_time, 'isoformat') else str(sleep_start_time)

    # Check required columns
    missing = [f for f in REQUIRED_FEATURES if f not in df.columns]
    if missing:
        result["error"] = f"转换后缺少必要列: {missing}"
        return result

    # Set metadata about real vs synthesized features
    if format_name == "raw_epoch":
        result["metadata"]["features_real"] = REQUIRED_FEATURES.copy()
        result["metadata"]["features_synthesized"] = []
        result["metadata"]["conversion_notes"].append("所有特征均来自原始传感器数据。")
    else:
        result["metadata"]["features_real"] = ["hr_mean", "hr_std", "hr_min", "hr_max", "steps_sum"]
        result["metadata"]["features_synthesized"] = ["acc_mean", "acc_std", "acc_min", "acc_max"]
        if format_name == "apple_health_xml":
            result["metadata"]["conversion_notes"].append(
                "Apple Health XML 不含原始加速度数据，加速度特征根据睡眠阶段标签估算。"
            )
            result["metadata"]["conversion_notes"].append(
                "心率数据从 HealthKit 记录中提取并重采样为 30 秒 epoch。"
            )
        else:
            result["metadata"]["conversion_notes"].append(
                f"{FORMAT_LABELS[format_name]} 格式不包含原始加速度数据，加速度特征已合成。"
            )
        if format_name in ("autosleep_csv", "sleep_cycle_csv"):
            result["metadata"]["conversion_notes"].append("Epoch 数据基于夜间摘要统计值生成，为近似估计。")

    inspect_result = inspect_sleep_windows(file_bytes, filename)
    if inspect_result.get("success"):
        available = inspect_result.get("windows", [])
        selected_ids = set(selected_window_ids or [])
        selected_windows = [w for w in available if w.get("id") in selected_ids]
        if not selected_windows and available and not selected_ids:
            selected_windows = [available[0]]
        result["metadata"]["available_windows"] = available
        result["metadata"]["selected_windows"] = selected_windows
        if selected_windows:
            result["metadata"]["conversion_notes"].append(
                "本次仅分析所选日期/睡眠窗口: " + "；".join(w["label"] for w in selected_windows)
            )
        elif available:
            result["metadata"]["conversion_notes"].append("未选择具体日期窗口，已使用默认可分析范围。")

    # Ensure subject_id column for context builder
    if "subject_id" not in df.columns:
        df["subject_id"] = "uploaded_night"

    # Generate preview
    result["preview_rows"] = df.head(20).to_dict(orient="records")
    result["df"] = df
    result["success"] = True
    result["warnings"] = []

    if len(df) < 5:
        result["warnings"].append(f"仅 {len(df)} 个 epoch，上下文构建至少需要 5 个。")

    return result
