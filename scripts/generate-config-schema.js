// @ts-check
// Copies contracts/game-config.schema.json into configurator/gameConfigSchema.js. The configurator page runs from
// file://, where it cannot read a JSON file, so it loads the schema as a classic script that sets one global.
// Usage: `npm run generate:schema`, or `node scripts/generate-config-schema.js <output path>`.

const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.join(__dirname, '..');
const CONTRACT_PATH = path.join(REPO_ROOT, 'contracts', 'game-config.schema.json');
const SCHEMA_SCRIPT_PATH = path.join(REPO_ROOT, 'configurator', 'gameConfigSchema.js');

/**
 * Return the text of the classic script that assigns the schema to `globalThis.MysteryForgeGameConfigSchema`.
 * @param {string} schemaText
 * @returns {string}
 */
function buildSchemaScript(schemaText) {
  const schema = JSON.parse(schemaText);
  return [
    '// GENERATED from contracts/game-config.schema.json by `npm run generate:schema`. Do not edit.',
    `globalThis.MysteryForgeGameConfigSchema = ${JSON.stringify(schema, null, 2)};`,
    '',
  ].join('\n');
}

/**
 * @param {string} outPath
 * @returns {void}
 */
function writeSchemaScript(outPath) {
  fs.writeFileSync(outPath, buildSchemaScript(fs.readFileSync(CONTRACT_PATH, 'utf8')), 'utf8');
}

/**
 * Return the output path: the first command-line argument, else the committed configurator file.
 * @param {string[]} argv
 * @returns {string}
 */
function resolveOutputPath(argv) {
  return argv[2] ?? SCHEMA_SCRIPT_PATH;
}

if (require.main === module) {
  writeSchemaScript(resolveOutputPath(process.argv));
}

module.exports = { buildSchemaScript, writeSchemaScript, resolveOutputPath, CONTRACT_PATH, SCHEMA_SCRIPT_PATH };
