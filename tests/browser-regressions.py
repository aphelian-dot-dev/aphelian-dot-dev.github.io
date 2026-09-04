# pyright: reportMissingImports=false

import json
import shutil
import tempfile
import threading
import time
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait


REPO = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
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
