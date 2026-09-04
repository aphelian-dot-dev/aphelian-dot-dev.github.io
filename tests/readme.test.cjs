const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const readme = fs.readFileSync(path.join(__dirname, '..', 'README.md'), 'utf8');

test('README records the requested future run-history and meteor-achievement goals', () => {
  assert.match(readme, /Future goals/i);
  assert.match(readme, /cookie|local storage/i);
  assert.match(readme, /previous runs/i);
  assert.match(readme, /compare/i);
  assert.match(readme, /meteor achievement/i);
});
