"""Lost WebGL must gate gameplay state, not just unfocused keyboard input."""
import tempfile
import unittest
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]


class ContextLossInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.file = Path(cls.tmp.name) / 'index.html'
        html = (ROOT / 'index.html').read_text().replace(
            'window.__ORRERY__ = Object.freeze(debugApi);',
            'window.__ORRERY__ = Object.freeze(debugApi); window.__RESUME_QA__ = resumeGame;')
        cls.file.write_text(html)
        options = Options()
        options.add_argument('-headless')
        options.set_preference('webgl.force-enabled', True)
        cls.d = webdriver.Firefox(options=options)
        cls.d.set_window_size(1280, 900)

    @classmethod
    def tearDownClass(cls):
        cls.d.quit()
        cls.tmp.cleanup()

    def lose(self, start=True):
        d = self.d
        d.get(self.file.as_uri() + '?debug=1')
        WebDriverWait(d, 10).until(lambda d: d.execute_script(
            'return window.__ORRERY__?.renderer().triangles > 0'))
        if start:
            d.find_element('id', 'riteButton').click()
        d.execute_script('''window.lostContext=document.getElementById('stage3D')
            .getContext('webgl2').getExtension('WEBGL_lose_context'); lostContext.loseContext();''')
        WebDriverWait(d, 5).until(lambda d: not d.find_element('id', 'view3D').is_enabled())
        self.assertEqual(self.mode(), 'paused' if start else 'title')

    def mode(self):
        return self.d.execute_script('return window.__ORRERY__.snapshot().mode')

    def test_focused_controls_cannot_resume(self):
        for target in ['soundButton', 'qaInput']:
            for key in ['p', Keys.ESCAPE]:
                with self.subTest(target=target, key=key):
                    self.lose()
                    if target == 'qaInput':
                        self.d.execute_script("const input=document.createElement('input'); input.id='qaInput'; document.body.append(input);")
                    self.d.find_element('id', target).send_keys(key)
                    self.assertEqual(self.mode(), 'paused', 'Shortcut bypassed lost-context gate')

    def test_state_entry_points_cannot_resume_or_start(self):
        self.lose()
        self.d.execute_script('window.__RESUME_QA__()')
        self.assertEqual(self.mode(), 'paused')
        self.d.execute_script('window.__ORRERY__.start()')
        self.assertEqual(self.mode(), 'paused')
        self.lose(start=False)
        self.d.execute_script('window.__ORRERY__.start()')
        self.assertEqual(self.mode(), 'title')

    def test_native_controls_fallback_and_manual_recovery(self):
        self.lose()
        sound = self.d.find_element('id', 'soundButton')
        for key in ['m', Keys.RETURN, Keys.ENTER, Keys.SPACE]:
            before = sound.get_attribute('aria-pressed')
            sound.send_keys(key)
            self.assertNotEqual(sound.get_attribute('aria-pressed'), before, repr(key))
            self.assertEqual(self.mode(), 'paused')
        sound.send_keys(Keys.TAB)
        self.assertNotEqual(self.d.execute_script('return document.activeElement.id'), 'soundButton')
        self.d.execute_script('lostContext.restoreContext()')
        WebDriverWait(self.d, 5).until(lambda d: d.find_element('id', 'view3D').is_enabled())
        self.assertEqual(self.mode(), 'paused')
        sound.send_keys('p')
        self.assertEqual(self.mode(), 'playing')
        for key in [Keys.ENTER, Keys.SPACE]:
            self.lose(start=False)
            self.d.find_element('id', 'view2D').send_keys(key)
            self.assertEqual(self.mode(), 'title')
            self.assertEqual(self.d.execute_script('return window.__ORRERY__.renderer().kind'), 'canvas2d')
            self.d.find_element('id', 'riteButton').send_keys(Keys.ENTER)
            self.assertEqual(self.mode(), 'playing')


if __name__ == '__main__':
    unittest.main(verbosity=2)
