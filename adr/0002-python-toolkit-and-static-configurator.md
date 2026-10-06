# Python toolkit and a static JavaScript configurator

## Context

The project has two runtimes. The configurator must open with a double-click (a `file://` URL) in Chrome and Firefox, with no server and no install, so it must be plain browser JavaScript. The generator runs in a coding agent, and pskill (the workflow runner) already needs uv and Python. Every extra prerequisite costs a non-technical user an install step.

## Decision

- **The toolkit is Python 3.12**, a uv project in `toolkit/` with the CLI `forge`. uv is the only prerequisite for a user, next to the agent app and a Chrome or Edge browser. The generator calls `uv run --project ../toolkit forge <verb>`.
- **The configurator is plain JavaScript in classic scripts**, with JSDoc types that `tsc` checks. Chrome blocks ES modules and `fetch` on `file://` pages, so the page loads sibling files with `<script src>` only. Node and npm are development tools only: Prettier, `tsc`, `node --test`, and lefthook.
- **Shared rules live once in `contracts/`.** Three rules exist on both sides: the config schema, answer normalization with hashing, and the time estimate. Each contract file has test vectors that the Python tests and the JavaScript tests both run.
  - The config schema is `contracts/game-config.schema.json` and uses a small subset of JSON Schema (`type`, `enum`, `minimum`, `maximum`, `maxLength`, `maxItems`, `items`, `properties`, `required`, `additionalProperties`, `default`). Python validates it with the `jsonschema` library. The configurator has a small validator for that subset, and a test fails when the schema uses a keyword outside it.
  - The page cannot read a JSON file from `file://`, so `npm run generate:schema` copies the schema into `configurator/gameConfigSchema.js` (committed, never hand-edited). A test fails when the copy is stale.

**Rejected alternative:** a TypeScript toolkit, so that one language covers everything. It removes the cross-language contracts, but every user must then install Node next to uv, and pskill scripts would mix two runtimes anyway.

## Consequences

- A user installs uv, the agent app, and a Chromium-based browser. Nothing else.
- A change to a shared rule touches the contract file and both implementations in one PR. The shared vectors catch drift.
