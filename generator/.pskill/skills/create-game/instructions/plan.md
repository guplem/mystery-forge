Plan the puzzles of the game in `{{ steps.setup.json.game_dir }}`.

Read first: `source/config.json`, `source/brief.json`, `source/draw.json` (the mechanic candidates), `source/story.yaml`, `uv run --project ../toolkit forge catalog rules`, and `uv run --project ../toolkit forge catalog show <id>` for each mechanic that you consider. Do not read the toolkit's source code: the rules and the check findings say everything that the checks want.
{% if history.review_story and (history.review_story[-1].results[0].findings | selectattr('severity', 'equalto', 'required') | list) %}
The story review left these required problems open. Fix them in `story.yaml` while you plan, with the smallest change:
{% for finding in history.review_story[-1].results[0].findings %}{% if finding.severity == 'required' %}- {{ finding.problem | truncate(300) }} Fix: {{ finding.fix | truncate(200) }}
{% endif %}{% endfor %}{% endif %}
Write these files with the Write tool (a long shell command fails on Windows).

**`source/flow.yaml`** (`forge schema flow`): the stages (envelopes) in order. The first stage opens at the start; each later stage opens with the answer to a puzzle of an earlier stage. Use `brief.json` → `stage_count` stages. `structure` is `funnel` when the last stage gathers answers from every earlier stage. Set `final_puzzle` to the climax puzzle of the last stage, and `accusation: true` when the story has a deduction. Give each stage a short `label` (in the game language, no spoiler) and an `opening_text`: one or two sentences that greet the players when they open it (a mid-game twist belongs here).

**`source/plan.yaml`** with these fields:
- `format_version: 1`, and `motif`: how the drawn motif recurs and pays off.
- `puzzles`: about `brief.json` → `puzzle_count` puzzles. Each has `id` (P1, P2, ...), `stage`, `title` (in the game language; a good title is a hint), `mechanic` (a candidate from `draw.json`, or another implemented mechanic that fits better), `difficulty`, `depends_on`, `answer`, `in_world_reason` (why this information is hidden this way), `hidden_from` (the character or group that the hiding defeats), `reveals` (the story fact that the answer reveals), `documents` (the ids of the documents that this puzzle's writer writes: at least one, where the puzzle material goes), `relies_on` (ids of story documents that the puzzle also needs), `must_contain` (exact sentences that the puzzle's documents must include, such as a link of the final puzzle), and `notes` for the writer: the aha and the signpost, never the text that explains the method.
- `story_documents`: the documents that no puzzle owns: the case briefing, every document that a plain story clue points to, red herrings, and context. Each has `id`, `kind` (`forge schema document`), `stage`, `title`, `purpose`, and `must_contain` (the exact sentences that must appear: every plain story clue quote of that document, and the facts that puzzles rely on).

**`source/story.yaml`**: set `revealed_by` on every hidden clue to the planned puzzle whose answer reveals that fact.

Design rules (the checks and a puzzle-design reviewer enforce them):
- **Every puzzle has a job:** it opens a stage, or feeds the final puzzle, or reveals a hidden clue that the accusation needs. A puzzle with no job is cut.
- **Keys on other props.** A symbol cipher for teens or adults splits its key (`key_parts`) over other props, so the puzzle owns one document per key part.
- **One aha per puzzle.** Name it in `notes` in one sentence. The material shows what to solve and where to look, never how: the hints carry the method.
- **Hiding that works.** The method must defeat `hidden_from` and not the reader that the hider writes for. Reject: a key printed next to the code; a lock whose inputs `hidden_from` already knows; a sender with no reason to encode; an ally who could simply tell the players. One friendly character authors at most 2 puzzles.
- **Evidence, not confessions.** A puzzle reveals a time, a place, an object, or a number that players must connect; never the culprit's own statement of the act, and never the answer of an accusation question.
- **A real final puzzle.** In an envelope game, the final puzzle combines earlier answers by a mechanism that players discover (times on one clock face, words placed in one grid, numbers that index one document); it uses every answer of the last stage and at least one from each earlier stage; a note that spells out a formula is not a meta. Write each link that players need (a stamp, a symbol, a number that pairs a document with an answer) as an exact sentence in `must_contain` of the puzzle or story document that carries it: the checks keep it there through every later fix.
- **An author who chose it.** Every hidden answer has an in-world author who put those letters there on purpose, when they knew the fact, to hide it from `hidden_from`. No letters that nobody chose.
- Pacing: an easy first puzzle that teaches the answer check, a ramp, a twist when a new envelope opens, one hard climax, then the final puzzle or the accusation.
- Variety: at least 4 different player actions, at most 2 lookup ciphers, never the same action twice in a row, at most about 40% of the answers read letters off something, and at least 40% of the puzzles combine two or more documents.
- Parallel work: each stage offers about `brief.json` → `parallel_width` puzzles that people can solve at the same time.
- Answers: specific, unambiguous, and not guessable from the premise or from the answer format. A word that is the theme of the game is a bad answer.
- Every document has exactly one owner: one puzzle, or `story_documents`. Keep the document ids that `story.yaml` plain clues already use.
- Time: the catalog minutes of the puzzles plus the reading must fit the duration of the config.

Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope plan` and fix every error before you answer. Your answer is a summary with no answer and no twist.
