{% set forced = steps.export_with_warnings is defined %}{% set exported = steps.export_with_warnings.json if forced else steps.export.json %}Tell the user that their game is ready, in the folder `{{ exported.folder }}`. List the files that it holds, one line each, with what each is for:
{% for file in exported.files %}- {{ file }}
{% endfor %}
Then say, in short lines:
- What to do now: open "1 - START HERE" first; it has the printing checklist.
- How it was tested: {{ history.panel | length }} solver panel round(s){% if steps.panel is defined and not steps.panel.outputs.ok %}; some puzzles still had panel findings, listed in the game's `reports/` folder{% endif %}{% if not inputs.panel %}; the solver panel was turned off for this run{% endif %}.{% if forced %} Some checks did not run again after the last changes: the game is probably fine, but it was exported with warnings (see `reports/` in the game folder).{% endif %}
- The game's source stays in `{{ steps.setup.json.game_dir }}`. To change something later, they can ask you here (for example: "make puzzle B2 easier", "print it in black and white").

Do not reveal any answer, culprit, twist, or puzzle content: the user may play this game.
