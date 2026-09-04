# APHELIAN — The Last Orrery

Source for [aphelian.dev](https://aphelian.dev/), a single-page canvas action game hosted with GitHub Pages.

## Gameplay

Command three Ward Moons, break the approaching Voidcraft, and survive the three movements until the Black Sun appears. The final fight has no time limit: the rite continues until you seal the Black Sun or your Vital Light is extinguished. Your total elapsed time is recorded, including whether you complete the rite in under two minutes.

## Controls

- **Move:** WASD, arrow keys, or drag on the left side of a touch screen.
- **Aim:** Pointer or a right-side touch.
- **Strike:** Hold and release Space, left click, or a right-side touch.
- **Retrograde:** Right click, Shift, or tap the left side of a touch screen.
- **Pause / sound:** P or Escape pauses; M toggles sound.

## Local preview

Serve the repository root over HTTP, then open the printed local address:

```sh
python3 -m http.server 8000
```

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
