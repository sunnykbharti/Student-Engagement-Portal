/* ==========================================================================
   AI CELL PROFESSOR ANALYTICS SUITE - FRONTEND JAVASCRIPT CONTROLLER
   ========================================================================== */

const API_BASE = "";

// Global App State
let appState = {
    isProcessing: false,
    pollTimer: null,
    editingStudentId: null,
    summaryData: [],
    rawTelemetry: [],
    timelineData: [],
    pedagogyData: {}
};

// Chart.js Instances
let timelineChart = null;
let barChartSummary = null;
let donutBehaviorChart = null;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    initCharts();
    checkServerStatus();
    loadDashboardData();
    setInterval(checkServerStatus, 5000);
});

// Tab Switcher
function switchTab(tabId, btnElement) {
    document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
    
    document.getElementById(tabId).classList.add("active");
    btnElement.classList.add("active");
}

// Handle Source Type Dropdown Change
function handleSourceTypeChange() {
    const type = document.getElementById("sourceType").value;
    const sampleGroup = document.getElementById("samplePickerGroup");
    const uploadGroup = document.getElementById("uploadGroup");
    const videoPlayer = document.getElementById("sampleVideoPlayer");

    if (type === "sample") {
        sampleGroup.classList.remove("hidden");
        uploadGroup.classList.add("hidden");
        const sampleFile = document.getElementById("sampleSelect").value;
        videoPlayer.src = sampleFile;
    } else if (type === "upload") {
        sampleGroup.classList.add("hidden");
        uploadGroup.classList.remove("hidden");
    } else if (type === "webcam") {
        sampleGroup.classList.add("hidden");
        uploadGroup.classList.add("hidden");
    }
}

// Upload MP4 Video File
async function uploadVideoFile() {
    const fileInput = document.getElementById("videoFileInput");
    const statusLabel = document.getElementById("uploadStatus");

    if (!fileInput.files || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    statusLabel.innerText = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/api/analyze/upload`, {
            method: "POST",
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            statusLabel.innerText = `Uploaded: ${file.name}`;
            const videoPlayer = document.getElementById("sampleVideoPlayer");
            videoPlayer.src = URL.createObjectURL(file);
        } else {
            statusLabel.innerText = "Upload failed.";
        }
    } catch (err) {
        console.error("Upload error:", err);
        statusLabel.innerText = "Error uploading file.";
    }
}

// Check Backend Status
async function checkServerStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById("hardwareDevice").innerText = data.device;
            
            const badge = document.getElementById("statusBadge");
            if (data.is_processing) {
                badge.className = "status-badge processing";
                badge.innerHTML = `<span class="pulse-dot"></span> Processing Video...`;
                if (!appState.isProcessing) {
                    startPollingProgress();
                }
            } else {
                badge.className = "status-badge online";
                badge.innerHTML = `<span class="pulse-dot"></span> System Ready`;
                if (appState.isProcessing) {
                    stopPollingProgress();
                    loadDashboardData();
                }
            }
        }
    } catch (err) {
        console.error("Server connection offline:", err);
    }
}

// Start Analysis Trigger
async function startAnalysis() {
    const sourceType = document.getElementById("sourceType").value;
    const sampleName = document.getElementById("sampleSelect").value;
    const modelName = document.getElementById("modelSelect").value;
    const sampleFps = parseInt(document.getElementById("sampleFps").value);
    const maxSeconds = parseInt(document.getElementById("maxSeconds").value);
    const confThresh = parseFloat(document.getElementById("confThresh").value);

    const payload = {
        source_type: sourceType,
        sample_name: sampleName,
        model_name: modelName,
        conf_thresh: confThresh,
        sample_fps: sampleFps,
        max_seconds: maxSeconds
    };

    try {
        const res = await fetch(`${API_BASE}/api/analyze/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            document.getElementById("startBtn").disabled = true;
            document.getElementById("stopBtn").disabled = false;
            document.getElementById("progressBox").classList.remove("hidden");
            startPollingProgress();
        } else {
            const err = await res.json();
            alert(`Error: ${err.detail || 'Failed to start analysis.'}`);
        }
    } catch (err) {
        console.error("Start analysis error:", err);
    }
}

