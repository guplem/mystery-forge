"""The sheet plan of each output: which printed pages exist, in which order, with which content.

Python decides every page; the templates only draw one page each. So the page counts (for the manual's printing
checklist and the corner codes) are known before any HTML exists, and the layout never relies on the browser's
automatic page flow (`adr/0005-rendering-stack.md`).
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Final, Literal

from mystery_forge.i18n import text

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


# A last page filled below this share of the budget is a remainder that a slight stretch of the other pages may absorb.
REMAINDER_SHARE: Final[float] = 0.25
# The budget factors to try, smallest first, so the pages get only as full as they must.
REMAINDER_STRETCHES: Final[tuple[float, ...]] = (1.05, 1.1, 1.15)


# The HTML files stay inside the render folder, so their names never change. The user opens only the PDF files, the
# companion page, and the spoiler folder, so `output_file_names` names those in the game language.
OUTPUT_HTML_FILES: Final[dict[OutputId, str]] = {
    "manual": "manual.html",
    "materials": "materials.html",
    "hints": "hints.html",
    "solutions": "solutions.html",
}
# The export puts these outputs in the spoiler folder, so the manual names their real paths.
SPOILER_OUTPUTS: Final[frozenset[OutputId]] = frozenset({"hints", "solutions"})


@dataclass(frozen=True)
class OutputFileNames:
    # The PDF file of each output. The leading number sorts the files in the order that a host reads them.
    pdfs: dict[OutputId, str]
    # The companion page keeps this name from the render folder to the exported folder.
    companion: str
    spoiler_folder: str

    def exported_path(self, output: OutputId) -> str:
        """The path of an output PDF in the exported folder, with a forward slash."""
        name: str = self.pdfs[output]
        return f"{self.spoiler_folder}/{name}" if output in SPOILER_OUTPUTS else name


def output_file_names(language: str) -> OutputFileNames:
    """The names of the files and the folder that a user sees, in the game language."""
    return OutputFileNames(
        pdfs={output: f"{text(language, f'file_{output}')}.pdf" for output in OUTPUT_HTML_FILES},
        companion=f"{text(language, 'file_companion')}.html",
        spoiler_folder=text(language, "folder_spoilers"),
    )


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
    def html_file(self) -> str:
        return OUTPUT_HTML_FILES[self.id]


def fill_pages[Item](
    items: Sequence[Item],
    cost: Callable[[Item], float],
    budget: float,
    keep_with_next: Callable[[Item], bool],
) -> list[list[Item]]:
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


def paginate[Item](
    items: Sequence[Item],
    cost: Callable[[Item], float],
    budget: float,
    keep_with_next: Callable[[Item], bool] = lambda _: False,
) -> list[list[Item]]:
    """Group items into pages whose total cost stays within the budget. An item bigger than the budget gets a page.

    An item that must stay with the next one (a heading) never ends a page: it moves to the next page with it.
    A last page that holds only a tiny remainder wastes a sheet: when slightly fuller pages hold every item on one
    page less, those pages win. The browser loop gives the group less room again if a fuller page overflows.
    """
    pages: list[list[Item]] = fill_pages(items, cost, budget, keep_with_next)
    if len(pages) < 2 or sum(cost(item) for item in pages[-1]) >= budget * REMAINDER_SHARE:
        return pages
    for stretch in REMAINDER_STRETCHES:
        fuller: list[list[Item]] = fill_pages(items, cost, budget * stretch, keep_with_next)
        if len(fuller) < len(pages):
            return fuller
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
