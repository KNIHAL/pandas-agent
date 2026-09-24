"""CSV/Excel/PDF-table/PDF-report exporters for artifacts-visualization.

All exporters take tabular data as `list[dict]` (rows), consistent with the
row-shape already used elsewhere in the repo (e.g. investigation_engine's
compare_segments/drill_down inputs), and write into <repo_root>/exports/.

PDF generation uses reportlab (pure-Python, no system deps) — the only
library in this module not already covered by requirements.txt.
"""
from __future__ import annotations

import os
import time
import uuid

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _exports_dir() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exports_dir = os.path.join(base_dir, "exports")
    os.makedirs(exports_dir, exist_ok=True)
    return exports_dir


def _out_path(prefix: str, ext: str) -> str:
    return os.path.join(_exports_dir(), f"{prefix}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}")


def export_csv(data: list[dict], filename_prefix: str = "dataset") -> str:
    df = pd.DataFrame(data)
    path = _out_path(filename_prefix, "csv")
    df.to_csv(path, index=False)
    return path


def export_excel(data: list[dict], filename_prefix: str = "dataset", sheet_name: str = "Sheet1") -> str:
    df = pd.DataFrame(data)
    path = _out_path(filename_prefix, "xlsx")
    df.to_excel(path, index=False, sheet_name=sheet_name)
    return path


def export_pdf_table(data: list[dict], title: str = "Dataset", filename_prefix: str = "dataset") -> str:
    """Render tabular data as a PDF table."""
    df = pd.DataFrame(data)
    path = _out_path(filename_prefix, "pdf")

    doc = SimpleDocTemplate(path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    table_data = [list(df.columns)] + df.astype(str).values.tolist()
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4e73df")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return path


def export_report(title: str, sections: list[dict], filename_prefix: str = "report") -> str:
    """Render a text analysis report (title + heading/body sections) as PDF.

    Each section is {"heading": str, "body": str}.
    """
    path = _out_path(filename_prefix, "pdf")

    doc = SimpleDocTemplate(path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 16)]

    for section in sections:
        elements.append(Paragraph(section["heading"], styles["Heading2"]))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(section["body"], styles["BodyText"]))
        elements.append(Spacer(1, 14))

    doc.build(elements)
    return path
