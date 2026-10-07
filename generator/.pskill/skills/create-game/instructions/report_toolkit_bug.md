Tell the user that the game is written and passed its checks{% if steps.panel is defined %} and the solver panel{% endif %}, but the toolkit could not lay out one of its own pages (a page that the toolkit builds, not a page that the game writers wrote), so nothing was exported. This is a bug in Mystery Forge, not in their game.

- The render report is `{{ steps.render.json.report }}`. Name the page in one line, with no spoiler.
- The game's files stay in `{{ steps.setup.json.game_dir }}`. After a toolkit fix, they can ask you to render and export this game again: `uv run --project ../toolkit forge render --game {{ steps.setup.json.game_dir }}`, then `forge export`.
- Suggest that they report the bug on the project's GitHub page with that report file.
