import shutil
from pathlib import Path

import pytest
from test_assemble import FAKE_IMPLEMENTATIONS, GOLDEN_GAME

from mystery_forge.assemble import assemble_game
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.panel.models import ItemVerdict, PanelReport, Verdict
from mystery_forge.spec.documents import IMAGE_MARK
from mystery_forge.verification import (
    LedgerEntry,
    VerificationLedger,
    export_blockers,
    game_hashes,
    ledger_path,
    load_ledger,
    panel_stages_to_run,
    puzzle_closure_hash,
    record_checks,
    record_panel,
    save_ledger,
    stale_check_codes,
    stale_codes,
    stale_panel_codes,
)

HASHES: dict[str, str] = {"A1": "h1", "B1": "h2", "deduction": "h3"}


@pytest.fixture(scope="module")
def golden_game(tmp_path_factory: pytest.TempPathFactory) -> Game:
    game_dir: Path = tmp_path_factory.mktemp("golden")
    shutil.copytree(GOLDEN_GAME / "source", game_dir / "source")
    game = assemble_game(game_dir, FAKE_IMPLEMENTATIONS).game
    assert game is not None
    return game


def with_document_text(game: Game, document_id: str, text: str) -> Game:
    documents: list[AssembledDocument] = [
        document.model_copy(update={"text": text}) if document.meta.id == document_id else document
        for document in game.documents
    ]
    return game.model_copy(update={"documents": documents})


def item(code: str, verdict: Verdict) -> ItemVerdict:
    return ItemVerdict(
        code=code,
        verdict=verdict,
        solvers=5,
        required=3,
        solves_verified=5,
        guesses=0,
        wrong=[],
        alternatives=[],
        guessable=False,
        notes=[],
    )


def report(puzzles: list[ItemVerdict], questions: list[ItemVerdict]) -> PanelReport:
    return PanelReport(ok=False, puzzles=puzzles, questions=questions, invalid_solvers=[])


def test_the_hashes_cover_every_puzzle_and_the_deduction(golden_game: Game) -> None:
    hashes = game_hashes(golden_game)
    assert list(hashes) == ["A1", "A2", "B1", "deduction"]
    assert all(len(value) == 64 for value in hashes.values())
    assert hashes["A1"] == puzzle_closure_hash(golden_game, "P1")
    assert hashes == game_hashes(golden_game)
    no_deduction = golden_game.model_copy(update={"story": golden_game.story.model_copy(update={"deduction": None})})
    assert "deduction" not in game_hashes(no_deduction)


def test_a_document_change_touches_only_the_puzzles_that_see_it(golden_game: Game) -> None:
    before = game_hashes(golden_game)
    after = game_hashes(with_document_text(golden_game, "D4", "Low tide: 2:10 in the night"))
    assert after["A1"] == before["A1"] and after["A2"] == before["A2"]
    assert after["B1"] != before["B1"]
    assert after["deduction"] != before["deduction"]
    earlier = game_hashes(with_document_text(golden_game, "D1", "Dear friends, hello."))
    assert all(earlier[code] != before[code] for code in before)


def test_a_puzzle_or_registry_change_changes_the_hash(golden_game: Game) -> None:
    before = game_hashes(golden_game)
    puzzles = [
        puzzle.model_copy(update={"source": puzzle.source.model_copy(update={"answer": "0727"})})
        if puzzle.code == "A2"
        else puzzle
        for puzzle in golden_game.puzzles
    ]
    changed = game_hashes(golden_game.model_copy(update={"puzzles": puzzles}))
    assert changed["A2"] != before["A2"] and changed["A1"] == before["A1"]
    # B1 solvers see the answers of stage A in their packet.
    assert changed["B1"] != before["B1"]
    unbuilt = [puzzle.model_copy(update={"artifact": None}) for puzzle in golden_game.puzzles]
    assert game_hashes(golden_game.model_copy(update={"puzzles": unbuilt}))["A1"] != before["A1"]
    story = golden_game.story.model_copy(update={"objects": []})
    registry_changed = game_hashes(golden_game.model_copy(update={"story": story}))
    assert all(registry_changed[code] != before[code] for code in before)


def test_only_the_images_that_a_visible_document_uses_count(golden_game: Game) -> None:
    documents: list[AssembledDocument] = [
        document.model_copy(update={"body_html": document.body_html + IMAGE_MARK.format(image="lamp", caption="A")})
        if document.meta.id == "D4"
        else document
        for document in golden_game.documents
    ]
    game = golden_game.model_copy(update={"documents": documents, "images": {"lamp": "<svg>1</svg>"}})
    redrawn = game.model_copy(update={"images": {"lamp": "<svg>2</svg>"}})
    assert game_hashes(game)["A1"] == game_hashes(redrawn)["A1"]
    assert game_hashes(game)["B1"] != game_hashes(redrawn)["B1"]
    missing = game.model_copy(update={"images": {}})
    assert game_hashes(missing)["B1"] != game_hashes(game)["B1"]


def test_a_missing_or_broken_ledger_loads_empty(tmp_path: Path) -> None:
    path = ledger_path(tmp_path)
    assert path == tmp_path / "reports" / "verification.json"
    assert load_ledger(path) == VerificationLedger()
    path.parent.mkdir()
    path.write_text("{not json", encoding="utf-8")
    assert load_ledger(path) == VerificationLedger()
    path.write_bytes(b"{\xff}")
    assert load_ledger(path) == VerificationLedger()


