from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_submission_runtime_excludes_unsafe_features():
    runtime_files = [
        PROJECT_ROOT / "server.py",
        PROJECT_ROOT / "templates" / "index.html",
        PROJECT_ROOT / "static" / "app.js",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in runtime_files)
    assert "AutoSleep" not in combined
    assert "Sleep Cycle" not in combined
    assert "Apple Health" not in combined
    assert "api/detect-format" not in combined
    assert "api/convert" not in combined
    assert "[:200]" not in combined


def test_mobile_upload_is_accessible_and_not_camera_capture():
    template = (PROJECT_ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'type="date"' not in template
    assert "capture=" not in template
    assert 'id="privacyAck" type="checkbox" checked' not in template
    assert 'name="viewport" content="width=device-width, initial-scale=1"' in template
    assert 'for="fileInput"' in template
