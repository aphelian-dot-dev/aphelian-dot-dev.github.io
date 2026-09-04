const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const rulesSource = fs.readFileSync(path.join(__dirname, '..', 'game-rules.js'), 'utf8');

test('startup console renders the archival Little Orrery sigil', () => {
  assert.match(html, /┌───────────────────────────────┐/);
  assert.match(html, /│\s+☾\s+│/);
  assert.match(html, /│\s+╱\s+◉\s+╲\s+│/);
  assert.match(html, /│\s+☾───────────☽\s+│/);
  assert.match(html, /│  APHELIAN \/\/ THE LAST ORRERY  │/);
  assert.match(html, /│  THE OBSERVATORY REMEMBERS\.   │/);
  assert.match(html, /└───────────────────────────────┘/);
  assert.doesNotMatch(html, /THIS GAME NEEDS JAVASCRIPT TO AWAKEN THE ORRERY/);
});

test('visible game branding uses Aphelian', () => {
  assert.match(html, /<title>APHELIAN — The Last Orrery<\/title>/);
  assert.match(html, /aria-label="Aphelian, a celestial-sorcery defense game"/);
  assert.match(html, /<h1 id="mainTitle">APHELIAN<\/h1>/);
  assert.match(html, /Aphelian Sweep/);
  assert.doesNotMatch(html, /APHELION/);
});

test('browser rules are embedded exactly so a portal-exposed index works alone', () => {
  const embedded = html.match(/<script id="aphelionRulesSource">([\s\S]*?)<\/script>/);
  assert.ok(embedded, 'expected an inline Aphelion rules script');
  assert.equal(embedded[1], `\n${rulesSource}`);
  assert.doesNotMatch(html, /<script src="game-rules\.js"><\/script>/);
});

test('boss fight has no deadline and the HUD tracks total rite time', () => {
  assert.doesNotMatch(html, /const TOTALITY =/);
  assert.doesNotMatch(html, /TOTAL ECLIPSE/);
  assert.match(html, /const displayedTime = game\.phase < 3 \? Math\.max\(0, BOSS_TIME - game\.time\) : game\.time;/);
  assert.match(html, /game\.phase < 3 \? "TOTALITY APPROACHES" : "RITE ELAPSED"/);
  assert.match(html, /if \(p\.hp <= 0\) endGame\(false, "VITAL LIGHT EXTINGUISHED"\);/);
  assert.match(rulesSource, /stats\.won === true && Number\(stats\.time\) < 120/);
});

test('ordinary score sources share a two-minute cutoff while boss rewards remain guaranteed', () => {
  assert.match(html, /const RITE_SCORE_WINDOW = 120;/);
  assert.match(html, /function awardScore\(points, guaranteed = false\)/);
  assert.deepEqual(
    [...html.matchAll(/game\.score \+= ([^;]+);/g)].map(match => match[1]),
    ['awarded']
  );
  assert.match(html, /awardScore\(dt \* \(8 \+ game\.phase \* 2\)\);/);
  assert.match(html, /awardScore\(175\);/);
  assert.match(html, /const awarded = awardScore\(points, e\.boss\);/);
  assert.match(html, /awardScore\(250\);/);
  assert.match(html, /awardScore\(5000 \+ Math\.round\(Math\.max\(0, SPEED_BONUS_WINDOW - game\.time\) \* 100\), true\);/);
});

