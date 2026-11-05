from __future__ import annotations

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
TIMEFRAME = {
    "high": "0-30 days",
    "medium": "31-90 days",
    "low": "91-180 days",
}


def build_roadmap(results: list[dict]) -> list[dict]:
    actions = []
    for result in results:
        if result["status"] == "covered":
            continue
        status = result["status"]
        if status == "needs_review":
            next_step = (
                "Manually verify the cited passages, reconcile contradictory wording, "
                "and record the auditor's decision."
            )
        elif status == "partial":
            next_step = (
                "Assign an accountable owner, close the specific omissions in the draft, "
                "and attach evidence that the process is implemented."
            )
        else:
            next_step = (
                "Assign an accountable owner, approve a policy clause for this requirement, "
                "and define how implementation evidence will be retained."
            )
        actions.append(
            {
                "timeframe": TIMEFRAME.get(result["severity"], "31-90 days"),
                "priority": result["severity"],
                "control_id": result["id"],
                "status": status,
                "requirement": result["requirement"],
                "next_step": next_step,
                "proposed_clause": result.get("proposed_clause", ""),
                "acceptance_evidence": (
                    "Approved policy text plus a dated implementation record or review artifact."
                ),
            }
        )

    return sorted(
        actions,
        key=lambda item: (
            SEVERITY_ORDER.get(item["priority"], 3),
            {"missing": 0, "needs_review": 1, "partial": 2}.get(item["status"], 3),
            item["control_id"],
        ),
    )
