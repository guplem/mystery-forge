Review the puzzle design of the game in `{{ steps.setup.json.game_dir }}` before any puzzle is written. Read `source/config.json`, `source/story.yaml`, `source/flow.yaml`, `source/plan.yaml`, `uv run --project ../toolkit forge catalog rules`, and `uv run --project ../toolkit forge catalog show <id>` for the mechanics that the plan uses. Do not change any file.

For each planned puzzle, answer five questions:
1. **The aha:** state it in one sentence, or report "no aha" (the puzzle only follows stated rules).
2. **The job:** where is the answer used: does it open a stage, feed the final puzzle, or reveal a hidden clue that a deduction question needs? A puzzle with no job is a finding.
3. **The hiding:** does the method defeat `hidden_from` and not the reader? Would `hidden_from` already know the inputs? Is there a reason for this character to hide it this way, and why do the players hold this material? Apply the author test: who put this answer into the material, when, and did they know the fact then? Letters that nobody chose (filler that happens to spell a word), an author who hides a fact from no reader, or a document dated before the facts that it encodes is a finding.
4. **The method:** do the plan's notes or the mechanic force the material to print the method? A puzzle that tells players exactly what to do is a worksheet.
5. **The content:** does it reveal evidence (good) or a confession, a written plan of the culprit, or the answer of an accusation question (bad)?

Then look at the whole game: the pacing (a ramp and a hard climax, not a flat row of 2-minute tasks), the variety of what players do (at most about 40% of the answers read letters off something), the final puzzle (does it combine earlier answers by a mechanism that players discover, and is each link that it needs in `must_contain` of the puzzle or story document that carries it?), and whether the accusation needs the hidden clues.

A finding is `required` when a puzzle has no job, no aha, hides nothing from anyone, fails the author test, reveals a confession or an accusation answer, or when the final puzzle spells out its formula, ignores most earlier answers, or has a link outside `must_contain`. Everything else is a `suggestion`. Give each finding the puzzle id and a concrete fix: a different mechanic, a different answer, a different hiding reason, or a cut. Return an empty list when the plan is ready.
{% if history.review_plan | length > 0 %}
This is review round {{ (history.review_plan | length) + 1 }}. The planner already revised the plan for these earlier findings:
{% for round in history.review_plan %}{% for finding in round.results[0].findings %}{% if finding.severity == 'required' %}- {{ finding.puzzle }}: {{ finding.problem | truncate(160) }}
{% endif %}{% endfor %}{% endfor %}
Check that each one is fixed. Report as `required` only a problem that is still there or a new one. Do not raise the bar.
{% endif %}
