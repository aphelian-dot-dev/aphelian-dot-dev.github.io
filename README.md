# APHELIAN — The Last Orrery

Local **2D / 3D edition**, derived from upstream commit `0bb8be2bbe4b0ac2bb6ab9fcb1c03aeebcf4acbf` of [aphelian-dot-dev/aphelian-dot-dev.github.io](https://github.com/aphelian-dot-dev/aphelian-dot-dev.github.io).

## Open on Bazzite

Open **`/home/zach/Transfers/aphelian-3d/index.html`** in Firefox or Chrome. All code, including Three.js, is embedded: no installation, internet connection, CDN, or local server is needed to play. A Flatpak file picker can expose just this one HTML file and it still works. If you opened an earlier copy through a document portal, close that tab and open the file again.

This is a genuine WebGL 3D presentation with a perspective camera, lit solid models, a raised arena, moon shadows, volumetric Black Sun rings, projected aim, and 3D particles. **Combat remains on a single plane** to preserve the original movement and collision rules; it is not a free-flight or first-person redesign. Enemies still enter from beyond the arena edge.

Use **FIELD · 2D / 3D** on the home screen to choose the original Canvas presentation or the perspective 3D field. Both are embedded in this one file and run the same simulation. Your choice stays in memory when returning home; it resets to 3D on reopening and creates no preference cookie or local storage. The optional score archive is shared between views; entries are not tagged by dimension.

Outside the overheat mechanic below, the original spawning, damage, Focus, charged Lattice, Retrograde, meteors, pickups, scoring, audio, and result/consent interfaces are retained. **A pacing change applies to both views:** impact and damage hit-stop no longer suspend the fixed-step simulation. Movement, weapon orbits, cooldowns, and the rite clock continue during hits. A brief visual-only impact shake is capped at three CSS pixels in both views; the HUD stays steady, aiming follows the displaced field, and reduced-motion mode suppresses shake entirely. Fullscreen hit flashes are softened; local flashes, particles, and sound remain. Wave durations and other gameplay constants are unchanged, but no artificial hit pauses extend their wall-clock duration.

Shake is **impact-only**: releasing an attack into empty space, reversing without a hit, taking damage, and boss arrival/dash cues do not initiate it. Actual Ward Moon, Lattice, and Retrograde hits—including hits on meteors and the Black Sun—still produce the small visual nudge, without hit-stop.

**Overheating applies to both views.** Releasing in the orange timing window stays optimal. Reaching 100% charge automatically releases a blue, overheated Lattice for that burst (0.58 seconds): movement/acceleration are multiplied by 0.95, the triangle’s orbital spread by 0.90 versus its otherwise fully charged geometry, and automatic orbit speed by 0.75. Mouse/touch-controlled aiming is unchanged. Ward Moon and edge damage are 50% of the maximum orange-timed release (96% charge); Retrograde damage is also halved while overheated. The HUD says **OVERHEATED** and shows the blue cooldown. Penalties clear when the burst ends or a new run starts; early automatic release from exhausted Focus does not overheat. Ordinary attacks, perfect-release Focus/score bonuses, meteor three-hit rules, and boost durations are unchanged.

The result screen includes eight achievements. **DAWN IN THREE DIMENSIONS — EASY** is earned by sealing the Black Sun and reaching DAWN in 3D mode. A 2D win or any loss does not unlock it; the chosen view cannot be switched during a rite. Like the other achievements, it is evaluated per run and can appear in the existing rarest-achievement share text. This adds no storage or changes to score-archive consent.

The separate 2D playtest and public website are not replaced. The archive remains off in direct-file mode. WebGL is needed only for 3D: if unavailable, the game explains the fallback and remains playable in 2D. Context loss pauses an active 3D run until manual resumption after recovery, but does not interrupt a 2D run.

## Rebuilding this edition

- `upstream/index.html` and `upstream/COMMIT`: frozen source and provenance.
- `renderer-3d.js`: read-only scene adapter, camera projection, visual meshes and effects.
- `view-controls.js`: home selector, session-only view state, and context-loss isolation.
- `build-3d.py`: reproducibly embeds the renderer and local engine into the original game.
- `overheat-patches.json`: scoped overheat simulation/HUD edits, applied at build time and tracked by the baseline-parity test.
- `vendor/`: pinned Three.js 0.160.0 and its MIT license. No dependency installation needed.
- `game-rules.js`: testable gameplay rules and the local eight-achievement catalog, embedded during the build.

Run `python3 build-3d.py` after editing the renderer. Do not hand-edit the generated `index.html`.

Additional 3D verification:

```sh
uv run --with selenium python tests/three-smoke.py
uv run --with selenium python tests/three-framing.py
uv run --with selenium python tests/three-unavailable.py
uv run --with selenium python tests/three-visual.py
uv run --with selenium python tests/view-selector.py
uv run --with selenium python tests/context-loss-input.py
uv run --with selenium python tests/short-viewport-input.py
uv run --with selenium python tests/view-layout.py
uv run --with selenium python tests/impact-pacing.py
uv run --with selenium python tests/impact-shake.py
uv run --with selenium python tests/impact-events.py
uv run --with selenium python tests/dawn-3d.py
uv run --with selenium python tests/overheat-browser.py
uv run --with selenium python tests/overheat-layout.py
```

These exercise standalone startup, perspective projection/aim, WebGL recovery, keyboard/touch controls, meteor hits, boss victory, defeat, and desktop/narrow/short-height layouts. Core simulation parity is checked by the Node suite below.

## Gameplay

Command three Ward Moons, break the approaching Voidcraft, and survive the three movements until the Black Sun appears. The final fight has no time limit: the rite continues until you seal the Black Sun or your Vital Light is extinguished. Your total elapsed time is recorded, including whether you complete the rite in under two minutes.

## Controls

- **Move:** WASD, arrow keys, or drag on the left side of a touch screen.
- **Aim:** Pointer or a right-side touch.
- **Strike:** Hold and release Space, left click, or a right-side touch.
- **Retrograde:** Right click, Shift, or tap the left side of a touch screen.
- **Pause / sound:** P or Escape pauses; M toggles sound.

## Local preview

For the optional score archive, serve this folder on loopback only, then open `http://127.0.0.1:8000` on Bazzite:

```sh
cd /home/zach/Transfers/aphelian-3d
python3 -m http.server 8000 --bind 127.0.0.1
```

Stop with Ctrl+C. No service is installed. Cookies are shared across ports on the same hostname; use a separate browser profile if you want this experimental edition's archive isolated from another localhost game.

## Optional score archive

On the home screen, players can opt in to one first-party cookie named `aphelian_score_history`. It stores up to 10 completed rites: score, win/loss, best chain, rite time, and completion time. Its one-year `Max-Age` renews after each saved rite, so older entries may remain longer than one year while saving continues. It is used only to render the on-device score archive; there is no account, advertising, analytics, or cross-site tracking. Choosing **Not now** creates no cookie, and **Forget saved scores** deletes it.

Enabling, saving, and deleting the archive are serialized across tabs with the browser's Web Locks API. If Web Locks are unavailable, the archive remains off and Aphelian does not create, read, change, or renew the cookie; there is no fallback cookie or local storage. If a same-name cookie contains malformed or unsupported-version data, Aphelian marks it incompatible, never treats it as consent, and will not overwrite it when **Remember scores** is selected. Use **Remove incompatible cookie**, or remove it manually in DevTools or browser site-data settings.

Because this is a cookie, the browser includes it in requests to the current site. Aphelian is static and contains no code that sends or uses the data for another purpose. The archive requires an HTTP or HTTPS origin, so direct `file://` play remains available but score saving is disabled there.

To inspect it, open Firefox DevTools → **Storage** → **Cookies**, or Chrome/Edge DevTools → **Application** → **Storage** → **Cookies**. Its value is URL-encoded JSON; `window.__ORRERY__.scoreArchive()` returns the decoded content in the Console.

## Tests

The rule and integration tests use Node's built-in test runner:

```sh
node --test tests/*.test.cjs
```

Responsive result and share-lifecycle checks use headless Firefox through Selenium:

```sh
uv run --with selenium python tests/browser-regressions.py
```

## Future goals

- Add a meteor achievement for landing at least one hit on every Wayfaring Meteor in a rite.
