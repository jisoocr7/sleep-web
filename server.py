"""Flask API backend for sleep staging web app."""
import sys
import io
import json
import pickle
import base64
import tempfile
import threading
import time
from pathlib import Path
from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.data_check import validate_csv
from src.feature_builder import build_context_features
from src.predict import predict, load_schema, load_model
from src.metrics import compute_sleep_metrics, get_metric_reference, get_metric_reference_v2
from src.format_converter import convert_to_epoch_features, REQUIRED_FEATURES
from src.sleep_scoring import (
    compute_sleep_score,
    generate_recommendations,
    generate_reference_comparison,
    generate_summary_text,
)
from src.explain import (
    get_global_importance,
    compute_shap_for_upload,
    natural_language_explanation,
)
from src.report import (
    plot_hypnogram,
    plot_stage_distribution,
    fig_to_base64,
    generate_html_report,
    generate_docx_report,
)

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Enable CORS for all routes (allow cross-origin requests from frontend)
CORS(app)

# Session storage with TTL
SESSION = {}
SESSION_LOCK = threading.Lock()
SESSION_TTL = 86400  # 24 hours


def cleanup_sessions():
    """Remove expired sessions."""
    now = time.time()
    with SESSION_LOCK:
        expired = [sid for sid, s in SESSION.items()
                   if now - s.get("_created", 0) > SESSION_TTL]
        for sid in expired:
            del SESSION[sid]


def start_cleanup_thread():
    """Start a background thread for periodic session cleanup."""
    def _cleanup_loop():
        while True:
            time.sleep(900)  # every 15 minutes
            cleanup_sessions()
    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()


start_cleanup_thread()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/mobile")
def mobile():
    return render_template("mobile.html")


# ─── Format Detection ────────────────────────────────────────────

@app.route("/api/detect-format", methods=["POST"])
def api_detect_format():
    """Detect the format of an uploaded file without full analysis."""
    if "file" not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    try:
        file_bytes = file.read()
    except Exception as e:
        return jsonify({"error": f"文件读取失败: {str(e)}"}), 400

    from src.format_converter import detect_format
    format_name, confidence = detect_format(file_bytes, file.filename or "")

    format_labels = {
        "apple_health_xml": "Apple Health XML (手表原生导出)",
        "autosleep_csv": "AutoSleep CSV",
        "sleep_cycle_csv": "Sleep Cycle CSV",
        "health_auto_export_csv": "Health Auto Export CSV",
        "raw_epoch": "Raw Epoch CSV (原始特征数据)",
        "unknown": "未知格式",
    }

    return jsonify({
        "format_name": format_name,
        "format_label": format_labels.get(format_name, "未知格式"),
        "confidence": round(confidence, 2),
    })


@app.route("/api/convert", methods=["POST"])
def api_convert():
    """Convert an uploaded file and return a preview."""
    if "file" not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    try:
        file_bytes = file.read()
    except Exception as e:
        return jsonify({"error": f"文件读取失败: {str(e)}"}), 400

    result = convert_to_epoch_features(file_bytes, file.filename or "")

    if not result["success"]:
        return jsonify({"error": result["error"]}), 400

    return jsonify({
        "format_detected": result["format_detected"],
        "format_label": result["format_label"],
        "row_count": len(result["df"]),
        "preview_rows": result["preview_rows"],
        "warnings": result["warnings"],
        "metadata": result["metadata"],
    })


