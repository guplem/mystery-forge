from collections.abc import Iterator
from typing import Any

import pytest

from mystery_forge import i18n


@pytest.fixture
def restored_tables() -> Iterator[None]:
    """Remove every language that a test registers, so other tests still see the checked tables only."""
    tables: tuple[dict[str, Any], ...] = (i18n.STRINGS, i18n.MONTHS, i18n.WEEKDAYS, i18n.DATE_PATTERNS)
    before: list[set[str]] = [set(table) for table in tables]
    yield
    for table, keys in zip(tables, before, strict=True):
        for key in set(table) - keys:
            del table[key]
