"""The alignment face of a record: what was agreed, what remains to do, and who accepted it.

A review record is an audit log. This module turns it into the one page stakeholders
read and accept. Acceptance is digital: an approver's row carries a date and nothing
else, so entering the date is the act of acceptance.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from .models import Action, Approval, ApprovalDecision, Finding, Outcome, Record, Rule

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def document_hash(path: Path) -> str:
    """Short content hash of the reviewed file, so an acceptance is tied to one revision."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def today() -> str:
    return datetime.now(UTC).date().isoformat()


def derive_actions(findings: list[Finding], rules: dict[str, Rule]) -> list[Action]:
    """Failures the document owner must act on.

    A failure becomes an action when it is verified against the text, or when the author
    accepted, disputed or revised it in the walk-through. An unverified failure that nobody
    looked at stays in the appendix: a claim the model could not ground is not a commitment.
    Waived findings are never actions; the waiver and its rationale are recorded instead.
    """
    out: list[Action] = []
    for f in findings:
        if f.verdict != "fail" or f.disposition == "waived":
            continue
        if not (f.verified or f.disposition in {"accepted", "disputed", "revised"}):
            continue
        title = rules[f.rule_id].title if f.rule_id in rules else f.rule_id
        out.append(
            Action(
                rule_id=f.rule_id,
                decision_id=f.decision_id,
                severity=f.severity,
                summary=title,
                status="disputed" if f.disposition == "disputed" else "open",
            )
        )
    out.sort(key=lambda a: (SEVERITY_ORDER[a.severity], a.decision_id or "", a.rule_id))
    for i, a in enumerate(out, start=1):
        a.id = f"A{i}"
    return out


def derive_outcome(record: Record) -> Outcome:
    """The outcome the approvals imply. An explicit outcome set by a person wins over a derived one."""
    if not record.approvals:
        return record.outcome
    decisions = {a.decision for a in record.approvals}
    if "rejected" in decisions:
        return "not-approved"
    if "pending" in decisions:
        return "pending"
    if "approved-with-conditions" in decisions or record.conditions:
        return "approved-with-conditions"
    return "approved"


def add_approver(record: Record, name: str, role: str) -> Approval:
    """A pending row for someone who is expected to accept. Idempotent on name and role."""
    for a in record.approvals:
        if a.name.lower() == name.lower() and a.role.lower() == role.lower():
            return a
    a = Approval(name=name, role=role)
    record.approvals.append(a)
    return a


def sign(record: Record, name: str, role: str, decision: ApprovalDecision, note: str = "", date: str = "") -> Approval:
    """Record one stakeholder's decision. The date is the acceptance; today's if not given."""
    a = add_approver(record, name, role)
    a.decision = decision
    a.date = date or today()
    a.note = note
    record.outcome = derive_outcome(record)
    return a


def assign_owner(record: Record, action_id: str, owner: str) -> Action:
    for a in record.actions:
        if a.id == action_id:
            a.owner = owner
            return a
    raise KeyError(action_id)


def disposition_summary(findings: list[Finding]) -> dict[str, int]:
    counts = {"accepted": 0, "disputed": 0, "revised": 0, "waived": 0, "open": 0}
    for f in findings:
        if f.verdict in {"fail", "unclear"}:
            counts[f.disposition] += 1
    return counts


def render_alignment(record: Record) -> list[str]:
    """The first page of the record. Everything a stakeholder accepts is on it."""
    lines: list[str] = []
    lines.append("## Alignment")
    lines.append("")
    lines.append(
        "**Purpose.** This page states the architecture decisions in the reviewed document, "
        "the conditions attached to them and the actions they create, and records who accepted them. "
        "Acceptance is digital: an approver accepts by entering the date against their name in the "
        "approvals table, with `agent-arb sign` or by editing the record."
    )
    lines.append("")
    version = f", version {record.document_version}" if record.document_version else ""
    hash_ = f", content hash `{record.document_hash}`" if record.document_hash else ""
    lines.append(
        f"**Document.** `{record.document}`{version}{hash_}. Reviewed {record.created_at[:10]} "
        f"with model `{record.model}` at service tier {record.tier}. The acceptance below applies to "
        "this revision only; a changed document needs a new review."
    )
    lines.append("")
    lines.append(f"**Outcome.** {OUTCOME_LABELS[record.outcome]}")
    lines.append("")
    if record.statement:
        lines.append(f"**Statement.** {record.statement}")
        lines.append("")
    lines.append("**Conditions.**")
    lines.append("")
    if record.conditions:
        lines.extend(f"{i}. {c}" for i, c in enumerate(record.conditions, start=1))
    else:
        lines.append("None recorded.")
    lines.append("")

    lines.append("### Agreed decisions")
    lines.append("")
    if record.decisions:
        lines.append("| # | Decision | Chosen | Section |")
        lines.append("|---|---|---|---|")
        for d in record.decisions:
            chosen = (d.chosen or d.title).replace("|", "/")
            lines.append(f"| {d.id} | {d.title.replace('|', '/')} | {chosen} | {d.section_ref} |")
    else:
        lines.append("No decisions were extracted from the document.")
    lines.append("")

    lines.append("### Action items")
    lines.append("")
    if record.actions:
        lines.append("| # | Action | Decision | Severity | Owner | Status |")
        lines.append("|---|---|---|---|---|---|")
        for a in record.actions:
            lines.append(
                f"| {a.id} | {a.rule_id} {a.summary.replace('|', '/')} | {a.decision_id or 'document'} "
                f"| {a.severity} | {a.owner or '(unassigned)'} | {a.status} |"
            )
    else:
        lines.append("No action items. Every failure was either waived with a rationale or could not be verified.")
    lines.append("")

    counts = disposition_summary(record.findings)
    total = sum(counts.values())
    lines.append("### Disposition summary")
    lines.append("")
    lines.append(
        f"Of {total} findings that failed or were unclear: "
        + ", ".join(f"{k} {v}" for k, v in counts.items())
        + ". Not-applicable findings and verified passes are listed in the appendix."
    )
    lines.append("")

    lines.append("### Approvals")
    lines.append("")
    lines.append("| Name | Role | Decision | Date |")
    lines.append("|---|---|---|---|")
    if record.approvals:
        for ap in record.approvals:
            note = f" ({ap.note.replace('|', '/')})" if ap.note else ""
            lines.append(f"| {ap.name} | {ap.role} | {APPROVAL_LABELS[ap.decision]}{note} | {ap.date} |")
    else:
        lines.append("| | | pending | |")
    lines.append("")
    lines.append("A row with a date is an acceptance by that person on that date. A row without one is still pending.")
    lines.append("")
    return lines


OUTCOME_LABELS: dict[str, str] = {
    "pending": "Pending. Not all approvers have decided.",
    "approved": "Approved.",
    "approved-with-conditions": (
        "Approved with conditions. The conditions and action items below are part of the acceptance."
    ),
    "not-approved": "Not approved. See the approvals table for who rejected and why.",
}

APPROVAL_LABELS: dict[str, str] = {
    "pending": "pending",
    "approved": "approved",
    "approved-with-conditions": "approved with conditions",
    "rejected": "rejected",
}
