# Two-minute demo plan

Use a policy that is not the same exact file you used while tuning. Keep real customer data out of the recording.

## 0:00-0:15 — Customer request

Say: “A small company has paid for a first-pass security policy review. GapBridge will return cited gaps, draft amendments, and the next steps in one run.”

## 0:15-0:35 — Start one complete run

In PowerShell:

    python main.py data\policies\isms.md ISMS

Show the local Ollama address and the per-control progress. Explain that the model and embeddings run on the laptop; the assigned problem statement requires offline operation, so the optional Crustdata connector is intentionally excluded.

## 0:35-1:15 — Show the auditor's evidence

Open the generated report.html. Point to:

- the coverage summary, with needs-review shown separately;
- one control with a quote and policy source ID;
- one missing or partial item with no invented evidence;
- the CIS/MS-ISAC page link for the corresponding NIST control.

The synthetic ISMS example contains gaps and conflicting review language. Show GV.PO-02 as the exception that needs an owner to resolve, then show a partial finding with its source passage. Describe only what the actual run shows; do not claim it resolved a conflict unless the report did.

## 1:15-1:45 — Show the finished work

Open revised_policy_draft.md. The original extracted policy is preserved and proposed clauses are labeled as drafts with placeholders. Then open roadmap.md and show the timeframe, next step, and acceptance evidence.

## 1:45-2:00 — Explain the boundary

Close with: “This completes the first-pass review packet a small company would buy from a GRC analyst: cited gaps, proposed amendments, and a prioritized plan. It does not certify that controls operate. Conflicts go to human review, and a policy owner approves every change.”

## Before recording

- Run once before the timed recording so model startup does not consume the demo.
- Confirm the report opens from a local file and the output contains no secrets.
- Use a novel policy wording or a fresh synthetic variant for the recorded request.
- Verify the final video link in a private window before submission.
