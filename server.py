import os
import cv2
import time
import threading
import torch
import pandas as pd
from typing import Optional, Dict, List
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.vision_engine import VisionEngine
from core.analytics_engine import AnalyticsEngine
from core.pdf_generator import PDFReportGenerator

app = FastAPI(title="AI Classroom Analytics Suite API", version="2.0.0")

# Enable CORS for local dev / browser requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State Container
class SessionState:
    def __init__(self):
        self.raw_telemetry: List[Dict] = []
        self.student_names: Dict[str, str] = {}
        self.is_processing: bool = False
        self.stop_requested: bool = False
        self.current_frame: int = 0
        self.total_frames: int = 0
        self.progress_pct: float = 0.0
        self.active_source: str = ""
        self.raw_csv_path = "classroom_telemetry_raw.csv"
        self.summary_csv_path = "classroom_60s_summary.csv"
        self.pdf_report_path = "Classroom_Engagement_Report.pdf"

state = SessionState()

# Load disk telemetry if present
if os.path.exists(state.raw_csv_path):
    try:
        df_disk = pd.read_csv(state.raw_csv_path)
        if not df_disk.empty:
            state.raw_telemetry = df_disk.to_dict("records")
    except Exception:
        pass

# Pydantic Request Models
class StartAnalysisRequest(BaseModel):
    source_type: str = "sample" # "sample", "upload", "webcam"
    sample_name: str = "classroom3.mp4"
    model_name: str = "yolov8n-pose.pt"
    conf_thresh: float = 0.15
    sample_fps: int = 1
    max_seconds: int = 60

class StudentNameRequest(BaseModel):
    student_id: str
    display_name: str

def run_vision_processing_task(source_path, model_name, conf_thresh, sample_fps, max_seconds):
    state.is_processing = True
    state.stop_requested = False
    state.current_frame = 0
    state.progress_pct = 0.0
    state.raw_telemetry = []

    try:
        engine = VisionEngine(model_path=model_name, conf_thresh=conf_thresh)
        cap = cv2.VideoCapture(source_path if not str(source_path).isdigit() else int(source_path))

        if not cap.isOpened():
            print(f"❌ Server Vision Task: Failed to open source {source_path}")
            state.is_processing = False
            return

        video_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        state.total_frames = min(max_seconds * video_fps, total_video_frames if total_video_frames > 0 else 99999)

        frame_idx = 0
        raw_logs = []

        while cap.isOpened() and frame_idx < state.total_frames:
            if state.stop_requested:
                print("🛑 Server Vision Task: Stop signal received.")
                break

            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            state.current_frame = frame_idx

            skip_factor = max(1, int(video_fps / sample_fps))
            if frame_idx % skip_factor != 0:
                continue

            timestamp_sec = int(frame_idx / video_fps)
            annotated_frame, raw_logs = engine.process_frame(frame, timestamp_sec, raw_logs)
            
            state.raw_telemetry = raw_logs
            state.progress_pct = round(min(100.0, (frame_idx / state.total_frames) * 100.0), 1)

        cap.release()

        # Write datasets to disk
        if len(raw_logs) > 0:
            df_raw = pd.DataFrame(raw_logs)
            df_raw.to_csv(state.raw_csv_path, index=False)
            df_sum = AnalyticsEngine.compute_summary(df_raw, state.student_names)
            df_sum.to_csv(state.summary_csv_path, index=False)

    except Exception as e:
        print(f"❌ Server Vision Task Error: {e}")
    finally:
        state.is_processing = False
        state.progress_pct = 100.0 if not state.stop_requested else state.progress_pct

# REST API Endpoints
@app.get("/api/status")
def get_status():
    samples = []
    for f in ["classroom3.mp4", "classroom2.mp4", "classroom_test.mp4"]:
        if os.path.exists(f):
            samples.append(f)
            
    if torch.backends.mps.is_available():
        device = "MPS"
    elif torch.cuda.is_available():
        device = "CUDA"
    else:
        device = "CPU"
    
    return {
        "status": "online",
        "device": device,
        "is_processing": state.is_processing,
        "progress_pct": state.progress_pct,
        "samples": samples,
        "telemetry_count": len(state.raw_telemetry)
    }

@app.post("/api/analyze/start")
def start_analysis(req: StartAnalysisRequest):
    if state.is_processing:
        raise HTTPException(status_code=400, detail="Analysis task is already running.")

    if req.source_type == "sample":
        source_path = req.sample_name
        if not os.path.exists(source_path):
            raise HTTPException(status_code=404, detail=f"Sample video file '{source_path}' not found.")
    elif req.source_type == "webcam":
        source_path = 0
    else:
        source_path = state.active_source
        if not source_path or not os.path.exists(source_path):
            raise HTTPException(status_code=400, detail="No uploaded video file found.")

    # Run in background thread
    t = threading.Thread(
        target=run_vision_processing_task,
        args=(source_path, req.model_name, req.conf_thresh, req.sample_fps, req.max_seconds),
        daemon=True
    )
    t.start()

    return {"message": "Vision processing pipeline started successfully.", "source": str(source_path)}

