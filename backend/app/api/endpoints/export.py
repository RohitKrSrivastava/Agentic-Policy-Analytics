import io
import json

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from backend.app.core.database import DBAnalysisSession, get_db

router = APIRouter()

@router.get("/{session_id}/markdown", response_class=PlainTextResponse)
def export_markdown_report(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if not sess or not sess.report_json:
        raise HTTPException(status_code=404, detail="Report not generated for this session.")

    report = json.loads(sess.report_json)

    md_lines = [
        f"# {report.get('title', 'Singapore Policy Analytics Report')}",
        f"**Generated**: {report.get('generated_at', '')} | **Session ID**: `{session_id}`",
        f"**Query**: *\"{sess.query}\"*",
        f"**LLM Engine**: `{sess.llm_provider_used}` | **Quality Score**: `{report.get('quality_score')}%` | **Hallucination Score**: `{report.get('hallucination_score')}`",
        "\n---\n",
        "## Executive Summary",
        report.get("executive_summary", ""),
        "\n---\n",
        "## Key Findings",
    ]

    for finding in report.get("key_findings", []):
        md_lines.append(f"### {finding.get('heading')}")
        md_lines.append(finding.get("body", ""))
        md_lines.append(f"- **Statistical Evidence**: {finding.get('statistical_evidence')}")
        md_lines.append(f"- **Citation**: `{finding.get('citation_id')}`")
        md_lines.append("")

    md_lines.append("## Policy Recommendations")
    for rec in report.get("policy_recommendations", []):
        md_lines.append(f"1. {rec}")

    md_lines.append("\n## Data Source Citations & Audit Trail")
    for cit in report.get("citations", []):
        md_lines.append(f"- **[{cit.get('citation_id')}]** {cit.get('source_agency')} — *{cit.get('dataset_title')}* ({cit.get('time_period')}). Access Method: {cit.get('access_method')}")

    content = "\n".join(md_lines)
    return PlainTextResponse(
        content=content,
        headers={"Content-Disposition": f"attachment; filename=policy_report_{session_id}.md"}
    )

@router.get("/{session_id}/json")
def export_json_bundle(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    bundle = {
        "session_id": sess.id,
        "query": sess.query,
        "status": sess.status,
        "created_at": str(sess.created_at),
        "llm_provider_used": sess.llm_provider_used,
        "charts": json.loads(sess.charts_json) if sess.charts_json else [],
        "quality_reports": json.loads(sess.quality_json) if sess.quality_json else [],
        "report": json.loads(sess.report_json) if sess.report_json else None
    }

    return Response(
        content=json.dumps(bundle, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=policy_analysis_{session_id}.json"}
    )

@router.get("/{session_id}/pdf")
def export_pdf_report(session_id: str, db: Session = Depends(get_db)):
    sess = db.query(DBAnalysisSession).filter(DBAnalysisSession.id == session_id).first()
    if not sess or not sess.report_json:
        raise HTTPException(status_code=404, detail="Report not ready for PDF generation.")

    report = json.loads(sess.report_json)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#0F172A'), spaceAfter=10)
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#64748B'), spaceAfter=15)
    h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#1E293B'), spaceBefore=12, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor('#334155'), spaceAfter=8)
    bold_lead = ParagraphStyle('BoldLead', parent=styles['Normal'], fontSize=10, leading=14, fontName="Helvetica-Bold", textColor=colors.HexColor('#1E293B'), spaceBefore=6)

    elements = []

    # Title & Metadata
    elements.append(Paragraph(report.get("title", "Singapore Policy Research Analysis"), title_style))
    elements.append(Paragraph(f"<b>Session ID:</b> {session_id} | <b>Provider:</b> {sess.llm_provider_used} | <b>Date:</b> {str(sess.created_at)[:10]}", meta_style))
    elements.append(Spacer(1, 10))

    # Executive Summary
    elements.append(Paragraph("Executive Summary", h2_style))
    elements.append(Paragraph(report.get("executive_summary", ""), body_style))
    elements.append(Spacer(1, 10))

    # Key Findings
    elements.append(Paragraph("Key Findings & Evidence", h2_style))
    for f in report.get("key_findings", []):
        elements.append(Paragraph(f"<b>{f.get('heading')}</b>", bold_lead))
        elements.append(Paragraph(f.get("body", ""), body_style))
        elements.append(Paragraph(f"<i>Evidence:</i> {f.get('statistical_evidence')} (Ref: {f.get('citation_id')})", meta_style))
        elements.append(Spacer(1, 4))

    # Policy Recommendations
    elements.append(Paragraph("Strategic Policy Recommendations", h2_style))
    for idx, rec in enumerate(report.get("policy_recommendations", []), start=1):
        elements.append(Paragraph(f"<b>{idx}.</b> {rec}", body_style))

    # Citations Table
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Authoritative Data Citations", h2_style))
    table_data = [["Agency", "Dataset Reference", "Period", "Method"]]
    for c in report.get("citations", []):
        table_data.append([c.get("source_agency", "")[:25], c.get("dataset_title", "")[:35], c.get("time_period", ""), c.get("access_method", "")[:25]])

    t = Table(table_data, colWidths=[120, 180, 100, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    elements.append(t)

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=policy_report_{session_id}.pdf"}
    )
