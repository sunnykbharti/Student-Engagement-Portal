import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from core.analytics_engine import AnalyticsEngine

CSV_RAW_PATH = "classroom_telemetry_raw.csv"

if os.path.exists(CSV_RAW_PATH) and os.stat(CSV_RAW_PATH).st_size > 0:
    df_raw = pd.read_csv(CSV_RAW_PATH)
    max_sec = int(df_raw["timestamp"].max()) if not df_raw.empty else 60
else:
    print("⚠️ Warning: No raw telemetry logs found. Creating baseline plot.")
    df_raw = pd.DataFrame()
    max_sec = 60

timeline_series = AnalyticsEngine.compute_timeline(df_raw, max_seconds=max_sec)

# Render dark-themed engagement plot
plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'default')
fig, ax = plt.subplots(figsize=(11, 5), facecolor='#0f172a')
ax.set_facecolor('#1e293b')

ax.plot(timeline_series.index, timeline_series.values, color='#10b981', linewidth=2.5, label='Classroom Focus Index (%)')
ax.fill_between(timeline_series.index, timeline_series.values, color='#10b981', alpha=0.15)

ax.set_title("Classroom Focus & Engagement Index Trajectory", fontsize=14, fontweight='bold', color='#f8fafc', pad=15)
ax.set_xlabel("Timeline Duration (Seconds)", fontsize=11, fontweight='semibold', color='#94a3b8', labelpad=10)
ax.set_ylabel("Classroom Average Focus Score (%)", fontsize=11, fontweight='semibold', color='#94a3b8', labelpad=10)

ax.set_xlim(1, max_sec)
ax.set_ylim(0, 100)
ax.tick_params(colors='#94a3b8', labelsize=9)
ax.grid(True, color='#334155', linestyle='--', alpha=0.6)

ax.axhline(50, color='#ef4444', linestyle=':', alpha=0.7, label='Critical Attention Alert Baseline (50%)')
ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f8fafc', loc='upper right')

plt.tight_layout()
output_image = "Classroom_Activity_Intensity_Plot.png"
plt.savefig(output_image, dpi=300, facecolor=fig.get_facecolor())
print(f"📈 Timeline engagement intensity plot saved to {output_image}")