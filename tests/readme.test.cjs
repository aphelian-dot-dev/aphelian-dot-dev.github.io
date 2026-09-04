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

test('README records the requested future run-history and meteor-achievement goals', () => {
  assert.match(readme, /Future goals/i);
  assert.match(readme, /cookie|local storage/i);
  assert.match(readme, /previous runs/i);
  assert.match(readme, /compare/i);
  assert.match(readme, /meteor achievement/i);
});
