// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

// Classic browser scripts, not modules: load them for their side effect, by a computed path that tsc does not resolve.
// The order matches the <script> order in index.html, because configForm reads the earlier globals.
for (const file of [
  'gameConfigSchema.js',
  'configSchemaValidator.js',
  'configEstimate.js',
  'uiText.js',
  'configForm.js',
]) {
  require(path.join(__dirname, file));
}
const configForm = globalThis.MysteryForgeConfigForm;
const validator = globalThis.MysteryForgeConfigValidator;
const schema = globalThis.MysteryForgeGameConfigSchema;
const uiText = globalThis.MysteryForgeUiText;

/** @returns {MysteryForgeGameConfig} */
function defaults() {
  return configForm.initialConfig([]);
}

/**
 * @param {Record<string, unknown>} changes dotted path to value
 * @returns {MysteryForgeGameConfig}
 */
function configWith(changes) {
  return Object.entries(changes).reduce(
    (config, [fieldPath, value]) => configForm.setFieldValue(config, fieldPath, value),
    defaults(),
  );
}

/**
 * @param {MysteryForgeGameConfig} config
 * @returns {string[]}
 */
function warningIds(config) {
  return configForm.configWarnings(config).map((warning) => warning.id);
}

/**
 * @param {MysteryForgeJsonSchema} node
 * @param {string} prefix
 * @returns {string[]}
 */
function leafPaths(node, prefix) {
  return Object.entries(node.properties ?? {}).flatMap(([name, child]) => {
    const fieldPath = prefix ? `${prefix}.${name}` : name;
    return child.properties ? leafPaths(child, fieldPath) : [fieldPath];
  });
}

/** @returns {MysteryForgeDraftStorage & {items: Map<string, string>}} */
function fakeStorage() {
  const items = new Map();
  return {
    items,
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => void items.set(key, value),
    removeItem: (key) => void items.delete(key),
  };
}

/** @type {MysteryForgeDraftStorage} */
const brokenStorage = {
  getItem: () => {
    throw new Error('denied');
  },
  setItem: () => {
    throw new Error('denied');
  },
  removeItem: () => {
    throw new Error('denied');
  },
};

test('the sections show every config field once, except the schema version', () => {
  const shown = configForm.SECTIONS.flatMap((section) => section.fields);
  const expected = leafPaths(schema, '').filter((fieldPath) => fieldPath !== 'schema_version');
  assert.deepEqual([...shown].sort(), [...expected].sort());
  assert.equal(new Set(shown).size, shown.length);
});

test('buildFormModel derives each widget, its limits, and its options from the schema', () => {
  const sections = configForm.buildFormModel('en');
  const fields = new Map(sections.flatMap((section) => section.fields).map((field) => [field.path, field]));
  assert.equal(sections[0]?.title, 'Who is playing');
  assert.equal(sections.find((section) => section.id === 'personal')?.collapsed, true);
  assert.deepEqual(
    fields.get('audience')?.options.map((option) => option.value),
    schema.properties?.audience?.enum,
  );
  assert.equal(fields.get('audience')?.widget, 'cards');
  assert.equal(fields.get('audience')?.options[0]?.label, 'Kids');
  assert.equal(fields.get('difficulty')?.widget, 'segmented');
  assert.equal(fields.get('language')?.widget, 'select');
  assert.equal(fields.get('content.death_allowed')?.widget, 'toggle');
  assert.equal(fields.get('generation.seed')?.widget, 'number');
  assert.equal(fields.get('generation.seed')?.advanced, true);
  assert.equal(fields.get('generation.quality')?.advanced, true);
  assert.equal(fields.get('generation.pick_concept')?.advanced, false);
  assert.equal(fields.get('players.count')?.widget, 'stepper');
  assert.deepEqual(
    [
      fields.get('duration_minutes')?.widget,
      fields.get('duration_minutes')?.minimum,
      fields.get('duration_minutes')?.maximum,
      fields.get('duration_minutes')?.step,
    ],
    ['range', 30, 240, 15],
  );
  assert.deepEqual(
    [
      fields.get('players.names')?.widget,
      fields.get('players.names')?.maxItems,
      fields.get('players.names')?.maxLength,
    ],
    ['list', 12, 40],
  );
  assert.equal(fields.get('players.names')?.placeholder, 'Type a name and press Enter');
  assert.equal(fields.get('theme.idea')?.widget, 'textarea');
  assert.equal(fields.get('personalization.place')?.widget, 'text');
  assert.equal(fields.get('personalization.place')?.maxLength, 120);
  assert.equal(fields.get('content.death_allowed')?.placeholder, '');
  assert.equal(fields.get('content.death_allowed')?.maxLength, 0);
  assert.equal(configForm.buildFormModel('es')[0]?.title, 'Quién juega');
  assert.equal(configForm.buildFormModel('ca')[0]?.title, 'Qui juga');
});

