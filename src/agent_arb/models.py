"""Data models shared by the CLI, the skill and the evals.

The JSON schemas under ``spec/`` are generated from these classes by
``scripts/export_spec.py``; the skill reads those schemas, so a change here
is a change to the contract between the two engines.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Scope(StrEnum):
    ARCHITECTURE = "architecture"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    PRACTICE = "practice"


class Target(StrEnum):
    DECISION = "decision"
    DOCUMENT = "document"


class RuleType(StrEnum):
    CHECK = "check"
    ADVISORY = "advisory"


class Layer(StrEnum):
    BASE = "base"
    COMPANY = "company"
    PROJECT = "project"


class Status(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


DATA_CLASSES = ("cardholder-data", "personal-data", "health-data", "credentials", "financial-data")


class Source(BaseModel):
    """Where a rule came from. Every rule has one; the attribution file is built from these."""

    kind: Literal["public-domain", "cc-by", "mit", "author-principle", "reference", "company"]
    name: str
    locator: str = ""
    url: str = ""
    licence: str = ""
    text_reused: Literal["none", "adapted"] = "none"


class AppliesWhen(BaseModel):
    """Conditions that must hold for a rule to be selected. Empty means always."""

    data_classes: list[str] = Field(default_factory=list)
    tags_any: list[str] = Field(default_factory=list)
    min_tier: int | None = None


class Override(BaseModel):
    """How a company or project rule changes a base rule."""

    mode: Literal["supersedes", "tightens", "waives"]
    rule: str
    reason: str = ""


class Rule(BaseModel):
    id: str
    title: str
    scope: Scope = Scope.ARCHITECTURE
    target: Target = Target.DECISION
    type: RuleType = RuleType.CHECK
    severity: Severity = Severity.MEDIUM
    tags: list[str] = Field(default_factory=list)
    requirement: str = ""
    question: str = ""
    evidence_hints: list[str] = Field(default_factory=list)
    expects: list[str] = Field(default_factory=list)
    applies_when: AppliesWhen = Field(default_factory=AppliesWhen)
    level: int | None = None
    compliance_refs: list[str] = Field(default_factory=list)
    source: Source
    status: Status = Status.APPROVED
    overrides: Override | None = None
    reviewed_by: str = ""
    reviewed_on: str = ""


class Pack(BaseModel):
    name: str
    layer: Layer
    version: str = "0.0.0"
    description: str = ""
    rules: list[Rule] = Field(default_factory=list)
    content_hash: str = ""


class Option(BaseModel):
    name: str
    tradeoff: str = ""


class Section(BaseModel):
    ref: str
    heading: str
    level: int
    start_line: int
    end_line: int
    text: str


class Decision(BaseModel):
    id: str
    title: str
    section_ref: str
    scope: Scope = Scope.ARCHITECTURE
    context: str = ""
    options: list[Option] = Field(default_factory=list)
    chosen: str = ""
    implications: str = ""
    evidence_quote: str = ""
    tags: list[str] = Field(default_factory=list)
    data_classes: list[str] = Field(default_factory=list)
    confirmed: bool = False


class Finding(BaseModel):
    rule_id: str
    decision_id: str | None
    verdict: Literal["pass", "fail", "unclear", "n/a"]
    """n/a: the rule concerns a mechanism this decision does not involve, as judged from the text."""
    severity: Severity
    quote: str = ""
    explanation: str = ""
    verified: bool = False
    disposition: Literal["open", "accepted", "disputed", "revised", "waived"] = "open"
    rationale: str = ""


class AdvisoryAnswer(BaseModel):
    rule_id: str
    decision_id: str | None
    question: str
    answer: str = ""


class ManifestEntry(BaseModel):
    step: str
    decision_id: str | None = None
    sections: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    prompt_chars: int = 0
    model: str = ""
    at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class PackRef(BaseModel):
    name: str
    layer: Layer
    version: str
    content_hash: str
    rule_count: int


class LevelSummary(BaseModel):
    area: str
    observed: int
    target: int
    missing_rule_ids: list[str] = Field(default_factory=list)


class ComplianceRow(BaseModel):
    framework: str
    reference: str
    rule_id: str
    decision_id: str | None
    verdict: str
    disposition: str


class Record(BaseModel):
    engine: str
    engine_version: str
    model: str
    document: str
    tier: int
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    packs: list[PackRef] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    advisories: list[AdvisoryAnswer] = Field(default_factory=list)
    levels: list[LevelSummary] = Field(default_factory=list)
    compliance: list[ComplianceRow] = Field(default_factory=list)
    service_levels: list[str] = Field(default_factory=list)
