"""Extend the existing KT1 Word report with the KT2 analytical chapter.

The Markdown source is deliberately kept readable in docs/kt2/report_section.md.
Run from the repository root with the local document environment:
    .venv/Scripts/python tools/build_kt2_report.py
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
from docx.oxml import OxmlElement
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/kt2/report_section.md"
BASE = ROOT / "report/Отчет_ИКБО-10-24_ПавловаАА_КТ1.docx"
OUTPUT = ROOT / "report/Отчет_ИКБО-10-24_ПавловаАА_КТ2.docx"
SOURCES = [
    "19. Business Process Model and Notation (BPMN), Version 2.0.2 / Object Management Group. — 2014. — URL: https://www.omg.org/spec/BPMN/2.0.2/PDF/ (дата обращения: 02.11.2026). — Текст : электронный.",
    "20. Основы проектирования баз данных / Microsoft Support. — URL: https://support.microsoft.com/ru-ru/access/database-design-basics (дата обращения: 02.11.2026). — Текст : электронный.",
    "21. ГОСТ 19.701-90. Единая система программной документации. Схемы алгоритмов, программ, данных и систем. Обозначения условные и правила выполнения. — URL: https://protect.gost.ru/gost/details/0c85e066-f89e-433d-a6d3-b7f746bd0c7c (дата обращения: 02.11.2026). — Текст : электронный.",
    "22. Cormen, T. H. Introduction to Algorithms / T. H. Cormen, C. E. Leiserson, R. L. Rivest, C. Stein. — 4th ed. — Cambridge, MA : The MIT Press, 2022. — URL: https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/ (accessed: 02.11.2026). — Text : electronic.",
]


def paragraph(document: Document, value: str):
    item = document.add_paragraph(style="Normal")
    item.add_run(value)
    item.paragraph_format.first_line_indent = Cm(1.25)
    item.paragraph_format.line_spacing = 1.5
    item.paragraph_format.space_after = Pt(0)
    return item


def caption(document: Document, value: str):
    item = document.add_paragraph()
    item.alignment = WD_ALIGN_PARAGRAPH.CENTER
    item.paragraph_format.space_before = Pt(6)
    item.paragraph_format.space_after = Pt(9)
    item.paragraph_format.keep_with_next = False
    run = item.add_run(value)
    run.font.name = "Times New Roman"
    run.font.size = Pt(12)
    return item


def add_picture(document: Document, path: Path, label: str):
    available = document.sections[0].page_width - document.sections[0].left_margin - document.sections[0].right_margin
    item = document.add_paragraph()
    item.alignment = WD_ALIGN_PARAGRAPH.CENTER
    item.paragraph_format.space_after = Pt(0)
    item.add_run().add_picture(str(path), width=available)
    caption(document, label)

    # Keep the complete overview and show overlapping details at print size.
    with Image.open(path) as image:
        w, h = image.size
        if w / h >= 2.5:
            left, right = int(w * .075), int(w * .985)
            panel = int((right - left) / 4 + 85)
            step = (right - left - panel) / 3
            boxes = [(int(left + index * step), 0,
                      int(left + index * step + panel), h) for index in range(4)]
        elif w / h >= 1.45:
            boxes = [(0, 0, int(w * .57), h), (int(w * .43), 0, w, h)]
        else:
            boxes = [(0, 0, w, int(h * .57)), (0, int(h * .43), w, h)]
        for index, box in enumerate(boxes):
            part = image.crop(box)
            stream = BytesIO()
            part.save(stream, format="PNG")
            stream.seek(0)
            detail = document.add_paragraph()
            detail.alignment = WD_ALIGN_PARAGRAPH.CENTER
            detail.add_run().add_picture(stream, width=available)
            caption(document, f"{label} (фрагмент {index + 1})")


def add_table(document: Document, rows: list[list[str]]):
    table = document.add_table(rows=0, cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    is_entity_table = rows[0][0] == "Сущность"
    if is_entity_table:
        table.autofit = False
        widths = [Cm(3.8), Cm(7.0), Cm(5.7)]
        for column, width in zip(table.columns, widths):
            column.width = width
    for row_number, cells in enumerate(rows):
        row = table.add_row()
        if row_number == 0:
            row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        for column_number, (cell, value) in enumerate(zip(row.cells, cells)):
            cell.text = value
            if is_entity_table:
                cell.width = widths[column_number]
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for item in cell.paragraphs:
                item.alignment = WD_ALIGN_PARAGRAPH.LEFT
                item.paragraph_format.space_after = Pt(0)
                item.paragraph_format.line_spacing = 1.0
                for run in item.runs:
                    run.font.name = "Times New Roman"
                    run.font.size = Pt(10)
                    run.bold = row_number == 0
    document.add_paragraph()


def add_code(document: Document, lines: list[str]):
    item = document.add_paragraph()
    item.paragraph_format.left_indent = Cm(0.6)
    item.paragraph_format.space_after = Pt(6)
    item.paragraph_format.line_spacing = 1.0
    item.paragraph_format.keep_together = True
    run = item.add_run("\n".join(lines))
    run.font.name = "Courier New"
    run.font.size = Pt(9)


def build():
    document = Document(BASE)
    original_intro = next(p for p in document.paragraphs if p.text.startswith("В настоящем отчёте представлен только исследовательский этап."))
    original_intro.text = original_intro.text.replace(
        "В настоящем отчёте представлен только исследовательский этап.",
        "В настоящем отчёте представлены исследовательский и аналитический этапы.",
    )

    bibliography = next(p for p in document.paragraphs if p.text == "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ")
    appendix = next(p for p in document.paragraphs if p.text == "ПРИЛОЖЕНИЕ А")
    # Appended elements are moved ahead of the original bibliography after
    # creation; this retains every illustration and appendix from KT1.
    chapter_start = len(document.element.body) - 1
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        value = lines[i].strip()
        if not value:
            i += 1
            continue
        if value.startswith("## "):
            p = document.add_paragraph(value[3:], style="Heading 2")
            p.paragraph_format.keep_with_next = True
        elif value.startswith("# "):
            p = document.add_paragraph(value[2:], style="Heading 1")
            p.paragraph_format.page_break_before = True
            p.paragraph_format.keep_with_next = True
        elif value.startswith("!["):
            match = re.fullmatch(r"!\[(.+)]\((.+)\)", value)
            if not match:
                raise ValueError(f"Invalid image directive: {value}")
            add_picture(document, ROOT / match.group(2), match.group(1))
        elif value.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", x) for x in cells):
                    rows.append(cells)
                i += 1
            add_table(document, rows)
            continue
        elif value == "```python":
            code = []
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                code.append(lines[i])
                i += 1
            if i == len(lines):
                raise ValueError("Unclosed Python code fragment")
            add_code(document, code)
        elif value.startswith("Таблица 2."):
            caption(document, value)
        elif value.startswith("Фрагмент 2."):
            caption(document, value)
        else:
            paragraph(document, value)
        i += 1

    added = list(document.element.body)[chapter_start:-1]
    for element in added:
        if element.tag.endswith("sectPr"):
            continue
        bibliography._p.addprevious(element)

    for source in SOURCES:
        new = paragraph(document, source)
        appendix._p.addprevious(new._p)

    document.core_properties.title = "Потребительское кредитование в микрофинансовой организации — КТ2"
    document.core_properties.subject = "Исследовательский и аналитический этапы"
    document.save(OUTPUT)
    print(f"Report: {OUTPUT}")


if __name__ == "__main__":
    build()