test('initialConfig holds the schema defaults, a valid config', () => {
  const config = defaults();
  assert.deepEqual(validator.validateConfig(schema, config), []);
  assert.equal(config.schema_version, 1);
  assert.equal(config.players.count, 4);
  assert.equal(config.language, 'en');
  assert.equal(config.equipment.paper, 'A4');
});

test('initialConfig takes the game language and the paper size from the browser languages', () => {
  assert.equal(configForm.initialConfig(['es-ES', 'en']).language, 'es');
  assert.equal(configForm.initialConfig(['ca-ES', 'es']).language, 'ca');
  assert.equal(configForm.initialConfig(['ja-JP', 'fr']).language, 'ja');
  assert.equal(configForm.initialConfig(['qu-PE', 'fr']).language, 'fr');
  assert.equal(configForm.initialConfig(['qu-PE']).language, 'en');
  assert.equal(configForm.initialConfig(['en-US']).equipment.paper, 'Letter');
  assert.equal(configForm.initialConfig(['en-CA']).equipment.paper, 'Letter');
  assert.equal(configForm.initialConfig(['en-GB', 'en-US']).equipment.paper, 'A4');
  assert.equal(configForm.initialConfig(['es-US']).equipment.paper, 'A4');
  assert.equal(configForm.initialConfig(['fr-CA']).equipment.paper, 'A4');
});

test('followPageLanguage moves the game language and the default paper size to the new page language', () => {
  const usEnglish = configForm.initialConfig(['en-US']);
  const spanish = configForm.followPageLanguage(usEnglish, 'en', 'es', ['en-US']);
  assert.equal(spanish.followed, true);
  assert.equal(spanish.config.language, 'es');
  assert.equal(spanish.config.equipment.paper, 'A4');
  assert.equal(usEnglish.language, 'en');
  const catalan = configForm.followPageLanguage(spanish.config, 'es', 'ca', ['en-US']);
  assert.equal(catalan.followed, true);
  assert.equal(catalan.config.language, 'ca');
  assert.equal(catalan.config.equipment.paper, 'A4');
  const english = configForm.followPageLanguage(catalan.config, 'ca', 'en', ['en-US']);
  assert.deepEqual(english, { config: usEnglish, followed: true });
});

test('followPageLanguage keeps a game language and a paper size that the user chose', () => {
  const french = configWith({ language: 'fr' });
  assert.deepEqual(configForm.followPageLanguage(french, 'en', 'es', []), { config: french, followed: false });
  const letter = configForm.followPageLanguage(configWith({ 'equipment.paper': 'Letter' }), 'en', 'es', ['en-GB']);
  assert.equal(letter.config.language, 'es');
  assert.equal(letter.config.equipment.paper, 'Letter');
  assert.deepEqual(configForm.followPageLanguage(defaults(), 'en', 'en', []), {
    config: defaults(),
    followed: false,
  });
});

test('setFieldValue returns a new config and coerces the raw value to the schema type and limits', () => {
  const start = defaults();
  const changed = configForm.setFieldValue(start, 'players.count', '7');
  assert.equal(changed.players.count, 7);
  assert.equal(start.players.count, 4);
  assert.equal(configForm.setFieldValue(start, 'players.count', '99').players.count, 12);
  assert.equal(configForm.setFieldValue(start, 'players.count', '-3').players.count, 1);
  assert.equal(configForm.setFieldValue(start, 'players.count', '2.6').players.count, 3);
  assert.equal(configForm.setFieldValue(start, 'players.count', 'abc').players.count, 4);
  assert.equal(configForm.setFieldValue(start, 'generation.seed', '12345').generation.seed, 12345);
  assert.equal(configForm.setFieldValue(start, 'schema_version', '1').schema_version, 1);
  assert.equal(configForm.setFieldValue(start, 'content.death_allowed', false).content.death_allowed, false);
  assert.equal(configForm.setFieldValue(start, 'personalization.place', 42).personalization.place, '42');
  const longText = '\u{1F50D}'.repeat(130);
  assert.equal(
    [...configForm.setFieldValue(start, 'personalization.place', longText).personalization.place].length,
    120,
  );
  assert.deepEqual(configForm.setFieldValue(start, 'players.names', ['Ana']).players.names, ['Ana']);
  assert.deepEqual(configForm.setFieldValue(start, 'players.names', 'Ana').players.names, []);
  assert.equal(configForm.getAtPath(changed, 'players.count'), 7);
  assert.equal(configForm.getAtPath(changed, 'players.missing.deeper'), undefined);
});

