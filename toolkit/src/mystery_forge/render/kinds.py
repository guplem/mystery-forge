"""The document kinds: each one has a template with its own paper look and the front matter `fields` it prints.

The checks read `document_kind_ids()` to report an unknown kind, and `fields` to report a field that the template
does not print. The renderer prints an unknown kind as `generic`, so a render never fails on it.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class DocumentKind:
    id: str
    name: str
    fields: tuple[str, ...]

    @property
    def template(self) -> str:
        return f"{self.id}.html.j2"


DOCUMENT_KINDS: Final[dict[str, DocumentKind]] = {
    kind.id: kind
    for kind in (
        DocumentKind("letter", "Letter", ("letterhead", "place", "date", "recipient", "sender")),
        DocumentKind("notebook", "Notebook page", ("owner", "date")),
        DocumentKind("receipt", "Receipt", ("shop", "sender", "address", "date", "number", "total")),
        DocumentKind("police-report", "Police report", ("station", "case_number", "officer", "date", "subject")),
        DocumentKind("newspaper", "Newspaper", ("masthead", "date", "edition", "price", "headline", "subheadline")),
        DocumentKind("telegram", "Telegram", ("sender", "recipient", "place", "date")),
        DocumentKind("transcript", "Interview transcript", ("case_number", "subject", "interviewer", "place", "date")),
        DocumentKind("email", "Email", ("from", "to", "cc", "date", "subject")),
        DocumentKind("chat-log", "Chat log", ("contact", "owner", "date", "device")),
        DocumentKind(
            "ticket", "Ticket", ("issuer", "passenger", "from", "to", "date", "time", "seat", "number", "price")
        ),
        DocumentKind("id-card", "Identity card", ("issuer", "name", "role", "number", "birth_date", "expires")),
        DocumentKind("map", "Map", ("place", "scale", "legend_title")),
        DocumentKind("photo", "Photograph", ("caption", "date")),
        DocumentKind("poster", "Poster", ("issuer", "headline", "subheadline", "reward")),
        DocumentKind("form", "Official form", ("issuer", "form_number", "date")),
        DocumentKind(
            "case-briefing", "Case briefing", ("agency", "case_number", "classification", "recipient", "date")
        ),
        DocumentKind("generic", "Generic document", ()),
    )
}


def document_kind_ids() -> frozenset[str]:
    return frozenset(DOCUMENT_KINDS)


def document_kind(kind_id: str) -> DocumentKind:
    return DOCUMENT_KINDS.get(kind_id, DOCUMENT_KINDS["generic"])
