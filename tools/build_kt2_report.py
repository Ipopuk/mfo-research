"""Extend the existing KT1 Word report with the KT2 analytical chapter.

The Markdown source is deliberately kept readable in docs/kt2/report_section.md.
Run from the repository root with the local document environment:
    .venv/Scripts/python tools/build_kt2_report.py
"""

from __future__ import annotations

from io import BytesIO
import json
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
RESEARCH = ROOT / "docs/research_stage.md"
BASE = ROOT / "report/Отчет_ИКБО-10-24_ПавловаАА_КТ1.docx"
OUTPUT = ROOT / "report/Отчет_ИКБО-10-24_ПавловаАА_КТ2.docx"
TOPIC = "Потребительское кредитование в микрофинансовой организации"
SOURCES = [
    *(
        f"{item['number']}. {item['description']}"
        for item in json.loads((ROOT / "docs/sources.json").read_text(encoding="utf-8"))
        if item["number"] in (19, 20)
    ),
    "21. Business Process Model and Notation (BPMN), Version 2.0.2 / Object Management Group. — 2014. — URL: https://www.omg.org/spec/BPMN/2.0.2/PDF/ (дата обращения: 02.11.2026). — Текст : электронный.",
    "22. Основы проектирования баз данных / Microsoft Support. — URL: https://support.microsoft.com/ru-ru/access/database-design-basics (дата обращения: 02.11.2026). — Текст : электронный.",
    "23. ГОСТ 19.701-90. Единая система программной документации. Схемы алгоритмов, программ, данных и систем. Обозначения условные и правила выполнения. — URL: https://protect.gost.ru/gost/details/0c85e066-f89e-433d-a6d3-b7f746bd0c7c (дата обращения: 02.11.2026). — Текст : электронный.",
    "24. Cormen, T. H. Introduction to Algorithms / T. H. Cormen, C. E. Leiserson, R. L. Rivest, C. Stein. — 4th ed. — Cambridge, MA : The MIT Press, 2022. — URL: https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/ (accessed: 02.11.2026). — Text : electronic.",
]


def front_line(document: Document, value: str, *, size=12, bold=False,
               center=False, before=0, after=5):
    item = document.add_paragraph()
    item.alignment = WD_ALIGN_PARAGRAPH.CENTER if center else WD_ALIGN_PARAGRAPH.LEFT
    item.paragraph_format.first_line_indent = Cm(0)
    item.paragraph_format.line_spacing = 1.15
    item.paragraph_format.space_before = Pt(before)
    item.paragraph_format.space_after = Pt(after)
    run = item.add_run(value)
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    return item


