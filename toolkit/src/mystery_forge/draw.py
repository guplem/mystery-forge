"""The seeded draw of story ingredients and puzzle mechanic candidates for one game.

LLMs fall back to the same stories (a foggy murder, a secret diary) and the same puzzles (one more cipher). A random
draw from the catalog decks, filtered by the config, gives each game a different starting point, and the writers must
use the drawn cards. The draw is deterministic for a seed, so a run can be replayed.
"""

import random
from collections.abc import Callable, Sequence

from pydantic import BaseModel, ConfigDict

from mystery_forge.brief import Brief
from mystery_forge.catalog.loader import load_ingredients, load_mechanics
from mystery_forge.catalog.models import (
    AudienceRule,
    Cliches,
    Frame,
    Goal,
    Ingredients,
    Mechanic,
    Motif,
    Setting,
    ToneGuide,
    Twist,
)
from mystery_forge.config import GameConfig
from mystery_forge.i18n import LANGUAGES, NON_LATIN_LANGUAGES

SETTING_COUNT: int = 3
GOAL_COUNT: int = 2
TWIST_COUNT: int = 3
FRAME_COUNT: int = 2
MOTIF_COUNT: int = 2
MIN_MECHANIC_CANDIDATES: int = 12
MAX_LOOKUP_CIPHER_CANDIDATES: int = 3
DIFFICULTY_ORDER: tuple[str, ...] = ("easy", "medium", "hard", "expert")
PREFERENCE_WEIGHT: dict[str, int] = {"like": 3, "neutral": 1}

# Which config preference covers which catalog category.
CATEGORY_PREFERENCE: dict[str, str] = {
    "cipher": "words",
    "wordplay": "words",
    "math": "numbers",
    "logic": "logic",
    "observation": "visual",
    "spatial": "visual",
    "deduction": "deduction",
    "cross-reference": "deduction",
    "meta": "logic",
}


