window.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("#upload-form");
  const fileInput = document.querySelector("#file-input");
  const dropZone = document.querySelector("#drop-zone");
  const fileCard = document.querySelector("#file-card");
  const filePreview = document.querySelector("#file-preview");
  const fileName = document.querySelector("#file-name");
  const fileSize = document.querySelector("#file-size");
  const clearFile = document.querySelector("#clear-file");
  const analyzeButton = document.querySelector("#analyze-button");
  const statusPill = document.querySelector("#status-pill");
  const reportCard = document.querySelector("#report-card");
  const reportTemplate = document.querySelector("#report-template");
  const copyJson = document.querySelector("#copy-json");
  const demoFill = document.querySelector("#demo-fill");

  if (
    !form ||
    !fileInput ||
    !dropZone ||
    !fileCard ||
    !filePreview ||
    !fileName ||
    !fileSize ||
    !clearFile ||
    !analyzeButton ||
    !statusPill ||
    !reportCard ||
    !reportTemplate ||
    !copyJson ||
    !demoFill
  ) {
    return;
  }

  document.body.classList.add("js-ready");

  const maxBytes = 100 * 1024 * 1024;
  const allowedExtensions = [".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".mkv", ".webm"];
  let selectedFile = null;
  let lastReport = null;

  const demoReport = {
    label: "uncertain",
    risk_score: 38,
    confidence: "medium",
    summary:
      "The media shows a few ambiguous visual anomalies, but nothing strong enough to treat as definitive manipulation proof.",
    evidence: [
      {
        category: "Skin texture",
        finding: "Facial texture appears slightly smoothed in high-detail regions.",
        severity: "medium",
        timestamp: null,
      },
      {
        category: "Compression",
        finding: "Visible compression may explain some edge softness and should be treated as a false-positive risk.",
        severity: "low",
        timestamp: null,
      },
    ],
    limitations: [
      "Single-image analysis cannot prove authenticity.",
      "Low resolution and compression can mimic manipulation artifacts.",
      "The result is model-assisted screening, not forensic proof.",
    ],
    recommended_next_steps: [
      "Compare with the original source file if available.",
      "Check provenance, metadata, and upload history.",
      "Use expert forensic review for high-stakes decisions.",
    ],
  };

  function formatBytes(bytes) {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function getExtension(name) {
    const dot = name.lastIndexOf(".");
    return dot === -1 ? "" : name.slice(dot).toLowerCase();
  }

  function setStatus(text, tone = "ready") {
    statusPill.textContent = text;
    statusPill.dataset.tone = tone;
  }

  function showToast(message) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.remove(), 3600);
  }

  function setSelectedFile(file) {
    const extension = getExtension(file.name);
    if (!allowedExtensions.includes(extension)) {
      showToast("Unsupported file type. Use JPG, PNG, WEBP, MP4, MOV, MKV, or WEBM.");
      return;
    }
    if (file.size > maxBytes) {
      showToast("File is larger than the 100 MB upload limit.");
      return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    fileCard.hidden = false;
    analyzeButton.disabled = false;
    setStatus("Loaded");

    if (file.type.startsWith("image/")) {
      const previewUrl = URL.createObjectURL(file);
      filePreview.style.backgroundImage = `url("${previewUrl}")`;
    } else {
      filePreview.style.backgroundImage = "";
    }
  }

  function resetFile() {
    selectedFile = null;
    fileInput.value = "";
    fileCard.hidden = true;
    analyzeButton.disabled = true;
    filePreview.style.backgroundImage = "";
    setStatus("Ready");
  }

  function classForLabel(label) {
    if (label === "likely_authentic") return "is-low";
    if (label === "uncertain") return "is-mid";
    return "is-high";
  }

  function prettyLabel(label) {
    return label.replaceAll("_", " ");
  }

  function renderStack(container, items, mapper) {
    container.innerHTML = "";
    if (!items || items.length === 0) {
      const empty = document.createElement("div");
      empty.className = "report-item";
      empty.innerHTML = "<p>No items returned.</p>";
      container.appendChild(empty);
      return;
    }

    items.forEach((item) => {
      const node = document.createElement("div");
      node.className = "report-item";
      node.innerHTML = mapper(item);
      container.appendChild(node);
    });
  }

  function renderReport(report) {
    lastReport = report;
    copyJson.disabled = false;
    reportCard.className = "report-card";
    reportCard.innerHTML = "";
    reportCard.appendChild(reportTemplate.content.cloneNode(true));

    const score = Number(report.risk_score || 0);
    const scoreRing = reportCard.querySelector("#score-ring");
    const riskScore = reportCard.querySelector("#risk-score");
    const labelBadge = reportCard.querySelector("#label-badge");
    const confidenceBadge = reportCard.querySelector("#confidence-badge");
    const summary = reportCard.querySelector("#report-summary");

    scoreRing.style.setProperty("--score", `${Math.max(0, Math.min(score, 100)) * 3.6}deg`);
    riskScore.textContent = score;
    labelBadge.textContent = prettyLabel(report.label || "uncertain");
    labelBadge.classList.add(classForLabel(report.label));
    confidenceBadge.textContent = `${report.confidence || "low"} confidence`;
    summary.textContent = report.summary || "No summary returned.";

    renderStack(reportCard.querySelector("#evidence-list"), report.evidence, (item) => {
      const timestamp = item.timestamp ? ` · ${item.timestamp}` : "";
      return `
        <strong>${item.category}<span class="severity">${item.severity}${timestamp}</span></strong>
        <p>${item.finding}</p>
      `;
    });

    renderStack(reportCard.querySelector("#limitations-list"), report.limitations, (item) => `<p>${item}</p>`);
    renderStack(
      reportCard.querySelector("#steps-list"),
      report.recommended_next_steps,
      (item) => `<p>${item}</p>`,
    );

    reportCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function analyzeSelectedFile() {
    if (!selectedFile) return;

    const body = new FormData();
    body.append("file", selectedFile);

    analyzeButton.disabled = true;
    setStatus("Analyzing");
    analyzeButton.innerHTML = '<span class="plus" aria-hidden="true">+</span> Analyzing...';

    try {
      const response = await fetch("/analyze", {
        method: "POST",
        body,
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Analysis failed.");
      }
      renderReport(data);
      setStatus("Complete");
    } catch (error) {
      showToast(error.message || "Analysis failed.");
      setStatus("Error");
    } finally {
      analyzeButton.disabled = false;
      analyzeButton.innerHTML = '<span class="plus" aria-hidden="true">+</span> Run analysis';
    }
  }

  fileInput.addEventListener("change", () => {
    const [file] = fileInput.files;
    if (file) setSelectedFile(file);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("is-dragover");
    });
  });

  dropZone.addEventListener("drop", (event) => {
    const [file] = event.dataTransfer.files;
    if (file) setSelectedFile(file);
  });

  clearFile.addEventListener("click", resetFile);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    analyzeSelectedFile();
  });

  copyJson.addEventListener("click", async () => {
    if (!lastReport) return;
    await navigator.clipboard.writeText(JSON.stringify(lastReport, null, 2));
    showToast("Report JSON copied.");
  });

  demoFill.addEventListener("click", () => renderReport(demoReport));
});
