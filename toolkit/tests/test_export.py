from pathlib import Path

import pytest

from mystery_forge.export import SPOILER_FOLDER, ExportError, export_game, output_root


def make_render(folder: Path, companion: bool = True) -> Path:
    folder.mkdir(parents=True)
    for name in (
        "1 - START HERE (manual).pdf",
        "2 - PRINT THIS (game materials).pdf",
        "3 - Hints.pdf",
        "4 - Solutions.pdf",
        "manual.html",
    ):
        (folder / name).write_bytes(b"%PDF-1.7")
    if companion:
        (folder / "Game companion.html").write_text("<html></html>", encoding="utf-8")
    return folder


def test_export_copies_the_player_files_and_hides_the_spoilers(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render")
    result = export_game(render_dir, tmp_path / "out", 'The Lens: "Gull Rock"?')
    assert result.folder == tmp_path / "out" / "The Lens Gull Rock"
    assert result.files == [
        "1 - START HERE (manual).pdf",
        "2 - PRINT THIS (game materials).pdf",
        "Game companion.html",
        f"{SPOILER_FOLDER}/3 - Hints.pdf",
        f"{SPOILER_FOLDER}/4 - Solutions.pdf",
    ]
    for relative in result.files:
        assert (result.folder / relative).is_file()
    assert not (result.folder / "manual.html").exists()


def test_export_never_overwrites_an_earlier_export(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render")
    first = export_game(render_dir, tmp_path / "out", "Same Title")
    second = export_game(render_dir, tmp_path / "out", "Same Title")
    assert first.folder != second.folder
    assert second.folder.name == "Same Title (2)"


def test_export_without_a_companion_page(tmp_path: Path) -> None:
    render_dir = make_render(tmp_path / "render", companion=False)
    result = export_game(render_dir, tmp_path / "out", "No Phone")
    assert "Game companion.html" not in result.files


def test_export_needs_the_pdfs(tmp_path: Path) -> None:
    (tmp_path / "render").mkdir()
    with pytest.raises(ExportError, match="START HERE"):
        export_game(tmp_path / "render", tmp_path / "out", "Missing")


def test_output_root_is_the_config_folder_or_the_desktop(tmp_path: Path) -> None:
    assert output_root("", tmp_path / "Desktop") == tmp_path / "Desktop" / "Mystery Forge"
    assert output_root(str(tmp_path / "Games"), tmp_path / "Desktop") == tmp_path / "Games"
