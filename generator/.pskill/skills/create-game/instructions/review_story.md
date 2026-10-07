Review the story bible `{{ steps.setup.json.game_dir }}/source/story.yaml` before any puzzle exists. Also read `source/config.json`, `source/draw.json`, and `uv run --project ../toolkit forge catalog rules`.

Look for these problems, in this order:
1. **Contradictions.** Two statements that cannot both be true: times, places, ages, who knew what. Quote both statements.
2. **Unfair deduction.** The culprit cannot be proven from the story clues alone; an innocent suspect cannot be cleared; a question has two defensible options; the solution needs knowledge that no clue gives.
3. **Skippable puzzles.** Cover every hidden clue. Can the plain clues alone prove a question that cites a hidden clue, or clear every innocent suspect? Does a plain clue or the intro state a hidden fact in other words?
4. **A weak mystery.** No twist, a twist that is not foreshadowed, an obvious culprit from the first page, a motive that does not make sense.
5. **Audience and limits.** Content that breaks the audience rule or the config's content limits; a cliché name, phrase, or plot from `draw.json`.
6. **A dull frame.** The intro does not set a clear goal; an epilogue does not pay off what the players did.

A finding is `required` when it is a contradiction, unfair, a skippable puzzle, against the audience rule, or a cliché from the list. Everything else is a `suggestion`. Give each finding a concrete fix. Return an empty list when the story is ready. Do not change any file.
{% if history.review_story | length > 0 %}
This is review round {{ (history.review_story | length) + 1 }}. The writer already revised the story for these earlier findings:
{% for round in history.review_story %}{% for finding in round.results[0].findings %}{% if finding.severity == 'required' %}- {{ finding.problem | truncate(160) }}
{% endif %}{% endfor %}{% endfor %}
Check that each one is fixed. Report as `required` only a problem that is still there or a new contradiction or unfair step. Do not repeat suggestions, and do not raise the bar: a story that is coherent and fair is ready.
{% endif %}
