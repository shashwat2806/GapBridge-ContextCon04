from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

from .roadmap import build_roadmap

STATUS_LABEL = {
    "covered": "Covered",
    "partial": "Partial",
    "missing": "Missing",
    "needs_review": "Needs review",
}

BASIS_LABEL = {
    "local_model": "Local model assessment",
    "curated_partial_signal": "Conservative curated rule; partial only",
    "quote_validation": "Citation validation requires human review",
    "low_confidence": "Low model confidence requires human review",
}


def _atomic_write(path: Path, content: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def render_markdown(analysis: dict[str, Any]) -> str:
    counts = analysis["counts"]
    lines = [
        "# GapBridge Local Auditor | Policy evidence report",
        "",
        f"- **Policy:** {Path(analysis['policy_path']).name}",
        f"- **Domain:** {analysis['domain']}",
        f"- **Local model:** {analysis['model']}",
        f"- **Retrieved with:** {analysis['retrieval_mode']}",
        f"- **Verified policy coverage:** {analysis['weighted_policy_coverage_percent']}%",
        f"- **Controls reviewed:** {analysis['control_count']}",
        "",
        "## Summary",
        "",
        f"Covered: {counts['covered']} · Partial: {counts['partial']} · "
        f"Missing: {counts['missing']} · Needs review: {counts['needs_review']}",
        "",
        "> The score measures policy-text coverage for this bundled checklist. It is not a certification or proof that controls operate in practice.",
        "",
        "## Findings",
        "",
        "| Control | Status | Priority | Evidence |",
        "|---|---|---:|---|",
    ]
    for item in analysis["results"]:
        evidence = ", ".join(
            f"{entry['source_id']}: “{html.escape(entry['quote'][:110])}”"
            for entry in item["evidence"]
        ) or "No verified policy quote"
        safe_evidence = evidence.replace("|", "\\|")
        lines.append(
            f"| {item['id']} | {STATUS_LABEL[item['status']]} | "
            f"{item['severity']} | {safe_evidence} |"
        )

    for item in analysis["results"]:
        lines.extend(
            [
                "",
                f"### {item['id']} — {STATUS_LABEL[item['status']]}",
                "",
                f"**Requirement:** {html.escape(item['requirement'])}",
                "",
                f"**Why:** {html.escape(item['reason'])}",
                "",
                f"**Decision basis:** {html.escape(BASIS_LABEL.get(item.get('classification_basis', 'local_model'), 'Local model assessment'))}",
                "",
                f"**Model confidence:** {item['confidence']:.2f} (not a probability of compliance)",
                "",
            ]
        )
        if item["status"] == "missing":
            evidence_label = "Relevant policy text reviewed (insufficient to satisfy the control)"
        elif item["status"] == "needs_review":
            evidence_label = "Passages flagged for human review"
        else:
            evidence_label = "Verified supporting policy evidence"
        if item["evidence"]:
            lines.append(f"**{evidence_label}:**")
            lines.append("")
            for entry in item["evidence"]:
                quote = html.escape(" ".join(entry["quote"].split()))
                lines.append(
                    f"> “{quote}”  \n> Policy source {entry['source_id']}"
                )
                lines.append("")
        else:
            lines.extend([f"**{evidence_label}:** none returned", ""])
        lines.extend(
            [
                f"**Framework source:** [CIS/MS-ISAC NIST CSF Policy Template Guide, p. {item['guide_page']}]({item['guide_url']})",
                "",
            ]
        )
        if item["proposed_clause"]:
            lines.extend(
                [
                    "**Draft clause (requires owner review):**",
                    "",
                    html.escape(item["proposed_clause"]),
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def render_revised_policy(original_text: str, analysis: dict[str, Any]) -> str:
    lines = [
        "# Draft policy amendments",
        "",
        "> Review required. This file preserves the extracted source text below and appends suggested language. A draft clause does not assert that the organization has implemented the control.",
        "",
        f"Source policy: {Path(analysis['policy_path']).name}",
        "",
        "## Existing policy text (unchanged)",
        "",
        original_text.strip(),
        "",
        "## Proposed amendments",
        "",
    ]
    proposals = [
        item for item in analysis["results"]
        if item["status"] in {"partial", "missing"} and item["proposed_clause"]
    ]
    if not proposals:
        lines.extend(["No unambiguous draft clauses were generated. Review the report findings manually.", ""])
    for item in proposals:
        lines.extend(
            [
                f"### {item['id']} — {item['status'].replace('_', ' ').title()}",
                "",
                f"**Requirement:** {item['requirement']}",
                "",
                item["proposed_clause"],
                "",
                f"**Source:** CIS/MS-ISAC guide, p. {item['guide_page']}; "
                f"policy evidence reviewed: "
                f"{', '.join(e['source_id'] for e in item['evidence']) or 'none found'}.",
                "",
            ]
        )
    lines.extend(
        [
            "## Decisions still requiring an owner",
            "",
            "- Replace every bracketed placeholder with an approved owner, interval, system, or threshold.",
            "- Confirm the clause matches the organization’s actual controls and contractual obligations.",
            "- Approve and publish changes through the organization’s normal policy process.",
            "",
        ]
    )
    return "\n".join(lines)


def render_roadmap(roadmap: list[dict]) -> str:
    lines = [
        "# Remediation roadmap",
        "",
        "Priorities are a planning aid. Confirm owners, risk acceptance, and due dates with the organization.",
        "",
        "| Window | Priority | Control | Next step | Acceptance evidence |",
        "|---|---|---|---|---|",
    ]
    for item in roadmap:
        lines.append(
            f"| {item['timeframe']} | {item['priority']} | {item['control_id']} | "
            f"{item['next_step']} | {item['acceptance_evidence']} |"
        )
    if not roadmap:
        lines.extend(["", "No unresolved or review-required items were found in this scope.", ""])
    return "\n".join(lines) + "\n"


def _status_card(item: dict[str, Any]) -> str:
    status = html.escape(item["status"])
    evidence_html = ""
    evidence_label = (
        "Relevant passage reviewed; it does not satisfy the control"
        if item["status"] == "missing"
        else "Passage requiring human review"
        if item["status"] == "needs_review"
        else "Verified supporting passage"
    )
    for evidence in item["evidence"]:
        quote = html.escape(evidence["quote"])
        source = html.escape(evidence["source_id"])
        evidence_html += (
            f'<blockquote>“{quote}”<footer>Policy source {source}</footer></blockquote>'
        )
    if not evidence_html:
        evidence_html = '<p class="muted">No quote was returned for this finding.</p>'
    if item["evidence"]:
        evidence_html = f'<div class="evidence-label">{html.escape(evidence_label)}</div>{evidence_html}'

    basis = html.escape(
        BASIS_LABEL.get(item.get("classification_basis", "local_model"), "Local model assessment")
    )

    retrieved_html = ""
    retrieved = item.get("retrieved_sources", [])
    if retrieved:
        entries = "".join(
            f'<li><strong>{html.escape(str(source["source_id"]))} · '
            f'{html.escape(str(source["section"]))}</strong><p>{html.escape(str(source["text"]))}</p></li>'
            for source in retrieved
        )
        retrieved_html = (
            f'<details class="sources"><summary>Passages supplied to the model ({len(retrieved)})</summary>'
            f'<ul>{entries}</ul></details>'
        )

    proposal = ""
    if item["proposed_clause"]:
        proposal = (
            '<div class="proposal"><strong>Draft language · owner review required</strong>'
            f'<p>{html.escape(item["proposed_clause"])}</p></div>'
        )
    return (
        f'<article class="finding" data-status="{status}">'
        f'<div class="finding-head"><div><span class="control">{html.escape(item["id"])}</span>'
        f'<span class="severity">{html.escape(item["severity"])} priority</span></div>'
        f'<span class="badge {status}">{html.escape(STATUS_LABEL[item["status"]])}</span></div>'
        f'<h3>{html.escape(item["requirement"])}</h3>'
        f'<p class="reason">{html.escape(item["reason"])}</p>'
        f'<p class="basis"><strong>Decision basis:</strong> {basis}</p>'
        f'{evidence_html}{proposal}{retrieved_html}'
        f'<a class="source" href="{html.escape(item["guide_url"], quote=True)}" target="_blank" rel="noreferrer">'
        f'CIS/MS-ISAC guide · page {item["guide_page"]}</a>'
        '</article>'
    )


def render_html(analysis: dict[str, Any], roadmap: list[dict]) -> str:
    counts = analysis["counts"]
    score = analysis["weighted_policy_coverage_percent"]
    cards = "\n".join(_status_card(item) for item in analysis["results"])
    roadmap_rows = "".join(
        "<tr>"
        f"<td>{html.escape(item['timeframe'])}</td>"
        f"<td>{html.escape(item['priority'])}</td>"
        f"<td>{html.escape(item['control_id'])}</td>"
        f"<td>{html.escape(item['next_step'])}</td>"
        "</tr>"
        for item in roadmap
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GapBridge Local Auditor</title>
<style>
:root{{color-scheme:light;--ink:#172b3a;--muted:#617383;--line:#dce6e8;--paper:#f4f8f8;--teal:#047c78;--navy:#102b3f}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Segoe UI,Arial,sans-serif}}
header{{background:linear-gradient(120deg,#102b3f,#124653);color:white;padding:30px max(22px,calc((100vw - 1100px)/2))}}
.brand{{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:#9de0d5;font-weight:700}}
h1{{font-size:clamp(26px,4vw,40px);line-height:1.1;margin:10px 0}}
header p{{color:#d1e3e7;margin:8px 0 0}}main{{max-width:1100px;margin:24px auto;padding:0 18px}}
.metrics{{display:grid;grid-template-columns:repeat(5,minmax(100px,1fr));gap:12px;margin-bottom:24px}}
.metric,.panel,.finding{{background:white;border:1px solid var(--line);border-radius:14px;box-shadow:0 4px 16px #183e4b0a}}
.metric{{padding:16px}}.metric strong{{display:block;font-size:26px;color:var(--navy)}}.metric span{{font-size:12px;color:var(--muted)}}
.toolbar{{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:18px 0}}
select{{border:1px solid var(--line);border-radius:8px;background:white;padding:9px 12px;color:var(--ink)}}
.findings{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.finding{{padding:18px}}.finding-head{{display:flex;justify-content:space-between;align-items:center;gap:8px}}
.control{{font-weight:800;color:var(--teal);font-size:13px;letter-spacing:.04em}}
.severity{{margin-left:10px;text-transform:uppercase;font-size:10px;color:var(--muted);letter-spacing:.08em}}
.badge{{border-radius:999px;padding:4px 10px;font-size:11px;font-weight:700;text-transform:uppercase}}
.badge.covered{{background:#d9f4e8;color:#137148}}.badge.partial{{background:#fff0cc;color:#8a5c00}}
.badge.missing{{background:#ffe0dc;color:#a4372d}}.badge.needs_review{{background:#eee5ff;color:#6846a1}}
h2{{margin:28px 0 10px}}h3{{font-size:17px;line-height:1.35;margin:14px 0 8px}}
.reason,.muted{{color:var(--muted)}}.basis{{font-size:12px;color:var(--muted);margin-top:-6px}}blockquote{{margin:10px 0;padding:11px 14px;border-left:3px solid #58aaa0;background:#f3f9f8;font-size:14px}}
blockquote footer{{font-size:11px;color:var(--muted);margin-top:6px}}.proposal{{margin-top:12px;padding:12px;background:#f3f0ff;border-radius:9px}}
.proposal strong{{font-size:11px;text-transform:uppercase;color:#60449b;letter-spacing:.04em}}
.proposal p{{margin:7px 0 0}}.source{{font-size:12px;color:var(--teal);display:inline-block;margin-top:12px}}
.panel{{padding:18px;overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid var(--line)}}th{{color:var(--muted)}}
.note{{margin:20px 0;padding:13px 16px;background:#eaf2f3;border-radius:10px;color:#415765;font-size:13px}}
.sources{{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}}.sources summary{{cursor:pointer;color:var(--teal);font-size:12px;font-weight:700}}
.sources ul{{padding-left:20px}}.sources li{{margin:8px 0;color:var(--muted);font-size:12px}}.sources p{{white-space:pre-wrap;margin:3px 0 0}}.evidence-label{{font-size:11px;color:var(--muted);font-weight:700;margin-top:10px}}
@media(max-width:760px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.findings{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><div class="brand">GapBridge · Local Auditor</div><h1>Policy evidence, gaps, next steps.</h1>
<p>{html.escape(Path(analysis["policy_path"]).name)} · {html.escape(analysis["domain"])} · local model {html.escape(analysis["model"])}</p></header>
<main>
<section class="metrics">
<div class="metric"><strong>{score}%</strong><span>weighted policy coverage</span></div>
<div class="metric"><strong>{counts["covered"]}</strong><span>covered</span></div>
<div class="metric"><strong>{counts["partial"]}</strong><span>partial</span></div>
<div class="metric"><strong>{counts["missing"]}</strong><span>missing</span></div>
<div class="metric"><strong>{counts["needs_review"]}</strong><span>needs review</span></div>
</section>
<div class="note">Coverage score reflects policy wording in this checklist. It does not certify operational effectiveness. Policy excerpts and analysis stay on this machine.</div>
<div class="toolbar"><h2>Evidence findings</h2><label>Show <select id="filter" onchange="filterCards()"><option value="all">All findings</option><option value="covered">Covered</option><option value="partial">Partial</option><option value="missing">Missing</option><option value="needs_review">Needs review</option></select></label></div>
<section class="findings">{cards}</section>
<h2>Prioritized remediation</h2>
<section class="panel"><table><thead><tr><th>Window</th><th>Priority</th><th>Control</th><th>Next step</th></tr></thead><tbody>{roadmap_rows}</tbody></table></section>
<div class="note">Run ID: {html.escape(analysis["policy_sha256"][:12])} · Retrieval: {html.escape(analysis["retrieval_mode"])} · No cloud calls.</div>
</main>
<script>
function filterCards(){{const value=document.getElementById('filter').value;document.querySelectorAll('.finding').forEach(card=>{{card.hidden=value!=='all'&&card.dataset.status!==value}})}}
</script>
</body></html>
"""


def write_outputs(
    output_dir: str | Path,
    analysis: dict[str, Any],
    original_text: str,
    roadmap: list[dict] | None = None,
) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    roadmap_items = roadmap if roadmap is not None else build_roadmap(analysis["results"])
    _atomic_write(destination / "analysis.json", json.dumps(analysis, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(destination / "report.md", render_markdown(analysis))
    _atomic_write(destination / "revised_policy_draft.md", render_revised_policy(original_text, analysis))
    _atomic_write(destination / "roadmap.md", render_roadmap(roadmap_items))
    _atomic_write(destination / "report.html", render_html(analysis, roadmap_items))
    return destination
