Review the story bible `{{ steps.setup.json.game_dir }}/source/story.yaml` before any puzzle exists. Also read `source/config.json`, `source/draw.json`, and `uv run --project ../toolkit forge catalog rules`.

Look for these problems, in this order:
1. **Contradictions.** Two statements that cannot both be true: times, places, ages, who knew what. Quote both statements.
2. **Unfair deduction.** The culprit cannot be proven from the story clues alone; an innocent suspect cannot be cleared; a question has two defensible options; the solution needs knowledge that no clue gives.
3. **A weak mystery.** No twist, a twist that is not foreshadowed, an obvious culprit from the first page, a motive that does not make sense.
4. **Audience and limits.** Content that breaks the audience rule or the config's content limits; a cliché name, phrase, or plot from `draw.json`.
5. **A dull frame.** The intro does not set a clear goal; an epilogue does not pay off what the players did.

A finding is `required` when it is a contradiction, unfair, against the audience rule, or a cliché from the list. Everything else is a `suggestion`. Give each finding a concrete fix. Return an empty list when the story is ready. Do not change any file.
