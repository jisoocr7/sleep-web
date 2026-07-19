import io
import zipfile


def _upload(client, sample_bytes, consent="true", filename="night.csv"):
    return client.post(
        "/api/upload",
        data={
            "privacy_ack": consent,
            "language": "en",
            "file": (io.BytesIO(sample_bytes), filename),
        },
        headers={"X-Privacy-Ack": consent},
        content_type="multipart/form-data",
    )


def test_privacy_ack_is_enforced_by_server(client, sample_bytes):
    response = _upload(client, sample_bytes, consent="false")
    assert response.status_code == 403
    assert response.get_json()["error_code"] == "CONSENT_REQUIRED"


def test_upload_returns_complete_consistent_timeline(client, sample_bytes):
    response = _upload(client, sample_bytes)
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert data["model"]["id"] == "af0f2cb49980"
    assert data["summary"]["input_epochs"] == 961
    assert data["summary"]["analyzed_epochs"] == 957
    assert len(data["timeline"]["stages"]) == 957
    assert len(data["timeline"]["times_seconds"]) == 957
    assert sum(item["count"] for item in data["summary"]["stage_summary"].values()) == 957


def test_consumer_export_extension_cannot_enter_prediction(client, sample_bytes):
    response = _upload(client, sample_bytes, filename="apple_health.xml")
    assert response.status_code == 415
    assert response.get_json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_reports_are_evidence_focused_and_deidentified(client, sample_bytes):
    upload = _upload(client, sample_bytes, filename="Patient_Weihao_001.csv").get_json()
    session_id = upload["session_id"]

    html_response = client.post("/api/report/html", json={"session_id": session_id, "language": "en"})
    assert html_response.status_code == 200
    html_text = html_response.data.decode("utf-8")
    assert "Patient_Weihao_001" not in html_text
    assert "Quality: Poor" not in html_text
    assert "sleep score" not in html_text.lower()
    assert "normal range" not in html_text.lower()
    assert "Research use only" in html_text
    assert "Complete predicted hypnogram" in html_text

    docx_response = client.post("/api/report/docx", json={"session_id": session_id, "language": "en"})
    assert docx_response.status_code == 200
    assert docx_response.data[:2] == b"PK"
    with zipfile.ZipFile(io.BytesIO(docx_response.data)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "Patient_Weihao_001" not in document_xml
    assert "Quality: Poor" not in document_xml
    assert "Research use only" in document_xml


def test_chinese_reports_use_the_same_evidence_only_payload(client, sample_bytes):
    upload = _upload(client, sample_bytes).get_json()
    session_id = upload["session_id"]

    html_response = client.post("/api/report/html", json={"session_id": session_id, "language": "zh"})
    assert html_response.status_code == 200
    html_text = html_response.data.decode("utf-8")
    assert "可穿戴睡眠分期研究原型" in html_text
    assert "仅供研究使用" in html_text

    docx_response = client.post("/api/report/docx", json={"session_id": session_id, "language": "zh"})
    assert docx_response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(docx_response.data)) as archive:
        document_xml = archive.read("word/document.xml").decode("utf-8")
    assert "可穿戴睡眠分期研究原型" in document_xml
    assert "仅供研究使用" in document_xml


def test_sample_template_qr_and_health_routes(client):
    assert client.get("/api/sample-data/raw").status_code == 200
    template = client.get("/api/schema-template")
    assert template.status_code == 200
    assert b"acc_mean,acc_std" in template.data
    qr = client.get("/api/qr")
    assert qr.status_code == 200
    assert qr.data.startswith(b"\x89PNG")
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.get_json()["status"] == "ok"
