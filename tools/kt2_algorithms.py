"""Build editable draw.io flowcharts and PNGs for the two KT2 algorithms."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


# Each node is (ID, symbol, label, x, y, width, height).
ALGO_1 = {
    "title": "Алгоритм 1. Проверить комплектность заявки",
    "size": (1700, 1880),
    "nodes": [
        ("start", "terminal", "Начало", 650, 35, 380, 65),
        ("input", "io", "Ввести заявку, заявителя, документы, связи и требования", 580, 130, 520, 85),
        ("init_fields", "process", "missing_fields = []; missing_documents = []", 615, 245, 450, 65),
        ("field_loop", "loop", "Есть следующее обязательное поле?", 630, 340, 420, 85),
        ("field_missing", "decision", "Поле пустое или некорректное?", 650, 465, 380, 105),
        ("append_field", "process", "Добавить поле в missing_fields", 120, 480, 380, 70),
        ("kind_loop", "loop", "Есть следующий вид документа?", 630, 620, 420, 85),
        ("set_found", "process", "found = False", 650, 745, 380, 65),
        ("link_loop", "loop", "Есть следующая связь заявки с документом?", 630, 850, 420, 85),
        ("belongs", "decision", "Связь относится к этой заявке?", 650, 975, 380, 105),
        ("valid", "decision", "Документ нужного вида и действителен?", 650, 1110, 380, 105),
        ("found_true", "process", "found = True; выйти из внутреннего цикла", 1130, 1125, 450, 70),
        ("found_check", "decision", "Документ найден?", 650, 1275, 380, 105),
        ("append_kind", "process", "Добавить вид в missing_documents", 120, 1290, 400, 70),
        ("output", "io", "Вывести complete и перечни недостающего", 580, 1570, 520, 85),
        ("end", "terminal", "Конец", 650, 1700, 380, 65),
    ],
    "edges": [
        ("start", "input", "", [(840, 100), (840, 130)]),
        ("input", "init_fields", "", [(840, 215), (840, 245)]),
        ("init_fields", "field_loop", "", [(840, 310), (840, 340)]),
        ("field_loop", "field_missing", "Да", [(840, 425), (840, 465)]),
        ("field_loop", "kind_loop", "Нет", [(1050, 382), (1090, 382), (1090, 660), (1050, 660)]),
        ("field_missing", "append_field", "Да", [(650, 517), (500, 517)]),
        ("append_field", "field_loop", "", [(310, 480), (310, 380), (630, 380)]),
        ("field_missing", "field_loop", "Нет", [(1030, 517), (1170, 517), (1170, 380), (1050, 380)]),
        ("kind_loop", "set_found", "Да", [(840, 705), (840, 745)]),
        ("kind_loop", "output", "Нет", [(1050, 662), (1620, 662), (1620, 1612), (1100, 1612)]),
        ("set_found", "link_loop", "", [(840, 810), (840, 850)]),
        ("link_loop", "belongs", "Да", [(840, 935), (840, 975)]),
        ("link_loop", "found_check", "Нет", [(1050, 892), (1450, 892), (1450, 1327), (1030, 1327)]),
        ("belongs", "valid", "Да", [(840, 1080), (840, 1110)]),
        ("belongs", "link_loop", "Нет", [(650, 1027), (545, 1027), (545, 892), (630, 892)]),
        ("valid", "found_true", "Да", [(1030, 1162), (1130, 1162)]),
        ("valid", "link_loop", "Нет", [(650, 1162), (560, 1162), (560, 892), (630, 892)]),
        ("found_true", "found_check", "", [(1355, 1195), (1355, 1225), (840, 1225), (840, 1275)]),
        ("found_check", "append_kind", "Нет", [(650, 1327), (520, 1327)]),
        ("found_check", "kind_loop", "Да", [(1030, 1327), (1610, 1327), (1610, 690), (1050, 690)]),
        ("append_kind", "kind_loop", "", [(320, 1290), (320, 690), (630, 690)]),
        ("output", "end", "", [(840, 1655), (840, 1700)]),
    ],
}

ALGO_2 = {
    "title": "Алгоритм 2. Рассчитать предварительную платёжную нагрузку",
    "size": (1450, 1600),
    "nodes": [
        ("start", "terminal", "Начало", 545, 35, 360, 65),
        ("input", "io", "Ввести доходы, обязательства и предложенный платёж", 475, 130, 500, 85),
        ("negative", "decision", "Предложенный платёж отрицателен?", 65, 250, 360, 95),
        ("error", "io", "Вывести ошибку ввода", 65, 375, 360, 80),
        ("init", "process", "monthly_income = 0; existing_payments = 0", 500, 250, 450, 70),
        ("income_loop", "loop", "Есть следующая запись дохода?", 520, 350, 410, 85),
        ("income_valid", "decision", "Доход заявителя подтверждён?", 535, 480, 380, 105),
        ("add_income", "process", "Прибавить месячный доход", 65, 500, 350, 70),
        ("obligation_loop", "loop", "Есть следующее обязательство?", 520, 650, 410, 85),
        ("obligation_active", "decision", "Платёж заявителя активен?", 535, 780, 380, 105),
        ("add_payment", "process", "Прибавить месячный платёж", 65, 800, 350, 70),
        ("income_positive", "decision", "Подтверждённый доход больше нуля?", 535, 950, 380, 105),
        ("no_income", "io", "Вывести: недостаточно данных", 45, 1110, 430, 80),
        ("calculate", "process", "Доля = (платежи + новый платёж) / доход", 930, 965, 455, 80),
        ("output", "io", "Вывести предварительную долю платежей", 870, 1110, 500, 80),
        ("end", "terminal", "Конец", 545, 1330, 360, 65),
    ],
    "edges": [
        ("start", "input", "", [(725, 100), (725, 130)]),
        ("input", "negative", "", [(475, 172), (445, 172), (445, 297), (425, 297)]),
        ("negative", "error", "Да", [(245, 345), (245, 375)]),
        ("negative", "init", "Нет", [(425, 297), (500, 285)]),
        ("error", "end", "", [(65, 415), (20, 415), (20, 1362), (545, 1362)]),
        ("init", "income_loop", "", [(725, 320), (725, 350)]),
        ("income_loop", "income_valid", "Да", [(725, 435), (725, 480)]),
        ("income_loop", "obligation_loop", "Нет", [(930, 392), (1090, 392), (1090, 692), (930, 692)]),
        ("income_valid", "add_income", "Да", [(535, 532), (415, 532)]),
        ("add_income", "income_loop", "", [(240, 500), (240, 392), (520, 392)]),
        ("income_valid", "income_loop", "Нет", [(915, 532), (1030, 532), (1030, 392), (930, 392)]),
        ("obligation_loop", "obligation_active", "Да", [(725, 735), (725, 780)]),
        ("obligation_loop", "income_positive", "Нет", [(930, 692), (1400, 692), (1400, 925), (725, 925), (725, 950)]),
        ("obligation_active", "add_payment", "Да", [(535, 832), (415, 832)]),
        ("add_payment", "obligation_loop", "", [(240, 800), (240, 692), (520, 692)]),
        ("obligation_active", "obligation_loop", "Нет", [(915, 832), (1090, 832), (1090, 720), (930, 720)]),
        ("income_positive", "no_income", "Нет", [(535, 1002), (260, 1002), (260, 1110)]),
        ("income_positive", "calculate", "Да", [(915, 1002), (930, 1002)]),
        ("calculate", "output", "", [(1157, 1045), (1157, 1110)]),
        ("no_income", "end", "", [(260, 1190), (260, 1362), (545, 1362)]),
        ("output", "end", "", [(1120, 1190), (1120, 1362), (905, 1362)]),
    ],
}


def drawio(path: Path, model: dict) -> None:
    width, height = model["size"]
    mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "type": "device"})
    diagram = ET.SubElement(mxfile, "diagram", {"id": path.stem, "name": path.stem})
    graph = ET.SubElement(diagram, "mxGraphModel", {
        "dx": str(width), "dy": str(height), "grid": "1", "gridSize": "10",
        "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1",
        "page": "1", "pageScale": "1", "pageWidth": str(width), "pageHeight": str(height),
        "math": "0", "shadow": "0",
    })
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    styles = {
        "terminal": "ellipse;whiteSpace=wrap;html=0;",
        "io": "shape=parallelogram;whiteSpace=wrap;html=0;",
        "process": "rounded=0;whiteSpace=wrap;html=0;",
        "decision": "rhombus;whiteSpace=wrap;html=0;",
        "loop": "shape=hexagon;whiteSpace=wrap;html=0;",
    }
    for code, symbol, label, x, y, w, h in model["nodes"]:
        cell = ET.SubElement(root, "mxCell", {
            "id": code, "value": label,
            "style": styles[symbol] + "align=center;verticalAlign=middle;fontSize=17;"
                     "strokeColor=#334155;fillColor=#eff6ff;",
            "vertex": "1", "parent": "1",
        })
        ET.SubElement(cell, "mxGeometry", {
            "x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry",
        })
    for i, (source, target, label, points) in enumerate(model["edges"], 1):
        cell = ET.SubElement(root, "mxCell", {
            "id": f"flow_{i}", "value": label,
            "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
                     "html=0;endArrow=block;endFill=1;strokeColor=#475569;fontSize=15;",
            "edge": "1", "parent": "1", "source": source, "target": target,
        })
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        middle = ET.SubElement(geometry, "Array", {"as": "points"})
        for x, y in points[1:-1]:
            ET.SubElement(middle, "mxPoint", {"x": str(x), "y": str(y)})
    ET.indent(mxfile, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(mxfile).write(path, encoding="utf-8", xml_declaration=True)


def render_png(path: Path, model: dict) -> None:
    image = Image.new("RGB", model["size"], "white")
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 25)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    edge_font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
    draw.text((40, 5), model["title"], font=title_font, fill="#0f172a")

    def center_text(label: str, x: int, y: int, w: int, h: int) -> None:
        words = label.split()
        rows, current = [], ""
        for word in words:
            candidate = (current + " " + word).strip()
            if current and draw.textbbox((0, 0), candidate, font=font)[2] > w - 30:
                rows.append(current)
                current = word
            else:
                current = candidate
        if current:
            rows.append(current)
        line_height = 22
        for i, row in enumerate(rows):
            tw = draw.textbbox((0, 0), row, font=font)[2]
            draw.text((x + (w - tw) // 2, y + (h - len(rows) * line_height) // 2 + i * line_height),
                      row, font=font, fill="#0f172a")

    for source, target, label, points in model["edges"]:
        draw.line(points, fill="#475569", width=3, joint="curve")
        a, b = points[-2:]
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        tip1 = (b[0] - 11 * math.cos(angle - .5), b[1] - 11 * math.sin(angle - .5))
        tip2 = (b[0] - 11 * math.cos(angle + .5), b[1] - 11 * math.sin(angle + .5))
        draw.polygon((b, tip1, tip2), fill="#475569")
        if label:
            a, b = points[:2]
            cx, cy = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
            tw = draw.textbbox((0, 0), label, font=edge_font)[2]
            draw.rectangle((cx - tw // 2 - 4, cy - 21, cx + tw // 2 + 4, cy + 1), fill="white")
            draw.text((cx - tw // 2, cy - 20), label, font=edge_font, fill="#334155")

    for code, symbol, label, x, y, w, h in model["nodes"]:
        if symbol == "terminal":
            draw.ellipse((x, y, x + w, y + h), fill="#dcfce7", outline="#334155", width=3)
        elif symbol == "io":
            draw.polygon(((x + 25, y), (x + w, y), (x + w - 25, y + h), (x, y + h)),
                         fill="#fef3c7", outline="#334155")
        elif symbol == "decision":
            draw.polygon(((x + w // 2, y), (x + w, y + h // 2),
                          (x + w // 2, y + h), (x, y + h // 2)),
                         fill="white", outline="#334155")
        elif symbol == "loop":
            draw.polygon(((x + 40, y), (x + w - 40, y), (x + w, y + h // 2),
                          (x + w - 40, y + h), (x + 40, y + h), (x, y + h // 2)),
                         fill="#dbeafe", outline="#334155")
        else:
            draw.rectangle((x, y, x + w, y + h), fill="#eff6ff", outline="#334155", width=3)
        center_text(label, x, y, w, h)
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
    for number, model in ((1, ALGO_1), (2, ALGO_2)):
        if args.source:
            drawio(root / f"algo_{number}.drawio", model)
        if args.png:
            render_png(root / f"algo_{number}.png", model)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