@app.post("/api/analyze/upload")
async def upload_video(file: UploadFile = File(...)):
    temp_path = f"temp_upload_{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    state.active_source = temp_path
    return {"message": "File uploaded successfully.", "file_path": temp_path}

@app.get("/api/analyze/progress")
def get_progress():
    return {
        "is_processing": state.is_processing,
        "current_frame": state.current_frame,
        "total_frames": state.total_frames,
        "progress_pct": state.progress_pct,
        "events_logged": len(state.raw_telemetry)
    }

@app.post("/api/analyze/stop")
def stop_analysis():
    state.stop_requested = True
    return {"message": "Stop signal transmitted."}

@app.get("/api/telemetry/raw")
def get_raw_telemetry():
    return {"data": state.raw_telemetry}

@app.get("/api/telemetry/summary")
def get_summary_telemetry():
    df_raw = pd.DataFrame(state.raw_telemetry) if state.raw_telemetry else pd.DataFrame()
    df_summary = AnalyticsEngine.compute_summary(df_raw, state.student_names)
    return {"data": df_summary.to_dict("records")}

@app.get("/api/telemetry/timeline")
def get_timeline():
    df_raw = pd.DataFrame(state.raw_telemetry) if state.raw_telemetry else pd.DataFrame()
    max_sec = int(df_raw["timestamp"].max()) if not df_raw.empty else 60
    series = AnalyticsEngine.compute_timeline(df_raw, max_seconds=max_sec)
    
    result = []
    for ts, score in series.items():
        result.append({"timestamp": int(ts), "score": round(float(score), 1)})
    return {"data": result}

@app.get("/api/pedagogy")
def get_pedagogy():
    df_raw = pd.DataFrame(state.raw_telemetry) if state.raw_telemetry else pd.DataFrame()
    df_summary = AnalyticsEngine.compute_summary(df_raw, state.student_names)
    max_sec = int(df_raw["timestamp"].max()) if not df_raw.empty else 60
    series = AnalyticsEngine.compute_timeline(df_raw, max_seconds=max_sec)
    pedagogy = AnalyticsEngine.generate_pedagogical_report(df_summary, series)
    return pedagogy

@app.post("/api/student/name")
def update_student_name(req: StudentNameRequest):
    state.student_names[req.student_id] = req.display_name
    return {"message": "Student name mapped successfully.", "mappings": state.student_names}

@app.get("/api/report/pdf")
def download_pdf():
    df_raw = pd.DataFrame(state.raw_telemetry) if state.raw_telemetry else pd.DataFrame()
    df_summary = AnalyticsEngine.compute_summary(df_raw, state.student_names)
    max_sec = int(df_raw["timestamp"].max()) if not df_raw.empty else 60
    series = AnalyticsEngine.compute_timeline(df_raw, max_seconds=max_sec)
    pedagogy = AnalyticsEngine.generate_pedagogical_report(df_summary, series)
    
    pdf_path = PDFReportGenerator.generate_pdf(df_summary, pedagogy, output_path=state.pdf_report_path, duration_sec=max_sec)
    return FileResponse(pdf_path, media_type="application/pdf", filename="Classroom_Engagement_Report.pdf")

@app.get("/api/report/csv/raw")
def download_raw_csv():
    if not os.path.exists(state.raw_csv_path):
        df_empty = pd.DataFrame(columns=["timestamp", "student_id", "behavior"])
        df_empty.to_csv(state.raw_csv_path, index=False)
    return FileResponse(state.raw_csv_path, media_type="text/csv", filename="classroom_telemetry_raw.csv")

@app.get("/api/report/csv/summary")
def download_summary_csv():
    df_raw = pd.DataFrame(state.raw_telemetry) if state.raw_telemetry else pd.DataFrame()
    df_summary = AnalyticsEngine.compute_summary(df_raw, state.student_names)
    df_summary.to_csv(state.summary_csv_path, index=False)
    return FileResponse(state.summary_csv_path, media_type="text/csv", filename="classroom_60s_summary.csv")

@app.post("/api/reset")
def reset_session():
    state.raw_telemetry = []
    state.student_names = {}
    if os.path.exists(state.raw_csv_path):
        os.remove(state.raw_csv_path)
    if os.path.exists(state.summary_csv_path):
        os.remove(state.summary_csv_path)
    return {"message": "Session reset successfully."}

@app.get("/{video_name}.mp4")
def get_video_file(video_name: str):
    file_path = f"{video_name}.mp4"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4")
    raise HTTPException(status_code=404, detail="Video file not found")

# Mount static web assets
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting AI Cell FastAPI Server on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
