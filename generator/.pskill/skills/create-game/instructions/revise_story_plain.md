Fresh solvers who got only the plain clues of `{{ steps.setup.json.game_dir }}/source/story.yaml` (no hidden clue, no puzzle) proved these accusation answers. So players could skip the puzzles:

{% for item in steps.plain_test_judge.json.failing_questions | default([]) %}- Question `{{ item.question }}`. The solvers quoted: {% for quote in item.quotes %}"{{ quote }}"{% if not loop.last %}; {% endif %}{% endfor %}
{% endfor %}
Revise the story so that each of these answers needs a fact that only a puzzle reveals:
- Turn the deciding plain clue into a hidden clue (`hidden: true`, no `document`), so that a puzzle reveals it. Or make the plain clue weaker, so that it points at more than one option.
- A fact can leak from two plain clues together: weaken every route that the solvers quoted.
- When plain clues clear every innocent suspect, make one exclusion depend on a hidden clue.
- Keep the story fair: the hidden clue plus the plain clues must still prove the answer.
- Keep the parts that these findings do not touch, and add no new character, location, or event.

Edit the file with the Edit or Write tool (a long shell command fails on Windows). Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope story` and fix every error before you answer. Your answer is a spoiler-free summary.
