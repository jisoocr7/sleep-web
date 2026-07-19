"use strict";

const I18N = {
  en: {
    document_title: "Wearable Sleep Staging Research Prototype",
    skip: "Skip to the analysis workspace",
    brand_aria: "Wearable Sleep Staging Research Prototype",
    brand: "Sleep staging research prototype",
    brand_sub: "Deterministic offline inference",
    phone_upload: "Phone upload",
    language_aria: "Switch language",
    eyebrow: "Submission-safe research interface",
    page_title: "Wearable Sleep Staging Research Prototype",
    page_intro: "Analyze one night of real 30-second wearable epochs with the fixed three-class HGB context model.",
    protocol_aria: "Model protocol",
    protocol_offline: "Offline inference",
    protocol_epoch: "30-s epochs",
    protocol_research: "Research use only",
    input_aria: "Data input",
    fixed_sample: "Fixed research sample",
    sample_title: "Run the reproducible Raw Epoch example",
    sample_desc: "A single-night file with measured epoch features, no missing values, and no subject identifier.",
    sample_source: "De-identified derived features from",
    deterministic: "Deterministic",
    sample_rows: "Input epochs",
    sample_window: "Recording window",
    sample_fields: "Feature fields",
    run_sample: "Run fixed sample",
    own_data: "Your single-night data",
    upload_title: "Upload a Raw Epoch CSV",
    upload_desc: "Each row must represent one consecutive 30-second epoch. Other consumer-export formats are not converted.",
    choose_file: "Choose CSV file",
    no_file: "No file selected",
    requirements: "Required data fields",
    requirements_desc: "All nine values must be finite numeric measurements for every epoch.",
    download_template: "Download CSV template",
    privacy: "I understand that the selected CSV is transmitted only after I choose Analyze. The raw file, filename, and subject identifier are not retained.",
    analyze: "Analyze selected CSV",
    prediction_output: "Model prediction output",
    results_title: "Complete single-night result",
    results_desc: "Every summary below is computed from the same complete analyzed epoch sequence.",
    model_id: "Model ID",
    stamp_research: "Research use only",
    epoch_counts_aria: "Epoch counts",
    input_epochs: "Input epochs",
    analyzed_epochs: "Analyzed epochs",
    analyzed_duration: "Analyzed duration",
    stage_summary: "Predicted stage summary",
    denominator: "Percentages use all analyzed epochs as the denominator.",
    hypnogram: "Complete predicted hypnogram",
    hypnogram_note: "No first-200-epoch truncation",
    hypnogram_aria: "Complete predicted Wake, NREM, and REM hypnogram",
    metrics: "Model-derived exploratory metrics",
    metric_tst: "Predicted total sleep time",
    metric_sleep_prop: "Predicted sleep proportion",
    metric_waso: "Predicted WASO-like duration",
    derived_notice: "Derived solely from model-predicted Wake/NREM/REM labels; not independently validated clinical sleep measures.",
    reports: "Evidence-focused report",
    reports_desc: "Reports contain predictions, the complete hypnogram, model-derived metrics, and research limitations only.",
    download_html: "Download HTML",
    download_docx: "Download DOCX",
    boundaries: "Interpretation boundaries",
    limitations: "Research limitations",
    limit_three: "Three-class Wake/NREM/REM output; not five-stage AASM staging.",
    limit_offline: "Offline context uses two preceding and two following epochs.",
    limit_training: "No online training, tuning, calibration, or clinical diagnostic function.",
    limit_transfer: "Cross-device generalization is limited and results must not guide clinical decisions.",
    footer_main: "Research use only.",
    footer_sub: "Not for diagnosis or clinical decision-making.",
    phone_entry: "Phone entry",
    qr_title: "Open the same safe workflow on a phone",
    close: "Close",
    qr_alt: "QR code for the phone upload page",
    qr_note: "For local phone testing, open this site through the computer's LAN address before scanning.",
    elapsed_time: "Elapsed time",
    chart_description: "A complete offline three-class prediction trace across all analyzed epochs.",
    epochs: "epochs",
    minutes: "min",
    status_sample_loading: "Loading the fixed research sample...",
    status_analyzing: "Validating Raw Epoch data and running deterministic offline inference...",
    status_complete: "Analysis complete. The complete epoch sequence is shown below.",
    status_report: "Preparing the evidence-focused report...",
    status_report_ready: "Report ready.",
    error_CONSENT_REQUIRED: "Select the privacy confirmation before analyzing your CSV.",
    error_FILE_REQUIRED: "Choose one Raw Epoch CSV file.",
    error_FILE_TOO_LARGE: "The CSV is larger than the 10 MB limit.",
    error_UNSUPPORTED_FILE_TYPE: "Only a .csv Raw Epoch file is accepted.",
    error_CSV_ENCODING_INVALID: "Save the CSV as UTF-8 and try again.",
    error_CSV_PARSE_FAILED: "The file could not be parsed as a CSV.",
    error_MISSING_COLUMNS: "The CSV is missing required feature columns: {columns}.",
    error_NON_NUMERIC_VALUES: "A required feature contains non-numeric values.",
    error_MISSING_VALUES: "A required feature contains missing values. The safe prototype does not fill or synthesize them.",
    error_NON_FINITE_VALUES: "A required feature contains infinite values.",
    error_MULTIPLE_SUBJECTS: "Upload one subject and one night per CSV.",
    error_TIME_INTERVAL_INVALID: "The t or timestamp sequence must advance in consecutive 30-second intervals.",
    error_RECORDING_TOO_LONG: "The recording spans more than 24 hours.",
    error_INSUFFICIENT_EPOCHS: "At least five consecutive epochs are required for the offline context model.",
    error_INVALID_FEATURE_RANGE: "The file contains impossible feature ranges or inconsistent min/mean/max values.",
    error_PREDICTION_FAILED: "Prediction could not be completed with the fixed model.",
    error_SESSION_EXPIRED: "The temporary result expired. Run the analysis again before downloading a report.",
    error_INTERNAL_ERROR: "The analysis service encountered an internal error.",
    error_NETWORK: "The local analysis service could not be reached.",
  },
  zh: {
    document_title: "可穿戴睡眠分期研究原型",
    skip: "跳转到分析工作区",
    brand_aria: "可穿戴睡眠分期研究原型",
    brand: "睡眠分期研究原型",
    brand_sub: "确定性离线推理",
    phone_upload: "手机上传",
    language_aria: "切换语言",
    eyebrow: "投稿安全研究界面",
    page_title: "可穿戴睡眠分期研究原型",
    page_intro: "使用固定的三分类 HGB 上下文模型，分析一晚真实的 30 秒可穿戴 epoch 数据。",
    protocol_aria: "模型协议",
    protocol_offline: "离线推理",
    protocol_epoch: "30 秒 epoch",
    protocol_research: "仅供研究使用",
    input_aria: "数据输入",
    fixed_sample: "固定研究样例",
    sample_title: "运行可复现的 Raw Epoch 样例",
    sample_desc: "单夜实测 epoch 特征文件，不含缺失值和受试者标识符。",
    sample_source: "去标识化派生特征来源：",
    deterministic: "结果固定",
    sample_rows: "输入 epoch",
    sample_window: "记录窗口",
    sample_fields: "特征字段",
    run_sample: "运行固定样例",
    own_data: "你的单夜数据",
    upload_title: "上传 Raw Epoch CSV",
    upload_desc: "每行必须代表一个连续的 30 秒 epoch；本版本不转换其他消费者应用导出格式。",
    choose_file: "选择 CSV 文件",
    no_file: "尚未选择文件",
    requirements: "必要数据字段",
    requirements_desc: "每个 epoch 的 9 个字段都必须是有限的数值测量。",
    download_template: "下载 CSV 模板",
    privacy: "我理解：只有点击“分析”后才会传输所选 CSV；原始文件、文件名和受试者标识符不会被保留。",
    analyze: "分析所选 CSV",
    prediction_output: "模型预测输出",
    results_title: "完整单夜结果",
    results_desc: "下列所有汇总均来自同一个完整的分析 epoch 序列。",
    model_id: "模型 ID",
    stamp_research: "仅供研究使用",
    epoch_counts_aria: "Epoch 数量",
    input_epochs: "输入 epoch",
    analyzed_epochs: "分析 epoch",
    analyzed_duration: "分析时长",
    stage_summary: "预测阶段汇总",
    denominator: "百分比均以全部分析 epoch 为分母。",
    hypnogram: "完整预测睡眠阶段图",
    hypnogram_note: "不截取前 200 个 epoch",
    hypnogram_aria: "完整预测 Wake、NREM 和 REM 睡眠阶段图",
    metrics: "模型派生的探索性指标",
    metric_tst: "预测总睡眠时间",
    metric_sleep_prop: "预测睡眠占比",
    metric_waso: "预测 WASO-like 时长",
    derived_notice: "以下结果仅由模型预测的 Wake/NREM/REM 标签派生，并非经过独立验证的临床睡眠指标。",
    reports: "证据型结果报告",
    reports_desc: "报告仅包含预测、完整睡眠阶段图、模型派生指标和研究限制。",
    download_html: "下载 HTML",
    download_docx: "下载 DOCX",
    boundaries: "解释边界",
    limitations: "研究限制",
    limit_three: "仅输出 Wake/NREM/REM 三分类，不是 AASM 五阶段睡眠分期。",
    limit_offline: "离线上下文使用前后各 2 个 epoch。",
    limit_training: "不进行在线训练、调参、校准或临床诊断。",
    limit_transfer: "跨设备泛化能力有限，结果不得用于临床决策。",
    footer_main: "仅供研究使用。",
    footer_sub: "不用于诊断或临床决策。",
    phone_entry: "手机入口",
    qr_title: "在手机上打开同一套安全流程",
    close: "关闭",
    qr_alt: "手机上传页面二维码",
    qr_note: "本地手机测试时，请先通过电脑的局域网地址打开本站，再扫描二维码。",
    elapsed_time: "经过时间",
    chart_description: "覆盖全部分析 epoch 的完整离线三分类预测轨迹。",
    epochs: "个 epoch",
    minutes: "分钟",
    status_sample_loading: "正在加载固定研究样例……",
    status_analyzing: "正在验证 Raw Epoch 数据并运行确定性离线推理……",
    status_complete: "分析完成，下方展示完整 epoch 序列。",
    status_report: "正在生成证据型结果报告……",
    status_report_ready: "报告已生成。",
    error_CONSENT_REQUIRED: "分析 CSV 前请主动勾选隐私确认。",
    error_FILE_REQUIRED: "请选择一个 Raw Epoch CSV 文件。",
    error_FILE_TOO_LARGE: "CSV 超过 10 MB 限制。",
    error_UNSUPPORTED_FILE_TYPE: "仅接受 .csv Raw Epoch 文件。",
    error_CSV_ENCODING_INVALID: "请将 CSV 保存为 UTF-8 编码后重试。",
    error_CSV_PARSE_FAILED: "无法将该文件解析为 CSV。",
    error_MISSING_COLUMNS: "CSV 缺少必要特征列：{columns}。",
    error_NON_NUMERIC_VALUES: "必要特征中存在非数值内容。",
    error_MISSING_VALUES: "必要特征中存在缺失值；投稿安全版不会填补或合成这些值。",
    error_NON_FINITE_VALUES: "必要特征中存在无穷值。",
    error_MULTIPLE_SUBJECTS: "每个 CSV 只能包含一个受试者的一晚数据。",
    error_TIME_INTERVAL_INVALID: "t 或 timestamp 必须按连续 30 秒递增。",
    error_RECORDING_TOO_LONG: "记录跨度超过 24 小时。",
    error_INSUFFICIENT_EPOCHS: "离线上下文模型至少需要 5 个连续 epoch。",
    error_INVALID_FEATURE_RANGE: "文件中存在不可能的特征范围或不一致的最小值、均值和最大值。",
    error_PREDICTION_FAILED: "固定模型未能完成预测。",
    error_SESSION_EXPIRED: "临时结果已过期，请重新分析后再下载报告。",
    error_INTERNAL_ERROR: "分析服务发生内部错误。",
    error_NETWORK: "无法连接本地分析服务。",
  },
};

