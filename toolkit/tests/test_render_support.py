"""Shared helpers of the render tests: the golden game, assembled with the fake mechanics of `test_assemble.py`."""

from functools import cache
from typing import Any

from test_assemble import FAKE_IMPLEMENTATIONS, GOLDEN_GAME

from mystery_forge.assemble import assemble_game
from mystery_forge.game import AssembledDocument, Game
from mystery_forge.spec.documents import render_markdown
from mystery_forge.spec.models import DocumentMeta, PrintOptions


@cache
def golden_game() -> Game:
    result = assemble_game(GOLDEN_GAME, FAKE_IMPLEMENTATIONS)
    assert result.game is not None, result.findings
    return result.game


def configured(game: Game, top: dict[str, Any] | None = None, **sections: dict[str, Any]) -> Game:
    """Return the game with config values replaced: `top` for top-level keys, one dict per nested section."""
    updates: dict[str, Any] = dict(top or {})
    for section, values in sections.items():
        updates[section] = getattr(game.config, section).model_copy(update=values)
    return game.model_copy(update={"config": game.config.model_copy(update=updates)})


def with_story(game: Game, **values: Any) -> Game:
    return game.model_copy(update={"story": game.story.model_copy(update=values)})


LAMP_SVG: str = (
    '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120">'
    '<rect x="10" y="10" width="180" height="100" fill="none" stroke="currentColor" stroke-width="3"/>'
    '<path d="M100 20 L130 100 L70 100 Z" fill="none" stroke="currentColor" stroke-width="3"/></svg>'
)

# One sample per document kind: the front matter fields and a Markdown body that uses the directives.
SHOWCASE: dict[str, tuple[dict[str, str], str]] = {
    "letter": (
        {"letterhead": "Gull Rock Harbour Office", "place": "Port Wren", "date": "15 March 1931", "recipient": "Tom"},
        "Dear Tom,\n\nThe lens must be found.\n\n::: handwriting\nE. Lowe\n:::",
    ),
    "notebook": ({"owner": "T. Bell", "date": "14 March"}, "Wind from the west.\n\n::: note\nCheck the tide!\n:::"),
    "receipt": ({"shop": "Ward Supplies", "address": "Quay Street 4", "number": "0042", "total": "£3 2s"}, "Oil: 7"),
    "police-report": (
        {"station": "Port Wren Police", "case_number": "31/114", "officer": "Sgt. Hale", "subject": "Lens"},
        "The keeper says he slept.\n\n::: stamp\nFiled\n:::",
    ),
    "newspaper": (
        {
            "masthead": "The Wren Gazette",
            "date": "16 March 1931",
            "edition": "Morning",
            "price": "1d",
            "headline": "Lighthouse Goes Dark",
            "subheadline": "Great lens stolen in the night",
        },
        "Ships were nearly lost.\n\nThe harbour master asks for help.",
    ),
    "telegram": ({"sender": "Lowe", "recipient": "Inspector Price", "place": "Port Wren"}, "LENS GONE STOP COME"),
    "transcript": (
        {"case_number": "31/114", "subject": "Ana Ruiz", "interviewer": "Sgt. Hale", "date": "15 March"},
        "HALE: Where were you?\nANA: In the kitchen.\n\nShe looks at the window.",
    ),
    "email": ({"from": "ana@rock.example", "to": "tom@rock.example", "date": "Monday", "subject": "Bread"}, "Hi!"),
    "chat-log": ({"contact": "Felix", "owner": "Tom", "date": "Saturday"}, "Felix: On my way.\nTom: Be quick."),
    "ticket": (
        {
            "issuer": "Wren Ferries",
            "passenger": "M. Price",
            "from": "Port Wren",
            "to": "Gull Rock",
            "date": "15 March",
            "time": "08:15",
            "seat": "4",
            "number": "77",
            "price": "6d",
        },
        "Return valid one day.",
    ),
    "id-card": ({"issuer": "Coast Service", "name": "Maud Price", "role": "Inspector", "number": "C-12"}, "Signed."),
    "map": ({"place": "Gull Rock", "scale": "1:500"}, "{{image:lamp|The rock}}\n\n- A: the tower\n- B: the boathouse"),
    "photo": ({"caption": "The empty lamp room", "date": "15.3.31"}, "{{image:lamp|}}"),
    "poster": ({"issuer": "Harbour Office", "headline": "Wanted", "reward": "£50"}, "Information about the lens."),
    "form": ({"issuer": "Coast Service", "form_number": "C-7", "date": "15 March"}, "Boat: Wren\n\nCargo: oil, rope"),
    "case-briefing": (
        {"agency": "Coast Service", "case_number": "31/114", "classification": "Secret", "recipient": "You"},
        "Read every paper.\n\n::: redacted\nhidden words\n:::\n\n::: pagebreak\n:::\n\nSecond page.",
    ),
    "generic": ({}, "::: center\nCentered\n:::\n\n::: small\nSmall print\n:::\n\n::: typewriter\nTyped\n:::"),
}


def showcase_game() -> Game:
    """The golden game plus one document per kind in stage A, with an image, cut and fold notes, and two pages."""
    game = golden_game()
    documents = list(game.documents)
    for number, (kind, (fields, body)) in enumerate(SHOWCASE.items(), start=10):
        meta = DocumentMeta(
            format_version=1,
            id=f"D{number}",
            kind=kind,
            stage="A",
            title=f"A sample {kind}",
            fields=fields,
            print=PrintOptions(cut=kind == "ticket", fold=kind == "letter", note="Keep flat" if kind == "map" else ""),
            copies=2 if kind == "receipt" else 1,
            order=number,
        )
        resolved = body.replace("{{image:lamp|The rock}}", "⟦image:lamp|The rock⟧").replace(
            "{{image:lamp|}}", "⟦image:lamp|⟧"
        )
        rendered = render_markdown(resolved, f"documents/D{number}.md", 1)
        documents.append(
            AssembledDocument(meta=meta, file=f"documents/D{number}.md", body_html=rendered.html, text=rendered.text)
        )
    return game.model_copy(update={"documents": documents, "images": {"lamp": LAMP_SVG}})


def test_the_golden_game_helper_assembles() -> None:
    assert golden_game().story.title == "The Lens of Gull Rock"
    changed = configured(golden_game(), {"host": "game_master"}, equipment={"paper": "Letter"})
    assert changed.config.host == "game_master"
    assert changed.config.equipment.paper == "Letter"
    assert with_story(golden_game(), visual_style="noir").story.visual_style == "noir"
