// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// Classic browser scripts, not modules: load them for their side effect, by a computed path that tsc does not resolve.
require(path.join(__dirname, 'uiText.js'));
const uiText = globalThis.MysteryForgeUiText;

/** @type {MysteryForgeJsonSchema} */
const schema = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'contracts', 'game-config.schema.json'), 'utf8'));

/**
 * @param {string} text
 * @returns {string[]}
 */
function placeholdersOf(text) {
  return [...text.matchAll(/\{(\w+)\}/g)].map((match) => String(match[1])).sort();
}

test('requiredSchemaTextKeys lists a label and a help text for each property path and each enum value', () => {
  const keys = uiText.requiredSchemaTextKeys(schema);
  for (const key of [
    'field.schema_version.label',
    'field.players.label',
    'field.players.count.help',
    'field.players.names.label',
    'enum.audience.kids.label',
    'enum.audience.kids.help',
    'enum.puzzle_preferences.words.avoid.help',
    'enum.schema_version.1.label',
  ]) {
    assert.ok(keys.includes(key), key);
  }
  assert.equal(new Set(keys).size, keys.length);
  assert.deepEqual(uiText.requiredSchemaTextKeys({ type: 'string' }), []);
});

for (const language of uiText.UI_LANGUAGES) {
  test(`the "${language}" texts cover every schema field and every enum value`, () => {
    const texts = uiText.TEXTS[language] ?? {};
    const missing = uiText.requiredSchemaTextKeys(schema).filter((key) => !texts[key]);
    assert.deepEqual(missing, []);
  });

  test(`the "${language}" texts have no em dash and no outer spaces`, () => {
    for (const [key, text] of Object.entries(uiText.TEXTS[language] ?? {})) {
      assert.ok(!text.includes('—'), key);
      assert.equal(text, text.trim(), key);
      assert.ok(text.length > 0, key);
    }
  });
}

for (const language of uiText.UI_LANGUAGES) {
  test(`the "${language}" texts have the same keys and the same placeholders as English`, () => {
    const english = uiText.TEXTS.en ?? {};
    const texts = uiText.TEXTS[language] ?? {};
    assert.deepEqual(Object.keys(texts).sort(), Object.keys(english).sort());
    for (const [key, text] of Object.entries(english)) {
      assert.deepEqual(placeholdersOf(texts[key] ?? ''), placeholdersOf(text), key);
    }
  });
}

test('the page offers English, Spanish, and Catalan', () => {
  assert.deepEqual(uiText.UI_LANGUAGES, ['en', 'es', 'ca']);
});

test('translate fills the placeholders and keeps an unknown placeholder', () => {
  assert.equal(uiText.translate('en', 'estimate.about', { time: '2 h' }), 'about 2 h');
  assert.equal(uiText.translate('es', 'estimate.about', { time: '2 h' }), 'aprox. 2 h');
  assert.equal(uiText.translate('ca', 'estimate.about', { time: '50 min' }), 'aprox. 50 min');
  assert.equal(uiText.translate('en', 'estimate.about'), 'about {time}');
});

test('translate falls back to English for an unknown language, and to the key for an unknown key', () => {
  assert.equal(uiText.translate('xx', 'estimate.about', { time: 1 }), 'about 1');
  assert.equal(uiText.translate('en', 'no.such.key'), 'no.such.key');
});

test('pickUiLanguage takes the first supported browser language, else English', () => {
  assert.equal(uiText.pickUiLanguage(['es-ES', 'en-US']), 'es');
  assert.equal(uiText.pickUiLanguage(['fr-FR', 'ES']), 'es');
  assert.equal(uiText.pickUiLanguage(['ca-ES']), 'ca');
  assert.equal(uiText.pickUiLanguage(['fr-FR', 'ca', 'es']), 'ca');
  assert.equal(uiText.pickUiLanguage(['en-GB', 'es']), 'en');
  assert.equal(uiText.pickUiLanguage(['fr-FR']), 'en');
  assert.equal(uiText.pickUiLanguage([]), 'en');
});
