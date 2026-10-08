"""Typed models of the catalog files: puzzle mechanics, story ingredients, and evidence types.

The catalog keeps generated games varied and well designed. Code reads it to draw story ingredients, to pick
mechanic candidates, and to check variety and time budgets. The validators here reject a catalog edit that would
break those rules, so a bad entry fails the tests and never reaches a game.
"""

from collections.abc import Iterable
from typing import Annotated, Literal, Self, get_args

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StringConstraints, model_validator

Difficulty = Literal["easy", "medium", "hard", "expert"]
Audience = Literal["kids", "family", "teens", "adults", "puzzle_fans"]
Tone = Literal["cozy", "adventure", "noir", "spooky", "comedic", "dramatic"]
# The config formats, without "both": a "both" game may use any entry of either format.
GameFormat = Literal["envelopes", "case_file"]
EraGroup = Literal["historical", "modern", "future", "fantasy"]
MechanicCategory = Literal[
    "cipher", "wordplay", "logic", "observation", "spatial", "math", "cross-reference", "meta", "deduction"
]
PlayerAction = Literal[
    "decode",
    "search",
    "spatial",
    "logic",
    "wordplay",
    "arithmetic",
    "physical",
    "cross-reference",
    "deduction",
    "observation",
]
AnswerKind = Literal["word", "phrase", "number", "digits", "name", "choice"]
# built: code builds the material from the answer. verified: code checks material that the agent wrote.
# panel: only the AI solver panel can check it. See adr/0004-verification-strategy.md.
Verification = Literal["built", "verified", "panel"]
# A mirror reads mirror writing; a light (a bright window or a lamp) shines through stacked pages.
NeededItem = Literal["mirror", "light"]

DIFFICULTY_LEVELS: tuple[Difficulty, ...] = get_args(Difficulty)

KebabId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def require_unique_ids(ids: Iterable[str], list_name: str) -> None:
    seen: set[str] = set()
    for entry_id in ids:
        if entry_id in seen:
            raise ValueError(f"The id '{entry_id}' appears twice in '{list_name}'.")
        seen.add(entry_id)


class CraftNeeds(CatalogModel):
    scissors: bool
    tape: bool
    fold: bool
    # True only when the mechanic cannot work in black and white.
    color: bool
    # What players need beyond paper and pencils, for the manual's "What you need" list.
    items: list[NeededItem] = []


class DifficultyRange(CatalogModel):
    min: Difficulty
    max: Difficulty

    @model_validator(mode="after")
    def check_order(self) -> Self:
        if DIFFICULTY_LEVELS.index(self.min) > DIFFICULTY_LEVELS.index(self.max):
            raise ValueError(f"The difficulty min '{self.min}' is above the max '{self.max}'.")
        return self


class MinutesByDifficulty(CatalogModel):
    """Baseline minutes for a group of 3 or 4 players, by difficulty level."""

    easy: PositiveInt
    medium: PositiveInt
    hard: PositiveInt
    expert: PositiveInt

    def for_level(self, level: Difficulty) -> int:
        minutes: int = getattr(self, level)
        return minutes

    @model_validator(mode="after")
    def check_non_decreasing(self) -> Self:
        values: list[int] = [self.for_level(level) for level in DIFFICULTY_LEVELS]
        if values != sorted(values):
            raise ValueError(f"Minutes must be non-decreasing from easy to expert, got {values}.")
        return self


class Mechanic(CatalogModel):
    id: KebabId
    name: Text
    category: MechanicCategory
    player_action: PlayerAction
    # The variety check allows at most 2 lookup ciphers (a symbol or letter table) per game.
    lookup_cipher: bool
    summary: Text
    how_it_works: Text
    material: Text
    answer_kinds: Annotated[tuple[AnswerKind, ...], Field(min_length=1)]
    needs: CraftNeeds
    solo: bool
    parallel: bool
    audiences: Annotated[tuple[Audience, ...], Field(min_length=1)]
    difficulty: DifficultyRange
    minutes: MinutesByDifficulty
    verification: Verification
    builder: KebabId | None
    pitfalls: Annotated[tuple[Text, ...], Field(min_length=1)]
    # Hint 1: what you need and where to look. Hint 2: a nudge to the method. Hint 3: the method.
    hint_ladder: tuple[Text, Text, Text]
    in_world_examples: Annotated[tuple[Text, ...], Field(min_length=2, max_length=4)]
    combines_documents: bool
    # The builder folds text to the letters A to Z, or fills a grid with them, so it fits only a Latin-script language.
    latin_letters: bool = False
    # The builder writes sentences in the game language, so it fits only a language with a checked table.
    writes_sentences: bool = False

    @model_validator(mode="after")
    def check_rules(self) -> Self:
        if self.verification == "panel" and self.builder is not None:
            raise ValueError(f"'{self.id}' uses the panel, so its builder must be null.")
        if self.verification != "panel" and self.builder != self.id:
            raise ValueError(f"'{self.id}' is {self.verification}, so its builder must be '{self.id}'.")
        if self.lookup_cipher and self.category != "cipher":
            raise ValueError(f"'{self.id}' sets lookup_cipher, but its category is '{self.category}', not 'cipher'.")
        return self


