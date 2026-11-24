"""Add the KT3 chapter to the published KT2 DOCX."""
from __future__ import annotations

from io import BytesIO
import re

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.shared import Cm, Pt
from PIL import Image

from build_kt2_report import OUTPUT as KT2, ROOT, add_code, bibliography_item, paragraph


OUTPUT = ROOT / "report/Отчет_ИКБО-10-24_ПавловаАА_КТ3.docx"
SOURCE = ROOT / "docs/kt3/report_section.md"
LINK = re.compile(r"(\[([^\]]+)\]\((https://[^)]+)\))")
TABLE_WIDTHS = {
    1: [3, 4.25, 4.5, 5.25],
    2: [2.8, 4.4, 5.2, 4.6],
    3: [0.8, 5.1, 6.55, 4.55],
    4: [6.2, 2.4, 8.4],
}
SOURCES = [
    "25. Object Management Group. Unified Modeling Language (UML), Version 2.5.1. — 2017. — URL: https://www.omg.org/spec/UML/2.5.1 (accessed: 24.11.2026). — Text : electronic.",
    "26. Gosling, J. The Java Language Specification. Java SE 21 Edition / J. Gosling, B. Joy, G. Steele et al. — Oracle, 2023. — URL: https://docs.oracle.com/javase/specs/jls/se21/html/ (accessed: 24.11.2026). — Text : electronic.",
    "27. Architectural principles / Microsoft Learn. — 2023. — URL: https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/architectural-principles (accessed: 24.11.2026). — Text : electronic.",
]


def add_link(item, label: str, url: str, size: int) -> None:
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), item.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True))
    run = item.add_run(label)
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.font.underline = True
    link.append(run._r)
    item._p.append(link)


def write_cell(cell, value: str, header: bool) -> None:
    item = cell.paragraphs[0]
    item.alignment = WD_ALIGN_PARAGRAPH.LEFT
    item.paragraph_format.first_line_indent = Cm(0)
    item.paragraph_format.space_after = Pt(4)
    item.paragraph_format.space_before = Pt(3)
    item.paragraph_format.line_spacing = 1.15
    start = 0
    for match in LINK.finditer(value):
        run = item.add_run(value[start:match.start()])
        run.font.name = "Times New Roman"
        run.font.size = Pt(11)
        add_link(item, match[2], match[3], 11)
        start = match.end()
    run = item.add_run(value[start:])
    run.bold = header
    run.font.name = "Times New Roman"
    run.font.size = Pt(11)


def add_table(document, rows: list[list[str]], number: int) -> None:
    widths = TABLE_WIDTHS[number]
    table = document.add_table(rows=0, cols=len(widths))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for column, width in zip(table.columns, widths, strict=True):
        column.width = Cm(width)
    for index, values in enumerate(rows):
        row = table.add_row()
        properties = row._tr.get_or_add_trPr()
        properties.append(OxmlElement("w:cantSplit"))
        if index == 0:
            properties.append(OxmlElement("w:tblHeader"))
        for cell, value, width in zip(row.cells, values, widths, strict=True):
            cell.width = Cm(width)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            write_cell(cell, value, index == 0)


def label(document, value: str, *, above: bool = False):
    item = paragraph(document, value)
    item.alignment = WD_ALIGN_PARAGRAPH.LEFT if above else WD_ALIGN_PARAGRAPH.CENTER
    item.paragraph_format.first_line_indent = Cm(0)
    item.paragraph_format.keep_with_next = above
    item.paragraph_format.space_before = Pt(9 if above else 0)
    item.paragraph_format.space_after = Pt(4 if above else 10)
    for run in item.runs:
        run.font.size = Pt(12)
    return item


def add_uml(document, path, description: str) -> None:
    def image_block(image, title: str) -> None:
        item = document.add_paragraph()
        item.alignment = WD_ALIGN_PARAGRAPH.CENTER
        item.paragraph_format.first_line_indent = Cm(0)
        item.paragraph_format.keep_with_next = True
        item.paragraph_format.space_after = Pt(0)
        item.add_run().add_picture(image, width=Cm(16.8))
        label(document, title)

    image_block(str(path), description)
    with Image.open(path) as original:
        width, height = original.size
        panels = [
            (0, 0.125, 0.54, 0.955, "проверка комплектности и связи с документами"),
            (0.385, 0, 1, 0.45, "заявитель, заявка и расчёт нагрузки"),
            (0.385, 0.43, 0.86, 0.85, "согласие, проверка, решение и уведомление"),
        ]
        for index, (left, top, right, bottom, detail) in enumerate(panels, 1):
            crop = original.crop((int(left * width), int(top * height),
                                  int(right * width), int(bottom * height)))
            data = BytesIO()
            crop.save(data, format="PNG")
            data.seek(0)
            image_block(data, f"Рисунок 3.1, фрагмент {index} — {detail}")


def build() -> None:
    document = Document(KT2)
    intro = next(p for p in document.paragraphs if p.text.startswith("В настоящем отчёте"))
    old = "В настоящем отчёте представлены исследовательский и аналитический этапы."
    intro.text = intro.text.replace(old, "В отчёте представлены исследовательский и аналитический этапы, реализация на Java и организационный раздел.", 1)
    bibliography = next(p for p in document.paragraphs if p.text == "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ")
    appendix = next(p for p in document.paragraphs if p.text == "ПРИЛОЖЕНИЕ А")
    body = document.element.body
    before_chapter = len(body) - 1
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    index = 0
    table_number = 0
    while index < len(lines):
        value = lines[index].strip()
        index += 1
        if not value:
            continue
        if value.startswith(("# ", "## ")):
            prefix, title = value.split(" ", 1)
            heading = document.add_paragraph(title, style=f"Heading {len(prefix)}")
            heading.paragraph_format.keep_with_next = True
            if prefix == "#":
                heading.paragraph_format.page_break_before = True
        elif value.startswith("!["):
            match = re.fullmatch(r"!\[(.+)\]\((.+)\)", value)
            if match is None:
                raise ValueError(f"Invalid illustration: {value}")
            add_uml(document, ROOT / match[2], match[1])
        elif value.startswith(("Таблица 3.", "Фрагмент 3.")):
            label(document, value, above=True)
        elif value.startswith("|"):
            rows = []
            while True:
                parts = [cell.strip() for cell in value.strip("|").split("|")]
                if not all(re.fullmatch(r"-+", cell) for cell in parts):
                    rows.append(parts)
                if index == len(lines) or not lines[index].startswith("|"):
                    break
                value = lines[index].strip()
                index += 1
            table_number += 1
            add_table(document, rows, table_number)
        elif value == "```java":
            code = []
            while index < len(lines) and lines[index].strip() != "```":
                code.append(lines[index])
                index += 1
            if index == len(lines):
                raise ValueError("Unclosed Java code block")
            index += 1
            add_code(document, code)
        else:
            paragraph(document, value)

    for element in list(body)[before_chapter:-1]:
        bibliography._p.addprevious(element)
    for source in SOURCES:
        item = bibliography_item(document, source)
        item.alignment = WD_ALIGN_PARAGRAPH.LEFT
        appendix._p.addprevious(item._p)
    document.core_properties.title = "Потребительское кредитование в микрофинансовой организации — КТ3"
    document.core_properties.subject = "Учебная практика. Контрольные точки 1–3"
    document.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