const state = {
  language: localStorage.getItem("safeSleepLanguage") === "zh" ? "zh" : "en",
  selectedFile: null,
  sessionId: null,
  lastResult: null,
  lastStatus: null,
};

const elements = {
  languageButton: document.getElementById("languageButton"),
  qrButton: document.getElementById("qrButton"),
  qrDialog: document.getElementById("qrDialog"),
  closeQrButton: document.getElementById("closeQrButton"),
  fileInput: document.getElementById("fileInput"),
  selectedFileName: document.getElementById("selectedFileName"),
  privacyAck: document.getElementById("privacyAck"),
  analyzeButton: document.getElementById("analyzeButton"),
  runSampleButton: document.getElementById("runSampleButton"),
  statusMessage: document.getElementById("statusMessage"),
  results: document.getElementById("results"),
  modelId: document.getElementById("modelId"),
  inputEpochs: document.getElementById("inputEpochs"),
  analyzedEpochs: document.getElementById("analyzedEpochs"),
  analyzedDuration: document.getElementById("analyzedDuration"),
  stageGrid: document.getElementById("stageGrid"),
  chart: document.getElementById("hypnogramChart"),
  metricTst: document.getElementById("metricTst"),
  metricSleepProp: document.getElementById("metricSleepProp"),
  metricWaso: document.getElementById("metricWaso"),
  htmlReportButton: document.getElementById("htmlReportButton"),
  docxReportButton: document.getElementById("docxReportButton"),
};

