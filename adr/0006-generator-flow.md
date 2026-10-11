# Generator flow: the create-game pskill skill

## Context

One game takes hours of agent work and dozens of files. One agent session cannot hold all the content without losing quality after context compaction. Agents also skip steps of long prose instructions, which is why pskill exists.

## Decision

- The user opens the agent in `generator/`. The pskill skill `create-game` drives the whole run.
- **Fixed texts for any language.** The toolkit has checked tables of its fixed texts for 7 languages. For any other game language, the `texts` step has a subagent translate the English pack into `source/strings.json`, and `forge strings` checks every key, every `{field}`, the calendar, and the file names before any story work starts.
- **The main agent is an orchestrator.** It routes between steps and makes short decisions. Every heavy writing step (concepts, story, plan, each puzzle, documents, fixes, images, reviews) runs in a fresh subagent through a pskill `parallel` block, often with one item. A task returns the list of files that it wrote and a summary of five lines at most.
- **Every command runs as a pskill `script` block**, never inside a subagent. Scripts print one small JSON object and exit 0, also when they find problems; the next edge routes on the `ok` field. Full reports go to files.
- **Each fix loop is an internal child skill** called by a `call` block, so that each call starts with an empty `history` and its own visit cap. `game-check-loop` checks one scope (story, plan, full) and fixes it; `solver-panel` runs one panel round.
- **Every file has exactly one writer.** The puzzle plan (`source/plan.yaml`) names the documents that each puzzle writer owns; the story documents have their own writer, who runs first so that puzzle writers can quote them. `forge check` groups its findings by owner, so parallel fixers never edit the same file.
- **The work folder is `generator/games/<date>-<slug>/`** inside the workspace, so no write needs an extra permission. The last script copies the deliverables to the output folder (the real Desktop by default).
- **Every question comes first.** After the concept choice, the run asks nothing more. A config can let the agent pick the concept too.
- **Each parallel block picks a tier and a tool profile by the job of its agents** (pskill `tier` and `tools`). Agents that play or check against written rules (the solvers, the guesser, the plain-test solvers, the visual reviewer) get `tier: standard` and `tools: read`. Reviewers that hunt contradictions (story, plan, documents) get `tools: read` and keep the main model. Writers and fixers keep the main model and all tools, because they edit files. Solvers are the most numerous tasks, so this is where the cost falls.
- Each solver task names one packet file (`reports/panel/stage-<id>.md`) and tells the solver to read that file only. The packet text cannot go into the task list itself, because pskill cuts a script's output at 64 KiB. The `read` profile (Bash, Read, Grep, Glob, and Write for the answer file) removes Edit, the web tools, and the MCP tools only. A solver can still read source files, so the canary check (`0004-verification-strategy.md`) detects a solver that did.
- **Every visit cap is a safety net.** The history counts on the edges set the real round limits. Each `max_visits` sets `ask_on_max_visits: false`, so a run moves on at the cap and does not ask the user "more rounds or move on?".

**Rejected alternative:** one long prose skill. Agents skip steps and lose track in long runs, which is the failure that pskill prevents.

## Consequences

- Claude Code is the supported harness. Codex runs the skill with no hooks in a subfolder project, so a stop there is not caught.
- Claude Code ignores the project settings of `generator/` (permissions and hooks) until the user trusts the folder once; the README says so.
