// @ts-check
// Assembles the GitHub Pages site (https://guplem.github.io/mystery-forge/) in one folder: the project page from
// site/, the configurator page, and the screenshots. The Pages workflow uploads that folder.
// Usage: `npm run build:site`, or `node scripts/build-site.js <output folder>`.

const fs = require('node:fs');
const path = require('node:path');

const REPO_ROOT = path.join(__dirname, '..');
const DEFAULT_OUTPUT = path.join(REPO_ROOT, '_site');

/**
 * Each entry copies the files of one repo folder into one site folder. `keep` picks the files that the site serves.
 * @type {{ from: string, to: string, keep: (name: string) => boolean }[]}
 */
const SITE_FOLDERS = [
  { from: 'site', to: '.', keep: () => true },
  // The tests and the agent docs stay out: the page needs only its HTML, its CSS, and its scripts.
  {
    from: 'configurator',
    to: 'configurator',
    keep: (name) => /\.(html|css|js)$/.test(name) && !name.endsWith('.test.js'),
  },
  { from: path.join('docs', 'images'), to: 'images', keep: (name) => name.endsWith('.png') },
];

/**
 * Return the site files as pairs of a source path and a path inside the site, sorted by the site path.
 * @param {string} repoRoot
 * @returns {{ source: string, target: string }[]}
 */
function siteFiles(repoRoot) {
  return SITE_FOLDERS.flatMap(({ from, to, keep }) =>
    fs
      .readdirSync(path.join(repoRoot, from))
      .filter(keep)
      .map((name) => ({ source: path.join(repoRoot, from, name), target: path.posix.join(to, name) })),
  ).sort((first, second) => first.target.localeCompare(second.target));
}

/**
 * Copy the site into `outputFolder`, which starts empty, and return the paths inside the site.
 * @param {string} repoRoot
 * @param {string} outputFolder
 * @returns {string[]}
 */
function buildSite(repoRoot, outputFolder) {
  fs.rmSync(outputFolder, { recursive: true, force: true });
  const files = siteFiles(repoRoot);
  for (const { source, target } of files) {
    const destination = path.join(outputFolder, target);
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
  }
  return files.map((file) => file.target);
}

/**
 * Return the local links (href and src) of an HTML page: every link that names no scheme, no anchor, and no host.
 * @param {string} html
 * @returns {string[]}
 */
function localLinks(html) {
  return [...html.matchAll(/(?:href|src)="([^"]+)"/g)]
    .map((match) => /** @type {string} */ (match[1]))
    .filter((link) => !/^(?:[a-z]+:|#|\/\/)/i.test(link));
}

/**
 * Return the output folder: the first command-line argument, else `_site` at the repo root.
 * @param {string[]} argv
 * @returns {string}
 */
function resolveOutputFolder(argv) {
  return argv[2] ?? DEFAULT_OUTPUT;
}

if (require.main === module) {
  buildSite(REPO_ROOT, resolveOutputFolder(process.argv));
}

module.exports = { buildSite, siteFiles, localLinks, resolveOutputFolder, REPO_ROOT, DEFAULT_OUTPUT };
