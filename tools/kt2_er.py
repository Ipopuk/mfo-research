"""Build an editable draw.io logical ER source and its matching PNG."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


# ID, Russian name, key/attribute lines, canvas box (x, y, width, height).
ENTITIES = [
    ("Applicant", "Заявитель", ["PK applicant_id", "ФИО", "Контакт"], (70, 390, 270, 155)),
    ("Application", "Заявка", ["PK application_id", "FK applicant_id", "Сумма, срок", "Статус, дата поступления"], (690, 370, 300, 190)),
    ("Document", "Документ", ["PK document_id", "Вид", "Действителен"], (1460, 90, 270, 155)),
    ("ApplicationDocument", "ДокументЗаявки", ["PK, FK application_id", "PK, FK document_id", "Дата получения"], (1100, 85, 300, 170)),
    ("Consent", "Согласие", ["PK consent_id", "FK application_id", "Вид, дата, статус"], (1440, 390, 290, 155)),
    ("CheckResult", "РезультатПроверки", ["PK check_id", "FK application_id", "Вид, источник", "Дата, результат"], (1440, 710, 290, 185)),
    ("Income", "Доход", ["PK income_id", "FK applicant_id", "Месячная сумма", "Подтверждён"], (65, 70, 270, 185)),
    ("Obligation", "Обязательство", ["PK obligation_id", "FK applicant_id", "Месячный платёж", "Активно"], (390, 70, 275, 185)),
    ("Decision", "Решение", ["PK decision_id", "FK application_id", "Исход, причина", "Согласованные условия"], (690, 785, 300, 185)),
    ("Notification", "Уведомление", ["PK notification_id", "FK decision_id", "Канал, дата", "Статус передачи"], (70, 785, 280, 185)),
]

# Parent 1 -> child N, except the single optional decision.
RELATIONS = [
    ("Applicant", "Application", "1:N", ((340, 465), (690, 465))),
    ("Applicant", "Income", "1:N", ((190, 390), (190, 255))),
    ("Applicant", "Obligation", "1:N", ((340, 415), (525, 255))),
    ("Application", "ApplicationDocument", "1:N", ((920, 370), (1220, 255))),
    ("Document", "ApplicationDocument", "1:N", ((1460, 175), (1400, 175))),
    ("Application", "Consent", "1:N", ((990, 465), (1440, 465))),
    ("Application", "CheckResult", "1:N", ((950, 560), (1440, 765))),
    ("Application", "Decision", "1:0..1", ((840, 560), (840, 785))),
    ("Decision", "Notification", "1:N", ((690, 875), (350, 875))),
]


def build_source(path: Path) -> None:
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "type": "device"})
    diagram = ET.SubElement(mxfile, "diagram", {"id": "kt2-er", "name": "ER logical"})
    graph = ET.SubElement(diagram, "mxGraphModel", {
        "dx": "1800", "dy": "1050", "grid": "1", "gridSize": "10", "guides": "1",
        "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "1",
        "pageScale": "1", "pageWidth": "1800", "pageHeight": "1050", "math": "0", "shadow": "0",
    })
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    for code, name, attributes, (x, y, width, height) in ENTITIES:
        value = "\n".join([name, *attributes])
        cell = ET.SubElement(root, "mxCell", {
            "id": code, "value": value,
            "style": "rounded=0;whiteSpace=wrap;html=0;align=left;verticalAlign=top;spacing=9;"
                     "fontSize=15;strokeColor=#334155;fillColor=#eff6ff;",
            "vertex": "1", "parent": "1",
        })
        ET.SubElement(cell, "mxGeometry", {
            "x": str(x), "y": str(y), "width": str(width), "height": str(height), "as": "geometry",
        })
    for i, (source, target, cardinality, _) in enumerate(RELATIONS, 1):
        arrow = "ERone" if cardinality == "1:0..1" else "ERmany"
        cell = ET.SubElement(root, "mxCell", {
            "id": f"Relation_{i}", "value": cardinality,
            "style": "entityRelationEdgeStyle;html=0;rounded=0;jettySize=auto;orthogonalLoop=1;"
                     f"startArrow=ERone;endArrow={arrow};startFill=0;endFill=0;"
                     "strokeColor=#475569;fontSize=13;",
            "edge": "1", "parent": "1", "source": source, "target": target,
        })
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.indent(mxfile, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(mxfile).write(path, encoding="utf-8", xml_declaration=True)


def build_png(path: Path) -> None:
    image = Image.new("RGB", (1810, 1050), "white")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 24)
    header_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 18)
    body_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    label_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 14)
    draw.text((70, 15), "КТ2. Логическая модель данных · вороньи лапки", font=title_font, fill="#0f172a")

    def crowfoot(a: tuple[int, int], b: tuple[int, int]) -> None:
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        length = 14
        base = (b[0] - length * math.cos(angle), b[1] - length * math.sin(angle))
        perpendicular = (-math.sin(angle), math.cos(angle))
        for offset in (-12, 0, 12):
            tip = (b[0] + offset * perpendicular[0], b[1] + offset * perpendicular[1])
            draw.line((base, tip), fill="#475569", width=2)

    for source, target, cardinality, (a, b) in RELATIONS:
        draw.line((a, b), fill="#475569", width=2)
        if cardinality == "1:N":
            crowfoot(a, b)
        else:
            draw.line((b[0] - 8, b[1], b[0] + 8, b[1]), fill="#475569", width=2)
        midpoint = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
        tw = draw.textbbox((0, 0), cardinality, font=label_font)[2]
        draw.rectangle((midpoint[0] - tw // 2 - 4, midpoint[1] - 20,
                        midpoint[0] + tw // 2 + 4, midpoint[1] + 1), fill="white")
        draw.text((midpoint[0] - tw // 2, midpoint[1] - 19), cardinality,
                  font=label_font, fill="#334155")

    for code, name, attributes, (x, y, width, height) in ENTITIES:
        draw.rectangle((x, y, x + width, y + height), fill="#eff6ff", outline="#334155", width=2)
        draw.rectangle((x, y, x + width, y + 36), fill="#dbeafe", outline="#334155", width=2)
        draw.text((x + 10, y + 7), name, font=header_font, fill="#0f172a")
        for i, attribute in enumerate(attributes):
            draw.text((x + 12, y + 46 + i * 27), attribute, font=body_font, fill="#0f172a")
    draw.text((70, 1005), "M:N между заявкой и документом разрешена сущностью «ДокументЗаявки»; типы SQL относятся к КТ4.",
              font=body_font, fill="#334155")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true")
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    if not args.source and not args.png:
        parser.error("Укажите --source или --png")
    root = Path(__file__).resolve().parents[1] / "models"
    if args.source:
        build_source(root / "er_logical.drawio")
    if args.png:
        build_png(root / "er_logical.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
