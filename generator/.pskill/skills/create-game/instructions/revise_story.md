Revise `{{ steps.setup.json.game_dir }}/source/story.yaml` for these review findings:

{% for finding in steps.review_story.results[0].findings %}- [{{ finding.severity }}] {{ finding.problem }} Fix: {{ finding.fix }}
{% endfor %}
Fix every required finding. Apply a suggestion when it makes the game better and costs little. Keep the parts that the findings do not touch. Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope story` and fix every error before you answer. Your answer is a spoiler-free summary.
