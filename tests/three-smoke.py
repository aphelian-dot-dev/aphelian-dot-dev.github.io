"""Real-renderer contract: standalone 3D scene, same live game."""
import json
import tempfile
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
options = Options()
options.add_argument('-headless')
options.set_preference('webgl.force-enabled', True)
with tempfile.TemporaryDirectory() as directory, webdriver.Firefox(options=options) as driver:
    standalone = Path(directory) / 'index.html'
    standalone.write_bytes((ROOT / 'index.html').read_bytes())
    driver.set_window_size(1280, 900)
    driver.get(standalone.as_uri() + '?debug=1')
    WebDriverWait(driver, 15).until(lambda d: d.execute_script('return !!window.__ORRERY__'))
    info = driver.execute_script('return window.__ORRERY__.renderer?.() || null')
    assert info and info['kind'] == 'webgl3d', f'Expected genuine WebGL 3D renderer, got {info}'
    assert info['triangles'] > 100, info
    driver.find_element('id', 'riteButton').click()
    time.sleep(1)
    state = driver.execute_script('return window.__ORRERY__.snapshot()')
    assert state['mode'] == 'playing' and state['time'] > 0, state
    for point in [[0, 0], [640, 407], [1280, 814], [100, 700]]:
        result = driver.execute_script('return window.__ORRERY__.unproject3D(window.__ORRERY__.project3D(...arguments[0]))', point)
        assert abs(result['x'] - point[0]) < .001 and abs(result['y'] - point[1]) < .001, (point, result)
    driver.execute_script('''const s = window.__ORRERY__.project3D(900, 200);
        document.getElementById('game').dispatchEvent(new PointerEvent('pointermove', {clientX:s.x, clientY:s.y, pointerType:'mouse'}));''')
    aim = driver.execute_script('return window.__ORRERY__.snapshot().aim || null')
    assert aim and abs(aim['x'] - 900) < .01 and abs(aim['y'] - 200) < .01, aim
    driver.execute_script('window.__ORRERY__.spawnMeteor(); window.__ORRERY__.forceBoss()')
    time.sleep(.15)
    info = driver.execute_script('return window.__ORRERY__.renderer()')
    assert info['entities'].get('meteor') == 1 and info['entities'].get('boss') == 1, info
    assert info['arena'] and info['moons'] == 3, info
    context_script = 'document.getElementById("stage3D").getContext("webgl2").getExtension("WEBGL_lose_context")'
    driver.execute_script('window.lossExtension = ' + context_script + '; window.lossExtension.loseContext()')
    time.sleep(.3)
    assert driver.execute_script('return window.__ORRERY__.snapshot().mode') == 'paused', 'Context loss must pause combat'
    assert not driver.find_element('id', 'riteButton').is_enabled()
    driver.execute_script('window.lossExtension.restoreContext()')
    WebDriverWait(driver, 5).until(lambda d: d.find_element('id', 'riteButton').is_enabled())
    print(json.dumps({'renderer': info, 'game': state, 'contextRecovery': True}, indent=2))
