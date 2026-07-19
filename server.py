"""Flask server for the BSPC submission-safe research prototype."""

from __future__ import annotations

import io
import os
import secrets
import threading
import time
from pathlib import Path

import qrcode
from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge

from src.errors import SafeWebError
from src.metrics import summarize_predictions
from src.pipeline import (
    MAX_FILE_BYTES,
    load_model,
    model_id,
    parse_raw_epoch_csv,
    predict_raw_epochs,
)
from src.reporting import generate_docx_report, generate_html_report


PROJECT_ROOT = Path(__file__).resolve().parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
SESSION_TTL_SECONDS = 30 * 60


class ResultStore:
    """In-memory, non-identifying prediction results with a short TTL."""

    def __init__(self):
        self._items = {}
        self._lock = threading.Lock()

    def put(self, payload: dict) -> str:
        self.cleanup()
        session_id = secrets.token_urlsafe(24)
        with self._lock:
            self._items[session_id] = {
                "expires_at": time.time() + SESSION_TTL_SECONDS,
                "payload": payload,
            }
        return session_id

    def get(self, session_id: str) -> dict:
        self.cleanup()
        with self._lock:
            item = self._items.get(session_id)
            if not item:
                raise SafeWebError("SESSION_EXPIRED", status=404)
            return item["payload"]

    def cleanup(self) -> None:
        now = time.time()
        with self._lock:
            expired = [key for key, item in self._items.items() if item["expires_at"] <= now]
            for key in expired:
                self._items.pop(key, None)


RESULTS = ResultStore()


def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.update(
        TESTING=testing,
        MAX_CONTENT_LENGTH=MAX_FILE_BYTES + 1024 * 1024,
        JSON_SORT_KEYS=False,
    )

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; font-src 'self'; base-uri 'self'; frame-ancestors 'self'"
        )
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/")
    def index():
        return render_template("index.html", mobile_mode=False)

    @app.get("/mobile")
    def mobile():
        return render_template("index.html", mobile_mode=True)

    @app.get("/favicon.ico")
    def favicon():
        return send_file(PROJECT_ROOT / "static" / "favicon.svg", mimetype="image/svg+xml", max_age=86400)

    @app.post("/api/upload")
    def upload():
        if request.headers.get("X-Privacy-Ack", "").lower() != "true":
            raise SafeWebError("CONSENT_REQUIRED", status=403)
        if request.form.get("privacy_ack", "").lower() != "true":
            raise SafeWebError("CONSENT_REQUIRED", status=403)

        upload_file = request.files.get("file")
        if upload_file is None or not upload_file.filename:
            raise SafeWebError("FILE_REQUIRED")

        file_bytes = upload_file.read(MAX_FILE_BYTES + 1)
        upload_file.close()
        if len(file_bytes) > MAX_FILE_BYTES:
            raise SafeWebError(
                "FILE_TOO_LARGE",
                status=413,
                details={"max_mb": MAX_FILE_BYTES // (1024 * 1024)},
            )

        frame, metadata = parse_raw_epoch_csv(file_bytes, upload_file.filename)
        prediction = predict_raw_epochs(frame)
        summary = summarize_predictions(prediction["stages"], metadata["input_epochs"])
        payload = {
            "stages": prediction["stages"],
            "times_seconds": prediction["times_seconds"],
            "summary": summary,
            "model_id": model_id(),
        }
        session_id = RESULTS.put(payload)

        return jsonify(
            {
                "ok": True,
                "session_id": session_id,
                "expires_in_seconds": SESSION_TTL_SECONDS,
                "model": {
                    "id": payload["model_id"],
                    "name": "HGB context model",
                    "epoch_seconds": 30,
                    "base_features": 9,
                    "context_features": 45,
                    "context": "offline +/-2 epochs",
                    "classes": ["Wake", "NREM", "REM"],
                },
                "input": metadata,
                "summary": summary,
                "timeline": {
                    "stages": payload["stages"],
                    "times_seconds": payload["times_seconds"],
                },
            }
        )

    @app.get("/api/sample-data/raw")
    def sample_data():
        return send_file(
            EXAMPLES_DIR / "sample_raw_epoch.csv",
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name="sample_raw_epoch.csv",
            max_age=0,
        )

    @app.get("/api/schema-template")
    def schema_template():
        return send_file(
            EXAMPLES_DIR / "raw_epoch_template.csv",
            mimetype="text/csv; charset=utf-8",
            as_attachment=True,
            download_name="raw_epoch_template.csv",
            max_age=0,
        )

    @app.post("/api/report/html")
    def html_report():
        payload, language = _report_request()
        report_bytes = generate_html_report(payload, language)
        return send_file(
            io.BytesIO(report_bytes),
            mimetype="text/html; charset=utf-8",
            as_attachment=True,
            download_name=f"sleep_staging_research_report_{language}.html",
            max_age=0,
        )

    @app.post("/api/report/docx")
    def docx_report():
        payload, language = _report_request()
        report_buffer = generate_docx_report(payload, language)
        return send_file(
            report_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=f"sleep_staging_research_report_{language}.docx",
            max_age=0,
        )

    def _report_request():
        body = request.get_json(silent=True) or {}
        session_id = str(body.get("session_id", ""))
        if not session_id:
            raise SafeWebError("SESSION_EXPIRED", status=404)
        language = "zh" if body.get("language") == "zh" else "en"
        return RESULTS.get(session_id), language

    @app.get("/api/qr")
    def qr_code():
        base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
        if not base_url:
            base_url = request.url_root.rstrip("/")
        target = f"{base_url}/mobile"
        image = qrcode.make(target, border=2, box_size=8)
        output = io.BytesIO()
        image.save(output, format="PNG")
        output.seek(0)
        response = send_file(output, mimetype="image/png", max_age=0)
        response.headers["X-QR-Target"] = target
        return response

    @app.get("/api/health")
    def health():
        load_model()
        return jsonify(
            {
                "status": "ok",
                "model_id": model_id(),
                "input": "Raw Epoch CSV only",
                "classes": ["Wake", "NREM", "REM"],
            }
        )

    @app.errorhandler(SafeWebError)
    def handle_safe_error(error):
        return jsonify({"ok": False, "error_code": error.code, "details": error.details}), error.status

    @app.errorhandler(RequestEntityTooLarge)
    def handle_too_large(_error):
        return (
            jsonify(
                {
                    "ok": False,
                    "error_code": "FILE_TOO_LARGE",
                    "details": {"max_mb": MAX_FILE_BYTES // (1024 * 1024)},
                }
            ),
            413,
        )

    @app.errorhandler(404)
    def handle_not_found(_error):
        return jsonify({"ok": False, "error_code": "NOT_FOUND", "details": {}}), 404

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        if app.testing:
            raise error
        return jsonify({"ok": False, "error_code": "INTERNAL_ERROR", "details": {}}), 500

    return app


app = create_app()


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "7860"))
    app.run(host=host, port=port, debug=False)
