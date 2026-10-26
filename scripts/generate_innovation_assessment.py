import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

def add_hyperlink(paragraph, url, text, color="004B87", underline=True):
    """Adds a hyperlink to a Word document paragraph."""
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)

    hyperlink = parse_xml(f'<w:hyperlink xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" r:id="{r_id}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/>')
    new_run = parse_xml(f'<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')
    rPr = parse_xml(f'<w:rPr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>')

    if color:
        c = parse_xml(f'<w:color xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="{color}"/>')
        rPr.append(c)
    if underline:
        u = parse_xml(f'<w:u xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="single"/>')
        rPr.append(u)

    new_run.append(rPr)
    new_run_text = parse_xml(f'<w:t xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{text}</w:t>')
    new_run.append(new_run_text)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

def set_cell_background(cell, hex_color):
    """Sets the background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="clear" w:color="auto" w:fill="{hex_color}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets the internal padding of a table cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def generate_docx(output_path):
    doc = Document()

    # Set Margins (0.6 inch to ensure tight, professional 2-page fit)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.55)
        section.bottom_margin = Inches(0.55)
        section.left_margin = Inches(0.65)
        section.right_margin = Inches(0.65)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

    # Document Header / Title
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    t_run = title_p.add_run("Section 2: Innovation Assessment")
    t_run.font.name = "Arial"
    t_run.font.size = Pt(17)
    t_run.font.bold = True
    t_run.font.color.rgb = RGBColor(0, 51, 102) # Navy Blue

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_before = Pt(0)
    sub_p.paragraph_format.space_after = Pt(6)
    sub_run = sub_p.add_run("Architectural Evolution & Strategic Roadmap for Secure Government Environments")
    sub_run.font.name = "Arial"
    sub_run.font.size = Pt(11)
    sub_run.font.bold = True
    sub_run.font.color.rgb = RGBColor(70, 80, 95)

    # Metadata Panel (Table)
    meta_table = doc.add_table(rows=2, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False

    col_widths = [Inches(3.6), Inches(3.6)]
    for row in meta_table.rows:
        for idx, width in enumerate(col_widths):
            row.cells[idx].width = width

    # Row 1
    c0 = meta_table.cell(0, 0)
    p0 = c0.paragraphs[0]
    p0.paragraph_format.space_after = Pt(2)
    r = p0.add_run("Author: ")
    r.bold = True
    r.font.size = Pt(9)
    add_hyperlink(p0, "https://www.linkedin.com/in/rohit-kumar-srivastava-59921352/", "Rohit Kumar Srivastava (LinkedIn)")
    p0.runs[-1].font.size = Pt(9)

    c1 = meta_table.cell(0, 1)
    p1 = c1.paragraphs[0]
    p1.paragraph_format.space_after = Pt(2)
    r = p1.add_run("Repository: ")
    r.bold = True
    r.font.size = Pt(9)
    add_hyperlink(p1, "https://github.com/RohitKrSrivastava/Agentic-Policy-Analytics", "Agentic-Policy-Analytics (GitHub)")
    p1.runs[-1].font.size = Pt(9)

    # Row 2
    c2 = meta_table.cell(1, 0)
    p2 = c2.paragraphs[0]
    p2.paragraph_format.space_after = Pt(2)
    r = p2.add_run("Target Context: ")
    r.bold = True
    r.font.size = Pt(9)
    r2 = p2.add_run("Singapore Public Sector, WOG, GovTech SG, IMDA")
    r2.font.size = Pt(9)

    c3 = meta_table.cell(1, 1)
    p3 = c3.paragraphs[0]
    p3.paragraph_format.space_after = Pt(2)
    r = p3.add_run("Document Scope: ")
    r.bold = True
    r.font.size = Pt(9)
    r2 = p3.add_run("Executive Engineering & Innovation Strategy Brief")
    r2.font.size = Pt(9)

    for row in meta_table.rows:
        for cell in row.cells:
            set_cell_background(cell, "F1F5F9")
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    # Section 1
    h1 = doc.add_paragraph()
    h1.paragraph_format.space_before = Pt(8)
    h1.paragraph_format.space_after = Pt(3)
    hrun = h1.add_run("1. Executive Summary & Implemented Baseline")
    hrun.font.name = "Arial"
    hrun.font.size = Pt(11)
    hrun.font.bold = True
    hrun.font.color.rgb = RGBColor(0, 51, 102)

    p_exec = doc.add_paragraph()
    p_exec.paragraph_format.space_before = Pt(0)
    p_exec.paragraph_format.space_after = Pt(5)
    p_exec.paragraph_format.line_spacing = 1.05
    p_exec_run = p_exec.add_run(
        "The Agentic Policy Data Analytics Platform demonstrates a production-grade multi-agent foundation for automated "
        "public policy synthesis across Singapore government repositories. Operating in Whole-of-Government (WOG) secure environments "
        "(under GCC 2.0 and IM8 standards) requires transitioning from a single-machine prototype to an air-gapped, privacy-preserving, "
        "and sovereign intelligence backplane. This document articulates concrete architectural evolutions directly grounded in our implementation."
    )
    p_exec_run.font.name = "Calibri"
    p_exec_run.font.size = Pt(9.5)

    # Section 2: Concrete Innovations
    h2 = doc.add_paragraph()
    h2.paragraph_format.space_before = Pt(6)
    h2.paragraph_format.space_after = Pt(3)
    h2_run = h2.add_run("2. Concrete Architectural Evolutions for Secure Government Environments")
    h2_run.font.name = "Arial"
    h2_run.font.size = Pt(11)
    h2_run.font.bold = True
    h2_run.font.color.rgb = RGBColor(0, 51, 102)

    subsections_p1 = [
        ("A. Agent Intelligence, Dynamic Planning & Self-Correction",
         "Implementation Baseline: Our DataCoordinatorAgent evaluates query boundaries and dynamically delegates parameterized subtasks (sector, start_year, end_year) to the DataExtractionAgent.\n"
         "Evolution: Upgrade to a Supervisor-Critic Architecture where an autonomous Critic Agent evaluates intermediate SQL/Pandas outputs for anomalies. If an external API endpoint changes or exhibits schema drift, the Extraction Agent executes autonomous schema reconciliation in an isolated gVisor/Wasm sandbox, self-testing transformations against historical snapshots before reporting."),

        ("B. Real-World Data Challenges: Incomplete Data, Schema Drift & Privacy Enclaves",
         "Implementation Baseline: Our DataQualityEngine performs snake_case normalization, time-series forward fill, median imputation, and 2.5xIQR outlier capping, reporting unconstrained empirical completeness.\n"
         "Evolution: (1) Local Differential Privacy (LDP): Ingesting sensitive microdata (individual CPF contributions, employer retrenchments) by injecting calibrated Laplace noise (ε=0.5, δ=10⁻⁵) into wage aggregations, preserving statistical validity without exposing identifiable payroll records. (2) Dynamic Schema Adapters: Semantic vector embeddings automatically remap evolving Data.gov.sg schema headers (e.g. median_gross_wage_sgd to median_monthly_gross_excl_cpf)."),

        ("C. User Trust, Factuality & Semantic Entailment Verification",
         "Implementation Baseline: Our HallucinationVerificationGuard indexes ground-truth datasets and verifies quantitative claims within a ±1.5% tolerance, detecting fabrications and recording discrepancies.\n"
         "Evolution: Extend verification from numerical claims to qualitative policy logic by embedding Natural Language Inference (NLI) cross-encoders (e.g. DeBERTa-v3). The guard verifies that qualitative findings are logically entailed by authoritative whitepaper chunks retrieved via RAG, creating an auditable cryptographic citation tree for ministerial reviews.")
    ]

    for title, body in subsections_p1:
        sp = doc.add_paragraph()
        sp.paragraph_format.space_before = Pt(4)
        sp.paragraph_format.space_after = Pt(1)
        sr = sp.add_run(title)
        sr.font.name = "Arial"
        sr.font.size = Pt(9.5)
        sr.font.bold = True
        sr.font.color.rgb = RGBColor(20, 45, 85)

        bp = doc.add_paragraph()
        bp.paragraph_format.space_before = Pt(0)
        bp.paragraph_format.space_after = Pt(4)
        bp.paragraph_format.line_spacing = 1.05
        br = bp.add_run(body)
        br.font.name = "Calibri"
        br.font.size = Pt(9.0)

    # Force Page Break to guarantee exact 2-page pagination
    doc.add_page_break()

    # PAGE 2
    subsections_p2 = [
        ("D. Security, Sovereign Enclaves & Whole-of-Government Compliance (IM8 / GCC 2.0)",
         "Implementation Baseline: The system operates with non-root Docker isolation, parameterized SQL queries, CORS headers, and multi-cloud fallback (OpenAI, Gemini, Bedrock).\n"
         "Evolution: In restricted government zones where public cloud LLMs are prohibited by IM8 guidelines, deploy local quantized sovereign foundation models (e.g. Singapore's SEA-LION or Llama-3-70B) via vLLM on on-premise GPU clusters inside Singapore's Government Commercial Cloud (GCC 2.0). Integrate TechPass and Singpass SSO with Role-Based Access Control (RBAC) to enforce classified data redaction."),

        ("E. Scalability & Big Data Policy Simulation (DuckDB & EconML)",
         "Implementation Baseline: In-memory Pandas processes aggregate series in <2 seconds for standard analytical queries.\n"
         "Evolution: Migrate analytical processing to DuckDB / Apache Arrow for vectorized in-process OLAP, handling multi-gigabyte census and labor tables without memory bloat. Integrate Double Machine Learning (EconML) to enable causal policy simulation: analysts can model counterfactual scenarios (e.g. 'What if TeSA conversion subsidies had not been expanded in 2021?') to isolate true treatment effects."),

        ("F. Multi-Agency Collaboration, Knowledge Graph & Shared Blackboard",
         "Implementation Baseline: Thread-safe SQLite blackboard persists session logs and analytical state.\n"
         "Evolution: Establish a unified Policy Knowledge Graph linking datasets across MOM, IMDA, and EDB. Cross-ministry research teams can collaboratively annotate shared policy briefs, fork analytical models, and maintain synchronized versioned policy intelligence."),

        ("G. Multi-Cloud FinOps, Semantic Caching & Cost Optimization",
         "Implementation Baseline: MultiCloudLLMRouter tracks latency and simulated token consumption.\n"
         "Evolution: Implement semantic vector caching (Redis/pgvector) to resolve recurring quarterly policy queries instantaneously (<5ms) with zero LLM API cost. Employ cost-aware tiered routing: lightweight SLMs handle intent classification and schema formatting ($0.075/1M tokens), reserving frontier models exclusively for strategic synthesis, cutting compute costs by >75%.")
    ]

    for title, body in subsections_p2:
        sp = doc.add_paragraph()
        sp.paragraph_format.space_before = Pt(4)
        sp.paragraph_format.space_after = Pt(1)
        sr = sp.add_run(title)
        sr.font.name = "Arial"
        sr.font.size = Pt(9.5)
        sr.font.bold = True
        sr.font.color.rgb = RGBColor(20, 45, 85)

        bp = doc.add_paragraph()
        bp.paragraph_format.space_before = Pt(0)
        bp.paragraph_format.space_after = Pt(4)
        bp.paragraph_format.line_spacing = 1.05
        br = bp.add_run(body)
        br.font.name = "Calibri"
        br.font.size = Pt(9.0)

    # Section 3: Roadmap Table
    h3 = doc.add_paragraph()
    h3.paragraph_format.space_before = Pt(6)
    h3.paragraph_format.space_after = Pt(3)
    h3_run = h3.add_run("3. Phased Implementation Roadmap")
    h3_run.font.name = "Arial"
    h3_run.font.size = Pt(10.5)
    h3_run.font.bold = True
    h3_run.font.color.rgb = RGBColor(0, 51, 102)

    table = doc.add_table(rows=4, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    t_widths = [Inches(1.0), Inches(1.2), Inches(2.2), Inches(2.8)]
    for row in table.rows:
        for idx, width in enumerate(t_widths):
            row.cells[idx].width = width

    headers = ["Phase", "Timeline", "Strategic Focus", "Concrete Deliverables"]
    for idx, text in enumerate(headers):
        cell = table.cell(0, idx)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.bold = True
        run.font.name = "Arial"
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_background(cell, "003366")
        set_cell_margins(cell, top=60, bottom=60, left=80, right=80)

    row_data = [
        ("Phase 1", "Immediate (Q1-Q2)", "Sovereign Core & Security", "vLLM SEA-LION deployment on GCC 2.0; TechPass SSO & RBAC; DuckDB columnar analytics engine."),
        ("Phase 2", "Mid-Term (Q3-Q4)", "Privacy, Trust & Lineage", "Differential Privacy enclaves (ε=0.5); NLI qualitative claim verification; semantic API caching."),
        ("Phase 3", "Strategic (Year 2)", "Causal AI & WOG Ecosystem", "EconML counterfactual policy simulation; cross-agency knowledge graph; self-healing schema adapters.")
    ]

    for r_idx, (p_text, t_text, f_text, d_text) in enumerate(row_data, start=1):
        bg = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate([p_text, t_text, f_text, d_text]):
            cell = table.cell(r_idx, c_idx)
            p = cell.paragraphs[0]
            if c_idx < 2:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(val)
            run.font.name = "Calibri"
            run.font.size = Pt(8.0)
            if c_idx == 0:
                run.bold = True
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=40, bottom=40, left=80, right=80)

    # Conclusion
    h4 = doc.add_paragraph()
    h4.paragraph_format.space_before = Pt(6)
    h4.paragraph_format.space_after = Pt(2)
    h4_run = h4.add_run("4. Conclusion & Value Proposition")
    h4_run.font.name = "Arial"
    h4_run.font.size = Pt(10)
    h4_run.font.bold = True
    h4_run.font.color.rgb = RGBColor(0, 51, 102)

    p_conc = doc.add_paragraph()
    p_conc.paragraph_format.space_before = Pt(0)
    p_conc.paragraph_format.space_after = Pt(0)
    p_conc.paragraph_format.line_spacing = 1.05
    c_run = p_conc.add_run(
        "By grounding multi-agent orchestration in empirical quality measurement, source-grounded discrepancy auditing, "
        "and sovereign enclave deployment, this platform evolves from a functional technical demonstration into a secure, auditable, "
        "and indispensable national policy intelligence infrastructure for the Singapore Public Sector."
    )
    c_run.font.name = "Calibri"
    c_run.font.size = Pt(8.5)

    doc.save(output_path)
    print(f"Word document successfully created: {output_path}")

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print exact 'Page X of Y' page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header rule and text (page 2 only)
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(45, 11 * inch - 36, 8.5 * inch - 45, 11 * inch - 36)
            self.drawString(45, 11 * inch - 30, "GovPolicy AI — Section 2: Innovation Assessment")
            self.drawRightString(8.5 * inch - 45, 11 * inch - 30, "Singapore Public Sector Strategy")

        # Footer rule and text (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(45, 36, 8.5 * inch - 45, 36)
        
        self.drawString(45, 25, "Confidential — Evaluated for Singapore Public Sector (WOG / IMDA / GovTech SG)")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 45, 25, page_str)
        self.restoreState()

def generate_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=42,
        bottomMargin=42
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#003366"),
        spaceAfter=2
    )
    style_subtitle = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5
    )
    style_meta = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )
    style_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#003366"),
        spaceBefore=5,
        spaceAfter=3,
        keepWithNext=True
    )
    style_subhead = ParagraphStyle(
        'SubHead',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=3,
        spaceAfter=1,
        keepWithNext=True
    )
    style_body = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.0,
        leading=10.5,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=3
    )
    style_tbl_hdr = ParagraphStyle(
        'TblHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white,
        alignment=1
    )
    style_tbl_cell = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.0,
        leading=9.0,
        textColor=colors.HexColor("#0F172A")
    )
    style_tbl_cell_center = ParagraphStyle(
        'TblCellCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.0,
        leading=9.0,
        textColor=colors.HexColor("#0F172A"),
        alignment=1
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("Section 2: Innovation Assessment", style_title))
    story.append(Paragraph("Architectural Evolution & Strategic Roadmap for Secure Government Environments", style_subtitle))

    # Metadata Grid
    meta_data = [
        [
            Paragraph("<b>Author:</b> <a href='https://www.linkedin.com/in/rohit-kumar-srivastava-59921352/' color='#004B87'><u>Rohit Kumar Srivastava (LinkedIn)</u></a>", style_meta),
            Paragraph("<b>Repository:</b> <a href='https://github.com/RohitKrSrivastava/Agentic-Policy-Analytics' color='#004B87'><u>Agentic-Policy-Analytics (GitHub)</u></a>", style_meta)
        ],
        [
            Paragraph("<b>Target Context:</b> Singapore Public Sector, WOG, GovTech SG, IMDA", style_meta),
            Paragraph("<b>Document Type:</b> Architectural Assessment & Strategy Brief (Section 2)", style_meta)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 4))

    # 1. Executive Summary
    story.append(Paragraph("1. Executive Summary & Implemented Baseline", style_h1))
    story.append(Paragraph(
        "The <b>Agentic Policy Data Analytics Platform</b> implements a full-stack, multi-agent solution designed to assist "
        "policy researchers, economists, and government analysts in synthesizing evidence-backed insights across heterogeneous Singapore "
        "manpower repositories. Operating in Whole-of-Government (WOG) secure environments under Singapore's <b>Government Commercial Cloud (GCC 2.0)</b> "
        "and <b>Instruction Manual 8 (IM8)</b> standards requires transitioning from a prototype to an air-gapped, privacy-preserving, "
        "and sovereign intelligence backplane. This assessment articulates concrete architectural evolutions directly grounded in our implementation.",
        style_body
    ))

    # 2. Concrete Architectural Evolutions
    story.append(Paragraph("2. Concrete Architectural Evolutions for Secure Government Environments", style_h1))

    subsections_page1 = [
        ("A. Agent Intelligence, Dynamic Planning & Self-Correction",
         "<b>Implementation Baseline:</b> Our <i>DataCoordinatorAgent</i> evaluates query boundaries and dynamically delegates parameterized subtasks (sector, start_year, end_year) to the <i>DataExtractionAgent</i>.<br/>"
         "<b>Evolution:</b> Upgrade to a Supervisor-Critic Architecture where an autonomous Critic Agent evaluates intermediate SQL/Pandas outputs for anomalies. If an external API endpoint changes or exhibits schema drift, the Extraction Agent executes autonomous schema reconciliation in an isolated gVisor/Wasm sandbox, self-testing transformations against historical snapshots before reporting."),

        ("B. Real-World Data Challenges: Incomplete Data, Schema Drift & Privacy Enclaves",
         "<b>Implementation Baseline:</b> Our <i>DataQualityEngine</i> performs snake_case normalization, time-series forward fill, median imputation, and 2.5×IQR outlier capping, reporting unconstrained empirical completeness.<br/>"
         "<b>Evolution:</b> (1) <i>Local Differential Privacy (LDP)</i>: Ingesting sensitive microdata (individual CPF contributions, employer retrenchments) by injecting calibrated Laplace noise (ε=0.5, δ=10⁻⁵) into wage aggregations, preserving statistical validity without exposing identifiable payroll records. (2) <i>Dynamic Schema Adapters</i>: Semantic vector embeddings automatically remap evolving Data.gov.sg schema headers (e.g. <code>median_gross_wage_sgd</code> to <code>median_monthly_gross_excl_cpf</code>)."),

        ("C. User Trust, Factuality & Semantic Entailment Verification",
         "<b>Implementation Baseline:</b> Our <i>HallucinationVerificationGuard</i> indexes ground-truth datasets and verifies quantitative claims within a ±1.5% tolerance, detecting fabrications and recording discrepancies.<br/>"
         "<b>Evolution:</b> Extend verification from numerical claims to qualitative policy logic by embedding Natural Language Inference (NLI) cross-encoders (e.g. DeBERTa-v3). The guard verifies that qualitative findings are logically entailed by authoritative whitepaper chunks retrieved via RAG, creating an auditable cryptographic citation tree for ministerial reviews.")
    ]

    for title, text in subsections_page1:
        story.append(Paragraph(title, style_subhead))
        story.append(Paragraph(text, style_body))

    # Page Break to Page 2
    story.append(PageBreak())

    subsections_page2 = [
        ("D. Security, Sovereign Enclaves & Whole-of-Government Compliance (IM8 / GCC 2.0)",
         "<b>Implementation Baseline:</b> The system operates with non-root Docker isolation, parameterized SQL queries, CORS headers, and multi-cloud fallback (OpenAI, Gemini, Bedrock).<br/>"
         "<b>Evolution:</b> In restricted government zones where public cloud LLMs are prohibited by IM8 guidelines, deploy local quantized sovereign foundation models (e.g. Singapore's SEA-LION or Llama-3-70B) via vLLM on on-premise GPU clusters inside Singapore's Government Commercial Cloud (GCC 2.0). Integrate TechPass and Singpass SSO with Role-Based Access Control (RBAC) to enforce classified data redaction."),

        ("E. Scalability & Big Data Policy Simulation (DuckDB & EconML)",
         "<b>Implementation Baseline:</b> In-memory Pandas processes aggregate series in <2 seconds for standard analytical queries.<br/>"
         "<b>Evolution:</b> Migrate analytical processing to DuckDB / Apache Arrow for vectorized in-process OLAP, handling multi-gigabyte census and labor tables without memory bloat. Integrate Double Machine Learning (EconML) to enable causal policy simulation: analysts can model counterfactual scenarios (e.g. <i>'What if TeSA conversion subsidies had not been expanded in 2021?'</i>) to isolate true treatment effects."),

        ("F. Multi-Agency Collaboration, Knowledge Graph & Shared Blackboard",
         "<b>Implementation Baseline:</b> Thread-safe SQLite blackboard persists session logs and analytical state.<br/>"
         "<b>Evolution:</b> Establish a unified Policy Knowledge Graph linking datasets across MOM, IMDA, and EDB. Cross-ministry research teams can collaboratively annotate shared policy briefs, fork analytical models, and maintain synchronized versioned policy intelligence."),

        ("G. Multi-Cloud FinOps, Semantic Caching & Cost Optimization",
         "<b>Implementation Baseline:</b> MultiCloudLLMRouter tracks latency and simulated token consumption.<br/>"
         "<b>Evolution:</b> Implement semantic vector caching (Redis/pgvector) to resolve recurring quarterly policy queries instantaneously (<5ms) with zero LLM API cost. Employ cost-aware tiered routing: lightweight SLMs handle intent classification and schema formatting ($0.075/1M tokens), reserving frontier models exclusively for strategic synthesis, cutting compute costs by >75%.")
    ]

    for title, text in subsections_page2:
        story.append(Paragraph(title, style_subhead))
        story.append(Paragraph(text, style_body))

    # 3. Phased Implementation Roadmap
    story.append(Paragraph("3. Phased Implementation Roadmap", style_h1))

    roadmap_data = [
        [
            Paragraph("Phase", style_tbl_hdr),
            Paragraph("Timeline", style_tbl_hdr),
            Paragraph("Strategic Focus", style_tbl_hdr),
            Paragraph("Concrete Deliverables", style_tbl_hdr)
        ],
        [
            Paragraph("<b>Phase 1</b>", style_tbl_cell_center),
            Paragraph("Immediate (Q1-Q2)", style_tbl_cell_center),
            Paragraph("<b>Sovereign Core & Security</b>", style_tbl_cell),
            Paragraph("vLLM SEA-LION deployment on GCC 2.0; TechPass SSO & RBAC; DuckDB columnar analytics engine.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Phase 2</b>", style_tbl_cell_center),
            Paragraph("Mid-Term (Q3-Q4)", style_tbl_cell_center),
            Paragraph("<b>Privacy, Trust & Lineage</b>", style_tbl_cell),
            Paragraph("Differential Privacy enclaves (ε=0.5); NLI qualitative claim verification; semantic API caching.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Phase 3</b>", style_tbl_cell_center),
            Paragraph("Strategic (Year 2)", style_tbl_cell_center),
            Paragraph("<b>Causal AI & WOG Ecosystem</b>", style_tbl_cell),
            Paragraph("EconML counterfactual policy simulation; cross-agency knowledge graph; self-healing schema adapters.", style_tbl_cell)
        ]
    ]

    roadmap_table = Table(roadmap_data, colWidths=[55, 80, 140, 245])
    roadmap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F8FAFC")),
        ('BACKGROUND', (0, 2), (-1, 2), colors.white),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#F8FAFC")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(roadmap_table)

    # 4. Conclusion
    story.append(Paragraph("4. Conclusion & Value Proposition", style_h1))
    story.append(Paragraph(
        "By grounding multi-agent orchestration in empirical quality measurement, source-grounded discrepancy auditing, "
        "and sovereign enclave deployment, this platform evolves from a functional technical demonstration into a secure, auditable, "
        "and indispensable national policy intelligence infrastructure for the Singapore Public Sector.",
        style_body
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF document successfully created: {output_path}")

if __name__ == "__main__":
    docx_out = sys.argv[1] if len(sys.argv) > 1 else "INNOVATION_ASSESSMENT.docx"
    pdf_out = sys.argv[2] if len(sys.argv) > 2 else "INNOVATION_ASSESSMENT.pdf"
    
    generate_docx(docx_out)
    generate_pdf(pdf_out)