class CandidateMechanic(BaseModel):
    """A mechanic that the puzzle planner may use, with the numbers it needs to plan."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    category: str
    player_action: str
    verification: str
    summary: str
    minutes: int


class Draw(BaseModel):
    model_config = ConfigDict(frozen=True)

    tone: ToneGuide
    settings: tuple[Setting, ...]
    goals: tuple[Goal, ...]
    twists: tuple[Twist, ...]
    frames: tuple[Frame, ...]
    motifs: tuple[Motif, ...]
    cliches: Cliches
    audience_rule: AudienceRule
    mechanics: tuple[CandidateMechanic, ...]


def draw_ingredients(
    config: GameConfig,
    brief: Brief,
    implemented_builders: frozenset[str],
    avoid_settings: frozenset[str] = frozenset(),
) -> Draw:
    """Draw the cards for one game. `avoid_settings` holds the settings of recent games, so they do not repeat."""
    generator: random.Random = random.Random(brief.seed)
    ingredients: Ingredients = load_ingredients()
    tone: ToneGuide = pick_tone(config, ingredients, generator)
    era_ids: frozenset[str] = era_ids_for(config, ingredients)
    settings = draw_cards(
        ingredients.settings,
        SETTING_COUNT,
        generator,
        # Most important filter first: the draw drops filters from the end when too few cards fit.
        [
            lambda setting: config.audience in setting.audiences,
            lambda setting: not era_ids or bool(era_ids & set(setting.era_hints)),
            lambda setting: tone.id in setting.tones,
            lambda setting: setting.id not in avoid_settings,
        ],
    )
    formats: frozenset[str] = frozenset({"envelopes", "case_file"} if config.format == "both" else {config.format})
    goals = draw_cards(
        ingredients.goals,
        GOAL_COUNT,
        generator,
        [lambda goal: config.audience in goal.audiences, lambda goal: bool(formats & set(goal.formats))],
    )
    twists = draw_cards(
        ingredients.twists,
        TWIST_COUNT,
        generator,
        [lambda twist: config.audience in twist.audiences, lambda twist: bool(formats & set(twist.formats))],
    )
    frames = draw_cards(ingredients.frames, FRAME_COUNT, generator, [lambda frame: config.audience in frame.audiences])
    motifs = draw_cards(ingredients.motifs, MOTIF_COUNT, generator, [])
    return Draw(
        tone=tone,
        settings=settings,
        goals=goals,
        twists=twists,
        frames=frames,
        motifs=motifs,
        cliches=ingredients.cliches,
        audience_rule=ingredients.audience_rules[config.audience],
        mechanics=draw_mechanics(config, brief, implemented_builders, generator),
    )


def pick_tone(config: GameConfig, ingredients: Ingredients, generator: random.Random) -> ToneGuide:
    tones: dict[str, ToneGuide] = {tone.id: tone for tone in ingredients.tones}
    if config.theme.tone == "surprise":
        return tones[generator.choice(sorted(tones))]
    return tones[config.theme.tone]


def era_ids_for(config: GameConfig, ingredients: Ingredients) -> frozenset[str]:
    if config.theme.era == "any":
        return frozenset()
    return frozenset(era.id for era in ingredients.eras if era.group == config.theme.era)


def draw_cards[Card](
    deck: Sequence[Card], count: int, generator: random.Random, filters: list[Callable[[Card], bool]]
) -> tuple[Card, ...]:
    """Draw `count` distinct cards. When the filters leave too few cards, drop the last filter and try again."""
    for active in range(len(filters), -1, -1):
        fitting: list[Card] = [card for card in deck if all(rule(card) for rule in filters[:active])]
        if len(fitting) >= count:
            return tuple(generator.sample(fitting, count))
    return tuple(generator.sample(list(deck), min(count, len(deck))))


def mechanic_fits(
    mechanic: Mechanic, config: GameConfig, implemented_builders: frozenset[str], difficulty: str | None = None
) -> bool:
    """True when the config allows the mechanic and code can build or check it (or only the panel checks it).

    `difficulty` is the puzzle's own difficulty; it defaults to the game's difficulty.
    """
    if mechanic.verification != "panel" and mechanic.builder not in implemented_builders:
        return False
    equipment = config.equipment
    if (mechanic.needs.scissors and not equipment.scissors) or (mechanic.needs.tape and not equipment.tape_or_glue):
        return False
    if mechanic.needs.color and equipment.printer == "black_and_white":
        return False
    if config.audience not in mechanic.audiences:
        return False
    if mechanic.latin_letters and config.language in NON_LATIN_LANGUAGES:
        return False
    if mechanic.writes_sentences and config.language not in LANGUAGES:
        return False
    level: int = DIFFICULTY_ORDER.index(difficulty or config.difficulty)
    if not DIFFICULTY_ORDER.index(mechanic.difficulty.min) <= level <= DIFFICULTY_ORDER.index(mechanic.difficulty.max):
        return False
    return preference_of(mechanic, config) != "avoid"


def preference_of(mechanic: Mechanic, config: GameConfig) -> str:
    preferences = config.puzzle_preferences
    if (mechanic.needs.scissors or mechanic.needs.tape or mechanic.needs.fold) and preferences.crafts == "avoid":
        return "avoid"
    key: str = CATEGORY_PREFERENCE[mechanic.category]
    preference: str = getattr(preferences, key)
    return preference


def draw_mechanics(
    config: GameConfig, brief: Brief, implemented_builders: frozenset[str], generator: random.Random
) -> tuple[CandidateMechanic, ...]:
    """Pick about twice the needed puzzles, one player action at a time, so the candidates stay varied."""
    pool: list[Mechanic] = [
        mechanic for mechanic in load_mechanics() if mechanic_fits(mechanic, config, implemented_builders)
    ]
    target: int = max(MIN_MECHANIC_CANDIDATES, brief.puzzle_count * 2)
    by_action: dict[str, list[Mechanic]] = {}
    for mechanic in pool:
        by_action.setdefault(mechanic.player_action, []).append(mechanic)
    actions: list[str] = sorted(by_action)
    generator.shuffle(actions)
    chosen: list[Mechanic] = []
    lookup_ciphers: int = 0
    while len(chosen) < target and any(by_action.values()):
        for action in actions:
            remaining: list[Mechanic] = by_action[action]
            if not remaining or len(chosen) >= target:
                continue
            weights: list[int] = [PREFERENCE_WEIGHT[preference_of(mechanic, config)] for mechanic in remaining]
            picked: Mechanic = generator.choices(remaining, weights=weights)[0]
            remaining.remove(picked)
            if picked.lookup_cipher:
                if lookup_ciphers >= MAX_LOOKUP_CIPHER_CANDIDATES:
                    continue
                lookup_ciphers += 1
            chosen.append(picked)
    return tuple(candidate_from(mechanic, config) for mechanic in chosen)


def candidate_from(mechanic: Mechanic, config: GameConfig) -> CandidateMechanic:
    return CandidateMechanic(
        id=mechanic.id,
        name=mechanic.name,
        category=mechanic.category,
        player_action=mechanic.player_action,
        verification=mechanic.verification,
        summary=mechanic.summary,
        minutes=getattr(mechanic.minutes, config.difficulty),
    )
