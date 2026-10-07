"""The sheet plan of each output: which printed pages exist, in which order, with which content.

Python decides every page; the templates only draw one page each. So the page counts (for the manual's printing
checklist and the corner codes) are known before any HTML exists, and the layout never relies on the browser's
automatic page flow (`adr/0005-rendering-stack.md`).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Final, Literal

OutputId = Literal["manual", "materials", "hints", "solutions"]
SheetRole = Literal[
    "cover",
    "warning",
    "stage-cover",
    "document",
    "register",
    "register-results",
    "accusation",
    "envelope-labels",
    "detective-notes",
    "manual",
    "hint-cards",
    "solution",
    "deduction",
    "truth",
    "epilogues",
]


@dataclass(frozen=True)
class OutputFiles:
    html: str
    pdf: str


OUTPUT_FILES: Final[dict[OutputId, OutputFiles]] = {
    "manual": OutputFiles("manual.html", "1 - START HERE (manual).pdf"),
    "materials": OutputFiles("materials.html", "2 - PRINT THIS (game materials).pdf"),
    "hints": OutputFiles("hints.html", "3 - Hints.pdf"),
    "solutions": OutputFiles("solutions.html", "4 - Solutions.pdf"),
}


@dataclass(frozen=True)
class Sheet:
    role: SheetRole
    # The template under `templates/sheets/` that draws this page.
    template: str
    # The data that the template reads, one dataclass per template.
    content: object
    # The stage whose envelope holds this page, for the materials corner codes.
    stage: str | None = None
    # The small code printed in a corner, such as "B · 3/7". The output plan fills it in.
    corner: str = ""
    # The flow group of a sheet that the toolkit fills from a list. When it overflows, the group gets more sheets.
    group: str | None = None


@dataclass(frozen=True)
class OutputPlan:
    id: OutputId
    sheets: list[Sheet]

    @property
    def files(self) -> OutputFiles:
        return OUTPUT_FILES[self.id]


def paginate[Item](
    items: Sequence[Item],
    cost: Callable[[Item], float],
    budget: float,
    keep_with_next: Callable[[Item], bool] = lambda _: False,
) -> list[list[Item]]:
    """Group items into pages whose total cost stays within the budget. An item bigger than the budget gets a page.

    An item that must stay with the next one (a heading) never ends a page: it moves to the next page with it.
    """
    pages: list[list[Item]] = []
    current: list[Item] = []
    used: float = 0
    for item in items:
        item_cost: float = cost(item)
        if current and used + item_cost > budget:
            carried: list[Item] = []
            while current and keep_with_next(current[-1]):
                carried.insert(0, current.pop())
            if current:
                pages.append(current)
            current = carried
            used = sum(cost(kept) for kept in carried)
        current.append(item)
        used += item_cost
    if current:
        pages.append(current)
    return pages


def number_sheets(sheets: list[Sheet]) -> list[Sheet]:
    """Give each sheet the corner code "n/N"."""
    return [replace(sheet, corner=f"{index}/{len(sheets)}") for index, sheet in enumerate(sheets, start=1)]


def number_sheets_by_stage(sheets: list[Sheet]) -> list[Sheet]:
    """Give each sheet the corner code "B · n/N", counted inside its stage, or "n/N" in the pages without a stage."""
    totals: dict[str | None, int] = {}
    for sheet in sheets:
        totals[sheet.stage] = totals.get(sheet.stage, 0) + 1
    counters: dict[str | None, int] = {}
    numbered: list[Sheet] = []
    for sheet in sheets:
        counters[sheet.stage] = counters.get(sheet.stage, 0) + 1
        prefix: str = f"{sheet.stage} · " if sheet.stage else ""
        numbered.append(replace(sheet, corner=f"{prefix}{counters[sheet.stage]}/{totals[sheet.stage]}"))
    return numbered
