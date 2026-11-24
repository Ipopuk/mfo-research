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
    ("Decision", "Решение", ["PK decision_id", "FK application_id (уникальный)", "Исход, причина, условия, дата", "Код сотрудника (текст)"], (690, 785, 300, 185)),
    ("Notification", "Уведомление", ["PK notification_id", "FK decision_id", "Канал, дата", "Статус передачи"], (70, 785, 280, 185)),
]

# Every child references exactly one parent; a parent can have no children yet.
RELATIONS = [
    ("Applicant", "Application", "1:0..*", ((340, 465), (690, 465))),
    ("Applicant", "Income", "1:0..*", ((190, 390), (190, 255))),
    ("Applicant", "Obligation", "1:0..*", ((340, 415), (525, 255))),
    ("Application", "ApplicationDocument", "1:0..*", ((920, 370), (1220, 255))),
    ("Document", "ApplicationDocument", "1:0..*", ((1460, 175), (1400, 175))),
    ("Application", "Consent", "1:0..*", ((990, 465), (1440, 465))),
    ("Application", "CheckResult", "1:0..*", ((950, 560), (1440, 765))),
    ("Application", "Decision", "1:0..1", ((840, 560), (840, 785))),
    ("Decision", "Notification", "1:0..*", ((690, 875), (350, 875))),
]

LEGEND = "Две черты — ровно один; кружок и черта — 0..1; кружок и лапка — 0..*."
ASSOCIATION_NOTE = "Связь M:N между заявкой и документом разрешена сущностью «ДокументЗаявки»."

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
    boxes = {code: box for code, _, _, box in ENTITIES}
    for i, (source, target, cardinality, (a, b)) in enumerate(RELATIONS, 1):
        arrow = "ERzeroToOne" if cardinality == "1:0..1" else "ERzeroToMany"
        sx, sy, sw, sh = boxes[source]
        tx, ty, tw, th = boxes[target]
        anchors = (f"exitX={(a[0] - sx) / sw:.4f};exitY={(a[1] - sy) / sh:.4f};"
                   f"entryX={(b[0] - tx) / tw:.4f};entryY={(b[1] - ty) / th:.4f};")
        cell = ET.SubElement(root, "mxCell", {
            "id": f"Relation_{i}", "value": cardinality,
            "style": "edgeStyle=none;html=0;rounded=0;"
                     f"startArrow=ERmandOne;endArrow={arrow};startFill=0;endFill=0;"
                     f"strokeColor=#475569;fontSize=14;{anchors}",
            "edge": "1", "parent": "1", "source": source, "target": target,
        })
        ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    for code, value, y in (("Legend", LEGEND, 993), ("AssociationNote", ASSOCIATION_NOTE, 1018)):
        cell = ET.SubElement(root, "mxCell", {
            "id": code, "value": value, "style": "text;align=left;fontSize=16;html=0;",
            "vertex": "1", "parent": "1",
        })
        ET.SubElement(cell, "mxGeometry", {
            "x": "70", "y": str(y), "width": "850", "height": "24", "as": "geometry",
        })
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

    for code, name, attributes, (x, y, width, height) in ENTITIES:
        draw.rectangle((x, y, x + width, y + height), fill="#eff6ff", outline="#334155", width=2)
        draw.rectangle((x, y, x + width, y + 36), fill="#dbeafe", outline="#334155", width=2)
        draw.text((x + 10, y + 7), name, font=header_font, fill="#0f172a")
        for i, attribute in enumerate(attributes):
            draw.text((x + 12, y + 46 + i * 27), attribute, font=body_font, fill="#0f172a")

    def marker(origin, remote, cardinality):
        length = math.dist(origin, remote)
        dx, dy = (remote[0] - origin[0]) / length, (remote[1] - origin[1]) / length

        def point(distance, offset=0):
            return (origin[0] + distance * dx - offset * dy,
                    origin[1] + distance * dy + offset * dx)

        if cardinality == "0..*":
            for offset in (-9, 9):
                draw.line((point(18), point(8, offset)), fill="#475569", width=2)
        else:
            draw.line((point(8, -8), point(8, 8)), fill="#475569", width=2)
        if cardinality == "1":
            draw.line((point(16, -8), point(16, 8)), fill="#475569", width=2)
        else:
            x, y = point(26)
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="white", outline="#475569", width=2)

    for _, _, cardinality, (a, b) in RELATIONS:
        draw.line((a, b), fill="#475569", width=2)
        marker(a, b, "1")
        marker(b, a, cardinality.split(":")[1])
        cx, cy = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
        width = draw.textlength(cardinality, font=label_font)
        if a[0] == b[0]:
            cx += width / 2 + 9
        else:
            cy -= 25
        draw.text((cx - width / 2, cy), cardinality, font=label_font, fill="#334155")

    draw.text((70, 991), LEGEND, font=body_font, fill="#334155")
    draw.text((70, 1016), ASSOCIATION_NOTE, font=body_font, fill="#334155")
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
