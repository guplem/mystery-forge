from mystery_forge.findings import Finding, count_errors, findings_to_json


def test_finding_location_joins_file_and_line() -> None:
    assert Finding(severity="error", rule="r", message="m", file="a.yaml", line=3).location == "a.yaml:3"
    assert Finding(severity="error", rule="r", message="m", file="a.yaml").location == "a.yaml"
    assert Finding(severity="warning", rule="r", message="m").location == ""


def test_count_errors_ignores_warnings() -> None:
    findings = [
        Finding(severity="error", rule="a", message="x"),
        Finding(severity="warning", rule="b", message="y"),
        Finding(severity="error", rule="c", message="z"),
    ]
    assert count_errors(findings) == 2


def test_findings_to_json_drops_empty_fields() -> None:
    finding = Finding(severity="error", rule="r", message="m", path="a.b", fix_hint="do this")
    assert findings_to_json([finding]) == [
        {"severity": "error", "rule": "r", "message": "m", "path": "a.b", "fix_hint": "do this"}
    ]
