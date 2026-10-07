import streamlit as st
import pandas as pd
import numpy as np
import cv2
import time
import os
import tempfile
import altair as alt

from core.vision_engine import VisionEngine
from core.analytics_engine import AnalyticsEngine
from core.pdf_generator import PDFReportGenerator

# 1. Page Configuration & Custom CSS Styling
st.set_page_config(
    page_title="AI Classroom Analytics Suite",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Sleek CSS for Modern Dark UI
st.markdown("""
<style>
    /* Global Container Adjustments */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    /* Header Container Styling */
    .header-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        margin-bottom: 1.5rem;
    }
    
    .header-title {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .header-desc {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 0.3rem;
    }

    /* Metric Cards */
    .metric-card {
        background: #1e293b;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #334155;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #10b981;
    }
    .metric-label {
        color: #94a3b8;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Tab Headers */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px;
        background-color: #1e293b;
        color: #cbd5e1;
    }
    .stTabs [aria-selected="true"] {
        background-color: #10b981 !important;
        color: #ffffff !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 2. Session State Initialization
if "raw_telemetry" not in st.session_state:
    st.session_state["raw_telemetry"] = []
if "processing_active" not in st.session_state:
    st.session_state["processing_active"] = False
if "student_names" not in st.session_state:
    st.session_state["student_names"] = {}

RAW_CSV_PATH = "classroom_telemetry_raw.csv"
SUMMARY_CSV_PATH = "classroom_60s_summary.csv"

# Load existing telemetry CSV if available on disk
if os.path.exists(RAW_CSV_PATH) and len(st.session_state["raw_telemetry"]) == 0:
    try:
        df_disk = pd.read_csv(RAW_CSV_PATH)
        if not df_disk.empty:
            st.session_state["raw_telemetry"] = df_disk.to_dict("records")
    except Exception:
        pass

# 3. Sidebar Controls Panel
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/teacher.png", width=64)
    st.title("⚙️ Control Panel")
    st.caption("Configure AI video analysis parameters")

    st.markdown("---")
    st.subheader("📹 Input Video Source")
    input_type = st.radio(
        "Select Source",
        ["📁 Sample Classroom Videos", "📤 Upload Video File", "🎥 Live Webcam Stream"],
        index=0
    )

    selected_video_path = None
    
    if input_type == "📁 Sample Classroom Videos":
        samples = {
            "Classroom Sample 3 (Recommended)": "classroom3.mp4",
            "Classroom Sample 2": "classroom2.mp4",
            "Classroom Short Test": "classroom_test.mp4"
        }
        chosen_sample = st.selectbox("Choose Sample File", list(samples.keys()))
        selected_video_path = samples[chosen_sample]
        if not os.path.exists(selected_video_path):
            st.error(f"Sample file {selected_video_path} not found in workspace directory.")

    elif input_type == "📤 Upload Video File":
        uploaded_file = st.file_uploader("Upload Classroom MP4/MOV Video", type=["mp4", "mov", "avi"])
        if uploaded_file is not None:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_file.read())
            selected_video_path = tfile.name

    elif input_type == "🎥 Live Webcam Stream":
        selected_video_path = 0 # OpenCV device index 0

    st.markdown("---")
    st.subheader("🤖 Neural Network Model")
    model_choice = st.selectbox(
        "YOLOv8 Pose Architecture",
        ["yolov8n-pose.pt (Fast / Lightweight)", "yolov8m-pose.pt (High Precision)"],
        index=0
    )
    model_file = "yolov8n-pose.pt" if "yolov8n" in model_choice else "yolov8m-pose.pt"

    conf_thresh = st.slider("Detection Confidence Threshold", 0.05, 0.50, 0.15, 0.05)
    sample_fps = st.slider("Sampling Rate (FPS)", 1, 10, 1, 1, help="Higher FPS increases accuracy but uses more computing power.")
    max_duration_sec = st.slider("Max Window Duration (sec)", 10, 180, 60, 10)

    st.markdown("---")
    start_col, stop_col = st.columns(2)
    with start_col:
        start_btn = st.button("🚀 Start Analysis", use_container_width=True, type="primary")
    with stop_col:
        stop_btn = st.button("⏹️ Stop", use_container_width=True)

    if st.button("🔄 Reset Telemetry Data", use_container_width=True):
        st.session_state["raw_telemetry"] = []
        if os.path.exists(RAW_CSV_PATH):
            os.remove(RAW_CSV_PATH)
        if os.path.exists(SUMMARY_CSV_PATH):
            os.remove(SUMMARY_CSV_PATH)
        st.rerun()

# 4. Main Page Header
st.markdown("""
<div class="header-box">
    <div class="header-title">🎓 AI Cell Classroom Behavioral & Engagement Analytics</div>
    <div class="header-desc">Computer Vision Neural Network Infrastructure for Real-Time Pedagogy & Student Performance Audit</div>
</div>
""", unsafe_allow_html=True)

# 5. Core Video Processing Trigger Engine
if start_btn:
    if selected_video_path is None and input_type == "📤 Upload Video File":
        st.warning("⚠️ Please upload a valid MP4 video file first.")
    else:
        st.session_state["processing_active"] = True
        st.session_state["raw_telemetry"] = [] # Fresh session run

        st.info("🚀 Initializing Neural Network Computer Vision Engine...")
        engine = VisionEngine(model_path=model_file, conf_thresh=conf_thresh)

        cap = cv2.VideoCapture(selected_video_path)
        if not cap.isOpened():
            st.error(f"❌ Failed to open video source: {selected_video_path}")
        else:
            video_fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
            total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            max_frames = min(max_duration_sec * video_fps, total_video_frames if total_video_frames > 0 else 999999)

            st.write("🎥 **Processing Live Video Analytics Stream...**")
            video_placeholder = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()

            frame_idx = 0
            raw_logs = []
            
            while cap.isOpened() and frame_idx < max_frames:
                if stop_btn:
                    st.warning("⏹️ Processing manually stopped by user.")
                    break

                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1

                # Frame skipping logic according to chosen sample_fps
                skip_factor = max(1, int(video_fps / sample_fps))
                if frame_idx % skip_factor != 0:
                    continue

                timestamp_sec = int(frame_idx / video_fps)

                # Process frame through vision engine
                annotated_frame, raw_logs = engine.process_frame(frame, timestamp_sec, raw_logs)

                # Render frame RGB preview in Streamlit
                frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

                # Update progress
                pct = min(1.0, float(frame_idx / max_frames))
                progress_bar.progress(pct)
                status_text.caption(f"⏱️ Evaluated Frame {frame_idx}/{max_frames} ({timestamp_sec}s timestamp) | Captured Telemetry Events: {len(raw_logs)}")

            cap.release()
            st.session_state["raw_telemetry"] = raw_logs
            st.session_state["processing_active"] = False

            # Export datasets to disk
            if len(raw_logs) > 0:
                df_raw = pd.DataFrame(raw_logs)
                df_raw.to_csv(RAW_CSV_PATH, index=False)

                df_sum = AnalyticsEngine.compute_summary(df_raw, st.session_state["student_names"])
                df_sum.to_csv(SUMMARY_CSV_PATH, index=False)

                st.success("✅ Analysis Complete! Raw telemetry and summaries generated.")
                time.sleep(1)
                st.rerun()

# 6. Analytics Processing & Render Dashboard
df_raw = pd.DataFrame(st.session_state["raw_telemetry"]) if len(st.session_state["raw_telemetry"]) > 0 else pd.DataFrame()
df_summary = AnalyticsEngine.compute_summary(df_raw, st.session_state["student_names"])
max_sec = int(df_raw["timestamp"].max()) if not df_raw.empty else max_duration_sec
timeline_series = AnalyticsEngine.compute_timeline(df_raw, max_seconds=max_sec)
pedagogy = AnalyticsEngine.generate_pedagogical_report(df_summary, timeline_series)

# Top KPI Overview Row
headcount = len(df_summary)
avg_focus = pedagogy.get("avg_engagement", 0.0)
total_distraction_flips = df_summary["Distraction Count"].sum() if not df_summary.empty else 0
class_grade = pedagogy.get("overall_grade", "N/A")

kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
with kpi_col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">👥 Active Headcount</div>
        <div class="metric-val" style="color: #38bdf8;">{headcount} Students</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🟢 Avg Classroom Focus</div>
        <div class="metric-val" style="color: #10b981;">{avg_focus:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">⚠️ Total Distraction Flags</div>
        <div class="metric-val" style="color: #ef4444;">{int(total_distraction_flips)}</div>
    </div>
    """, unsafe_allow_html=True)

with kpi_col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">🏆 Pedagogy Grade</div>
        <div class="metric-val" style="color: #f59e0b;">{class_grade}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 7. Dashboard Main Content Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎥 Live & Video Preview", 
    "📊 Engagement Analytics", 
    "🎓 Student Profiles & Roster", 
    "🧠 AI Pedagogy Assistant", 
    "📄 Reports & Exports"
])

