import cv2
import torch
import numpy as np
import pandas as pd
from ultralytics import YOLO
import os
import time

class VisionEngine:
    """
    Computer Vision Engine for Classroom Student Engagement & Behavior Tracking.
    Uses YOLOv8 Pose Estimation + BOTSORT tracker for real-time posture analysis.
    """
    def __init__(self, model_path="yolov8n-pose.pt", conf_thresh=0.15, iou_thresh=0.45, device=None):
        if device is None:
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
        else:
            self.device = device
            
        self.model_path = model_path
        self.conf_thresh = conf_thresh
        self.iou_thresh = iou_thresh
        
        # Load YOLO pose model
        print(f"🚀 Loading YOLO Pose Model ({model_path}) on hardware accelerator: {self.device.upper()}")
        self.model = YOLO(model_path).to(self.device)

        # Status color maps (BGR for OpenCV)
        self.COLOR_MAP = {
            "focused": (16, 185, 129),           # Emerald Green
            "interacting with teacher": (248, 189, 56), # Cyan / Sky Blue
            "using phone": (68, 68, 239),        # Coral Red
            "drowsy / slouching": (11, 158, 245) # Amber Orange
        }

    def analyze_keypoints(self, kpts):
        if kpts is None or len(kpts) < 11:
            return "focused"
        try:
            nose_y = kpts[0][1].item()
            l_ear_y, r_ear_y = kpts[3][1].item(), kpts[4][1].item()
            l_shoulder_y, r_shoulder_y = kpts[5][1].item(), kpts[6][1].item()
            l_wrist_y, r_wrist_y = kpts[9][1].item(), kpts[10][1].item()

            avg_ear_y = (l_ear_y + r_ear_y) / 2 if (l_ear_y > 0 and r_ear_y > 0) else max(l_ear_y, r_ear_y)
            avg_shoulder_y = (l_shoulder_y + r_shoulder_y) / 2 if (l_shoulder_y > 0 and r_shoulder_y > 0) else max(l_shoulder_y, r_shoulder_y)
            
            # Rule 1: Hand raised / Teacher interaction
            if (l_wrist_y > 0 and l_wrist_y < nose_y) or (r_wrist_y > 0 and r_wrist_y < nose_y):
                return "interacting with teacher"

            # Rule 2: Distraction / Phone lookup (head dropped close to shoulders or desk level)
            if avg_shoulder_y > 0 and avg_ear_y > 0 and (avg_shoulder_y - avg_ear_y) < 42:
                return "using phone"

            # Rule 3: Drowsiness / Slouching (head dropped significantly low relative to torso plane)
            if avg_shoulder_y > 0 and nose_y > avg_shoulder_y - 15:
                return "drowsy / slouching"

            # Baseline Normal Attentive Posture
            return "focused"

        except (IndexError, TypeError, ValueError):
            return "focused"

    def draw_annotations(self, frame, boxes, keypoints, raw_logs, timestamp_sec):
        """
        Draws custom high-definition bounding boxes, skeleton wireframes, and posture tags.
        """
        annotated = frame.copy()
        
        if boxes is None or keypoints is None:
            return annotated, raw_logs

        for i, box in enumerate(boxes):
            track_id = int(box.id[0].item()) if (box.id is not None and len(box.id) > 0) else i + 1
            kpts = keypoints[i] if (keypoints is not None and i < len(keypoints)) else None
            
            behavior = self.analyze_keypoints(kpts)
            student_label = f"Student_{track_id}"
            
            # Record telemetry
            raw_logs.append({
                "timestamp": timestamp_sec,
                "student_id": student_label,
                "behavior": behavior
            })

            # Get bounding box coordinates [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            x1, y1, x2, y2 = xyxy

            color = self.COLOR_MAP.get(behavior, (16, 185, 129))

            # Bounding box frame
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Header pill overlay
            text = f"{student_label} | {behavior.upper()}"
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated, (x1, max(0, y1 - 25)), (x1 + tw + 10, y1), color, -1)
            cv2.putText(annotated, text, (x1 + 5, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

            # Render Keypoint Connections (Upper Body Skeleton)
            connections = [(0, 1), (0, 2), (1, 3), (2, 4), (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12)]
            for pt1_idx, pt2_idx in connections:
                try:
                    p1 = (int(kpts[pt1_idx][0].item()), int(kpts[pt1_idx][1].item()))
                    p2 = (int(kpts[pt2_idx][0].item()), int(kpts[pt2_idx][1].item()))
                    if p1[0] > 0 and p1[1] > 0 and p2[0] > 0 and p2[1] > 0:
                        cv2.line(annotated, p1, p2, color, 2, cv2.LINE_AA)
                except IndexError:
                    continue

        return annotated, raw_logs

    def process_frame(self, frame, timestamp_sec, raw_logs):
        """
        Runs tracking on a single frame and returns annotated frame + updated telemetry list.
        """
        results = self.model.track(
            frame,
            persist=True,
            device=self.device,
            verbose=False,
            tracker="botsort.yaml",
            imgsz=640,
            conf=self.conf_thresh,
            iou=self.iou_thresh
        )

        if len(results) > 0:
            boxes = results[0].boxes
            keypoints = results[0].keypoints.data if results[0].keypoints is not None else None
            return self.draw_annotations(frame, boxes, keypoints, raw_logs, timestamp_sec)

        return frame, raw_logs
