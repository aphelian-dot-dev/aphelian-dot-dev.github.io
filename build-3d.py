"""Bundle both renderers into one portal-safe, offline game; preserve simulation."""
from pathlib import Path
import re
import json

ROOT = Path(__file__).resolve().parent
html = (ROOT / 'upstream/index.html').read_text()

def replace(old, new):
    global html
    assert html.count(old) == 1, old[:100]
    html = html.replace(old, new, 1)

# Preserve the public branding/share additions when rebuilding frozen upstream.
replace('  <title>APHELIAN — The Last Orrery</title>', '''  <meta name="description" content="Command three Ward Moons. Seal the Black Sun in APHELIAN — The Last Orrery.">
  <link rel="icon" href="favicon.svg" type="image/svg+xml">
  <link rel="icon" href="favicon-32x32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="apple-touch-icon.png" sizes="180x180">
  <link rel="manifest" href="site.webmanifest">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://aphelian.dev/">
  <meta property="og:site_name" content="Aphelian">
  <meta property="og:title" content="APHELIAN — The Last Orrery">
  <meta property="og:description" content="Command three Ward Moons. Seal the Black Sun.">
  <meta property="og:image" content="https://aphelian.dev/social-preview.png">
  <meta property="og:image:secure_url" content="https://aphelian.dev/social-preview.png">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="The Little Orrery emblem beside the title APHELIAN — The Last Orrery">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="APHELIAN — The Last Orrery">
  <meta name="twitter:description" content="Command three Ward Moons. Seal the Black Sun.">
  <meta name="twitter:image" content="https://aphelian.dev/social-preview.png">
  <title>APHELIAN — The Last Orrery</title>''')
replace('''      if (typeof navigator.share === "function") {
        navigator.share({ title: "APHELIAN // THE LAST ORRERY", text })''', r'''      const shareUrl = "https://aphelian.dev/";
      const shareUrlText = shareUrl.replace(/\/$/, "");
      const nativeText = text.endsWith(shareUrlText)
        ? text.slice(0, -shareUrlText.length).trimEnd()
        : text;
      if (typeof navigator.share === "function") {
        navigator.share({ title: "APHELIAN // THE LAST ORRERY", text: nativeText, url: shareUrl })''')

# The local achievement catalog is authoritative for both Node and standalone play.
rules_start = html.index('<script id="aphelionRulesSource">')
rules_end = html.index('</script>', rules_start)
replace(html[rules_start:rules_end], '<script id="aphelionRulesSource">\n' + (ROOT / 'game-rules.js').read_text())
replace('''      const achievements = AphelionRules.evaluateAchievements({
        won,''', '''      const achievements = AphelionRules.evaluateAchievements({
        won,
        view: selectedView,''')
replace('id="achievementCount">0 / 7', 'id="achievementCount">0 / 8')

# Only successful weapon contacts may initiate camera shake. Keep other feedback.
for function in ['castOrbit', 'retrograde', 'spawnBoss', 'updateBoss', 'hurtPlayer']:
    start = html.index(f'    function {function}(')
    end = html.index('\n    function ', start + 1)
    block, removed = re.subn(r'^[ \t]*game\.shake = .*;\n', '', html[start:end], flags=re.M)
    assert removed == 1, function
    html = html[:start] + block + html[end:]

# Scoped gameplay/presentation changes are listed for auditable parity coverage.
for change in json.loads((ROOT / 'overheat-patches.json').read_text()):
    if change['function']:
        start = html.index(f"    function {change['function']}(")
        end = html.index('\n    function ', start + 1)
        block = html[start:end]
        assert block.count(change['old']) == 1, change
        html = html[:start] + block.replace(change['old'], change['new'], 1) + html[end:]
    else:
        replace(change['old'], change['new'])

vendor = (ROOT / 'vendor/three.min.js').read_text()
renderer = (ROOT / 'renderer-3d.js').read_text()
controls = (ROOT / 'view-controls.js').read_text()
replace('  <script id="aphelionRulesSource">', '<script id="threeLibrary">\n' + vendor + '\n</script>\n<script id="orrery3DSource">\n' + renderer + '\n</script>\n  <script id="aphelionRulesSource">')
replace('    const ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });', '    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });\n' + controls)
replace('      buildBackground();\n      grainPattern', '      buildBackground();\n      view3D?.resize(W, H, DPR);\n      grainPattern')