function t(key) {
  return I18N[state.language][key] || I18N.en[key] || key;
}

function applyLanguage() {
  document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
  document.title = t("document_title");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAria));
  });
  document.querySelectorAll("[data-i18n-alt]").forEach((node) => {
    node.setAttribute("alt", t(node.dataset.i18nAlt));
  });
  elements.languageButton.textContent = state.language === "en" ? "Chinese" : "EN";
  if (state.selectedFile) {
    elements.selectedFileName.textContent = state.selectedFile.name;
  }
  if (state.lastResult) {
    renderResult(state.lastResult);
  }
  if (state.lastStatus) {
    showStatus(state.lastStatus.key, state.lastStatus.type, state.lastStatus.values);
  }
}

function showStatus(key, type = "info", values = {}) {
  let message = t(key);
  Object.entries(values).forEach(([name, value]) => {
    message = message.replace(`{${name}}`, String(value));
  });
  elements.statusMessage.textContent = message;
  elements.statusMessage.dataset.state = type;
  elements.statusMessage.hidden = false;
  state.lastStatus = { key, type, values };
}

function showError(error) {
  const code = error.code || "NETWORK";
  const values = {};
  if (error.details && Array.isArray(error.details.columns)) {
    values.columns = error.details.columns.join(", ");
  }
  showStatus(`error_${code}`, "error", values);
}

