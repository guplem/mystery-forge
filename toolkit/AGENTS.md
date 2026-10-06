# toolkit

The Python package `mystery_forge` and its CLI `forge`. It loads configs, builds puzzle mechanics, checks games, and renders the outputs. The generator calls it as `uv run --project ../toolkit forge <verb>` from `generator/`.

## Module map

| Module       | Concern                                                                                                           |
| ------------ | ----------------------------------------------------------------------------------------------------------------- |
| `answers.py` | Answer normalization and the salted SHA-256 hash. The JavaScript copy must match `contracts/answer-vectors.json`. |

## Conventions

- One test file per module: `tests/test_<module>.py`. Shared fixture games live in `tests/fixtures/`.
- Models are pydantic v2 classes with explicit field types. Load YAML with `yaml_loading.py`, never with `yaml.safe_load`.
- A function that touches the system (files, the browser, the registry) takes that dependency as a parameter, so the tests can pass a fake on every operating system.

## Gotchas

- **Coverage must reach 100% on Windows and on Linux.** Never branch on `sys.platform` inside logic; pass the platform in as a value.
