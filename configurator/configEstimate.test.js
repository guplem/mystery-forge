// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

// Classic browser scripts, not modules: load them for their side effect, by a computed path that tsc does not resolve.
require(path.join(__dirname, 'configEstimate.js'));
require(path.join(__dirname, 'configSchemaValidator.js'));
const configEstimate = globalThis.MysteryForgeConfigEstimate;
const validator = globalThis.MysteryForgeConfigValidator;

const CONTRACTS_PATH = path.join(__dirname, '..', 'contracts');
/** @type {MysteryForgeJsonSchema} */
const schema = JSON.parse(fs.readFileSync(path.join(CONTRACTS_PATH, 'game-config.schema.json'), 'utf8'));
/** @type {{vectors: {name: string, input: MysteryForgeEstimateInput, expected: MysteryForgeEstimate}[]}} */
const estimateVectors = JSON.parse(fs.readFileSync(path.join(CONTRACTS_PATH, 'estimate-vectors.json'), 'utf8'));
/** @type {{valid: {name: string, config: unknown}[]}} */
const configVectors = JSON.parse(fs.readFileSync(path.join(CONTRACTS_PATH, 'config-vectors.json'), 'utf8'));

for (const vector of estimateVectors.vectors) {
  test(`estimate matches the shared vector "${vector.name}"`, () => {
    assert.deepEqual(configEstimate.estimate(vector.input), vector.expected);
  });
}

for (const vector of configVectors.valid) {
  test(`estimateFromConfig reads the filled config of the shared vector "${vector.name}"`, () => {
    const config = /** @type {MysteryForgeEstimateConfig} */ (validator.applyDefaults(schema, vector.config));
    const result = configEstimate.estimateFromConfig(config);
    assert.deepEqual(
      result,
      configEstimate.estimate({
        players: config.players.count,
        duration_minutes: config.duration_minutes,
        difficulty: config.difficulty,
        audience: config.audience,
        format: config.format,
        quality: config.generation.quality,
        reading_load: config.content.reading_load,
      }),
    );
    for (const value of Object.values(result)) {
      assert.ok(Number.isInteger(value));
    }
  });
}
