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
    ("complete", "exclusiveGateway", "Данные полны?", "specialist", 830, 210),
    ("request_info", "task", "Запросить недостающие сведения", "specialist", 670, 340),
    ("withdrawn", "exclusiveGateway", "Отзыв или срок истёк?", "specialist", 883, 345),
    ("close", "task", "Закрыть заявку с основанием", "specialist", 1000, 340),
    ("end_withdrawn", "endEvent", "Заявка закрыта", "specialist", 1180, 350),
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

DATA_POSITIONS = [(437, 147), (630, 125), (750, 125), (1000, 125),
                  (1170, 125), (2110, 125), (2600, 610), (2800, 345)]
FLOW_ROUTES = {
    ("complete", "request_info"): [(857, 265), (857, 304), (749, 304), (749, 340)],
    ("withdrawn", "check"): [(910, 400), (910, 428), (642, 428), (642, 306), (699, 306), (699, 274)],
    ("notify", "record_notice"): [(2948, 242), (2962, 242), (2962, 414), (2679, 414), (2679, 404)],
    ("record", "notify"): [(2699, 520), (2699, 470), (2976, 470), (2976, 224), (2948, 224)],
    ("delivered", "notify"): [(2447, 400), (2447, 429), (2774, 429), (2774, 242), (2790, 242)],
}
FLOW_LABELS = {
    ("complete", "identity"): (916, 216, 42, 20),
    ("complete", "request_info"): (777, 283, 42, 20),
    ("withdrawn", "close"): (946, 350, 42, 20),
    ("withdrawn", "check"): (690, 406, 200, 20),
    ("delivered", "end_notified"): (2334, 349, 42, 20),
}
MESSAGE_ROUTES = {
    ("Applicant", "register"): [(556, 100), (556, 210)],
    ("request_info", "Applicant"): [(670, 372), (604, 372), (604, 100)],
    ("Applicant", "check"): [(759, 100), (759, 119), (740, 119), (740, 210)],
    ("bki", "BKI"): [(1640, 274), (1640, 710)],
    ("BKI", "bki_answer"): [(1905, 710), (1905, 252), (1820, 252)],
    ("notify", "Service"): [(2930, 274), (2930, 815)],
    ("Service", "record_notice"): [(2615, 815), (2615, 404)],
}
MESSAGE_LABELS = {
    ("Applicant", "register"): (492, 76, 128, 20),
    ("request_info", "Applicant"): (537, 53, 134, 20),
    ("Applicant", "check"): (665, 76, 188, 20),
    ("bki", "BKI"): (1644, 512, 66, 20),
    ("BKI", "bki_answer"): (1908, 510, 64, 20),
    ("notify", "Service"): (2830, 663, 97, 20),
    ("Service", "record_notice"): (2470, 698, 142, 20),
    ("notify", "Applicant"): (2875, 135, 75, 20),
}

def node_size(kind: str) -> tuple[int, int]:
    if kind in {"startEvent", "endEvent"}:
        return (40, 40)
    if kind == "exclusiveGateway":
        return (55, 55)
    return (158, 64)