// Stop Analysis Trigger
async function stopAnalysis() {
    try {
        await fetch(`${API_BASE}/api/analyze/stop`, { method: "POST" });
        stopPollingProgress();
        document.getElementById("startBtn").disabled = false;
        document.getElementById("stopBtn").disabled = true;
    } catch (err) {
        console.error("Stop analysis error:", err);
    }
}

// Progress Polling Engine
function startPollingProgress() {
    appState.isProcessing = true;
    if (appState.pollTimer) clearInterval(appState.pollTimer);

    appState.pollTimer = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/analyze/progress`);
            if (res.ok) {
                const data = await res.json();
                document.getElementById("progressBar").style.width = `${data.progress_pct}%`;
                document.getElementById("progressPct").innerText = `${data.progress_pct}%`;
                document.getElementById("progressText").innerText = `Evaluated ${data.current_frame}/${data.total_frames} Frames (${data.events_logged} Telemetry Events Logged)`;

                if (!data.is_processing && data.progress_pct >= 100) {
                    stopPollingProgress();
                    loadDashboardData();
                }
            }
        } catch (err) {
            console.error("Progress poll error:", err);
        }
    }, 1000);
}

function stopPollingProgress() {
    appState.isProcessing = false;
    if (appState.pollTimer) clearInterval(appState.pollTimer);
    document.getElementById("startBtn").disabled = false;
    document.getElementById("stopBtn").disabled = true;
    document.getElementById("progressBox").classList.add("hidden");
}

// Reset Session Data
async function resetSession() {
    if (!confirm("Are you sure you want to clear current telemetry logs?")) return;

    try {
        await fetch(`${API_BASE}/api/reset`, { method: "POST" });
        loadDashboardData();
    } catch (err) {
        console.error("Reset error:", err);
    }
}

// Load Dashboard Data & Update UI
async function loadDashboardData() {
    try {
        const [sumRes, rawRes, timelineRes, pedRes] = await Promise.all([
            fetch(`${API_BASE}/api/telemetry/summary`),
            fetch(`${API_BASE}/api/telemetry/raw`),
            fetch(`${API_BASE}/api/telemetry/timeline`),
            fetch(`${API_BASE}/api/pedagogy`)
        ]);

        if (sumRes.ok) {
            const sumData = await sumRes.json();
            appState.summaryData = sumData.data || [];
        }

        if (rawRes.ok) {
            const rawData = await rawRes.json();
            appState.rawTelemetry = rawData.data || [];
        }

        if (timelineRes.ok) {
            const timelineData = await timelineRes.json();
            appState.timelineData = timelineData.data || [];
        }

        if (pedRes.ok) {
            appState.pedagogyData = await pedRes.json();
        }

        renderDashboardUI();
    } catch (err) {
        console.error("Load dashboard data error:", err);
    }
}

// Render Dashboard Controls & Views
function renderDashboardUI() {
    const summary = appState.summaryData;
    const raw = appState.rawTelemetry;
    const timeline = appState.timelineData;
    const pedagogy = appState.pedagogyData;

    // 1. KPI Cards
    const totalStudents = summary.length;
    const avgFocus = pedagogy.avg_engagement || 0.0;
    const totalDistractions = summary.reduce((acc, row) => acc + (row["Distraction Count"] || 0), 0);
    const grade = pedagogy.overall_grade || "N/A";

    document.getElementById("kpiHeadcount").innerText = `${totalStudents} Students`;
    document.getElementById("kpiFocus").innerText = `${avgFocus.toFixed(1)}%`;
    document.getElementById("kpiDistractions").innerText = totalDistractions;
    document.getElementById("kpiGrade").innerText = grade;

    // 2. Timeline Chart
    updateTimelineChart(timeline);

    // 3. Analytics Charts
    updateBarChart(summary);
    updateBehaviorDonutChart(raw);

    // 4. Tables
    renderRawTelemetryTable(raw);
    renderRosterTable(summary);

    // 5. Pedagogy Panel
    renderPedagogyPanel(pedagogy);
}

// Chart 1: Continuous Focus Timeline Curve
function updateTimelineChart(timeline) {
    if (!timelineChart) return;

    const labels = timeline.map(item => `${item.timestamp}s`);
    const scores = timeline.map(item => item.score);

    timelineChart.data.labels = labels;
    timelineChart.data.datasets[0].data = scores;
    timelineChart.update();
}

// Chart 2: Focused vs Interaction Bar Chart
function updateBarChart(summary) {
    if (!barChartSummary) return;

    const labels = summary.map(row => row["Display Name"] || row["Student ID"]);
    const focusData = summary.map(row => row["Focused Duration (s)"]);
    const interactData = summary.map(row => row["Interaction Duration (s)"]);

    barChartSummary.data.labels = labels;
    barChartSummary.data.datasets[0].data = focusData;
    barChartSummary.data.datasets[1].data = interactData;
    barChartSummary.update();
}

// Chart 3: Posture & Behavior Donut Distribution
function updateBehaviorDonutChart(raw) {
    if (!donutBehaviorChart) return;

    let counts = { "focused": 0, "interacting with teacher": 0, "using phone": 0, "drowsy / slouching": 0 };
    raw.forEach(row => {
        if (counts.hasOwnProperty(row.behavior)) {
            counts[row.behavior]++;
        }
    });

    donutBehaviorChart.data.datasets[0].data = [
        counts["focused"],
        counts["interacting with teacher"],
        counts["using phone"],
        counts["drowsy / slouching"]
    ];
    donutBehaviorChart.update();
}

// Render Telemetry Table
function renderRawTelemetryTable(raw) {
    const tbody = document.querySelector("#rawTelemetryTable tbody");
    if (!raw || raw.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No telemetry logged yet. Click 'Start Analysis' to process video.</td></tr>`;
        return;
    }

    let rowsHtml = "";
    raw.slice(0, 100).forEach(row => {
        let badgeColor = "#10b981";
        if (row.behavior === "using phone") badgeColor = "#ef4444";
        else if (row.behavior === "interacting with teacher") badgeColor = "#38bdf8";
        else if (row.behavior.includes("drowsy")) badgeColor = "#f59e0b";

        rowsHtml += `
            <tr>
                <td><strong>${row.timestamp}s</strong></td>
                <td>${row.student_id}</td>
                <td><span style="color: ${badgeColor}; font-weight: 700;">${row.behavior.toUpperCase()}</span></td>
            </tr>
        `;
    });
    tbody.innerHTML = rowsHtml;
}

