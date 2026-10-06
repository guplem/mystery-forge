import pytest
from test_checks_support import edit_document, edit_story, golden_game, rules

from mystery_forge.checks.fact_registry import check_fact_registry, edit_distance
from mystery_forge.game import Game
from mystery_forge.spec.models import Character, StoryObject, TimelineEvent


def with_d2_text(extra: str, game: Game | None = None) -> Game:
    base: Game = game or golden_game()
    return edit_document(base, "D2", text=f"{base.documents[1].text}\n\n{extra}")


def with_events(*events: TimelineEvent) -> Game:
    return edit_story(golden_game(), timeline=[*golden_game().story.timeline, *events])


def test_the_golden_registry_has_no_findings() -> None:
    assert check_fact_registry(golden_game()) == []


def test_edit_distance_counts_single_letter_edits() -> None:
    assert edit_distance("margret hale", "margaret hale") == 1
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("", "abc") == 3


def test_a_near_spelling_of_a_registry_name_is_a_warning_once_per_document() -> None:
    findings = check_fact_registry(with_d2_text("Then Felx Ward left. Felx Ward came back."))
    assert rules(findings) == ["registry.near_duplicate_name"]
    assert (findings[0].file, findings[0].severity) == ("documents/D2.md", "warning")
    assert "'Felx Ward'" in findings[0].message
    assert "'Felix Ward'" in findings[0].message


def test_an_alias_is_an_exact_name() -> None:
    characters: list[Character] = list(golden_game().story.characters)
    characters[2] = characters[2].model_copy(update={"aliases": ["Felx Ward"]})
    game: Game = edit_story(golden_game(), characters=characters)
    assert check_fact_registry(with_d2_text("Felx Ward rowed.", game)) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The Opel shines.", ["registry.near_duplicate_name"]),
        ("The Goal shines.", []),
        ("The Bob sails.", []),
        ("Felx, Ward and Tom.", []),
        ("Felx\nWard", []),
        ("Felipe Wardrobe", []),
    ],
)
def test_short_names_need_a_closer_match_and_sequences_stop_at_punctuation(text: str, expected: list[str]) -> None:
    objects: list[StoryObject] = [
        StoryObject(id="opal", name="Opal", description="A gem."),
        StoryObject(id="bo", name="Bo", description="A dog."),
    ]
    game: Game = edit_story(golden_game(), objects=objects)
    assert rules(check_fact_registry(with_d2_text(text, game))) == expected


def test_the_closest_registry_name_is_named() -> None:
    characters: list[Character] = [
        *golden_game().story.characters,
        Character(id="maud-pryce", name="Maud Pryde", role="twin", description="Her twin."),
    ]
    game: Game = edit_story(golden_game(), characters=characters)
    findings = check_fact_registry(with_d2_text("Maud Pryse waved.", game))
    assert len(findings) == 1
    assert "'Maud Pryde'" in findings[0].message


def test_an_unknown_participant_or_location_is_an_error() -> None:
    ghost = TimelineEvent(
        id="ghost", start="1931-03-14 20:00", location="attic", participants=["nobody"], description="x"
    )
    findings = check_fact_registry(with_events(ghost))
    assert rules(findings) == ["registry.unknown_participant", "registry.unknown_location"]
    assert [finding.path for finding in findings] == ["timeline.4.participants.0", "timeline.4.location"]


@pytest.mark.parametrize(
    ("start", "end", "location", "conflict"),
    [
        ("1931-03-15 02:00", "1931-03-15 03:00", "kitchen", True),
        ("1931-03-15 02:30", "1931-03-15 03:00", "kitchen", False),
        ("1931-03-15 02:00", None, "kitchen", True),
        ("1931-03-15 02:30", None, "kitchen", False),
        ("1931-03-15 02:00", "1931-03-15 03:00", "lamp-room", False),
        ("1931-03-15 02:00", "1931-03-15 03:00", None, False),
    ],
)
def test_nobody_can_be_in_two_places_at_once(start: str, end: str | None, location: str | None, conflict: bool) -> None:
    event = TimelineEvent(
        id="second-trip", start=start, end=end, location=location, participants=["felix-ward"], description="x"
    )
    findings = check_fact_registry(with_events(event))
    assert rules(findings) == (["registry.two_places"] if conflict else [])
    if conflict:
        assert (findings[0].file, findings[0].path, findings[0].severity) == ("story.yaml", "timeline.4", "error")
        assert "Felix Ward" in findings[0].message


def test_two_moments_conflict_only_at_the_same_time() -> None:
    same_time = TimelineEvent(
        id="call", start="1931-03-15 09:00", location="kitchen", participants=["tom-bell"], description="x"
    )
    assert rules(check_fact_registry(with_events(same_time))) == ["registry.two_places"]
    later = same_time.model_copy(update={"start": "1931-03-15 09:05"})
    assert check_fact_registry(with_events(later)) == []


def test_an_unknown_participant_in_two_places_is_named_by_id() -> None:
    first = TimelineEvent(
        id="one", start="1931-03-16 10:00", location="kitchen", participants=["stranger"], description="x"
    )
    second = first.model_copy(update={"id": "two", "location": "boathouse"})
    findings = check_fact_registry(with_events(first, second))
    assert "registry.two_places" in rules(findings)
    assert "stranger" in findings[-1].message