def replace_front_images(document: Document) -> None:
    originals = document.paragraphs[:3]
    if any(len(item._p.xpath(".//w:drawing")) != 1 for item in originals):
        raise ValueError("Expected three image-only title/assignment pages in KT1 source")
    anchor = document.paragraphs[3]._p  # preserve the two work-schedule images
    first_new = len(document.element.body) - 1

    front_line(document, "МИНОБРНАУКИ РОССИИ", center=True, bold=True)
    front_line(document, "Федеральное государственное бюджетное образовательное учреждение", center=True)
    front_line(document, "высшего образования «МИРЭА — Российский технологический университет»", center=True)
    front_line(document, "РТУ МИРЭА", center=True, bold=True, size=14)
    front_line(document, "Институт информационных технологий (ИИТ)", center=True, before=32)
    front_line(document, "Кафедра инструментального и прикладного программного обеспечения (ИиППО)", center=True)
    front_line(document, "ОТЧЁТ ПО ПРОИЗВОДСТВЕННОЙ ПРАКТИКЕ", center=True,
               bold=True, size=16, before=78, after=8)
    front_line(document, "Учебная практика", center=True, bold=True, size=14)
    front_line(document, f"Тема практики: «{TOPIC}»", center=True,
               bold=True, size=14, before=32, after=24)
    front_line(document, "Выполнила: студентка 3 курса группы ИКБО-10-24", size=14, before=30)
    front_line(document, "Павлова Анна Алексеевна", size=14)
    front_line(document, "Руководитель практики от кафедры: Синицын Анатолий Васильевич", size=14, before=18)
    front_line(document, "Подпись студентки: ____________________    Подпись руководителя: ____________________", before=18)
    front_line(document, "Москва — 2026", center=True, size=14, before=80)
    document.add_page_break()

    front_line(document, "РТУ МИРЭА · Институт информационных технологий", center=True, size=12)
    front_line(document, "ИНДИВИДУАЛЬНОЕ ЗАДАНИЕ НА ПРОИЗВОДСТВЕННУЮ ПРАКТИКУ", center=True,
               bold=True, size=15, before=25)
    front_line(document, "Учебная практика", center=True, bold=True, size=13, after=16)
    front_line(document, f"Тема практики: «{TOPIC}»", bold=True, size=13, after=12)
    front_line(document, "Студентке 3 курса группы ИКБО-10-24 Павловой Анне Алексеевне", size=12)
    front_line(document, "Место практики: ООО «Бюджетные и Финансовые Технологии».", size=12)
    front_line(document, "Сроки практики: с 1 сентября по 21 декабря 2026 года.", size=12, after=16)
    front_line(document, "1. СОДЕРЖАНИЕ ПРАКТИКИ", bold=True, size=13, after=9)
    front_line(document, "1.1 Изучить научную и техническую литературу, стандарты и документацию среды разработки и программных средств, включая издания на иностранном языке.", after=9)
    front_line(document, "1.2 Исследовать предметную область и построить модель основного бизнес-процесса; спроектировать логическую и физическую модели данных; разработать алгоритмы и реализовать их процедурно на Python и объектно-ориентированно на Java; выполнить тестирование и отладку.", after=9)
    front_line(document, "1.3 Ознакомиться с нормативными документами по теме практики, стандартами оформления программного кода и условиями лицензирования используемых программных средств.", after=9)
    front_line(document, "1.4 Выполнить на иностранном языке перевод фрагмента профессионального источника по теме практики и подготовить аннотацию к отчёту с глоссарием.", after=9)
    front_line(document, "1.5 Оценить требования рынка труда к специалистам рассматриваемой области и предложения образовательных программ; определить приоритеты профессионального роста.", after=13)
    front_line(document, "2. ДОПОЛНИТЕЛЬНОЕ ЗАДАНИЕ: нет.", bold=True, size=12)
    document.add_page_break()

    front_line(document, "3. ОРГАНИЗАЦИОННО-МЕТОДИЧЕСКИЕ УКАЗАНИЯ", bold=True, size=13)
    front_line(document, "В процессе практики рекомендуется использовать периодические издания и отраслевую литературу не старше пяти лет от даты начала прохождения практики.", after=22)
    front_line(document, "Руководитель практики от кафедры: Синицын А. В.", before=12)
    front_line(document, "Дата: ________________    Подпись: ____________________", after=18)
    front_line(document, "Руководитель практики от профильной организации: Жиркова М. И.")
    front_line(document, "Дата: ________________    Подпись: ____________________", after=18)
    front_line(document, "Задание получила: Павлова А. А.")
    front_line(document, "Дата: ________________    Подпись: ____________________", after=18)
    front_line(document, "Согласовано, заведующий кафедрой: Болбаков Р. Г.")
    front_line(document, "Дата: ________________    Подпись: ____________________", after=20)
    front_line(document, "Отметки о прохождении инструктажей и рабочий график приведены далее.")
    document.add_page_break()

    for element in list(document.element.body)[first_new:-1]:
        anchor.addprevious(element)
    for item in originals:
        item._p.getparent().remove(item._p)


def sync_research_sections(document: Document) -> None:
    lines = RESEARCH.read_text(encoding="utf-8").splitlines()
    for number, next_number in (("1.4", "1.5"), ("1.6", "1.7"), ("1.7", "СПИСОК")):
        start_line = next(i for i, line in enumerate(lines) if line.startswith(f"## {number} "))
        end_line = next(i for i in range(start_line + 1, len(lines))
                        if lines[i].startswith(f"## {next_number} ") or
                        (next_number == "СПИСОК" and lines[i].startswith("# СПИСОК")))
        content = [line.strip() for line in lines[start_line + 1:end_line] if line.strip()]
        headings = document.paragraphs
        start = next(i for i, p in enumerate(headings)
                     if p.style.name.startswith("Heading") and p.text.startswith(f"{number} "))
        end = next(i for i in range(start + 1, len(headings))
                   if headings[i].style.name.startswith("Heading") and
                   (headings[i].text.startswith(f"{next_number} ") or
                    (next_number == "СПИСОК" and headings[i].text == "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ")))
        anchor = headings[end]._p
        for item in headings[start + 1:end]:
            item._p.getparent().remove(item._p)
        for value in content:
            item = paragraph(document, value)
            anchor.addprevious(item._p)


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
    replace_front_images(document)
    sync_research_sections(document)
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
