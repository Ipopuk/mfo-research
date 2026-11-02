"""Build the editable BPMN 2.0 source and a matching review PNG.

The diagram is a teaching model of the process described in docs/business_process.md.
Run with --source first; --png creates the raster from the same node/flow data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


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
    for i, (code, _, _) in enumerate(DATA):
        x = (620, 650, 720, 950, 1130, 2120, 2620, 2600)[i]
        y = 125 if i < 6 else 360
        shape(f"DataRef_{code}", (x, y, 42, 50))

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
    for i, (code, _, task) in enumerate(DATA):
        x = (620, 650, 720, 950, 1130, 2120, 2620, 2600)[i]
        y = 125 if i < 6 else 360
        tx, ty, tw, th = positions[task]
        edge(f"Association_{code}", (x + 21, y + 25), (tx + tw // 2, ty + th // 2))
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
    """Render the same BPMN nodes and flows as a labeled review image."""
    def escape(label: str) -> str:
        return label.replace("\\", "\\\\").replace('"', '\\"')

    lines = [
        "digraph KT2 {",
        'graph [rankdir=LR, bgcolor="white", pad="0.3", nodesep="0.6", ranksep="0.85", fontsize=20, fontname="Arial", label="КТ2 — рассмотрение заявки на микрозаём"];',
        'node [fontname="Arial", fontsize=12, color="#334155", style="filled", fillcolor="white"];',
        'edge [fontname="Arial", fontsize=10, color="#475569", arrowsize=0.7];',
        'subgraph cluster_mkk { label="Микрокредитная компания"; color="#1d4ed8"; penwidth=2;',
        'subgraph cluster_specialist { label="Кредитный специалист"; color="#93c5fd";',
    ]
    for node_id, kind, label, owner, _, _ in NODES:
        if owner != "specialist":
            continue
        shape = "ellipse" if kind in {"startEvent", "endEvent"} else "diamond" if kind == "exclusiveGateway" else "box"
        fill = "#dcfce7" if node_id in {"check", "payment", "record_notice"} else "white"
        lines.append(f'Node_{node_id} [label="{escape(label)}", shape={shape}, fillcolor="{fill}"];')
    lines += ['}', 'subgraph cluster_authorized { label="Уполномоченный сотрудник"; color="#93c5fd";']
    for node_id, kind, label, owner, _, _ in NODES:
        if owner == "authorized":
            lines.append(f'Node_{node_id} [label="{escape(label)}", shape=box, fillcolor="#dcfce7"];')
    lines += ['}', '}']
    for code, label in (("Applicant", "Заявитель"), ("BKI", "БКИ"), ("Service", "Сервис уведомлений")):
        lines.append(f'Participant_{code} [label="{label}", shape=box, style="rounded,dashed", color="#64748b"];')
    for source, target, label in FLOWS:
        attr = f' [label="{escape(label)}"]' if label else ""
        lines.append(f"Node_{source} -> Node_{target}{attr};")
    for source, target, label in MESSAGES:
        s = f"Participant_{source}" if source in {"Applicant", "BKI", "Service"} else f"Node_{source}"
        t = f"Participant_{target}" if target in {"Applicant", "BKI", "Service"} else f"Node_{target}"
        lines.append(f'{s} -> {t} [style=dashed, color="#64748b", label="{escape(label)}", constraint=false];')
    for code, label, task in DATA:
        lines.append(f'DataRef_{code} [label="{escape(label)}", shape=note, fillcolor="#fef9c3"];')
        lines.append(f'DataRef_{code} -> Node_{task} [style=dotted, arrowhead=none, constraint=false];')
    lines.append("}")
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["dot", "-Tpng", "-o", str(path)], input="\n".join(lines), text=True, encoding="utf-8", check=True)


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
