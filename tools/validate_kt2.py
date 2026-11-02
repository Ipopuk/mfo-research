"""Check model files, report references and procedural code against KT2."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import kt2_algorithms  # noqa: E402
import kt2_bpmn  # noqa: E402
import kt2_er  # noqa: E402

REPORT = ROOT / "report/Отчет_ИКБО-10-24_ПавловаАА_КТ2.docx"
OPERATIONS = {
    "Проверить комплектность заявки": "check_request",
    "Рассчитать предварительную платёжную нагрузку": "calculate_payment_load",
    "Зафиксировать решение по заявке": "record_decision",
    "Зафиксировать уведомление заявителя": "record_notification",
}
MODELS = [
    "bpmn.bpmn", "bpmn.png", "er_logical.drawio", "er_logical.png",
    "algo_1.drawio", "algo_1.png", "algo_2.drawio", "algo_2.png",
]


def same_bytes(path: Path, expected: Path) -> None:
    digest = lambda item: hashlib.sha256(item.read_bytes()).digest()
    assert digest(path) == digest(expected), f"Generated file differs from source: {path.name}"


def generated_files() -> None:
    with TemporaryDirectory() as folder:
        target = Path(folder)
        kt2_bpmn.build_source(target / "bpmn.bpmn")
        kt2_bpmn.build_png(target / "bpmn.png")
        kt2_er.build_source(target / "er_logical.drawio")
        kt2_er.build_png(target / "er_logical.png")
        for number, model in ((1, kt2_algorithms.ALGO_1), (2, kt2_algorithms.ALGO_2)):
            kt2_algorithms.drawio(target / f"algo_{number}.drawio", model)
            kt2_algorithms.render_png(target / f"algo_{number}.png", model)
        for name in MODELS:
            same_bytes(ROOT / "models" / name, target / name)


def model_structure() -> None:
    bpmn = ET.parse(ROOT / "models/bpmn.bpmn").getroot()
    namespace = "{http://www.omg.org/spec/BPMN/20100524/MODEL}"
    tasks = [node.attrib["name"] for node in bpmn.iter(f"{namespace}task")]
    assert len(tasks) == 15, f"Expected 15 BPMN tasks, found {len(tasks)}"
    assert set(OPERATIONS).issubset(tasks)
    assert "Закрыть заявку с основанием" in tasks
    assert any(node.get("name") == "Отзыв или срок истёк?" for node in bpmn.iter(f"{namespace}exclusiveGateway"))
    assert len(list(bpmn.iter(f"{namespace}startEvent"))) == 1
    assert len(list(bpmn.iter(f"{namespace}endEvent"))) >= 2
    assert len(list(bpmn.iter(f"{namespace}dataObjectReference"))) >= 8
    assert len(list(bpmn.iter(f"{namespace}participant"))) >= 4
    assert len(list(bpmn.iter(f"{namespace}lane"))) >= 2

    entity_names = set()
    for name in ("er_logical.drawio", "algo_1.drawio", "algo_2.drawio"):
        graph = ET.parse(ROOT / "models" / name).getroot()
        cells = list(graph.iter("mxCell"))
        ids = {cell.get("id") for cell in cells}
        for cell in cells:
            if cell.get("edge") == "1":
                assert cell.get("source") in ids and cell.get("target") in ids, (name, cell.get("id"))
            if name == "er_logical.drawio" and cell.get("vertex") == "1":
                entity_names.add(cell.get("value", "").split("\n")[0])
        if name.startswith("algo_"):
            assert any("Начало" in cell.get("value", "") for cell in cells)
            assert any("Конец" in cell.get("value", "") for cell in cells)
    assert len(entity_names) == 10
    assert "ДокументЗаявки" in entity_names

    for name in MODELS:
        if name.endswith(".png"):
            with Image.open(ROOT / "models" / name) as image:
                assert image.width >= 1000 and image.height >= 800, name
                assert ImageChops.difference(image.convert("RGB"), Image.new("RGB", image.size, "white")).getbbox(), name


def report_and_code() -> None:
    source = (ROOT / "src/main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    function_names = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert set(OPERATIONS.values()).issubset(function_names)

    text = (ROOT / "docs/kt2/report_section.md").read_text(encoding="utf-8")
    for task, function in OPERATIONS.items():
        assert f"| {task} |" in text and f"{function}()" in text
    with ZipFile(REPORT) as word:
        document = ET.fromstring(word.read("word/document.xml"))
        visible = "".join(node.text or "" for node in document.iter() if node.tag.endswith("}t"))
        for phrase in (
            "2 АНАЛИТИЧЕСКИЙ РАЗДЕЛ", "2.1 Модель процесса", "2.2 Логическая модель",
            "2.3 Алгоритмы", "2.4 Процедурный прототип", "Рисунок 2.1",
            "Рисунок 2.2", "Рисунок 2.3", "Рисунок 2.4", "Таблица 2.1",
            "Таблица 2.2", "Фрагмент 2.1", "Фрагмент 2.2", "Introduction to Algorithms",
            "retry_notification",
        ):
            assert phrase in visible, phrase
        for task, function in OPERATIONS.items():
            assert task in visible and f"{function}()" in visible
    subprocess.run([sys.executable, str(ROOT / "src/self_check.py")], check=True)


def main() -> int:
    generated_files()
    model_structure()
    report_and_code()
    print("KT2 validation: eight models reproduce exactly; BPMN, ER, flowcharts, report and code agree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