test('player Vital Light is rendered as five diamond health slivers', () => {
  assert.match(html, /function drawVitalDiamonds\(p, pad, bottom, compact\)/);
  assert.match(html, /AphelionRules\.healthDiamondCount\(p\.hp\)/);
  assert.match(html, /for \(let i = 0; i < 5; i\+\+\)/);
  assert.doesNotMatch(html, /function drawVitalBar\(/);
});

test('post-run achievement panel evaluates all tracked run conditions', () => {
  assert.match(html, /id="achievementList"/);
  assert.match(html, /id="achievementCount">0 \/ 7<\/strong>/);
  const renderer = html.match(/function renderAchievements\(won\) \{([\s\S]*?)\n    function shareRun\(\)/);
  assert.ok(renderer, 'expected the post-run achievement renderer');
  assert.match(renderer[1], /AphelionRules\.evaluateAchievements\(/);
  assert.match(renderer[1], /game\.runStats\.damageTaken/);
  assert.match(renderer[1], /game\.runStats\.moved/);
  assert.match(renderer[1], /game\.runStats\.healed/);
  assert.match(renderer[1], /score: game\.score/);
  assert.match(renderer[1], /game\.runStats\.reversals/);
  assert.match(html, /Math\.min\(99, game\.chain \+ 1\)/);
});

test('result screen exposes a share action with native and clipboard paths', () => {
  assert.match(html, /id="shareButton"/);
  assert.match(html, /\.overlay\[data-state="result"\] \.share-button/);
  assert.match(html, /function shareRun\(\)/);
  assert.match(html, /AphelionRules\.buildShareText\(/);
  assert.match(html, /navigator\.share/);
  assert.match(html, /navigator\.clipboard\.writeText/);
  assert.match(html, /shareButton\.addEventListener\("click", shareRun\)/);
});

test('a harmless three-hit meteor appears once per wave and grants a five-second orbit boost', () => {
  assert.match(html, /function spawnMeteor\(wave\)/);
  assert.match(html, /AphelionRules\.meteorWaveDue\(game\.time, game\.meteorWavesSpawned\)/);
  assert.match(html, /hitsRemaining: 3/);
  assert.match(html, /AphelionRules\.applyMeteorHit\(e\.hitsRemaining\)/);
  assert.match(html, /p\.orbitBoostTime = AphelionRules\.METEOR_BOOST_DURATION/);
  assert.match(html, /e\.type !== "meteor" && !e\.dead && p\.invuln <= 0/);
  assert.match(html, /p\.orbitBoostTime > 0 \? 1\.3 : 0/);
});

test('result screen reports the actual best chain, including zero', () => {
  assert.match(html, /resultChain\.textContent = `×\$\{game\.bestChain\}`/);
  assert.doesNotMatch(html, /resultChain\.textContent = `×\$\{Math\.max\(1, game\.bestChain\)\}`/);
});

test('achievement names get a full-width column on narrow portrait screens', () => {
  assert.match(html, /@media \(max-width: 420px\)/);
  assert.match(html, /\.overlay\[data-state="result"\] \.achievement-list \{ grid-template-columns: 1fr; \}/);
});

test('score archive consent and history expose accessible labels', () => {
  assert.match(
    html,
    /id="scoreConsent" class="score-consent" role="group" aria-labelledby="scoreConsentQuestion" aria-describedby="scoreConsentPurpose"/
  );
  assert.match(html, /id="scoreConsentQuestion" class="score-ask"/);
  assert.match(html, /id="scoreConsentPurpose" class="score-purpose"/);
  assert.match(html, /id="scoreHistoryList" class="score-history-list" aria-label="Saved rites, most recent first"/);
});

test('score archive is consent-gated and uses only its disclosed cookie', () => {
  assert.match(html, /const SCORE_COOKIE_NAME = "aphelian_score_history";/);
  assert.match(html, /const SCORE_COOKIE_MAX_AGE = 60 \* 60 \* 24 \* 365;/);
  assert.match(html, /Path=\/; SameSite=Strict/);
  assert.match(html, /location\.protocol === "https:" \? "; Secure" : ""/);
  assert.match(html, /rememberScoresButton\.addEventListener\("click", enableScoreArchive\)/);
  assert.match(html, /const scoreSaveResult = recordCompletedRun\(won\);/);
  assert.match(html, /forgetScoresButton\.addEventListener\("click", forgetScoreArchive\)/);
  assert.doesNotMatch(html, /localStorage|sessionStorage/);
  assert.match(html, /No name or unique identifier is stored\./);
  assert.match(html, /browser includes it in requests to this site/);
});

test('score archive clearly discloses rolling one-year renewal', () => {
  assert.match(
    html,
    /id="scoreConsentPurpose"[^>]*>[^<]*one-year Max-Age renews after each saved rite/i
  );
  assert.match(html, /older entries may remain longer than one year while you continue saving/i);
});

test('cookie details disclose synchronization and incompatible-cookie controls', () => {
  const details = html.match(/<details id="scoreCookieDetails"[\s\S]*?<\/details>/);
  assert.ok(details, 'expected cookie details disclosure');
  assert.match(details[0], /Web Locks/i);
  assert.match(details[0], /malformed or unsupported-version/i);
  assert.match(details[0], /will not[^<]*overwrit/i);
  assert.match(html, /id="removeBlockedScoreCookieButton"[^>]*>Remove incompatible cookie<\/button>/);
});

test('cookie-derived score rows use text-only DOM construction', () => {
  const renderer = html.match(/function renderScoreArchive\(\) \{([\s\S]*?)\n    function showScoreConsent\(\)/);
  assert.ok(renderer, 'expected the score archive renderer');
  assert.match(renderer[1], /document\.createElement\("li"\)/);
  assert.match(renderer[1], /\.textContent =/);
  assert.match(renderer[1], /scoreHistoryList\.replaceChildren\(fragment\)/);
  assert.doesNotMatch(renderer[1], /innerHTML|outerHTML|insertAdjacentHTML|document\.write/);
});