with tab1:
    st.subheader("📹 Video Source & Continuous Engagement Trajectory")
    
    preview_col, timeline_col = st.columns([1, 1])
    
    with preview_col:
        st.markdown("**Source Preview**")
        if selected_video_path and isinstance(selected_video_path, str) and os.path.exists(selected_video_path):
            st.video(selected_video_path)
        else:
            st.info("ℹ️ Select a video sample or start live camera stream to display video here.")

    with timeline_col:
        st.markdown("**Real-Time Engagement Timeline (0 - 100%)**")
        if not timeline_series.empty and timeline_series.sum() > 0:
            df_chart = pd.DataFrame({"Timestamp (s)": timeline_series.index, "Engagement Score (%)": timeline_series.values})
            chart = alt.Chart(df_chart).mark_area(
                line={'color': '#10b981', 'size': 2.5},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#10b981', offset=1),
                           alt.GradientStop(color='rgba(16, 185, 129, 0.1)', offset=0)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X('Timestamp (s):Q', title='Timeline (Seconds)'),
                y=alt.Y('Engagement Score (%):Q', scale=alt.Scale(domain=[0, 100]), title='Score (%)')
            ).properties(height=280)
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("⏳ Click '🚀 Start Analysis' in the sidebar to process video and stream engagement data.")

