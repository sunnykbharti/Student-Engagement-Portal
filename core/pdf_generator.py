import os
import time
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class PDFReportGenerator:
    """
    Automated PDF Report Builder using ReportLab.
    Produces executive classroom engagement audits for professors.
    """
    @staticmethod
    def generate_pdf(df_summary, pedagogy_data, output_path="Classroom_Engagement_Report.pdf", duration_sec=60):
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        
        # Color Palette
        PRIMARY = colors.HexColor('#0F172A')   # Slate Dark
        ACCENT = colors.HexColor('#10B981')    # Emerald
        TEXT_MUTED = colors.HexColor('#64748B')# Gray Muted
        BG_LIGHT = colors.HexColor('#F8FAFC')  # Soft Gray
        
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=PRIMARY,
            fontName='Helvetica-Bold',
            spaceAfter=4
        )
        
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=TEXT_MUTED,
            fontName='Helvetica',
            spaceAfter=15
        )

        h2_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=13,
            leading=16,
            textColor=PRIMARY,
            fontName='Helvetica-Bold',
            spaceBefore=12,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'BodyCustom',
            parent=styles['Normal'],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#334155')
        )

        bullet_style = ParagraphStyle(
            'BulletCustom',
            parent=body_style,
            leftIndent=12,
            spaceAfter=4
        )

        story = []

        # 1. Header Title & Metadata
        story.append(Paragraph("🎓 Executive Classroom Behavioral Performance Audit", title_style))
        current_time_str = time.strftime("%B %d, %Y - %H:%M:%S")
        story.append(Paragraph(f"AI Cell Analytics Core • Timestamp: {current_time_str} • Session Window: {duration_sec}s", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=15))

        # 2. Executive Overview Table
        total_students = len(df_summary) if not df_summary.empty else 0
        avg_score = pedagogy_data.get("avg_engagement", 0.0)
        grade = pedagogy_data.get("overall_grade", "N/A")

        summary_table_data = [
            ["Metric Parameter", "Audit Value", "Status Benchmark"],
            ["Total Headcount Tracked", f"{total_students} Students", "Verified"],
            ["Classroom Focus Score", f"{avg_score}%", grade],
            ["Evaluation Window Duration", f"{duration_sec} Seconds", "1 FPS Telemetry"]
        ]

        t_summary = Table(summary_table_data, colWidths=[180, 160, 180])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 15))

        # 3. Student Roster Audit Table
        story.append(Paragraph("📋 Individual Student Performance Breakdown", h2_style))
        
        if df_summary.empty:
            story.append(Paragraph("<i>No student tracking telemetry logged for this interval window.</i>", body_style))
        else:
            table_headers = ["Student ID", "Display Name", "Focused (s)", "Interactions", "Phone Offenses", "Score (%)", "Attention Level"]
            roster_data = [table_headers]

            for _, row in df_summary.iterrows():
                roster_data.append([
                    str(row.get("Student ID", "")),
                    str(row.get("Display Name", "")),
                    f"{row.get('Focused Duration (s)', 0)}s",
                    f"{row.get('Interaction Duration (s)', 0)}s",
                    str(row.get("Distraction Count", 0)),
                    f"{row.get('Engagement Score (%)', 0)}%",
                    str(row.get("Attention Level", ""))
                ])

            t_roster = Table(roster_data, colWidths=[70, 100, 65, 70, 75, 65, 95])
            t_roster.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t_roster)

        story.append(Spacer(1, 15))

        # 4. AI Pedagogy Insights & Recommendations
        story.append(Paragraph("🧠 Pedagogical Intelligence & Action Plan", h2_style))
        
        insights = pedagogy_data.get("insights", [])
        for insight in insights:
            story.append(Paragraph(f"• {insight}", bullet_style))
        
        story.append(Spacer(1, 8))
        story.append(Paragraph("<b>Recommended Teaching Strategy Adjustments:</b>", body_style))
        
        recommendations = pedagogy_data.get("recommendations", [])
        for rec in recommendations:
            story.append(Paragraph(f"➜ {rec}", bullet_style))

        # Build document
        doc.build(story)
        print(f"📄 PDF Audit Report successfully generated and written to {output_path}")
        return output_path
