# APHELION — The Last Orrery

Source for [aphelian.dev](https://aphelian.dev/), a single-page canvas action game hosted with GitHub Pages.

## Local preview

Serve the repository root over HTTP, then open the printed local address:

```sh
python3 -m http.server 8000
```

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

- Store previous runs in a cookie or local storage so returning players can compare the current rite with earlier runs both before and after play.
- Add a meteor achievement for landing at least one hit on every Wayfaring Meteor in a rite.