def flow_points(source, target, boxes):
    route = FLOW_ROUTES.get((source, target))
    if route:
        return route
    sx, sy, sw, sh = boxes[source]
    tx, ty, tw, th = boxes[target]
    a = (sx + sw // 2, sy + sh // 2)
    b = (tx + tw // 2, ty + th // 2)
    bypass = {("consent", "payment"): 190, ("refusal", "merge"): 435,
              ("wait_bki", "bki"): 415}
    via = bypass.get((source, target))
    if via:
        a = (a[0], sy + sh if via > a[1] else sy)
        b = (b[0], ty + th if via > b[1] else ty)
        return [a, (a[0], via), (b[0], via), b]
    if abs(b[1] - a[1]) < 75:
        return [(sx + sw, a[1]), (tx, b[1])] if tx > sx else [(sx, a[1]), (tx + tw, b[1])]
    if sx == tx or source in {"complete", "restricted", "bki_answer"}:
        via = (sy + sh + ty) // 2
        return [(a[0], sy + sh), (a[0], via), (b[0], via), (b[0], ty)]
    via = (sx + sw + tx) // 2
    return [(sx + sw, a[1]), (via, a[1]), (via, b[1]), (tx, b[1])]


def message_points(source, target, boxes):
    route = MESSAGE_ROUTES.get((source, target))
    if route:
        return route
    pool_y = {"Applicant": 100, "BKI": 710, "Service": 815}
    if source in pool_y:
        x, y, w, h = boxes[target]
        pool = (x + w // 2, pool_y[source])
        return [pool, (pool[0], y + h)]
    x, y, w, h = boxes[source]
    pool = (x + w // 2, pool_y[target])
    return [(pool[0], y if target == "Applicant" else y + h), pool]


def flow_label(source, target, points):
    position = FLOW_LABELS.get((source, target))
    if position:
        return position
    a, b = points[:2]
    if abs(a[1] - b[1]) <= abs(a[0] - b[0]):
        return ((a[0] + b[0]) // 2 - 21, min(a[1], b[1]) - 22, 42, 20)
    return (a[0] + 3, (a[1] + b[1]) // 2 - 10, 42, 20)


def gateway_label(code, box):
    x, y, w, h = box
    label_y = y + h + 5 if y < 300 else y - 41
    if code in {"complete", "restricted", "bki_answer", "merge"}:
        label_y = 173 if code == "complete" else 151
    return (x - 45, label_y, w + 90, 38)


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
        "Applicant": (250, 30, 2740, 70),
        "BKI": (250, 710, 2740, 75),
        "Service": (250, 815, 2740, 75),
        "specialist": (250, 110, 2740, 335),
        "authorized": (250, 445, 2740, 235),
    }

    def label_bounds(node, box):
        label = ET.SubElement(node, q(BPMNDI, "BPMNLabel"))
        ET.SubElement(label, q(DC, "Bounds"), dict(zip(("x", "y", "width", "height"), map(str, box))))

    def shape(element_id: str, box: tuple[int, int, int, int], horizontal: bool = False,
              label_box=None) -> None:
        attrs = {"id": f"Shape_{element_id}", "bpmnElement": element_id}
        if horizontal:
            attrs["isHorizontal"] = "true"
        node = ET.SubElement(plane, q(BPMNDI, "BPMNShape"), attrs)
        ET.SubElement(node, q(DC, "Bounds"), dict(zip(("x", "y", "width", "height"), map(str, box))))
        if label_box:
            label_bounds(node, label_box)

    for code, _, _ in participants:
        shape(f"Participant_{code}", bounds[code], True)
    for code in ("specialist", "authorized"):
        shape(f"Lane_{code}", bounds[code], True)
    positions = {}
    for node_id, kind, _, _, x, y in NODES:
        width, height = node_size(kind)
        positions[node_id] = (x, y, width, height)
        label_box = gateway_label(node_id, positions[node_id]) if kind == "exclusiveGateway" else None
        shape(f"Node_{node_id}", positions[node_id], label_box=label_box)
    for (code, _, _), (x, y) in zip(DATA, DATA_POSITIONS):
        shape(f"DataRef_{code}", (x, y, 100, 50))

    def edge(element_id, points, label_box=None):
        node = ET.SubElement(plane, q(BPMNDI, "BPMNEdge"), {
            "id": f"Edge_{element_id}", "bpmnElement": element_id,
        })
        for x, y in points:
            ET.SubElement(node, q(DI, "waypoint"), {"x": str(x), "y": str(y)})
        if label_box:
            label_bounds(node, label_box)

    for i, (source, target, label) in enumerate(FLOWS, 1):
        points = flow_points(source, target, positions)
        edge(f"Flow_{i}", points, flow_label(source, target, points) if label else None)
    for (code, _, task), (x, y) in zip(DATA, DATA_POSITIONS):
        tx, ty, tw, th = positions[task]
        src = (x + 50, y + 50 if y < ty else y)
        dst = (tx + tw // 2, ty if y < ty else ty + th)
        edge(f"Association_{code}", [src, dst])
    for i, (source, target, _) in enumerate(MESSAGES, 1):
        edge(f"MessageFlow_{i}", message_points(source, target, positions), MESSAGE_LABELS.get((source, target)))

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

    labels = []
    for source, target, label in FLOWS:
        points = flow_points(source, target, boxes)
        arrow(points)
        if label:
            labels.append((label, flow_label(source, target, points), palette["line"]))

    for source, target, label in MESSAGES:
        points = message_points(source, target, boxes)
        arrow(points, palette["message"], True)
        label_box = MESSAGE_LABELS.get((source, target))
        if label_box:
            labels.append((label, label_box, palette["message"]))
        else:
            a, b = points
            draw.text((a[0] + 4, (a[1] + b[1]) / 2), label, font=small, fill=palette["message"])

    for (code, label, task), (x, y) in zip(DATA, DATA_POSITIONS):
        tx, ty, tw, th = boxes[task]
        src = (x + 50, y + 50 if y < ty else y)
        dst = (tx + tw // 2, ty if y < ty else ty + th)
        segment(src, dst, "#a16207", True)
        draw.polygon(((x, y), (x + 90, y), (x + 100, y + 10),
                      (x + 100, y + 50), (x, y + 50)),
                     fill=palette["data"], outline="#a16207")
        text_center(label, (x + 3, y + 3, 94, 44), small)

    for label, box, color in labels:
        text_center(label, box, small, color)

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
            text_center(label, gateway_label(code, boxes[code]), small)
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