def test_a_saved_ledger_loads_back(tmp_path: Path) -> None:
    path = ledger_path(tmp_path)
    ledger = record_checks(VerificationLedger(), HASHES, ["A1"])
    save_ledger(path, ledger)
    assert load_ledger(path) == ledger
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_record_checks_keeps_the_hash_of_the_last_pass() -> None:
    ledger = record_checks(VerificationLedger(), HASHES, ["A1", "B1"])
    assert ledger.entries["A1"] == LedgerEntry(checks_hash="h1", checks_pass_hash="h1")
    assert ledger.entries["deduction"] == LedgerEntry(checks_hash="h3")
    ledger = record_checks(ledger, {**HASHES, "B1": "h2b"}, ["A1"])
    assert ledger.entries["B1"] == LedgerEntry(checks_hash="h2b", checks_pass_hash="h2")


def test_record_panel_stores_the_verdicts_and_merges_the_questions() -> None:
    ledger = record_panel(
        VerificationLedger(),
        HASHES,
        report([item("A1", "pass"), item("B1", "ambiguous"), item("Z9", "pass")], [item("who", "pass")]),
    )
    assert ledger.entries["A1"] == LedgerEntry(panel_hash="h1", panel_verdict="pass", panel_pass_hash="h1")
    assert ledger.entries["B1"] == LedgerEntry(panel_hash="h2", panel_verdict="ambiguous")
    assert ledger.entries["deduction"] == LedgerEntry(panel_hash="h3", panel_verdict="pass", panel_pass_hash="h3")
    assert "Z9" not in ledger.entries
    ledger = record_panel(ledger, HASHES, report([], [item("who", "pass"), item("why", "too_hard")]))
    assert ledger.entries["deduction"] == LedgerEntry(panel_hash="h3", panel_verdict="too_hard", panel_pass_hash="h3")
    assert record_panel(ledger, {"A1": "h1"}, report([], [item("who", "pass")])) == ledger


def test_a_story_only_failure_fails_the_deduction_entry() -> None:
    story_only_failure = PanelReport(
        ok=False,
        puzzles=[],
        questions=[item("who", "pass")],
        story_only=[item("who", "puzzles_not_needed")],
        invalid_solvers=[],
    )
    ledger = record_panel(VerificationLedger(), HASHES, story_only_failure)
    assert ledger.entries["deduction"] == LedgerEntry(panel_hash="h3", panel_verdict="puzzles_not_needed")


def test_stale_codes_need_a_pass_on_the_current_hash() -> None:
    assert stale_codes(VerificationLedger(), HASHES) == ["A1", "B1", "deduction"]
    ledger = record_checks(VerificationLedger(), HASHES, ["A1", "B1", "deduction"])
    assert stale_codes(ledger, HASHES, panel_required=False) == []
    assert stale_codes(ledger, HASHES) == ["A1", "B1", "deduction"]
    ledger = record_panel(ledger, HASHES, report([item("A1", "pass"), item("B1", "pass")], [item("who", "pass")]))
    assert stale_codes(ledger, HASHES) == []
    assert stale_codes(ledger, {**HASHES, "B1": "new"}) == ["B1"]


def test_stale_checks_and_stale_panel_codes_are_listed_apart() -> None:
    ledger = record_checks(VerificationLedger(), HASHES, ["A1", "B1"])
    ledger = record_panel(ledger, HASHES, report([item("A1", "pass")], []))
    assert stale_check_codes(ledger, HASHES) == ["deduction"]
    assert stale_panel_codes(ledger, HASHES) == ["B1", "deduction"]


def test_export_blockers_name_failing_and_stale_codes() -> None:
    ledger = record_checks(VerificationLedger(), HASHES, ["A1", "deduction"])
    ledger = record_panel(ledger, HASHES, report([item("A1", "pass"), item("B1", "too_hard")], []))
    blockers = export_blockers(ledger, {**HASHES, "C1": "h4"}, panel_required=True)
    assert [(finding.rule, finding.path) for finding in blockers] == [
        ("verification.failing", "B1"),
        ("verification.failing", "B1"),
        ("verification.stale", "deduction"),
        ("verification.stale", "C1"),
        ("verification.stale", "C1"),
    ]
    assert "too_hard" in blockers[1].message
    assert all(finding.severity == "error" and finding.fix_hint for finding in blockers)
    assert [finding.path for finding in export_blockers(ledger, HASHES, panel_required=False)] == ["B1"]


def test_the_panel_runs_the_stages_that_have_no_pass_on_their_current_content(golden_game: Game) -> None:
    hashes = game_hashes(golden_game)
    assert panel_stages_to_run(golden_game, VerificationLedger()) == {"A", "B", "story-only"}
    passing = PanelReport(
        ok=True,
        puzzles=[item(code, "pass") for code in ("A1", "A2", "B1")],
        questions=[item("who", "pass")],
        invalid_solvers=[],
    )
    ledger = record_panel(VerificationLedger(), hashes, passing)
    assert panel_stages_to_run(golden_game, ledger) == set()
    stale_a2 = record_panel(ledger, {**hashes, "A2": "old"}, report([item("A2", "pass")], []))
    assert panel_stages_to_run(golden_game, stale_a2) == {"A"}
    stale_deduction = record_panel(ledger, {**hashes, "deduction": "old"}, report([], [item("who", "pass")]))
    assert panel_stages_to_run(golden_game, stale_deduction) == {"B", "story-only"}
