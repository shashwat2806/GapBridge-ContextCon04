# Build notes

Keep this file honest and update it during the event. Judges want to hear what was considered, what actually worked, what failed, and why the approach was chosen.

## Hackathon fit

The event handbook encourages Crustdata use but makes it optional and asks for an end-to-end service. The assigned policy-analysis problem statement is narrower and explicitly requires local execution with zero external API integration. GapBridge therefore targets the Trust and compliance theme as a local first-pass policy review service; it does not call the Crustdata MCP server.

## Before implementation

| Approach | Expected strength | Main risk | Decision |
|---|---|---|---|
| Keyword matching only | Fast, transparent, easy to run offline | Misses paraphrases; a keyword can look like coverage without satisfying a requirement | Keep only as a retrieval fallback |
| Local embeddings plus local LLM | Handles paraphrases while policy data stays on-device | Small models can misjudge; retrieved text may be incomplete | Chosen, with exact-quote verification and needs-review states |
| Cloud model | Potentially stronger language reasoning | Conflicts with the problem statement's offline-only requirement | Excluded |

## Environment notes from the builder's pasted console

The supplied PowerShell log shows Ollama 0.40.14, qwen2.5:3b-instruct, and nomic-embed-text installed. It also shows a one-line local hello response. These observations came from the builder's earlier console capture; rerun the actual audit in this repo and record what happens.

## Record during the build

- Time / commit:
- Policy and scope used:
- What worked:
- What failed or was slow:
- Hardest case:
- How the quote verifier behaved:
- Change made:
- What remains for a human:

## First end-to-end run (builder console)

The first local run reached Ollama, processed all eight ISMS controls, and wrote the expected artifact folder. It reported six missing findings and two needs-review findings, even though the synthetic input contains relevant review, inventory, access, monitoring, and incident language. The run also exposed a confidence value of 100 rejected by the 0-1 schema, and a validator rule that incorrectly turned any missing result with a relevant quote into needs-review.

Changes made after that run:
- Retrieve up to eight passages for the small policy and include the section heading in lexical and embedding inputs.
- Clarify the rubric: related but incomplete language is partial; conflicting review statements are needs-review; a missing result may cite a near-match without implying coverage.
- Normalize model confidence values expressed as 0-100 to 0-1.
- Save the passages shown to the model and expose them in the HTML report so reviewers can see whether retrieval missed evidence.

Rerun the same command and record the new statuses, quotes, and anything still wrong. The model may still misclassify; do not present this first result as a valid audit outcome.

## Second end-to-end run (builder console)

The second local run retrieved all eight policy sections for every control, including the inventory, access, monitoring, and incident passages. The model returned seven missing results and one needs-review result (GV.PO-02), so retrieval was working while the small model still treated incomplete but relevant text as missing.

Change made after this run:
- Added control-specific curated partial signals. When a result is missing but a listed phrase appears in a retrieved passage, the deterministic rule changes it to partial, attaches the source passage, and explains the match. It cannot change any result to covered, and it does not override needs-review.
- Match signals against passage text case-insensitively; section headings alone do not trigger the rule.
- Added the decision basis to HTML and Markdown reports so reviewers can distinguish the model from the conservative rule.

At this stage, the signal change awaited a rerun. Check especially RC.RP-01: backups are mentioned, but the policy does not define recovery execution. Confirm the partial label and evidence are useful, and tune the signal if they are too broad.

## Third end-to-end run (builder console)

The rerun after adding curated signals produced six partial findings, one missing finding, and one needs-review finding; weighted policy-text coverage was 40.5%. The evidence excerpts for the six partial findings point to the intended sections. GV.PO-02 correctly remained needs-review because the policy says both annual review and incident-only review.

Report issue found during review: the local model reused GV.PO-02's annual-review explanation under GV.PO-01 and returned unrelated excerpts with the GV.PO-02 conflict. Changes made:
- Remove the model's free-form explanation when the deterministic rule changes a missing result to partial; show the matched signals and explicit review boundary instead.
- Filter needs-review citations to passages containing this control's curated signals when such matches exist.
- Leave missing findings without individual evidence quotes; all retrieved excerpts remain available in the expandable source list.

Rerun once more before recording. Confirm GV.PO-01's reason now describes policy establishment/communication only, GV.PO-02 cites just the conflicting review passages, and GV.OV-01 remains missing without a misleading quote.

Follow-up report check: GV.PO-02's citation filter retained the annual-review passage but missed the incident-only passage because of the word "only". Added that exact phrase to the control's curated signals. Rerun and confirm both S0002 and S0008 appear under GV.PO-02 before recording.
