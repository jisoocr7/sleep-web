"""Calculate sleep quality metrics from predicted sleep stages."""
import pandas as pd
import numpy as np


def compute_sleep_metrics(predictions: pd.DataFrame) -> dict:
    """Compute overnight sleep metrics from epoch-level predictions.

    Args:
        predictions: DataFrame with 'predicted_label' column (0=Wake, 1=NREM, 2=REM)

    Returns:
        dict of sleep metrics
    """
    labels = predictions["predicted_label"].values
    n_epochs = len(labels)
    epoch_duration = 30  # seconds

    wake_epochs = (labels == 0).sum()
    nrem_epochs = (labels == 1).sum()
    rem_epochs = (labels == 2).sum()
    sleep_epochs = nrem_epochs + rem_epochs

    # TST: Total Sleep Time
    tst_minutes = sleep_epochs * epoch_duration / 60

    # Time in bed
    tib_minutes = n_epochs * epoch_duration / 60

    # Sleep efficiency
    se_pct = (sleep_epochs / n_epochs * 100) if n_epochs > 0 else 0

    # WASO: Wake After Sleep Onset
    # Find first sleep epoch, then count wake after that
    sleep_indices = np.where(labels != 0)[0]
    if len(sleep_indices) > 0:
        first_sleep = sleep_indices[0]
        last_sleep = sleep_indices[-1]
        wake_after_onset = ((labels == 0) & (np.arange(n_epochs) > first_sleep)).sum()
        waso_minutes = wake_after_onset * epoch_duration / 60
        sleep_period_epochs = last_sleep - first_sleep + 1
    else:
        waso_minutes = 0
        sleep_period_epochs = 0

    # Stage proportions
    nrem_pct = (nrem_epochs / sleep_epochs * 100) if sleep_epochs > 0 else 0
    rem_pct = (rem_epochs / sleep_epochs * 100) if sleep_epochs > 0 else 0

    # Stage transitions
    transitions = (labels[1:] != labels[:-1]).sum()

    # Sleep latency: minutes to first sleep epoch
    sleep_latency = first_sleep * epoch_duration / 60 if len(sleep_indices) > 0 else None

    # REM latency: time from first sleep epoch to first REM epoch
    rem_indices = np.where(labels == 2)[0]
    if len(sleep_indices) > 0 and len(rem_indices) > 0:
        first_rem = rem_indices[0]
        rem_latency = (first_rem - first_sleep) * epoch_duration / 60
        rem_latency = max(0, round(rem_latency, 1))
    else:
        rem_latency = None

    # Sleep cycle count: NREM→REM transitions
    cycle_count = 0
    in_rem = False
    for lbl in labels:
        if lbl == 2 and not in_rem:
            cycle_count += 1
            in_rem = True
        elif lbl != 2:
            in_rem = False

    metrics = {
        "总记录时长 (分钟)": round(tib_minutes, 1),
        "总睡眠时长 TST (分钟)": round(tst_minutes, 1),
        "睡眠效率 SE (%)": round(se_pct, 1),
        "入睡后清醒 WASO (分钟)": round(waso_minutes, 1),
        "入睡潜伏期 (分钟)": round(sleep_latency, 1) if sleep_latency is not None else "N/A",
        "REM 潜伏期 (分钟)": round(rem_latency, 1) if rem_latency is not None else "N/A",
        "Wake 时长 (分钟)": round(wake_epochs * epoch_duration / 60, 1),
        "NREM 时长 (分钟)": round(nrem_epochs * epoch_duration / 60, 1),
        "REM 时长 (分钟)": round(rem_epochs * epoch_duration / 60, 1),
        "NREM 占比 (%)": round(nrem_pct, 1),
        "REM 占比 (%)": round(rem_pct, 1),
        "阶段转换次数": int(transitions),
        "睡眠周期数": int(cycle_count),
        "有效 epoch 数": n_epochs,
    }

    return metrics


def get_metric_reference() -> dict:
    """Return reference ranges for sleep metrics (healthy adults)."""
    return {
        "总睡眠时长 TST (分钟)": "成人通常 360-480 分钟 (6-8 小时)",
        "睡眠效率 SE (%)": ">85% 为正常，<80% 可能提示睡眠效率低下",
        "入睡后清醒 WASO (分钟)": "成人通常 <30-60 分钟",
        "入睡潜伏期 (分钟)": "通常 <30 分钟，>30 分钟可能提示入睡困难",
        "REM 潜伏期 (分钟)": "通常 70-120 分钟",
        "NREM 占比 (%)": "通常占 TST 的 75-80%",
        "REM 占比 (%)": "通常占 TST 的 20-25%",
        "阶段转换次数": "正常夜间约 20-40 次阶段转换",
        "睡眠周期数": "正常每夜 4-6 个完整睡眠周期",
    }