# ─── Main Upload & Analysis ──────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Upload file (any supported format), analyze, return all results."""
    if "file" not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    try:
        file_bytes = file.read()
    except Exception as e:
        return jsonify({"error": f"文件读取失败: {str(e)}"}), 400

    # Step 1: Format detection + conversion
    convert_result = convert_to_epoch_features(file_bytes, file.filename or "")
    if not convert_result["success"]:
        return jsonify({
            "error": convert_result["error"],
            "format_detected": convert_result.get("format_detected", "unknown"),
        }), 400

    df = convert_result["df"]
    fmt_meta = convert_result["metadata"]

    # Step 2: Validate
    report = validate_csv(df)
    if not report["valid"]:
        return jsonify({
            "error": f"数据验证失败: 缺少必要列 {report['missing']}",
            "required_columns": REQUIRED_FEATURES,
        }), 400

    # Step 3: Build context features
    df_context = build_context_features(df)

    if len(df_context) < 5:
        return jsonify({
            "error": f"上下文构建后仅剩 {len(df_context)} 个 epoch，至少需要 5 个。请确认数据覆盖了至少 1 小时的睡眠。"
        }), 400

    # Step 4: Predict
    predictions = predict(df_context)

    # Step 5: Metrics
    metrics = compute_sleep_metrics(predictions)

    # Step 6: Sleep scoring
    score_data = compute_sleep_score(metrics)
    recs = generate_recommendations(metrics, score_data.get("subscores"))
    ref_comp = generate_reference_comparison(metrics)
    summary = generate_summary_text(score_data, recs)

    # Step 7: Charts (matplotlib)
    hypno_fig = plot_hypnogram(predictions)
    hypno_b64 = fig_to_base64(hypno_fig)

    dist_fig = plot_stage_distribution(predictions)
    dist_b64 = fig_to_base64(dist_fig)

    # Step 8: Store in session (SHAP computed async in background)
    session_id = str(hash(file.filename + str(datetime.now().timestamp())))
    with SESSION_LOCK:
        SESSION[session_id] = {
            "predictions": predictions,
            "metrics": metrics,
            "df_context": df_context,
            "sleep_score": score_data,
            "recommendations": recs,
            "ref_comparison": ref_comp,
            "summary": summary,
            "upload_importance": None,
            "explanation_text": "",
            "shap_top": [],
            "shap_ready": False,
            "hypno_b64": hypno_b64,
            "dist_b64": dist_b64,
            "filename": file.filename,
            "format_metadata": fmt_meta,
            "row_count_original": len(df),
            "row_count_context": len(df_context),
            "_created": time.time(),
        }

    # Launch SHAP computation in background thread
    def _compute_shap():
        try:
            shap_vals, upload_importance = compute_shap_for_upload(df_context, max_samples=300)
            explanation_text = natural_language_explanation(upload_importance) if upload_importance is not None else ""
            shap_top = []
            if upload_importance is not None:
                for _, row in upload_importance.head(15).iterrows():
                    shap_top.append({
                        "feature": row["feature"],
                        "importance": round(float(row["importance"]), 4),
                    })
            with SESSION_LOCK:
                s = SESSION.get(session_id)
                if s:
                    s["upload_importance"] = upload_importance
                    s["explanation_text"] = explanation_text
                    s["shap_top"] = shap_top
                    s["shap_ready"] = True
        except Exception:
            with SESSION_LOCK:
                s = SESSION.get(session_id)
                if s:
                    s["shap_ready"] = True  # mark done even on failure

    threading.Thread(target=_compute_shap, daemon=True).start()

    # Build response (immediate, no SHAP)
    label_counts = predictions["predicted_stage"].value_counts().to_dict()
    epochs_list = []
    for _, row in predictions.iterrows():
        epoch_data = {
            "predicted_label": int(row["predicted_label"]),
            "predicted_stage": row["predicted_stage"],
            "prob_Wake": round(float(row["prob_Wake"]), 4),
            "prob_NREM": round(float(row["prob_NREM"]), 4),
            "prob_REM": round(float(row["prob_REM"]), 4),
        }
        if "t" in predictions.columns:
            epoch_data["t"] = int(row["t"]) if pd.notna(row["t"]) else None
        epochs_list.append(epoch_data)

    return jsonify({
        "session_id": session_id,
        "format_detected": convert_result["format_detected"],
        "format_label": convert_result["format_label"],
        "format_metadata": fmt_meta,
        "row_count_original": len(df),
        "row_count_context": len(df_context),
        "label_counts": {
            "Wake": int(label_counts.get("Wake", 0)),
            "NREM": int(label_counts.get("NREM", 0)),
            "REM": int(label_counts.get("REM", 0)),
        },
        "metrics": {k: (v if isinstance(v, str) else (round(v, 1) if isinstance(v, float) else v))
                    for k, v in metrics.items()},
        "sleep_score": score_data,
        "recommendations": recs,
        "ref_comparison": {k: v for k, v in ref_comp.items()},
        "summary": summary,
        "hypno_b64": hypno_b64,
        "dist_b64": dist_b64,
        "shap_ready": False,
        "shap_top": [],
        "explanation_text": "",
        "epochs": epochs_list[:200],
        "epochs_total": len(epochs_list),
        "sleep_start_time": fmt_meta.get("sleep_start_time"),
    })


