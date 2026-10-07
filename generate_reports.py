import pandas as pd
import os
from core.analytics_engine import AnalyticsEngine
from core.pdf_generator import PDFReportGenerator

CSV_RAW_PATH = "classroom_telemetry_raw.csv"
CSV_SUMMARY_PATH = "classroom_60s_summary.csv"
PDF_PATH = "Classroom_Engagement_Report.pdf"

print("📊 Compiling CSV telemetry records and building automated PDF report...")

if os.path.exists(CSV_RAW_PATH) and os.stat(CSV_RAW_PATH).st_size > 0:
    df_raw = pd.read_csv(CSV_RAW_PATH)
else:
    print("⚠️ Warning: Raw telemetry CSV is empty or missing. Generating baseline metrics.")
    df_raw = pd.DataFrame()

df_summary = AnalyticsEngine.compute_summary(df_raw)
df_summary.to_csv(CSV_SUMMARY_PATH, index=False)
print(f"✅ Summary dataset written to {CSV_SUMMARY_PATH}")

max_sec = int(df_raw["timestamp"].max()) if not df_raw.empty else 60
timeline_series = AnalyticsEngine.compute_timeline(df_raw, max_seconds=max_sec)
pedagogy = AnalyticsEngine.generate_pedagogical_report(df_summary, timeline_series)

PDFReportGenerator.generate_pdf(df_summary, pedagogy, output_path=PDF_PATH, duration_sec=max_sec)
print(f"📄 Executive PDF Audit Report successfully saved to {PDF_PATH}")