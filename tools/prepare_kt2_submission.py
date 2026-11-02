"""Build the exact KT2 ZIP from committed and published repository files.

Normal mode requires three real KT2 commit days after the KT1 baseline.
On an earlier day, --preview creates a clearly named review archive only.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report/Отчет_ИКБО-10-24_ПавловаАА_КТ2.docx"
BASELINE = "fe6a041"  # last KT1 report fix, before the first KT2 commit
CONTENTS = {
    "report.docx": REPORT,
    **{f"models/{name}": ROOT / "models" / name for name in (
        "bpmn.bpmn", "bpmn.png", "er_logical.drawio", "er_logical.png",
        "algo_1.drawio", "algo_1.png", "algo_2.drawio", "algo_2.png",
    )},
    **{f"src/{name}": ROOT / "src" / name for name in (
        "README.md", "main.py", "sample_data.json", "self_check.py",
    )},
}


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *arguments], capture_output=True,
        encoding="utf-8", errors="replace", check=True,
    )
    return result.stdout.strip()


def public_url(remote: str) -> str:
    if remote.startswith("git@github.com:"):
        return "https://github.com/" + remote.split(":", 1)[1].removesuffix(".git")
    parsed = urlsplit(remote)
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        raise ValueError("origin must be a GitHub HTTPS or SSH URL")
    return f"https://github.com{parsed.path.removesuffix('.git')}"


def review_history() -> tuple[int, int, int]:
    git("merge-base", "--is-ancestor", BASELINE, "HEAD")
    records = git("log", f"{BASELINE}..HEAD", "--format=%H%x09%aI%x09%cI").splitlines()
    moscow = timezone(timedelta(hours=3))
    author_days = set()
    committer_days = set()
    for row in records:
        _, author, committer = row.split("\t")
        author_days.add(datetime.fromisoformat(author).astimezone(moscow).date())
        committer_days.add(datetime.fromisoformat(committer).astimezone(moscow).date())
    return len(records), len(author_days), len(committer_days)


def build(preview: bool) -> Path:
    if git("branch", "--show-current") != "main":
        raise RuntimeError("Build from main")
    if git("status", "--porcelain"):
        raise RuntimeError("Commit all repository changes before packaging")
    if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
        raise RuntimeError("Publish main before packaging; HEAD and origin/main differ")
    url = public_url(git("config", "--get", "remote.origin.url"))
    for member, path in CONTENTS.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        if not git("ls-files", "--", path.relative_to(ROOT).as_posix()):
            raise RuntimeError(f"Not tracked in Git: {member}")

    count, author_days, committer_days = review_history()
    complete = count >= 3 and author_days >= 3 and committer_days >= 3
    if not complete and not preview:
        raise RuntimeError(
            f"KT2 history has {count} commits on {author_days} author days and "
            f"{committer_days} committer days; three different actual days are required. "
            "Use --preview only for an early review archive."
        )
    log = git("log", "--all", "--date=iso", "--pretty=format:%h %ad %an %s") + "\n"
    files = {
        **CONTENTS,
        "vcs/git_log.txt": log.encode("utf-8"),
        "vcs/repo_url.txt": (url + "\n").encode("utf-8"),
    }
    directory = ROOT / "submission" / ("preview" if preview else "")
    directory.mkdir(parents=True, exist_ok=True)
    filename = "ИКБО-10-24_ПавловаАА_КТ2" + ("_PREVIEW" if preview else "") + ".zip"
    archive = directory / filename
    with ZipFile(archive, "w", ZIP_DEFLATED) as package:
        for member, content in files.items():
            if isinstance(content, Path):
                package.write(content, member)
            else:
                info = ZipInfo(member, date_time=datetime.now().timetuple()[:6])
                info.compress_type = ZIP_DEFLATED
                package.writestr(info, content)
    with ZipFile(archive) as package:
        assert package.testzip() is None
        assert set(package.namelist()) == set(files)
        assert package.read("report.docx") == REPORT.read_bytes()
    print(f"KT2 history: {count} commits, {author_days} author days, {committer_days} committer days")
    print(f"Archive: {archive}")
    if preview:
        print("PREVIEW ONLY: final ZIP requires three actual KT2 commit days and a final published HEAD.")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    options = parser.parse_args()
    build(options.preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