// Filter Raw Telemetry Table
function filterTelemetryTable() {
    const input = document.getElementById("tableFilter").value.toLowerCase();
    const rows = document.querySelectorAll("#rawTelemetryTable tbody tr");

    rows.forEach(row => {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(input) ? "" : "none";
    });
}

// Render Student Roster Audit Table
function renderRosterTable(summary) {
    const tbody = document.querySelector("#rosterTable tbody");
    if (!summary || summary.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">Run analysis to populate student profiles.</td></tr>`;
        return;
    }

    let rowsHtml = "";
    summary.forEach(row => {
        rowsHtml += `
            <tr>
                <td><strong>${row["Student ID"]}</strong></td>
                <td>${row["Display Name"]}</td>
                <td>${row["Focused Duration (s)"]}s</td>
                <td>${row["Interaction Duration (s)"]}s</td>
                <td>${row["Distraction Count"]}</td>
                <td><strong>${row["Engagement Score (%)"]}%</strong></td>
                <td>${row["Attention Level"]}</td>
                <td>
                    <button class="btn btn-ghost" style="padding: 4px 8px; font-size: 0.75rem;" onclick="openNameModal('${row["Student ID"]}', '${row["Display Name"]}')">
                        <i data-lucide="edit"></i> Edit Name
                    </button>
                </td>
            </tr>
        `;
    });
    tbody.innerHTML = rowsHtml;
    lucide.createIcons();
}

