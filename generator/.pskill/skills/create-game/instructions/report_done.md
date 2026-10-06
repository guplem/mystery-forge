Tell the user that their game is ready, in the folder `{{ steps.export.json.folder }}`. List the files that it holds, one line each, with what each is for:
{% for file in steps.export.json.files %}- {{ file }}
{% endfor %}
Then say, in short lines:
- What to do now: open "1 - START HERE" first; it has the printing checklist.
- How it was tested: {{ history.panel | length }} solver panel round(s){% if steps.panel is defined and not steps.panel.outputs.ok %}; some puzzles still had panel findings, listed in the game's `reports/` folder{% endif %}{% if not inputs.panel %}; the solver panel was turned off for this run{% endif %}.
- The game's source stays in `{{ steps.setup.json.game_dir }}`. To change something later, they can ask you here (for example: "make puzzle B2 easier", "print it in black and white").

Do not reveal any answer, culprit, twist, or puzzle content: the user may play this game.
