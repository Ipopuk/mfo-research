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

    undelivered = dict(data)
    undelivered["notification"] = dict(data["notification"], sent=False)
    retry = run_case(undelivered)
    assert retry["notification"]["sent"] is False
    assert retry["next_step"] == "retry_notification"

    missing = check_request(
        data["application"], data["applicant"],
        {row["document_id"]: row for row in data["documents"]},
        data["application_documents"][:1],
        data["required_fields"], data["required_document_kinds"],
    )
    assert missing["missing_documents"] == ["income_statement"]
    blank_name = dict(data, applicant=dict(data["applicant"], full_name=" \t "))
    incomplete = run_case(blank_name)
    assert incomplete["completeness"]["missing_fields"] == ["applicant.full_name"]
    assert incomplete["next_step"] == "request_information"
    no_income = calculate_payment_load("person-1", [], data["obligations"], 18000)
    assert no_income["status"] == "insufficient_income_data"
    incomes = [
        dict(data["incomes"][0], monthly_amount=22508.60),
        dict(data["incomes"][1], monthly_amount=9411.40),
    ]
    obligations = [dict(data["obligations"][0], monthly_payment=1411.12)]
    rounded = calculate_payment_load("person-1", incomes, obligations, 8659.64)
    assert rounded["monthly_income"] == 31920
    assert rounded["payment_share_percent"] == 31.6
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