test('setFieldValue rejects a path outside the schema', () => {
  assert.throws(() => configForm.setFieldValue(defaults(), 'players.nickname', 'x'), /players\.nickname/);
});

test('list helpers trim, skip empty text, cut long text, stop at the limit, and remove by index', () => {
  let config = defaults();
  config = configForm.addListItem(config, 'players.names', '  Ana  ');
  config = configForm.addListItem(config, 'players.names', '   ');
  config = configForm.addListItem(config, 'players.names', 'x'.repeat(50));
  assert.deepEqual(config.players.names, ['Ana', 'x'.repeat(40)]);
  for (let index = 0; index < 10; index += 1) {
    config = configForm.addListItem(config, 'personalization.inside_jokes', `joke ${index}`);
  }
  assert.equal(config.personalization.inside_jokes.length, 5);
  assert.equal(configForm.isListFull(config, 'personalization.inside_jokes'), true);
  assert.equal(configForm.isListFull(config, 'players.names'), false);
  config = configForm.removeListItem(config, 'personalization.inside_jokes', 1);
  assert.deepEqual(config.personalization.inside_jokes, ['joke 0', 'joke 2', 'joke 3', 'joke 4']);
});

test('every audience has a preset, and each preset gives a valid config with that audience', () => {
  assert.deepEqual(
    Object.keys(configForm.AUDIENCE_PRESETS).sort(),
    [...(schema.properties?.audience?.enum ?? [])].sort(),
  );
  for (const audience of Object.keys(configForm.AUDIENCE_PRESETS)) {
    const config = configForm.applyAudiencePreset(defaults(), audience);
    assert.deepEqual(validator.validateConfig(schema, config), [], audience);
    assert.equal(config.audience, audience);
  }
});

test('the kids preset makes a gentle, easy, readable game', () => {
  const config = configForm.applyAudiencePreset(configWith({ 'players.count': 6 }), 'kids');
  assert.equal(config.difficulty, 'easy');
  assert.equal(config.content.death_allowed, false);
  assert.equal(config.content.scary_level, 'none');
  assert.equal(config.content.reading_load, 'light');
  assert.equal(config.visuals.style, 'kids');
  assert.equal(config.visuals.readable_font, true);
  assert.equal(config.players.count, 6);
  assert.deepEqual(warningIds(config), []);
});

test('the puzzle fans preset makes an expert game', () => {
  assert.equal(configForm.applyAudiencePreset(defaults(), 'puzzle_fans').difficulty, 'expert');
});

test('an audience without a preset only sets the audience', () => {
  const config = configForm.applyAudiencePreset(defaults(), 'aliens');
  assert.deepEqual(config, { ...defaults(), audience: 'aliens' });
});

test('the default config has no warning', () => {
  assert.deepEqual(configForm.configWarnings(defaults()), []);
});

