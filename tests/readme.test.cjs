const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const readme = fs.readFileSync(path.join(__dirname, '..', 'README.md'), 'utf8');

test('README introduces Aphelian and explains how to play locally', () => {
  assert.match(readme, /^# APHELIAN — The Last Orrery/m);
  assert.match(readme, /## Gameplay/);
  assert.match(readme, /no time limit/i);
  assert.match(readme, /under two minutes/i);
  assert.match(readme, /## Controls/);
  assert.match(readme, /python3 -m http\.server 8000/);
  assert.match(readme, /node --test tests\/\*\.test\.cjs/);
});

test('README documents the optional score-history cookie and local preview requirement', () => {
  assert.match(readme, /## Optional score archive/i);
  assert.match(readme, /aphelian_score_history/);
  assert.match(readme, /up to 10 completed rites/i);
  assert.match(readme, /one year/i);
  assert.match(readme, /no account, advertising, analytics, or cross-site tracking/i);
  assert.match(readme, /requires an HTTP or HTTPS origin/i);
});

test('README discloses that one-year cookie expiry renews after saved rites', () => {
  assert.match(readme, /one-year `Max-Age` renews after each saved rite/i);
  assert.match(readme, /older entries may remain longer than one year while saving continues/i);
});

test('README documents fail-closed synchronization and incompatible-cookie removal', () => {
  assert.match(readme, /Web Locks/i);
  assert.match(readme, /unavailable[^.]*archive remains off/i);
  assert.match(readme, /malformed or unsupported-version/i);
  assert.match(readme, /will not[^.]*overwrite/i);
  assert.match(readme, /remove[^.]*DevTools[^.]*site-data settings/i);
});

test('README retains the future meteor-achievement goal', () => {
  assert.match(readme, /Future goals/i);
  assert.match(readme, /meteor achievement/i);
});
