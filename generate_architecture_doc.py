# Objective: Generates system architecture PDF documentation containing layered diagrams and specifications.
"""
Automotive QA Intelligence - Professional Architecture Documentation Generator
Generates a comprehensive, enterprise-grade PDF explaining the complete system
architecture, workflow, and implementation details.
"""
import os

import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Location: generate_architecture_doc.py

# ═══════════════════════════════════════════════════════════════════════════════
#  CUSTOM CANVAS WITH HEADER/FOOTER DECORATIONS
# ═══════════════════════════════════════════════════════════════════════════════
class EnterpriseCanvas(canvas.Canvas):
    """Custom canvas with corporate header bar, footer, page numbering."""
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
            self._draw_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, page_count):
        self.saveState()
        w, h = letter

        # ── Top accent bar ──
        self.setFillColor(colors.HexColor('#0f172a'))
        self.rect(0, h - 28, w, 28, fill=True, stroke=False)
        self.setFillColor(colors.HexColor('#0ea5e9'))
        self.rect(0, h - 32, w, 4, fill=True, stroke=False)

        # Header text inside dark bar
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.white)
        self.drawString(54, h - 20, "AUTOMOTIVE QA INTELLIGENCE — SYSTEM ARCHITECTURE DOCUMENTATION")
        self.setFont("Helvetica", 7.5)
        self.drawRightString(w - 54, h - 20, f"v1.1 | {datetime.datetime.now().strftime('%B %d, %Y')}")

        # ── Footer ──
        self.setStrokeColor(colors.HexColor('#e2e8f0'))
        self.setLineWidth(0.5)
        self.line(54, 44, w - 54, 44)

        self.setFont("Helvetica", 7)
        self.setFillColor(colors.HexColor('#94a3b8'))
        self.drawString(54, 30, "CONFIDENTIAL — FOR INTERNAL ENGINEERING USE ONLY")
        self.drawRightString(w - 54, 30, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()

# ═══════════════════════════════════════════════════════════════════════════════
#  STYLE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════
def get_styles():
    base = getSampleStyleSheet()

    styles = {}

    styles['cover_title'] = ParagraphStyle(
        'CoverTitle', parent=base['Heading1'],
        fontName='Helvetica-Bold', fontSize=32,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=8, alignment=TA_CENTER, leading=38
    )
    styles['cover_subtitle'] = ParagraphStyle(
        'CoverSubtitle', parent=base['Normal'],
        fontName='Helvetica', fontSize=14,
        textColor=colors.HexColor('#475569'),
        alignment=TA_CENTER, spaceAfter=4
    )
    styles['cover_meta'] = ParagraphStyle(
        'CoverMeta', parent=base['Normal'],
        fontName='Helvetica', fontSize=10,
        textColor=colors.HexColor('#94a3b8'),
        alignment=TA_CENTER, spaceAfter=2
    )
    styles['h1'] = ParagraphStyle(
        'H1', parent=base['Heading1'],
        fontName='Helvetica-Bold', fontSize=22,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=24, spaceAfter=10, keepWithNext=True
    )
    styles['h2'] = ParagraphStyle(
        'H2', parent=base['Heading2'],
        fontName='Helvetica-Bold', fontSize=15,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=16, spaceAfter=8, keepWithNext=True
    )
    styles['h3'] = ParagraphStyle(
        'H3', parent=base['Heading3'],
        fontName='Helvetica-Bold', fontSize=12,
        textColor=colors.HexColor('#0ea5e9'),
        spaceBefore=12, spaceAfter=6, keepWithNext=True
    )
    styles['body'] = ParagraphStyle(
        'Body', parent=base['Normal'],
        fontName='Helvetica', fontSize=10,
        textColor=colors.HexColor('#334155'),
        leading=15, spaceAfter=6, alignment=TA_JUSTIFY
    )
    styles['body_bold'] = ParagraphStyle(
        'BodyBold', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=10,
        textColor=colors.HexColor('#1e293b'),
        leading=15, spaceAfter=4
    )
    styles['bullet'] = ParagraphStyle(
        'Bullet', parent=base['Normal'],
        fontName='Helvetica', fontSize=9.5,
        textColor=colors.HexColor('#334155'),
        leading=14, leftIndent=18, spaceAfter=3, bulletIndent=6
    )
    styles['code'] = ParagraphStyle(
        'Code', parent=base['Normal'],
        fontName='Courier', fontSize=8,
        textColor=colors.HexColor('#e2e8f0'),
        leading=11, backColor=colors.HexColor('#0f172a'),
        borderPadding=6
    )
    styles['toc_entry'] = ParagraphStyle(
        'TOCEntry', parent=base['Normal'],
        fontName='Helvetica', fontSize=11,
        textColor=colors.HexColor('#1e293b'),
        leading=20, leftIndent=12, spaceAfter=2
    )
    styles['toc_section'] = ParagraphStyle(
        'TOCSection', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=12,
        textColor=colors.HexColor('#0f172a'),
        leading=22, spaceAfter=2
    )
    styles['table_header'] = ParagraphStyle(
        'TblHdr', parent=base['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5,
        textColor=colors.white, leading=12
    )
    styles['table_cell'] = ParagraphStyle(
        'TblCell', parent=base['Normal'],
        fontName='Helvetica', fontSize=8.5,
        textColor=colors.HexColor('#334155'), leading=12
    )
    styles['caption'] = ParagraphStyle(
        'Caption', parent=base['Normal'],
        fontName='Helvetica-Oblique', fontSize=8,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER, spaceAfter=12
    )
    styles['callout'] = ParagraphStyle(
        'Callout', parent=base['Normal'],
        fontName='Helvetica', fontSize=9.5,
        textColor=colors.HexColor('#1e3a8a'),
        leading=14, leftIndent=12, borderPadding=8
    )
    return styles

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════
def esc(text):
    """Escape HTML special characters for ReportLab Paragraphs."""
    if not text:
        return ""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def make_table(headers, rows, col_widths=None, header_color='#1e3a8a'):
    """Creates a professionally styled table."""
    s = get_styles()
    data = [[Paragraph(f"<b>{esc(h)}</b>", s['table_header']) for h in headers]]
    for row in rows:
        data.append([Paragraph(esc(str(c)), s['table_cell']) for c in row])

    if col_widths is None:
        col_widths = [500 / len(headers)] * len(headers)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return t

def info_box(text, styles, bg='#eff6ff', border='#bfdbfe'):
    """Creates a styled information callout box."""
    p = Paragraph(text, styles['callout'])
    t = Table([[p]], colWidths=[500])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(bg)),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(border)),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    return t

def section_divider():
    return HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'),
                      spaceBefore=8, spaceAfter=8)

def bullet(text, styles):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", styles['bullet'])

