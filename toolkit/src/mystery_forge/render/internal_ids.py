"""Replace internal ids in a printed text: a puzzle id (`P3`) prints as its code, a document id (`D7`) as its title.

Players never see the internal ids, so an id in a hint or a solution means nothing to them. A check rejects these
ids in the game files; the renderer still replaces any id that gets through.
"""

import re
from typing import Final

from mystery_forge.game import Game

INTERNAL_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b[PD]\d+\b")


def printed_ids(game: Game, value: str) -> str:
    names: dict[str, str] = {puzzle.source.id: puzzle.code for puzzle in game.puzzles}
    names.update({document.meta.id: document.meta.title for document in game.documents})
    return INTERNAL_ID_PATTERN.sub(lambda match: names.get(match.group(0), match.group(0)), value)
