// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// Classic browser scripts, not modules: load them for their side effect, by a computed path that tsc does not resolve.
require(path.join(__dirname, 'configSchemaValidator.js'));
require(path.join(__dirname, 'gameConfigSchema.js'));
const validator = globalThis.MysteryForgeConfigValidator;

const CONTRACTS_PATH = path.join(__dirname, '..', 'contracts');
/** @type {MysteryForgeJsonSchema} */
const schema = JSON.parse(fs.readFileSync(path.join(CONTRACTS_PATH, 'game-config.schema.json'), 'utf8'));
/** @type {{valid: {name: string, config: unknown, normalized_summary: Record<string, unknown>}[], invalid: {name: string, config: unknown, error_paths: string[]}[]}} */
const vectors = JSON.parse(fs.readFileSync(path.join(CONTRACTS_PATH, 'config-vectors.json'), 'utf8'));

/**
 * @param {unknown} document
 * @param {string} dottedPath
 * @returns {unknown}
 */
function readDottedPath(document, dottedPath) {
  return dottedPath.split('.').reduce((value, key) => /** @type {Record<string, unknown>} */ (value)[key], document);
}

test('the contract uses only the keywords that the validator supports', () => {
  assert.deepEqual(validator.listUnsupportedKeywords(schema), []);
});

test('listUnsupportedKeywords finds keywords outside the subset at every depth, once each', () => {
  const unsupported = {
    type: 'object',
    pattern: 'x',
    properties: {
      name: { type: 'string', minLength: 1, pattern: 'y' },
      tags: { type: 'array', items: { type: 'string', format: 'email' } },
    },
  };
  assert.deepEqual(validator.listUnsupportedKeywords(unsupported), ['format', 'minLength', 'pattern']);
});

test('the generated schema script holds the same schema as the contract', () => {
  assert.deepEqual(globalThis.MysteryForgeGameConfigSchema, schema);
});

for (const vector of vectors.valid) {
  test(`validateConfig accepts the shared vector "${vector.name}"`, () => {
    assert.deepEqual(validator.validateConfig(schema, vector.config), []);
  });

  test(`applyDefaults fills the shared vector "${vector.name}"`, () => {
    const filled = validator.applyDefaults(schema, vector.config);
    for (const [dottedPath, expected] of Object.entries(vector.normalized_summary)) {
      assert.deepEqual(readDottedPath(filled, dottedPath), expected, dottedPath);
    }
  });
}

for (const vector of vectors.invalid) {
  test(`validateConfig rejects the shared vector "${vector.name}" at the expected paths`, () => {
    const findings = validator.validateConfig(schema, vector.config);
    const paths = [...new Set(findings.map((finding) => finding.path))].sort();
    assert.deepEqual(paths, vector.error_paths);
    for (const finding of findings) {
      assert.ok(finding.message.length > 0);
    }
  });
}

test('a finding names the keyword that failed, and the findings are sorted by path', () => {
  const findings = validator.validateConfig(schema, {
    schema_version: 1,
    players: { nickname: 'x', count: 0 },
    audience: 3,
  });
  assert.deepEqual(
    findings.map((finding) => [finding.path, finding.keyword]),
    [
      ['audience', 'enum'],
      ['audience', 'type'],
      ['players.count', 'minimum'],
      ['players.nickname', 'additionalProperties'],
    ],
  );
});

test('a missing required key is reported at its own path', () => {
  assert.deepEqual(validator.validateConfig(schema, {}), [
    { path: 'schema_version', keyword: 'required', message: 'This value is required.' },
  ]);
});

test('each JSON type matches its own values only', () => {
  /** @type {[string, unknown[], unknown[]][]} */
  const cases = [
    ['object', [{}], [[], null, 'x']],
    ['array', [[]], [{}, 'x']],
    ['string', ['x'], [1, null]],
    ['integer', [1, -3, 2.0], [1.5, '1', true]],
    ['number', [1, 1.5], ['1', false]],
    ['boolean', [true, false], [0, 'true']],
    ['null', [null], [0, undefined]],
    ['unknown-type', [], [null, 1]],
  ];
  for (const [type, matching, other] of cases) {
    for (const value of matching) {
      assert.deepEqual(validator.validateConfig({ type }, value), [], `${type} accepts ${String(value)}`);
    }
    for (const value of other) {
      const findings = validator.validateConfig({ type }, value);
      assert.deepEqual(
        findings.map((finding) => finding.keyword),
        ['type'],
        `${type} rejects ${String(value)}`,
      );
    }
  }
});

test('an object schema without additionalProperties false accepts unknown keys', () => {
  assert.deepEqual(validator.validateConfig({ type: 'object', properties: {} }, { extra: 1 }), []);
});

test('applyDefaults returns a new object and never shares a default list', () => {
  const raw = { schema_version: 1, players: { count: 2 } };
  const first = /** @type {{players: {names: string[]}}} */ (validator.applyDefaults(schema, raw));
  const second = /** @type {{players: {names: string[]}}} */ (validator.applyDefaults(schema, raw));
  assert.deepEqual(raw, { schema_version: 1, players: { count: 2 } });
  assert.notEqual(first.players.names, second.players.names);
  assert.notEqual(first.players.names, schema.properties?.players?.properties?.names?.default);
});

test('applyDefaults keeps unknown keys, skips a key without a default, and copies a value that is not an object', () => {
  /** @type {MysteryForgeJsonSchema} */
  const smallSchema = {
    type: 'object',
    properties: { requiredKey: { type: 'integer' }, filled: { type: 'string', default: 'x' } },
  };
  const unknownList = [1];
  const filled = /** @type {{unknown: number[]}} */ (validator.applyDefaults(smallSchema, { unknown: unknownList }));
  assert.deepEqual(filled, { filled: 'x', unknown: [1] });
  assert.notEqual(filled.unknown, unknownList);
  assert.equal(validator.applyDefaults(smallSchema, 5), 5);
  assert.deepEqual(validator.applyDefaults({ type: 'object' }, { a: 1 }), { a: 1 });
});
