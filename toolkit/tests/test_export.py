from pathlib import Path

import pytest

from mystery_forge.export import ExportError, export_game, output_root, warnings_text
from mystery_forge.render.sheets import OutputFileNames, output_file_names
from mystery_forge.verification import ExportProblem

ENGLISH: OutputFileNames = output_file_names("en")


def make_render(folder: Path, names: OutputFileNames = ENGLISH, companion: bool = True, hints: bool = True) -> Path:
    folder.mkdir(parents=True)
    for output, name in names.pdfs.items():
        if hints or output != "hints":
            (folder / name).write_bytes(b"%PDF-1.7")
    (folder / "manual.html").write_text("<html></html>", encoding="utf-8")
    if companion:
        (folder / names.companion).write_text("<html></html>", encoding="utf-8")
    return folder


def test_export_copies_the_player_files_and_hides_the_spoilers(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render")
    result = export_game(render_dir, tmp_path / "out", 'The Lens: "Gull Rock"?', ENGLISH)
    assert result.folder == tmp_path / "out" / "The Lens - Gull Rock"
    assert result.files == [
        "1 - START HERE (manual).pdf",
        "2 - PRINT THIS (game materials).pdf",
        "Game companion.html",
        "HOST ONLY - spoilers/3 - Hints.pdf",
        "HOST ONLY - spoilers/4 - Solutions.pdf",
    ]
    for relative in result.files:
        assert (result.folder / relative).is_file()
    assert not (result.folder / "manual.html").exists()


def test_export_keeps_the_names_of_the_game_language(tmp_path: Path) -> None:
    spanish = output_file_names("es")
    render_dir = make_render(tmp_path / "render", spanish)
    result = export_game(render_dir, tmp_path / "out", "El faro", spanish)
    assert result.files == [
        "1 - EMPIEZA AQUÍ (manual).pdf",
        "2 - IMPRIME ESTO (materiales del juego).pdf",
        "Compañero de juego.html",
        "SOLO ANFITRIÓN - spoilers/3 - Pistas.pdf",
        "SOLO ANFITRIÓN - spoilers/4 - Soluciones.pdf",
    ]
    for relative in result.files:
        assert (result.folder / relative).is_file()


def test_export_never_overwrites_an_earlier_export(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render")
    first = export_game(render_dir, tmp_path / "out", "Same Title", ENGLISH)
    second = export_game(render_dir, tmp_path / "out", "Same Title", ENGLISH)
    assert first.folder != second.folder
    assert second.folder.name == "Same Title (2)"


def test_export_without_a_companion_page(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render", companion=False)
    result = export_game(render_dir, tmp_path / "out", "No Phone", ENGLISH)
    assert "Game companion.html" not in result.files


def test_export_of_a_game_without_hints(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render", hints=False)
    result = export_game(render_dir, tmp_path / "out", "No Hints", ENGLISH)
    assert result.files[-1] == "HOST ONLY - spoilers/4 - Solutions.pdf"
    assert "HOST ONLY - spoilers/3 - Hints.pdf" not in result.files


def test_export_needs_the_pdfs(tmp_path: Path) -> None:
    (tmp_path / "render").mkdir()
    with pytest.raises(ExportError, match="START HERE"):
        export_game(tmp_path / "render", tmp_path / "out", "Missing", ENGLISH)


def test_output_root_is_the_config_folder_or_the_desktop(tmp_path: Path) -> None:
    assert output_root("", tmp_path / "Desktop") == tmp_path / "Desktop" / "Mystery Forge"
    assert output_root(str(tmp_path / "Games"), tmp_path / "Desktop") == tmp_path / "Games"


def test_a_game_with_problems_gets_a_warnings_file_first(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render")
    problems = [
        ExportProblem("B1", "checks_stale"),
        ExportProblem("B1", "ambiguous"),
        ExportProblem("deduction", "puzzles_not_needed"),
    ]
    result = export_game(render_dir, tmp_path / "out", "Flawed", ENGLISH, warnings_text(problems, "en"))
    assert result.files[0] == "0 - READ FIRST (warnings).txt"
    warnings = (result.folder / result.files[0]).read_text(encoding="utf-8-sig")
    assert warnings.startswith("Read this before you play\n")
    assert (
        "- Puzzle B1: the automatic checks did not run after the last change. The test players found more than one "
        "answer that fits."
    ) in warnings
    assert "- Accusation form: the test players could answer it without solving the puzzles." in warnings
    assert "type 4" in warnings


def test_the_warnings_follow_the_game_language() -> None:
    spanish = warnings_text([ExportProblem("A2", "too_hard")], "es")
    assert "- Enigma A2: los jugadores de prueba no lo pudieron resolver." in spanish
    assert output_file_names("ca").warnings == "0 - LLEGEIX AIXÒ PRIMER (avisos).txt"


def test_a_clean_game_gets_no_warnings_file(tmp_path: Path) -> None:
    assert warnings_text([], "en") == ""
    result = export_game(make_render(tmp_path / "render"), tmp_path / "out", "Clean", ENGLISH, "")
    assert not any(name.startswith("0 - ") for name in result.files)
    assert not list(result.folder.glob("*.txt"))
