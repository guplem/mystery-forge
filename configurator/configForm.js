// @ts-check
// The decisions of the configurator page, kept out of app.js so that unit tests cover them: the form model derived
// from the schema, the audience presets, the warnings, the prompt, the file name, file loading, and the saved draft.
// The schema (gameConfigSchema.js) is the one source of fields, enums, limits, and defaults; this file adds only the
// layout of the page and the presentation of each field.

(function registerConfigForm() {
  const DRAFT_STORAGE_KEY = 'mystery-forge.configurator.draft.v1';
  const MAX_SLUG_LENGTH = 40;

  /** The page sections in order, each with the dotted paths of its fields. */
  const SECTIONS = [
    { id: 'players', collapsed: false, fields: ['audience', 'players.count', 'players.names', 'host'] },
    { id: 'game', collapsed: false, fields: ['format', 'duration_minutes', 'difficulty', 'language'] },
    {
      id: 'story',
      collapsed: false,
      fields: [
        'theme.idea',
        'theme.tone',
        'theme.era',
        'content.death_allowed',
        'content.scary_level',
        'content.reading_load',
      ],
    },
    {
      id: 'personal',
      collapsed: true,
      fields: [
        'personalization.host_name',
        'personalization.place',
        'personalization.inside_jokes',
        'personalization.dedication',
      ],
    },
    {
      id: 'puzzles',
      collapsed: false,
      fields: [
        'puzzle_preferences.words',
        'puzzle_preferences.numbers',
        'puzzle_preferences.logic',
        'puzzle_preferences.visual',
        'puzzle_preferences.crafts',
        'puzzle_preferences.deduction',
      ],
    },
    {
      id: 'printing',
      collapsed: false,
      fields: [
        'equipment.printer',
        'equipment.ink_saving',
        'equipment.paper',
        'equipment.scissors',
        'equipment.tape_or_glue',
        'equipment.envelopes',
      ],
    },
    { id: 'look', collapsed: false, fields: ['visuals.style', 'visuals.images', 'visuals.readable_font'] },
    {
      id: 'help',
      collapsed: false,
      fields: ['assistance.hints', 'assistance.paper_answer_check', 'assistance.companion_page'],
    },
    {
      id: 'generation',
      collapsed: false,
      fields: ['generation.quality', 'generation.pick_concept', 'output.folder', 'generation.seed'],
    },
  ];

  /** Fields whose widget differs from the one that the schema type implies. */
  /** @type {Record<string, MysteryForgeFieldWidget>} */
  const WIDGET_OVERRIDES = {
    audience: 'cards',
    format: 'cards',
    host: 'cards',
    'visuals.style': 'cards',
    language: 'select',
    'players.count': 'stepper',
    duration_minutes: 'range',
    'theme.idea': 'textarea',
  };
  /** @type {Record<string, number>} */
  const RANGE_STEPS = { duration_minutes: 15 };
  const ADVANCED_FIELDS = new Set(['generation.quality', 'generation.seed']);
  const LETTER_PAPER_REGIONS = ['us', 'ca'];

  /** What each audience preset changes, by dotted path. A choice that the preset does not name keeps its value. */
  /** @type {Record<string, Record<string, unknown>>} */
  const AUDIENCE_PRESETS = {
    kids: {
      difficulty: 'easy',
      duration_minutes: 60,
      'content.reading_load': 'light',
      'content.death_allowed': false,
      'content.scary_level': 'none',
      'visuals.style': 'kids',
      'visuals.readable_font': true,
    },
    family: {
      difficulty: 'medium',
      duration_minutes: 90,
      'content.reading_load': 'light',
      'content.death_allowed': false,
      'content.scary_level': 'mild',
      'visuals.style': 'auto',
      'visuals.readable_font': false,
    },
    teens: {
      difficulty: 'medium',
      duration_minutes: 90,
      'content.reading_load': 'medium',
      'content.death_allowed': true,
      'content.scary_level': 'mild',
      'visuals.style': 'auto',
      'visuals.readable_font': false,
    },
    adults: {
      difficulty: 'hard',
      duration_minutes: 120,
      'content.reading_load': 'medium',
      'content.death_allowed': true,
      'content.scary_level': 'mild',
      'visuals.style': 'auto',
      'visuals.readable_font': false,
    },
    puzzle_fans: {
      difficulty: 'expert',
      duration_minutes: 120,
      'content.reading_load': 'light',
      'content.death_allowed': true,
      'content.scary_level': 'mild',
      'visuals.style': 'minimal',
      'visuals.readable_font': false,
    },
  };

  /**
   * @typedef {object} WarningRule
   * @property {string} id
   * @property {'warning' | 'info'} severity
   * @property {string} path
   * @property {(config: MysteryForgeGameConfig) => boolean} applies
   * @property {(config: MysteryForgeGameConfig) => Record<string, string | number>} [params]
   */

  /** @type {WarningRule[]} */
  const WARNING_RULES = [
    {
      id: 'kids_death',
      severity: 'warning',
      path: 'content.death_allowed',
      applies: (config) => config.audience === 'kids' && config.content.death_allowed,
    },
    {
      id: 'kids_spooky',
      severity: 'warning',
      path: 'content.scary_level',
      applies: (config) => config.audience === 'kids' && config.content.scary_level === 'spooky',
    },
    {
      id: 'solo_game_master',
      severity: 'warning',
      path: 'host',
      applies: (config) => config.players.count === 1 && config.host === 'game_master',
    },
    {
      id: 'many_players_no_game_master',
      severity: 'info',
      path: 'host',
      applies: (config) => config.players.count > 8 && config.host !== 'game_master',
    },
    {
      id: 'more_names_than_players',
      severity: 'info',
      path: 'players.names',
      applies: (config) => config.players.names.length > config.players.count,
      params: (config) => ({ count: config.players.count }),
    },
    {
      id: 'short_expert',
      severity: 'warning',
      path: 'duration_minutes',
      applies: (config) => config.difficulty === 'expert' && config.duration_minutes <= 45,
    },
    {
      id: 'all_puzzles_avoided',
      severity: 'warning',
      path: 'puzzle_preferences',
      applies: (config) => Object.values(config.puzzle_preferences).every((preference) => preference === 'avoid'),
    },
    {
      id: 'crafts_without_scissors',
      severity: 'warning',
      path: 'equipment.scissors',
      applies: (config) => !config.equipment.scissors && config.puzzle_preferences.crafts === 'like',
    },
    {
      id: 'no_scissors',
      severity: 'info',
      path: 'equipment.scissors',
      applies: (config) => !config.equipment.scissors && config.puzzle_preferences.crafts !== 'like',
    },
    {
      id: 'envelopes_without_envelopes',
      severity: 'info',
      path: 'equipment.envelopes',
      applies: (config) => config.format === 'envelopes' && !config.equipment.envelopes,
    },
    {
      id: 'colors_go_gray',
      severity: 'info',
      path: 'visuals.style',
      applies: (config) => config.equipment.printer === 'black_and_white' && config.visuals.style === 'kids',
    },
    {
      id: 'no_help',
      severity: 'warning',
      path: 'assistance.hints',
      applies: (config) =>
        !config.assistance.hints && !config.assistance.paper_answer_check && !config.assistance.companion_page,
    },
  ];

  /** @returns {MysteryForgeJsonSchema} */
  function schema() {
    return globalThis.MysteryForgeGameConfigSchema;
  }

  /**
   * @param {string} language
   * @param {string} key
   * @param {Record<string, string | number>} [params]
   * @returns {string}
   */
  function text(language, key, params) {
    return globalThis.MysteryForgeUiText.translate(language, key, params);
  }

  /**
   * @param {string} key
   * @returns {boolean}
   */
  function hasText(key) {
    return key in globalThis.MysteryForgeUiText.TEXTS.en;
  }

  /**
   * Return the schema node of a dotted path. A number step enters the `items` schema of an array.
   * @param {string} fieldPath
   * @returns {MysteryForgeJsonSchema | undefined}
   */
  function schemaAtPath(fieldPath) {
    /** @type {MysteryForgeJsonSchema | undefined} */
    let node = schema();
    for (const part of fieldPath.split('.')) {
      node = /^\d+$/.test(part) ? node?.items : node?.properties?.[part];
    }
    return node;
  }

  /**
   * @param {MysteryForgeJsonSchema} node
   * @returns {MysteryForgeFieldWidget}
   */
  function widgetFromSchema(node) {
    if (node.enum) {
      return 'segmented';
    }
    if (node.type === 'boolean') {
      return 'toggle';
    }
    if (node.type === 'integer') {
      return 'number';
    }
    return node.type === 'array' ? 'list' : 'text';
  }

  /**
   * @param {string} fieldPath
   * @param {string} language
   * @returns {MysteryForgeFormField}
   */
  function buildField(fieldPath, language) {
    const node = /** @type {MysteryForgeJsonSchema} */ (schemaAtPath(fieldPath));
    const placeholderKey = `field.${fieldPath}.placeholder`;
    return {
      path: fieldPath,
      widget: WIDGET_OVERRIDES[fieldPath] ?? widgetFromSchema(node),
      label: text(language, `field.${fieldPath}.label`),
      help: text(language, `field.${fieldPath}.help`),
      placeholder: hasText(placeholderKey) ? text(language, placeholderKey) : '',
      options: (node.enum ?? []).map((value) => ({
        value: String(value),
        label: text(language, `enum.${fieldPath}.${String(value)}.label`),
        help: text(language, `enum.${fieldPath}.${String(value)}.help`),
      })),
      minimum: node.minimum ?? 0,
      maximum: node.maximum ?? 0,
      step: RANGE_STEPS[fieldPath] ?? 1,
      maxLength: node.maxLength ?? node.items?.maxLength ?? 0,
      maxItems: node.maxItems ?? 0,
      advanced: ADVANCED_FIELDS.has(fieldPath),
    };
  }

  /**
   * Return the sections of the page, each with its fields, in the page language.
   * @param {string} language
   * @returns {MysteryForgeFormSection[]}
   */
  function buildFormModel(language) {
    return SECTIONS.map((section) => ({
      id: section.id,
      title: text(language, `section.${section.id}.title`),
      intro: text(language, `section.${section.id}.intro`),
      collapsed: section.collapsed,
      fields: section.fields.map((fieldPath) => buildField(fieldPath, language)),
    }));
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @returns {unknown}
   */
  function getAtPath(config, fieldPath) {
    /** @type {unknown} */
    let value = config;
    for (const part of fieldPath.split('.')) {
      value = /** @type {Record<string, unknown> | undefined} */ (value)?.[part];
    }
    return value;
  }

  /**
   * @param {string} value
   * @param {number | undefined} maxLength
   * @returns {string}
   */
  function cutText(value, maxLength) {
    // Count code points, as the schema validator does, so an emoji never splits in half.
    return maxLength === undefined ? value : [...value].slice(0, maxLength).join('');
  }

  /**
   * Turn a raw value from the page (often text) into the schema type, inside the schema limits. A number that does
   * not parse keeps the current value.
   * @param {MysteryForgeJsonSchema} node
   * @param {unknown} rawValue
   * @param {unknown} currentValue
   * @returns {unknown}
   */
  function coerceValue(node, rawValue, currentValue) {
    if (node.type === 'integer') {
      const parsed = Math.round(Number(rawValue));
      if (!Number.isFinite(parsed)) {
        return currentValue;
      }
      return Math.min(node.maximum ?? parsed, Math.max(node.minimum ?? parsed, parsed));
    }
    if (node.type === 'boolean') {
      return Boolean(rawValue);
    }
    if (node.type === 'array') {
      const items = Array.isArray(rawValue) ? rawValue : [];
      return items.slice(0, node.maxItems).map((item) => cutText(String(item), node.items?.maxLength));
    }
    return cutText(String(rawValue), node.maxLength);
  }

  /**
   * Return a new config where the field at `fieldPath` holds the raw value, coerced to the schema type and limits.
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @param {unknown} rawValue
   * @returns {MysteryForgeGameConfig}
   */
  function setFieldValue(config, fieldPath, rawValue) {
    const node = schemaAtPath(fieldPath);
    if (!node) {
      throw new Error(`The config has no field "${fieldPath}".`);
    }
    const updated = structuredClone(config);
    const parts = fieldPath.split('.');
    const lastPart = /** @type {string} */ (parts.pop());
    const parent = /** @type {Record<string, unknown>} */ (getAtPath(updated, parts.join('.')) ?? updated);
    parent[lastPart] = coerceValue(node, rawValue, parent[lastPart]);
    return updated;
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @returns {number}
   */
  function textLength(config, fieldPath) {
    // Count code points, as the schema validator does, so the counter and the limit agree on emoji.
    return [...String(getAtPath(config, fieldPath))].length;
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @returns {string[]}
   */
  function listAt(config, fieldPath) {
    return /** @type {string[]} */ (getAtPath(config, fieldPath));
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @returns {boolean}
   */
  function isListFull(config, fieldPath) {
    // A list without maxItems gives NaN, and a comparison with NaN is false: such a list is never full.
    return listAt(config, fieldPath).length >= Number(schemaAtPath(fieldPath)?.maxItems);
  }

  /**
   * Add trimmed text to a list field. Blank text, or a full list, leaves the config as it is.
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @param {string} itemText
   * @returns {MysteryForgeGameConfig}
   */
  function addListItem(config, fieldPath, itemText) {
    const trimmed = itemText.trim();
    if (trimmed === '' || isListFull(config, fieldPath)) {
      return config;
    }
    return setFieldValue(config, fieldPath, [...listAt(config, fieldPath), trimmed]);
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @param {number} index
   * @returns {MysteryForgeGameConfig}
   */
  function removeListItem(config, fieldPath, index) {
    return setFieldValue(
      config,
      fieldPath,
      listAt(config, fieldPath).filter((_, itemIndex) => itemIndex !== index),
    );
  }

  /**
   * @param {unknown} value
   * @returns {MysteryForgeGameConfig}
   */
  function filledConfig(value) {
    return /** @type {MysteryForgeGameConfig} */ (
      globalThis.MysteryForgeConfigValidator.applyDefaults(schema(), value)
    );
  }

  /**
   * Return the paper size that suits a game language. Only English for a browser in the United States or Canada gets
   * Letter; the rest of the world uses A4.
   * @param {string} gameLanguage
   * @param {readonly string[]} browserLanguages
   * @returns {string}
   */
  function defaultPaper(gameLanguage, browserLanguages) {
    const region = browserLanguages[0]?.toLowerCase().split('-')[1] ?? '';
    return gameLanguage === 'en' && LETTER_PAPER_REGIONS.includes(region) ? 'Letter' : 'A4';
  }

  /**
   * Return the schema defaults, with the game language and the paper size taken from the browser languages.
   * @param {readonly string[]} browserLanguages
   * @returns {MysteryForgeGameConfig}
   */
  function initialConfig(browserLanguages) {
    const versionNode = /** @type {MysteryForgeJsonSchema} */ (schemaAtPath('schema_version'));
    let config = filledConfig({ schema_version: versionNode.enum?.[0] });
    const gameLanguages = /** @type {unknown[]} */ (schemaAtPath('language')?.enum);
    const gameLanguage = browserLanguages
      .map((browserLanguage) => browserLanguage.toLowerCase().split('-')[0])
      .find((base) => gameLanguages.includes(base));
    if (gameLanguage) {
      config = setFieldValue(config, 'language', gameLanguage);
    }
    return setFieldValue(config, 'equipment.paper', defaultPaper(config.language, browserLanguages));
  }

  /**
   * Let the game language follow a new page language, with the paper size that suits it. The game language counts as
   * chosen by the user when it differs from the old page language, and a chosen game language stays. In the same way,
   * a paper size that differs from the default of the old game language stays.
   * @param {MysteryForgeGameConfig} config
   * @param {string} oldUiLanguage
   * @param {string} newUiLanguage
   * @param {readonly string[]} browserLanguages
   * @returns {{config: MysteryForgeGameConfig, followed: boolean}}
   */
  function followPageLanguage(config, oldUiLanguage, newUiLanguage, browserLanguages) {
    if (config.language !== oldUiLanguage || oldUiLanguage === newUiLanguage) {
      return { config, followed: false };
    }
    let updated = setFieldValue(config, 'language', newUiLanguage);
    if (config.equipment.paper === defaultPaper(oldUiLanguage, browserLanguages)) {
      updated = setFieldValue(updated, 'equipment.paper', defaultPaper(newUiLanguage, browserLanguages));
    }
    return { config: updated, followed: true };
  }

  /**
   * Set the audience and the choices that suit it. The player count and every other choice keep their values.
   * @param {MysteryForgeGameConfig} config
   * @param {string} audience
   * @returns {MysteryForgeGameConfig}
   */
  function applyAudiencePreset(config, audience) {
    const preset = AUDIENCE_PRESETS[audience] ?? {};
    return Object.entries(preset).reduce((updated, [fieldPath, value]) => setFieldValue(updated, fieldPath, value), {
      ...structuredClone(config),
      audience,
    });
  }

  /**
   * Apply a change that the user made on the page. A new audience also applies the preset of that audience.
   * @param {MysteryForgeGameConfig} config
   * @param {string} fieldPath
   * @param {unknown} rawValue
   * @returns {{config: MysteryForgeGameConfig, presetApplied: boolean}}
   */
  function applyFieldChange(config, fieldPath, rawValue) {
    if (fieldPath === 'audience') {
      return { config: applyAudiencePreset(config, String(rawValue)), presetApplied: true };
    }
    return { config: setFieldValue(config, fieldPath, rawValue), presetApplied: false };
  }

  /**
   * Return the combinations of choices that work badly, in a fixed order.
   * @param {MysteryForgeGameConfig} config
   * @returns {MysteryForgeConfigWarning[]}
   */
  function configWarnings(config) {
    return WARNING_RULES.filter((rule) => rule.applies(config)).map((rule) => ({
      id: rule.id,
      severity: rule.severity,
      path: rule.path,
      params: rule.params?.(config) ?? {},
    }));
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @returns {boolean}
   */
  function showsSurpriseNote(config) {
    return config.theme.idea.trim() === '';
  }

  /**
   * @param {number} minutes
   * @returns {string}
   */
  function formatMinutes(minutes) {
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    if (hours === 0) {
      return `${rest} min`;
    }
    return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
  }

  /**
   * The generation time, rounded to 10 minutes: the estimate is rough, and "2 h 37 min" would look exact.
   * @param {MysteryForgeGameConfig} config
   * @param {string} language
   * @returns {string}
   */
  function generationTimeText(config, language) {
    const minutes = globalThis.MysteryForgeConfigEstimate.estimateFromConfig(config).generation_minutes;
    return text(language, 'estimate.about', { time: formatMinutes(Math.round(minutes / 10) * 10) });
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @param {string} language
   * @returns {MysteryForgeEstimateItem[]}
   */
  function estimateItems(config, language) {
    const estimate = globalThis.MysteryForgeConfigEstimate.estimateFromConfig(config);
    // A case file without envelopes still has stages; the player sees them as chapters.
    const stageKey = config.format === 'case_file' ? 'estimate.chapters' : 'estimate.envelopes';
    return [
      { id: 'puzzles', label: text(language, 'estimate.puzzles'), value: String(estimate.puzzle_count) },
      { id: 'stages', label: text(language, stageKey), value: String(estimate.stage_count) },
      { id: 'pages', label: text(language, 'estimate.pages'), value: String(estimate.printed_pages) },
      {
        id: 'play_time',
        label: text(language, 'estimate.play_time'),
        value: formatMinutes(config.duration_minutes),
      },
      { id: 'generation', label: text(language, 'estimate.generation'), value: generationTimeText(config, language) },
    ];
  }

  /**
   * The short line of the phone bar: the puzzle count and the play time.
   * @param {MysteryForgeGameConfig} config
   * @param {string} language
   * @returns {string}
   */
  function summaryBarText(config, language) {
    const estimate = globalThis.MysteryForgeConfigEstimate.estimateFromConfig(config);
    return text(language, 'summary.bar', {
      puzzles: estimate.puzzle_count,
      time: formatMinutes(config.duration_minutes),
    });
  }

  /**
   * @param {Date} date
   * @returns {string}
   */
  function localIsoDate(date) {
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${date.getFullYear()}-${month}-${day}`;
  }

  /**
   * @param {string} idea
   * @returns {string}
   */
  function slugOf(idea) {
    const slug = idea
      .normalize('NFD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '');
    if (slug.length <= MAX_SLUG_LENGTH) {
      return slug;
    }
    // Look one character past the limit: a dash there means that the last word ends exactly at the limit.
    const head = slug.slice(0, MAX_SLUG_LENGTH + 1);
    const lastDash = head.lastIndexOf('-');
    return lastDash > 0 ? head.slice(0, lastDash) : slug.slice(0, MAX_SLUG_LENGTH);
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @param {Date} [today]
   * @returns {string}
   */
  function configFileName(config, today = new Date()) {
    const slug = slugOf(config.theme.idea) || localIsoDate(today);
    return `mystery-forge-${slug}.mystery-config.json`;
  }

  /**
   * @param {MysteryForgeGameConfig} config
   * @returns {string}
   */
  function configFileText(config) {
    return `${JSON.stringify(config, null, 2)}\n`;
  }

  /**
   * The text that the user pastes into the agent, in the page language.
   * @param {MysteryForgeGameConfig} config
   * @param {string} language
   * @param {Date} [today]
   * @returns {string}
   */
  function buildPrompt(config, language, today = new Date()) {
    return [
      text(language, 'prompt.intro'),
      text(language, 'prompt.run_skill', { fileName: configFileName(config, today) }),
      text(language, 'prompt.questions'),
      '',
      '```json',
      configFileText(config).trimEnd(),
      '```',
    ].join('\n');
  }

  /**
   * Parse a config file: JSON, then the schema check, then the defaults. Any finding means no config.
   * @param {string} fileText
   * @returns {MysteryForgeParsedConfig}
   */
  function parseConfigFile(fileText) {
    /** @type {unknown} */
    let raw;
    try {
      // Windows editors often save JSON with a byte order mark, which JSON.parse rejects.
      raw = JSON.parse(fileText.replace(/^﻿/, ''));
    } catch {
      return { config: null, errors: [{ path: '', keyword: 'json', message: 'The file is not valid JSON.' }] };
    }
    const errors = globalThis.MysteryForgeConfigValidator.validateConfig(schema(), raw);
    return { config: errors.length > 0 ? null : filledConfig(raw), errors };
  }

  /**
   * Explain a finding in the page language, with the field label and the limit. A keyword without a text keeps the
   * English message of the validator.
   * @param {MysteryForgeConfigFinding} finding
   * @param {string} language
   * @returns {string}
   */
  function describeFinding(finding, language) {
    const messageKey = `error.${finding.keyword}`;
    if (!hasText(messageKey)) {
      return finding.message;
    }
    const fieldPath = finding.path
      .split('.')
      .filter((part) => !/^\d+$/.test(part))
      .join('.');
    const labelKey = `field.${fieldPath}.label`;
    let field = finding.path;
    if (finding.path === '') {
      field = text(language, 'error.whole_file');
    } else if (hasText(labelKey)) {
      field = text(language, labelKey);
    }
    const node = /** @type {Record<string, unknown>} */ (schemaAtPath(finding.path) ?? {});
    return text(language, messageKey, { field, limit: String(node[finding.keyword] ?? '') });
  }

  /**
   * Save the draft. Storage can throw (private mode, a full disk), so a failure returns false and nothing else.
   * @param {MysteryForgeDraftStorage} storage
   * @param {MysteryForgeDraft} draft
   * @returns {boolean}
   */
  function saveDraft(storage, draft) {
    try {
      storage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Return the saved draft with the current defaults filled in, or null when there is none or when it is not valid.
   * @param {MysteryForgeDraftStorage} storage
   * @returns {MysteryForgeDraft | null}
   */
  function loadDraft(storage) {
    try {
      const saved = /** @type {{config?: unknown, uiLanguage?: unknown} | null} */ (
        JSON.parse(storage.getItem(DRAFT_STORAGE_KEY) ?? 'null')
      );
      if (saved === null) {
        return null;
      }
      const parsed = parseConfigFile(JSON.stringify(saved.config ?? null));
      if (parsed.config === null) {
        return null;
      }
      const languages = /** @type {readonly unknown[]} */ (globalThis.MysteryForgeUiText.UI_LANGUAGES);
      const uiLanguage = languages.includes(saved.uiLanguage)
        ? /** @type {MysteryForgeUiLanguage} */ (saved.uiLanguage)
        : 'en';
      return { config: parsed.config, uiLanguage };
    } catch {
      return null;
    }
  }

  /**
   * @param {MysteryForgeDraftStorage} storage
   * @returns {void}
   */
  function clearDraft(storage) {
    try {
      storage.removeItem(DRAFT_STORAGE_KEY);
    } catch {
      // A storage that throws holds no draft to clear.
    }
  }

  globalThis.MysteryForgeConfigForm = {
    SECTIONS,
    AUDIENCE_PRESETS,
    buildFormModel,
    initialConfig,
    followPageLanguage,
    getAtPath,
    setFieldValue,
    addListItem,
    removeListItem,
    isListFull,
    textLength,
    applyAudiencePreset,
    applyFieldChange,
    configWarnings,
    showsSurpriseNote,
    formatMinutes,
    estimateItems,
    summaryBarText,
    generationTimeText,
    configFileName,
    configFileText,
    buildPrompt,
    parseConfigFile,
    describeFinding,
    saveDraft,
    loadDraft,
    clearDraft,
  };
})();
