from mystery_forge.render.sheets import OUTPUT_FILES, OutputPlan, Sheet, number_sheets, number_sheets_by_stage, paginate


def sheet(stage: str | None) -> Sheet:
    return Sheet(role="document", template="x.html.j2", content=None, stage=stage)


def test_paginate_fills_each_page_up_to_the_budget() -> None:
    assert paginate([3, 3, 3, 9, 1], lambda item: item, 6) == [[3, 3], [3], [9], [1]]
    assert paginate([], lambda item: item, 6) == []


def test_paginate_moves_a_heading_to_the_page_of_the_item_after_it() -> None:
    def is_heading(item: str) -> bool:
        return item.startswith("#")

    def cost(item: str) -> float:
        return 1 if is_heading(item) else 3

    assert paginate(["a", "#h", "b"], cost, 5, is_heading) == [["a"], ["#h", "b"]]
    assert paginate(["#h", "#i", "b"], cost, 4, is_heading) == [["#h", "#i", "b"]]


def test_number_sheets_counts_the_whole_output() -> None:
    assert [item.corner for item in number_sheets([sheet(None), sheet("A")])] == ["1/2", "2/2"]


def test_number_sheets_by_stage_counts_inside_each_stage() -> None:
    numbered = number_sheets_by_stage([sheet(None), sheet("A"), sheet("A"), sheet("B"), sheet(None)])
    assert [item.corner for item in numbered] == ["1/2", "A · 1/2", "A · 2/2", "B · 1/1", "2/2"]


def test_an_output_plan_knows_its_file_names() -> None:
    assert OutputPlan(id="hints", sheets=[]).files.pdf == "3 - Hints.pdf"
    assert OUTPUT_FILES["materials"].html == "materials.html"