# Keep the actual upstream 2D renderer, rather than a flattened 3D imitation.
a = html.index('      ctx.drawImage(backgroundLayer, 0, 0, W, H);', html.index('    function draw(realDt)'))
b = html.index('      if (game.player && game.mode === "playing") drawHUD();', a)
original_draw = html[a:b]
shake_start = original_draw.index('      const shakeAmount =')
shake_end = original_draw.index('      ctx.save();', shake_start)
original_draw = original_draw[:shake_start] + '''      lastImpactOffset = window.orreryImpactOffset(game, ambientTime, reducedMotion);
      const sx = lastImpactOffset.x, sy = lastImpactOffset.y;

''' + original_draw[shake_end:]
html = html[:a] + '''      if (selectedView === "3d") {
        ctx.clearRect(0, 0, W, H);
        view3D.render(game, ambientTime, reducedMotion, pointer);
        view3D.drawOverlay(ctx, game);
      } else {
''' + original_draw + '''      }
''' + html[b:]
replace('game.flash * .34', 'game.flash * .08')
replace('    const debugApi = {', '''    const debugApi = {
      renderer: () => selectedView === "3d"
        ? view3D.info()
        : { kind: "canvas2d", mode: game.mode, moons: 3 },
      project3D: (x, y) => view3D ? view3D.project(x, y) : { x, y },
      unproject3D: point => view3D ? view3D.unproject(point) : { ...point },''')

# Aim is projected only in 3D; touch joystick distances stay in CSS pixels.
replace('''      return {
        x: (event.clientX - rect.left) * W / rect.width,
        y: (event.clientY - rect.top) * H / rect.height
      };''', '''      const screen = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top
      };
      // 3D rays and touch distances use CSS pixels; the 2D world uses W/H.
      const aim = selectedView === "3d" ? view3D.unproject(screen)
        : { x: screen.x * W / rect.width - lastImpactOffset.x,
            y: screen.y * H / rect.height - lastImpactOffset.y };
      return { ...aim, screenX: screen.x, screenY: screen.y };''')
replace('          touchMove.x = pos.x;\n          touchMove.y = pos.y;', '          touchMove.x = pos.screenX;\n          touchMove.y = pos.screenY;')
replace('if (pos.x < W * .46 && touchMove.id === null)', 'if (pos.screenX < W * .46 && touchMove.id === null)')
replace('touchMove.ox = touchMove.x = pos.x;\n          touchMove.oy = touchMove.y = pos.y;', 'touchMove.ox = touchMove.x = pos.screenX;\n          touchMove.oy = touchMove.y = pos.screenY;')
replace('        mode: game.mode,', '        mode: game.mode,\n        aim: { x: pointer.x, y: pointer.y },')
replace('A rite in three movements</div>', '3D / A rite in three movements</div>')
replace('eyebrow.textContent = "A rite in three movements";', 'eyebrow.textContent = `${selectedView.toUpperCase()} / A rite in three movements`;')
replace('    updateSoundButton();\n    renderScoreArchive();', '    updateSoundButton();\n    updateViewControls();\n    renderScoreArchive();')

# Let native activation reach its control without the gameplay bubble handler
# cancelling its default action (including inputs, links and summaries).
replace('      const code = event.code;', '''      const code = event.code;
      if (graphicsLost && selectedView === "3d" && code !== "KeyM") return;''')

# Guard state entry as well as keyboard input while the selected renderer is lost.
for function in ['startGame', 'resumeGame']:
    replace(f'    function {function}() {{', f'''    function {function}() {{
      if (selectedView === "3d" && graphicsLost) return;''')

# Home-only native toggle buttons. Choice is retained in memory for this tab.
replace('''      </div>

      <div class="briefing">''', '''        <section id="viewSelector" class="view-selector" aria-label="Game view">
          <div class="view-options" role="group" aria-label="Choose 2D or 3D view">
            <span aria-hidden="true">FIELD</span>
            <button id="view2D" type="button" aria-pressed="false">2D</button>
            <button id="view3D" type="button" aria-pressed="true">3D</button>
          </div>
          <p id="viewDescription">Sculpted cosmos / perspective field</p>
          <p id="graphicsError" role="status" hidden></p>
        </section>
      </div>

      <div class="briefing">''')
