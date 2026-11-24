"""Build the KT3 submission ZIP from the current commit and repository history."""
from __future__ import annotations

from pathlib import Path
import subprocess
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from prepare_kt2_submission import ROOT, git, public_url


NAME = "ИКБО-10-24_ПавловаАА_КТ3"
REPORT = f"Отчет_{NAME}.docx"
BASELINE = "25fd7a7"


def committed_file(name: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"HEAD:{name}"])


def main() -> None:
    tracked_java = git("ls-tree", "-r", "--name-only", "HEAD", "--", "src/java").splitlines()
    sources = [path for path in tracked_java if path.endswith(".java")]
    if not sources:
        raise RuntimeError("Нет исходников Java в текущем коммите.")
    paths = {
        REPORT: f"report/{REPORT}",
        "models/classes.puml": "models/classes.puml",
        "models/classes.png": "models/classes.png",
        "review/review.md": "review/review.md",
        **{path: path for path in ["src/java/README.md", "src/java/pom.xml",
                                  "src/java/sample_data.json", *sources]},
    }
    content = {name: committed_file(path) for name, path in paths.items()}
    url = public_url(git("config", "remote.origin.url"))
    log = git("log", "--all", "--date=iso", "--pretty=format:%h %ad %an %s")
    content["vcs/git_log.txt"] = (log + "\n").encode("utf-8")
    content["vcs/repo_url.txt"] = (url + "\n").encode("utf-8")
    directory = ROOT / "submission"
    directory.mkdir(exist_ok=True)
    output = directory / f"{NAME}.zip"
    with NamedTemporaryFile(dir=directory, suffix=".tmp", delete=False) as temporary:
        staged = Path(temporary.name)
    try:
        with ZipFile(staged, "w", ZIP_DEFLATED) as archive:
            for name, data in content.items():
                archive.writestr(name, data)
        with ZipFile(staged) as archive:
            if archive.testzip() is not None or archive.namelist() != list(content):
                raise RuntimeError("Проверка содержимого ZIP не прошла.")
        staged.replace(output)
    finally:
        staged.unlink(missing_ok=True)

    print(f"КТ3: {len(content)} файлов, коммит {git('rev-parse', '--short', 'HEAD')}")
    print(git("log", f"{BASELINE}..HEAD", "--format=%h %aI %cI %s"))
    print(output)


if __name__ == "__main__":
    main()
