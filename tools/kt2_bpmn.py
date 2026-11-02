"""Build the editable BPMN 2.0 source and a matching review PNG.

The diagram is a teaching model of the process described in docs/business_process.md.
Run with --source first; --png creates the raster from the same node/flow data.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


MODEL = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"
ET.register_namespace("bpmn", MODEL)
ET.register_namespace("bpmndi", BPMNDI)
ET.register_namespace("dc", DC)
ET.register_namespace("di", DI)


def q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


# ID, BPMN element, label, responsible lane, x, y.
NODES = [
    ("start", "startEvent", "Поступило обращение", "specialist", 340, 220),
    ("register", "task", "Зарегистрировать заявку", "specialist", 440, 210),
    ("check", "task", "Проверить комплектность заявки", "specialist", 620, 210),
    ("complete", "exclusiveGateway", "Данные полны?", "specialist", 800, 210),
    ("request_info", "task", "Запросить недостающие сведения", "specialist", 670, 340),
    ("withdrawn", "exclusiveGateway", "Заявка отозвана?", "specialist", 850, 345),
    ("close", "task", "Закрыть отозванную заявку", "specialist", 970, 340),
    ("end_withdrawn", "endEvent", "Заявка закрыта", "specialist", 1150, 350),
    ("identity", "task", "Проверить личность и согласия", "specialist", 950, 210),
    ("restrictions", "task", "Проверить ограничения", "specialist", 1130, 210),
    ("restricted", "exclusiveGateway", "Есть запрет?", "specialist", 1310, 210),
    ("refusal", "task", "Подготовить основание отказа", "specialist", 1290, 340),
    ("consent", "exclusiveGateway", "Есть основание для БКИ?", "specialist", 1460, 210),
    ("bki", "task", "Получить сведения БКИ", "specialist", 1600, 210),
    ("bki_answer", "exclusiveGateway", "Ответ получен?", "specialist", 1780, 210),
    ("wait_bki", "task", "Ожидать повторной проверки", "specialist", 1740, 340),
    ("payment", "task", "Рассчитать предварительную платёжную нагрузку", "specialist", 1930, 210),
    ("proposal", "task", "Подготовить предложение", "specialist", 2120, 210),
    ("merge", "exclusiveGateway", "Предложение готово", "specialist", 2300, 210),
    ("decide", "task", "Принять решение", "authorized", 2420, 520),
    ("record", "task", "Зафиксировать решение по заявке", "authorized", 2620, 520),
    ("notify", "task", "Направить уведомление", "specialist", 2790, 210),
    ("record_notice", "task", "Зафиксировать уведомление заявителя", "specialist", 2600, 340),
    ("delivered", "exclusiveGateway", "Уведомление доставлено?", "specialist", 2420, 345),
    ("end_notified", "endEvent", "Решение сообщено", "specialist", 2260, 350),
]

# Source, target, branch label. Unnamed flows use an empty label.
FLOWS = [
    ("start", "register", ""), ("register", "check", ""),
    ("check", "complete", ""),
    ("complete", "identity", "Да"), ("complete", "request_info", "Нет"),
    ("request_info", "withdrawn", ""),
    ("withdrawn", "close", "Да"), ("withdrawn", "check", "Нет: сведения получены"),
    ("close", "end_withdrawn", ""),
    ("identity", "restrictions", ""), ("restrictions", "restricted", ""),
    ("restricted", "refusal", "Да"), ("restricted", "consent", "Нет"),
    ("refusal", "merge", ""),
    ("consent", "bki", "Да"), ("consent", "payment", "Нет"),
    ("bki", "bki_answer", ""),
    ("bki_answer", "payment", "Да"), ("bki_answer", "wait_bki", "Нет"),
    ("wait_bki", "bki", ""),
    ("payment", "proposal", ""), ("proposal", "merge", ""),
    ("merge", "decide", ""), ("decide", "record", ""),
    ("record", "notify", ""), ("notify", "record_notice", ""),
    ("record_notice", "delivered", ""),
    ("delivered", "end_notified", "Да"), ("delivered", "notify", "Нет"),
]

# A data object is attached to a task and later appears in the logical model.
DATA = [
    ("form", "Анкета заявителя", "register"),
    ("application", "Заявка", "check"),
    ("document", "Документ", "check"),
    ("consent_data", "Согласие", "identity"),
    ("check_result", "Результат проверки", "restrictions"),
    ("proposal_data", "Предложение", "proposal"),
    ("decision_data", "Решение", "record"),
    ("notification_data", "Уведомление", "record_notice"),
]

MESSAGES = [
    ("Applicant", "register", "Обращение"),
    ("request_info", "Applicant", "Запрос уточнения"),
    ("Applicant", "check", "Дополнительные сведения"),
    ("bki", "BKI", "Запрос"),
    ("BKI", "bki_answer", "Ответ"),
    ("notify", "Service", "Сообщение"),
    ("Service", "record_notice", "Статус доставки"),
    ("notify", "Applicant", "Решение"),
]


def node_size(kind: str) -> tuple[int, int]:
    if kind in {"startEvent", "endEvent"}:
        return (40, 40)
    if kind == "exclusiveGateway":
        return (55, 55)
    return (158, 64)


def build_source(path: Path) -> None:
    definitions = ET.Element(q(MODEL, "definitions"), {
        "id": "Definitions_KT2", "targetNamespace": "https://github.com/Ipopuk/mfo-research/kt2",
        "exporter": "mfo-research", "exporterVersion": "1.0",
    })
    collaboration = ET.SubElement(definitions, q(MODEL, "collaboration"), {"id": "Collaboration_KT2"})
    participants = [
        ("MKK", "Микрокредитная компания", "Process_MKK"),
        ("Applicant", "Заявитель", None),
        ("BKI", "Бюро кредитных историй", None),
        ("Service", "Сервис уведомлений", None),
    ]
    for code, label, process_ref in participants:
        attrs = {"id": f"Participant_{code}", "name": label}
        if process_ref:
            attrs["processRef"] = process_ref
        ET.SubElement(collaboration, q(MODEL, "participant"), attrs)
    for i, (source, target, label) in enumerate(MESSAGES, 1):
        ET.SubElement(collaboration, q(MODEL, "messageFlow"), {
            "id": f"MessageFlow_{i}", "name": label,
            "sourceRef": f"Participant_{source}" if source in {"Applicant", "BKI", "Service"} else f"Node_{source}",
            "targetRef": f"Participant_{target}" if target in {"Applicant", "BKI", "Service"} else f"Node_{target}",
        })

    process = ET.SubElement(definitions, q(MODEL, "process"), {"id": "Process_MKK", "isExecutable": "false"})
    lane_set = ET.SubElement(process, q(MODEL, "laneSet"), {"id": "LaneSet_MKK"})
    for code, label in (("specialist", "Кредитный специалист"), ("authorized", "Уполномоченный сотрудник")):
        lane = ET.SubElement(lane_set, q(MODEL, "lane"), {"id": f"Lane_{code}", "name": label})
        for node_id, _, _, owner, _, _ in NODES:
            if owner == code:
                ET.SubElement(lane, q(MODEL, "flowNodeRef")).text = f"Node_{node_id}"

    for node_id, kind, label, _, _, _ in NODES:
        element = ET.SubElement(process, q(MODEL, kind), {"id": f"Node_{node_id}", "name": label})
        for i, (_, target, _) in enumerate(FLOWS, 1):
            if target == node_id:
                ET.SubElement(element, q(MODEL, "incoming")).text = f"Flow_{i}"
        for i, (source, _, _) in enumerate(FLOWS, 1):
            if source == node_id:
                ET.SubElement(element, q(MODEL, "outgoing")).text = f"Flow_{i}"
    for i, (source, target, label) in enumerate(FLOWS, 1):
        attrs = {"id": f"Flow_{i}", "sourceRef": f"Node_{source}", "targetRef": f"Node_{target}"}
        if label:
            attrs["name"] = label
        ET.SubElement(process, q(MODEL, "sequenceFlow"), attrs)
    for code, label, task in DATA:
        ET.SubElement(process, q(MODEL, "dataObject"), {"id": f"Data_{code}"})
        ET.SubElement(process, q(MODEL, "dataObjectReference"), {
            "id": f"DataRef_{code}", "dataObjectRef": f"Data_{code}", "name": label,
        })
        ET.SubElement(process, q(MODEL, "association"), {
            "id": f"Association_{code}", "sourceRef": f"DataRef_{code}", "targetRef": f"Node_{task}",
        })

    diagram = ET.SubElement(definitions, q(BPMNDI, "BPMNDiagram"), {"id": "Diagram_KT2"})
    plane = ET.SubElement(diagram, q(BPMNDI, "BPMNPlane"), {
        "id": "Plane_KT2", "bpmnElement": "Collaboration_KT2",
    })
    bounds = {
        "MKK": (250, 110, 2740, 570),
        "Applicant": (250, 10, 2740, 80),
        "BKI": (250, 710, 2740, 75),
        "Service": (250, 815, 2740, 75),
        "specialist": (250, 110, 2740, 335),
        "authorized": (250, 445, 2740, 235),
    }

    def shape(element_id: str, box: tuple[int, int, int, int], horizontal: bool = False) -> None:
        attrs = {"id": f"Shape_{element_id}", "bpmnElement": element_id}
        if horizontal:
            attrs["isHorizontal"] = "true"
        node = ET.SubElement(plane, q(BPMNDI, "BPMNShape"), attrs)
        ET.SubElement(node, q(DC, "Bounds"), dict(zip(("x", "y", "width", "height"), map(str, box))))

    for code, _, _ in participants:
        shape(f"Participant_{code}", bounds[code], True)
    for code in ("specialist", "authorized"):
        shape(f"Lane_{code}", bounds[code], True)
    positions = {}
    for node_id, kind, _, _, x, y in NODES:
        width, height = node_size(kind)
        positions[node_id] = (x, y, width, height)
        shape(f"Node_{node_id}", positions[node_id])
    data_positions = [(600, 125), (730, 125), (860, 125), (1000, 125),
                      (1170, 125), (2110, 125), (2600, 610), (2800, 345)]
    for (code, _, _), (x, y) in zip(DATA, data_positions):
        shape(f"DataRef_{code}", (x, y, 100, 50))

    def edge(element_id: str, source: tuple[int, int], target: tuple[int, int]) -> None:
        node = ET.SubElement(plane, q(BPMNDI, "BPMNEdge"), {
            "id": f"Edge_{element_id}", "bpmnElement": element_id,
        })
        for x, y in (source, target):
            ET.SubElement(node, q(DI, "waypoint"), {"x": str(x), "y": str(y)})

    for i, (source, target, _) in enumerate(FLOWS, 1):
        sx, sy, sw, sh = positions[source]
        tx, ty, tw, th = positions[target]
        edge(f"Flow_{i}", (sx + sw // 2, sy + sh // 2), (tx + tw // 2, ty + th // 2))
    for (code, _, task), (x, y) in zip(DATA, data_positions):
        tx, ty, tw, th = positions[task]
        edge(f"Association_{code}", (x + 50, y + 25), (tx + tw // 2, ty + th // 2))
    external_y = {"Applicant": 50, "BKI": 747, "Service": 852}
    for i, (source, target, _) in enumerate(MESSAGES, 1):
        if source in external_y:
            tx, ty, tw, th = positions[target]
            edge(f"MessageFlow_{i}", (tx + tw // 2, external_y[source]), (tx + tw // 2, ty + th // 2))
        else:
            sx, sy, sw, sh = positions[source]
            edge(f"MessageFlow_{i}", (sx + sw // 2, sy + sh // 2), (sx + sw // 2, external_y[target]))

    ET.indent(definitions, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(definitions).write(path, encoding="utf-8", xml_declaration=True)


def build_png(path: Path) -> None:
    """Render the exact source nodes/flows on the fixed BPMN DI canvas."""
    image = Image.new("RGB", (3040, 915), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 16)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
    title = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 18)
    palette = {"line": "#334155", "pool": "#1d4ed8", "lane": "#93c5fd",
               "data": "#fef3c7", "highlight": "#dcfce7", "message": "#64748b"}
    boxes = {code: (x, y, *node_size(kind)) for code, kind, _, _, x, y in NODES}

    def text_center(value: str, rect: tuple[int, int, int, int], face=font, fill="#0f172a") -> None:
        x, y, w, h = rect
        words = value.split()
        rows = []
        current = ""
        for word in words:
            candidate = (current + " " + word).strip()
            if current and draw.textbbox((0, 0), candidate, font=face)[2] > w - 12:
                rows.append(current)
                current = word
            else:
                current = candidate
        if current:
            rows.append(current)
        height = len(rows) * 19
        for index, row in enumerate(rows):
            width = draw.textbbox((0, 0), row, font=face)[2]
            draw.text((x + (w - width) / 2, y + (h - height) / 2 + index * 19),
                      row, font=face, fill=fill)

    def segment(a: tuple[int, int], b: tuple[int, int], color: str, dashed=False) -> None:
        if not dashed:
            draw.line((a, b), fill=color, width=2)
            return
        length = math.dist(a, b)
        if not length:
            return
        count = max(1, int(length / 12))
        for i in range(count):
            if i % 2 == 0:
                p = (a[0] + (b[0] - a[0]) * i / count, a[1] + (b[1] - a[1]) * i / count)
                q = (a[0] + (b[0] - a[0]) * (i + 1) / count,
                     a[1] + (b[1] - a[1]) * (i + 1) / count)
                draw.line((p, q), fill=color, width=2)

    def arrow(points: list[tuple[int, int]], color="#334155", dashed=False) -> None:
        for a, b in zip(points, points[1:]):
            segment(a, b, color, dashed)
        a, b = points[-2:]
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        left = (b[0] - 10 * math.cos(angle - .45), b[1] - 10 * math.sin(angle - .45))
        right = (b[0] - 10 * math.cos(angle + .45), b[1] - 10 * math.sin(angle + .45))
        draw.polygon((b, left, right), fill=color)

    draw.text((260, 0), "КТ2. Рассмотрение заявки на потребительский микрозаём", font=title, fill="#0f172a")
    for x1, y1, x2, y2, label in (
        (250, 30, 2990, 100, "Заявитель"),
        (250, 110, 2990, 680, "Микрокредитная компания"),
        (250, 710, 2990, 785, "Бюро кредитных историй"),
        (250, 815, 2990, 890, "Сервис уведомлений"),
    ):
        draw.rectangle((x1, y1, x2, y2), outline=palette["pool"], width=2)
        draw.text((x1 + 8, y1 + 6), label, font=title, fill=palette["pool"])
    draw.rectangle((250, 110, 2990, 445), outline=palette["lane"], width=2)
    draw.rectangle((250, 445, 2990, 680), outline=palette["lane"], width=2)
    draw.text((260, 420), "Кредитный специалист", font=small, fill=palette["pool"])
    draw.text((260, 655), "Уполномоченный сотрудник", font=small, fill=palette["pool"])

    bypass = {("consent", "payment"): 190, ("refusal", "merge"): 425,
              ("withdrawn", "check"): 428, ("wait_bki", "bki"): 425,
              ("delivered", "notify"): 430}
    for source, target, label in FLOWS:
        sx, sy, sw, sh = boxes[source]
        tx, ty, tw, th = boxes[target]
        a = (sx + sw // 2, sy + sh // 2)
        b = (tx + tw // 2, ty + th // 2)
        if (source, target) in bypass:
            via = bypass[(source, target)]
            a = (a[0], sy + sh if via > a[1] else sy)
            b = (b[0], ty + th if via > b[1] else ty)
            points = [a, (a[0], via), (b[0], via), b]
        elif tx > sx and abs(b[1] - a[1]) < 75:
            points = [(sx + sw, a[1]), (tx, b[1])]
        elif target == "record_notice":
            points = [(sx + sw // 2, sy + sh), (sx + sw // 2, 410),
                      (tx + tw // 2, 410), (tx + tw // 2, ty + sh)]
        elif target == "notify":
            points = [(sx + sw // 2, sy), (sx + sw // 2, 470),
                      (tx + tw // 2, 470), (tx + tw // 2, ty + th)]
        else:
            points = [a, (b[0], a[1]), b]
        arrow(points)
        if label:
            middle = points[len(points) // 2]
            width = draw.textbbox((0, 0), label, font=small)[2]
            draw.rectangle((middle[0] - width / 2 - 3, middle[1] - 17,
                            middle[0] + width / 2 + 3, middle[1] + 1), fill="white")
            draw.text((middle[0] - width / 2, middle[1] - 17), label, font=small,
                      fill=palette["line"])

    for source, target, label in MESSAGES:
        if source in {"Applicant", "BKI", "Service"}:
            x, y, w, h = boxes[target]
            a = (x + w // 2, {"Applicant": 100, "BKI": 710, "Service": 815}[source])
            b = (x + w // 2, y + h // 2)
        else:
            x, y, w, h = boxes[source]
            a = (x + w // 2, y + h // 2)
            b = (x + w // 2, {"Applicant": 100, "BKI": 710, "Service": 815}[target])
        arrow([a, b], palette["message"], True)
        draw.text((a[0] + 4, (a[1] + b[1]) / 2), label, font=small, fill=palette["message"])

    data_positions = [(600, 125), (730, 125), (860, 125), (1000, 125),
                      (1170, 125), (2110, 125), (2600, 610), (2800, 345)]
    for (code, label, task), (x, y) in zip(DATA, data_positions):
        tx, ty, tw, th = boxes[task]
        segment((x + 50, y + 45), (tx + tw // 2, ty + th // 2), "#a16207", True)
        draw.polygon(((x, y), (x + 90, y), (x + 100, y + 10),
                      (x + 100, y + 50), (x, y + 50)),
                     fill=palette["data"], outline="#a16207")
        text_center(label, (x + 3, y + 3, 94, 44), small)

    for code, kind, label, _, x, y in NODES:
        w, h = node_size(kind)
        fill = palette["highlight"] if code in {"check", "payment", "record", "record_notice"} else "white"
        if kind == "task":
            draw.rounded_rectangle((x, y, x + w, y + h), radius=8,
                                   fill=fill, outline=palette["line"], width=2)
            text_center(label, (x + 2, y + 2, w - 4, h - 4), small)
        elif kind == "exclusiveGateway":
            draw.polygon(((x + w // 2, y), (x + w, y + h // 2),
                          (x + w // 2, y + h), (x, y + h // 2)),
                         fill="white", outline=palette["line"])
            label_y = y + h + 5 if y < 300 else y - 41
            text_center(label, (x - 45, label_y, w + 90, 38), small)
        else:
            draw.ellipse((x, y, x + w, y + h), fill="white",
                         outline=palette["line"], width=3 if kind == "endEvent" else 2)
            text_center(label, (x - 45, y + h + 4, w + 90, 36), small)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true")
    parser.add_argument("--png", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.source and not args.png:
        parser.error("Укажите --source или --png")
    if args.source:
        build_source(root / "models" / "bpmn.bpmn")
    if args.png:
        build_png(root / "models" / "bpmn.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
