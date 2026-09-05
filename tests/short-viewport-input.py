"""Click actual rendered mesh centers in exact, sub-320px-high iframes."""
import math
import tempfile
import time
import unittest
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
HOOK = '''window.__ORRERY__ = Object.freeze(debugApi);
window.__INPUT_QA__ = {game, draw, touchMove, touchCast,
  setReduced: value => {reducedMotion=value;}};
const normalHUD=drawHUD, normalEnemies=drawEnemies;
const capture=()=>{const m=ctx.getTransform();return {x:m.e/DPR,y:m.f/DPR};};
drawHUD=()=>{window.__INPUT_QA__.hud=capture();normalHUD();};
drawEnemies=()=>{window.__INPUT_QA__.world=capture();normalEnemies();};
const normalText=ctx.fillText;
ctx.fillText=function(text,x,y) {
  if(text==='FUEL') {
    const pos=new DOMPoint(x,y).matrixTransform(ctx.getTransform());
    const rect=canvas.getBoundingClientRect();
    window.__INPUT_QA__.label={x:rect.left+pos.x*rect.width/canvas.width,
      y:rect.top+pos.y*rect.height/canvas.height};
  }
  return normalText.apply(this,arguments);
};'''
# Measure a real scene object's world matrix with the camera actually rendered.
# Do not derive the click from the production project/unproject helpers.
MESH_HOOK = '''renderer.render(scene, camera);
const rect = canvas.getBoundingClientRect();
const meshNDC = player.getWorldPosition(new T.Vector3()).project(camera);
const labelWorld = player.getWorldPosition(new T.Vector3());
labelWorld.y += 45;
const labelNDC = labelWorld.project(camera);
window.__MESH_QA__ = {
  x: rect.left + (meshNDC.x + 1) * rect.width / 2,
  y: rect.top + (1 - meshNDC.y) * rect.height / 2,
  width: rect.width, height: rect.height, shake,
  label: {x:rect.left+(labelNDC.x+1)*rect.width/2,
    y:rect.top+(1-labelNDC.y)*rect.height/2-3}
};'''


def distance(a, b):
    return math.hypot(a['x'] - b['x'], a['y'] - b['y'])


class ShortViewportInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.file = Path(cls.tmp.name) / 'index.html'
        html = (ROOT / 'index.html').read_text()
        for old, new in [('window.__ORRERY__ = Object.freeze(debugApi);', HOOK),
                         ('renderer.render(scene, camera);', MESH_HOOK)]:
            assert html.count(old) == 1
            html = html.replace(old, new)
        html = html.replace('requestAnimationFrame(frame);', '/* deterministic QA draws */')
        cls.file.write_text(html)
        options = Options()
        options.add_argument('-headless')
        options.set_preference('webgl.force-enabled', True)
        cls.d = webdriver.Firefox(options=options)
        cls.d.set_window_size(1100, 900)

    @classmethod
    def tearDownClass(cls):
        cls.d.quit()
        cls.tmp.cleanup()

    def load(self, width, height, view):
        d = self.d
        d.switch_to.default_content()
        wrapper = Path(self.tmp.name) / 'frame.html'
        wrapper.write_text(f'<body style="margin:0"><iframe style="border:0" width="{width}" height="{height}" src="{self.file.as_uri()}?debug=1"></iframe>')
        d.get(wrapper.as_uri())
        d.switch_to.frame(d.find_element('tag name', 'iframe'))
        WebDriverWait(d, 10).until(lambda d: d.execute_script('return !!window.__INPUT_QA__'))
        self.assertEqual(d.execute_script('return [innerWidth,innerHeight]'), [width, height])
        d.find_element('id', 'view' + view).click()
        d.execute_script('''window.__ORRERY__.start(); const q=window.__INPUT_QA__;
          q.game.player.x=innerWidth/2;q.game.player.y=160;q.game.player.fuelTime=1;
          q.setReduced(false);q.game.shake=0;q.draw(0);''')
        time.sleep(.25)  # Let only the DOM overlay's fade finish.

    def test_mesh_click_roundtrip_and_shake(self):
        for width, height in [(800, 264), (320, 234)]:
            for view in ['3D', '2D']:
                with self.subTest(view=view, viewport=(width, height)):
                    self.load(width, height, view)
                    expected = {'x': width / 2, 'y': 160}
                    rest = None
                    for shake in [0, 18]:
                        point = self.d.execute_script('''const q=window.__INPUT_QA__;
                          q.game.shake=arguments[0];q.draw(0);
                          return arguments[1] ? {...window.__MESH_QA__,hud:q.hud}
                            : {x:q.game.player.x+q.world.x,y:q.game.player.y+q.world.y,hud:q.hud};''', shake, view == '3D')
                        self.assertEqual(point['hud'], {'x': 0, 'y': 0})
                        if view == '3D':
                            label = self.d.execute_script('return window.__INPUT_QA__.label')
                            self.assertLess(distance(label, point['label']), .001, (label, point))
                        if rest is None:
                            rest = point
                        else:
                            self.assertGreater(distance(point, rest), .1)
                            self.assertLessEqual(distance(point, rest), 3.001)
                            if view == '3D':
                                self.assertAlmostEqual(point['x']-rest['x'], point['shake']['x'], places=6)
                                self.assertAlmostEqual(point['y']-rest['y'], point['shake']['y'], places=6)
                        # Real WebDriver pointer down/up on the mesh, not a helper roundtrip.
                        actions = ActionBuilder(self.d)
                        actions.pointer_action.move_to_location(round(point['x']), round(point['y']))
                        actions.pointer_action.click()
                        actions.perform()
                        aim = self.d.execute_script('return window.__ORRERY__.snapshot().aim')
                        self.assertLess(distance(aim, expected), 1.5, (point, aim, expected))
                        # Fractional CSS event coordinates additionally catch subpixel errors.
                        aim = self.d.execute_script('''const p=arguments[0];
                          document.getElementById('game').dispatchEvent(new PointerEvent('pointermove',
                            {clientX:p.x,clientY:p.y,pointerType:'mouse',bubbles:true}));
                          return window.__ORRERY__.snapshot().aim;''', point)
                        self.assertLess(distance(aim, expected), .001, (point, aim, expected))
                        if view == '3D':
                            projected = self.d.execute_script('return window.__ORRERY__.project3D(arguments[0],160)', width / 2)
                            self.assertLess(distance(projected, point), .001)

    def test_touch_deltas_and_zones_stay_css_pixels(self):
        for width, height in [(800, 264), (320, 234)]:
            for view in ['3D', '2D']:
                with self.subTest(view=view, viewport=(width, height)):
                    self.load(width, height, view)
                    result = self.d.execute_script('''const c=document.getElementById('game'),q=window.__INPUT_QA__;
                      const touch=(type,id,x,y)=>c.dispatchEvent(new PointerEvent(type,
                        {pointerId:id,pointerType:'touch',clientX:x,clientY:y,bubbles:true}));
                      touch('pointerdown',41,50,100);touch('pointermove',41,77,118);
                      touch('pointerdown',42,innerWidth*.8,100);q.draw(0);
                      const result={dx:q.touchMove.x-q.touchMove.ox,dy:q.touchMove.y-q.touchMove.oy,
                        move:q.touchMove.id,cast:q.touchCast.id,hud:q.hud};
                      touch('pointercancel',41,77,118);touch('pointercancel',42,innerWidth*.8,100);
                      return result;''')
                    self.assertEqual(result, {'dx': 27, 'dy': 18, 'move': 41, 'cast': 42, 'hud': {'x': 0, 'y': 0}})


if __name__ == '__main__':
    unittest.main(verbosity=2)
