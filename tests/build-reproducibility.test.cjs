const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const root = path.join(__dirname, '..');

test('offline rebuild preserves the entire checked-in game, including branding and native sharing', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'aphelian-build-'));
  try {
    for (const name of ['build-3d.py', 'game-rules.js', 'overheat-patches.json', 'renderer-3d.js', 'view-controls.js', 'upstream', 'vendor']) {
      fs.cpSync(path.join(root, name), path.join(temp, name), { recursive: true });
    }
    const result = spawnSync('python3', [path.join(temp, 'build-3d.py')], { encoding: 'utf8', timeout: 30000 });
    assert.equal(result.status, 0, result.stderr || String(result.error || 'Build failed'));
    assert.ok(fs.readFileSync(path.join(temp, 'index.html')).equals(fs.readFileSync(path.join(root, 'index.html'))),
      'Rebuilding must not remove metadata, favicon links, native share changes, or mobile controls');
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});
