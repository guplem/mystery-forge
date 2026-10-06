# Verification strategy: builders, code checks, and the AI solver panel

## Context

LLMs make confident mistakes: an answer that the material does not support, a cipher with a wrong letter, a name spelled two ways, a hint that points to the wrong document, a second answer that also fits. A printed game cannot be patched at the table, so every puzzle must be checked before export.

## Decision

Use the strongest check that each puzzle allows, in this order:

1. **Builders** (correct by construction). The agent picks the answer and the parameters; code builds the material (ciphers, word search, maze, nonogram, logic grid, symbol substitution, and more). After rendering, a round-trip check reads the text of the rendered page and decodes it again.
2. **Code verifiers.** The agent writes the material; code checks a stated rule (an acrostic spells the answer, an anagram uses the same letters, the arithmetic gives the code).
3. **The AI solver panel**, for puzzles that only a reader can check (riddles, deduction, observation). Solver subagents get the player view of one stage: the text of every document available there, the answers already found, and the answer formats. They do not get answers, hints, or mechanic names. Each solver returns its answers, the candidates that it considered, and evidence quotes.

Whole-game code checks run on every assembly: the puzzle graph, the evidence ledger (each clue quote is verbatim in its document, each solution step and hint cites clues), answer leaks, the hint ladder, the fact registry (near-duplicate names, nobody in two places at once), the deduction (each innocent suspect has an exclusion clue), variety by player action, and the time and reading budgets.

Panel rules:

- 5 solvers (best quality) or 3 (fast draft) per stage. Pass needs this many correct answers with verified evidence: easy 4 of 5 (3 of 3), medium 3 of 5 (2 of 3), hard 2 of 5 (1 of 3).
- A correct answer whose quotes are not in the packet counts as a guess, not a solve.
- A wrong answer that 2 or more solvers share, or that a solver marks as "fits every clue" with verified quotes, makes the puzzle ambiguous. The fixer must exclude it with a clue or accept it as an equivalent variant.
- When 3 or more solvers agree on the same wrong answer, the fixer checks the gold answer first.
- One guesser gets only the premise and the answer formats. A correct guess marks the puzzle as guessable.
- Each puzzle file holds a canary string. A solver answer that contains a canary read the source files, so it does not count.
- Every check result stores a content hash of what it checked. Export refuses a game with a stale result.

**Rejected alternative:** a panel vote on every puzzle, with no builders. Same-model solvers make correlated mistakes, and LLMs solve ciphers that humans find hard while they fail at folds and overlays that humans find easy. The panel finds ambiguity; it does not measure human difficulty.

## Consequences

- The catalog prefers buildable mechanics, and each catalog entry names its verification level.
- Panel cost grows with stages times solvers, not with puzzles times solvers.
- A harness with no subagents skips the panel, and the report and the manual say "panel not run".
