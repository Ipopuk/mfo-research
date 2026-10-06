"""Record actual installed tools without claiming an unavailable tool is installed."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def probe(command: list[str]) -> dict:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "command": command, "error": "not found in PATH"}
    try:
        result = subprocess.run(
            [executable, *command[1:]], text=True, capture_output=True,
            timeout=15, encoding="utf-8", errors="replace",
        )
        return {
            "available": result.returncode == 0,
            "command": command,
            "version_output": (result.stdout + result.stderr).strip(),
            "returncode": result.returncode,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "command": command, "error": str(exc)}


def main() -> int:
    checks = {
        "python": {"available": True, "version_output": sys.version.split()[0]},
        "java": probe(["java", "--version"]),
        "javac": probe(["javac", "--version"]),
        "postgresql_client": probe(["psql", "--version"]),
        "vscode": probe(["code", "--version"]),
        "git": probe(["git", "--version"]),
    }
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "tools": checks,
        "note": "psql availability does not verify that a PostgreSQL server is running",
    }
    destination = Path(__file__).resolve().parents[1] / "environment_check.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, check in checks.items():
        output = check.get("version_output", check.get("error", ""))
        print(f"{name}: {output}")
    print(f"\nФактические результаты: {destination}")
    return 0 if all(check["available"] for check in checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