with tab2:
    st.subheader("📊 Classroom Behavior & Attention Breakdown")

    if df_summary.empty:
        st.info("No telemetry logs recorded yet. Start analysis from the sidebar control panel.")
    else:
        left_chart, right_chart = st.columns(2)

        with left_chart:
            st.markdown("### 📝 Individual Focus vs Interaction Duration (s)")
            df_plot_bars = df_summary[["Display Name", "Focused Duration (s)", "Interaction Duration (s)"]].melt(
                id_vars="Display Name", var_name="Metric", value_name="Seconds"
            )
            bar_chart = alt.Chart(df_plot_bars).mark_bar().encode(
                x=alt.X('Display Name:N', title='Student'),
                y=alt.Y('Seconds:Q', title='Duration (Seconds)'),
                color=alt.Color('Metric:N', scale=alt.Scale(domain=['Focused Duration (s)', 'Interaction Duration (s)'], range=['#10b981', '#38bdf8'])),
                xOffset='Metric:N'
            ).properties(height=320)
            st.altair_chart(bar_chart, use_container_width=True)

        with right_chart:
            st.markdown("### 📱 Distraction Offenses by Student")
            distraction_chart = alt.Chart(df_summary).mark_bar(color='#ef4444').encode(
                y=alt.Y('Display Name:N', sort='-x', title='Student'),
                x=alt.X('Distraction Count:Q', title='Count of Event Flips')
            ).properties(height=320)
            st.altair_chart(distraction_chart, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Second-by-Second Raw Behavioral Telemetry Register")
        st.dataframe(df_raw, use_container_width=True, height=250)

with tab3:
    st.subheader("🎓 Student Roster & Individual Profiling")

    if df_summary.empty:
        st.info("No student telemetry registered. Run an analysis to populate student profiles.")
    else:
        st.markdown("### 🏷️ Map Student Identifiers to Names")
        edit_col1, edit_col2 = st.columns([1, 2])
        with edit_col1:
            selected_student_id = st.selectbox("Select Tracked ID", df_summary["Student ID"].unique())
        with edit_col2:
            current_custom_name = st.session_state["student_names"].get(selected_student_id, selected_student_id)
            new_name = st.text_input("Enter Student Real Name", value=current_custom_name)
            if st.button("Save Name Mapping"):
                st.session_state["student_names"][selected_student_id] = new_name
                st.success(f"Mapped {selected_student_id} ➔ {new_name}")
                st.rerun()

        st.markdown("---")
        st.markdown("### 📋 Student Engagement Audit Roster")
        
        # Display colored dataframe
        st.dataframe(
            df_summary[[
                "Student ID", "Display Name", "Engagement Score (%)", 
                "Attention Level", "Focused Duration (s)", 
                "Interaction Duration (s)", "Distraction Count"
            ]],
            use_container_width=True
        )

with tab4:
    st.subheader("🧠 AI Pedagogy Assistant & Automated Teaching Audit")

    if df_summary.empty:
        st.info("AI Pedagogy Assistant requires active telemetry data to compile recommendations.")
    else:
        g_col1, g_col2 = st.columns([1, 2])
        with g_col1:
            st.markdown(f"""
            <div style="background: #1e293b; padding: 1.5rem; border-radius: 12px; border: 1px solid #334155; text-align: center;">
                <h4 style="color: #94a3b8; margin: 0;">Overall Class Grade</h4>
                <h1 style="color: #f59e0b; font-size: 3rem; margin: 0.5rem 0;">{pedagogy['overall_grade']}</h1>
                <p style="color: #cbd5e1; font-size: 0.9rem;">Mean Class Focus: <b>{pedagogy['avg_engagement']}%</b></p>
            </div>
            """, unsafe_allow_html=True)

        with g_col2:
            st.markdown("### 🔍 Key Lecture Insights")
            for insight in pedagogy.get("insights", []):
                st.markdown(f"- {insight}")

            st.markdown("### 💡 Recommended Teaching Action Plan")
            for rec in pedagogy.get("recommendations", []):
                st.markdown(f"➔ **{rec}**")

with tab5:
    st.subheader("📄 Automated PDF Audit Report & Telemetry Export")

    st.write("Generate a formatted PDF document containing session analytics, student rosters, and AI pedagogical recommendations.")

    exp_col1, exp_col2, exp_col3 = st.columns(3)

    with exp_col1:
        if st.button("🔨 Build PDF Report", type="primary", use_container_width=True):
            if df_summary.empty:
                st.warning("⚠️ No telemetry available to generate PDF. Creating template fallback report.")
            
            pdf_path = PDFReportGenerator.generate_pdf(df_summary, pedagogy, duration_sec=max_sec)
            st.success(f"✅ PDF generated successfully!")
            
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 Download PDF Audit Report",
                    data=f.read(),
                    file_name="Classroom_Engagement_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    with exp_col2:
        if not df_raw.empty:
            csv_raw_bytes = df_raw.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Raw Telemetry CSV",
                data=csv_raw_bytes,
                file_name="classroom_telemetry_raw.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Export Raw Telemetry CSV", disabled=True, use_container_width=True)

    with exp_col3:
        if not df_summary.empty:
            csv_sum_bytes = df_summary.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Summary Metrics CSV",
                data=csv_sum_bytes,
                file_name="classroom_60s_summary.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("📥 Export Summary Metrics CSV", disabled=True, use_container_width=True)