replace('  </style>', '''    .overlay[data-state="result"] .achievement-title { white-space: normal; }
    .view-selector { margin-top: 18px; max-width: 360px; }
    .overlay:not([data-state="title"]) .view-selector { display: none; }
    .view-options { display: flex; align-items: center; gap: 0; }
    .view-options span { margin-right: 14px; color: var(--muted); font: 700 9px/1 monospace; letter-spacing: .16em; }
    .view-options button { min-width: 66px; min-height: 40px; border: 1px solid var(--rule); border-radius: 0; padding: 10px 20px; color: var(--paper); background: var(--void); cursor: pointer; font: 700 12px/1 monospace; letter-spacing: .12em; }
    .view-options button + button { margin-left: -1px; }
    .view-options button[aria-pressed="true"] { background: var(--paper); color: var(--void); border-color: var(--paper); }
    .view-options button:focus-visible { position: relative; outline: 2px solid var(--ember); outline-offset: 3px; z-index: 1; }
    .view-options button:hover { border-color: var(--ember); }
    .view-options button:disabled { opacity: .4; cursor: not-allowed; }
    #viewDescription, #graphicsError { margin: 8px 0 0; color: var(--muted); font: 600 9px/1.5 'Courier New', monospace; letter-spacing: .03em; }
    #graphicsError { color: var(--ember); }
    @media (max-width: 760px), (max-height: 600px) {
      .view-selector { margin-top: 12px; }
      #viewDescription { display: none; }
    }
    @media (max-width: 519px) and (max-height: 300px) {
      .overlay[data-state="title"] .index-mark { display: none; }
      .overlay[data-state="title"] h1 { font-size: 24px; }
      .overlay[data-state="title"] .cover { align-content: start; gap: 2px; }
      .overlay[data-state="title"] .score-history-list { max-height: 44px; }
      .view-selector { margin-top: 0; }
      .view-options button { min-height: 24px; min-width: 52px; padding: 4px 12px; font-size: 10px; }
    }
  </style>''')

# Touch-accessible pause uses the existing state transition/input cleanup.
replace('  <button id="soundButton"', '''  <button id="pauseButton" class="pause-button" type="button" aria-label="Pause game" hidden>II / Pause</button>
  <button id="soundButton"''')
replace('    const soundButton =', '    const pauseButton = document.getElementById("pauseButton");\n    const soundButton =')
replace('      overlay.setAttribute("aria-hidden", String(hidden));', '''      overlay.setAttribute("aria-hidden", String(hidden));
      pauseButton.hidden = !hidden;''')
replace('    soundButton.addEventListener("click", toggleSound);', '''    soundButton.addEventListener("click", toggleSound);
    pauseButton.addEventListener("click", pauseGame);
    pauseButton.addEventListener("pointerdown", event => {
      // A second/third finger must pause immediately, without a primary click.
      if (event.pointerType !== "touch") return;
      event.preventDefault();
      pauseGame();
    });
    // Safari's long-press selection/callout is separate from Pointer Events.
    // Cancel only playfield defaults; keep native menus/buttons/scrolling intact.
    canvas.addEventListener("touchstart", event => {
      if (game.mode === "playing") event.preventDefault();
    }, { passive: false });
    canvas.addEventListener("selectstart", event => event.preventDefault());''')
replace('    .sound-button {\n      position: fixed;', '    .sound-button, .pause-button {\n      position: fixed;')
replace('    .sound-button:focus-visible {', '    .sound-button:focus-visible,\n    .pause-button:focus-visible {')
replace('  </style>', '''    #game, #stage3D {
      -webkit-user-select: none;
      user-select: none;
      -webkit-touch-callout: none;
      -webkit-tap-highlight-color: transparent;
    }
    .pause-button {
      right: max(16px, env(safe-area-inset-right));
      bottom: calc(max(14px, env(safe-area-inset-bottom)) + 52px);
      min-height: 44px;
      touch-action: manipulation;
    }
    .pause-button[hidden] { display: none; }
  </style>''')
# Reserve space above the two field buttons for the desktop reversal hint.
replace('W - pad, bottom - 47);', 'W - pad, bottom - 100);')

# Fit chapter text against the actual active Canvas font on narrow screens.
replace('      ctx.fillText(chapter.title, W / 2, y + 6);', '''      const chapterWidth = ctx.measureText(chapter.title).width;
      if (chapterWidth > W - 40) {
        const fontSize = clamp(W * .035, 24, 52) * (W - 40) / chapterWidth;
        ctx.font = `700 ${fontSize}px Baskerville, Georgia, serif`;
      }
      ctx.fillText(chapter.title, W / 2, y + 6);''')
# The inherited freeze values no longer gate simulation. Fixed-step behavior,
# damage/cooldowns/spawns and the real pause control remain unchanged.
start = html.index('        if (game.freeze > 0) {', html.index('    function frame(now)'))
end = html.index('      adjustRenderQuality(realDt);', start)
html = html[:start] + '''        game.freeze = 0;
        accumulator += realDt;
        let loops = 0;
        while (accumulator >= STEP && loops < 4) {
          update(STEP);
          accumulator -= STEP;
          loops += 1;
        }
        if (loops === 4) accumulator = 0;
      }
''' + html[end:]
(ROOT / 'index.html').write_text(html)
print('Built offline index.html: 2D / 3D selector, continuous combat, embedded dependencies.')
