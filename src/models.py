from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["covered", "partial", "missing", "needs_review"]


@dataclass(frozen=True)
class SourceChunk:
    source_id: str
    text: str
    section: str
    page: int | None = None

    def as_prompt_record(self) -> dict[str, str | int | None]:
        return {
            "source_id": self.source_id,
            "section": self.section,
            "page": self.page,
            "text": self.text,
        }


class Evidence(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source_id: str
    quote: str


class ModelFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Status
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    evidence: list[Evidence] = Field(default_factory=list)
    proposed_clause: str = ""
    classification_basis: str = "local_model"


@dataclass
class PolicyDocument:
    path: str
    extracted_text: str
    chunks: list[SourceChunk]
    sha256: str


def finding_to_dict(finding: ModelFinding, control: dict) -> dict:
    return {
        "id": control["id"],
        "domain": control["domain"],
        "function": control["function"],
        "severity": control["severity"],
        "requirement": control["requirement"],
        "guide_page": control["guide_page"],
        "guide_url": control["guide_url"],
        "status": finding.status,
        "confidence": round(finding.confidence, 2),
        "classification_basis": finding.classification_basis,
        "reason": finding.reason.strip(),
        "evidence": [item.model_dump() for item in finding.evidence],
        "proposed_clause": finding.proposed_clause.strip(),
    }
