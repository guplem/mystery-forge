"""Output helpers of the `forge` verbs: one JSON object per run, capped findings, and report files."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, TextIO

from mystery_forge.findings import Finding, count_errors, findings_to_json

MAX_FINDINGS_IN_OUTPUT: int = 20
BROWSER_FIX: Final[str] = "Install Google Chrome or Microsoft Edge, or run: uv run playwright install chromium"


@dataclass(frozen=True)
class OutputOptions:
    """What a verb reports and writes. Parallel fixers use both fields, so that no fixer overwrites a shared report.

    `only` keeps the findings whose file is in the set; the verb still runs every check. `write` False keeps every
    file in the game folder as it is: no report, no game.json, no ledger, no fix files.
    """

    only: frozenset[str] | None = None
    write: bool = True

    def selected(self, findings: list[Finding]) -> list[Finding]:
        if self.only is None:
            return findings
        return [finding for finding in findings if finding.file in self.only]


def parse_file_list(text: str) -> frozenset[str]:
    """Parse the `--only` value: source files relative to source/, separated by commas."""
    return frozenset(part.strip() for part in text.split(",") if part.strip())


def emit(output: TextIO, payload: dict[str, Any]) -> None:
    output.write(json.dumps(payload, ensure_ascii=False) + "\n")


def capped_findings(findings: list[Finding]) -> dict[str, Any]:
    ordered: list[Finding] = sorted(findings, key=lambda finding: finding.severity != "error")
    return {
        "errors": count_errors(findings),
        "warnings": len(findings) - count_errors(findings),
        "findings": findings_to_json(ordered[:MAX_FINDINGS_IN_OUTPUT]),
        "more_findings": max(0, len(findings) - MAX_FINDINGS_IN_OUTPUT),
    }


def write_report(game_dir: Path, name: str, payload: dict[str, Any]) -> Path:
    reports: Path = game_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    path: Path = reports / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def optional_report(game_dir: Path, name: str, findings: list[Finding], options: OutputOptions) -> str | None:
    """Write the full report of a verb, unless the options say to write nothing. Return its path as text."""
    if not options.write:
        return None
    return str(write_report(game_dir, name, {"findings": findings_to_json(findings)}))


def input_problem(rule: str, message: str, fix_hint: str) -> Finding:
    """A finding for a bad input of a verb (stdin, a missing earlier step), which no game file causes."""
    return Finding(severity="error", rule=rule, message=message, fix_hint=fix_hint)
