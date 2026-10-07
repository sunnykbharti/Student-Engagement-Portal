import cv2
import pandas as pd
import os
from core.vision_engine import VisionEngine

def run_pipeline(source="classroom3.mp4", max_seconds=60, output_csv="classroom_telemetry_raw.csv"):
    """
    CLI / Script execution wrapper for Computer Vision tracking pipeline.
    """
    print(f"🚀 Initializing AI Cell Processing Pipeline on source: {source}")
    engine = VisionEngine(model_path="yolov8n-pose.pt")

    cap = cv2.VideoCapture(source if not str(source).isdigit() else int(source))
    if not cap.isOpened():
        print(f"❌ Error: Unable to open video source {source}")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    max_frames = min(fps * max_seconds, total_frames if total_frames > 0 else fps * max_seconds)

    raw_logs = []
    frame_idx = 0

    print("🎥 Running posture evaluation loop (1 FPS sampling)...")
    while cap.isOpened() and frame_idx < max_frames:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % fps != 0:
            continue

        timestamp_sec = int(frame_idx / fps)
        annotated_frame, raw_logs = engine.process_frame(frame, timestamp_sec, raw_logs)

        # Show live visual inspection window
        cv2.imshow("AI Cell Classroom Processing Engine", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if len(raw_logs) > 0:
        df_raw = pd.DataFrame(raw_logs)
        df_raw.to_csv(output_csv, index=False)
        print(f"💾 Raw data pipeline completed. Saved {len(raw_logs)} telemetry records to {output_csv}")
    else:
        print("⚠️ Processing completed, but no student tracking telemetry was logged.")

if __name__ == "__main__":
    # If classroom3.mp4 exists, use it as sample source; otherwise fallback to webcam 0
    sample_path = "classroom3.mp4" if os.path.exists("classroom3.mp4") else 0
    run_pipeline(source=sample_path, max_seconds=60)