def get_metric_reference_v2() -> dict:
    """Return structured reference data for sleep metrics."""
    return {
        "总睡眠时长 TST (分钟)": {
            "label": "总睡眠时长",
            "unit": "分钟",
            "reference_range": "360-480 分钟 (6-8 小时)",
            "normal_min": 360, "normal_max": 480,
            "borderline_min": 300, "borderline_max": 540,
            "interpretation": {
                "low": "睡眠时长偏短，建议争取更多睡眠时间",
                "normal": "睡眠时长在健康范围内",
                "high": "睡眠时长偏长，注意观察是否伴有白天嗜睡",
            },
            "source": "AASM / CDC",
        },
        "睡眠效率 SE (%)": {
            "label": "睡眠效率",
            "unit": "%",
            "reference_range": ">85%",
            "normal_min": 85, "normal_max": 100,
            "borderline_min": 70, "borderline_max": 100,
            "interpretation": {
                "low": "睡眠效率偏低，床上清醒时间较多",
                "normal": "睡眠效率良好",
                "high": "",
            },
            "source": "AASM",
        },
        "入睡后清醒 WASO (分钟)": {
            "label": "入睡后清醒",
            "unit": "分钟",
            "reference_range": "<30 分钟",
            "normal_min": 0, "normal_max": 30,
            "borderline_min": 0, "borderline_max": 60,
            "interpretation": {
                "low": "",
                "normal": "夜间清醒时间正常",
                "high": "夜间清醒时间偏长，睡眠碎片化",
            },
            "source": "AASM",
        },
        "入睡潜伏期 (分钟)": {
            "label": "入睡潜伏期",
            "unit": "分钟",
            "reference_range": "<30 分钟",
            "normal_min": 0, "normal_max": 30,
            "borderline_min": 0, "borderline_max": 45,
            "interpretation": {
                "low": "",
                "normal": "入睡速度正常",
                "high": "入睡较慢，可能存在入睡困难",
            },
            "source": "AASM",
        },
        "REM 潜伏期 (分钟)": {
            "label": "REM 潜伏期",
            "unit": "分钟",
            "reference_range": "70-120 分钟",
            "normal_min": 70, "normal_max": 120,
            "borderline_min": 50, "borderline_max": 150,
            "interpretation": {
                "low": "REM 潜伏期偏短",
                "normal": "REM 潜伏期正常",
                "high": "REM 潜伏期偏长",
            },
            "source": "AASM",
        },
        "REM 占比 (%)": {
            "label": "REM 占比",
            "unit": "%",
            "reference_range": "20-25% of TST",
            "normal_min": 18, "normal_max": 28,
            "borderline_min": 15, "borderline_max": 30,
            "interpretation": {
                "low": "REM 占比偏低，可能影响记忆和情绪调节",
                "normal": "REM 占比正常",
                "high": "REM 占比偏高，可能提示 REM 反弹",
            },
            "source": "NIH / NINDS",
        },
        "NREM 占比 (%)": {
            "label": "NREM 占比",
            "unit": "%",
            "reference_range": "75-80% of TST",
            "normal_min": 70, "normal_max": 85,
            "borderline_min": 60, "borderline_max": 90,
            "interpretation": {
                "low": "NREM 占比偏低",
                "normal": "NREM 占比正常",
                "high": "NREM 占比偏高",
            },
            "source": "AASM",
        },
        "阶段转换次数": {
            "label": "阶段转换",
            "unit": "次",
            "reference_range": "20-40 次/晚",
            "normal_min": 15, "normal_max": 50,
            "borderline_min": 10, "borderline_max": 60,
            "interpretation": {
                "low": "阶段转换偏少，可能睡眠较深",
                "normal": "阶段转换次数正常",
                "high": "阶段转换偏多，睡眠较不稳定",
            },
            "source": "AASM",
        },
        "睡眠周期数": {
            "label": "睡眠周期",
            "unit": "次",
            "reference_range": "4-6 个周期/晚",
            "normal_min": 4, "normal_max": 6,
            "borderline_min": 3, "borderline_max": 7,
            "interpretation": {
                "low": "睡眠周期偏少，深度睡眠可能不足",
                "normal": "睡眠周期数正常",
                "high": "睡眠周期偏多，可能睡眠碎片化",
            },
            "source": "AASM",
        },
    }