function setBusy(isBusy) {
  elements.runSampleButton.disabled = isBusy;
  elements.analyzeButton.disabled = isBusy;
  elements.htmlReportButton.disabled = isBusy;
  elements.docxReportButton.disabled = isBusy;
  document.body.setAttribute("aria-busy", String(isBusy));
}

async function responseJson(response) {
  let data = {};
  try {
    data = await response.json();
  } catch (_error) {
    throw { code: "NETWORK", details: {} };
  }
  if (!response.ok || !data.ok) {
    throw { code: data.error_code || "INTERNAL_ERROR", details: data.details || {} };
  }
  return data;
}

async function analyzeFile(file, privacyAck) {
  if (!file) {
    showError({ code: "FILE_REQUIRED" });
    return;
  }
  if (!privacyAck) {
    showError({ code: "CONSENT_REQUIRED" });
    return;
  }

  setBusy(true);
  showStatus("status_analyzing");
  const body = new FormData();
  body.append("privacy_ack", "true");
  body.append("language", state.language);
  body.append("file", file, file.name);

  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      headers: { "X-Privacy-Ack": "true" },
      body,
    });
    const data = await responseJson(response);
    state.sessionId = data.session_id;
    state.lastResult = data;
    renderResult(data);
    showStatus("status_complete");
    elements.results.hidden = false;
    elements.results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
}

