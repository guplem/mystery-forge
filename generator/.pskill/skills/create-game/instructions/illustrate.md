Draw the illustrations of the game in `{{ steps.setup.json.game_dir }}`. Every document is written now, and no other subagent works at the same time.

Read first: `source/config.json` (the visual style, the printer, and ink saving), `source/story.yaml`, `source/plan.yaml`, every file in `source/documents/`, and `uv run --project ../toolkit forge schema references`.

1. **Pick the documents that a picture makes better**, about one image per two documents, at least 3 and at most 10. Good candidates: a photo (draw the scene that the caption describes), a map (the real places of the registry, with their exact names), an ID card or a wanted poster (a portrait), a newspaper (a news picture), a letter or a receipt (a letterhead logo or a stamp), a ticket, a floor plan, an object that the story talks about.
2. **Draw each image** as `source/images/<id>.svg` (id in kebab case). Rules:
   - One `<svg>` with a `viewBox`, plain shapes, paths, and short text. No scripts, no event attributes, no links, no raster images, no fonts that the page may not have (use `font-family="serif"` or `"sans-serif"`). At most 30 KB.
   - Draw like an illustrator, not a clip-art generator: a clear composition, a few well-chosen details, lines in `currentColor`. Use at most two flat fills that stay readable in grayscale; never let a color carry meaning.
   - Show nothing that solves a puzzle or names the culprit, unless the plan puts that clue in this image on purpose.
   - A map uses the registry names exactly as `story.yaml` writes them.
3. **Place each image** with `{{ '{{image:<id>|caption}}' }}` on its own line in its document, where a reader expects it. Change nothing else in the document: every clue quote and every `{{ '{{artifact}}' }}` must stay exactly as it is.

Then run `uv run --project ../toolkit forge check --game {{ steps.setup.json.game_dir }} --scope full` and fix every `images.*` finding. Your answer lists the image files.