# ═══════════════════════════════════════════════════════════════════════════════
#  DIAGRAM BUILDERS (ASCII-art rendered as styled code blocks)
# ═══════════════════════════════════════════════════════════════════════════════
def ascii_diagram(lines, styles, title=None):
    """Renders an ASCII diagram inside a dark-themed box."""
    elements = []
    if title:
        elements.append(Paragraph(f"<b>{esc(title)}</b>", styles['body_bold']))
    joined = "<br/>".join([esc(l) for l in lines])
    p = Paragraph(joined, styles['code'])
    t = Table([[p]], colWidths=[500])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1e293b')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
    ]))
    elements.append(t)
    return elements

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN DOCUMENT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
def build_document(output_path):
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=54, leftMargin=54,
        topMargin=50, bottomMargin=60
    )

    s = get_styles()
    story = []

    # ═════════════════════════════════════════════════════════════════════════
    #  COVER PAGE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 120))

    # Accent line
    story.append(HRFlowable(width="60%", thickness=3, color=colors.HexColor('#0ea5e9'),
                            spaceBefore=0, spaceAfter=16))

    story.append(Paragraph("Automotive QA Intelligence", s['cover_title']))
    story.append(Paragraph("System Architecture &amp; Technical Documentation", s['cover_subtitle']))
    story.append(Spacer(1, 20))
    story.append(Paragraph("Comprehensive Technical Reference for the Offline RAG-Powered", s['cover_meta']))
    story.append(Paragraph("Automotive Quality Analytics &amp; Diagnostics Platform", s['cover_meta']))
    story.append(Spacer(1, 30))

    story.append(HRFlowable(width="40%", thickness=1, color=colors.HexColor('#cbd5e1'),
                            spaceBefore=0, spaceAfter=16))

    story.append(Paragraph(f"Document Version: <b>1.1</b>", s['cover_meta']))
    story.append(Paragraph(f"Date: <b>{datetime.datetime.now().strftime('%B %d, %Y')}</b>", s['cover_meta']))
    story.append(Paragraph("Classification: <b>CONFIDENTIAL — INTERNAL</b>", s['cover_meta']))
    story.append(Paragraph("Prepared by: <b>Senior Solutions Architect</b>", s['cover_meta']))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  TABLE OF CONTENTS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Table of Contents", s['h1']))
    story.append(section_divider())

    toc_items = [
        ("1", "System Overview"),
        ("2", "End-to-End Architecture"),
        ("3", "Data Flow &amp; Processing Pipeline"),
        ("4", "Component Interactions"),
        ("5", "Backend Workflow"),
        ("6", "Database Architecture"),
        ("7", "API &amp; Query Flow"),
        ("8", "AI / ML Pipeline"),
        ("9", "Retrieval Pipeline (SQL + BM25 + FAISS + RAG)"),
        ("10", "Frontend Architecture"),
        ("11", "Report Generation Engine"),
        ("12", "Deployment Architecture"),
        ("13", "Scalability Considerations"),
        ("14", "Performance Optimizations"),
        ("15", "Security Considerations"),
        ("16", "Error Handling &amp; Resilience"),
        ("17", "Future Improvements"),
        ("18", "Technology Stack Summary"),
    ]
    for num, title in toc_items:
        prefix = f"<b>{num}.</b>" if "." not in num else f"&nbsp;&nbsp;&nbsp;&nbsp;{num}"
        story.append(Paragraph(f"{prefix}&nbsp;&nbsp;{title}", s['toc_entry']))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  1. SYSTEM OVERVIEW
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. System Overview", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "<b>Automotive QA Intelligence</b> is a fully offline, enterprise-grade quality analytics and diagnostics platform "
        "designed for automotive field technical information report (FTIR) analysis. The system enables technicians and "
        "quality engineers to perform natural language queries against a structured database of historical vehicle failure "
        "records, leveraging a hybrid Retrieval-Augmented Generation (RAG) architecture that combines SQL-based structured "
        "search, FAISS vector similarity search, and local Large Language Model (LLM) inference.", s['body']))

    story.append(Paragraph("1.1 Core Objectives", s['h3']))
    objectives = [
        "<b>Offline-First Architecture:</b> Operates entirely without internet connectivity using local LLM inference (Phi-3 Mini 4K via llama.cpp) and local FAISS vector indexing.",
        "<b>Hybrid Retrieval:</b> Combines SQL keyword search, FAISS cosine similarity vector search, and NLP entity extraction for precise multi-strategy information retrieval.",
        "<b>Intelligent Query Routing:</b> An NLP pipeline classifies user intent (SEARCH, ANALYTICS, VISUALIZE, COMPARE, REPORT) and dispatches queries to the optimal processing backend.",
        "<b>Dynamic Analytics:</b> LLM-generated SQL queries enable ad-hoc analytics without pre-defined report templates.",
        "<b>Automated Report Generation:</b> Monthly PDF and DOCX quality reports are compiled dynamically from database aggregations.",
        "<b>Enterprise UI:</b> A Streamlit-based web interface with multi-session chat, real-time data visualization (Plotly), and citation-backed responses.",
    ]
    for o in objectives:
        story.append(bullet(o, s))

    story.append(Spacer(1, 6))
    story.append(info_box(
        "<b>Key Differentiator:</b> Unlike cloud-based AI platforms, this system operates entirely offline with no API keys, "
        "no external network calls, and no data egress — making it suitable for air-gapped automotive manufacturing environments "
        "where data confidentiality is paramount.",
        s
    ))

    story.append(Paragraph("1.2 System Specifications", s['h3']))
    story.append(make_table(
        ["Parameter", "Specification"],
        [
            ["LLM Engine", "Microsoft Phi-3 Mini 4K Instruct (Q4 GGUF, 3.8B params)"],
            ["Embedding Model", "all-MiniLM-L6-v2 (SentenceTransformers, 384-dim)"],
            ["Vector Index", "FAISS IndexFlatIP with IDMap (Cosine Similarity)"],
            ["Database", "SQLite 3 with WAL mode + Materialized Views"],
            ["Frontend", "Streamlit 1.x with custom enterprise CSS theme"],
            ["Visualization", "Plotly Express + Plotly Graph Objects"],
            ["LLM Runtime", "llama-cpp-python with CUDA GPU offloading"],
            ["Report Formats", "PDF (ReportLab) + DOCX (python-docx)"],
            ["Deployment", "Single-node local / on-premise (Windows/Linux)"],
        ],
        col_widths=[160, 340]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  2. END-TO-END ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. End-to-End Architecture", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The system follows a layered architecture pattern with clear separation of concerns across six layers: "
        "Presentation, Application Logic, Intelligence (AI/ML), Data Access, Storage, and Infrastructure.",
        s['body']))

    arch_diagram = [
        "┌──────────────────────────────────────────────────────────────────────┐",
        "│                    PRESENTATION LAYER (Streamlit)                    │",
        "│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐             │",
        "│  │ Login Screen │  │ Chat & RAG   │  │ Dashboard Page │             │",
        "│  │ (auth/       │  │ (AI Chat w/  │  │ (Charts +      │             │",
        "│  │  session.py) │  │  Citations)  │  │  Metrics)      │             │",
        "│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘             │",
        "│         │                 │                   │                      │",
        "├─────────┴─────────────────┴───────────────────┴──────────────────────┤",
        "│                    APPLICATION LOGIC LAYER                           │",
        "│  ┌──────────────────────────────────────────────────────────┐        │",
        "│  │              QueryRouter (core/router.py)                │        │",
        "│  │   Intent Classification → Dispatch → Response Assembly  │        │",
        "│  └──────┬──────────┬──────────┬──────────┬─────────────────┘        │",
        "│         │          │          │          │                           │",
        "├─────────┴──────────┴──────────┴──────────┴───────────────────────────┤",
        "│                    INTELLIGENCE LAYER (AI/ML)                        │",
        "│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐         │",
        "│  │ NLP Engine  │  │ LLM Client   │  │ FAISS Embedder     │         │",
        "│  │ (nlp/       │  │ (llm/        │  │ (rag/embedder.py)  │         │",
        "│  │ pipeline.py)│  │  client.py)  │  │ SentenceTransformer│         │",
        "│  └─────────────┘  └──────────────┘  └──────────────────────┘         │",
        "│                                                                      │",
        "├──────────────────────────────────────────────────────────────────────┤",
        "│                    DATA ACCESS LAYER                                │",
        "│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐        │",
        "│  │ Analytics       │  │ ETL Pipeline │  │ Report Engine   │        │",
        "│  │ Engine          │  │ (etl/        │  │ (reports/       │        │",
        "│  │ (analytics/     │  │  pipeline.py)│  │  engine.py)     │        │",
        "│  │  engine.py)     │  └──────────────┘  └──────────────────┘        │",
        "│  └────────────────┘                                                 │",
        "├──────────────────────────────────────────────────────────────────────┤",
        "│                    STORAGE LAYER                                     │",
        "│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐        │",
        "│  │ SQLite DB       │  │ FAISS Index  │  │ GGUF Model File │        │",
        "│  │ (automotive.db) │  │ (.bin + JSON)│  │ (Phi-3-mini)    │        │",
        "│  └────────────────┘  └──────────────┘  └──────────────────┘        │",
        "└──────────────────────────────────────────────────────────────────────┘",
    ]
    story.extend(ascii_diagram(arch_diagram, s, "Figure 2.1 — Layered System Architecture"))
    story.append(Paragraph("<i>Figure 2.1: Six-layer architecture showing clear separation between Presentation, Application Logic, Intelligence, Data Access, and Storage layers.</i>", s['caption']))

    story.append(Paragraph("2.1 Module Directory Structure", s['h3']))
    dir_diagram = [
        "automotive_qa/",
        "├── app/                 # Streamlit frontend (main.py)",
        "├── auth/                # User session management (session.py)",
        "├── core/                # Central infrastructure",
        "│   ├── router.py        #   Query routing & dispatch engine",
        "│   ├── singletons.py    #   Cached resource loaders (DB, LLM, FAISS)",
        "│   ├── cache.py         #   L1 (RAM) + L2 (SQLite) query cache",
        "│   └── paths.py         #   Absolute path resolver",
        "├── etl/                 # Data ingestion & transformation",
        "│   └── pipeline.py      #   Excel → SQLite ETL with deduplication",
        "├── nlp/                 # Natural language processing",
        "│   └── pipeline.py      #   Intent classifier + entity extractor",
        "├── rag/                 # Retrieval-Augmented Generation",
        "│   ├── embedder.py      #   FAISS index manager + vector search",
        "│   └── document_builder.py # Structured text builder for embeddings",
        "├── llm/                 # Local LLM inference",
        "│   └── client.py        #   Phi-3 GGUF streaming client (llama.cpp)",
        "├── analytics/           # SQL analytics engine",
        "│   ├── engine.py        #   12+ parameterized analytics queries",
        "│   ├── graph_selector.py#   Dynamic chart type inference",
        "│   └── views.py         #   Materialized view refresh logic",
        "├── viz/                 # Plotly visualization library",
        "│   └── charts.py        #   6 chart types with premium theming",
        "├── reports/             # Document generation",
        "│   └── engine.py        #   PDF + DOCX report builder",
        "├── data/                # Persistent data store",
        "│   ├── automotive.db    #   SQLite database",
        "│   ├── faiss_index.bin  #   FAISS vector index",
        "│   ├── vector_metadata.json # Index metadata",
        "│   └── inbox/           #   Manual ingestion drop folder",
        "├── models/              # GGUF model weights",
        "│   └── Phi-3-mini-*.gguf",
        "├── schema.sql           # Database DDL (tables + indexes)",
        "├── setup.py             # Automated project bootstrapper",
        "└── requirements.txt     # Python dependencies",
    ]
    story.extend(ascii_diagram(dir_diagram, s, "Figure 2.2 — Project Directory Structure"))
    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  3. DATA FLOW
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. Data Flow &amp; Processing Pipeline", s['h1']))
    story.append(section_divider())

    story.append(Paragraph("3.1 Ingestion Data Flow (ETL)", s['h2']))
    story.append(Paragraph(
        "Data enters the system through Excel (.xlsx) files containing FTIR records from field operations. "
        "The ETL pipeline performs column normalization, data cleaning, deduplication via MD5 hashing, computed field "
        "generation, heuristic/LLM-based summarization, and materialized view refresh — all within a single atomic transaction.",
        s['body']))

    etl_flow = [
        "  ┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐",
        "  │ Excel File   │────▶│ Column Normalize │────▶│ Data Cleaning    │",
        "  │ (.xlsx)      │     │ (rename headers) │     │ (parse dates,    │",
        "  └─────────────┘     └──────────────────┘     │  clean mileage)  │",
        "                                                └────────┬─────────┘",
        "                                                         │",
        "                                                         ▼",
        "  ┌─────────────┐     ┌──────────────────┐     ┌──────────────────┐",
        "  │ Materialized│◀────│ SQLite INSERT     │◀────│ MD5 Dedup Check  │",
        "  │ View Refresh │     │ (44 columns)     │     │ (row_hash +      │",
        "  └──────┬──────┘     └──────────────────┘     │  ftir_no unique) │",
        "         │                                      └──────────────────┘",
        "         ▼                                               ▲",
        "  ┌─────────────┐     ┌──────────────────┐              │",
        "  │ FAISS Index  │◀────│ Document Builder │◀─────────────┘",
        "  │ Update       │     │ (text concat)    │  Heuristic/LLM Summary",
        "  └─────────────┘     └──────────────────┘",
    ]
    story.extend(ascii_diagram(etl_flow, s, "Figure 3.1 — ETL Ingestion Pipeline"))

    story.append(Paragraph("3.2 ETL Processing Steps", s['h3']))
    story.append(make_table(
        ["Step", "Module", "Operation", "Details"],
        [
            ["1", "etl/pipeline.py", "Read Excel", "pd.read_excel() with column rename normalization"],
            ["2", "etl/pipeline.py", "Clean & Parse", "Date parsing (4 formats), mileage integer extraction"],
            ["3", "etl/pipeline.py", "Deduplication", "MD5(ftir_no|subject|complaint) + UNIQUE constraint"],
            ["4", "etl/pipeline.py", "Computed Fields", "using_km_int, report_year/month, is_resolved, has_sbpr"],
            ["5", "etl/pipeline.py", "Summarization", "LLM 2-sentence summary or heuristic fallback"],
            ["6", "analytics/views.py", "MV Refresh", "5 materialized views rebuilt in single transaction"],
            ["7", "rag/document_builder.py", "Text Build", "Concatenate 6 key fields into embedding document"],
            ["8", "rag/embedder.py", "Vectorize", "SentenceTransformer encode + FAISS IndexIDMap upsert"],
        ],
        col_widths=[30, 110, 80, 280]
    ))

    story.append(Spacer(1, 8))

    story.append(Paragraph("3.3 Query Processing Data Flow", s['h2']))
    query_flow = [
        "  User Query (Natural Language)",
        "       │",
        "       ▼",
        "  ┌──────────────────────────────────────────────────────────────────┐",
        "  │                    QueryRouter.dispatch_query()                  │",
        "  │                                                                  │",
        "  │  1. Check L1/L2 Cache ──▶ [HIT] Return cached result           │",
        "  │       │ [MISS]                                                   │",
        "  │       ▼                                                          │",
        "  │  2. NLP Parse Query                                             │",
        "  │     ├─ classify_intent() ──▶ SEARCH|ANALYTICS|VISUALIZE|..      │",
        "  │     ├─ extract_entities() ─▶ TROUBLE_CODE, COUNTRY, MODEL..     │",
        "  │     └─ extract_filters() ──▶ year, month, km_min, km_max..      │",
        "  │       │                                                          │",
        "  │       ▼                                                          │",
        "  │  3. Intent-Based Dispatch                                       │",
        "  │     ├─ SEARCH/AMBIGUOUS ──▶ _handle_search()                    │",
        "  │     ├─ ANALYTICS/VISUALIZE ─▶ _handle_analytics()               │",
        "  │     └─ REPORT ────────────▶ Report generation params            │",
        "  │                                                                  │",
        "  └──────────────────────────────────────────────────────────────────┘",
        "       │",
        "       ▼",
        "  Response: {intent, type, data, citations, chart_type, chart_title}",
    ]
    story.extend(ascii_diagram(query_flow, s, "Figure 3.2 — Query Processing Pipeline"))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  4. COMPONENT INTERACTIONS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. Component Interactions", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The following diagram illustrates the runtime interaction between all major system components "
        "during a typical user query lifecycle. Components communicate via function calls within a single Python process.",
        s['body']))

    interaction = [
        "  ┌────────┐   Query    ┌───────────┐  Parse   ┌───────────┐",
        "  │Streamlit│──────────▶│QueryRouter │────────▶│NLPProcessor│",
        "  │  UI     │           │(dispatcher)│         │(intent+NER)│",
        "  └────┬───┘           └─────┬─────┘         └───────────┘",
        "       │                     │",
        "       │          ┌──────────┼──────────────────────────┐",
        "       │          │          │                          │",
        "       │    [SEARCH]    [ANALYTICS]              [REPORT]",
        "       │          │          │                          │",
        "       │          ▼          ▼                          ▼",
        "       │   ┌────────────┐ ┌──────────────┐    ┌─────────────┐",
        "       │   │SQL Prefilter│ │AnalyticsEngine│    │ReportEngine │",
        "       │   │(WHERE clause│ │(12+ queries + │    │(PDF + DOCX  │",
        "       │   │ from NER)  │ │ LLM SQL gen) │    │ generation) │",
        "       │   └─────┬──────┘ └──────┬───────┘    └─────────────┘",
        "       │         │               │",
        "       │         ▼               ▼",
        "       │   ┌────────────┐ ┌──────────────┐",
        "       │   │FAISS Vector│ │GraphSelector │",
        "       │   │Search      │ │(chart type   │",
        "       │   │(cosine sim)│ │ inference)   │",
        "       │   └─────┬──────┘ └──────────────┘",
        "       │         │",
        "       │         ▼",
        "       │   ┌────────────┐      ┌──────────────┐",
        "       │   │LLM Client  │─────▶│Plotly Charts  │",
        "       │   │(Phi-3 GGUF │      │(6 chart types)│",
        "       │   │ streaming) │      └──────────────┘",
        "       │   └─────┬──────┘",
        "       │         │",
        "       ◀─────────┘  Streamed Response + Citations + Charts",
    ]
    story.extend(ascii_diagram(interaction, s, "Figure 4.1 — Component Interaction Diagram"))

    story.append(Paragraph("4.1 Singleton Resource Management", s['h3']))
    story.append(Paragraph(
        "All expensive resources are loaded once and cached using Streamlit's <font name='Courier'>@st.cache_resource</font> "
        "decorator in <b>core/singletons.py</b>. This ensures the FAISS index (~9.5 MB), SentenceTransformer model, and Phi-3 "
        "GGUF model (~2.4 GB) are loaded into GPU VRAM/RAM only once across all Streamlit reruns.",
        s['body']))

    story.append(make_table(
        ["Singleton", "Module", "Cached Resource", "Lifecycle"],
        [
            ["get_db_connection()", "core/singletons.py", "SQLite DB path (WAL mode verified)", "App lifetime"],
            ["get_embedder()", "core/singletons.py", "SentenceTransformer + FAISS index + metadata", "App lifetime"],
            ["get_llm()", "core/singletons.py", "Phi-3 GGUF loaded via llama-cpp (GPU offload)", "App lifetime"],
            ["get_ingestion_tracker()", "core/singletons.py", "Thread-safe ingestion status tracker", "App lifetime"],
        ],
        col_widths=[120, 100, 180, 100]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  5. BACKEND WORKFLOW
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("5. Backend Workflow", s['h1']))
    story.append(section_divider())

    story.append(Paragraph("5.1 Application Startup Sequence", s['h2']))
    startup_flow = [
        "  ┌────────────────────┐",
        "  │ python setup.py    │",
        "  └────────┬───────────┘",
        "           │",
        "           ▼",
        "  ┌────────────────────┐    ┌────────────────────┐",
        "  │ 1. create_folders()│───▶│ 2. init_database() │",
        "  │    (12 directories)│    │    (schema.sql DDL) │",
        "  └────────────────────┘    └──────────┬─────────┘",
        "                                       │",
        "           ┌───────────────────────────┘",
        "           ▼",
        "  ┌────────────────────┐    ┌────────────────────┐",
        "  │ 3. download_spacy()│───▶│ 4. download_qwen() │",
        "  │    (en_core_web_sm)│    │    (4.7 GB GGUF)   │",
        "  └────────────────────┘    └──────────┬─────────┘",
        "                                       │",
        "           ┌───────────────────────────┘",
        "           ▼",
        "  ┌────────────────────┐",
        "  │ 5. run_initial_etl()│",
        "  │    Excel → DB → FAISS│",
        "  └────────────────────┘",
    ]
    story.extend(ascii_diagram(startup_flow, s, "Figure 5.1 — Project Setup Sequence"))

    story.append(Paragraph("5.2 Runtime Query Processing Workflow", s['h2']))
    story.append(Paragraph(
        "When a user submits a query through the Streamlit chat interface, the following end-to-end workflow executes:",
        s['body']))

    workflow_steps = [
        ["Step 1", "User types query in st.chat_input()", "app/main.py"],
        ["Step 2", "QueryRouter.dispatch_query() invoked", "core/router.py"],
        ["Step 3", "QueryCache L1/L2 lookup (MD5 hash key)", "core/cache.py"],
        ["Step 4", "NLPProcessor.parse_query() — intent + entities + filters", "nlp/pipeline.py"],
        ["Step 5a", "SEARCH: SQL pre-filter → FAISS search_subset() → LLM generation", "core/router.py"],
        ["Step 5b", "ANALYTICS: LLM SQL gen (4 retries) → static fallback → GraphSelector", "analytics/engine.py"],
        ["Step 5c", "REPORT: Pass year/month params to ReportEngine", "reports/engine.py"],
        ["Step 6", "LLM streaming response via st.write_stream()", "llm/client.py"],
        ["Step 7", "Plotly chart rendered via render_plotly_chart()", "viz/charts.py"],
        ["Step 8", "Response cached to L1 RAM + L2 SQLite", "core/cache.py"],
        ["Step 9", "Chat message persisted to chat_history table", "auth/session.py"],
    ]
    story.append(make_table(
        ["Step", "Operation", "Module"],
        workflow_steps,
        col_widths=[45, 300, 155]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  6. DATABASE ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("6. Database Architecture", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The system uses SQLite 3 with Write-Ahead Logging (WAL) mode for concurrent read/write access. The schema "
        "consists of 10 tables: 1 core data table, 4 application tables, and 5 materialized view tables.",
        s['body']))

    story.append(Paragraph("6.1 Core Schema — records Table", s['h2']))
    story.append(Paragraph(
        "The <b>records</b> table stores all FTIR data with 44 columns including 6 computed fields. It serves as the single "
        "source of truth for all analytics, search, and report generation.",
        s['body']))

    story.append(make_table(
        ["Column Group", "Columns", "Purpose"],
        [
            ["Identity", "id, sbpr_no, ftir_no, row_hash", "Primary key, deduplication"],
            ["Temporal", "ftir_report_date, reply_date, date_registered, date_of_incident", "Date tracking"],
            ["Vehicle", "product_model_code, sales_model_code, vin, engine_no, transmission_no", "Vehicle identification"],
            ["Classification", "segmentation, status, quality, fc_ok", "Categorical grouping"],
            ["Geography", "outbreak_country, reported_company, issued_company, manufacturer_factory", "Location & dealer tracking"],
            ["Technical", "subject, customer_complaint, trouble_code_complaint, trouble_code_defect", "Failure description"],
            ["Diagnostics", "checked_contents, checked_results, repair_status, repair_contents", "Inspection & repair data"],
            ["Resolution", "problem_solved, action_judgement, causal_parts_no, causal_parts_name", "Root cause & fix"],
            ["Computed", "using_km_int, report_year, report_month, is_resolved, has_sbpr, summary", "Derived analytics fields"],
        ],
        col_widths=[80, 250, 170]
    ))

    story.append(Paragraph("6.2 Application Tables", s['h2']))
    story.append(make_table(
        ["Table", "Purpose", "Key Columns"],
        [
            ["users", "Passwordless user authentication", "id, username, created_at"],
            ["chat_sessions", "Multi-thread conversation management", "id, user_id, title, created_at"],
            ["chat_history", "Persistent message storage", "id, user_id, session_id, role, content"],
            ["query_cache", "L2 query result cache with TTL", "query_hash, user_id, result_json, expires_at"],
            ["embedding_cache", "Persistent embedding vector cache", "text_hash, embedding_blob (BLOB)"],
        ],
        col_widths=[110, 200, 190]
    ))

    story.append(Paragraph("6.3 Materialized Views", s['h2']))
    story.append(Paragraph(
        "Five materialized view tables are pre-computed from the records table and refreshed atomically after every ETL ingestion. "
        "These provide O(1) access to common dashboard aggregations without runtime computation.",
        s['body']))

    story.append(make_table(
        ["View Table", "Aggregation", "Refresh Trigger"],
        [
            ["mv_country_month", "Record count by country, year, and month", "Post-ETL ingestion"],
            ["mv_trouble_codes", "Frequency count by trouble code", "Post-ETL ingestion"],
            ["mv_dealer_summary", "Record count by reporting dealer/company", "Post-ETL ingestion"],
            ["mv_quality_dist", "Distribution count by quality rating", "Post-ETL ingestion"],
        ],
        col_widths=[120, 230, 150]
    ))

    story.append(Paragraph("6.4 Index Strategy", s['h2']))
    story.append(Paragraph(
        "Nine B-tree indexes cover 95%+ of filter patterns used in analytics and search queries:",
        s['body']))
    story.append(make_table(
        ["Index Name", "Column", "Primary Use Case"],
        [
            ["idx_outbreak_country", "outbreak_country", "Country-based filtering & grouping"],
            ["idx_product_model_code", "product_model_code", "Model-specific analytics"],
            ["idx_segmentation", "segmentation", "Engine/Transmission category filters"],
            ["idx_trouble_code_complaint", "trouble_code_complaint", "DTC frequency analysis"],
            ["idx_status", "status", "Status-based filtering"],
            ["idx_quality", "quality", "Quality distribution queries"],
            ["idx_repair_status", "repair_status", "Repair status analytics"],
            ["idx_using_km_int", "using_km_int", "Mileage range queries"],
            ["idx_report_year", "report_year", "Temporal analytics"],
        ],
        col_widths=[160, 160, 180]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  7. API & QUERY FLOW
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("7. API &amp; Query Flow", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The system does not expose a REST API — all interactions occur through the Streamlit UI. However, "
        "the QueryRouter acts as an internal API gateway that routes classified intents to the appropriate processing backend.",
        s['body']))

    story.append(Paragraph("7.1 Internal Query API Contract", s['h2']))
    story.append(Paragraph("The QueryRouter returns a standardized response dictionary:", s['body']))

    story.append(make_table(
        ["Field", "Type", "Description"],
        [
            ["intent", "str", "Classified intent: SEARCH, ANALYTICS, VISUALIZE, COMPARE, REPORT, AMBIGUOUS"],
            ["type", "str", "Response type: text_stream, table_stream, table_only, report"],
            ["data", "mixed", "Messages (list of dicts) for LLM, or DataFrame, or report params"],
            ["citations", "list[dict]", "Referenced FTIR records with ftir_no, subject, company, country"],
            ["chart_type", "str", "Plotly chart type: horizontal_bar, line, donut, histogram, radar, grouped_bar"],
            ["chart_title", "str", "Generated chart title string"],
            ["sql_query", "str", "The actual SQL query executed (for transparency)"],
        ],
        col_widths=[80, 80, 340]
    ))

    story.append(Paragraph("7.2 Intent Classification Rules", s['h2']))
    story.append(make_table(
        ["Intent", "Score", "Trigger Keywords", "Handler"],
        [
            ["VISUALIZE+EXPLAIN", "4", "(chart|graph|plot) AND (why|explain|cause)", "_handle_analytics()"],
            ["VISUALIZE", "3", "chart, graph, plot, visualize", "_handle_analytics()"],
            ["COMPARE", "3", "compare, vs, versus, difference between", "_handle_analytics()"],
            ["REPORT", "3-6", "monthly report, generate report, export + year", "Report params"],
            ["ANALYTICS", "2", "top, count, how many, total, frequency, average", "_handle_analytics()"],
            ["SEARCH", "3", "similar, find, cases like, search, lookup", "_handle_search()"],
            ["AMBIGUOUS", "0", "No keyword match (fallback to search)", "_handle_search()"],
        ],
        col_widths=[100, 35, 220, 145]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  8. AI/ML PIPELINE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("8. AI / ML Pipeline", s['h1']))
    story.append(section_divider())

    story.append(Paragraph("8.1 NLP Processing Pipeline", s['h2']))
    story.append(Paragraph(
        "The NLP pipeline in <b>nlp/pipeline.py</b> performs three sequential tasks: intent classification, "
        "named entity recognition (NER), and filter extraction. It uses a dual-mode approach: spaCy with custom EntityRuler "
        "patterns as primary, with regex-based fallback.",
        s['body']))

    story.append(make_table(
        ["Entity Type", "Recognition Method", "Pattern Example", "Database Validation"],
        [
            ["TROUBLE_CODE", "Regex: [PBCU]\\d{4}", "P0500, C0035", "No (format-based)"],
            ["PRODUCT_MODEL", "Regex: Y[A-Z0-9]{5,9}", "YNC412, YFBP51", "Yes (cross-checked with DB models)"],
            ["COUNTRY", "Lookup list from DB", "India, Brunei, Nepal", "Yes (loaded at init from records)"],
            ["SALES_MODEL", "Regex: [A-Z]{3}\\d{3,4}", "ERT701, ATM412", "No (format-based)"],
            ["VIN", "Regex: MA3[A-Z0-9]{14}", "MA3FJEB1S00123456", "No (format-based)"],
            ["FTIR_NO", "Regex: FTIR/\\d{4}/\\d{4}", "FTIR/2024/1018", "No (format-based)"],
        ],
        col_widths=[90, 130, 130, 150]
    ))

    story.append(Paragraph("8.2 Local LLM Inference Engine", s['h2']))
    story.append(Paragraph(
        "The LLM subsystem uses <b>Microsoft Phi-3 Mini 4K Instruct</b> (3.8B parameters, Q4 quantized GGUF format) "
        "running locally via <b>llama-cpp-python</b> with full CUDA GPU layer offloading. The model serves three distinct roles:",
        s['body']))

    story.append(make_table(
        ["Role", "Function", "Temperature", "Max Tokens", "Stop Tokens"],
        [
            ["Chat Response", "generate_chat_stream()", "0.1", "300", "<|end|>, <|user|>, <|system|>"],
            ["Record Summary", "generate_summary()", "0.1", "150", "\\n, Summary:, Issue:"],
            ["SQL Generation", "query_via_llm()", "0.1", "500", "<|end|>, <|user|>"],
        ],
        col_widths=[90, 130, 70, 70, 140]
    ))

    story.append(Paragraph(
        "The Phi-3 native chat template format is used for all prompts: "
        "<font name='Courier' size='8'>&lt;|system|&gt;...&lt;|end|&gt; &lt;|user|&gt;...&lt;|end|&gt; &lt;|assistant|&gt;</font>",
        s['body']))

    story.append(Paragraph("8.3 LLM-Generated SQL with Self-Healing", s['h2']))
    story.append(Paragraph(
        "The AnalyticsEngine in <b>analytics/engine.py</b> implements a sophisticated LLM-to-SQL pipeline with automatic "
        "error recovery. When the LLM generates an invalid SQL query, the error message is appended to the prompt context, "
        "and the LLM is asked to self-correct — up to 4 retry attempts.",
        s['body']))

    sql_heal = [
        "  Attempt 1: LLM generates SQL → Execute",
        "       │",
        "       ├── [SUCCESS] → Return DataFrame",
        "       │",
        "       ├── [SQL ERROR] → Append error to prompt context",
        "       │         │",
        "       │         ▼",
        "       │   Attempt 2: LLM re-generates → Execute",
        "       │         │",
        "       │         ├── [SUCCESS] → Return DataFrame",
        "       │         │",
        "       │         ├── [SQL ERROR] → Append error...",
        "       │         │         │",
        "       │         │         ▼",
        "       │         │   Attempt 3 → Attempt 4",
        "       │         │",
        "       │         └── [MAX RETRIES] → Raise exception",
        "       │                               │",
        "       │                               ▼",
        "       │                     Static fallback router",
        "       │                     (12 parameterized queries)",
    ]
    story.extend(ascii_diagram(sql_heal, s, "Figure 8.1 — LLM SQL Self-Healing Pipeline"))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  9. RETRIEVAL PIPELINE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("9. Retrieval Pipeline (SQL + FAISS + RAG)", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The SEARCH intent triggers a three-stage hybrid retrieval pipeline that combines structured SQL filtering, "
        "FAISS vector similarity search, and LLM-powered response generation with source citations.",
        s['body']))

    story.append(Paragraph("9.1 Three-Stage Hybrid Retrieval", s['h2']))

    retrieval = [
        "  STAGE 1: SQL Pre-Filter (Metadata Whitelisting)",
        "  ────────────────────────────────────────────────",
        "  NLP entities → Dynamic WHERE clause → Record ID whitelist",
        "  Example: COUNTRY='India' AND TROUBLE_CODE='P0500'",
        "           → Returns [id: 12, 45, 67, 89, 112, ...]",
        "",
        "  STAGE 2: FAISS Vector Search (Cosine Similarity)",
        "  ────────────────────────────────────────────────",
        "  Query → SentenceTransformer → 384-dim embedding",
        "  FAISS range_search() with IDSelector (whitelist)",
        "  Dynamic threshold: 0.30 (if SQL match) / 0.45 (no SQL match)",
        "  Returns: [(record_id, score), ...]",
        "",
        "  STAGE 3: Result Fusion + LLM Generation",
        "  ────────────────────────────────────────────────",
        "  Merge SQL keyword matches + FAISS vector matches",
        "  SQL-only matches get baseline score = 0.35",
        "  Sort by score DESC → Top 5 → Fetch summaries",
        "  System prompt includes total_count for accurate counts",
        "  LLM generates streamed narrative response",
    ]
    story.extend(ascii_diagram(retrieval, s, "Figure 9.1 — Three-Stage Hybrid Retrieval Pipeline"))

    story.append(Paragraph("9.2 Vector Index Architecture", s['h2']))
    story.append(make_table(
        ["Parameter", "Value", "Rationale"],
        [
            ["Index Type", "IndexFlatIP + IndexIDMap", "Exact inner product search with custom record IDs"],
            ["Embedding Model", "all-MiniLM-L6-v2", "384-dim, fast inference, strong semantic similarity"],
            ["Similarity Metric", "Cosine (via normalized IP)", "L2 normalized vectors → Inner Product = Cosine"],
            ["Document Fields", "6 concatenated text fields", "subject, complaint, checked, results, repair, part"],
            ["Metadata Stored", "id, country, model, trouble_code, segment", "Enables pre-filter ID selection"],
            ["Search Method", "range_search() with IDSelectorArray", "Threshold-based filtering on whitelisted subset"],
            ["Persistence", "faiss_index.bin + vector_metadata.json", "Binary index + JSON metadata on disk"],
        ],
        col_widths=[110, 170, 220]
    ))

    story.append(Paragraph("9.3 Embedding Cache Strategy", s['h2']))
    story.append(Paragraph(
        "To avoid redundant SentenceTransformer inference, all computed embeddings are cached in the <b>embedding_cache</b> "
        "SQLite table as BLOB-serialized NumPy arrays. The cache key is an MD5 hash of the input text, providing O(1) lookup. "
        "This is critical during ETL batch ingestion where thousands of documents are processed.",
        s['body']))

    story.append(Paragraph("9.4 SQL Keyword Search (BM25-like)", s['h2']))
    story.append(Paragraph(
        "Alongside vector search, the system performs keyword-based SQL LIKE queries across four text columns: "
        "<b>subject</b>, <b>customer_complaint</b>, <b>causal_parts_name</b>, and <b>summary</b>. Keywords are extracted "
        "by the NLP pipeline (nouns, proper nouns, adjectives) with stop-word filtering. Results are intersected with "
        "the metadata-whitelisted IDs and merged with FAISS scores.",
        s['body']))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  10. FRONTEND ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("10. Frontend Architecture", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The frontend is built with Streamlit and features a multi-page layout with three main views, custom enterprise CSS "
        "theming, and interactive chat with streaming LLM responses.",
        s['body']))

    story.append(Paragraph("10.1 Page Structure", s['h2']))
    story.append(make_table(
        ["Page", "Route", "Features"],
        [
            ["AI Chat & RAG", "💬 AI Chat & RAG", "Chat interface, streamed LLM, citation cards, SQL viewer, Plotly charts, PDF export"],
            ["Quality Dashboard", "📊 Quality Dashboard", "4 KPI metric cards, trouble code chart, trend line, quality donut, model comparison"],
            ["Monthly Reports", "📄 Monthly Reports", "Year/month selector, PDF + DOCX generation, download buttons"],
        ],
        col_widths=[110, 130, 260]
    ))

    story.append(Paragraph("10.2 UI Component Hierarchy", s['h2']))
    ui_tree = [
        "  main()",
        "  ├── inject_custom_styles()       # Enterprise CSS injection",
        "  ├── show_login_screen()           # Passwordless auth form",
        "  ├── show_sidebar()                # Navigation + Chat sessions",
        "  │   ├── Navigation buttons        #   3 page links",
        "  │   ├── New Chat / Session list   #   CRUD on chat_sessions",
        "  │   ├── Manual data ingest        #   File upload + inbox scan",
        "  │   └── Logout button",
        "  ├── render_chat_page()            # Main AI chat interface",
        "  │   ├── Welcome hero + starters   #   Empty state with prompts",
        "  │   ├── Chat history renderer     #   Intent badges, tables, charts",
        "  │   ├── render_plotly_chart()      #   6 chart type dispatcher",
        "  │   ├── render_citations()         #   Source FTIR citation cards",
        "  │   └── Chat input handler        #   Query → Router → Stream",
        "  ├── render_dashboard_page()       # Analytics dashboard",
        "  │   ├── 4x Metric cards (SQL)     #   Total, Models, Dealers, Resolved",
        "  │   └── 4x Plotly charts          #   Bar, Line, Donut, Table",
        "  └── render_reports_page()         # PDF/DOCX report generator",
    ]
    story.extend(ascii_diagram(ui_tree, s, "Figure 10.1 — Frontend Component Hierarchy"))

    story.append(Paragraph("10.3 Chat Visualization Types", s['h2']))
    story.append(make_table(
        ["Chart Type", "Function", "Use Case", "Auto-Selected When"],
        [
            ["horizontal_bar", "plot_horizontal_bar()", "Rankings (dealers, codes, parts)", "failures/count column detected"],
            ["line", "plot_line_trend()", "Temporal trends", "period/report_year column detected"],
            ["donut", "plot_donut_chart()", "Category distribution", "quality column + 2 columns only"],
            ["histogram", "plot_histogram()", "Mileage distribution", "mileage column detected"],
            ["radar", "plot_radar_comparison()", "Multi-metric model comparison", "COMPARE intent + resolution_rate"],
            ["grouped_bar", "plot_grouped_bar()", "Multi-variable comparison", "3+ numeric columns"],
        ],
        col_widths=[80, 110, 130, 180]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  11. REPORT GENERATION ENGINE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("11. Report Generation Engine", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The ReportEngine in <b>reports/engine.py</b> generates two types of reports: monthly quality reports (PDF + DOCX) "
        "and chat session transcripts (PDF only). Both use enterprise-grade formatting with custom headers, footers, "
        "page numbering, and professional typography.",
        s['body']))

    story.append(make_table(
        ["Feature", "Monthly Report", "Chat Transcript"],
        [
            ["Format", "PDF (ReportLab) + DOCX (python-docx)", "PDF (ReportLab) only"],
            ["Header/Footer", "Navy accent bar, date, page X of Y, confidential", "Same enterprise canvas"],
            ["Content", "Executive summary, country/model tables, DTC, cases", "User/assistant bubbles, SQL, tables, charts, citations"],
            ["Data Source", "SQLite aggregation queries (year, month)", "In-memory chat_history list"],
            ["Chart Embedding", "Not included", "Plotly → PNG → ReportLab Image"],
            ["Caching", "Stored in reports_cache/ directory", "Generated on-demand per session"],
        ],
        col_widths=[100, 200, 200]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  12. DEPLOYMENT ARCHITECTURE
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("12. Deployment Architecture", s['h1']))
    story.append(section_divider())

    story.append(Paragraph(
        "The system is designed for single-node on-premise deployment on Windows or Linux workstations with NVIDIA GPU "
        "acceleration. No cloud services, API keys, or network connectivity are required.",
        s['body']))

    deploy = [
        "  ┌────────────────────────────────────────────────────────────┐",
        "  │              On-Premise Workstation / Server               │",
        "  │                                                            │",
        "  │  ┌──────────────────────────────────────────────────────┐  │",
        "  │  │              Streamlit Application Server             │  │",
        "  │  │              (streamlit run app/main.py)              │  │",
        "  │  │                   Port: 8501                          │  │",
        "  │  └────────────────────────┬─────────────────────────────┘  │",
        "  │                           │                                │",
        "  │  ┌────────────┐  ┌────────┴───────┐  ┌──────────────────┐ │",
        "  │  │ SQLite DB   │  │ FAISS Index    │  │ Phi-3 GGUF Model│ │",
        "  │  │ (WAL mode)  │  │ (in-memory)    │  │ (CUDA GPU VRAM) │ │",
        "  │  │ ~6.7 MB     │  │ ~9.5 MB        │  │ ~2.4 GB         │ │",
        "  │  └────────────┘  └────────────────┘  └──────────────────┘ │",
        "  │                                                            │",
        "  │  ┌────────────────────────────────────────────────────────┐│",
        "  │  │  NVIDIA CUDA GPU (n_gpu_layers=-1, full offload)      ││",
        "  │  └────────────────────────────────────────────────────────┘│",
        "  └────────────────────────────────────────────────────────────┘",
    ]
    story.extend(ascii_diagram(deploy, s, "Figure 12.1 — Deployment Topology"))

    story.append(Paragraph("12.1 System Requirements", s['h2']))
    story.append(make_table(
        ["Resource", "Minimum", "Recommended"],
        [
            ["RAM", "8 GB", "16+ GB"],
            ["GPU VRAM", "4 GB (NVIDIA CUDA)", "8+ GB"],
            ["Disk Space", "10 GB", "20+ GB (models + data growth)"],
            ["Python", "3.9+", "3.10+"],
            ["CUDA Toolkit", "11.x+", "12.x"],
            ["OS", "Windows 10+ / Linux", "Windows 11 / Ubuntu 22.04"],
        ],
        col_widths=[120, 190, 190]
    ))

    story.append(Paragraph("12.2 Startup Commands", s['h3']))
    startup_cmds = [
        "  # Initial setup (one-time):",
        "  cd automotive_qa",
        "  pip install -r requirements.txt",
        "  python setup.py",
        "",
        "  # Launch application:",
        "  streamlit run app/main.py",
    ]
    story.extend(ascii_diagram(startup_cmds, s, ""))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  13. SCALABILITY CONSIDERATIONS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("13. Scalability Considerations", s['h1']))
    story.append(section_divider())

    story.append(make_table(
        ["Dimension", "Current Design", "Scaling Strategy", "Threshold"],
        [
            ["Record Count", "SQLite single-file DB", "Migrate to PostgreSQL with partitioning", "> 500K records"],
            ["Vector Index", "FAISS IndexFlatIP (brute-force)", "Switch to FAISS IVF-PQ or HNSW", "> 1M vectors"],
            ["LLM Inference", "Single Phi-3 instance on 1 GPU", "Model parallelism, vLLM server, or batching", "> 10 concurrent users"],
            ["Concurrent Users", "Streamlit single-threaded", "Deploy behind NGINX + multiple workers", "> 5 concurrent"],
            ["ETL Volume", "Sequential row-by-row insertion", "Batch INSERT with executemany()", "> 10K rows/file"],
            ["Cache Size", "200-entry RAM LRU + SQLite L2", "Redis with configurable TTL", "> 1000 queries/day"],
            ["Embedding Model", "CPU + GPU inference", "Pre-computed embeddings, batch encoding", "> 50K documents"],
        ],
        col_widths=[80, 130, 170, 120]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  14. PERFORMANCE OPTIMIZATIONS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("14. Performance Optimizations", s['h1']))
    story.append(section_divider())

    story.append(make_table(
        ["Optimization", "Implementation", "Impact"],
        [
            ["Two-Tier Query Cache", "L1 RAM (dict, 200 entries) + L2 SQLite (TTL 2 hours)", "Eliminates duplicate LLM inference calls"],
            ["Embedding Cache", "SQLite BLOB storage of NumPy arrays (MD5 key)", "Avoids re-encoding repeated texts during ETL"],
            ["Singleton Resources", "@st.cache_resource for DB, LLM, FAISS", "One-time model loading across Streamlit reruns"],
            ["WAL Journal Mode", "PRAGMA journal_mode=WAL", "Concurrent reads during writes; reduces lock contention"],
            ["FAISS IDSelector", "Pre-filter search space with IDSelectorArray", "Reduces vector comparisons to whitelisted subset"],
            ["Dynamic Threshold", "0.30 (SQL match exists) vs 0.45 (no match)", "Reduces false positives for unrelated queries"],
            ["Adaptive Table Truncation", "df.head(20) + describe() for large DataFrames", "Prevents LLM context window overflow"],
            ["9 B-Tree Indexes", "Covering 95% of filter column patterns", "Sub-millisecond SQL WHERE clause execution"],
            ["GPU Full Offload", "n_gpu_layers=-1 + use_mlock=True", "Maximizes LLM inference throughput on NVIDIA GPU"],
            ["Materialized Views", "5 pre-aggregated tables refreshed post-ETL", "O(1) dashboard metric queries"],
        ],
        col_widths=[120, 210, 170]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  15. SECURITY CONSIDERATIONS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("15. Security Considerations", s['h1']))
    story.append(section_divider())

    story.append(make_table(
        ["Security Domain", "Implementation", "Assessment"],
        [
            ["Authentication", "Passwordless username-based login (verify_or_create_user)", "Suitable for trusted internal networks"],
            ["Data Isolation", "User-scoped chat sessions (user_id FK constraint)", "Users can only access their own history"],
            ["Data at Rest", "SQLite database with OS-level file permissions", "No encryption; relies on OS access controls"],
            ["Data in Transit", "Localhost only (no network exposure by default)", "No TLS needed for localhost deployment"],
            ["AI Data Privacy", "Fully offline LLM — no data sent to external APIs", "No data egress risk"],
            ["SQL Injection", "Parameterized queries (?) throughout codebase", "Protected against SQL injection attacks"],
            ["File Upload", "Restricted to .xlsx only; saved to data/inbox/", "File type validation via Streamlit uploader"],
            ["LLM Output Safety", "Temperature 0.1 + strict stop tokens", "Minimizes hallucination; factual output"],
            ["Session Management", "Streamlit session_state (in-memory per browser tab)", "Session cleared on logout or tab close"],
        ],
        col_widths=[100, 230, 170]
    ))

    story.append(info_box(
        "<b>⚠ Security Note:</b> The current authentication is passwordless and suitable only for trusted internal networks. "
        "For production deployment exposed to wider networks, implement password hashing (bcrypt), JWT tokens, and HTTPS via "
        "a reverse proxy (NGINX + TLS).",
        s, bg='#fef3c7', border='#f59e0b'
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  16. ERROR HANDLING
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("16. Error Handling &amp; Resilience", s['h1']))
    story.append(section_divider())

    story.append(make_table(
        ["Error Scenario", "Handling Strategy", "Module"],
        [
            ["LLM SQL generation failure", "4-retry self-healing with error context injection", "analytics/engine.py"],
            ["LLM model file not found", "FileNotFoundError with descriptive message", "llm/client.py"],
            ["spaCy model not installed", "Fallback to regex-only NER extraction", "nlp/pipeline.py"],
            ["FAISS index missing", "Automatic rebuild from database records", "rag/embedder.py"],
            ["Duplicate FTIR records", "MD5 hash + UNIQUE constraint → skip silently", "etl/pipeline.py"],
            ["Excel column name mismatch", "Column rename normalization map", "etl/pipeline.py"],
            ["Date parsing failure", "Try 4 date formats; fallback to raw string", "etl/pipeline.py"],
            ["LLM summary generation failure", "Heuristic 2-sentence summary fallback", "etl/pipeline.py"],
            ["Unrelated user query", "FAISS threshold filter → general assistant fallback", "core/router.py"],
            ["Empty analytics result", "text_stream response: 'No data available'", "core/router.py"],
            ["Chat session deletion", "CASCADE delete of chat_history records", "auth/session.py"],
            ["Query cache expiry", "Auto-delete from SQLite on next access", "core/cache.py"],
            ["Materialized view refresh failure", "ROLLBACK transaction; log error", "analytics/views.py"],
            ["CUDA DLL not found (Windows)", "Dynamic DLL directory registration at startup", "core/singletons.py"],
        ],
        col_widths=[140, 230, 130]
    ))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  17. FUTURE IMPROVEMENTS
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("17. Future Improvements", s['h1']))
    story.append(section_divider())

    story.append(Paragraph("17.1 Short-Term Enhancements", s['h2']))
    short_term = [
        "<b>Multi-Turn Conversation Context:</b> Pass previous chat messages to the LLM for context-aware follow-up answers.",
        "<b>Advanced Authentication:</b> Add password hashing (bcrypt), role-based access control (admin/viewer), and JWT session tokens.",
        "<b>Chart Embedding in Reports:</b> Render Plotly charts as PNG images and embed them in monthly PDF reports.",
        "<b>Real-Time ETL Watchdog:</b> Use filesystem event monitoring (watchdog library) for automatic inbox ingestion.",
        "<b>Batch ETL Optimization:</b> Replace row-by-row INSERT with executemany() for 10x+ ingestion performance.",
    ]
    for item in short_term:
        story.append(bullet(item, s))

    story.append(Paragraph("17.2 Medium-Term Enhancements", s['h2']))
    medium_term = [
        "<b>PostgreSQL Migration:</b> Replace SQLite with PostgreSQL for true concurrent multi-user access and table partitioning.",
        "<b>FAISS IVF-PQ Index:</b> Upgrade to IVF-PQ (Inverted File with Product Quantization) for sub-linear search at 1M+ scale.",
        "<b>Larger LLM Models:</b> Support Qwen 2.5 7B (already downloaded) or Llama 3.1 for improved SQL generation and richer answers.",
        "<b>REST API Layer:</b> Expose FastAPI endpoints for headless integration with other enterprise systems.",
        "<b>Automated Testing:</b> Add pytest suite covering NLP classification, ETL pipeline, and analytics engine correctness.",
    ]
    for item in medium_term:
        story.append(bullet(item, s))

    story.append(Paragraph("17.3 Long-Term Vision", s['h2']))
    long_term = [
        "<b>Kubernetes Deployment:</b> Containerize (Docker) and deploy on K8s with horizontal pod autoscaling for multi-node HA.",
        "<b>Real-Time Streaming:</b> Integrate with Kafka or MQTT for live field data streaming from IoT-connected vehicles.",
        "<b>Predictive Analytics:</b> Train time-series models (Prophet/ARIMA) on failure trends for proactive quality alerts.",
        "<b>Knowledge Graph:</b> Build a Neo4j knowledge graph linking models, parts, failure modes, and repair actions.",
        "<b>Multi-Language Support:</b> Extend NLP pipeline for Japanese, Korean, and other OEM-relevant languages.",
    ]
    for item in long_term:
        story.append(bullet(item, s))

    story.append(PageBreak())

    # ═════════════════════════════════════════════════════════════════════════
    #  18. TECHNOLOGY STACK SUMMARY
    # ═════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("18. Technology Stack Summary", s['h1']))
    story.append(section_divider())

    story.append(make_table(
        ["Category", "Technology", "Version / Variant", "Role"],
        [
            ["Language", "Python", "3.9+", "Primary development language"],
            ["Web Framework", "Streamlit", "1.x", "Frontend UI and application server"],
            ["Database", "SQLite 3", "WAL mode", "Structured data storage"],
            ["Vector Store", "FAISS (faiss-cpu)", "1.x", "384-dim cosine similarity index"],
            ["Embedding", "SentenceTransformers", "all-MiniLM-L6-v2", "Text → 384-dim vector encoding"],
            ["LLM Runtime", "llama-cpp-python", "CUDA build", "Local GGUF model inference"],
            ["LLM Model", "Phi-3 Mini 4K Instruct", "Q4 GGUF (2.4 GB)", "Chat, summary, SQL generation"],
            ["NLP", "spaCy", "en_core_web_sm", "NER and keyword extraction"],
            ["Visualization", "Plotly", "Express + Graph Objects", "6 interactive chart types"],
            ["Data Processing", "Pandas", "2.x", "DataFrame operations and analytics"],
            ["PDF Generation", "ReportLab", "4.x", "Professional PDF report rendering"],
            ["DOCX Generation", "python-docx", "0.8+", "Word document report generation"],
            ["Excel Parsing", "openpyxl", "3.x", "FTIR Excel file reading"],
            ["Numerical", "NumPy", "1.x", "Vector array operations"],
            ["GPU Acceleration", "NVIDIA CUDA", "11.x+", "LLM inference GPU offloading"],
        ],
        col_widths=[80, 110, 120, 190]
    ))

    story.append(Spacer(1, 30))
    story.append(HRFlowable(width="40%", thickness=2, color=colors.HexColor('#0ea5e9'),
                            spaceBefore=20, spaceAfter=10))
    story.append(Paragraph("— End of Document —", s['cover_meta']))
    story.append(Paragraph(
        f"Document generated on {datetime.datetime.now().strftime('%B %d, %Y at %H:%M:%S')}",
        s['cover_meta']
    ))

    # ═════════════════════════════════════════════════════════════════════════
    #  BUILD PDF
    # ═════════════════════════════════════════════════════════════════════════
    doc.build(story, canvasmaker=EnterpriseCanvas)
    print(f"\n{'='*60}")
    print(f"  ✅ Architecture documentation generated successfully!")
    print(f"  📄 Output: {os.path.abspath(output_path)}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "System_Architecture_Documentation.pdf")
    build_document(output)
