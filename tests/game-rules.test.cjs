const test = require('node:test');
const assert = require('node:assert/strict');

const rules = require('../game-rules.js');

test('health diamonds represent five 20-percent health slivers', () => {
  const cases = [
    [100, 5],
    [81, 5],
    [80, 4],
    [61, 4],
    [60, 3],
    [41, 3],
    [40, 2],
    [21, 2],
    [20, 1],
    [1, 1],
    [0, 0],
    [-10, 0]
  ];

  for (const [health, expected] of cases) {
    assert.equal(rules.healthDiamondCount(health), expected, `${health}% health`);
  }
});

test('achievement catalog contains the six requested run feats and difficulties', () => {
  assert.deepEqual(
    rules.ACHIEVEMENTS.map(({ id, difficulty }) => [id, difficulty]),
    [
      ['no-damage', 'VERY HARD'],
      ['under-two-minutes', 'MEDIUM'],
      ['no-movement', 'VERY HARD'],
      ['wounded-unhealed', 'HARD'],
      ['chain-20', 'MEDIUM'],
      ['no-reversal', 'EASY']
    ]
  );
});

function unlocked(stats, id) {
  return rules.evaluateAchievements(stats).find(achievement => achievement.id === id).unlocked;
}

test('no-damage achievement tracks whether any Vital Light was lost', () => {
  assert.equal(unlocked({ damageTaken: 0 }, 'no-damage'), true);
  assert.equal(unlocked({ damageTaken: 1 }, 'no-damage'), false);
});

test('under-two-minutes achievement requires a win before 120 seconds', () => {
  assert.equal(unlocked({ won: true, time: 119.99 }, 'under-two-minutes'), true);
  assert.equal(unlocked({ won: true, time: 120 }, 'under-two-minutes'), false);
  assert.equal(unlocked({ won: false, time: 90 }, 'under-two-minutes'), false);
});

test('no-movement achievement requires a win with no movement input', () => {
  assert.equal(unlocked({ won: true, moved: false }, 'no-movement'), true);
  assert.equal(unlocked({ won: true, moved: true }, 'no-movement'), false);
  assert.equal(unlocked({ won: false, moved: false }, 'no-movement'), false);
});

test('wounded-unhealed achievement requires a wounded win with no healing', () => {
  assert.equal(unlocked({ won: true, health: 99, healed: false }, 'wounded-unhealed'), true);
  assert.equal(unlocked({ won: true, health: 100, healed: false }, 'wounded-unhealed'), false);
  assert.equal(unlocked({ won: true, health: 70, healed: true }, 'wounded-unhealed'), false);
  assert.equal(unlocked({ won: false, health: 70, healed: false }, 'wounded-unhealed'), false);
});

test('chain-20 achievement unlocks at a best chain of twenty', () => {
  assert.equal(unlocked({ bestChain: 20 }, 'chain-20'), true);
  assert.equal(unlocked({ bestChain: 19 }, 'chain-20'), false);
});

test('no-reversal achievement tracks whether Retrograde was used', () => {
  assert.equal(unlocked({ reversals: 0 }, 'no-reversal'), true);
  assert.equal(unlocked({ reversals: 1 }, 'no-reversal'), false);
});

test('rarest achievement selects the highest unlocked difficulty', () => {
  const evaluated = rules.evaluateAchievements({
    won: true,
    time: 80,
    damageTaken: 10,
    health: 70,
    healed: false,
    moved: true,
    bestChain: 20,
    reversals: 0
  });
  const rarest = rules.rarestAchievement(evaluated);
  assert.equal(rarest.id, 'wounded-unhealed');
  assert.equal(rules.rarestAchievement(evaluated.map(item => ({ ...item, unlocked: false }))), null);
});

test('share text includes score, best chain, rite time, and rarest achievement', () => {
  const achievements = rules.evaluateAchievements({
    won: true,
    time: 80,
    damageTaken: 10,
    health: 70,
    healed: false,
    moved: true,
    bestChain: 20,
    reversals: 0
  });
  assert.equal(
    rules.buildShareText({ score: 12345.9, bestChain: 20, time: 80, achievements }),
    'APHELION // THE LAST ORRERY\nScore: 012345\nBest Chain: ×20\nRite: 01:20\nRarest Achievement: WOUNDED / NEVER HEALED [HARD]\nhttps://aphelian.dev'
  );
});

test('one meteor becomes due four seconds into each pre-totality wave', () => {
  assert.equal(rules.meteorWaveDue(3.99, []), null);
  assert.equal(rules.meteorWaveDue(4, []), 0);
  assert.equal(rules.meteorWaveDue(19, [0]), null);
  assert.equal(rules.meteorWaveDue(24, [0]), 1);
  assert.equal(rules.meteorWaveDue(44, [0, 1]), 2);
  assert.equal(rules.meteorWaveDue(64, [0, 1, 2]), null);
});

test('a meteor is destroyed on its third hit and not before', () => {
  let hitsRemaining = 3;
  hitsRemaining = rules.applyMeteorHit(hitsRemaining);
  assert.equal(hitsRemaining, 2);
  hitsRemaining = rules.applyMeteorHit(hitsRemaining);
  assert.equal(hitsRemaining, 1);
  hitsRemaining = rules.applyMeteorHit(hitsRemaining);
  assert.equal(hitsRemaining, 0);
  assert.equal(rules.applyMeteorHit(hitsRemaining), 0);
});

test('meteor travel speed is slightly slower than normal player movement', () => {
  const playerSpeed = rules.defaultPlayerMaxSpeed(1920, 1080);
  const meteorSpeed = rules.meteorTravelSpeed(1920, 1080);
  assert.equal(playerSpeed, 285);
  assert.equal(meteorSpeed, playerSpeed * 0.82);
  assert.ok(meteorSpeed < playerSpeed);
});

test('destroying a meteor grants a five-second orbit boost', () => {
  assert.equal(rules.METEOR_BOOST_DURATION, 5);
});
