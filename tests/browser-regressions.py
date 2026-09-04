# pyright: reportMissingImports=false

import json
import shutil
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait


REPO = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/__score_notice_frame__":
            parameters = parse_qs(url.query)
            width = int(parameters.get("width", ["900"])[0])
            height = int(parameters.get("height", ["700"])[0])
            body = (
                "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
                f'<iframe id="gameFrame" width="{width}" height="{height}" '
                'src="/index.html?debug=1"></iframe>'
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, format, *args):
        del format, args
        pass


class ResultScreenBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = lambda *args, **kwargs: QuietHandler(*args, directory=str(REPO), **kwargs)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

        options = Options()
        options.add_argument("-headless")
        cls.driver = webdriver.Firefox(options=options)
        cls.driver.set_window_size(1200, 900)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=2)

    def tearDown(self):
        self.driver.switch_to.default_content()

    def execute_awaited(self, body, *args):
        script = """
            const done = arguments[arguments.length - 1];
            (async () => {
        """ + body + """
            })().then(
              value => done({ ok: true, value }),
              error => done({
                ok: false,
                error: `${error && error.name ? error.name : 'Error'}: ${error && error.message ? error.message : error}`
              })
            );
        """
        outcome = self.driver.execute_async_script(script, *args)
        self.assertTrue(outcome.get("ok"), json.dumps(outcome, indent=2))
        return outcome.get("value")

    def result_metrics(self, width, height):
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="{width}" height="{height}" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return document.readyState === "complete" && typeof window.__ORRERY__ === "object"'
            )
        )
        self.driver.execute_script("window.__ORRERY__.start(); window.__ORRERY__.finish(true)")
        metrics = self.driver.execute_script(
            """
            const rect = selector => {
              const box = document.querySelector(selector).getBoundingClientRect();
              return { top: box.top, bottom: box.bottom, left: box.left, right: box.right };
            };
            return {
              width: innerWidth,
              height: innerHeight,
              briefing: rect('.briefing'),
              results: rect('.results'),
              achievements: rect('.achievements'),
              actions: rect('.result-actions'),
              sound: (() => {
                const node = document.querySelector('.sound-button');
                const box = node.getBoundingClientRect();
                return {
                  visible: getComputedStyle(node).display !== 'none',
                  top: box.top,
                  bottom: box.bottom,
                  left: box.left,
                  right: box.right
                };
              })(),
              clippedTitles: [...document.querySelectorAll('.achievement-title')]
                .filter(node => node.scrollWidth > node.clientWidth + 1)
                .map(node => node.textContent),
              clippedDifficulties: [...document.querySelectorAll('.achievement-difficulty')]
                .filter(node => node.scrollWidth > node.clientWidth + 1)
                .map(node => node.textContent),
              clippedButtons: [...document.querySelectorAll('.result-actions button')]
                .filter(node => node.scrollHeight > node.clientHeight + 1 || node.scrollWidth > node.clientWidth + 1)
                .map(node => node.textContent),
              horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1
            };
            """
        )
        self.driver.switch_to.default_content()
        return metrics

    def title_metrics(self, width, height):
        self.driver.get(f"{self.base_url}/index.html")
        self.driver.delete_all_cookies()
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="{width}" height="{height}" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        metrics = self.driver.execute_script(
            """
            const rect = selector => {
              const box = document.querySelector(selector).getBoundingClientRect();
              return { top: box.top, bottom: box.bottom, left: box.left, right: box.right };
            };
            return {
              width: innerWidth,
              height: innerHeight,
              archive: rect('#scoreArchive'),
              consent: rect('#scoreConsent'),
              actions: rect('.result-actions'),
              rite: rect('#riteButton'),
              clippedButtons: [...document.querySelectorAll('#scoreConsent button, #riteButton')]
                .filter(node => node.scrollHeight > node.clientHeight + 1 || node.scrollWidth > node.clientWidth + 1)
                .map(node => node.textContent),
              horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1
            };
            """
        )
        self.driver.switch_to.default_content()
        return metrics

    def title_cookie_details_metrics(self, width, height):
        self.driver.get(f"{self.base_url}/index.html")
        self.driver.delete_all_cookies()
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="{width}" height="{height}" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        metrics = self.driver.execute_script(
            """
            const overlay = document.getElementById('overlay');
            const details = document.getElementById('scoreCookieDetails');
            const rite = document.getElementById('riteButton');
            const folio = document.querySelector('.folio');
            const rect = node => {
              const box = node.getBoundingClientRect();
              return { top: box.top, bottom: box.bottom, left: box.left, right: box.right };
            };
            const overlaps = (first, second) => (
              first.left < second.right && first.right > second.left
              && first.top < second.bottom && first.bottom > second.top
            );
            details.open = true;
            details.scrollIntoView({ block: 'nearest' });
            const detailsBox = rect(details);
            rite.scrollIntoView({ block: 'nearest' });
            const riteBox = rect(rite);
            const folioBox = rect(folio);
            return {
              detailsReachable: detailsBox.top >= 0 && detailsBox.bottom <= innerHeight + 1,
              riteReachable: riteBox.top >= 0 && riteBox.bottom <= innerHeight + 1,
              folioOverlapsRite: getComputedStyle(folio).display !== 'none'
                && overlaps(folioBox, riteBox),
              canScrollOverflow: overlay.scrollHeight <= overlay.clientHeight + 1
                || ['auto', 'scroll'].includes(getComputedStyle(overlay).overflowY),
              horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1
            };
            """
        )
        self.driver.switch_to.default_content()
        return metrics

    def title_history_metrics(self, width, height):
        history = {
            "version": 1,
            "runs": [
                {
                    "score": 12000 - index * 137,
                    "won": index % 2 == 0,
                    "bestChain": 20 - index,
                    "time": 70.4 + index,
                    "completedAt": f"2026-09-{10 - index:02d}T12:00:00.000Z",
                }
                for index in range(10)
            ],
        }
        self.driver.get(f"{self.base_url}/index.html")
        self.driver.delete_all_cookies()
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="{width}" height="{height}" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.execute_script("window.__ORRERY__.setScoreHistory(arguments[0])", history)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return window.__ORRERY__.scoreArchive().history.runs.length === 10'
            )
        )
        metrics = self.driver.execute_script(
            """
            const rect = selector => {
              const box = document.querySelector(selector).getBoundingClientRect();
              return { top: box.top, bottom: box.bottom, left: box.left, right: box.right };
            };
            const list = document.getElementById('scoreHistoryList');
            return {
              archive: rect('#scoreArchive'),
              history: rect('#scoreHistory'),
              actions: rect('.result-actions'),
              rite: rect('#riteButton'),
              rowCount: list.children.length,
              listScrollable: list.scrollHeight > list.clientHeight + 1,
              horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
              listHorizontalOverflow: list.scrollWidth > list.clientWidth + 1
            };
            """
        )
        self.driver.switch_to.default_content()
        return metrics

    def score_save_notice_metrics(self, width, height, reject_write):
        self.driver.get(f"{self.base_url}/index.html")
        self.driver.delete_all_cookies()
        self.driver.get(
            f"{self.base_url}/__score_notice_frame__?width={width}&height={height}"
        )
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )
        metrics = self.execute_awaited(
            """
            if (arguments[0]) {
              const savedCookie = document.cookie;
              Object.defineProperty(document, 'cookie', {
                configurable: true,
                get() { return savedCookie; },
                set() { /* simulate a policy silently rejecting the write */ }
              });
            }
            window.__ORRERY__.start();
            await window.__ORRERY__.finish(false);
            const notice = document.getElementById('scoreSaveNotice');
            const box = notice ? notice.getBoundingClientRect() : null;
            return {
              exists: Boolean(notice),
              hidden: notice ? notice.hidden : null,
              display: notice ? getComputedStyle(notice).display : null,
              parentDisplay: notice ? getComputedStyle(notice.parentElement).display : null,
              visible: Boolean(notice && !notice.hidden && getComputedStyle(notice).display !== 'none'),
              text: notice ? notice.textContent : '',
              box: box ? { top: box.top, bottom: box.bottom, left: box.left, right: box.right } : null,
              archive: window.__ORRERY__.scoreArchive(),
              status: document.getElementById('scoreArchiveStatus').textContent,
              overlayState: document.getElementById('overlay').dataset.state,
              horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1
            };
            """,
            reject_write,
        )
        self.driver.switch_to.default_content()
        return metrics

    def test_ten_saved_scores_fit_the_home_screen_archive(self):
        viewports = [(320, 234), (320, 568), (390, 844), (520, 300), (640, 420), (900, 700), (1200, 900)]
        failures = []
        for width, height in viewports:
            metrics = self.title_history_metrics(width, height)
            for name in ("archive", "history", "actions", "rite"):
                box = metrics[name]
                if box["top"] < 0 or box["bottom"] > height:
                    failures.append({"viewport": [width, height], name: box})
            if metrics["rowCount"] != 10:
                failures.append({"viewport": [width, height], "rowCount": metrics["rowCount"]})
            if metrics["horizontalOverflow"] or metrics["listHorizontalOverflow"]:
                failures.append({"viewport": [width, height], "horizontalOverflow": True})
        self.assertEqual([], failures, json.dumps(failures, indent=2))

    def test_score_archive_consent_is_visible_across_home_screen_viewports(self):
        viewports = [
            (320, 234),
            (320, 568),
            (390, 844),
            (520, 300),
            (640, 420),
            (740, 500),
            (900, 700),
            (1200, 900),
        ]
        failures = []
        for width, height in viewports:
            metrics = self.title_metrics(width, height)
            for name in ("archive", "consent", "actions", "rite"):
                box = metrics[name]
                if box["top"] < 0 or box["bottom"] > height:
                    failures.append({"viewport": [width, height], name: box})
            if metrics["clippedButtons"]:
                failures.append({"viewport": [width, height], "clippedButtons": metrics["clippedButtons"]})
            if metrics["horizontalOverflow"]:
                failures.append({"viewport": [width, height], "horizontalOverflow": True})
        self.assertEqual([], failures, json.dumps(failures, indent=2))

    def test_cookie_details_and_begin_button_remain_reachable_across_viewports(self):
        viewports = [(320, 234), (320, 568), (390, 844), (520, 300), (640, 420), (900, 700), (1200, 900)]
        failures = []
        for width, height in viewports:
            metrics = self.title_cookie_details_metrics(width, height)
            if not metrics["detailsReachable"]:
                failures.append({"viewport": [width, height], "detailsReachable": False})
            if not metrics["riteReachable"]:
                failures.append({"viewport": [width, height], "riteReachable": False})
            if not metrics["canScrollOverflow"]:
                failures.append({"viewport": [width, height], "canScrollOverflow": False})
            if metrics["horizontalOverflow"]:
                failures.append({"viewport": [width, height], "horizontalOverflow": True})
        self.assertEqual([], failures, json.dumps(failures, indent=2))

    def test_expanded_cookie_details_keep_footer_clear_of_begin_button(self):
        metrics = self.title_cookie_details_metrics(1440, 906)
        self.assertFalse(metrics["folioOverlapsRite"], json.dumps(metrics, indent=2))

    def test_cookie_details_summary_return_opens_without_starting_the_game(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        summary = self.driver.find_element("css selector", "#scoreCookieDetails summary")
        self.driver.execute_script("arguments[0].focus()", summary)
        before = self.driver.execute_script(
            """
            return {
              focused: document.activeElement === arguments[0],
              detailsOpen: document.getElementById('scoreCookieDetails').open,
              mode: window.__ORRERY__.snapshot().mode
            };
            """,
            summary,
        )
        self.assertEqual(
            {"focused": True, "detailsOpen": False, "mode": "title"},
            before,
            json.dumps(before, indent=2),
        )

        summary.send_keys(Keys.RETURN)
        after = self.driver.execute_script(
            """
            return {
              detailsOpen: document.getElementById('scoreCookieDetails').open,
              mode: window.__ORRERY__.snapshot().mode
            };
            """
        )
        self.assertEqual(
            {"detailsOpen": True, "mode": "title"},
            after,
            json.dumps(after, indent=2),
        )

    def test_score_save_notice_is_visible_on_failure_and_hidden_on_success_across_viewports(self):
        viewports = [(320, 234), (390, 844), (900, 700)]
        failures = []
        for width, height in viewports:
            failed = self.score_save_notice_metrics(width, height, True)
            if not failed["exists"] or not failed["visible"]:
                failures.append({"viewport": [width, height], "failedWrite": failed})
            elif (
                failed["box"]["top"] < 0
                or failed["box"]["bottom"] > height
                or failed["box"]["left"] < 0
                or failed["box"]["right"] > width
            ):
                failures.append({"viewport": [width, height], "noticeBounds": failed["box"]})
            if "score not saved" not in failed["text"].lower():
                failures.append({"viewport": [width, height], "noticeText": failed["text"]})
            if failed["horizontalOverflow"]:
                failures.append({"viewport": [width, height], "horizontalOverflow": True})

            saved = self.score_save_notice_metrics(width, height, False)
            if not saved["exists"] or saved["visible"]:
                failures.append({"viewport": [width, height], "successfulWrite": saved})

        self.assertEqual([], failures, json.dumps(failures, indent=2))

    def test_score_archive_requests_consent_before_creating_a_cookie(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return document.readyState === "complete" && typeof window.__ORRERY__ === "object"'
            )
        )

        state = self.driver.execute_script(
            """
            const consent = document.getElementById('scoreConsent');
            return {
              cookie: document.cookie,
              consentVisible: consent && !consent.hidden,
              copy: consent ? consent.textContent : '',
              details: document.getElementById('scoreCookieDetails')?.textContent || ''
            };
            """
        )
        self.assertNotIn("aphelian_score_history=", state["cookie"], json.dumps(state, indent=2))
        self.assertTrue(state["consentVisible"], json.dumps(state, indent=2))
        self.assertIn("Would you like Aphelian to remember", state["copy"])
        self.assertIn("used only for this score archive", state["copy"])
        self.assertIn("aphelian_score_history", state["details"])
        self.assertIn("Storage", state["details"])
        self.assertIn("Application", state["details"])
        self.assertIn("includes it in requests to this site", state["details"])

    def test_malformed_and_unsupported_cookies_do_not_grant_consent_or_get_overwritten(self):
        invalid_values = {
            "malformed percent encoding": "%E0%A4%A",
            "malformed JSON": quote("{not-json", safe=""),
            "unsupported schema": quote(json.dumps({"version": 2, "runs": []}), safe=""),
            "coercible wrong field type": quote(json.dumps({
                "version": 1,
                "runs": [{
                    "score": "99",
                    "won": True,
                    "bestChain": 2,
                    "time": 30,
                    "completedAt": "2026-09-04T12:00:00.000Z",
                }],
            }), safe=""),
        }

        for label, invalid_value in invalid_values.items():
            with self.subTest(label=label):
                self.driver.get(f"{self.base_url}/index.html?debug=1")
                self.driver.delete_all_cookies()
                self.driver.execute_script(
                    "document.cookie = `aphelian_score_history=${arguments[0]}; Path=/; SameSite=Strict`",
                    invalid_value,
                )
                original = self.driver.get_cookie("aphelian_score_history")
                self.driver.refresh()
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
                )

                blocked = self.driver.execute_script(
                    """
                    return {
                      archive: window.__ORRERY__.scoreArchive(),
                      consentVisible: !document.getElementById('scoreConsent').hidden,
                      declinedVisible: !document.getElementById('scoreDeclined').hidden,
                      removeVisible: !document.getElementById('removeBlockedScoreCookieButton').hidden,
                      status: document.getElementById('scoreArchiveStatus').textContent,
                      copy: document.getElementById('scoreDeclinedCopy').textContent,
                      details: document.getElementById('scoreCookieDetails').textContent,
                      focusedId: document.activeElement && document.activeElement.id,
                      focusedTag: document.activeElement && document.activeElement.tagName
                    };
                    """
                )
                self.execute_awaited(
                    """
                    document.getElementById('rememberScoresButton').click();
                    await navigator.locks.request('aphelian-score-archive', () => {});
                    await Promise.resolve();
                    """
                )
                after_remember = self.driver.get_cookie("aphelian_score_history")
                still_blocked = self.driver.execute_script(
                    """
                    const focused = document.activeElement;
                    return {
                      archive: window.__ORRERY__.scoreArchive(),
                      focusedId: focused && focused.id,
                      focusedVisible: Boolean(focused && focused.getClientRects().length)
                    };
                    """
                )

                self.assertIsNotNone(original)
                self.assertFalse(blocked["archive"]["enabled"], json.dumps(blocked, indent=2))
                self.assertTrue(blocked["archive"]["blocked"], json.dumps(blocked, indent=2))
                self.assertEqual("incompatible", blocked["archive"]["reason"])
                self.assertFalse(blocked["consentVisible"], json.dumps(blocked, indent=2))
                self.assertTrue(blocked["declinedVisible"], json.dumps(blocked, indent=2))
                self.assertTrue(blocked["removeVisible"], json.dumps(blocked, indent=2))
                self.assertIn("incompatible", blocked["status"].lower())
                self.assertIn("will not read, save, or replace", blocked["copy"].lower())
                self.assertIn("Storage", blocked["details"])
                self.assertEqual("BODY", blocked["focusedTag"], json.dumps(blocked, indent=2))
                self.assertNotIn(
                    blocked["focusedId"],
                    {"rememberScoresButton", "removeBlockedScoreCookieButton", "forgetScoresButton"},
                    json.dumps(blocked, indent=2),
                )
                self.assertIsNotNone(after_remember)
                self.assertEqual(original["value"], after_remember["value"])
                self.assertTrue(still_blocked["archive"]["blocked"], json.dumps(still_blocked, indent=2))
                self.assertEqual("removeBlockedScoreCookieButton", still_blocked["focusedId"])
                self.assertTrue(still_blocked["focusedVisible"], json.dumps(still_blocked, indent=2))

                self.driver.find_element("id", "removeBlockedScoreCookieButton").click()
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script(
                        "return !document.cookie.includes('aphelian_score_history=') "
                        "&& !document.getElementById('scoreConsent').hidden"
                    )
                )
                removed = self.driver.execute_script(
                    """
                    return {
                      cookie: document.cookie,
                      consentVisible: !document.getElementById('scoreConsent').hidden,
                      archive: window.__ORRERY__.scoreArchive()
                    };
                    """
                )
                self.assertNotIn("aphelian_score_history=", removed["cookie"], json.dumps(removed, indent=2))
                self.assertTrue(removed["consentVisible"], json.dumps(removed, indent=2))
                self.assertFalse(removed["archive"]["blocked"], json.dumps(removed, indent=2))

    def test_remember_preserves_incompatible_cookie_added_after_consent_view_loaded(self):
        unsupported_value = quote(json.dumps({"version": 2, "runs": []}), safe="")
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return typeof window.__ORRERY__ === "object" '
                '&& !document.getElementById("scoreConsent").hidden'
            )
        )
        self.driver.execute_script(
            "document.cookie = `aphelian_score_history=${arguments[0]}; Path=/; SameSite=Strict`",
            unsupported_value,
        )
        original = self.driver.get_cookie("aphelian_score_history")

        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return window.__ORRERY__.scoreArchive().blocked '
                '&& !document.getElementById("removeBlockedScoreCookieButton").hidden'
            )
        )
        after = self.driver.get_cookie("aphelian_score_history")
        state = self.driver.execute_script(
            """
            const focused = document.activeElement;
            return {
              archive: window.__ORRERY__.scoreArchive(),
              consentHidden: document.getElementById('scoreConsent').hidden,
              removeVisible: !document.getElementById('removeBlockedScoreCookieButton').hidden,
              focusedId: focused && focused.id,
              focusedVisible: Boolean(focused && focused.getClientRects().length)
            };
            """
        )

        self.assertIsNotNone(original)
        self.assertIsNotNone(after)
        self.assertEqual(original["value"], after["value"], json.dumps(state, indent=2))
        self.assertTrue(state["archive"]["blocked"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertTrue(state["consentHidden"], json.dumps(state, indent=2))
        self.assertTrue(state["removeVisible"], json.dumps(state, indent=2))
        self.assertEqual("removeBlockedScoreCookieButton", state["focusedId"])
        self.assertTrue(state["focusedVisible"], json.dumps(state, indent=2))

    def test_declining_score_archive_creates_no_cookie_and_can_be_reconsidered(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )

        self.driver.find_element("id", "declineScoresButton").click()
        declined = self.driver.execute_script(
            """
            return {
              cookie: document.cookie,
              consentHidden: document.getElementById('scoreConsent').hidden,
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent
            };
            """
        )
        self.assertNotIn("aphelian_score_history=", declined["cookie"], json.dumps(declined, indent=2))
        self.assertTrue(declined["consentHidden"], json.dumps(declined, indent=2))
        self.assertTrue(declined["declinedVisible"], json.dumps(declined, indent=2))
        self.assertIn("off", declined["status"].lower())

        self.driver.find_element("id", "reconsiderScoresButton").click()
        reconsidered = self.driver.execute_script(
            """
            return {
              cookie: document.cookie,
              consentVisible: !document.getElementById('scoreConsent').hidden,
              declinedHidden: document.getElementById('scoreDeclined').hidden
            };
            """
        )
        self.assertNotIn("aphelian_score_history=", reconsidered["cookie"], json.dumps(reconsidered, indent=2))
        self.assertTrue(reconsidered["consentVisible"], json.dumps(reconsidered, indent=2))
        self.assertTrue(reconsidered["declinedHidden"], json.dumps(reconsidered, indent=2))

    def test_latest_decline_cancels_remember_queued_behind_archive_lock(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.execute_script(
            """
            window.__scoreLockHeld = false;
            window.__releaseScoreLock = null;
            window.__scoreLockBlocker = navigator.locks.request(
              'aphelian-score-archive',
              () => new Promise(resolve => {
                window.__scoreLockHeld = true;
                window.__releaseScoreLock = resolve;
              })
            );
            """
        )
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__scoreLockHeld === true')
        )

        try:
            self.driver.find_element("id", "rememberScoresButton").click()
            queued = self.driver.execute_script(
                """
                return {
                  cookie: document.cookie,
                  declineEnabled: !document.getElementById('declineScoresButton').disabled
                };
                """
            )
            self.driver.find_element("id", "declineScoresButton").click()
            declined = self.driver.execute_script(
                """
                return {
                  cookie: document.cookie,
                  archive: window.__ORRERY__.scoreArchive(),
                  consentHidden: document.getElementById('scoreConsent').hidden,
                  declinedVisible: !document.getElementById('scoreDeclined').hidden,
                  historyHidden: document.getElementById('scoreHistory').hidden,
                  status: document.getElementById('scoreArchiveStatus').textContent,
                  copy: document.getElementById('scoreDeclinedCopy').textContent
                };
                """
            )
        finally:
            settled = self.execute_awaited(
                """
                window.__releaseScoreLock();
                await window.__scoreLockBlocker;
                await navigator.locks.request('aphelian-score-archive', () => {});
                await new Promise(resolve => setTimeout(resolve, 0));
                return {
                  cookie: document.cookie,
                  archive: window.__ORRERY__.scoreArchive(),
                  consentHidden: document.getElementById('scoreConsent').hidden,
                  declinedVisible: !document.getElementById('scoreDeclined').hidden,
                  historyHidden: document.getElementById('scoreHistory').hidden,
                  status: document.getElementById('scoreArchiveStatus').textContent,
                  copy: document.getElementById('scoreDeclinedCopy').textContent,
                  announcement: document.getElementById('announcer').textContent
                };
                """
            )

        diagnostic = {"queued": queued, "declined": declined, "settled": settled}
        self.assertNotIn("aphelian_score_history=", queued["cookie"], json.dumps(diagnostic, indent=2))
        self.assertTrue(queued["declineEnabled"], json.dumps(diagnostic, indent=2))
        self.assertNotIn("aphelian_score_history=", declined["cookie"], json.dumps(diagnostic, indent=2))
        self.assertFalse(declined["archive"]["enabled"], json.dumps(diagnostic, indent=2))
        self.assertTrue(declined["consentHidden"], json.dumps(diagnostic, indent=2))
        self.assertTrue(declined["declinedVisible"], json.dumps(diagnostic, indent=2))
        self.assertTrue(declined["historyHidden"], json.dumps(diagnostic, indent=2))
        self.assertIn("off", declined["status"].lower())
        self.assertIn("no cookie was created", declined["copy"].lower())
        self.assertNotIn("aphelian_score_history=", settled["cookie"], json.dumps(diagnostic, indent=2))
        self.assertFalse(settled["archive"]["enabled"], json.dumps(diagnostic, indent=2))
        self.assertTrue(settled["consentHidden"], json.dumps(diagnostic, indent=2))
        self.assertTrue(settled["declinedVisible"], json.dumps(diagnostic, indent=2))
        self.assertTrue(settled["historyHidden"], json.dumps(diagnostic, indent=2))
        self.assertIn("off", settled["status"].lower())
        self.assertIn("no cookie was created", settled["copy"].lower())
        self.assertIn("score saving remains off", settled["announcement"].lower())

    def test_not_now_has_no_click_window_after_enable_commit_starts(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.execute_script(
            """
            window.__nativeSetTimeout = window.setTimeout;
            window.__scorePropagationHeld = false;
            window.__releaseScorePropagation = null;
            window.setTimeout = (callback, delay, ...args) => {
              if (delay === 100 && !window.__scorePropagationHeld) {
                window.__scorePropagationHeld = true;
                window.__releaseScorePropagation = () => callback(...args);
                return 0;
              }
              return window.__nativeSetTimeout(callback, delay, ...args);
            };
            """
        )

        try:
            self.driver.find_element("id", "rememberScoresButton").click()
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return window.__scorePropagationHeld === true')
            )
            committing = self.driver.execute_script(
                """
                const decline = document.getElementById('declineScoresButton');
                const before = {
                  cookie: document.cookie,
                  declineDisabled: decline.disabled,
                  consentVisible: !document.getElementById('scoreConsent').hidden,
                  declinedHidden: document.getElementById('scoreDeclined').hidden
                };
                decline.click();
                return {
                  ...before,
                  declinedHiddenAfterClick: document.getElementById('scoreDeclined').hidden
                };
                """
            )
        finally:
            settled = self.execute_awaited(
                """
                window.setTimeout = window.__nativeSetTimeout;
                window.__releaseScorePropagation();
                await navigator.locks.request('aphelian-score-archive', () => {});
                await Promise.resolve();
                return {
                  archive: window.__ORRERY__.scoreArchive(),
                  status: document.getElementById('scoreArchiveStatus').textContent
                };
                """
            )

        diagnostic = {"committing": committing, "settled": settled}
        self.assertIn("aphelian_score_history=", committing["cookie"], json.dumps(diagnostic, indent=2))
        self.assertTrue(committing["declineDisabled"], json.dumps(diagnostic, indent=2))
        self.assertTrue(committing["consentVisible"], json.dumps(diagnostic, indent=2))
        self.assertTrue(committing["declinedHidden"], json.dumps(diagnostic, indent=2))
        self.assertTrue(committing["declinedHiddenAfterClick"], json.dumps(diagnostic, indent=2))
        self.assertTrue(settled["archive"]["enabled"], json.dumps(diagnostic, indent=2))
        self.assertIn("on", settled["status"].lower())

    def test_debug_score_history_is_an_unsaved_preview(self):
        preview = {
            "version": 1,
            "runs": [{
                "score": 4321,
                "won": True,
                "bestChain": 9,
                "time": 54.3,
                "completedAt": "2026-09-04T12:00:00.000Z",
            }],
        }
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )

        before_run = self.driver.execute_script(
            """
            window.__ORRERY__.setScoreHistory(arguments[0]);
            return {
              cookie: document.cookie,
              archive: window.__ORRERY__.scoreArchive(),
              historyVisible: !document.getElementById('scoreHistory').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent
            };
            """,
            preview,
        )
        self.driver.execute_script("window.__ORRERY__.start(); window.__ORRERY__.finish(true);")
        after_run = self.driver.execute_script("return document.cookie")

        self.assertNotIn("aphelian_score_history=", before_run["cookie"])
        self.assertFalse(before_run["archive"]["enabled"], json.dumps(before_run, indent=2))
        self.assertEqual(preview, before_run["archive"]["history"])
        self.assertTrue(before_run["historyVisible"], json.dumps(before_run, indent=2))
        self.assertIn("preview", before_run["status"].lower())
        self.assertNotIn("aphelian_score_history=", after_run)

    def test_accepting_score_archive_creates_one_strict_first_party_cookie(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )

        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )
        cookie = self.driver.get_cookie("aphelian_score_history")
        archive = self.driver.execute_script(
            """
            return {
              diagnostic: window.__ORRERY__.scoreArchive(),
              consentHidden: document.getElementById('scoreConsent').hidden,
              historyVisible: !document.getElementById('scoreHistory').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent
            };
            """
        )

        self.assertIsNotNone(cookie, json.dumps(archive, indent=2))
        self.assertEqual("/", cookie["path"])
        self.assertEqual("Strict", cookie["sameSite"])
        self.assertGreater(cookie["expiry"], time.time() + 300 * 24 * 60 * 60)
        self.assertEqual(
            {
                "name": "aphelian_score_history",
                "enabled": True,
                "blocked": False,
                "reason": None,
                "history": {"version": 1, "runs": []},
            },
            archive["diagnostic"]
        )
        self.assertTrue(archive["consentHidden"], json.dumps(archive, indent=2))
        self.assertTrue(archive["historyVisible"], json.dumps(archive, indent=2))
        self.assertIn("on", archive["status"].lower())

    def test_remember_adopts_archive_created_after_consent_view_loaded(self):
        external_history = {
            "version": 1,
            "runs": [{
                "score": 8765,
                "won": True,
                "bestChain": 15,
                "time": 49.8,
                "completedAt": "2026-09-04T12:00:00.000Z",
            }],
        }
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )

        self.driver.execute_script(
            """
            const encoded = encodeURIComponent(JSON.stringify(arguments[0]));
            document.cookie = `aphelian_score_history=${encoded}; Max-Age=31536000; Path=/; SameSite=Strict`;
            window.__beforeRememberCookie = document.cookie;
            document.getElementById('rememberScoresButton').click();
            """,
            external_history,
        )
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )
        state = self.driver.execute_script(
            """
            return {
              before: window.__beforeRememberCookie,
              after: document.cookie,
              archive: window.__ORRERY__.scoreArchive(),
              historyVisible: !document.getElementById('scoreHistory').hidden
            };
            """
        )

        self.assertEqual(state["before"], state["after"], json.dumps(state, indent=2))
        self.assertTrue(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertEqual(external_history, state["archive"]["history"])
        self.assertTrue(state["historyVisible"], json.dumps(state, indent=2))

    def test_completed_run_is_saved_and_rendered_on_the_next_home_screen(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        completed = self.execute_awaited(
            """
            window.__ORRERY__.start();
            window.__ORRERY__.setElapsedTime(42.25);
            await window.__ORRERY__.finish(false);
            return {
              snapshot: window.__ORRERY__.snapshot(),
              archive: window.__ORRERY__.scoreArchive()
            };
            """
        )
        runs = completed["archive"]["history"]["runs"]
        self.assertEqual(1, len(runs), json.dumps(completed, indent=2))
        self.assertEqual(completed["snapshot"]["score"], runs[0]["score"])
        self.assertFalse(runs[0]["won"])
        self.assertEqual(0, runs[0]["bestChain"])
        self.assertEqual(42.3, runs[0]["time"])
        completed_at = datetime.fromisoformat(runs[0]["completedAt"].replace("Z", "+00:00"))
        self.assertLess(abs(datetime.now(timezone.utc).timestamp() - completed_at.timestamp()), 120)

        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        home = self.driver.execute_script(
            """
            return {
              mode: window.__ORRERY__.snapshot().mode,
              historyVisible: !document.getElementById('scoreHistory').hidden,
              summary: document.getElementById('scoreHistorySummary').textContent,
              rows: [...document.querySelectorAll('.score-history-item')].map(node => node.textContent)
            };
            """
        )
        self.assertEqual("title", home["mode"], json.dumps(home, indent=2))
        self.assertTrue(home["historyVisible"], json.dumps(home, indent=2))
        self.assertIn("1 completed rite", home["summary"])
        self.assertEqual(1, len(home["rows"]), json.dumps(home, indent=2))
        self.assertIn(str(runs[0]["score"]).zfill(6), home["rows"][0])
        self.assertIn("Totality", home["rows"][0])
        self.assertIn("00:43", home["rows"][0])

    def test_external_cookie_deletion_disables_saving_without_recreating_it(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        state = self.execute_awaited(
            """
            document.cookie = 'aphelian_score_history=; Max-Age=0; Path=/; SameSite=Strict';
            window.__ORRERY__.start();
            await window.__ORRERY__.finish(false);
            return {
              cookie: document.cookie,
              archive: window.__ORRERY__.scoreArchive(),
              consentVisible: !document.getElementById('scoreConsent').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent
            };
            """
        )

        self.assertNotIn("aphelian_score_history=", state["cookie"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertTrue(state["consentVisible"], json.dumps(state, indent=2))
        self.assertIn("off", state["status"].lower())

    def test_completed_run_merges_cookie_changes_made_after_page_load(self):
        external_run = {
            "score": 7777,
            "won": True,
            "bestChain": 12,
            "time": 61.2,
            "completedAt": "2026-09-04T12:00:00.000Z",
        }
        external_history = {"version": 1, "runs": [external_run]}
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        state = self.execute_awaited(
            """
            window.__ORRERY__.start();
            document.cookie = `aphelian_score_history=${encodeURIComponent(JSON.stringify(arguments[0]))}; Path=/; SameSite=Strict`;
            await window.__ORRERY__.finish(false);
            const value = document.cookie.split('; ')
              .find(part => part.startsWith('aphelian_score_history='))
              .slice('aphelian_score_history='.length);
            return {
              archive: window.__ORRERY__.scoreArchive(),
              stored: JSON.parse(decodeURIComponent(value))
            };
            """,
            external_history,
        )

        self.assertEqual(2, len(state["stored"]["runs"]), json.dumps(state, indent=2))
        self.assertEqual(external_run, state["stored"]["runs"][1])
        self.assertEqual(state["stored"], state["archive"]["history"])

    def test_overlapping_two_tab_completions_are_serialized_without_losing_either_run(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )
        first_tab = self.driver.current_window_handle
        second_tab = None

        try:
            self.driver.switch_to.new_window("tab")
            second_tab = self.driver.current_window_handle
            self.driver.get(f"{self.base_url}/index.html?debug=1")
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script(
                    'return typeof window.__ORRERY__ === "object" '
                    '&& window.__ORRERY__.scoreArchive().enabled'
                )
            )

            self.driver.switch_to.window(first_tab)
            self.driver.execute_script(
                """
                window.__scoreLockHeld = false;
                window.__releaseScoreLock = null;
                window.__scoreLockBlocker = navigator.locks.request(
                  'aphelian-score-archive',
                  () => new Promise(resolve => {
                    window.__scoreLockHeld = true;
                    window.__releaseScoreLock = resolve;
                  })
                );
                """
            )
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return window.__scoreLockHeld === true')
            )
            self.driver.execute_script(
                """
                window.__scoreSaveSettled = false;
                window.__scoreSaveError = '';
                window.__scoreSaveResult = null;
                window.__ORRERY__.start();
                window.__ORRERY__.setElapsedTime(11);
                Promise.resolve(window.__ORRERY__.finish(false)).then(
                  result => {
                    window.__scoreSaveResult = result;
                    window.__scoreSaveSettled = true;
                  },
                  error => {
                    window.__scoreSaveError = `${error.name}: ${error.message}`;
                    window.__scoreSaveSettled = true;
                  }
                );
                """
            )

            self.driver.switch_to.window(second_tab)
            self.driver.execute_script(
                """
                window.__scoreSaveSettled = false;
                window.__scoreSaveError = '';
                window.__scoreSaveResult = null;
                window.__ORRERY__.start();
                window.__ORRERY__.setElapsedTime(22);
                Promise.resolve(window.__ORRERY__.finish(false)).then(
                  result => {
                    window.__scoreSaveResult = result;
                    window.__scoreSaveSettled = true;
                  },
                  error => {
                    window.__scoreSaveError = `${error.name}: ${error.message}`;
                    window.__scoreSaveSettled = true;
                  }
                );
                """
            )

            second_pending = self.driver.execute_script(
                "return !window.__scoreSaveSettled"
            )
            self.driver.switch_to.window(first_tab)
            first_pending = self.driver.execute_script(
                "return !window.__scoreSaveSettled"
            )
            self.driver.execute_script("window.__releaseScoreLock()")

            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return window.__scoreSaveSettled === true')
            )
            self.driver.switch_to.window(second_tab)
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return window.__scoreSaveSettled === true')
            )
            second_state = self.driver.execute_script(
                """
                const value = document.cookie.split('; ')
                  .find(part => part.startsWith('aphelian_score_history='))
                  .slice('aphelian_score_history='.length);
                return {
                  error: window.__scoreSaveError,
                  result: window.__scoreSaveResult,
                  archive: window.__ORRERY__.scoreArchive(),
                  status: document.getElementById('scoreArchiveStatus').textContent,
                  cookie: document.cookie,
                  stored: JSON.parse(decodeURIComponent(value))
                };
                """
            )

            self.driver.switch_to.window(first_tab)
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script('return window.__scoreSaveSettled === true')
            )
            first_state = self.driver.execute_script(
                """
                return {
                  error: window.__scoreSaveError,
                  result: window.__scoreSaveResult,
                  archive: window.__ORRERY__.scoreArchive(),
                  status: document.getElementById('scoreArchiveStatus').textContent,
                  cookie: document.cookie
                };
                """
            )
        finally:
            if second_tab and second_tab in self.driver.window_handles:
                self.driver.switch_to.window(second_tab)
                self.driver.close()
            if first_tab in self.driver.window_handles:
                self.driver.switch_to.window(first_tab)

        self.assertTrue(first_pending, "first completion bypassed the held score lock")
        self.assertTrue(second_pending, "second completion bypassed the held score lock")
        diagnostic = {"first": first_state, "second": second_state}
        self.assertEqual("", first_state["error"], json.dumps(diagnostic, indent=2))
        self.assertEqual("", second_state["error"], json.dumps(diagnostic, indent=2))
        self.assertTrue(first_state["result"], json.dumps(diagnostic, indent=2))
        self.assertTrue(second_state["result"], json.dumps(diagnostic, indent=2))
        stored = second_state["stored"]
        self.assertEqual(2, len(stored["runs"]), json.dumps(diagnostic, indent=2))
        self.assertEqual({11, 22}, {run["time"] for run in stored["runs"]})

    def test_cookie_getter_exception_disables_archive_without_breaking_results(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        state = self.execute_awaited(
            """
            Object.defineProperty(document, 'cookie', {
              configurable: true,
              get() { throw new DOMException('Cookie access blocked', 'SecurityError'); },
              set() { throw new DOMException('Cookie access blocked', 'SecurityError'); }
            });
            window.__ORRERY__.start();
            await window.__ORRERY__.finish(false);
            return {
              mode: window.__ORRERY__.snapshot().mode,
              overlayHidden: document.getElementById('overlay').getAttribute('aria-hidden'),
              archive: window.__ORRERY__.scoreArchive(),
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent,
              copy: document.getElementById('scoreDeclinedCopy').textContent,
              noticeVisible: !document.getElementById('scoreSaveNotice').hidden,
              notice: document.getElementById('scoreSaveNotice').textContent
            };
            """
        )

        self.assertEqual("lost", state["mode"], json.dumps(state, indent=2))
        self.assertEqual("false", state["overlayHidden"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertTrue(state["declinedVisible"], json.dumps(state, indent=2))
        self.assertIn("unavailable", state["status"].lower())
        self.assertIn("no data was saved", state["copy"].lower())
        self.assertTrue(state["noticeVisible"], json.dumps(state, indent=2))
        self.assertIn("score not saved", state["notice"].lower())

    def test_cookie_setter_exception_shows_no_storage_ui(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )

        self.driver.execute_script(
            """
            window.__cookieErrors = [];
            addEventListener('error', event => window.__cookieErrors.push(event.message));
            Object.defineProperty(document, 'cookie', {
              configurable: true,
              get() { return ''; },
              set() { throw new DOMException('Cookie writes blocked', 'SecurityError'); }
            });
            const remember = document.getElementById('rememberScoresButton');
            remember.focus();
            remember.click();
            """
        )
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                "return !document.getElementById('scoreDeclined').hidden"
            )
        )
        state = self.driver.execute_script(
            """
            const focused = document.activeElement;
            return {
              errors: window.__cookieErrors,
              archive: window.__ORRERY__.scoreArchive(),
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent,
              copy: document.getElementById('scoreDeclinedCopy').textContent,
              focusedId: focused && focused.id,
              focusedVisible: Boolean(focused && focused.getClientRects().length)
            };
            """
        )

        self.assertEqual([], state["errors"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertTrue(state["declinedVisible"], json.dumps(state, indent=2))
        self.assertIn("unavailable", state["status"].lower())
        self.assertIn("no data was saved", state["copy"].lower())
        self.assertNotEqual("rememberScoresButton", state["focusedId"])
        self.assertTrue(state["focusedVisible"], json.dumps(state, indent=2))

    def test_archive_fails_closed_when_web_locks_are_unavailable(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )

        state = self.driver.execute_script(
            """
            Object.defineProperty(navigator, 'locks', {
              configurable: true,
              value: undefined
            });
            const remember = document.getElementById('rememberScoresButton');
            remember.focus();
            remember.click();
            const focused = document.activeElement;
            return {
              cookie: document.cookie,
              archive: window.__ORRERY__.scoreArchive(),
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent,
              copy: document.getElementById('scoreDeclinedCopy').textContent,
              focusedId: focused && focused.id,
              focusedVisible: Boolean(focused && focused.getClientRects().length)
            };
            """
        )

        self.assertNotIn("aphelian_score_history=", state["cookie"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertTrue(state["declinedVisible"], json.dumps(state, indent=2))
        self.assertIn("synchronization unavailable", state["status"].lower())
        self.assertIn("web locks", state["copy"].lower())
        self.assertNotEqual("rememberScoresButton", state["focusedId"])
        self.assertTrue(state["focusedVisible"], json.dumps(state, indent=2))

    def test_cookie_deleter_exception_is_reported_without_breaking_play(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        self.driver.execute_script(
            """
            const savedCookie = document.cookie;
            window.__cookieErrors = [];
            addEventListener('error', event => window.__cookieErrors.push(event.message));
            Object.defineProperty(document, 'cookie', {
              configurable: true,
              get() { return savedCookie; },
              set() { throw new DOMException('Cookie deletion blocked', 'SecurityError'); }
            });
            const forget = document.getElementById('forgetScoresButton');
            forget.focus();
            forget.click();
            """
        )
        WebDriverWait(self.driver, 10).until(
            lambda driver: "delete failed" in driver.execute_script(
                "return document.getElementById('scoreArchiveStatus').textContent.toLowerCase()"
            )
        )
        state = self.driver.execute_script(
            """
            const focused = document.activeElement;
            document.getElementById('riteButton').click();
            return {
              errors: window.__cookieErrors,
              archive: window.__ORRERY__.scoreArchive(),
              mode: window.__ORRERY__.snapshot().mode,
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent,
              copy: document.getElementById('scoreDeclinedCopy').textContent,
              focusedId: focused && focused.id,
              focusedVisible: Boolean(focused && focused.getClientRects().length)
            };
            """
        )

        self.assertEqual([], state["errors"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertEqual("playing", state["mode"], json.dumps(state, indent=2))
        self.assertTrue(state["declinedVisible"], json.dumps(state, indent=2))
        self.assertIn("delete failed", state["status"].lower())
        self.assertIn("remove it in devtools", state["copy"].lower())
        self.assertNotEqual("forgetScoresButton", state["focusedId"])
        self.assertTrue(state["focusedVisible"], json.dumps(state, indent=2))

    def test_cookie_getter_exception_after_delete_reports_unverified_deletion(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        self.driver.execute_script(
            """
            const savedCookie = document.cookie;
            let deleteAttempted = false;
            window.__cookieErrors = [];
            addEventListener('error', event => window.__cookieErrors.push(event.message));
            Object.defineProperty(document, 'cookie', {
              configurable: true,
              get() {
                if (deleteAttempted) throw new DOMException('Cookie readback blocked', 'SecurityError');
                return savedCookie;
              },
              set() { deleteAttempted = true; }
            });
            const forget = document.getElementById('forgetScoresButton');
            forget.focus();
            forget.click();
            """
        )
        WebDriverWait(self.driver, 10).until(
            lambda driver: "delete unverified" in driver.execute_script(
                "return document.getElementById('scoreArchiveStatus').textContent.toLowerCase()"
            )
        )
        state = self.driver.execute_script(
            """
            const focused = document.activeElement;
            return {
              errors: window.__cookieErrors,
              archive: window.__ORRERY__.scoreArchive(),
              consentVisible: !document.getElementById('scoreConsent').hidden,
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent,
              copy: document.getElementById('scoreDeclinedCopy').textContent,
              focusedId: focused && focused.id,
              focusedVisible: Boolean(focused && focused.getClientRects().length)
            };
            """
        )

        self.assertEqual([], state["errors"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertFalse(state["consentVisible"], json.dumps(state, indent=2))
        self.assertTrue(state["declinedVisible"], json.dumps(state, indent=2))
        self.assertIn("delete unverified", state["status"].lower())
        self.assertIn("could not confirm deletion", state["copy"].lower())
        self.assertIn("remove it in devtools", state["copy"].lower())
        self.assertNotEqual("forgetScoresButton", state["focusedId"])
        self.assertTrue(state["focusedVisible"], json.dumps(state, indent=2))

    def test_silently_rejected_forget_revokes_consent_and_never_renews_cookie(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )
        self.execute_awaited(
            """
            window.__ORRERY__.start();
            window.__ORRERY__.setElapsedTime(12);
            await window.__ORRERY__.finish(false);
            """
        )
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return window.__ORRERY__.scoreArchive().history.runs.length === 1'
            )
        )
        original = self.driver.get_cookie("aphelian_score_history")

        immediate = self.driver.execute_script(
            """
            window.__physicalScoreCookie = document.cookie;
            window.__scoreCookieWrites = [];
            Object.defineProperty(document, 'cookie', {
              configurable: true,
              get() { return window.__physicalScoreCookie; },
              set(value) { window.__scoreCookieWrites.push(value); }
            });
            const forget = document.getElementById('forgetScoresButton');
            forget.focus();
            forget.click();
            const focused = document.activeElement;
            return {
              archive: window.__ORRERY__.scoreArchive(),
              physicalCookie: document.cookie,
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              historyHidden: document.getElementById('scoreHistory').hidden,
              rowCount: document.querySelectorAll('.score-history-item').length,
              focusedId: focused && focused.id,
              focusedVisible: Boolean(focused && focused.getClientRects().length)
            };
            """
        )
        WebDriverWait(self.driver, 10).until(
            lambda driver: "delete failed" in driver.execute_script(
                "return document.getElementById('scoreArchiveStatus').textContent.toLowerCase()"
            )
        )
        failed = self.driver.execute_script(
            """
            return {
              archive: window.__ORRERY__.scoreArchive(),
              physicalCookie: document.cookie,
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              historyHidden: document.getElementById('scoreHistory').hidden,
              rowCount: document.querySelectorAll('.score-history-item').length,
              status: document.getElementById('scoreArchiveStatus').textContent,
              copy: document.getElementById('scoreDeclinedCopy').textContent,
              writesAfterForget: window.__scoreCookieWrites.length
            };
            """
        )
        later = self.execute_awaited(
            """
            window.__ORRERY__.start();
            await window.__ORRERY__.finish(false);
            return {
              archive: window.__ORRERY__.scoreArchive(),
              physicalCookie: document.cookie,
              historyHidden: document.getElementById('scoreHistory').hidden,
              rowCount: document.querySelectorAll('.score-history-item').length,
              writes: [...window.__scoreCookieWrites]
            };
            """
        )
        after = self.driver.get_cookie("aphelian_score_history")
        state = {"immediate": immediate, "failed": failed, "later": later}

        self.assertIsNotNone(original)
        self.assertIsNotNone(after)
        self.assertEqual(original["value"], after["value"], json.dumps(state, indent=2))
        self.assertFalse(immediate["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertEqual([], immediate["archive"]["history"]["runs"])
        self.assertTrue(immediate["declinedVisible"], json.dumps(state, indent=2))
        self.assertTrue(immediate["historyHidden"], json.dumps(state, indent=2))
        self.assertEqual(0, immediate["rowCount"])
        self.assertNotEqual("forgetScoresButton", immediate["focusedId"])
        self.assertTrue(immediate["focusedVisible"], json.dumps(state, indent=2))
        self.assertFalse(failed["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertEqual([], failed["archive"]["history"]["runs"])
        self.assertIn("delete failed", failed["status"].lower())
        self.assertIn("remove it", failed["copy"].lower())
        self.assertTrue(failed["historyHidden"], json.dumps(state, indent=2))
        self.assertEqual(0, failed["rowCount"])
        self.assertFalse(later["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertEqual([], later["archive"]["history"]["runs"])
        self.assertEqual(immediate["physicalCookie"], later["physicalCookie"])
        self.assertTrue(later["historyHidden"], json.dumps(state, indent=2))
        self.assertEqual(0, later["rowCount"])
        self.assertEqual(failed["writesAfterForget"], len(later["writes"]), json.dumps(state, indent=2))

    def test_failed_completed_run_write_is_visible_and_disables_stale_state(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        state = self.execute_awaited(
            """
            const savedCookie = document.cookie;
            Object.defineProperty(document, 'cookie', {
              configurable: true,
              get() { return savedCookie; },
              set() { /* simulate a policy silently rejecting the write */ }
            });
            window.__ORRERY__.start();
            await window.__ORRERY__.finish(false);
            return {
              archive: window.__ORRERY__.scoreArchive(),
              mode: window.__ORRERY__.snapshot().mode,
              overlayHidden: document.getElementById('overlay').getAttribute('aria-hidden'),
              declinedVisible: !document.getElementById('scoreDeclined').hidden,
              status: document.getElementById('scoreArchiveStatus').textContent,
              copy: document.getElementById('scoreDeclinedCopy').textContent,
              notice: document.getElementById('scoreSaveNotice').textContent,
              noticeVisible: !document.getElementById('scoreSaveNotice').hidden,
              eyebrow: document.getElementById('eyebrow').textContent,
              announcement: document.getElementById('announcer').textContent
            };
            """
        )

        self.assertEqual("lost", state["mode"], json.dumps(state, indent=2))
        self.assertEqual("false", state["overlayHidden"], json.dumps(state, indent=2))
        self.assertFalse(state["archive"]["enabled"], json.dumps(state, indent=2))
        self.assertTrue(state["declinedVisible"], json.dumps(state, indent=2))
        self.assertIn("save failed", state["status"].lower())
        self.assertIn("completed rite was not saved", state["copy"].lower())
        self.assertTrue(state["noticeVisible"], json.dumps(state, indent=2))
        self.assertIn("score not saved", state["notice"].lower())
        self.assertEqual("The orrery has fallen", state["eyebrow"])
        self.assertIn("score was not saved", state["announcement"].lower())

    def test_forgetting_score_archive_deletes_the_cookie_and_history(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )
        self.execute_awaited(
            "window.__ORRERY__.start(); await window.__ORRERY__.finish(true);"
        )
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().history.runs.length === 1')
        )

        self.driver.find_element("id", "forgetScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                "return !document.cookie.includes('aphelian_score_history=') "
                "&& !document.getElementById('scoreConsent').hidden"
            )
        )
        state = self.driver.execute_script(
            """
            return {
              cookie: document.cookie,
              archive: window.__ORRERY__.scoreArchive(),
              consentVisible: !document.getElementById('scoreConsent').hidden,
              historyHidden: document.getElementById('scoreHistory').hidden,
              rowCount: document.querySelectorAll('.score-history-item').length
            };
            """
        )
        self.assertNotIn("aphelian_score_history=", state["cookie"], json.dumps(state, indent=2))
        self.assertEqual({"version": 1, "runs": []}, state["archive"]["history"])
        self.assertFalse(state["archive"]["enabled"])
        self.assertTrue(state["consentVisible"], json.dumps(state, indent=2))
        self.assertTrue(state["historyHidden"], json.dumps(state, indent=2))
        self.assertEqual(0, state["rowCount"])

    def test_standalone_index_starts_when_only_the_selected_file_is_available(self):
        with tempfile.TemporaryDirectory() as folder:
            standalone = Path(folder, "index.html")
            shutil.copy2(REPO / "index.html", standalone)
            self.driver.get(standalone.as_uri() + "?debug=1")
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.execute_script(
                    'return document.readyState === "complete" && typeof window.__ORRERY__ === "object"'
                )
            )
            self.driver.execute_script(
                """
                window.__standaloneErrors = [];
                addEventListener('error', event => window.__standaloneErrors.push(event.message));
                """
            )
            archive = self.driver.execute_script(
                """
                return {
                  diagnostic: window.__ORRERY__.scoreArchive(),
                  status: document.getElementById('scoreArchiveStatus').textContent,
                  declinedVisible: !document.getElementById('scoreDeclined').hidden,
                  copy: document.getElementById('scoreDeclinedCopy').textContent,
                  cookie: document.cookie
                };
                """
            )
            self.assertFalse(archive["diagnostic"]["enabled"], json.dumps(archive, indent=2))
            self.assertEqual("", archive["cookie"])
            self.assertIn("unavailable", archive["status"].lower())
            self.assertTrue(archive["declinedVisible"], json.dumps(archive, indent=2))
            self.assertIn("http://localhost", archive["copy"])
            self.driver.find_element("id", "riteButton").click()
            time.sleep(.75)
            state = self.driver.execute_script(
                """
                let snapshot = null;
                try { snapshot = window.__ORRERY__.snapshot(); }
                catch (error) { window.__standaloneErrors.push(String(error)); }
                return {
                  rules: typeof window.AphelionRules,
                  snapshot,
                  errors: window.__standaloneErrors
                };
                """
            )
            self.assertEqual("object", state["rules"], json.dumps(state, indent=2))
            self.assertEqual([], state["errors"], json.dumps(state, indent=2))
            self.assertIsNotNone(state["snapshot"], json.dumps(state, indent=2))
            self.assertEqual("playing", state["snapshot"]["mode"], json.dumps(state, indent=2))
            self.assertGreater(state["snapshot"]["time"], .5, json.dumps(state, indent=2))

    def test_boss_fight_continues_past_two_minutes_and_late_win_keeps_elapsed_time(self):
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="900" height="700" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return document.readyState === "complete" && typeof window.__ORRERY__ === "object"'
            )
        )
        checkpoint = self.driver.execute_script(
            """
            window.__ORRERY__.start();
            window.__ORRERY__.forceBoss();
            const advanced = window.__ORRERY__.setElapsedTime(121);
            return { advanced, snapshot: window.__ORRERY__.snapshot() };
            """
        )
        self.assertTrue(checkpoint["advanced"], json.dumps(checkpoint, indent=2))
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script(
                'const snapshot = window.__ORRERY__.snapshot(); '
                'return snapshot.mode === "playing" && snapshot.time > 121.25;'
            )
        )
        active = self.driver.execute_script("return window.__ORRERY__.snapshot()")
        self.assertEqual("playing", active["mode"], json.dumps(active, indent=2))
        self.assertGreater(active["time"], 121.25, json.dumps(active, indent=2))
        self.assertEqual(checkpoint["snapshot"]["score"], active["score"], json.dumps(active, indent=2))
        self.assertIsNotNone(active["boss"], json.dumps(active, indent=2))

        self.driver.execute_script("window.__ORRERY__.defeatBoss()")
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.snapshot().mode === "won"')
        )
        result = self.driver.execute_script(
            """
            const snapshot = window.__ORRERY__.snapshot();
            return {
              snapshot,
              resultTime: document.getElementById('resultTime').textContent,
              expectedTime: window.AphelionRules.formatTime(snapshot.time),
              underTwoMinutes: snapshot.achievements
                .find(achievement => achievement.id === 'under-two-minutes').unlocked
            };
            """
        )
        self.assertGreater(result["snapshot"]["time"], 121, json.dumps(result, indent=2))
        self.assertEqual(active["score"] + 11250, result["snapshot"]["score"], json.dumps(result, indent=2))
        self.assertEqual(result["expectedTime"], result["resultTime"], json.dumps(result, indent=2))
        self.assertFalse(result["underTwoMinutes"], json.dumps(result, indent=2))
        self.driver.switch_to.default_content()

    def test_result_content_is_visible_at_short_and_intermediate_viewports(self):
        viewports = [
            (320, 234),
            (320, 300),
            (320, 301),
            (320, 420),
            (320, 568),
            (340, 234),
            (340, 420),
            (341, 234),
            (341, 420),
            (359, 234),
            (359, 420),
            (360, 234),
            (360, 420),
            (360, 640),
            (390, 234),
            (390, 420),
            (390, 844),
            (420, 234),
            (420, 420),
            (420, 421),
            (420, 844),
            (421, 420),
            (421, 844),
            (430, 844),
            (440, 844),
            (460, 844),
            (480, 844),
            (500, 844),
            (600, 844),
            (760, 844),
            (500, 320),
            (500, 234),
            (519, 234),
            (519, 420),
            (520, 234),
            (520, 300),
            (520, 301),
            (520, 420),
            (740, 300),
            (740, 301),
            (740, 380),
            (900, 380),
            (1440, 380),
            (500, 520),
            (639, 420),
            (639, 421),
            (639, 600),
            (640, 420),
            (640, 421),
            (640, 600),
            (700, 500),
            (740, 500),
            (760, 420),
            (760, 421),
            (760, 521),
            (760, 600),
            (761, 420),
            (761, 421),
            (761, 521),
            (761, 600),
            (800, 500),
            (800, 600),
            (900, 500),
            (1000, 600),
            (1040, 420),
            (1040, 421),
            (1040, 521),
            (1040, 600),
            (1040, 610),
            (1040, 611),
            (1041, 420),
            (1041, 421),
            (1041, 500),
            (1041, 521),
            (1041, 600),
            (1041, 610),
            (1041, 611),
            (1050, 600),
            (1050, 611),
            (1075, 600),
            (1075, 611),
            (1100, 600),
            (1100, 611),
            (1200, 600),
            (1200, 611),
            (1280, 421),
            (1280, 521),
            (1280, 600),
            (1280, 610),
            (1280, 611),
            (1280, 700),
            (1281, 421),
            (1281, 521),
            (1281, 600),
            (1281, 610),
            (1281, 611),
            (1281, 700),
        ]
        failures = []
        for width, height in viewports:
            metrics = self.result_metrics(width, height)
            if metrics["briefing"]["top"] < 0 or metrics["briefing"]["bottom"] > height:
                failures.append({"viewport": [width, height], "briefing": metrics["briefing"]})
            if metrics["achievements"]["top"] < 0 or metrics["achievements"]["bottom"] > height:
                failures.append({"viewport": [width, height], "achievements": metrics["achievements"]})
            sound = metrics["sound"]
            results = metrics["results"]
            sound_overlaps_results = (
                sound["visible"]
                and sound["left"] < results["right"]
                and sound["right"] > results["left"]
                and sound["top"] < results["bottom"]
                and sound["bottom"] > results["top"]
            )
            if sound_overlaps_results:
                failures.append({"viewport": [width, height], "soundOverlapsResults": True})
            if metrics["actions"]["top"] < 0 or metrics["actions"]["bottom"] > height:
                failures.append({"viewport": [width, height], "actions": metrics["actions"]})
            if metrics["clippedTitles"]:
                failures.append({"viewport": [width, height], "clippedTitles": metrics["clippedTitles"]})
            if metrics["clippedDifficulties"]:
                failures.append(
                    {"viewport": [width, height], "clippedDifficulties": metrics["clippedDifficulties"]}
                )
            if metrics["clippedButtons"]:
                failures.append({"viewport": [width, height], "clippedButtons": metrics["clippedButtons"]})
            if metrics["horizontalOverflow"]:
                failures.append({"viewport": [width, height], "horizontalOverflow": True})
        self.assertEqual([], failures, json.dumps(failures, indent=2))

    def test_six_figure_rite_achievement_unlocks_in_run_results(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        result = self.execute_awaited(
            """
            window.__ORRERY__.start();
            const scoreSet = window.__ORRERY__.setScore(100000);
            await window.__ORRERY__.finish(true);
            const achievement = window.__ORRERY__.snapshot().achievements
              .find(item => item.id === 'score-100k');
            const row = [...document.querySelectorAll('.achievement-item')]
              .find(item => item.getAttribute('aria-label').startsWith('SIX-FIGURE RITE.'));
            return {
              scoreSet,
              achievement,
              rowUnlocked: Boolean(row && row.classList.contains('is-unlocked')),
              rowLabel: row ? row.getAttribute('aria-label') : ''
            };
            """
        )
        self.assertTrue(result["scoreSet"], json.dumps(result, indent=2))
        self.assertEqual(
            {"id": "score-100k", "difficulty": "HARD", "unlocked": True},
            result["achievement"],
        )
        self.assertTrue(result["rowUnlocked"], json.dumps(result, indent=2))
        self.assertIn("Earned", result["rowLabel"])
        self.assertIn("100,000 or more", result["rowLabel"])

    def test_return_home_button_restores_title_screen_after_a_run(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.execute_script("window.__ORRERY__.start(); window.__ORRERY__.finish(true)")
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.snapshot().mode === "won"')
        )

        home_button = self.driver.find_element("id", "homeButton")
        self.assertTrue(home_button.is_displayed())
        home_button.click()

        state = self.driver.execute_script(
            """
            const overlay = document.getElementById('overlay');
            const home = document.getElementById('homeButton');
            return {
              mode: window.__ORRERY__.snapshot().mode,
              overlayState: overlay.dataset.state,
              overlayHidden: overlay.getAttribute('aria-hidden'),
              title: document.getElementById('mainTitle').textContent,
              archiveVisible: getComputedStyle(document.getElementById('scoreArchive')).display !== 'none',
              homeVisible: getComputedStyle(home).display !== 'none',
              playingClass: document.body.classList.contains('is-playing'),
              focused: document.activeElement && document.activeElement.id
            };
            """
        )
        self.assertEqual(
            {
                "mode": "title",
                "overlayState": "title",
                "overlayHidden": "false",
                "title": "APHELIAN",
                "archiveVisible": True,
                "homeVisible": False,
                "playingClass": False,
                "focused": "riteButton",
            },
            state,
        )

    def test_return_home_refreshes_the_score_archive_after_an_in_flight_save(self):
        self.driver.get(f"{self.base_url}/index.html?debug=1")
        self.driver.delete_all_cookies()
        self.driver.refresh()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return typeof window.__ORRERY__ === "object"')
        )
        self.driver.find_element("id", "rememberScoresButton").click()
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script('return window.__ORRERY__.scoreArchive().enabled')
        )

        state = self.execute_awaited(
            """
            window.__ORRERY__.start();
            window.__ORRERY__.setScore(43210);
            const save = window.__ORRERY__.finish(true);
            document.getElementById('homeButton').click();
            await save;
            return {
              mode: window.__ORRERY__.snapshot().mode,
              savedRuns: window.__ORRERY__.scoreArchive().history.runs.length,
              renderedRows: document.getElementById('scoreHistoryList').children.length,
              summary: document.getElementById('scoreHistorySummary').textContent
            };
            """
        )
        self.assertEqual("title", state["mode"], json.dumps(state, indent=2))
        self.assertEqual(1, state["savedRuns"], json.dumps(state, indent=2))
        self.assertEqual(1, state["renderedRows"], json.dumps(state, indent=2))
        self.assertIn("1 completed rite saved", state["summary"])

    def test_share_feedback_resets_before_the_next_result(self):
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="900" height="700" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return document.readyState === "complete" && typeof window.__ORRERY__ === "object"'
            )
        )
        self.driver.execute_script("window.__ORRERY__.start(); window.__ORRERY__.finish(true)")
        share = self.driver.find_element("id", "shareButton")
        share.click()
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script(
                'return document.getElementById("shareButton").textContent.trim().toUpperCase() !== "SHARE RUN"'
            )
        )
        self.driver.find_element("id", "riteButton").click()
        self.assertEqual("playing", self.driver.execute_script("return window.__ORRERY__.snapshot().mode"))
        time.sleep(2)
        self.driver.execute_script("window.__ORRERY__.finish(true)")
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script(
                'return window.__ORRERY__.snapshot().mode === "won" '
                '&& getComputedStyle(document.getElementById("shareButton")).display !== "none"'
            )
        )
        label = self.driver.execute_script(
            'return document.getElementById("shareButton").textContent.trim().toUpperCase()'
        )
        self.assertEqual("SHARE RUN", label)
        self.driver.switch_to.default_content()

    def test_new_share_attempt_clears_feedback_even_when_cancelled(self):
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="900" height="700" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return document.readyState === "complete" && typeof window.__ORRERY__ === "object"'
            )
        )
        self.driver.execute_script(
            """
            Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });
            Object.defineProperty(navigator, 'clipboard', {
              configurable: true,
              value: { writeText: () => Promise.resolve() }
            });
            window.__ORRERY__.start();
            window.__ORRERY__.finish(true);
            """
        )
        self.driver.find_element("id", "shareButton").click()
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script(
                'return document.getElementById("shareButton").textContent.trim().toUpperCase() === "RUN COPIED"'
            )
        )
        self.driver.execute_script(
            """
            Object.defineProperty(navigator, 'share', {
              configurable: true,
              value: () => Promise.reject(Object.assign(new Error('cancelled'), { name: 'AbortError' }))
            });
            """
        )
        self.driver.find_element("id", "shareButton").click()
        time.sleep(2)
        label = self.driver.execute_script(
            'return document.getElementById("shareButton").textContent.trim().toUpperCase()'
        )
        announcement = self.driver.execute_script(
            'return document.getElementById("announcer").textContent.trim()'
        )
        self.assertEqual("SHARE RUN", label)
        self.assertEqual("", announcement)
        self.driver.switch_to.default_content()

    def test_completed_share_from_an_old_run_cannot_change_the_new_result(self):
        wrapper = (
            "<!doctype html><style>html,body{margin:0}iframe{display:block;border:0}</style>"
            f'<iframe id="gameFrame" width="900" height="700" '
            f'src="{self.base_url}/index.html?debug=1"></iframe>'
        )
        self.driver.get("data:text/html;charset=utf-8," + quote(wrapper))
        frame = self.driver.find_element("id", "gameFrame")
        self.driver.switch_to.frame(frame)
        WebDriverWait(self.driver, 10).until(
            lambda driver: driver.execute_script(
                'return document.readyState === "complete" && typeof window.__ORRERY__ === "object"'
            )
        )
        self.driver.execute_script(
            """
            Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });
            Object.defineProperty(navigator, 'clipboard', {
              configurable: true,
              value: {
                writeText: () => new Promise(resolve => { window.__resolveOldShare = resolve; })
              }
            });
            window.__ORRERY__.start();
            window.__ORRERY__.finish(true);
            """
        )
        self.driver.find_element("id", "shareButton").click()
        WebDriverWait(self.driver, 5).until(
            lambda driver: driver.execute_script('return typeof window.__resolveOldShare === "function"')
        )
        self.driver.find_element("id", "riteButton").click()
        self.driver.execute_script("window.__ORRERY__.finish(true); window.__resolveOldShare()")
        time.sleep(.1)
        label = self.driver.execute_script(
            'return document.getElementById("shareButton").textContent.trim().toUpperCase()'
        )
        self.assertEqual("SHARE RUN", label)
        self.driver.switch_to.default_content()


if __name__ == "__main__":
    unittest.main(verbosity=2)
