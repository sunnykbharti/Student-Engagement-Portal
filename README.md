# 🎓 AI Classroom Engagement & Analytics Suite

An end-to-end, computer vision-powered classroom analytics platform designed to monitor student engagement, attentiveness, and classroom dynamics in real time. Powered by **YOLOv8 Pose Estimation**, automated telemetry logging, and dynamic report generation.

---

## 📌 Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Prerequisites & Installation](#prerequisites--installation)
- [How to Run the Application](#how-to-run-the-application)
- [Supported Execution Modes](#supported-execution-modes)
- [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## 🌟 Overview

The **AI Classroom Engagement & Analytics Suite** analyzes classroom video streams (prerecorded or live webcam) using computer vision to evaluate student behaviors in real time without intrusive biometric identification. 

It classifies behavioral states:
- 🟢 **Focused / Attentive**: Active listening, forward-facing orientation.
- 🔵 **Interacting with Teacher**: Raised hands, active engagement.
- 🔴 **Using Phone / Distracted**: Downward gaze with bent neck angles toward lap/desk.
- 🟠 **Drowsy / Slouching**: Excessive head drop or resting posture.

---

## 🚀 Key Features

- **Real-Time Pose Estimation**: Uses Ultralytics YOLOv8 Pose models (`yolov8n-pose.pt` for speed or `yolov8m-pose.pt` for precision).
- **Multi-Device Acceleration**: Automatically activates Apple Silicon Metal (`mps`), NVIDIA CUDA (`cuda`), or fallback `cpu`.
- **Multiple Interface Modes**:
  - **FastAPI Web App**: Full-featured modern web application with REST APIs.
  - **Streamlit Interactive Suite**: Interactive visual controls, video upload, webcam feed, and real-time Altair charts.
  - **Headless CLI Pipeline**: High-throughput batch processing for offline recordings.
- **Automated Analytics & Auditing**:
  - Raw telemetry capture (`classroom_telemetry_raw.csv`).
  - Interval-aggregated performance metrics (`classroom_60s_summary.csv`).
  - Matplotlib activity intensity curves (`Classroom_Activity_Intensity_Plot.png`).
  - Executive-level PDF audit reports (`Classroom_Engagement_Report.pdf`) generated via ReportLab.

---

## 🏗️ System Architecture

```
                       ┌──────────────────────────────┐
                       │   Input Video / Live Stream  │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │   core.vision_engine.py      │
                       │   (YOLOv8 Pose Estimation)   │
                       └──────────────┬───────────────┘
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        ┌─────────────────────┐               ┌─────────────────────┐
        │  Posture & Keypoint │               │ Frame Annotation &  │
        │  Classification     │               │ Bounding Overlays   │
        └──────────┬──────────┘               └─────────────────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ core.analytics_     │ ──► classroom_telemetry_raw.csv
        │ engine.py           │ ──► classroom_60s_summary.csv
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ core.pdf_generator  │ ──► Classroom_Engagement_Report.pdf
        │ & visualize.py      │ ──► Classroom_Activity_Intensity_Plot.png
        └─────────────────────┘
```

---

## 📁 Project Structure

```text
├── core/
│   ├── vision_engine.py         # YOLOv8 pose tracker, keypoint heuristics
│   ├── analytics_engine.py      # Telemetry aggregation, engagement scoring
│   ├── pdf_generator.py         # Automated executive PDF report compiler
│   └── __init__.py
├── static/                      # Frontend assets for the FastAPI web interface
│   ├── css/
│   ├── js/
│   └── index.html
├── app.py                       # Streamlit interactive dashboard application
├── server.py                    # FastAPI backend server with REST endpoints
├── main.py                      # Unified runner & CLI entrypoint
├── pipeline.py                  # Video stream processor & loop controller
├── generate_reports.py          # Standalone PDF report generator
├── visualize.py                 # Matplotlib trend plotter
├── requirements.txt             # Project dependencies
├── yolov8n-pose.pt              # Lightweight YOLOv8 pose model weights
└── yolov8m-pose.pt              # Medium YOLOv8 pose model weights
```

---

## ⚙️ Prerequisites & Installation

### 1. Prerequisites
- Python **3.9+** installed on macOS, Linux, or Windows.
- A functional webcam (for live streaming) or sample MP4 video files.

### 2. Setup Virtual Environment
```bash
# Create a virtual environment
python3 -m venv env

# Activate the virtual environment
# On macOS / Linux:
source env/bin/activate

# On Windows:
# env\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🖥️ How to Run the Application

The project includes multiple ways to run depending on your preferred interface:

### Option 1: FastAPI Web Application (Recommended)
Launches the FastAPI server and automatically opens the web dashboard in your default browser:
```bash
python3 main.py
```
- **Local URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Option 2: Streamlit Interactive Dashboard
Run the Streamlit app directly:
```bash
streamlit run app.py
```
Or via `main.py`:
```bash
python3 main.py --streamlit
```
- **Local URL**: [http://localhost:8501](http://localhost:8501)

> ⚠️ **Note**: Streamlit apps **must** be launched using `streamlit run app.py` (or `python3 -m streamlit run app.py`). Running `python3 app.py` directly executes the script in headless bare mode and results in `missing ScriptRunContext!` warnings without opening the browser.

---

### Option 3: Headless CLI Processing & Batch Reports
Process a video in the terminal and generate all summaries, plots, and PDF reports without opening a browser:
```bash
python3 main.py --cli
```
This runs the video pipeline on `classroom3.mp4`, aggregates telemetry, and produces:
- `classroom_telemetry_raw.csv`
- `classroom_60s_summary.csv`
- `Classroom_Activity_Intensity_Plot.png`
- `Classroom_Engagement_Report.pdf`

---

## ❓ Troubleshooting & FAQs

### Q: Why do I see `missing ScriptRunContext!` when running `python3 app.py`?
**A**: `app.py` is built with Streamlit. Executing `python3 app.py` runs Python directly rather than through Streamlit's web server runner. Use:
```bash
streamlit run app.py
```
or
```bash
python3 main.py --streamlit
```

### Q: How do I test with my own video?
- **Web App / Streamlit**: Use the "Upload Video File" option in the UI sidebar.
- **CLI**: Place your MP4 file in the root directory and pass the path in `pipeline.py` or modify the default in `main.py`.

### Q: How can I change the model between lightweight and high precision?
In `app.py` or `main.py`, select either `yolov8n-pose.pt` (faster, lower resource consumption) or `yolov8m-pose.pt` (higher pose detection fidelity).
