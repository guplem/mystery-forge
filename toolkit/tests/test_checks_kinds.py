from test_checks_support import edit_document, golden_game, rules

from mystery_forge.checks.kinds import KNOWN_DOCUMENT_KINDS, check_document_kinds
from mystery_forge.render.kinds import document_kind_ids


def test_the_golden_documents_use_known_kinds() -> None:
    assert check_document_kinds(golden_game()) == []
    assert "case-briefing" in KNOWN_DOCUMENT_KINDS


def test_an_unknown_document_kind_is_an_error() -> None:
    findings = check_document_kinds(edit_document(golden_game(), "D5", meta={"kind": "diary"}))
    assert rules(findings) == ["documents.kind_unknown"]
    assert (findings[0].file, findings[0].path, findings[0].severity) == ("documents/D5.md", "kind", "error")
    assert "notebook" in (findings[0].fix_hint or "")


def test_the_known_kinds_match_the_renderer_templates() -> None:
    assert set(KNOWN_DOCUMENT_KINDS) == document_kind_ids()
