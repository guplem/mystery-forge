{% set summary = steps.setup.json.summary %}{% set brief = steps.setup.json.brief %}Show the user this short summary, then ask whether to start:

- **Config:** {{ steps.setup.json.config_file or "the default settings" }}
- **Game:** {{ summary.players }} players, about {{ summary.duration_minutes }} minutes, {{ summary.difficulty }}, for {{ summary.audience }}, in language `{{ summary.language }}`.
- **Idea:** {{ summary.idea or "surprise me" }}
- **Size:** about {{ brief.puzzle_count }} puzzles in {{ brief.stage_count }} envelopes, about {{ brief.printed_pages }} printed pages.
- **Time:** the generation takes about {{ brief.generation_minutes }} minutes{% if summary.quality == 'best' %} on the best quality setting{% endif %}. It uses a large part of a usage window.

Tell the user what happens next: you show three story teasers with no spoilers, they pick one{% if summary.pick_concept == 'agent' %} (their config lets you pick it for them){% endif %}, and after that the run asks nothing more, so they can leave. If the run stops (for example at a usage limit), they open Claude Code in this folder again and say "continue".
{% if summary.host == 'host_plays' %}
Also tell them: you plan to play this game too, so the run keeps every answer out of this chat. Do not look at the game files until you play.
{% endif %}
