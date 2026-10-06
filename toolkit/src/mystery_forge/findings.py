"""Findings: the one shape of every problem that the loader and the checks report.

Fix loops in the generator read findings, so each one names the rule, the file, the line when known, the field path,
and a hint that tells the agent how to fix it.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["error", "warning"]


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    severity: Severity
    rule: str
    message: str
    file: str | None = None
    line: int | None = None
    path: str | None = None
    fix_hint: str | None = None

    @property
    def location(self) -> str:
        if self.file is None:
            return ""
        return f"{self.file}:{self.line}" if self.line is not None else self.file


def count_errors(findings: list[Finding]) -> int:
    return sum(1 for finding in findings if finding.severity == "error")


def findings_to_json(findings: list[Finding]) -> list[dict[str, Any]]:
    return [finding.model_dump(exclude_none=True) for finding in findings]
