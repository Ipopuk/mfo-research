"""Build the required submission using the actual repository and its pushed history."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        encoding="utf-8", errors="replace",
    )
    return process.stdout.strip()


def public_url(remote: str) -> str:
    if remote.startswith("git@github.com:"):
        return "https://github.com/" + remote.split(":", 1)[1].removesuffix(".git")
    split = urlsplit(remote)
    if split.scheme not in {"https", "http"} or not split.hostname:
        raise ValueError("Используйте HTTPS-адрес origin либо SSH-адрес git@github.com:...")
    # Credentials must never be exported with the URL.
    authority = split.hostname + (f":{split.port}" if split.port else "")
    return f"{split.scheme}://{authority}{split.path.removesuffix('.git')}"


def docx_text(path: Path) -> str:
    with ZipFile(path) as document:
        root = ET.fromstring(document.read("word/document.xml"))
    return "".join(root.itertext())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True)
    parser.add_argument("--short-name", required=True, help="Фамилия и инициалы без пробелов")
    parser.add_argument("--report", type=Path, help="Отчёт DOCX; по умолчанию единственный DOCX из report/")
    parser.add_argument("--allow-incomplete-history", action="store_true")
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not re.fullmatch(r"[А-Яа-яЁёA-Za-z0-9-]+", options.group):
        parser.error("В группе допускаются буквы, цифры и дефис.")
    if not re.fullmatch(r"[А-Яа-яЁёA-Za-z-]+", options.short_name):
        parser.error("Укажите фамилию и инициалы без пробелов и точек.")
    for name in ["README.md", ".gitignore", "translation/original.pdf"]:
        if not (root / name).is_file():
            parser.error(f"Не найден обязательный файл {name}")
    if "{{" in (root / "README.md").read_text(encoding="utf-8"):
        parser.error("Сначала заполните ФИО и группу в README.md.")
    candidates = list((root / "report").glob("*.docx"))
    if options.report:
        report = options.report.resolve()
    elif len(candidates) == 1:
        report = candidates[0]
    else:
        parser.error("В report/ должен быть один DOCX, либо укажите --report.")
    if not report.is_file():
        parser.error("Файл отчёта не найден.")
    if "{{" in docx_text(report):
        parser.error("В титульном листе остались поля {{...}}. Заполните их в Word.")
    try:
        git(root, "rev-parse", "--show-toplevel")
        remote = git(root, "config", "--get", "remote.origin.url")
        url = public_url(remote)
        local_head = git(root, "rev-parse", "HEAD")
        git(root, "fetch", "origin")
        remote_head = git(root, "rev-parse", "origin/main")
        if local_head != remote_head:
            parser.error("Локальная main и origin/main различаются. Проверьте ветку и выполните push.")
        # Required command, unchanged in meaning, with Python handling UTF-8 output.
        log = git(root, "log", "--all", "--date=iso", "--pretty=format:%h %ad %an %s") + "\n"
        records = git(root, "log", "HEAD", "--format=%h%x09%aI%x09%cI").splitlines()
        author_days = {row.split("\t")[1][:10] for row in records}
        committer_days = {row.split("\t")[2][:10] for row in records}
        # Ensures the submitted report and research materials are committed, not merely on disk.
        for item in [report, root / "README.md", root / ".gitignore", root / "translation/original.pdf"]:
            relative = item.relative_to(root).as_posix()
            if not git(root, "ls-files", "--", relative):
                parser.error(f"Файл не добавлен в Git: {relative}")
            if git(root, "status", "--porcelain", "--", relative):
                parser.error(f"Есть незакоммиченные изменения: {relative}")
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        parser.error(f"Невозможно получить подтверждённые данные репозитория: {exc}")
    incomplete = len(records) < 3 or len(author_days) < 3 or len(committer_days) < 3
    if incomplete:
        print(
            f"История: {len(records)} коммитов; {len(author_days)} дней автора; "
            f"{len(committer_days)} дней создания коммитов."
        )
        print("Требование о трёх коммитах в разные дни не подтверждено. Метаданные не доказывают реальную дату работы.")
        if not options.allow_incomplete_history:
            print("При осознанной сдаче неполной истории добавьте --allow-incomplete-history.")
            return 2
    destination = root / "submission"
    destination.mkdir(exist_ok=True)
    vcs = destination / "vcs"
    vcs.mkdir(exist_ok=True)
    (vcs / "git_log.txt").write_text(log, encoding="utf-8")
    (vcs / "repo_url.txt").write_text(url + "\n", encoding="utf-8")
    name = f"{options.group}_{options.short_name}_КТ1"
    archive = destination / (name + ".zip")
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        package.write(report, f"Отчет_{name}.docx")
        package.write(root / "translation/original.pdf", "translation/original.pdf")
        package.write(vcs / "git_log.txt", "vcs/git_log.txt")
        package.write(vcs / "repo_url.txt", "vcs/repo_url.txt")
    print(f"Архив: {archive}")
    print("Архив имеет ровно требуемую структуру: отчёт, оригинал, два файла vcs.")
    if incomplete:
        print("ВНИМАНИЕ: состав архива корректен, но история остаётся несоответствующей требованию КТ1.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
