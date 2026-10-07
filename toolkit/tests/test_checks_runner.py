from test_checks_support import edit_document, golden_catalog, golden_game, rules

from mystery_forge.checks import CHECK_PREFIXES, run_checks, sort_findings
from mystery_forge.findings import Finding, count_errors
from mystery_forge.game import Game

GOLDEN_WARNINGS: list[tuple[str, str | None]] = [
    ("variety.cross_document", None),
    ("ledger.hint_ladder_narrows", "puzzles/P1.yaml"),
    ("ledger.hint_ladder_narrows", "puzzles/P2.yaml"),
    ("variety.final_not_meta", "puzzles/P3.yaml"),
]


def test_the_golden_game_has_no_errors_and_known_warnings() -> None:
    findings: list[Finding] = run_checks(golden_game(), golden_catalog())
    assert count_errors(findings) == 0
    assert [(finding.rule, finding.file) for finding in findings] == GOLDEN_WARNINGS


def test_without_a_catalog_the_packaged_catalog_is_used() -> None:
    assert run_checks(golden_game()) == run_checks(golden_game(), golden_catalog())


def test_errors_come_first() -> None:
    game: Game = edit_document(golden_game(), "D5", meta={"kind": "diary"})
    findings: list[Finding] = run_checks(game, golden_catalog())
    assert rules(findings)[0] == "documents.kind_unknown"
    assert [finding.severity for finding in findings] == ["error"] + ["warning"] * len(GOLDEN_WARNINGS)


def test_only_runs_the_checks_and_rules_with_the_given_prefixes() -> None:
    game: Game = edit_document(golden_game(), "D5", meta={"kind": "diary"})
    assert set(rules(run_checks(game, golden_catalog(), only=["ledger"]))) == {"ledger.hint_ladder_narrows"}
    narrowed = run_checks(game, golden_catalog(), only=["ledger.hint_ladder_narrows", "documents"])
    assert rules(narrowed) == ["documents.kind_unknown", "ledger.hint_ladder_narrows", "ledger.hint_ladder_narrows"]
    assert run_checks(game, golden_catalog(), only=["ledger.quote_not_found"]) == []
    assert run_checks(game, golden_catalog(), only=["nothing"]) == []


def test_every_check_family_has_a_prefix() -> None:
    assert CHECK_PREFIXES == (
        "graph",
        "ledger",
        "leaks",
        "hints",
        "registry",
        "deduction",
        "variety",
        "budget",
        "references",
        "documents",
        "images",
    )


def test_findings_sort_by_severity_then_file_then_line() -> None:
    findings: list[Finding] = [
        Finding(severity="warning", rule="w", message="m", file="a.yaml"),
        Finding(severity="error", rule="e2", message="m", file="b.yaml", line=9),
        Finding(severity="error", rule="e1", message="m", file="b.yaml", line=2),
        Finding(severity="error", rule="e0", message="m"),
    ]
    assert rules(sort_findings(findings)) == ["e0", "e1", "e2", "w"]
