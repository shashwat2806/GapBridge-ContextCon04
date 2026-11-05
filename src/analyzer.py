from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .document import read_policy
from .judge import judge_control
from .llm import LocalLLM, LocalModelError
from .models import ModelFinding, finding_to_dict
from .retrieval import Retriever
from .roadmap import build_roadmap


def load_checklist(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("Reference checklist must be a non-empty JSON array.")
    identifiers = [item.get("id") for item in data]
    if None in identifiers or len(set(identifiers)) != len(identifiers):
        raise ValueError("Reference checklist has a missing or duplicate control ID.")
    return data


def analyze(
    policy_path: str | Path,
    domain: str,
    checklist_path: str | Path,
    llm: LocalLLM,
    *,
    use_embeddings: bool = True,
    on_result: Callable[[dict], None] | None = None,
) -> tuple[dict, str, list[dict]]:
    policy = read_policy(policy_path)
    checklist = load_checklist(checklist_path)
    selected_domain = domain.upper()
    if selected_domain != "ALL":
        checklist = [item for item in checklist if item["domain"] == selected_domain]
    if not checklist:
        raise ValueError(f"No checklist entries found for domain '{selected_domain}'.")

    retriever = Retriever(policy.chunks, llm, use_embeddings=use_embeddings)
    results = []
    for control in checklist:
        excerpts = retriever.search(control["requirement"], k=min(8, len(policy.chunks)))
        try:
            finding = judge_control(control, excerpts, llm)
        except LocalModelError as exc:
            finding = ModelFinding(
                status="needs_review",
                confidence=0.0,
                reason=f"Local model became unavailable during this check: {exc}",
            )
        result = finding_to_dict(finding, control)
        result["retrieved_sources"] = [source.as_prompt_record() for source in excerpts]
        results.append(result)
        if on_result:
            on_result(result)

    counts = Counter(result["status"] for result in results)
    weights = {"high": 3.0, "medium": 2.0, "low": 1.0}
    credit = {"covered": 1.0, "partial": 0.5}
    total_weight = sum(weights.get(item["severity"], 1.0) for item in results)
    earned = sum(
        weights.get(item["severity"], 1.0) * credit.get(item["status"], 0.0)
        for item in results
    )
    score = round(100.0 * earned / total_weight, 1) if total_weight else 0.0

    analysis = {
        "product": "GapBridge Local Auditor",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "policy_path": policy.path,
        "policy_sha256": policy.sha256,
        "domain": selected_domain,
        "model": llm.model,
        "embedding_model": llm.embedding_model if retriever.mode.startswith("local embeddings") else None,
        "retrieval_mode": retriever.mode,
        "retrieval_notice": retriever.notice,
        "offline_runtime": "Ollama on 127.0.0.1; no cloud or external API calls",
        "control_count": len(results),
        "weighted_policy_coverage_percent": score,
        "counts": {
            "covered": counts.get("covered", 0),
            "partial": counts.get("partial", 0),
            "missing": counts.get("missing", 0),
            "needs_review": counts.get("needs_review", 0),
        },
        "scope_note": (
            "This score measures coverage in the selected policy text against the bundled "
            "checklist. It is not a certification or proof that controls operate in practice."
        ),
        "results": results,
    }
    return analysis, policy.extracted_text, build_roadmap(results)
