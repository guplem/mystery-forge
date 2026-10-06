# AGENTS.md map with Claude-Code-only skills, subagents, and ADRs

## Context

The repo started empty. It has two kinds of agent: a development agent that changes the project, and a generation agent that a user opens in `generator/` to make a game. This repo adopts a shared personal standard: a root `AGENTS.md` as the always-loaded map, on-demand skills, subagents for delegated checks, and living ADRs. The repo is developed with Claude Code only, so no multi-tool sync machinery is needed.

## Decision

- `AGENTS.md` at the repo root is the canonical, always-loaded map. `CLAUDE.md` is a one-line `@AGENTS.md` shim so Claude Code loads it. Tools that read `AGENTS.md` natively work without extra files.
- Areas that earn their own doc follow the same pattern: `<area>/AGENTS.md` holds the content, next to a one-line `<area>/CLAUDE.md` shim that makes Claude Code load it on demand when working in that area. A nested `AGENTS.md` without its shim never loads.
- Skills live committed directly at `.claude/skills/<name>/SKILL.md`. No `.agents/skills/` canonical tree, no gitignored mirror, no sync scripts.
- All skills are model-invocable (no `disable-model-invocation` frontmatter). The set is small, so the startup-context cost of their descriptions is low.
- Subagents live at `.claude/agents/<name>.md` (`pattern-scout`, `adr-checker`, `validate`, `docs-checker`).
- ADRs live in this single `adr/` directory, indexed as one-line rows in the root `AGENTS.md`, and are living documents updated in place. The folder's conventions live in `adr/AGENTS.md`, auto-loaded via its `adr/CLAUDE.md` shim.
- `.claude/settings.json` holds the permission allow/deny lists and PostToolUse hooks.

- `generator/` is a separate agent workspace with its own `generator/AGENTS.md` + `generator/CLAUDE.md` shim pair. That file is the generation guide, not a development doc. Its `.claude/` and `.pskill/` folders belong to pskill and to the generation flow, not to development.

**Rejected alternative:** one guide for both agents. A generation agent then reads the TDD and CI rules, and a development agent reads the game-writing rules; both waste attention and follow the wrong rules.

## Consequences

**Positive:**

- One canonical copy of each instruction; the always-on context stays small because procedures load on demand as skills.
- No sync scripts or mirrors to maintain.

**Trade-offs and follow-up:**

- Skills, subagents, and settings are Claude-Code-only surfaces. If another agent tool is adopted, move skills to a canonical `.agents/skills/` tree with a gitignored `.claude/skills/` mirror and a sync script.
- If the number of skills grows enough that their always-loaded descriptions bloat startup context, add `disable-model-invocation: true` to the human-invoked ones and introduce an `/invoke` chaining skill.
