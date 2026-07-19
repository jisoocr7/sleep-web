# BSPC Submission-Safe Web Prototype

Independent local research prototype for deterministic three-class wearable sleep staging. The original `0529\sleep_web_mvp` project and the live PythonAnywhere site are not modified.

## Scope

- Raw Epoch CSV only.
- One subject and one night per file.
- Nine measured base features per 30-second epoch.
- Fixed HGB model with offline `+/-2` epoch context.
- Complete Wake/NREM/REM timeline; no 200-epoch truncation.
- Evidence-focused HTML and DOCX reports.
- Shared English/Chinese desktop and phone workflow.
- Research use only; not for diagnosis or clinical decision-making.

Apple Health, AutoSleep, Sleep Cycle, synthetic feature generation, sleep scores, health grades, normal ranges, and advice are intentionally excluded from this runtime.

## Run Locally

From this folder:

```powershell
.\run_local.ps1
```

Open:

- Desktop: `http://127.0.0.1:7860/`
- Phone layout on the same computer: `http://127.0.0.1:7860/mobile`

For a phone on the same Wi-Fi network:

```powershell
.\run_local.ps1 -AllowLan
```

The script prints the LAN phone URL and configures the QR code to use it. Windows Firewall may ask for permission on the selected local network.

## Raw Epoch Contract

Required finite numeric columns:

```text
acc_mean, acc_std, acc_min, acc_max,
hr_mean, hr_std, hr_min, hr_max,
steps_sum
```

Optional ordering columns are `t` or `timestamp`; `subject_id` is accepted only to verify that the file contains one subject, then discarded. Unknown extra columns are ignored and reported. Missing values, infinite values, non-numeric values, multiple subjects, inconsistent min/mean/max values, and non-30-second time intervals are rejected.

Files:

- `examples/sample_raw_epoch.csv`: fixed 961-epoch research sample without a subject identifier.
- `examples/raw_epoch_template.csv`: blank schema header.
- `examples/SOURCE_AND_LICENSE.md`: sample provenance and attribution.
- `examples/Sleep-Accel_LICENSE.txt`: official ODC Attribution License v1.0 text.
- `models/hgb_context_model.pkl`: strict 25,017-epoch full-data HGB context model, SHA-256 `af0f2cb499804f550ba54cefc93d919ecc207d531cce53bee8c834b3678d0971` (model ID `af0f2cb49980`).
- `models/feature_schema.json`: the same ordered 45-feature schema used by the research-data deposit.

The context model excludes the first and last two rows because they do not have complete `+/-2` epoch context. The fixed sample therefore produces 957 analyzed epochs.

The model binary and feature order are byte-for-byte synchronized with `06_research_data_deposit/models`. The runtime is locked to NumPy 2.4.4, pandas 2.3.3 and scikit-learn 1.8.0; the fixed sample prediction SHA-256 is `fb8bdb4a0f376e1eae6ce9f71a621a4160bb4e3125a78d356e53295f3e839097`.

The fixed sample contains de-identified derived features from Sleep-Accel, PhysioNet version 1.0.0, DOI `10.13026/hmhs-py35`. The source files are distributed under the Open Data Commons Attribution License v1.0; attribution and the official license text are included with this prototype.

## Privacy Behavior

- Selecting a file does not trigger a network request.
- The privacy checkbox is empty by default.
- Analyze sends both a consent request header and form field; the server checks the header before parsing multipart data.
- Raw CSV bytes, original filename, and subject identifier are not persisted.
- Only non-identifying prediction results are held in memory for 30 minutes for report generation.

## Verification

Run unit and API tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run desktop and phone browser QA with installed Google Chrome:

```powershell
powershell -ExecutionPolicy Bypass -File .\tests\run_browser_qa.ps1
```

Verified outputs are under `artifacts`:

- `screenshots/submission_safe_desktop_en.png`
- `screenshots/submission_safe_mobile_en.png`
- `screenshots/Figure_S2_submission_safe_web_results.png`
- `reports/example_report_en.html`
- `reports/example_report_en.docx`
- `browser_qa.json`

## License

Copyright (c) 2026 Zhengru Xie. The website source code is licensed under the [MIT License](LICENSE).

The fixed sample data are distributed separately under the Open Data Commons Attribution License v1.0; see `examples/SOURCE_AND_LICENSE.md` and `examples/Sleep-Accel_LICENSE.txt`. The MIT License does not replace the licenses or terms that apply to the sample data, trained model, or other third-party materials.
