import pandas as pd
import numpy as np

class AnalyticsEngine:
    """
    Analytics & Pedagogical Intelligence Engine for Classroom Behavior Telemetry.
    Translates raw frame-by-frame student telemetry into executive insights,
    engagement scores, drop-off alerts, and individual student risk profiles.
    """
    
    @staticmethod
    def compute_summary(df_raw, custom_names=None):
        """
        Processes raw telemetry dataframe and aggregates metrics per student.
        """
        if df_raw is None or df_raw.empty:
            return pd.DataFrame(columns=[
                "Student ID", "Display Name", "Focused Duration (s)", 
                "Interaction Duration (s)", "Distraction Count", 
                "Engagement Score (%)", "Attention Level"
            ])

        summary_rows = []
        unique_students = df_raw["student_id"].unique()

        for student in unique_students:
            s_df = df_raw[df_raw["student_id"] == student].sort_values(by="timestamp").copy()
            
            focused_secs = len(s_df[s_df["behavior"] == "focused"])
            interaction_secs = len(s_df[s_df["behavior"] == "interacting with teacher"])
            phone_secs = len(s_df[s_df["behavior"] == "using phone"])
            slouch_secs = len(s_df[s_df["behavior"] == "drowsy / slouching"])
            total_observed = max(1, len(s_df))

            # Discrete incident flips
            s_df["state_change"] = s_df["behavior"].ne(s_df["behavior"].shift())
            distraction_events = len(
                s_df[(s_df["behavior"].isin(["using phone", "drowsy / slouching"])) & (s_df["state_change"] == True)]
            )

            # Quantitative score calculation (0 - 100)
            raw_score = ((focused_secs + 1.2 * interaction_secs) / total_observed) * 100.0 - (distraction_events * 8.0)
            score = float(np.clip(raw_score, 0.0, 100.0))

            # Attention Level Rating
            if score >= 80:
                level = "🟢 High Attention"
            elif score >= 55:
                level = "🟡 Moderate"
            else:
                level = "🔴 Needs Attention"

            display_name = custom_names.get(student, student) if custom_names else student

            summary_rows.append({
                "Student ID": student,
                "Display Name": display_name,
                "Focused Duration (s)": focused_secs,
                "Interaction Duration (s)": interaction_secs,
                "Phone Usage (s)": phone_secs,
                "Slouch Duration (s)": slouch_secs,
                "Distraction Count": distraction_events,
                "Total Observed (s)": total_observed,
                "Engagement Score (%)": round(score, 1),
                "Attention Level": level
            })

        df_summary = pd.DataFrame(summary_rows)
        return df_summary

    @staticmethod
    def compute_timeline(df_raw, max_seconds=60):
        """
        Generates continuous second-by-second average classroom engagement score trajectory.
        """
        if df_raw is None or df_raw.empty:
            timeline_idx = list(range(1, max_seconds + 1))
            return pd.Series(0, index=timeline_idx)

        unique_students = df_raw["student_id"].unique()
        timeline_idx = list(range(1, max_seconds + 1))
        reconstructed = []

        behavior_scores = {
            "focused": 100,
            "interacting with teacher": 120,
            "using phone": 20,
            "drowsy / slouching": 10
        }

        for student in unique_students:
            s_df = df_raw[df_raw["student_id"] == student].drop_duplicates(subset=["timestamp"]).copy()
            s_df = s_df.set_index("timestamp").reindex(timeline_idx)
            s_df["behavior"] = s_df["behavior"].ffill(limit=3).fillna("focused")
            s_df["score"] = s_df["behavior"].map(behavior_scores)
            reconstructed.append(s_df["score"])

        if reconstructed:
            avg_timeline = pd.concat(reconstructed, axis=1).mean(axis=1)
            # Clip between 0 and 100
            return avg_timeline.clip(0, 100)
        else:
            return pd.Series(0, index=timeline_idx)

    @staticmethod
    def generate_pedagogical_report(df_summary, timeline_series):
        """
        Returns structured pedagogical evaluation & automated teaching tips.
        """
        if df_summary.empty:
            return {
                "overall_grade": "N/A",
                "avg_engagement": 0.0,
                "insights": ["No student tracking telemetry captured in this session window."],
                "recommendations": ["Ensure camera visibility and lighting are optimized for video tracking."]
            }

        avg_score = df_summary["Engagement Score (%)"].mean()
        total_distractions = df_summary["Distraction Count"].sum()
        total_interactions = df_summary["Interaction Duration (s)"].sum()

        if avg_score >= 85:
            grade = "A+ (Outstanding)"
        elif avg_score >= 75:
            grade = "A (Excellent)"
        elif avg_score >= 65:
            grade = "B (Good)"
        elif avg_score >= 50:
            grade = "C (Satisfactory)"
        else:
            grade = "D (Action Required)"

        insights = []
        recommendations = []

        # Insight 1: Engagement level
        insights.append(f"Overall Class Engagement Average is **{avg_score:.1f}%** ({grade}).")

        # Insight 2: Interaction rate
        if total_interactions > 15:
            insights.append("High student-teacher interaction detected! Active participation is strong.")
        else:
            insights.append("Low student interaction observed during this evaluation window.")
            recommendations.append("Consider incorporating cold-calling or polling questions to boost active engagement.")

        # Insight 3: Distraction alerts
        high_risk_students = df_summary[df_summary["Engagement Score (%)"] < 55]
        if not high_risk_students.empty:
            student_list = ", ".join(high_risk_students["Display Name"].tolist())
            insights.append(f"⚠️ **Attention Alert**: {len(high_risk_students)} student(s) showed high distraction levels ({student_list}).")
            recommendations.append("Re-seat distracted students closer to the instructor platform or check for digital distraction sources.")

        # Insight 4: Timeline Dips
        if not timeline_series.empty:
            min_sec = timeline_series.idxmin()
            min_val = timeline_series.min()
            if min_val < 50:
                insights.append(f"📉 Engagement reached its lowest point ({min_val:.0f}%) at **{min_sec}s**.")
                recommendations.append(f"Review lecture material covered around second {min_sec}—this segment experienced an attention dip.")

        if not recommendations:
            recommendations.append("Classroom focus is optimal. Maintain current instructional pacing and interactive rhythm.")

        return {
            "overall_grade": grade,
            "avg_engagement": round(avg_score, 1),
            "insights": insights,
            "recommendations": recommendations
        }