/** @type {[string, Record<string, unknown>, string[]][]} */
const WARNING_CASES = [
  ['kids with a death', { audience: 'kids', 'content.scary_level': 'none' }, ['kids_death']],
  [
    'kids with a spooky story',
    { audience: 'kids', 'content.death_allowed': false, 'content.scary_level': 'spooky' },
    ['kids_spooky'],
  ],
  ['one player with a game master', { 'players.count': 1, host: 'game_master' }, ['solo_game_master']],
  [
    'the kids style on a black and white printer',
    { 'equipment.printer': 'black_and_white', 'visuals.style': 'kids' },
    ['colors_go_gray'],
  ],
  ['black and white with ink saving off is fine', { 'equipment.printer': 'black_and_white' }, []],
  ['no scissors', { 'equipment.scissors': false }, ['no_scissors']],
  [
    'craft puzzles without scissors',
    { 'equipment.scissors': false, 'puzzle_preferences.crafts': 'like' },
    ['crafts_without_scissors'],
  ],
  ['a short expert game', { duration_minutes: 45, difficulty: 'expert' }, ['short_expert']],
  ['a long expert game', { duration_minutes: 60, difficulty: 'expert' }, []],
  ['a big group without a game master', { 'players.count': 9 }, ['many_players_no_game_master']],
  ['a big group with a game master', { 'players.count': 9, host: 'game_master' }, []],
  [
    'envelopes without envelopes',
    { format: 'envelopes', 'equipment.envelopes': false },
    ['envelopes_without_envelopes'],
  ],
  ['a case file without envelopes', { format: 'case_file', 'equipment.envelopes': false }, []],
  [
    'no help at all',
    { 'assistance.hints': false, 'assistance.paper_answer_check': false, 'assistance.companion_page': false },
    ['no_help'],
  ],
  ['hints only', { 'assistance.paper_answer_check': false, 'assistance.companion_page': false }, []],
];

for (const [name, changes, expected] of WARNING_CASES) {
  test(`configWarnings: ${name}`, () => {
    assert.deepEqual(warningIds(configWith(changes)), expected);
  });
}

test('configWarnings: every puzzle kind skipped', () => {
  const changes = Object.fromEntries(
    Object.keys(schema.properties?.puzzle_preferences?.properties ?? {}).map((kind) => [
      `puzzle_preferences.${kind}`,
      'avoid',
    ]),
  );
  assert.deepEqual(warningIds(configWith(changes)), ['all_puzzles_avoided']);
});

test('configWarnings: more names than players carries the player count, and every warning has a text', () => {
  const config = configWith({ 'players.count': 2, 'players.names': ['A', 'B', 'C'] });
  const [warning] = configForm.configWarnings(config);
  assert.deepEqual(warning, {
    id: 'more_names_than_players',
    severity: 'info',
    path: 'players.names',
    params: { count: 2 },
  });
  assert.match(uiText.translate('en', `warning.${warning?.id}`, warning?.params), /first 2 names/);
  const ids = WARNING_CASES.flatMap(([, , expected]) => expected).concat('all_puzzles_avoided');
  for (const id of ids) {
    assert.ok(uiText.TEXTS.en[`warning.${id}`], id);
  }
});

test('showsSurpriseNote is true only while the story idea is blank', () => {
  assert.equal(configForm.showsSurpriseNote(defaults()), true);
  assert.equal(configForm.showsSurpriseNote(configWith({ 'theme.idea': '   ' })), true);
  assert.equal(configForm.showsSurpriseNote(configWith({ 'theme.idea': 'A heist' })), false);
});

test('textLength counts code points, as the schema limit does', () => {
  assert.equal(configForm.textLength(defaults(), 'theme.idea'), 0);
  assert.equal(configForm.textLength(configWith({ 'theme.idea': 'A heist 🎨' }), 'theme.idea'), 9);
});

test('the story idea shows its character limit', () => {
  const idea = configForm
    .buildFormModel('en')
    .flatMap((section) => section.fields)
    .find((field) => field.path === 'theme.idea');
  assert.equal(idea?.maxLength, 5000);
  for (const language of uiText.UI_LANGUAGES) {
    assert.match(uiText.translate(language, 'form.text_count', { count: 9, max: 5000 }), /9.*5000/);
  }
});

test('formatMinutes writes hours and minutes', () => {
  assert.equal(configForm.formatMinutes(45), '45 min');
  assert.equal(configForm.formatMinutes(60), '1 h');
  assert.equal(configForm.formatMinutes(135), '2 h 15 min');
});

test('estimateItems shows the estimate, with envelopes or chapters by format, and a rounded generation time', () => {
  const items = configForm.estimateItems(defaults(), 'en');
  const estimate = globalThis.MysteryForgeConfigEstimate.estimateFromConfig(defaults());
  assert.deepEqual(
    items.map((item) => item.id),
    ['puzzles', 'stages', 'pages', 'play_time', 'generation'],
  );
  assert.equal(items[0]?.value, String(estimate.puzzle_count));
  assert.equal(items[1]?.label, 'Envelopes');
  assert.equal(items[2]?.value, String(estimate.printed_pages));
  assert.equal(items[3]?.value, '1 h 30 min');
  const roundedGeneration = Math.round(estimate.generation_minutes / 10) * 10;
  assert.equal(items[4]?.value, `about ${configForm.formatMinutes(roundedGeneration)}`);
  assert.equal(configForm.estimateItems(configWith({ format: 'case_file' }), 'es')[1]?.label, 'Capítulos');
});

