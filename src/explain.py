"""SHAP-based model explainability for the sleep staging web app."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from .predict import load_explainer, load_schema

# CJK-friendly font setup
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"


def get_global_importance() -> pd.DataFrame:
    """Load pre-computed global SHAP feature importance."""
    path = MODEL_DIR / "global_shap_importance.csv"
    if path.exists():
        return pd.read_csv(path)
    return None


def plot_global_importance(top_n: int = 12, figsize=(8, 5)):
    """Generate global feature importance bar chart."""
    imp = get_global_importance()
    if imp is None:
        return None

    imp_top = imp.head(top_n).iloc[::-1]  # reverse for horizontal bar

    fig, ax = plt.subplots(figsize=figsize)
    colors = []
    for f in imp_top["feature"]:
        if "hr_" in f:
            colors.append("#e74c3c")  # red for heart rate
        elif "acc_" in f:
            colors.append("#3498db")  # blue for acceleration
        else:
            colors.append("#2ecc71")  # green for steps

    ax.barh(range(len(imp_top)), imp_top["importance"], color=colors, height=0.6)
    ax.set_yticks(range(len(imp_top)))
    ax.set_yticklabels(imp_top["feature"])
    ax.set_xlabel("Mean |SHAP Value|")
    ax.set_title("Global Feature Importance (HGB + Context)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#e74c3c", label="心率 (HR)"),
        Patch(facecolor="#3498db", label="运动 (ACC)"),
        Patch(facecolor="#2ecc71", label="步数 (Steps)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8)

    plt.tight_layout()
    return fig


def compute_shap_for_upload(df_context: pd.DataFrame, max_samples: int = 500):
    """Compute SHAP values for uploaded data.

    Returns:
        fig: SHAP summary plot figure, or None if explainer not available
    """
    explainer = load_explainer()
    schema = load_schema()
    if explainer is None:
        return None, None

    X = df_context[schema["context_features"]].copy()

    # Limit samples for compute
    if len(X) > max_samples:
        rng = np.random.RandomState(42)
        indices = rng.choice(len(X), size=max_samples, replace=False)
        X_sample = X.iloc[indices]
    else:
        X_sample = X

    shap_values = explainer.shap_values(X_sample, check_additivity=False)

    # Handle different SHAP output formats
    if isinstance(shap_values, list):
        # Multi-class as list of arrays: use class 1 (NREM)
        shap_vals = shap_values[1]
        importance_arr = np.abs(shap_vals).mean(axis=0)
    elif shap_values.ndim == 3:
        # Multi-class as 3D array: (samples, features, classes)
        shap_vals = shap_values
        importance_arr = np.abs(shap_values).mean(axis=(0, 2))
    else:
        # Binary or single-output: (samples, features)
        shap_vals = shap_values
        importance_arr = np.abs(shap_values).mean(axis=0)

    # Global importance for this upload
    upload_importance = pd.DataFrame({
        "feature": schema["context_features"],
        "importance": importance_arr,
    }).sort_values("importance", ascending=False)

    return shap_vals, upload_importance


def get_feature_family(feat: str) -> str:
    """Classify feature into sensor family."""
    if "hr_" in feat:
        return "心率 (HR)"
    elif "acc_" in feat:
        return "运动 (ACC)"
    elif "steps" in feat:
        return "步数 (Steps)"
    return "其他"


def natural_language_explanation(upload_importance: pd.DataFrame, top_n: int = 6) -> str:
    """Generate a natural language explanation of model behavior."""
    if upload_importance is None or len(upload_importance) == 0:
        return "无法生成解释：SHAP 数据不可用。"

    top_features = upload_importance.head(top_n)
    lines = ["**模型判断睡眠阶段时主要关注以下特征：**\n"]

    for i, row in top_features.iterrows():
        feat = row["feature"]
        fam = get_feature_family(feat)

        # Determine position descriptor
        if "_prev2" in feat:
            pos = "前 60 秒的"
        elif "_prev1" in feat:
            pos = "前 30 秒的"
        elif "_next1" in feat:
            pos = "后 30 秒的"
        elif "_next2" in feat:
            pos = "后 60 秒的"
        else:
            pos = "当前"

        # Determine metric descriptor
        if "acc_std" in feat:
            metric = "运动波动性"
        elif "acc_mean" in feat:
            metric = "运动均值"
        elif "acc_min" in feat:
            metric = "运动最小值"
        elif "acc_max" in feat:
            metric = "运动最大值"
        elif "hr_std" in feat:
            metric = "心率波动性"
        elif "hr_mean" in feat:
            metric = "平均心率"
        elif "hr_min" in feat:
            metric = "最小心率"
        elif "hr_max" in feat:
            metric = "最大心率"
        elif "steps_sum" in feat:
            metric = "步数"
        else:
            metric = feat

        lines.append(
            f"{i+1}. **{pos}{metric}** ({fam})"
        )

    lines.append("\n> ⚠️ 本结果为可穿戴信号下的算法估计，不等同于临床 PSG 诊断。")
    return "\n".join(lines)
