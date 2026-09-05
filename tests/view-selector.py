"""Home selector switches actual renderers while preserving native controls."""
import tempfile,time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1]
options=Options();options.add_argument('-headless');options.set_preference('webgl.force-enabled',True)
with tempfile.TemporaryDirectory() as folder, webdriver.Firefox(options=options) as d:
    file=Path(folder)/'index.html';file.write_bytes((ROOT/'index.html').read_bytes())
    d.set_window_size(1440,1000);d.get(file.as_uri()+'?debug=1')
    WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__ORRERY__'))
    assert d.execute_script('return !!document.getElementById("view2D") && !!document.getElementById("view3D")'), 'Home view selector is missing'
    assert d.find_element('id','view3D').get_attribute('aria-pressed')=='true'
    d.find_element('id','view2D').click()
    assert d.execute_script('return window.__ORRERY__.renderer().kind')=='canvas2d'
    assert not d.find_element('id','stage3D').is_displayed()
    assert d.find_element('id','view2D').get_attribute('aria-pressed')=='true'
    # Return/Space on selector buttons must not start the rite.
    d.find_element('id','view3D').send_keys(Keys.ENTER)
    assert d.execute_script('return window.__ORRERY__.snapshot().mode')=='title'
    assert d.execute_script('return window.__ORRERY__.renderer().kind')=='webgl3d'
    d.find_element('id','view2D').send_keys(Keys.SPACE)
    assert d.execute_script('return window.__ORRERY__.renderer().kind')=='canvas2d'
    d.find_element('id','riteButton').click();time.sleep(.3)
    assert d.execute_script('return window.__ORRERY__.snapshot().mode')=='playing'
    assert not d.find_element('id','view2D').is_displayed()
    d.execute_script('''document.getElementById('game').dispatchEvent(new PointerEvent('pointermove',{pointerType:'mouse',clientX:300,clientY:250}));''')
    assert d.execute_script('return window.__ORRERY__.snapshot().aim')=={'x':300,'y':250}
    d.execute_script('window.__ORRERY__.finish(false)');time.sleep(.25);d.find_element('id','homeButton').click()
    assert d.find_element('id','view2D').get_attribute('aria-pressed')=='true'
    d.find_element('id','view3D').click();d.find_element('id','riteButton').click();time.sleep(.3)
    assert d.execute_script('return window.__ORRERY__.renderer().kind')=='webgl3d'
    d.execute_script('''const p=window.__ORRERY__.project3D(300,250);document.getElementById('game').dispatchEvent(new PointerEvent('pointermove',{pointerType:'mouse',clientX:p.x,clientY:p.y}));''')
    aim=d.execute_script('return window.__ORRERY__.snapshot().aim')
    assert abs(aim['x']-300)<.01 and abs(aim['y']-250)<.01,aim
    assert d.execute_script('return document.querySelectorAll("#stage3D").length')==1
    # A hidden WebGL canvas failing must not interrupt the selected 2D renderer.
    d.execute_script('window.__ORRERY__.finish(false)');time.sleep(.25);d.find_element('id','homeButton').click()
    d.find_element('id','view2D').click();d.find_element('id','riteButton').click()
    d.execute_script('window.lostContext=document.getElementById("stage3D").getContext("webgl2").getExtension("WEBGL_lose_context");lostContext.loseContext()')
    time.sleep(.15)
    assert d.execute_script('return window.__ORRERY__.snapshot().mode')=='playing'
    d.execute_script('lostContext.restoreContext()')
    WebDriverWait(d,5).until(lambda d:d.find_element('id','view3D').is_enabled())
    # Losing 3D on the title must allow choosing 2D without stale warnings.
    d.execute_script('window.__ORRERY__.finish(false)');time.sleep(.25);d.find_element('id','homeButton').click()
    d.find_element('id','view3D').click()
    d.execute_script('lostContext.loseContext()');time.sleep(.15)
    d.find_element('id','view2D').send_keys(Keys.ENTER)
    assert d.find_element('id','riteButton').is_enabled()
    assert 'interrupted' not in d.find_element('id','subtitle').text.lower()
    print('PASS: standalone 2D / 3D selection, native keyboard activation, both game starts, renderer-specific aim, home retention and context-loss isolation.')
