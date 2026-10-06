// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');

const generator = require('./generate-config-schema.js');

const contractText = fs.readFileSync(generator.CONTRACT_PATH, 'utf8');

/** @type {string[]} */
const temporaryFolders = [];

/** @returns {string} */
function makeTemporaryFolder() {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'mystery-forge-schema-'));
  temporaryFolders.push(folder);
  return folder;
}

test.after(() => {
  for (const folder of temporaryFolders) {
    fs.rmSync(folder, { recursive: true, force: true });
  }
});

test('the committed configurator/gameConfigSchema.js is not stale (run `npm run generate:schema` to fix)', () => {
  assert.equal(fs.readFileSync(generator.SCHEMA_SCRIPT_PATH, 'utf8'), generator.buildSchemaScript(contractText));
});

test('buildSchemaScript marks the file as generated and assigns the parsed schema to one global', () => {
  const script = generator.buildSchemaScript('{"type": "object", "properties": {}}');
  assert.ok(script.startsWith('// GENERATED'));
  assert.ok(script.endsWith(';\n'));
  /** @type {Record<string, unknown>} */
  const sandbox = {};
  vm.runInNewContext(script, sandbox);
  // The object comes from another realm (another set of built-in prototypes), so compare its JSON form.
  assert.equal(JSON.stringify(sandbox['MysteryForgeGameConfigSchema']), '{"type":"object","properties":{}}');
});

test('writeSchemaScript writes the script for the contract to the given path', () => {
  const outPath = path.join(makeTemporaryFolder(), 'gameConfigSchema.js');
  generator.writeSchemaScript(outPath);
  assert.equal(fs.readFileSync(outPath, 'utf8'), generator.buildSchemaScript(contractText));
});

test('resolveOutputPath takes the first argument, else the committed configurator file', () => {
  assert.equal(generator.resolveOutputPath(['node', 'script.js', 'out.js']), 'out.js');
  assert.equal(generator.resolveOutputPath(['node', 'script.js']), generator.SCHEMA_SCRIPT_PATH);
});

test('the command line writes to the path in its first argument', () => {
  const outPath = path.join(makeTemporaryFolder(), 'gameConfigSchema.js');
  const result = childProcess.spawnSync(process.execPath, [path.join(__dirname, 'generate-config-schema.js'), outPath]);
  assert.equal(result.status, 0, String(result.stderr));
  assert.equal(fs.readFileSync(outPath, 'utf8'), generator.buildSchemaScript(contractText));
});