# ─── Scoring (on-demand) ─────────────────────────────────────────

@app.route("/api/score", methods=["POST"])
def api_score():
    """Get sleep score and recommendations for a session."""
    data = request.get_json()
    session_id = data.get("session_id", "")

    with SESSION_LOCK:
        session = SESSION.get(session_id, {})

    if not session:
        return jsonify({"error": "Session 已过期，请重新上传。"}), 404

    metrics = session.get("metrics", {})
    score_data = compute_sleep_score(metrics)
    recs = generate_recommendations(metrics, score_data.get("subscores"))
    ref_comp = generate_reference_comparison(metrics)
    summary = generate_summary_text(score_data, recs)

    return jsonify({
        "sleep_score": score_data,
        "recommendations": recs,
        "ref_comparison": ref_comp,
        "summary": summary,
    })


# ─── SHAP Status (async polling) ─────────────────────────────────

@app.route("/api/shap-status/<session_id>", methods=["GET"])
def api_shap_status(session_id):
    """Poll for async SHAP computation results."""
    with SESSION_LOCK:
        session = SESSION.get(session_id, {})

    if not session:
        return jsonify({"error": "Session expired"}), 404

    return jsonify({
        "shap_ready": session.get("shap_ready", False),
        "shap_top": session.get("shap_top", []),
        "explanation_text": session.get("explanation_text", ""),
    })


# ─── Global SHAP ─────────────────────────────────────────────────

@app.route("/api/global-shap", methods=["GET"])
def api_global_shap():
    """Return pre-computed global SHAP importance."""
    imp = get_global_importance()
    if imp is None:
        return jsonify({"error": "SHAP data not available"}), 404

    result = []
    for _, row in imp.iterrows():
        feat = row["feature"]
        if "hr_" in feat:
            family = "heart_rate"
        elif "acc_" in feat:
            family = "acceleration"
        elif "steps" in feat:
            family = "steps"
        else:
            family = "other"

        if "_prev2" in feat:
            pos = "prev2"
        elif "_prev1" in feat:
            pos = "prev1"
        elif "_next2" in feat:
            pos = "next2"
        elif "_next1" in feat:
            pos = "next1"
        else:
            pos = "current"

        result.append({
            "feature": feat,
            "importance": round(float(row["importance"]), 4),
            "family": family,
            "position": pos,
        })

    return jsonify({"features": result})


# ─── Reports ─────────────────────────────────────────────────────

@app.route("/api/report/html", methods=["POST"])
def api_report_html():
    """Generate HTML report for download."""
    data = request.get_json()
    session_id = data.get("session_id", "")

    with SESSION_LOCK:
        session = SESSION.get(session_id, {})

    if not session:
        return jsonify({"error": "Session 已过期，请重新上传。"}), 404

    html = generate_html_report(
        session["predictions"],
        session["metrics"],
        sleep_score=session.get("sleep_score"),
        recommendations=session.get("recommendations"),
        ref_comparison=session.get("ref_comparison"),
        shap_importance=session.get("upload_importance"),
        explanation_text=session.get("explanation_text", ""),
        upload_filename=session.get("filename", ""),
        format_metadata=session.get("format_metadata"),
    )
    return jsonify({"html": html})


@app.route("/api/report/docx", methods=["POST"])
def api_report_docx():
    """Generate DOCX report for download."""
    data = request.get_json()
    session_id = data.get("session_id", "")

    with SESSION_LOCK:
        session = SESSION.get(session_id, {})

    if not session:
        return jsonify({"error": "Session 已过期，请重新上传。"}), 404

    docx_buf = generate_docx_report(
        session["predictions"],
        session["metrics"],
        sleep_score=session.get("sleep_score"),
        recommendations=session.get("recommendations"),
        ref_comparison=session.get("ref_comparison"),
        shap_importance=session.get("upload_importance"),
        explanation_text=session.get("explanation_text", ""),
        upload_filename=session.get("filename", ""),
        format_metadata=session.get("format_metadata"),
    )

    if docx_buf is None:
        return jsonify({"error": "DOCX 生成失败（缺少 python-docx 库）"}), 500

    return send_file(
        docx_buf,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=f"sleep_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
    )


# ─── Metrics Reference ───────────────────────────────────────────

