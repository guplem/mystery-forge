"""The fixed texts of the outputs (labels, headings, warnings) in every game language, plus date formatting.

The agent writes the story texts in the game language. Every text that the toolkit itself prints comes from here, so
a Spanish game never shows an English label. English is the fallback for an unknown language. A test checks that
every language has every key.
"""

from datetime import datetime
from typing import Final

LANGUAGES: Final[tuple[str, ...]] = ("en", "es", "ca", "fr", "de", "it", "pt")

STRINGS: Final[dict[str, dict[str, str]]] = {
    "en": {"envelope_label": "Envelope {stage}"},
    "es": {"envelope_label": "Sobre {stage}"},
    "ca": {"envelope_label": "Sobre {stage}"},
    "fr": {"envelope_label": "Enveloppe {stage}"},
    "de": {"envelope_label": "Umschlag {stage}"},
    "it": {"envelope_label": "Busta {stage}"},
    "pt": {"envelope_label": "Envelope {stage}"},
}

MONTHS: Final[dict[str, tuple[str, ...]]] = {
    "en": (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
    "es": (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ),
    "ca": (
        "gener", "febrer", "març", "abril", "maig", "juny",
        "juliol", "agost", "setembre", "octubre", "novembre", "desembre",
    ),
    "fr": (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ),
    "de": (
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ),
    "it": (
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    ),
    "pt": (
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ),
}  # fmt: skip

WEEKDAYS: Final[dict[str, tuple[str, ...]]] = {
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
    "es": ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"),
    "ca": ("dilluns", "dimarts", "dimecres", "dijous", "divendres", "dissabte", "diumenge"),
    "fr": ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"),
    "de": ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"),
    "it": ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"),
    "pt": ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"),
}

# Each pattern receives the day number, the month name, and the year.
DATE_PATTERNS: Final[dict[str, str]] = {
    "en": "{day} {month} {year}",
    "es": "{day} de {month} de {year}",
    "ca": "{day} de {month} de {year}",
    "fr": "{day} {month} {year}",
    "de": "{day}. {month} {year}",
    "it": "{day} {month} {year}",
    "pt": "{day} de {month} de {year}",
}


def known_language(language: str) -> str:
    return language if language in STRINGS else "en"


def text(language: str, key: str, **values: str) -> str:
    """Return the fixed text `key` in the language, with `{name}` fields filled from `values`."""
    strings: dict[str, str] = STRINGS[known_language(language)]
    if key not in strings:
        raise KeyError(f"No fixed text named '{key}'.")
    return strings[key].format(**values)


def format_date(moment: datetime, language: str) -> str:
    """Return a long date such as "14 de marzo de 1931"."""
    chosen: str = known_language(language)
    month: str = MONTHS[chosen][moment.month - 1]
    return DATE_PATTERNS[chosen].format(day=moment.day, month=month, year=moment.year)


def weekday_name(moment: datetime, language: str) -> str:
    return WEEKDAYS[known_language(language)][moment.weekday()]
