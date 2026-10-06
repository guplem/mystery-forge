// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

// A classic browser script, not a module: load it for its side effect, by a computed path that tsc does not resolve.
require(path.join(__dirname, 'answers.js'));
const answers = globalThis.MysteryForgeAnswers;

/** @type {{salt: string, normalization: {language: string, input: string, expected: string}[], hashes: {normalized: string, expected_sha256: string}[]}} */
const contract = JSON.parse(
  fs.readFileSync(path.join(__dirname, '..', '..', '..', '..', '..', 'contracts', 'answer-vectors.json'), 'utf8'),
);

for (const vector of contract.normalization) {
  test(`normalizeAnswer matches the shared vector ${vector.language}:${JSON.stringify(vector.input)}`, () => {
    assert.equal(answers.normalizeAnswer(vector.input, vector.language), vector.expected);
  });
}

for (const vector of contract.hashes) {
  test(`answerHash matches the shared vector ${JSON.stringify(vector.normalized)}`, () => {
    assert.equal(answers.answerHash(vector.normalized, contract.salt), vector.expected_sha256);
  });
}

test('sha256Hex matches Node crypto for text longer than one 64-byte block and for non-ASCII text', () => {
  const samples = ['', 'abc', 'x'.repeat(55), 'x'.repeat(56), 'x'.repeat(64), 'y'.repeat(200), 'señal ✓ 灯台'];
  for (const sample of samples) {
    const expected = crypto.createHash('sha256').update(sample, 'utf8').digest('hex');
    assert.equal(answers.sha256Hex(sample), expected, `sample of length ${sample.length}`);
  }
});
