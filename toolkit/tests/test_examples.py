from pathlib import Path

import pytest

from mystery_forge.config import load_config_file

EXAMPLES: Path = Path(__file__).resolve().parents[2] / "examples" / "configs"


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.mystery-config.json")), ids=lambda path: path.name)
def test_every_example_config_is_valid(path: Path) -> None:
    result = load_config_file(path)
    assert result.findings == []


def test_there_are_example_configs() -> None:
    assert len(list(EXAMPLES.glob("*.mystery-config.json"))) >= 3