test('summaryBarText gives the puzzle count and the play time in the casing of the page language', () => {
  const puzzles = globalThis.MysteryForgeConfigEstimate.estimateFromConfig(defaults()).puzzle_count;
  assert.equal(configForm.summaryBarText(defaults(), 'es'), `${puzzles} enigmas · 1 h 30 min`);
  assert.equal(configForm.summaryBarText(defaults(), 'en'), `${puzzles} puzzles · 1 h 30 min`);
});

test('generationTimeText is shorter for fast quality', () => {
  const best = configForm.generationTimeText(defaults(), 'en');
  const fast = configForm.generationTimeText(configWith({ 'generation.quality': 'fast' }), 'en');
  assert.match(best, /^about /);
  assert.notEqual(best, fast);
});

test('configFileName uses an ASCII slug of the story idea, cut after a whole word at 40 characters at most', () => {
  const today = new Date(2026, 9, 6);
  assert.equal(
    configForm.configFileName(configWith({ 'theme.idea': '  ¡El Misterio del Café Señorial!  ' }), today),
    'mystery-forge-el-misterio-del-cafe-senorial.mystery-config.json',
  );
  const longName = configForm.configFileName(
    configWith({ 'theme.idea': 'A stolen painting at a seaside hotel during the summer festival' }),
    today,
  );
  const slug = longName.replace('mystery-forge-', '').replace('.mystery-config.json', '');
  assert.ok(slug.length <= 40);
  assert.equal(slug, 'a-stolen-painting-at-a-seaside-hotel');
  assert.equal(
    configForm.configFileName(
      configWith({ 'theme.idea': 'Un robo en el hotel de la playa el día de San Juan!!' }),
      today,
    ),
    'mystery-forge-un-robo-en-el-hotel-de-la-playa-el-dia.mystery-config.json',
  );
  assert.equal(
    configForm.configFileName(configWith({ 'theme.idea': 'x'.repeat(60) }), today),
    `mystery-forge-${'x'.repeat(40)}.mystery-config.json`,
  );
});

test('configFileName falls back to the date when the idea has no usable letter', () => {
  const today = new Date(2026, 0, 5);
  assert.equal(configForm.configFileName(defaults(), today), 'mystery-forge-2026-01-05.mystery-config.json');
  assert.equal(
    configForm.configFileName(configWith({ 'theme.idea': '\u{1F50D}\u{1F575}' }), today),
    'mystery-forge-2026-01-05.mystery-config.json',
  );
  assert.match(configForm.configFileName(defaults()), /^mystery-forge-\d{4}-\d{2}-\d{2}\.mystery-config\.json$/);
});

test('configFileText is pretty JSON that parses back to the same config', () => {
  const text = configForm.configFileText(defaults());
  assert.ok(text.endsWith('}\n'));
  assert.ok(text.includes('\n  "audience": "family",'));
  assert.deepEqual(JSON.parse(text), defaults());
});

