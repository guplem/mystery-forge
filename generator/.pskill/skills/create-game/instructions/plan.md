Plan the puzzles of the game in `{{ steps.setup.json.game_dir }}`.

Read first: `source/config.json`, `source/brief.json`, `source/draw.json` (the mechanic candidates), `source/story.yaml`, `uv run --project ../toolkit forge catalog rules`, and `uv run --project ../toolkit forge catalog show <id>` for each mechanic that you consider.

Write two files.

**`source/flow.yaml`** (`forge schema flow`): the stages (envelopes) in order. The first stage opens at the start; each later stage opens with the answer to a puzzle of an earlier stage. Use `brief.json` → `stage_count` stages. `structure` is `funnel` when the last stage gathers answers from every earlier stage. Set `final_puzzle` to the climax puzzle of the last stage, and `accusation: true` when the story has a deduction. Give each stage a short `label` (in the game language, no spoiler) and an `opening_text`: one or two sentences that greet the players when they open it (a mid-game twist belongs here).

**`source/plan.yaml`** with these fields:
- `format_version: 1`, and `motif`: how the drawn motif recurs and pays off.
- `puzzles`: about `brief.json` → `puzzle_count` puzzles. Each has `id` (P1, P2, ...), `stage`, `title` (in the game language; a good title is a hint), `mechanic` (a candidate from `draw.json`, or another implemented mechanic that fits better), `difficulty`, `depends_on`, `answer`, `in_world_reason` (why this information is hidden this way, in the story), `reveals` (the story fact that the answer reveals), `documents` (the ids of the documents that this puzzle's writer writes: at least one, where the puzzle material goes), `relies_on` (ids of story documents that the puzzle also needs), and `notes` for the writer.
- `story_documents`: the documents that no puzzle owns: the case briefing, every document that `story.yaml` clues point to, red herrings, and context. Each has `id`, `kind` (`forge schema document`), `stage`, `title`, `purpose`, and `must_contain` (the exact sentences that must appear: every story clue quote of that document, and the facts that puzzles rely on).

Design rules (the checks enforce most of them):
- Pacing: an easy first puzzle that teaches the answer check, a ramp, a twist when a new envelope opens, one hard climax, then the final puzzle or the accusation. The final puzzle uses earlier answers (a meta puzzle) when the format has envelopes.
- Variety: at least 4 different player actions, at most 2 lookup ciphers, never the same action twice in a row, and at least 40% of the puzzles combine two or more documents.
- Parallel work: each stage offers about `brief.json` → `parallel_width` puzzles that people can solve at the same time.
- Answers: specific, unambiguous, and not guessable from the premise. A word that is the theme of the game (for example "lighthouse" in a lighthouse story) is a bad answer.
- Every document has exactly one owner: one puzzle, or `story_documents`. Keep the document ids that `story.yaml` clues already use.
- Time: the catalog minutes of the puzzles must fit the duration of the config.

Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope plan` and fix every error before you answer. Your answer is a summary with no answer and no twist.
