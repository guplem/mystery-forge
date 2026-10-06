from mystery_forge.render.kinds import DOCUMENT_KINDS, document_kind, document_kind_ids
from mystery_forge.render.package_files import package_file


def test_the_kind_ids_include_every_kind_of_the_golden_game() -> None:
    assert {"letter", "notebook", "receipt", "police-report", "generic"} <= document_kind_ids()
    assert len(document_kind_ids()) == 17


def test_every_kind_has_a_template_file() -> None:
    for kind in DOCUMENT_KINDS.values():
        assert package_file(f"templates/kinds/{kind.template}").is_file(), kind.id


def test_the_golden_receipt_fields_are_allowed() -> None:
    assert {"sender", "date", "shop", "total"} <= set(document_kind("receipt").fields)


def test_an_unknown_kind_renders_as_generic() -> None:
    assert document_kind("hologram").id == "generic"
    assert document_kind("letter").name == "Letter"
