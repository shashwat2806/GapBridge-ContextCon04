# GapBridge Local Auditor

**A security policy analyst that turns a policy document into an evidence-backed gap report, a reviewable amendment draft, and a prioritized remediation roadmap.**

## Why this is a service

Organizations pay security consultants and compliance teams to read policy documents, map them to frameworks, explain gaps, write policy language, and plan remediation. GapBridge takes one policy from intake to a review packet in a single local run. A human still approves policy changes and resolves ambiguous evidence.

This is a fresh hackathon implementation built from the problem statement and my experience with an earlier internship project. It does not copy that project's source code. The hackathon handbook asks builders to bring an idea, not code, and to start in a new repository during the event.

## Hackathon fit

This fits the **Trust and compliance** theme: it takes on the first-pass policy review work that a security consultant or GRC analyst is paid to do. One request produces a cited gap report, proposed amendments, and an ordered remediation plan. Conflicts and unverifiable evidence are explicit human exceptions; the policy owner approves changes. The assigned problem statement requires local-only execution and zero external APIs, so this build intentionally does not connect the optional Crustdata MCP service described in the general event handbook.

## What it produces

For one ISMS, privacy, patch-management, or risk-management policy, the CLI:

1. Extracts text from PDF, DOCX, TXT, or Markdown.
2. Retrieves relevant passages with a local embedding model, with a lexical fallback.
3. Asks a local LLM to classify each scoped requirement and cite exact policy text.
4. Verifies every returned quote against the original extracted policy text. Invalid quotes become needs-review findings.
5. If the model says missing despite a curated, control-specific phrase in a supplied passage, conservatively raises the result to partial and shows the matched source. It checks passage text, not headings, and cannot mark a control covered.
6. Drafts proposed clauses for gaps without inventing owners, tools, schedules, or implementation facts.
7. Writes a report, unchanged-source-plus-amendments draft, and prioritized roadmap.

The bundled reference contains 27 selected NIST CSF 2.0 subcategories mapped in the CIS/MS-ISAC 2024 guide. It is an intentionally scoped prototype, not the complete framework.

## Offline design

The application calls only Ollama on 127.0.0.1:11434. It contains no web, cloud-LLM, Crustdata, or external API client. Policy files, embeddings, analysis, and generated reports remain on the machine. Reference URLs in reports are provenance links for a human reviewer; the application does not fetch them.

Recommended local models:

- Chat: qwen2.5:3b-instruct
- Embeddings: nomic-embed-text

## Run it

From PowerShell in the project folder:

    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

If the local Ollama service is not already running, start it in another PowerShell window:

    ollama serve

The model downloads shown in the builder's setup notes are enough. If a model is absent, pull it once while online:

    ollama pull qwen2.5:3b-instruct
    ollama pull nomic-embed-text

Run the ISMS example:

    python main.py data\policies\isms.md ISMS

Other scopes:

    python main.py data\policies\data_privacy.md PRIVACY
    python main.py data\policies\patch_management.md PATCH
    python main.py data\policies\risk_management.md RISK

For lexical retrieval without the embedding model:

    python main.py data\policies\isms.md ISMS --no-embeddings

The default checklist scope is ISMS. ALL runs every bundled requirement and will take longer.

## Review the result

The run prints one line per control. It writes a deterministic folder under output/, named from the policy, scope, and input hash:

- report.html — offline visual report with evidence cards and status filtering
- report.md — readable audit summary and detailed findings
- revised_policy_draft.md — extracted source text kept unchanged, followed by proposed clauses
- roadmap.md — prioritized remediation actions and acceptance evidence
- analysis.json — machine-readable record of the run

Open report.html locally in a browser. Re-running the same policy and scope writes to the same folder, so a retry does not create a second external action or send data anywhere.

## What the score means

The weighted policy-coverage score uses the prototype's explicit planning weights: high = 3, medium = 2, low = 1. Covered earns full weight, partial earns half, and missing or needs-review earns zero. The labels and weights are product choices, not official CIS/NIST risk ratings.

A written policy is not proof that a control works in practice. The report says this prominently. Every generated quote is checked against the cited passage. The conservative phrase rule can only change missing to partial; review its matched evidence because a phrase alone does not prove full coverage.

## Architecture

![GapBridge Local Auditor architecture](docs/architecture.svg)

The parser and analysis are deterministic except for the local model's wording and judgments. Temperature is zero and a fixed seed is supplied. Model confidence is displayed as a model-reported signal, not a calibrated probability. Each result shows whether it came from the model, citation validation, low confidence, or the conservative curated partial rule.

## Reference

The checklist follows the CIS/MS-ISAC [NIST Cybersecurity Framework Policy Template Guide (2024)](https://www.cisecurity.org/-/media/project/cisecurity/cisecurity/data/media/files/uploads/2024/08/cis-ms-isac-nist-cybersecurity-framework-policy-template-guide-2024.pdf).
See data/reference/README.md for scope and mapping notes. The four policy labels are demo scopes; they are not NIST categories.

## Approaches considered

- Keyword-only matching is fast and explainable, but misses paraphrases and can confuse a mention with meaningful coverage.
- Local embeddings plus a local LLM can retrieve paraphrased evidence while keeping documents on-device. Exact-quote checking makes fabricated citations visible; it cannot prove the quote supports the whole requirement.
- Cloud LLMs could offer stronger language reasoning, but violate the problem statement's offline-only constraint.

The selected approach is a local hybrid: retrieval narrows the evidence, the model reasons over a small excerpt set, and deterministic code checks citations and creates the roadmap.

## Limitations and next steps

- Only 27 carefully selected controls are bundled. Expand the checklist after validating mappings against the guide.
- Scanned PDFs need OCR before ingestion; this prototype fails clearly rather than silently auditing an empty scan.
- The LLM can still misclassify a real quote. Review partial, missing, and needs-review results before acting.
- PDF layout, signatures, and tables may not survive text extraction. DOCX table text is included, but original formatting is not preserved.
- The tool evaluates policy wording, not actual technical configuration or operating effectiveness.
- Organizations should add a human-approved profile for control owners, risk appetite, timelines, and legal obligations before using this beyond a demo.
