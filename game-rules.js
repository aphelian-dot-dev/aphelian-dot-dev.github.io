(function exposeAphelionRules(root, factory) {
  const rules = factory();
  if (typeof module === "object" && module.exports) module.exports = rules;
  else root.AphelionRules = Object.freeze(rules);
})(typeof globalThis !== "undefined" ? globalThis : this, () => {
  "use strict";

  const METEOR_BOOST_DURATION = 5;
  const SCORE_HISTORY_LIMIT = 10;
  const SCORE_HISTORY_VERSION = 1;
  const ACHIEVEMENTS = Object.freeze([
    Object.freeze({
      id: "no-damage",
      title: "NO DAMAGE TAKEN",
      description: "Finish the run without losing Vital Light.",
      difficulty: "VERY HARD",
      rank: 4
    }),
    Object.freeze({
      id: "under-two-minutes",
      title: "RITE UNDER TWO MINUTES",
      description: "Seal the Black Sun in under two minutes.",
      difficulty: "MEDIUM",
      rank: 2
    }),
    Object.freeze({
      id: "no-movement",
      title: "RITE WITHOUT MOVING",
      description: "Finish without using movement controls.",
      difficulty: "VERY HARD",
      rank: 4
    }),
    Object.freeze({
      id: "wounded-unhealed",
      title: "WOUNDED / NEVER HEALED",
      description: "Finish below full health without recovering any.",
      difficulty: "HARD",
      rank: 3
    }),
    Object.freeze({
      id: "chain-20",
      title: "CHAIN ×20",
      description: "Reach a twenty-destruction chain.",
      difficulty: "MEDIUM",
      rank: 2
    }),
    Object.freeze({
      id: "no-reversal",
      title: "NEVER REVERSED COURSE",
      description: "Complete the run without Retrograde.",
      difficulty: "EASY",
      rank: 1
    })
  ]);

  function healthDiamondCount(health) {
    const value = Number.isFinite(Number(health)) ? Number(health) : 0;
    return Math.ceil(Math.max(0, Math.min(100, value)) / 20);
  }

  function nonNegativeFiniteNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.max(0, number) : 0;
  }

  function normalizeScoreRun(run = {}) {
    const time = nonNegativeFiniteNumber(run.time);
    return {
      score: Math.floor(nonNegativeFiniteNumber(run.score)),
      won: run.won === true,
      bestChain: Math.floor(nonNegativeFiniteNumber(run.bestChain)),
      time: time > Number.MAX_VALUE / 10 ? time : Math.round(time * 10) / 10,
      completedAt: typeof run.completedAt === "string" ? run.completedAt : ""
    };
  }

  function appendScoreHistory(history = {}, run = {}) {
    const previousRuns = Array.isArray(history.runs) ? history.runs : [];
    return {
      version: SCORE_HISTORY_VERSION,
      runs: [normalizeScoreRun(run), ...previousRuns.map(normalizeScoreRun)].slice(0, SCORE_HISTORY_LIMIT)
    };
  }

  function validStoredScoreNumber(value) {
    return typeof value === "number" && Number.isFinite(value) && value >= 0;
  }

  function validStoredScoreRun(run) {
    return Boolean(
      run
      && typeof run === "object"
      && !Array.isArray(run)
      && validStoredScoreNumber(run.score)
      && typeof run.won === "boolean"
      && validStoredScoreNumber(run.bestChain)
      && validStoredScoreNumber(run.time)
      && typeof run.completedAt === "string"
      && Number.isFinite(Date.parse(run.completedAt))
    );
  }

  function normalizeScoreHistory(history = {}) {
    const runs = history && history.version === SCORE_HISTORY_VERSION && Array.isArray(history.runs)
      ? history.runs
      : [];
    return {
      version: SCORE_HISTORY_VERSION,
      runs: runs
        .filter(validStoredScoreRun)
        .map(normalizeScoreRun)
        .slice(0, SCORE_HISTORY_LIMIT)
    };
  }

  function parseScoreHistory(serialized) {
    try { return normalizeScoreHistory(JSON.parse(serialized)); }
    catch (_) { return normalizeScoreHistory(); }
  }

  function parseStoredScoreHistory(serialized) {
    try {
      const history = JSON.parse(serialized);
      if (
        !history
        || typeof history !== "object"
        || history.version !== SCORE_HISTORY_VERSION
        || !Array.isArray(history.runs)
        || !history.runs.every(validStoredScoreRun)
      ) return null;
      return normalizeScoreHistory(history);
    } catch (_) {
      return null;
    }
  }

  function serializeScoreHistory(history) {
    return JSON.stringify(normalizeScoreHistory(history));
  }

  function evaluateAchievements(stats = {}) {
    const unlockedById = {
      "no-damage": (Number(stats.damageTaken) || 0) <= 0,
      "under-two-minutes": stats.won === true && Number(stats.time) < 120,
      "no-movement": stats.won === true && stats.moved !== true,
      "wounded-unhealed": stats.won === true
        && Number(stats.health) > 0
        && Number(stats.health) < 100
        && stats.healed !== true,
      "chain-20": Number(stats.bestChain) >= 20,
      "no-reversal": (Number(stats.reversals) || 0) === 0
    };
    return ACHIEVEMENTS.map(achievement => ({
      ...achievement,
      unlocked: Boolean(unlockedById[achievement.id])
    }));
  }

  function rarestAchievement(achievements = []) {
    return achievements.reduce((rarest, achievement) => {
      if (!achievement.unlocked) return rarest;
      if (!rarest || achievement.rank > rarest.rank) return achievement;
      return rarest;
    }, null);
  }

  function formatTime(seconds) {
    const whole = Math.max(0, Math.ceil(Number(seconds) || 0));
    return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
  }

  function buildShareText({ score = 0, bestChain = 0, time = 0, achievements = [] } = {}) {
    const rarest = rarestAchievement(achievements);
    const rarestLabel = rarest ? `${rarest.title} [${rarest.difficulty}]` : "NONE THIS RUN";
    const paddedScore = String(Math.max(0, Math.floor(Number(score) || 0))).padStart(6, "0");
    return [
      "APHELIAN // THE LAST ORRERY",
      `Score: ${paddedScore}`,
      `Best Chain: ×${Math.max(0, Math.floor(Number(bestChain) || 0))}`,
      `Rite: ${formatTime(time)}`,
      `Rarest Achievement: ${rarestLabel}`,
      "https://aphelian.dev"
    ].join("\n");
  }

  function defaultPlayerMaxSpeed(width, height) {
    const shortestSide = Math.min(Number(width) || 320, Number(height) || 320);
    return Math.min(285, Math.max(185, shortestSide * .34));
  }

  function meteorTravelSpeed(width, height) {
    return defaultPlayerMaxSpeed(width, height) * .82;
  }

  function applyMeteorHit(hitsRemaining) {
    return Math.max(0, Math.floor(Number(hitsRemaining) || 0) - 1);
  }

  function meteorWaveDue(time, spawnedWaves = []) {
    const elapsed = Number(time);
    if (!Number.isFinite(elapsed) || elapsed < 0) return null;
    const wave = Math.floor(elapsed / 20);
    if (wave >= 3 || elapsed < wave * 20 + 4) return null;
    const alreadySpawned = typeof spawnedWaves.has === "function"
      ? spawnedWaves.has(wave)
      : Array.from(spawnedWaves).includes(wave);
    return alreadySpawned ? null : wave;
  }

  return {
    ACHIEVEMENTS,
    METEOR_BOOST_DURATION,
    SCORE_HISTORY_LIMIT,
    SCORE_HISTORY_VERSION,
    applyMeteorHit,
    appendScoreHistory,
    buildShareText,
    defaultPlayerMaxSpeed,
    evaluateAchievements,
    formatTime,
    healthDiamondCount,
    meteorTravelSpeed,
    meteorWaveDue,
    parseScoreHistory,
    parseStoredScoreHistory,
    rarestAchievement,
    serializeScoreHistory
  };
});
