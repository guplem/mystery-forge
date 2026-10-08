"""The double-click launchers are thin glue: these tests pin what each one must do, on every operating system."""

from pathlib import Path

import pytest

ROOT: Path = Path(__file__).resolve().parents[2]
WINDOWS_LAUNCHER: Path = ROOT / "Start Mystery Forge.cmd"
MAC_LAUNCHER: Path = ROOT / "Start Mystery Forge.command"


@pytest.mark.parametrize("launcher", [WINDOWS_LAUNCHER, MAC_LAUNCHER])
def test_a_launcher_installs_the_tools_and_starts_the_agent_in_the_generator_folder(launcher: Path) -> None:
    text: str = launcher.read_text(encoding="utf-8")
    assert "astral.sh/uv/install" in text
    assert "claude.ai/install" in text
    assert "configurator" in text and "index.html" in text
    assert "generator" in text
    assert 'claude "create a game"' in text
    assert 'claude "continue"' in text
    # Option 4 opens the AI with no request, to change a finished game.
    assert "4  Talk to the AI" in text


def test_the_windows_launcher_keeps_windows_line_endings() -> None:
    """cmd.exe can misread labels in a file with Unix line endings, so .gitattributes keeps CRLF for .cmd files."""
    content: bytes = WINDOWS_LAUNCHER.read_bytes()
    assert b"\r\n" in content
    assert content.count(b"\n") == content.count(b"\r\n")


def test_the_mac_launcher_is_a_bash_script() -> None:
    assert MAC_LAUNCHER.read_text(encoding="utf-8").startswith("#!/bin/bash\n")
