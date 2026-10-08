// @ts-check
const test = require('node:test');
const assert = require('node:assert/strict');
const childProcess = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const site = require('./build-site.js');

/** @type {string[]} */
const temporaryFolders = [];

/** @returns {string} */
function makeTemporaryFolder() {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'mystery-forge-site-'));
  temporaryFolders.push(folder);
  return folder;
}

test.after(() => {
  for (const folder of temporaryFolders) {
    fs.rmSync(folder, { recursive: true, force: true });
  }
});

test('the site holds the project page, the configurator, and the screenshots, without tests or agent docs', () => {
  const output = makeTemporaryFolder();
  fs.writeFileSync(path.join(output, 'stale.txt'), 'from an earlier build', 'utf8');
  const files = site.buildSite(site.REPO_ROOT, output);
  assert.ok(files.includes('index.html'));
  assert.ok(files.includes('configurator/index.html'));
  assert.ok(files.includes('configurator/app.js'));
  assert.ok(files.includes('images/configurator.png'));
  assert.ok(!files.some((file) => file.endsWith('.test.js') || file.endsWith('.md')));
  assert.ok(!fs.existsSync(path.join(output, 'stale.txt')));
  for (const file of files) {
    assert.ok(fs.statSync(path.join(output, file)).isFile(), file);
  }
});

test('every local link of every page points to a file of the site', () => {
  const output = makeTemporaryFolder();
  const files = new Set(site.buildSite(site.REPO_ROOT, output));
  for (const page of [...files].filter((file) => file.endsWith('.html'))) {
    const html = fs.readFileSync(path.join(output, page), 'utf8');
    for (const link of site.localLinks(html)) {
      const target = path.posix.normalize(path.posix.join(path.posix.dirname(page), link.split('#')[0] ?? ''));
      assert.ok(files.has(target), `${page} links to ${link}, which the site does not hold`);
    }
  }
});

test('localLinks keeps relative links and skips other sites, anchors, and data URLs', () => {
  const html =
    '<a href="configurator/index.html">x</a><img src="images/a.png"><a href="https://github.com">g</a>' +
    '<a href="#how">h</a><link href="data:image/svg+xml,x"><a href="//cdn.example">c</a>';
  assert.deepEqual(site.localLinks(html), ['configurator/index.html', 'images/a.png']);
});

test('the output folder is the first argument, else _site', () => {
  assert.equal(site.resolveOutputFolder(['node', 'build-site.js', 'out']), 'out');
  assert.equal(site.resolveOutputFolder(['node', 'build-site.js']), site.DEFAULT_OUTPUT);
});

test('running the script builds the site into the given folder', () => {
  const output = makeTemporaryFolder();
  childProcess.execFileSync(process.execPath, [path.join(__dirname, 'build-site.js'), output]);
  assert.ok(fs.existsSync(path.join(output, 'index.html')));
});
