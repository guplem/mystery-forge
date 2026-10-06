Write the story documents of the game in `{{ steps.setup.json.game_dir }}`: every entry of `story_documents` in `source/plan.yaml`.

Read first: `source/config.json`, `source/draw.json` (the audience rule), `source/story.yaml`, `source/flow.yaml`, `source/plan.yaml`, `uv run --project ../toolkit forge schema document`, and `uv run --project ../toolkit forge schema references`.

For each planned story document, write `source/documents/<id>.md`: front matter (`format_version: 1`, `id`, `kind`, `stage`, `title`, and the `fields` that its kind uses, such as `sender` and `date` for a letter) and a body in the game language.
- Include every sentence of its `must_contain` list word for word.
- Make each document feel real for its kind: a police report reads like a police report, a receipt like a receipt. Use `{{ '{{char:<id>}}' }}` and the other references for names, places, and dates, so every document agrees with the registry.
- Keep the reading budget: the audience rule's words per document, and `brief.json` → `reading_words` for the whole game.
- Add texture that rewards close readers, but never a fact that contradicts `story.yaml`, and never a puzzle answer in clear text.
- You may add simple SVG illustrations in `source/images/<id>.svg` (stamps, maps, logos, diagrams) and place them with `{{ '{{image:<id>|caption}}' }}`. Use `currentColor` and plain shapes; no scripts, no external links, no raster images.

Then run `uv run --project ../toolkit forge assemble --game {{ steps.setup.json.game_dir }}` and fix every error in your files (errors in puzzle files that do not exist yet are expected). Your answer lists the files that you wrote, with a spoiler-free summary.
