"""The assembled game: the one validated model that the checks, the panel, and the renderer read (`game.json`)."""

from pydantic import BaseModel, ConfigDict

from mystery_forge.brief import Brief
from mystery_forge.config import GameConfig
from mystery_forge.mechanics.base import Artifact
from mystery_forge.spec.models import DocumentMeta, Flow, Puzzle, Story


class AssembledPuzzle(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Puzzle
    file: str
    # The code printed on every material of the puzzle and on its hint cards, such as "B2".
    code: str
    # None when the mechanic is unknown or its build failed; the assembly then has a finding for it.
    artifact: Artifact | None
    # The normalized answer first, then the normalized accepted variants, without repeats.
    accepted_normalized: list[str]


class AssembledDocument(BaseModel):
    model_config = ConfigDict(frozen=True)

    meta: DocumentMeta
    file: str
    # The body as HTML, with artifact and image marks that the renderer replaces.
    body_html: str
    # The visible text, with each artifact as its solver text and each image as a caption.
    text: str


class Game(BaseModel):
    model_config = ConfigDict(frozen=True)

    config: GameConfig
    brief: Brief
    story: Story
    flow: Flow
    puzzles: list[AssembledPuzzle]
    documents: list[AssembledDocument]
    images: dict[str, str]
    # Mixed into every answer hash of the companion page, so that one game's hashes do not work for another game.
    salt: str
