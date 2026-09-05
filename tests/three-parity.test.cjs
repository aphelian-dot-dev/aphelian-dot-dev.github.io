const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'upstream/index.html'), 'utf8');
const rework = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const block = (html, name) => {
  const start = html.indexOf(`    function ${name}(`);
  assert.notEqual(start, -1, name);
  const rest = html.slice(start);
  const end = rest.slice(5).search(/\n    (?:async )?function /);
  assert.notEqual(end, -1, name);
  return rest.slice(0, end + 5);
};
const mechanics = ['createRunStats','createPlayer','resetGame','startGame','pauseGame','resumeGame','endGame','renderAchievements','awardScore','update','updatePlayer','calculateOrbs','beginFold','endFold','castOrbit','retrograde','updateSpawning','edgeSpawn','spawnMeteor','spawnEnemy','spawnBoss','updateEnemy','updateRam','updateBoss','resolveCombat','hitEnemy','shatterMeteor','killEnemy','spawnPickup','hurtPlayer','updateVitalEchoes','updatePickups','spawnInkBurst','spawnWave','updateFx','clearInputs'];
const impactOnly = new Set(['castOrbit','retrograde','spawnBoss','updateBoss','hurtPlayer']);
for (const name of mechanics) test(`3D retains upstream ${name} gameplay`, () => {
  let actual=block(rework,name), expected=block(source,name);
  if(impactOnly.has(name)) {
    // Permit only removal of these explicitly requested non-impact shake cues.
    expected=expected.replace(/^[ \t]*game\.shake = .*;\n/gm,'');
  }
  if(name==='renderAchievements') actual=actual.replace('        view: selectedView,\n','');
  if(['startGame','resumeGame'].includes(name)) {
    expected=expected.replace(`    function ${name}() {`, `    function ${name}() {\n      if (selectedView === "3d" && graphicsLost) return;`);
  }
  for (const change of JSON.parse(fs.readFileSync(path.join(root,'overheat-patches.json'),'utf8'))) {
    if(change.function===name) {
      assert.ok(expected.includes(change.old), `Missing scoped baseline: ${name}`);
      expected=expected.replace(change.old,change.new);
    }
  }
  assert.equal(actual,expected);
});
test('the embedded renderer and vendored engine match their offline source files', () => {
  for (const [id, filename] of [['orrery3DSource','renderer-3d.js'],['threeLibrary','vendor/three.min.js']]) {
    assert.equal(rework.match(new RegExp(`<script id="${id}">([\\s\\S]*?)</script>`))[1].trim(), fs.readFileSync(path.join(root, filename), 'utf8').trim());
  }
});
