"""End-to-end visual and interaction QA for the local safe prototype."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = os.environ.get("SAFE_WEB_BASE_URL", "http://127.0.0.1:7860")
CHROME_PATH = Path(os.environ.get("CHROME_PATH", r"C:\Program Files\Google\Chrome\Application\chrome.exe"))
SCREENSHOT_DIR = PROJECT_ROOT / "artifacts" / "screenshots"
REPORT_DIR = PROJECT_ROOT / "artifacts" / "reports"
SAMPLE_PATH = PROJECT_ROOT / "examples" / "sample_raw_epoch.csv"
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")


def visible_text_without_language_switch(page) -> str:
    return page.evaluate(
        """() => {
          const clone = document.body.cloneNode(true);
          const language = clone.querySelector('#languageButton');
          if (language) language.remove();
          return clone.innerText;
        }"""
    )


def assert_english_visible(page) -> None:
    text = visible_text_without_language_switch(page)
    matches = sorted(set(CJK_PATTERN.findall(text)))
    assert not matches, f"Visible Chinese remained in English mode: {matches[:12]}"


def record_console(findings, message) -> None:
    if message.type == "error":
        findings["console_errors"].append({"text": message.text, "location": message.location})


def main() -> None:
    if not CHROME_PATH.exists():
        raise FileNotFoundError(f"Chrome not found: {CHROME_PATH}")

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    findings = {
        "desktop": {},
        "mobile": {},
        "console_errors": [],
        "page_errors": [],
        "http_errors": [],
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(CHROME_PATH))
        try:
            desktop = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, accept_downloads=True)
            page = desktop.new_page()
            page.on("console", lambda message: record_console(findings, message))
            page.on("pageerror", lambda error: findings["page_errors"].append(str(error)))
            page.on("response", lambda response: findings["http_errors"].append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
            requests = []
            page.on("request", lambda request: requests.append((request.method, request.url)))

            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            assert page.locator("#pageTitle").inner_text() == "Wearable Sleep Staging Research Prototype"
            assert_english_visible(page)

            page.locator("#fileInput").set_input_files(str(SAMPLE_PATH))
            uploads_before = [item for item in requests if item[1].endswith("/api/upload")]
            page.locator("#analyzeButton").click()
            page.wait_for_timeout(250)
            uploads_after = [item for item in requests if item[1].endswith("/api/upload")]
            assert uploads_after == uploads_before
            assert "privacy confirmation" in page.locator("#statusMessage").inner_text()

            page.locator("#privacyAck").check()
            with page.expect_response(lambda response: response.url.endswith("/api/upload") and response.request.method == "POST") as upload_info:
                page.locator("#analyzeButton").click()
            upload_payload = upload_info.value.json()
            page.locator("#results:not([hidden])").wait_for(state="visible")
            assert upload_payload["summary"]["analyzed_epochs"] == 957
            assert page.locator("#inputEpochs").inner_text() == "961"
            assert page.locator("#analyzedEpochs").inner_text() == "957"
            assert page.locator("#stageGrid .stage-item").count() == 3
            assert page.locator("#hypnogramChart path").count() == 1
            assert page.locator("#hypnogramChart path").get_attribute("d").count("H") == 956
            assert_english_visible(page)

            page.screenshot(path=str(SCREENSHOT_DIR / "submission_safe_desktop_en.png"), full_page=True)
            page.locator("#results").screenshot(path=str(SCREENSHOT_DIR / "Figure_S2_submission_safe_web_results.png"))

            with page.expect_download() as html_download:
                page.locator("#htmlReportButton").click()
            html_download.value.save_as(str(REPORT_DIR / "example_report_en.html"))
            with page.expect_download() as docx_download:
                page.locator("#docxReportButton").click()
            docx_download.value.save_as(str(REPORT_DIR / "example_report_en.docx"))

            page.locator("#qrButton").click()
            page.locator("#qrDialog").wait_for(state="visible")
            qr_loaded = page.locator("#qrDialog img").evaluate("img => img.complete && img.naturalWidth > 0")
            assert qr_loaded
            page.locator("#closeQrButton").click()

            page.locator("#languageButton").click()
            assert page.locator("#pageTitle").inner_text() == "可穿戴睡眠分期研究原型"
            assert CJK_PATTERN.search(page.locator("#statusMessage").inner_text())
            page.locator("#languageButton").click()
            assert_english_visible(page)

            findings["desktop"] = {
                "input_epochs": upload_payload["summary"]["input_epochs"],
                "analyzed_epochs": upload_payload["summary"]["analyzed_epochs"],
                "timeline_points": len(upload_payload["timeline"]["stages"]),
                "body_scroll_width": page.evaluate("document.body.scrollWidth"),
                "viewport_width": page.evaluate("window.innerWidth"),
            }
            desktop.close()

            mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, accept_downloads=True)
            mobile_page = mobile.new_page()
            mobile_page.on("console", lambda message: record_console(findings, message))
            mobile_page.on("pageerror", lambda error: findings["page_errors"].append(str(error)))
            mobile_page.on("response", lambda response: findings["http_errors"].append({"status": response.status, "url": response.url}) if response.status >= 400 else None)
            mobile_page.goto(f"{BASE_URL}/mobile", wait_until="networkidle")
            assert mobile_page.locator("#qrButton").is_hidden()
            assert mobile_page.locator("#fileInput").get_attribute("capture") is None
            assert "user-scalable=no" not in mobile_page.locator('meta[name="viewport"]').get_attribute("content")
            upload_box = mobile_page.locator(".upload-card").bounding_box()
            sample_box = mobile_page.locator(".sample-card").bounding_box()
            assert upload_box and sample_box and upload_box["y"] < sample_box["y"]
            assert_english_visible(mobile_page)

            with mobile_page.expect_response(lambda response: response.url.endswith("/api/upload")):
                mobile_page.locator("#runSampleButton").click()
            mobile_page.locator("#results:not([hidden])").wait_for(state="visible")
            assert mobile_page.locator("#analyzedEpochs").inner_text() == "957"
            body_width = mobile_page.evaluate("document.body.scrollWidth")
            viewport_width = mobile_page.evaluate("window.innerWidth")
            assert body_width <= viewport_width
            assert_english_visible(mobile_page)
            mobile_page.screenshot(path=str(SCREENSHOT_DIR / "submission_safe_mobile_en.png"), full_page=True)

            findings["mobile"] = {
                "body_scroll_width": body_width,
                "viewport_width": viewport_width,
                "upload_before_sample": True,
                "analyzed_epochs": 957,
            }
            mobile.close()
        finally:
            browser.close()

    assert not findings["console_errors"], {"console": findings["console_errors"], "http": findings["http_errors"]}
    assert not findings["page_errors"], findings["page_errors"]
    (PROJECT_ROOT / "artifacts" / "browser_qa.json").write_text(
        json.dumps(findings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(findings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
