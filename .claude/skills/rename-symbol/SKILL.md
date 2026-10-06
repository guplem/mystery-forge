---
name: rename-symbol
description: Rename or refactor a symbol safely by searching every naming-case variant across code, tests, docs, configs, and JSON. Use when renaming any identifier so no reference is missed.
---

# Rename a symbol safely

When you rename or refactor any symbol, search **all** naming variants (camelCase, PascalCase, snake_case, kebab-case, UPPER_CASE) across the whole project (code, tests, docs, configs, and JSON), not just the obvious code references. A missed variant in a config key or a data file is the usual cause of a rename that compiles fine but breaks at runtime.

Extra traps in this repo:

- **Names shared across languages through `contracts/`.** A config field name lives in `contracts/game-config.schema.json`, the configurator scripts and their i18n labels, the toolkit pydantic model `GameConfig` in `toolkit/src/mystery_forge/config.py`, the shared vector files in `contracts/`, the sample configs in `examples/configs/`, and the generator docs (`generator/AGENTS.md`, pskill `instructions/*.md`). Rename it in all of them in the same PR.
- **The generated schema file.** `configurator/gameConfigSchema.js` holds the config field names. Never edit it by hand. Run `npm run generate:schema` after the schema change, then grep for the old name to confirm that no stale reference remains.
- **Stored keys.** Config files that users already downloaded and game source files in `generator/games/<slug>/source/` store field and model names as keys. Renaming the code symbol is safe. Renaming a stored key breaks those files, so it needs an explicit migration in the loader or a new `format_version`.
- **pskill skill ids.** The folder name in `generator/.pskill/skills/<id>/` is the skill id. Rename the folder and every reference to the id (child skill calls, `tests/*.yaml`, `generator/AGENTS.md`). Then run `uv run .pskill/pskill.py sync` from `generator/` to regenerate the stubs. Never edit the stubs by hand.
- **`forge` CLI verb names.** pskill `skill.yaml` script blocks call the verbs by name (`uv run --project ../toolkit forge assemble ...`). Rename a verb in `toolkit/src/mystery_forge/cli.py` and in every `skill.yaml`, `generator/AGENTS.md`, and `toolkit/AGENTS.md` together. Run `npm run check:skills` to confirm.
- **Catalog and registry ids.** A mechanic id, document kind, or theme id appears in its code registry, in `toolkit/src/mystery_forge/catalog/*.yaml`, and in pskill instructions. Change all of them together.