// Render AI Pedagogy Assistant Panel
function renderPedagogyPanel(pedagogy) {
    document.getElementById("pedagogyGradeDisplay").innerText = pedagogy.overall_grade || "N/A";
    document.getElementById("pedagogyScoreDisplay").innerText = `${(pedagogy.avg_engagement || 0).toFixed(1)}%`;

    const insightsList = document.getElementById("insightsList");
    if (pedagogy.insights && pedagogy.insights.length > 0) {
        insightsList.innerHTML = pedagogy.insights.map(item => `<li>• ${item}</li>`).join("");
    } else {
        insightsList.innerHTML = `<li>No telemetry data analyzed for recommendations.</li>`;
    }

    const recsList = document.getElementById("recommendationsList");
    if (pedagogy.recommendations && pedagogy.recommendations.length > 0) {
        recsList.innerHTML = pedagogy.recommendations.map(item => `<li>➔ ${item}</li>`).join("");
    } else {
        recsList.innerHTML = `<li>Run analysis from the control panel to generate pedagogical tips.</li>`;
    }
}

// Student Name Mapping Modal
function openNameModal(studentId, currentName) {
    appState.editingStudentId = studentId;
    document.getElementById("modalStudentId").innerText = studentId;
    document.getElementById("modalNameInput").value = currentName;
    document.getElementById("nameModal").classList.remove("hidden");
}

function closeNameModal() {
    document.getElementById("nameModal").classList.add("hidden");
}

async function saveStudentName() {
    const studentId = appState.editingStudentId;
    const newName = document.getElementById("modalNameInput").value;

    if (!studentId || !newName) return;

    try {
        const res = await fetch(`${API_BASE}/api/student/name`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ student_id: studentId, display_name: newName })
        });

        if (res.ok) {
            closeNameModal();
            loadDashboardData();
        }
    } catch (err) {
        console.error("Save name error:", err);
    }
}

// File Downloads
function downloadPdfReport() {
    window.open(`${API_BASE}/api/report/pdf`, "_blank");
}

function downloadCsv(type) {
    window.open(`${API_BASE}/api/report/csv/${type}`, "_blank");
}

// Initialize Chart.js Graphs
function initCharts() {
    // 1. Timeline Chart
    const ctxTimeline = document.getElementById("timelineChart").getContext("2d");
    const gradient = ctxTimeline.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, "rgba(16, 185, 129, 0.3)");
    gradient.addColorStop(1, "rgba(16, 185, 129, 0.0)");

    timelineChart = new Chart(ctxTimeline, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Classroom Focus Score (%)",
                data: [],
                borderColor: "#10b981",
                borderWidth: 2.5,
                fill: true,
                backgroundColor: gradient,
                tension: 0.3,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { color: "#334155" }, ticks: { color: "#94a3b8" } },
                y: { min: 0, max: 100, grid: { color: "#334155" }, ticks: { color: "#94a3b8" } }
            },
            plugins: { legend: { display: false } }
        }
    });

    // 2. Bar Chart
    const ctxBar = document.getElementById("barChartSummary").getContext("2d");
    barChartSummary = new Chart(ctxBar, {
        type: "bar",
        data: {
            labels: [],
            datasets: [
                { label: "Focused (s)", data: [], backgroundColor: "#10b981" },
                { label: "Interactions (s)", data: [], backgroundColor: "#38bdf8" }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { grid: { display: false }, ticks: { color: "#94a3b8" } },
                y: { grid: { color: "#334155" }, ticks: { color: "#94a3b8" } }
            },
            plugins: { legend: { labels: { color: "#f8fafc" } } }
        }
    });

    // 3. Donut Chart
    const ctxDonut = document.getElementById("donutBehaviorChart").getContext("2d");
    donutBehaviorChart = new Chart(ctxDonut, {
        type: "doughnut",
        data: {
            labels: ["Focused", "Teacher Interaction", "Using Phone", "Drowsy / Slouching"],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: ["#10b981", "#38bdf8", "#ef4444", "#f59e0b"],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: "right", labels: { color: "#f8fafc" } } }
        }
    });
}
