"""Output helpers of the `forge` verbs: one JSON object per run, capped findings, and report files."""

import json
from pathlib import Path
from typing import Any, TextIO

from mystery_forge.findings import Finding, count_errors, findings_to_json

MAX_FINDINGS_IN_OUTPUT: int = 20


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
