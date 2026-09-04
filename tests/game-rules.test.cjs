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
    'APHELIAN // THE LAST ORRERY\nScore: 012345\nBest Chain: ×20\nRite: 01:20\nRarest Achievement: WOUNDED / NEVER HEALED [HARD]\nhttps://aphelian.dev'
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

test('score archive stores a normalized completed run newest first', () => {
  const previous = {
    version: 1,
    runs: [{
      score: 75,
      won: false,
      bestChain: 2,
      time: 30,
      completedAt: '2026-09-03T12:00:00.000Z'
    }]
  };

  const history = rules.appendScoreHistory(previous, {
    score: 123.9,
    won: true,
    bestChain: 4.8,
    time: 65.67,
    completedAt: '2026-09-04T12:00:00.000Z'
  });

  assert.deepEqual(history, {
    version: 1,
    runs: [
      {
        score: 123,
        won: true,
        bestChain: 4,
        time: 65.7,
        completedAt: '2026-09-04T12:00:00.000Z'
      },
      previous.runs[0]
    ]
  });
});

test('score archive keeps only the ten most recent runs', () => {
  let history = { version: 1, runs: [] };
  for (let score = 1; score <= 12; score += 1) {
    history = rules.appendScoreHistory(history, {
      score,
      won: false,
      bestChain: 0,
      time: score,
      completedAt: `2026-09-${String(score).padStart(2, '0')}T12:00:00.000Z`
    });
  }

  assert.equal(history.runs.length, 10);
  assert.deepEqual(history.runs.map(run => run.score), [12, 11, 10, 9, 8, 7, 6, 5, 4, 3]);
});

test('score archive serializes and parses its documented JSON shape', () => {
  const history = {
    version: 1,
    runs: [{
      score: 9321,
      won: true,
      bestChain: 14,
      time: 87.4,
      completedAt: '2026-09-04T13:00:00.000Z'
    }]
  };

  const serialized = rules.serializeScoreHistory(history);
  assert.equal(serialized, JSON.stringify(history));
  assert.deepEqual(rules.parseScoreHistory(serialized), history);
});

test('score archive treats malformed or unknown cookie data as empty', () => {
  const empty = { version: 1, runs: [] };
  assert.deepEqual(rules.parseScoreHistory('{not-json'), empty);
  assert.deepEqual(rules.parseScoreHistory(JSON.stringify({ version: 2, runs: [{ score: 99 }] })), empty);
  assert.deepEqual(
    rules.parseScoreHistory(JSON.stringify({
      version: 1,
      runs: [null, 'bad', { score: 'not-number', won: false, bestChain: 0, time: 2, completedAt: 'not-a-date' }]
    })),
    empty
  );
});

test('stored score archive rejects coerced and negative numeric fields', () => {
  const validRun = {
    score: 100,
    won: true,
    bestChain: 5,
    time: 42.5,
    completedAt: '2026-09-04T13:00:00.000Z'
  };
  const invalidValues = [null, true, false, [], [1], '7', -1];

  for (const field of ['score', 'bestChain', 'time']) {
    for (const value of invalidValues) {
      const serialized = JSON.stringify({
        version: 1,
        runs: [{ ...validRun, [field]: value }]
      });
      assert.equal(
        rules.parseStoredScoreHistory(serialized),
        null,
        `${field} must reject ${JSON.stringify(value)}`
      );
    }
  }
});

test('score archive keeps finite huge values finite while normalizing', () => {
  const history = rules.parseScoreHistory(JSON.stringify({
    version: 1,
    runs: [{
      score: 1e308,
      won: true,
      bestChain: 1e308,
      time: 1e308,
      completedAt: '2026-09-04T13:00:00.000Z'
    }]
  }));

  assert.equal(history.runs.length, 1);
  assert.equal(history.runs[0].time, 1e308);
  assert.ok(Object.values(history.runs[0]).every(value => typeof value !== 'number' || Number.isFinite(value)));
  assert.doesNotMatch(rules.serializeScoreHistory(history), /null/);
});
