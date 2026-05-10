"""Sleep Stage Classification Web MVP — Streamlit Application.

Upload wearable epoch features → Predict Wake/NREM/REM → Hypnogram → Metrics → SHAP → Report.
"""
import sys
from pathlib import Path
import io

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
import pandas as pd
import numpy as np

from src.data_check import validate_csv, REQUIRED_BASE_FEATURES
from src.feature_builder import build_context_features, BASE_FEATURES, CONTEXT_FEATURES
from src.predict import predict, load_schema
from src.metrics import compute_sleep_metrics, get_metric_reference
from src.explain import (
    get_global_importance,
    plot_global_importance,
    compute_shap_for_upload,
    natural_language_explanation,
)
from src.report import (
    plot_hypnogram,
    plot_stage_distribution,
    generate_html_report,
    generate_docx_report,
)

st.set_page_config(
    page_title="睡眠分期分析系统",
    page_icon="🌙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- Sidebar ----
st.sidebar.title("🌙 睡眠分期分析")
st.sidebar.markdown("**可穿戴设备 · 离线整晚分析**")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📌 关于本系统")
st.sidebar.markdown(
    "基于 Apple Watch 信号（加速度、心率、步数）进行 "
    "Wake / NREM / REM 三分类睡眠分期。\n\n"
    "**模型：** HGB + Context (±2)\n"
    "**训练数据：** Sleep-Accel 公开数据集（31 人）\n"
    "**分析模式：** 整晚离线分析"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📥 模板下载")

# Generate sample CSV from processed data
sample_path = Path(__file__).resolve().parent / "examples" / "sample_epoch_features.csv"
if sample_path.exists():
    with open(sample_path, "rb") as f:
        st.sidebar.download_button(
            label="下载样例数据 CSV",
            data=f,
            file_name="sample_epoch_features.csv",
            mime="text/csv",
        )

st.sidebar.markdown("---")
st.sidebar.markdown("### 📖 使用步骤")
st.sidebar.markdown(
    "1. 上传包含 9 个基础特征的 CSV 文件\n"
    "2. 系统自动构建 ±2 上下文特征\n"
    "3. 模型预测 Wake/NREM/REM\n"
    "4. 生成整夜分期图和睡眠指标\n"
    "5. 查看 SHAP 可解释性分析\n"
    "6. 下载个体睡眠报告"
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ 本系统为算法估计，不等同于临床 PSG 诊断。\n"
    "模型使用了未来 epoch (±2 上下文)，属于离线分析。"
)

# ---- Main Content ----
st.title("🌙 可穿戴睡眠分期分析系统")
st.markdown(
    "上传 Apple Watch / 可穿戴设备的 30 秒 epoch 特征数据，自动进行睡眠分期预测与分析。"
)

# Initialize session state
for key, default in {
    "predictions": None,
    "metrics": None,
    "context_df": None,
    "upload_filename": None,
    "shap_done": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ---- Step 1: Upload ----
st.header("📤 步骤 1：上传数据")

upload_col, info_col = st.columns([2, 1])
with upload_col:
    uploaded_file = st.file_uploader(
        "上传 CSV 文件（需包含 9 个基础特征列）",
        type=["csv"],
        help="CSV 文件需包含：acc_mean, acc_std, acc_min, acc_max, hr_mean, hr_std, hr_min, hr_max, steps_sum",
    )

with info_col:
    st.markdown("**要求：**")
    st.markdown(
        "- 包含 9 个基础特征列\n"
        "- 每行 = 一个 30 秒 epoch\n"
        "- 支持可选列：`t`, `subject_id`\n"
        "- 至少需要 5 行数据（±2 上下文需要）"
    )

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.session_state.upload_filename = uploaded_file.name

        # Validate
        report = validate_csv(df)

        if report["valid"]:
            st.success(f"✅ 数据验证通过 — {report['row_count']} 行，{len(df.columns)} 列")

            with st.expander("📋 数据预览与字段统计", expanded=False):
                st.dataframe(df.head(10), use_container_width=True)

                if report["stats"]:
                    stats_df = pd.DataFrame(report["stats"]).T
                    st.dataframe(stats_df, use_container_width=True)

                if report["warnings"]:
                    for w in report["warnings"]:
                        st.warning(w)

            # ---- Step 2: Build Context Features ----
            st.header("🔧 步骤 2：构建上下文特征")
            with st.spinner("正在构建 ±2 上下文特征..."):
                df_context = build_context_features(df)
                st.session_state.context_df = df_context

            before = len(df)
            after = len(df_context)
            st.success(
                f"✅ 上下文特征构建完成 — 有效 epoch：{after} 个 "
                f"（去除边界 {before - after} 行）"
            )
            st.caption(f"特征维度：{len(CONTEXT_FEATURES)} 列（9 基础特征 × 5 时间位置）")

            # ---- Step 3: Predict ----
            st.header("🤖 步骤 3：模型预测")
            with st.spinner("正在加载模型并预测..."):
                predictions = predict(df_context)
                st.session_state.predictions = predictions

            # Label distribution
            label_counts = predictions["predicted_stage"].value_counts()
            cols = st.columns(3)
            for i, (stage, color) in enumerate([
                ("Wake", "#e74c3c"), ("NREM", "#2ecc71"), ("REM", "#3498db")
            ]):
                count = label_counts.get(stage, 0)
                pct = count / len(predictions) * 100 if len(predictions) > 0 else 0
                cols[i].metric(
                    f"{stage}",
                    f"{count}",
                    f"{pct:.1f}%",
                )

            with st.expander("📋 预测结果明细", expanded=False):
                st.dataframe(predictions, use_container_width=True)

            # ---- Step 4: Hypnogram ----
            st.header("📊 步骤 4：整夜睡眠分期图")
            fig_hypno = plot_hypnogram(predictions)
            st.pyplot(fig_hypno)

            col1, col2 = st.columns(2)
            with col1:
                fig_dist = plot_stage_distribution(predictions)
                st.pyplot(fig_dist)

            # ---- Step 5: Sleep Metrics ----
            st.header("📋 步骤 5：睡眠质量指标")
            metrics = compute_sleep_metrics(predictions)
            st.session_state.metrics = metrics

            ref = get_metric_reference()

            metric_cols = st.columns(3)
            for i, (key, value) in enumerate(metrics.items()):
                with metric_cols[i % 3]:
                    ref_text = ref.get(key, "")
                    st.metric(
                        label=key,
                        value=value,
                        delta=ref_text if ref_text else None,
                        delta_color="off",
                    )

            # ---- Step 6: SHAP Explainability ----
            st.header("🔍 步骤 6：可解释性分析")

            with st.spinner("正在计算 SHAP 值..."):
                shap_vals, upload_importance = compute_shap_for_upload(df_context)

            if upload_importance is not None:
                explanation_text = natural_language_explanation(upload_importance)
                st.markdown(explanation_text)

                st.markdown("**全局特征重要性（预计算）**")
                fig_global = plot_global_importance(top_n=12)
                if fig_global:
                    st.pyplot(fig_global)

                st.markdown("**本次上传数据的特征重要性 Top 10**")
                top10 = upload_importance.head(10)
                st.dataframe(
                    top10.style.background_gradient(subset=["importance"], cmap="Reds"),
                    use_container_width=True,
                )
            else:
                st.info("SHAP 解释器尚未就绪，请先运行模型训练脚本生成 SHAP 解释器。")

            # ---- Step 7: Report ----
            st.header("📝 步骤 7：生成睡眠报告")

            rep_col1, rep_col2 = st.columns(2)

            with rep_col1:
                st.markdown("**HTML 报告（可直接在浏览器中查看）**")
                html_report = generate_html_report(
                    predictions,
                    metrics,
                    upload_importance,
                    explanation_text if upload_importance is not None else "",
                    uploaded_file.name,
                )
                st.download_button(
                    label="📥 下载 HTML 报告",
                    data=html_report,
                    file_name=f"sleep_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True,
                )

                # Preview
                with st.expander("👁 报告预览", expanded=False):
                    st.components.v1.html(html_report, height=600, scrolling=True)

            with rep_col2:
                st.markdown("**DOCX 报告（Word 文档）**")
                try:
                    docx_buf = generate_docx_report(
                        predictions,
                        metrics,
                        upload_importance,
                        explanation_text if upload_importance is not None else "",
                        uploaded_file.name,
                    )
                    if docx_buf:
                        st.download_button(
                            label="📥 下载 DOCX 报告",
                            data=docx_buf,
                            file_name=f"sleep_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True,
                        )
                    else:
                        st.warning("python-docx 未安装，无法生成 DOCX 报告。运行 `pip install python-docx` 安装。")
                except Exception as e:
                    st.warning(f"DOCX 生成失败：{e}")

        else:
            st.error(f"❌ 数据验证失败 — 缺少列：{report['missing']}")
            st.markdown("**需要以下 9 个基础特征列：**")
            st.code(", ".join(REQUIRED_BASE_FEATURES))
            st.markdown("请参考样例数据模板准备您的 CSV 文件。")

    except Exception as e:
        st.error(f"处理文件时出错：{e}")
        st.info("请确认 CSV 格式正确。可以先下载样例数据模板作为参考。")

else:
    # Landing state
    st.info("👆 请上传包含 9 个基础特征的 CSV 文件开始分析")

    st.markdown("### 支持的输入格式")
    st.markdown(
        "您的 CSV 文件至少需要包含以下 **9 列基础特征**（每行对应一个 30 秒 epoch）：\n\n"
        "| 列名 | 含义 | 示例值 |\n"
        "|------|------|--------|\n"
        "| `acc_mean` | 加速度均值 | 1.000 |\n"
        "| `acc_std` | 加速度标准差 | 0.004 |\n"
        "| `acc_min` | 加速度最小值 | 0.955 |\n"
        "| `acc_max` | 加速度最大值 | 1.027 |\n"
        "| `hr_mean` | 心率均值 (bpm) | 53.6 |\n"
        "| `hr_std` | 心率标准差 | 2.89 |\n"
        "| `hr_min` | 最小心率 (bpm) | 50 |\n"
        "| `hr_max` | 最大心率 (bpm) | 56 |\n"
        "| `steps_sum` | 步数总和 | 0 |\n\n"
        "可选列：`t`（时间戳/序号）、`subject_id`（受试者 ID）"
    )

    st.markdown("### 🔬 技术说明")
    tech_col1, tech_col2, tech_col3 = st.columns(3)
    with tech_col1:
        st.markdown(
            "**模型架构**\n"
            "- HistGradientBoosting (HGB)\n"
            "- ±2 上下文窗口\n"
            "- 45 个输入特征\n"
            "- 3 分类：Wake/NREM/REM"
        )
    with tech_col2:
        st.markdown(
            "**训练数据**\n"
            "- Sleep-Accel 公开数据集\n"
            "- 31 名健康受试者\n"
            "- 26,773 个有效 epoch\n"
            "- PSG 标注作为金标准"
        )
    with tech_col3:
        st.markdown(
            "**性能指标**\n"
            "- 主要指标：Macro-F1 ≈ 0.50\n"
            "- 严格 subject-wise 验证\n"
            "- 分类别 F1 可用\n"
            "- SHAP 可解释性"
        )

# ---- Footer ----
st.markdown("---")
st.caption(
    "⚠️ 本系统基于可穿戴设备信号进行算法估计，结果不等同于临床多导睡眠图（PSG）诊断。"
    "模型在 Sleep-Accel 公开数据集（31 名受试者）上训练，未经过独立外部验证。"
    "当前为离线睡眠分期分析（使用了 ±2 上下文窗口，包含未来 epoch）。"
    "仅供健康管理参考和研究演示，不构成医疗诊断。"
)
