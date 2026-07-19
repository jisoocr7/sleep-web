"""Conservative summaries derived only from model-predicted stages."""

from __future__ import annotations

import numpy as np


STAGE_NAMES = {0: "Wake", 1: "NREM", 2: "REM"}
EPOCH_MINUTES = 0.5


def _display_percentages(counts: dict[str, int], analyzed_epochs: int) -> dict[str, float]:
    """Allocate tenths deterministically so displayed stage shares sum to 100.0%."""
    stages = ("Wake", "NREM", "REM")
    if not analyzed_epochs:
        return {stage: 0.0 for stage in stages}

    exact_tenths = {stage: counts[stage] * 1000.0 / analyzed_epochs for stage in stages}
    allocated = {stage: int(np.floor(exact_tenths[stage])) for stage in stages}
    remaining = 1000 - sum(allocated.values())
    order = sorted(
        stages,
        key=lambda stage: (exact_tenths[stage] - allocated[stage], -stages.index(stage)),
        reverse=True,
    )
    for stage in order[:remaining]:
        allocated[stage] += 1
    return {stage: allocated[stage] / 10.0 for stage in stages}


def summarize_predictions(stages: list[int], input_epochs: int) -> dict:
    labels = np.asarray(stages, dtype=int)
    analyzed_epochs = int(labels.size)
    counts = {stage: int((labels == label).sum()) for label, stage in STAGE_NAMES.items()}
    display_percentages = _display_percentages(counts, analyzed_epochs)

    stage_summary = {}
    for stage in ("Wake", "NREM", "REM"):
        count = counts[stage]
        stage_summary[stage] = {
            "count": count,
            "minutes": round(count * EPOCH_MINUTES, 1),
            "percent": display_percentages[stage],
        }

    sleep_mask = labels != 0
    sleep_epochs = int(sleep_mask.sum())
    sleep_indices = np.flatnonzero(sleep_mask)
    if sleep_indices.size:
        first_sleep = int(sleep_indices[0])
        last_sleep = int(sleep_indices[-1])
        waso_like_epochs = int((labels[first_sleep : last_sleep + 1] == 0).sum())
    else:
        waso_like_epochs = 0

    return {
        "input_epochs": int(input_epochs),
        "analyzed_epochs": analyzed_epochs,
        "analyzed_duration_minutes": round(analyzed_epochs * EPOCH_MINUTES, 1),
        "stage_summary": stage_summary,
        "derived_metrics": {
            "predicted_total_sleep_minutes": round(sleep_epochs * EPOCH_MINUTES, 1),
            "predicted_sleep_proportion_percent": round(
                display_percentages["NREM"] + display_percentages["REM"], 1
            ),
            "predicted_waso_like_minutes": round(waso_like_epochs * EPOCH_MINUTES, 1),
        },
    }