test('buildPrompt asks for the create-game skill and carries the config JSON, in the page language', () => {
  const today = new Date(2026, 9, 6);
  const config = configWith({ 'theme.idea': 'Cake heist' });
  const prompt = configForm.buildPrompt(config, 'en', today);
  assert.match(prompt, /create-game/);
  assert.match(prompt, /mystery-forge-cake-heist\.mystery-config\.json/);
  const json = prompt.split('```json\n')[1]?.split('\n```')[0] ?? '';
  assert.deepEqual(JSON.parse(json), config);
  assert.match(configForm.buildPrompt(config, 'es', today), /^Crea un juego/);
  assert.match(configForm.buildPrompt(config, 'en'), /```json/);
});

test('parseConfigFile fills the defaults of a valid file, also with a byte order mark', () => {
  const parsed = configForm.parseConfigFile('﻿{"schema_version": 1, "players": {"count": 3}}');
  assert.deepEqual(parsed.errors, []);
  assert.equal(parsed.config?.players.count, 3);
  assert.equal(parsed.config?.difficulty, 'medium');
});

test('parseConfigFile returns the findings of an invalid file and no config', () => {
  const parsed = configForm.parseConfigFile('{"schema_version": 1, "players": {"count": 40}}');
  assert.equal(parsed.config, null);
  assert.deepEqual(
    parsed.errors.map((finding) => [finding.path, finding.keyword]),
    [['players.count', 'maximum']],
  );
});

test('parseConfigFile reports text that is not JSON', () => {
  const parsed = configForm.parseConfigFile('not json {');
  assert.equal(parsed.config, null);
  assert.deepEqual(
    parsed.errors.map((finding) => [finding.path, finding.keyword]),
    [['', 'json']],
  );
});

test('describeFinding names the field and the limit in the page language', () => {
  /**
   * @param {string} text
   * @param {string} language
   * @returns {string[]}
   */
  function describe(text, language) {
    return configForm.parseConfigFile(text).errors.map((finding) => configForm.describeFinding(finding, language));
  }
  assert.deepEqual(describe('{"schema_version": 1, "players": {"count": 40}}', 'en'), [
    'Number of players: the value must be 12 or less.',
  ]);
  assert.deepEqual(describe('{"schema_version": 1, "players": {"count": 40}}', 'es'), [
    'Número de jugadores: el valor debe ser 12 o menos.',
  ]);
  assert.deepEqual(describe(`{"schema_version": 1, "players": {"names": ["${'x'.repeat(41)}"]}}`, 'en'), [
    'Player names: the text must have 40 characters or fewer.',
  ]);
  assert.deepEqual(describe('{"schema_version": 1, "players": {"nickname": "x"}}', 'en'), [
    'players.nickname: this setting is unknown.',
  ]);
  assert.deepEqual(describe('{}', 'en'), ['Config version: this value is missing.']);
  assert.deepEqual(describe('[]', 'en'), ['The file: the value has the wrong type.']);
  assert.deepEqual(describe('nope', 'en'), ['The file is not valid JSON text.']);
  assert.equal(
    configForm.describeFinding({ path: 'audience', keyword: 'pattern', message: 'Raw message.' }, 'en'),
    'Raw message.',
  );
});

test('saveDraft and loadDraft keep the config and the page language', () => {
  const storage = fakeStorage();
  const config = configWith({ 'players.count': 5 });
  assert.equal(configForm.saveDraft(storage, { config, uiLanguage: 'es' }), true);
  assert.deepEqual(configForm.loadDraft(storage), { config, uiLanguage: 'es' });
  configForm.clearDraft(storage);
  assert.equal(configForm.loadDraft(storage), null);
});

test('loadDraft ignores a broken, invalid, or old draft, and fills new defaults', () => {
  const storage = fakeStorage();
  const [key] = (() => {
    configForm.saveDraft(storage, { config: defaults(), uiLanguage: 'en' });
    return [...storage.items.keys()];
  })();
  const draftKey = String(key);
  storage.items.set(draftKey, 'not json');
  assert.equal(configForm.loadDraft(storage), null);
  storage.items.set(
    draftKey,
    JSON.stringify({ config: { schema_version: 1, players: { count: 0 } }, uiLanguage: 'en' }),
  );
  assert.equal(configForm.loadDraft(storage), null);
  storage.items.set(draftKey, JSON.stringify({ config: { schema_version: 1 }, uiLanguage: 'xx' }));
  assert.deepEqual(configForm.loadDraft(storage), { config: defaults(), uiLanguage: 'en' });
  storage.items.set(draftKey, '{}');
  assert.equal(configForm.loadDraft(storage), null);
  storage.items.set(draftKey, 'null');
  assert.equal(configForm.loadDraft(storage), null);
});

test('the draft helpers survive a storage that throws', () => {
  assert.equal(configForm.saveDraft(brokenStorage, { config: defaults(), uiLanguage: 'en' }), false);
  assert.equal(configForm.loadDraft(brokenStorage), null);
  assert.doesNotThrow(() => configForm.clearDraft(brokenStorage));
});

test('applyFieldChange applies the audience preset for a new audience, and sets any other field as it is', () => {
  const audienceChange = configForm.applyFieldChange(defaults(), 'audience', 'kids');
  assert.equal(audienceChange.presetApplied, true);
  assert.deepEqual(audienceChange.config, configForm.applyAudiencePreset(defaults(), 'kids'));
  const otherChange = configForm.applyFieldChange(defaults(), 'difficulty', 'hard');
  assert.equal(otherChange.presetApplied, false);
  assert.deepEqual(otherChange.config, configWith({ difficulty: 'hard' }));
});
