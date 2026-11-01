"""Small checks for the two KT2 algorithms and decision recording."""

from __future__ import annotations

import json
from pathlib import Path

from main import calculate_payment_load, check_request, record_decision, run_case


def main() -> int:
    data = json.loads(Path(__file__).with_name("sample_data.json").read_text(encoding="utf-8"))
    result = run_case(data)
    assert result["completeness"]["complete"]
    assert result["payment_load"]["payment_share_percent"] == 37.5
    assert result["decision"]["outcome"] == "approved"

    missing = check_request(
        data["application"], data["applicant"],
        {row["document_id"]: row for row in data["documents"]},
        data["application_documents"][:1],
        data["required_fields"], data["required_document_kinds"],
    )
    assert missing["missing_documents"] == ["income_statement"]
    no_income = calculate_payment_load("person-1", [], data["obligations"], 18000)
    assert no_income["status"] == "insufficient_income_data"
    try:
        record_decision(data["application"], "decision-2", "employee-1", "refused", "")
    except ValueError:
        pass
    else:
        raise AssertionError("Refusal without reason must be rejected")
    print("KT2 procedural checks: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
