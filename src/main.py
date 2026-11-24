"""Procedural KT2 prototype for reviewing a consumer microloan application.

This educational calculation is not a regulatory PDN calculation or an
automated lending decision. All sample data is synthetic.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path


def check_request(
    application: dict,
    applicant: dict,
    documents_by_id: dict,
    application_documents: list,
    required_fields: list,
    required_kinds: list,
) -> dict:
    """Find missing fields and document kinds for one application.

    The nested scan is intentional: with f fields, r required kinds and d
    document links, worst-case time is O(f + r*d), extra memory O(f + r).
    """
    entities = {"application": application, "applicant": applicant}
    missing_fields = []
    for entity_name, field_name in required_fields:
        value = entities[entity_name].get(field_name)
        blank_text = isinstance(value, str) and not value.strip()
        if value is None or blank_text or (isinstance(value, (int, float)) and value <= 0):
            missing_fields.append(f"{entity_name}.{field_name}")

    missing_documents = []
    for kind in required_kinds:
        found = False
        for link in application_documents:
            if link["application_id"] != application["application_id"]:
                continue
            document = documents_by_id.get(link["document_id"])
            if document and document["kind"] == kind and document["valid"]:
                found = True
                break
        if not found:
            missing_documents.append(kind)

    return {
        "complete": not missing_fields and not missing_documents,
        "missing_fields": missing_fields,
        "missing_documents": missing_documents,
    }


def calculate_payment_load(
    applicant_id: str,
    incomes: list,
    obligations: list,
    proposed_monthly_payment: int | float,
) -> dict:
    """Estimate a payment share in O(n + m) time and O(1) extra memory."""
    if proposed_monthly_payment < 0:
        raise ValueError("Предложенный платёж не может быть отрицательным")

    monthly_income = Fraction(0)
    for income in incomes:
        if income["applicant_id"] == applicant_id and income["verified"]:
            monthly_income += Fraction(str(income["monthly_amount"]))

    existing_payments = Fraction(0)
    for obligation in obligations:
        if obligation["applicant_id"] == applicant_id and obligation["active"]:
            existing_payments += Fraction(str(obligation["monthly_payment"]))

    share = None
    if monthly_income > 0:
        # Keep decimal amounts exact through rounding, then emit a JSON number.
        total_payment = existing_payments + Fraction(str(proposed_monthly_payment))
        share = float(round(total_payment * 100 / monthly_income, 1))
    return {
        "status": "calculated" if share is not None else "insufficient_income_data",
        "monthly_income": int(monthly_income) if monthly_income.denominator == 1 else float(monthly_income),
        "existing_payments": int(existing_payments) if existing_payments.denominator == 1 else float(existing_payments),
        "payment_share_percent": share,
    }


def record_decision(
    application: dict,
    decision_id: str,
    employee_id: str,
    outcome: str,
    reason: str,
    approved_amount: int | None = None,
    approved_term_months: int | None = None,
) -> tuple[dict, dict]:
    """Record an authorized employee's decision without changing the input."""
    if application["status"] in {"approved", "refused", "withdrawn"}:
        raise ValueError("У завершённой заявки уже есть итоговый статус")
    if not employee_id:
        raise ValueError("Не указан уполномоченный сотрудник")
    if outcome not in {"approved", "refused"}:
        raise ValueError("Допустимы только одобрение и отказ")
    if outcome == "refused" and not reason:
        raise ValueError("Для отказа требуется основание")
    if outcome == "approved" and (
        approved_amount is None or approved_amount <= 0
        or approved_term_months is None or approved_term_months <= 0
    ):
        raise ValueError("Для одобрения нужны положительные сумма и срок")

    updated_application = dict(application)
    updated_application["status"] = outcome
    decision = {
        "decision_id": decision_id,
        "application_id": application["application_id"],
        "employee_id": employee_id,
        "outcome": outcome,
        "reason": reason,
        "approved_amount": approved_amount if outcome == "approved" else None,
        "approved_term_months": approved_term_months if outcome == "approved" else None,
    }
    return updated_application, decision


def record_notification(
    decision: dict,
    notification_id: str,
    channel: str,
    sent: bool,
) -> dict:
    """Keep each notification attempt, including an unsuccessful one."""
    if not channel:
        raise ValueError("Не указан канал уведомления")
    return {
        "notification_id": notification_id,
        "decision_id": decision["decision_id"],
        "channel": channel,
        "sent": sent,
    }


def run_case(data: dict) -> dict:
    """Run one synthetic case using entities from the logical model."""
    applicant = data["applicant"]
    application = data["application"]
    if application["applicant_id"] != applicant["applicant_id"]:
        raise ValueError("Заявка связана с другим заявителем")
    documents_by_id = {row["document_id"]: row for row in data["documents"]}
    completeness = check_request(
        application,
        applicant,
        documents_by_id,
        data["application_documents"],
        data["required_fields"],
        data["required_document_kinds"],
    )
    payment_load = calculate_payment_load(
        applicant["applicant_id"],
        data["incomes"],
        data["obligations"],
        data["proposed_monthly_payment"],
    )
    result = {"application_id": application["application_id"],
              "completeness": completeness, "payment_load": payment_load}
    if not completeness["complete"] or payment_load["status"] != "calculated":
        result["next_step"] = "request_information"
        return result

    choice = data["employee_decision"]
    updated_application, decision = record_decision(
        application,
        choice["decision_id"],
        choice["employee_id"],
        choice["outcome"],
        choice["reason"],
        choice.get("approved_amount"),
        choice.get("approved_term_months"),
    )
    notification = record_notification(
        decision,
        data["notification"]["notification_id"],
        data["notification"]["channel"],
        data["notification"]["sent"],
    )
    result.update({"application": updated_application,
                   "decision": decision,
                   "notification": notification})
    if not notification["sent"]:
        result["next_step"] = "retry_notification"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=Path(__file__).with_name("sample_data.json"),
        help="JSON с синтетическими данными одной заявки",
    )
    args = parser.parse_args()
    with args.data.open(encoding="utf-8") as stream:
        data = json.load(stream)
    print(json.dumps(run_case(data), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
