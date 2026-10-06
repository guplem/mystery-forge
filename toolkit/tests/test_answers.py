import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from mystery_forge.answers import answer_hash, normalize_answer

CONTRACT_PATH: Path = Path(__file__).resolve().parents[2] / "contracts" / "answer-vectors.json"
CONTRACT: dict[str, Any] = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "vector", CONTRACT["normalization"], ids=lambda vector: f"{vector['language']}:{vector['input']}"
)
def test_normalize_answer_matches_the_shared_vectors(vector: dict[str, str]) -> None:
    assert normalize_answer(vector["input"], vector["language"]) == vector["expected"]


def test_answer_hash_is_the_sha256_of_salt_colon_normalized_answer() -> None:
    expected: str = hashlib.sha256(b"test-salt:lighthouse").hexdigest()
    assert answer_hash("lighthouse", "test-salt") == expected


@pytest.mark.parametrize("vector", CONTRACT["hashes"], ids=lambda vector: vector["normalized"] or "empty")
def test_answer_hash_matches_the_shared_vectors(vector: dict[str, str]) -> None:
    assert answer_hash(vector["normalized"], CONTRACT["salt"]) == vector["expected_sha256"]