@app.route("/api/metrics-reference", methods=["GET"])
def api_metrics_reference():
    """Return reference ranges for sleep metrics."""
    return jsonify(get_metric_reference_v2())


# ─── QR Code ─────────────────────────────────────────────────────

@app.route("/api/qr", methods=["GET"])
def api_qr():
    """Generate QR code linking to the mobile upload page."""
    try:
        import qrcode
    except ImportError:
        return jsonify({"error": "QR code generation not available"}), 500

    url = request.args.get("url", request.host_url.rstrip("/") + "/mobile")

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Use warm color for QR
    img = qr.make_image(fill_color="#8B6914", back_color="#FEFAF5")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# ─── Sample Data ─────────────────────────────────────────────────

@app.route("/api/sample-data/<fmt>", methods=["GET"])
def api_sample_data(fmt):
    """Serve sample data files for testing."""
    examples_dir = BASE_DIR / "examples"

    file_map = {
        "epoch": "sample_epoch_features.csv",
        "good-sleep": "text-92.csv",
        "poor-sleep": "sample_poor_sleep.csv",
        "apple-health": "sample_export.xml",
        "autosleep": "sample_autosleep.csv",
        "sleep-cycle": "sample_sleep_cycle.csv",
        "health-export": "sample_health_export.csv",
    }

    # Determine mimetype
    mime_map = {
        ".csv": "text/csv",
        ".xml": "application/xml",
    }

    filename = file_map.get(fmt)
    if not filename:
        return jsonify({
            "error": f"Unknown sample format: {fmt}",
            "available": list(file_map.keys()),
        }), 404

    filepath = examples_dir / filename
    if not filepath.exists():
        return jsonify({"error": f"Sample file not found: {filename}"}), 404

    ext = Path(filename).suffix
    mimetype = mime_map.get(ext, "application/octet-stream")
    return send_file(
        filepath,
        mimetype=mimetype,
        as_attachment=True,
        download_name=filename,
    )


# ─── API Documentation ───────────────────────────────────────────

@app.route("/api/docs", methods=["GET"])
def api_docs():
    """Return API specification."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "睡眠分期分析 API",
            "version": "2.0.0",
            "description": "上传可穿戴设备数据，获取睡眠分期预测、质量评分和个性化报告。",
        },
        "paths": {
            "/api/upload": {
                "post": {
                    "summary": "上传并分析睡眠数据",
                    "description": "支持 Apple Health XML、AutoSleep CSV、Sleep Cycle CSV、Health Auto Export CSV、Raw Epoch CSV 等格式。",
                    "requestBody": {
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "file": {
                                            "type": "string",
                                            "format": "binary",
                                            "description": "睡眠数据文件"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "分析完成，返回睡眠分期、指标、评分、建议"},
                        "400": {"description": "文件格式错误或数据不完整"}
                    }
                }
            },
            "/api/detect-format": {
                "post": {"summary": "检测文件格式，不上传分析"}
            },
            "/api/convert": {
                "post": {"summary": "转换文件并返回预览"}
            },
            "/api/score": {
                "post": {
                    "summary": "获取睡眠评分和建议",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "session_id": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/report/html": {
                "post": {"summary": "生成 HTML 睡眠报告"}
            },
            "/api/report/docx": {
                "post": {"summary": "生成 DOCX 睡眠报告"}
            },
            "/api/metrics-reference": {
                "get": {"summary": "获取指标参考范围（结构化）"}
            },
            "/api/global-shap": {
                "get": {"summary": "获取全局 SHAP 特征重要性"}
            },
            "/api/qr": {
                "get": {
                    "summary": "获取移动端上传页 QR 码",
                    "parameters": [{
                        "name": "url",
                        "in": "query",
                        "description": "QR 码目标 URL（可选，默认为本站 /mobile）",
                        "schema": {"type": "string"}
                    }]
                }
            },
            "/api/sample-data/{format}": {
                "get": {
                    "summary": "下载示例数据",
                    "parameters": [{
                        "name": "format",
                        "in": "path",
                        "description": "格式: epoch, apple-health, autosleep, sleep-cycle, health-export",
                        "schema": {"type": "string"}
                    }]
                }
            },
        }
    }
    return jsonify(spec)


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8501))
    app.run(debug=False, port=port, host="0.0.0.0")
