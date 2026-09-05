"""Mobile controls in Chromium: real CDP touch, not iOS system-UI emulation.
Run: uv run --with playwright python tests/mobile-controls.py
"""
import json
import tempfile
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class MobileControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.file = Path(cls.tmp.name) / 'index.html'
        html = (ROOT / 'index.html').read_text()
        hook = 'window.__ORRERY__ = Object.freeze(debugApi);'
        assert html.count(hook) == 1
        cls.file.write_text(html.replace(hook, hook + '\nwindow.__MOBILE_QA__={game,touchMove,touchCast,draw,ctx};'))
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.tmp.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, device_scale_factor=1)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.cdp = self.context.new_cdp_session(self.page)

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def load(self, view):
        self.page.goto(self.file.as_uri() + '?debug=1')
        self.page.wait_for_function('!!window.__MOBILE_QA__')
        self.page.locator('#view' + view).click()
        self.page.locator('#riteButton').tap()
        self.page.wait_for_function("getComputedStyle(document.getElementById('overlay')).opacity==='0'")
        self.page.evaluate('window.__MOBILE_QA__.game.player.invuln=1000')

    def touches(self, kind, points):
        self.cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [dict(id=i, x=x, y=y) for i, x, y in points]})

    def test_touch_pause_cancels_held_inputs_and_resume_is_explicit(self):
        for view in ['2D', '3D']:
            with self.subTest(view=view):
                self.load(view)
                button = self.page.get_by_role('button', name='Pause game', exact=True)
                self.assertEqual(button.count(), 1, 'A native on-screen Pause button is required')
                r = button.bounding_box()
                self.assertGreaterEqual(r['width'], 44)
                self.assertGreaterEqual(r['height'], 44)
                self.touches('touchStart', [(1, 65, 430)])
                self.touches('touchStart', [(1, 65, 430), (2, 280, 370)])
                self.page.wait_for_function('window.__MOBILE_QA__.game.player.folding')
                # Pause with a third finger while movement and charge remain held.
                self.touches('touchStart', [(1, 65, 430), (2, 280, 370), (3, r['x'] + r['width']/2, r['y'] + r['height']/2)])
                self.page.wait_for_function("window.__MOBILE_QA__.game.mode==='paused'")
                self.touches('touchEnd', [])
                state = self.page.evaluate('''() => {const q=window.__MOBILE_QA__;return {time:q.game.time,fold:q.game.player.folding,burst:q.game.player.burst,move:q.touchMove.id,cast:q.touchCast.id,active:document.activeElement.id}}''')
                self.assertFalse(state['fold'])
                self.assertEqual(state['burst'], 0)
                self.assertIsNone(state['move'])
                self.assertIsNone(state['cast'])
                self.assertEqual(state['active'], 'riteButton')
                self.page.wait_for_timeout(300)
                self.assertEqual(self.page.evaluate('window.__MOBILE_QA__.game.time'), state['time'])
                self.assertFalse(button.is_visible())
                self.page.locator('#riteButton').tap()
                self.page.wait_for_function("window.__MOBILE_QA__.game.mode==='playing'")
                self.assertTrue(button.is_visible())
                self.assertFalse(self.page.evaluate('window.__MOBILE_QA__.game.player.folding'))

    def test_long_press_guards_are_scoped_and_touch_charge_still_works(self):
        html = (ROOT / 'index.html').read_text()
        self.assertIn('-webkit-touch-callout: none', html)
        for view in ['2D', '3D']:
            with self.subTest(view=view):
                self.load(view)
                state = self.page.evaluate('''() => {
                  const canvas=document.getElementById('game');
                  const start=new Event('touchstart',{bubbles:true,cancelable:true});canvas.dispatchEvent(start);
                  const select=new Event('selectstart',{bubbles:true,cancelable:true});canvas.dispatchEvent(select);
                  const native=new Event('touchstart',{bubbles:true,cancelable:true});document.getElementById('soundButton').dispatchEvent(native);
                  return {start:start.defaultPrevented,select:select.defaultPrevented,native:native.defaultPrevented,
                    styles:['game','stage3D'].map(id=>getComputedStyle(document.getElementById(id)).webkitUserSelect)};
                }''')
                self.assertEqual(state, {'start': True, 'select': True, 'native': False, 'styles': ['none', 'none']})
                self.touches('touchStart', [(1, 275, 350)])
                self.page.wait_for_function('window.__MOBILE_QA__.game.player.folding && window.__MOBILE_QA__.game.player.charge > .05')
                self.touches('touchMove', [(1, 290, 345)])
                self.touches('touchEnd', [])
                self.assertFalse(self.page.evaluate('window.__MOBILE_QA__.game.player.folding'))
                self.assertGreater(self.page.evaluate('window.__MOBILE_QA__.game.player.burst'), 0)
                self.assertEqual(self.page.evaluate('getSelection().toString()'), '')
                # A long, stationary hold still reaches the existing overheat endpoint.
                self.page.wait_for_timeout(650)
                self.touches('touchStart', [(2, 275, 350)])
                self.page.wait_for_function('window.__MOBILE_QA__.game.player.overheated', timeout=4000)
                self.touches('touchEnd', [])

    def test_pause_layout_does_not_cover_hud(self):
        out = ROOT / 'verification'
        out.mkdir(exist_ok=True)
        results = []
        for width, height in [(390, 844), (320, 234), (844, 390), (1440, 900)]:
            self.page.set_viewport_size({'width': width, 'height': height})
            for view in ['2D', '3D']:
                with self.subTest(width=width, height=height, view=view):
                    self.load(view)
                    result = self.page.evaluate('''() => {
                      const q=window.__MOBILE_QA__,c=q.ctx,g=q.game,labels=[];
                      g.chapter=null;g.enemies=[];g.floaters=[];g.shake=0;
                      g.player.overheated=true;g.player.burst=g.player.burstDuration=.58;
                      window.requestAnimationFrame=()=>0;
                      const fill=c.fillText;
                      c.fillText=function(text,x,y,...args) {
                        const m=c.measureText(text),matrix=c.getTransform(),rect=c.canvas.getBoundingClientRect();
                        const project=(x,y)=>({x:rect.left+(matrix.a*x+matrix.c*y+matrix.e)*rect.width/c.canvas.width,
                          y:rect.top+(matrix.b*x+matrix.d*y+matrix.f)*rect.height/c.canvas.height});
                        const a=project(x-m.actualBoundingBoxLeft,y-m.actualBoundingBoxAscent),b=project(x+m.actualBoundingBoxRight,y+m.actualBoundingBoxDescent);
                        labels.push({text,left:a.x,top:a.y,right:b.x,bottom:b.y});
                        return fill.call(this,text,x,y,...args);
                      };
                      try {q.draw(0)} finally {c.fillText=fill}
                      return {width:innerWidth,height:innerHeight,labels,
                        pause:document.getElementById('pauseButton').getBoundingClientRect().toJSON(),
                        sound:document.getElementById('soundButton').getBoundingClientRect().toJSON()};
                    }''')
                    self.assertEqual((result['width'], result['height']), (width, height))
                    pause = result['pause']
                    self.assertTrue(0 <= pause['left'] < pause['right'] <= width)
                    self.assertTrue(0 <= pause['top'] < pause['bottom'] <= height)
                    self.assertGreaterEqual(pause['height'], 44)
                    self.assertTrue(result['labels'])
                    for other in result['labels'] + [result['sound']]:
                        overlaps = pause['left'] < other['right'] and pause['right'] > other['left'] and pause['top'] < other['bottom'] and pause['bottom'] > other['top']
                        self.assertFalse(overlaps, (width, height, view, other))
                    self.page.screenshot(path=str(out / f'mobile-pause-{width}-{view}.png'))
                    results.append(dict(view=view, **result))
        (out / 'mobile-pause-layout.json').write_text(json.dumps(results, indent=2))

    def test_keyboard_pause_and_hidden_states(self):
        self.load('2D')
        for key in ['Enter', 'Space']:
            button = self.page.get_by_role('button', name='Pause game', exact=True)
            self.assertEqual(button.count(), 1)
            button.focus()
            button.press(key)
            self.page.wait_for_function("window.__MOBILE_QA__.game.mode==='paused'")
            self.page.locator('#riteButton').press(key)
            self.page.wait_for_function("window.__MOBILE_QA__.game.mode==='playing'")
        self.page.evaluate('window.__ORRERY__.finish(false)')
        self.assertFalse(self.page.locator('#pauseButton').is_visible())
        self.page.locator('#homeButton').click()
        self.assertFalse(self.page.locator('#pauseButton').is_visible())


if __name__ == '__main__':
    unittest.main(verbosity=2)