class MechanicCatalog(CatalogModel):
    mechanics: tuple[Mechanic, ...]

    @model_validator(mode="after")
    def check_unique_ids(self) -> Self:
        require_unique_ids((mechanic.id for mechanic in self.mechanics), "mechanics")
        return self


class Era(CatalogModel):
    id: KebabId
    name: Text
    # The config's era choice ("any" matches every group).
    group: EraGroup
    details: Text


class Setting(CatalogModel):
    id: KebabId
    name: Text
    era_hints: Annotated[tuple[KebabId, ...], Field(min_length=1)]
    audiences: Annotated[tuple[Audience, ...], Field(min_length=1)]
    tones: Annotated[tuple[Tone, ...], Field(min_length=1)]


class Goal(CatalogModel):
    id: KebabId
    name: Text
    description: Text
    formats: Annotated[tuple[GameFormat, ...], Field(min_length=1)]
    audiences: Annotated[tuple[Audience, ...], Field(min_length=1)]


class Twist(CatalogModel):
    id: KebabId
    name: Text
    description: Text
    formats: Annotated[tuple[GameFormat, ...], Field(min_length=1)]
    audiences: Annotated[tuple[Audience, ...], Field(min_length=1)]


class Frame(CatalogModel):
    id: KebabId
    name: Text
    description: Text
    audiences: Annotated[tuple[Audience, ...], Field(min_length=1)]


class ToneGuide(CatalogModel):
    id: Tone
    name: Text
    description: Text


class Motif(CatalogModel):
    id: KebabId
    name: Text
    puzzle_skins: Text


class Cliches(CatalogModel):
    names: Annotated[tuple[Text, ...], Field(min_length=1)]
    phrases: Annotated[tuple[Text, ...], Field(min_length=1)]
    plots: Annotated[tuple[Text, ...], Field(min_length=1)]


class AudienceRule(CatalogModel):
    max_words_per_document: PositiveInt
    allow_murder: bool
    themes_to_avoid: tuple[Text, ...]
    decoders_preprinted: bool
    notes: Text


class Ingredients(CatalogModel):
    settings: tuple[Setting, ...]
    eras: tuple[Era, ...]
    goals: tuple[Goal, ...]
    twists: tuple[Twist, ...]
    frames: tuple[Frame, ...]
    tones: tuple[ToneGuide, ...]
    motifs: tuple[Motif, ...]
    cliches: Cliches
    audience_rules: dict[Audience, AudienceRule]

    @model_validator(mode="after")
    def check_decks(self) -> Self:
        ids_by_deck: dict[str, list[str]] = {
            "settings": [setting.id for setting in self.settings],
            "eras": [era.id for era in self.eras],
            "goals": [goal.id for goal in self.goals],
            "twists": [twist.id for twist in self.twists],
            "frames": [frame.id for frame in self.frames],
            "tones": [tone.id for tone in self.tones],
            "motifs": [motif.id for motif in self.motifs],
        }
        for list_name, ids in ids_by_deck.items():
            require_unique_ids(ids, list_name)
        era_ids: set[str] = {era.id for era in self.eras}
        for setting in self.settings:
            unknown_eras: list[str] = [era for era in setting.era_hints if era not in era_ids]
            if unknown_eras:
                raise ValueError(f"Setting '{setting.id}' names unknown eras: {', '.join(unknown_eras)}.")
        missing_tones: set[str] = set(get_args(Tone)) - {tone.id for tone in self.tones}
        if missing_tones:
            raise ValueError(f"The tones list misses: {', '.join(sorted(missing_tones))}.")
        missing_audiences: set[str] = set(get_args(Audience)) - set(self.audience_rules)
        if missing_audiences:
            raise ValueError(f"The audience_rules miss: {', '.join(sorted(missing_audiences))}.")
        return self


class EvidenceType(CatalogModel):
    id: KebabId
    name: Text
    carries: Text
    realism_tips: Annotated[tuple[Text, ...], Field(min_length=1)]
    typical_fields: Annotated[tuple[Text, ...], Field(min_length=1)]


class EvidenceCatalog(CatalogModel):
    evidence_types: tuple[EvidenceType, ...]

    @model_validator(mode="after")
    def check_unique_ids(self) -> Self:
        require_unique_ids((evidence_type.id for evidence_type in self.evidence_types), "evidence_types")
        return self
