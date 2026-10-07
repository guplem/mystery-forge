Revise the puzzle plan of the game in `{{ steps.setup.json.game_dir }}` for these design findings:

{% for finding in steps.review_plan.results[0].findings %}- [{{ finding.severity }}] {{ finding.puzzle }}: {{ finding.problem }} Fix: {{ finding.fix }}
{% endfor %}
Fix every required finding. You may change `source/plan.yaml`, `source/flow.yaml`, and the clue fields of `source/story.yaml` (`revealed_by`, and a hidden clue when a puzzle needs a new fact to reveal). Keep the puzzles that the findings do not touch. Edit the files with the Edit or Write tool.

Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope plan` and fix every error before you answer. Your answer is a summary with no answer and no twist.
