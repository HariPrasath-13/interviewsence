import os
import sqlite3
import json
from datetime import datetime
import numpy as np

# ReportLab libraries
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line

import database as db

class NumberedCanvas(canvas.Canvas):
    """
    Custom canvas that performs two-pass rendering to dynamically compute total pages
    and add high-fidelity headers and footers to every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_decorations(page_count)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        self.saveState()
        
        # 1. Header (only on page 2 and onwards, keep cover page clean)
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#1e293b"))
            self.drawString(54, 755, "INTERVIEWSENSE — AI POWERED MOCK INTERVIEW FEEDBACK")
            
            # Subtle header divider line
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 747, 558, 747)
            
        # 2. Footer (on all pages)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4f46e5"))
        self.drawString(54, 38, "INTERVIEWSENSE")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawString(140, 38, "|   Confidential Mock Interview Analytics & Recommendation Report")
        
        # Page numbering
        self.drawRightString(558, 38, f"Page {self._pageNumber} of {page_count}")
        
        # Subtle footer divider line
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        
        self.restoreState()


class ReportGenerator:
    def __init__(self, db_path, reports_dir):
        self.db_path = db_path
        self.reports_dir = reports_dir

    def format_duration(self, seconds):
        """Converts float seconds into MM:SS format."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    def generate_pdf_report(self, session_id):
        """
        Retrieves database session results and exports a highly styled
        PDF summary of interview expressions and personalized feedback.
        """
        session = db.get_session(self.db_path, session_id)
        if not session:
            print(f"Error: Session {session_id} not found in DB.")
            return None

        details = db.get_session_details(self.db_path, session_id)
        
        pdf_filename = f"{session_id}.pdf"
        pdf_path = os.path.join(self.reports_dir, pdf_filename)
        
        # Margins: 0.75 in (54 pt) from left/right, top 1.0 in (72 pt) and bottom 1.0 in (72 pt)
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=72,
            bottomMargin=72
        )
        
        styles = getSampleStyleSheet()
        
        # Custom Typography Styles
        title_style = ParagraphStyle(
            name='CoverTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=6
        )
        
        subtitle_style = ParagraphStyle(
            name='CoverSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=25
        )
        
        h1_style = ParagraphStyle(
            name='SectionHeading',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=15,
            spaceAfter=8,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            name='StandardBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=10
        )
        
        bold_body_style = ParagraphStyle(
            name='BoldBody',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        recommendation_style = ParagraphStyle(
            name='RecommendationText',
            parent=body_style,
            fontName='Helvetica-Oblique',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1e293b")
        )
        
        story = []
        
        # ------------------ FIRST PAGE HEADER & TITLE ------------------
        story.append(Paragraph("InterviewSense", title_style))
        story.append(Paragraph("Artificial Intelligence Mock Interview Reflection Report", subtitle_style))
        story.append(Spacer(1, 15))
        
        # ------------------ METADATA SUMMARY TABLE ------------------
        # Convert timestamp to human readable format
        try:
            db_date = datetime.strptime(session['timestamp'], '%Y-%m-%d %H:%M:%S')
            display_date = db_date.strftime('%B %d, %Y at %I:%M %p')
        except:
            display_date = session['timestamp']
            
        metadata_data = [
            [
                Paragraph("<b>Mock Interview Metadata</b>", bold_body_style),
                ""
            ],
            [
                Paragraph(f"<b>Session Reference ID:</b> {session_id}", body_style),
                Paragraph(f"<b>Interview Date:</b> {display_date}", body_style)
            ],
            [
                Paragraph(f"<b>Practice Duration:</b> {self.format_duration(session['duration'])}", body_style),
                Paragraph(f"<b>Avg Detection Confidence:</b> {session['average_confidence']:.1f}%", body_style)
            ]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[252, 252])
        metadata_table.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('BACKGROUND', (0, 0), (-1, 0)),
            ('TEXTCOLOR', (0, 0), (-1, 0)),
            ('BACKGROUND', (0, 1), (-1, -1)),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor("#4f46e5")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 15))
        
        # ------------------ DETAILED EMOTION SCORECARDS ------------------
        story.append(Paragraph("Expression Summary Analysis", h1_style))
        
        # Build raw counts of emotions and general percentages
        emotion_counts = {}
        for d in details:
            emotion_counts[d['emotion']] = emotion_counts.get(d['emotion'], 0) + 1
            
        dominant_em = session['dominant_emotion'].title()
        
        summary_table_data = [
            [
                Paragraph("<b>Dominant Emotion State</b>", bold_body_style),
                Paragraph("<b>Positive Signals</b>", bold_body_style),
                Paragraph("<b>Neutral Signals</b>", bold_body_style),
                Paragraph("<b>Negative Signals</b>", bold_body_style)
            ],
            [
                Paragraph(f"<font size=14 color='#4f46e5'><b>{dominant_em}</b></font>", body_style),
                Paragraph(f"<font size=14 color='#10b981'><b>{session['positive_pct']:.1f}%</b></font>", body_style),
                Paragraph(f"<font size=14 color='#6b7280'><b>{session['neutral_pct']:.1f}%</b></font>", body_style),
                Paragraph(f"<font size=14 color='#ef4444'><b>{session['negative_pct']:.1f}%</b></font>", body_style)
            ]
        ]
        
        summary_table = Table(summary_table_data, colWidths=[126, 126, 126, 126])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0)),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1)),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 15))

        # ------------------ EMOTIONAL DISTRIBUTION CHART ------------------
        story.append(Paragraph("Comparative Emotional Distribution", h1_style))
        story.append(Paragraph("This chart shows the breakdown of individual expressions detected throughout the session, reflecting how open or focused your posture appeared.", body_style))
        
        # Custom representation of a bar chart in reportlab
        # Let's count emotion occurrences
        detailed_emotions_list = ['happy', 'surprise', 'neutral', 'sad', 'angry', 'fear', 'disgust']
        total_frames = len(details) if len(details) > 0 else 1
        
        chart_rows = []
        chart_rows.append([Paragraph("<b>Emotion</b>", bold_body_style), 
                           Paragraph("<b>Samples Detected</b>", bold_body_style), 
                           Paragraph("<b>Visual Distribution %</b>", bold_body_style)])
        
        # Color palettes for emotions
        emotion_colors = {
            'happy': '#10b981',    # Teal/Green
            'surprise': '#3b82f6', # Blue
            'neutral': '#6b7280',  # Slate/Gray
            'sad': '#f59e0b',      # Orange
            'angry': '#ef4444',    # Red
            'fear': '#8b5cf6',     # Purple
            'disgust': '#ec4899'   # Pink
        }
        
        for em in detailed_emotions_list:
            count = emotion_counts.get(em, 0)
            percentage = (count / total_frames) * 100
            
            # Draw a colored progress bar
            bar_width = int(percentage * 2.5) # Scale factor so 100% is 250 pt max
            drawing = Drawing(260, 12)
            if bar_width > 0:
                drawing.add(Rect(0, 1, bar_width, 10, fillColor=colors.HexColor(emotion_colors[em]), strokeColor=None))
            # Append percentage label
            drawing.add(String(bar_width + 5, 2, f"{percentage:.1f}%", fontName="Helvetica", fontSize=8, fillColor=colors.HexColor("#334155")))
            
            chart_rows.append([
                Paragraph(em.title(), body_style),
                Paragraph(str(count), body_style),
                drawing
            ])
            
        chart_table = Table(chart_rows, colWidths=[100, 120, 284])
        chart_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0)),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(chart_table)
        story.append(Spacer(1, 15))

        # ------------------ TIMELINE SECTION ------------------
        story.append(Paragraph("Practice Session Timeline (Expression Over Time)", h1_style))
        story.append(Paragraph("The grid below maps how your expressions shifted across different stages of the practice, indicating facial response triggers or stress responses at specific offsets.", body_style))
        
        # Sample up to 10 points
        if len(details) > 0:
            sample_count = min(10, len(details))
            sampled_indices = np.linspace(0, len(details) - 1, sample_count, dtype=int)
            timeline_data = [details[idx] for idx in sampled_indices]
            
            timeline_table_headers = [Paragraph("<b>Time Offset</b>", bold_body_style)]
            timeline_table_emotions = [Paragraph("<b>Emotion</b>", bold_body_style)]
            timeline_table_conf = [Paragraph("<b>Confidence</b>", bold_body_style)]
            
            for item in timeline_data:
                offset_str = self.format_duration(item['elapsed_seconds'])
                timeline_table_headers.append(Paragraph(offset_str, body_style))
                
                # Check dominant emotion
                em_name = item['emotion'].title()
                col = emotion_colors.get(item['emotion'], '#334155')
                timeline_table_emotions.append(Paragraph(f"<font color='{col}'><b>{em_name}</b></font>", body_style))
                timeline_table_conf.append(Paragraph(f"{item['confidence']:.0f}%", body_style))
                
            timeline_table_rows = [
                timeline_table_headers,
                timeline_table_emotions,
                timeline_table_conf
            ]
            
            # Calculate dynamic column width: First column takes 84 pt, the remaining 10 take 42 pt.
            col_widths = [84] + [42] * len(timeline_data)
            
            timeline_table = Table(timeline_table_rows, colWidths=col_widths)
            timeline_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1)),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(timeline_table)
        else:
            story.append(Paragraph("Insufficient timeline events logged for this session.", body_style))
            
        story.append(Spacer(1, 15))

        # ------------------ PERSONALIZED RECOMMENDATIONS ------------------
        recommendations_box_data = [
            [Paragraph("<b>Artificial Intelligence Personalized Coaching Recommendations</b>", bold_body_style)],
            [Paragraph(session['recommendations'], recommendation_style)]
        ]
        
        recommendations_table = Table(recommendations_box_data, colWidths=[504])
        recommendations_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1)),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1.0, colors.HexColor("#4f46e5")),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        
        story.append(KeepTogether([
            Paragraph("Feedback & Next Steps", h1_style),
            recommendations_table,
            Spacer(1, 15),
            Paragraph("<b>Disclaimer:</b> The emotion metrics are gathered automatically using computer vision algorithms tracking facial postures only. They reflect visual presentation state and do not measure core analytical competence or predict direct success.", ParagraphStyle('Disc', parent=body_style, fontSize=8, textColor=colors.HexColor('#94a3b8')))
        ]))
        
        # Build the document
        doc.build(story, canvasmaker=NumberedCanvas)
        return pdf_path
