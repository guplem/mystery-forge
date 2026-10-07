# configurator

The config page that a user opens with a double-click (`file://`). It writes a `*.mystery-config.json` file that the generator reads.

## File map

| File                       | Holds                                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `gameConfigSchema.js`      | GENERATED from `contracts/game-config.schema.json` by `npm run generate:schema`. Never edit it.                    |
| `configSchemaValidator.js` | The JSON Schema subset validator and `applyDefaults`.                                                              |
| `configEstimate.js`        | The puzzle count, pages, and generation time estimate. Must match `contracts/estimate-vectors.json`.               |
| `uiText.js`                | Every page text in English, Spanish, and Catalan. Keys `field.<path>` and `enum.<path>.<value>` follow the schema. |
| `configForm.js`            | The page decisions: form model, presets, warnings, language follow, prompt, file name, loading, draft.             |
| `index.html`, `styles.css` | The page and its look. Icons are inline SVG symbols; no external resource.                                         |
| `app.js`                   | DOM glue only. The browser tests in `toolkit/tests/test_configurator_page.py` cover it.                            |

## Rules

- **Classic scripts only.** Chrome blocks ES modules and `fetch` on `file://` pages. Each file is an IIFE that sets one global object (declared in `globals.d.ts`), and the tests load it with `require(path.join(__dirname, '<file>.js'))`.
- **Logic lives in the logic files; `app.js` only wires the DOM.** The logic files have a 100% coverage gate; `app.js` is covered by the browser tests.
- **The schema drives the form.** Add a config field to the schema, then add its texts to every language in `uiText.js` and its path to `SECTIONS` in `configForm.js`. Tests fail until you do all three.