async function runFixedSample() {
  setBusy(true);
  showStatus("status_sample_loading");
  try {
    const response = await fetch("/api/sample-data/raw", { cache: "no-store" });
    if (!response.ok) {
      throw { code: "NETWORK" };
    }
    const blob = await response.blob();
    const sample = new File([blob], "sample_raw_epoch.csv", { type: "text/csv" });
    setBusy(false);
    await analyzeFile(sample, true);
  } catch (error) {
    setBusy(false);
    showError(error);
  }
}

function renderResult(data) {
  const summary = data.summary;
  elements.modelId.textContent = data.model.id;
  elements.inputEpochs.textContent = summary.input_epochs.toLocaleString();
  elements.analyzedEpochs.textContent = summary.analyzed_epochs.toLocaleString();
  elements.analyzedDuration.textContent = `${summary.analyzed_duration_minutes.toFixed(1)} ${t("minutes")}`;

  elements.stageGrid.replaceChildren();
  ["Wake", "NREM", "REM"].forEach((stage) => {
    const item = summary.stage_summary[stage];
    const card = document.createElement("article");
    card.className = "stage-item";
    card.dataset.stage = stage;

    const name = document.createElement("span");
    name.className = "stage-name";
    name.textContent = stage;
    const main = document.createElement("strong");
    main.className = "stage-main";
    main.textContent = `${item.percent.toFixed(1)}%`;
    const detail = document.createElement("span");
    detail.className = "stage-detail";
    detail.textContent = `${item.count.toLocaleString()} ${t("epochs")} | ${item.minutes.toFixed(1)} ${t("minutes")}`;
    card.append(name, main, detail);
    elements.stageGrid.append(card);
  });

  const metrics = summary.derived_metrics;
  elements.metricTst.textContent = metrics.predicted_total_sleep_minutes.toFixed(1);
  elements.metricSleepProp.textContent = metrics.predicted_sleep_proportion_percent.toFixed(1);
  elements.metricWaso.textContent = metrics.predicted_waso_like_minutes.toFixed(1);
  drawHypnogram(data.timeline.stages, data.timeline.times_seconds);
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function drawHypnogram(stages, times) {
  const chart = elements.chart;
  chart.replaceChildren();
  if (!stages || !stages.length) {
    return;
  }

  const title = svgElement("title");
  title.textContent = t("hypnogram");
  const description = svgElement("desc");
  description.textContent = t("chart_description");
  chart.append(title, description);

  const compact = window.matchMedia("(max-width: 620px)").matches;
  const chartWidth = compact ? 760 : 1200;
  const chartHeight = compact ? 320 : 280;
  chart.setAttribute("viewBox", `0 0 ${chartWidth} ${chartHeight}`);
  const left = compact ? 92 : 105;
  const right = compact ? 735 : 1170;
  const bottom = compact ? 252 : 225;
  const yMap = compact ? { 0: 70, 1: 145, 2: 220 } : { 0: 62, 1: 128, 2: 194 };
  const stageNames = ["Wake", "NREM", "REM"];
  const stageColors = ["#c97258", "#5f9f87", "#6f70a8"];
  const x = (index) => left + (right - left) * (index / Math.max(stages.length - 1, 1));

  stageNames.forEach((stage, index) => {
    chart.append(
      svgElement("rect", {
        x: left,
        y: yMap[index] - (compact ? 31 : 27),
        width: right - left,
        height: compact ? 62 : 54,
        fill: stageColors[index],
        opacity: "0.08",
      }),
    );
    chart.append(
      svgElement("line", {
        x1: left,
        y1: yMap[index],
        x2: right,
        y2: yMap[index],
        stroke: "#cfd5d1",
        "stroke-width": "1",
      }),
    );
    const label = svgElement("text", {
      x: left - 14,
      y: yMap[index] + 5,
      "text-anchor": "end",
      fill: stageColors[index],
      "font-size": compact ? "21" : "18",
      "font-weight": "700",
      "font-family": "Aptos, Segoe UI, Arial, sans-serif",
    });
    label.textContent = stage;
    chart.append(label);
  });

  let pathData = `M ${x(0).toFixed(2)} ${yMap[stages[0]]}`;
  for (let index = 1; index < stages.length; index += 1) {
    pathData += ` H ${x(index).toFixed(2)} V ${yMap[stages[index]]}`;
  }
  chart.append(
    svgElement("path", {
      d: pathData,
      fill: "none",
      stroke: "#17372f",
      "stroke-width": "2.2",
      "stroke-linejoin": "round",
      "vector-effect": "non-scaling-stroke",
    }),
  );

  const firstTime = Number(times[0] || 0);
  const lastTime = Number(times[times.length - 1] || firstTime);
  const elapsedHours = Math.max(0, (lastTime - firstTime) / 3600);
  [0, 0.25, 0.5, 0.75, 1].forEach((fraction) => {
    const tickX = left + (right - left) * fraction;
    chart.append(
      svgElement("line", {
        x1: tickX,
        y1: bottom,
        x2: tickX,
        y2: bottom + 7,
        stroke: "#65736d",
        "stroke-width": "1",
      }),
    );
    const tick = svgElement("text", {
      x: tickX,
      y: bottom + (compact ? 30 : 28),
      "text-anchor": "middle",
      fill: "#53635c",
      "font-size": compact ? "16" : "14",
      "font-family": "Aptos, Segoe UI, Arial, sans-serif",
    });
    tick.textContent = `${(elapsedHours * fraction).toFixed(1)} h`;
    chart.append(tick);
  });

  const axisLabel = svgElement("text", {
    x: (left + right) / 2,
    y: bottom + (compact ? 58 : 52),
    "text-anchor": "middle",
    fill: "#34453e",
    "font-size": compact ? "17" : "15",
    "font-weight": "700",
    "font-family": "Aptos, Segoe UI, Arial, sans-serif",
  });
  axisLabel.textContent = `${t("elapsed_time")} (h)`;
  chart.append(axisLabel);
}

async function downloadReport(format) {
  if (!state.sessionId) {
    showError({ code: "SESSION_EXPIRED" });
    return;
  }
  setBusy(true);
  showStatus("status_report");
  try {
    const response = await fetch(`/api/report/${format}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId, language: state.language }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw { code: data.error_code || "INTERNAL_ERROR", details: data.details || {} };
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `sleep_staging_research_report_${state.language}.${format}`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showStatus("status_report_ready");
  } catch (error) {
    showError(error);
  } finally {
    setBusy(false);
  }
}

elements.languageButton.addEventListener("click", () => {
  state.language = state.language === "en" ? "zh" : "en";
  localStorage.setItem("safeSleepLanguage", state.language);
  applyLanguage();
});

elements.fileInput.addEventListener("change", () => {
  state.selectedFile = elements.fileInput.files && elements.fileInput.files[0] ? elements.fileInput.files[0] : null;
  elements.selectedFileName.textContent = state.selectedFile ? state.selectedFile.name : t("no_file");
});

elements.analyzeButton.addEventListener("click", () => analyzeFile(state.selectedFile, elements.privacyAck.checked));
elements.runSampleButton.addEventListener("click", runFixedSample);
elements.htmlReportButton.addEventListener("click", () => downloadReport("html"));
elements.docxReportButton.addEventListener("click", () => downloadReport("docx"));

elements.qrButton.addEventListener("click", () => {
  if (typeof elements.qrDialog.showModal === "function") {
    elements.qrDialog.showModal();
  } else {
    elements.qrDialog.setAttribute("open", "");
  }
});

elements.closeQrButton.addEventListener("click", () => elements.qrDialog.close());
elements.qrDialog.addEventListener("click", (event) => {
  if (event.target === elements.qrDialog) {
    elements.qrDialog.close();
  }
});

applyLanguage();
