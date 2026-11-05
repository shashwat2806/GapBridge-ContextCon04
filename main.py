from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from src.analyzer import analyze
from src.llm import LocalLLM, LocalModelError
from src.report import write_outputs

ROOT = Path(__file__).resolve().parent
CHECKLIST = ROOT / "data" / "reference" / "checklist.json"
DOMAINS = ("ISMS", "PRIVACY", "PATCH", "RISK", "ALL")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "policy"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a policy against the bundled CIS/MS-ISAC NIST CSF checklist using local Ollama only."
    )
    parser.add_argument("policy", type=Path, help="Input PDF, DOCX, TXT, or Markdown policy")
    parser.add_argument(
        "domain",
        nargs="?",
        default="ISMS",
        type=str.upper,
        choices=DOMAINS,
        help="Checklist scope (default: ISMS)",
    )
    parser.add_argument("--model", default="qwen2.5:3b-instruct", help="Installed local Ollama model")
    parser.add_argument("--embedding-model", default="nomic-embed-text", help="Installed local embedding model")
    parser.add_argument("--no-embeddings", action="store_true", help="Use deterministic local lexical retrieval")
    parser.add_argument("--checklist", type=Path, default=CHECKLIST, help="Local reference checklist JSON")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output", help="Local output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.policy.is_file():
        print(f"Policy file not found: {args.policy}", file=sys.stderr)
        return 2
    llm = LocalLLM(model=args.model, embedding_model=args.embedding_model)
    try:
        models = llm.check_available()
        print(f"Local Ollama ready at 127.0.0.1:11434; model: {args.model}")
        print(f"Local models detected: {', '.join(models)}")
        counter = [0]

        def progress(result: dict) -> None:
            counter[0] += 1
            print(
                f"[{counter[0]}] {result['id']:<10} {result['status']:<12} "
                f"confidence={result['confidence']:.2f}"
            )

        analysis, original_text, roadmap = analyze(
            args.policy,
            args.domain,
            args.checklist,
            llm,
            use_embeddings=not args.no_embeddings,
            on_result=progress,
        )
        run_dir = (
            args.output_dir
            / f"{_slug(args.policy.stem)}-{args.domain.lower()}-{analysis['policy_sha256'][:8]}"
        )
        write_outputs(run_dir, analysis, original_text, roadmap)
    except (LocalModelError, OSError, ValueError) as exc:
        print(f"Audit stopped safely: {exc}", file=sys.stderr)
        return 2

    if analysis["retrieval_notice"]:
        print(analysis["retrieval_notice"])
    print()
    print(
        f"Verified policy coverage: {analysis['weighted_policy_coverage_percent']}% "
        f"({analysis['control_count']} controls; {analysis['counts']['needs_review']} need review)"
    )
    print(f"Artifacts: {run_dir}")
    print(f"Open the offline report: {run_dir / 'report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
