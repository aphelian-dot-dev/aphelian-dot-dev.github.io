"""Exercise real input, 3D effects, layouts and result flows; retain screenshots."""
import json
import time
from pathlib import Path
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'verification'
OUT.mkdir(exist_ok=True)
options = Options()
options.add_argument('-headless')
options.set_preference('webgl.force-enabled', True)
report = []
with webdriver.Firefox(options=options) as driver:
    driver.set_window_size(1440, 1000)
    def ready():
        WebDriverWait(driver, 15).until(lambda d: d.execute_script('return !!window.__ORRERY__ && window.__ORRERY__.renderer().triangles > 0'))
    def state():
        return driver.execute_script('return window.__ORRERY__.snapshot()')
    def shot(name, frame=None):
        metrics = driver.execute_script('return {width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth,renderer:window.__ORRERY__.renderer()}')
        assert not metrics['overflow'], metrics
        report.append({'name':name, **metrics})
        if frame:
            driver.switch_to.default_content()
            frame.screenshot(str(OUT / (name + '.png')))
            driver.switch_to.frame(frame)
        else:
            driver.save_screenshot(str(OUT / (name + '.png')))
    driver.get((ROOT / 'index.html').as_uri() + '?debug=1')
    ready(); time.sleep(.4); shot('desktop-title')
    driver.find_element('id', 'riteButton').click()
    time.sleep(.5)
    before = state()['position']
    ActionChains(driver).key_down('d').pause(.5).key_up('d').perform()
    assert state()['position']['x'] > before['x'] + 15
    ActionChains(driver).key_down(Keys.SPACE).pause(.9).perform()
    charged = state(); assert charged['orbit']['folding'] and charged['orbit']['charge'] >= .36, charged
    shot('desktop-charge')
    ActionChains(driver).key_up(Keys.SPACE).perform()
    assert state()['orbit']['burst'] > 0
    direction = state()['orbit']['direction']
    ActionChains(driver).key_down(Keys.SHIFT).pause(.1).key_up(Keys.SHIFT).perform()
    assert state()['orbit']['direction'] == -direction
    driver.execute_script('window.__ORRERY__.spawnMeteor()')
    time.sleep(.2)
    for expected in [2, 1, 0]:
        driver.execute_script('window.__ORRERY__.strikeMeteor()')
        time.sleep(.2)
        snap = state()
        if expected:
            assert snap['meteors'][0]['hitsRemaining'] == expected, snap
        else:
            assert snap['orbit']['meteorBoost'] > 4, snap
    driver.execute_script('window.__ORRERY__.forceBoss()')
    time.sleep(2.8); shot('desktop-boss')
    ActionChains(driver).send_keys('p').perform(); time.sleep(.25)
    assert state()['mode'] == 'paused'
    stopped = state()['time']; time.sleep(.25); assert state()['time'] == stopped
    driver.find_element('id', 'riteButton').click(); time.sleep(.2)
    driver.execute_script('window.__ORRERY__.defeatBoss()')
    WebDriverWait(driver, 5).until(lambda d: state()['mode'] == 'won')
    time.sleep(.25); shot('desktop-result')
    driver.find_element('id', 'homeButton').click(); assert state()['mode'] == 'title'
    for width, height in [(390, 844), (844, 390)]:
        markup = f'<style>body{{margin:0}}iframe{{border:0}}</style><iframe width="{width}" height="{height}" src="{(ROOT / "index.html").as_uri()}?debug=1"></iframe>'
        # Firefox permits a local wrapper to frame the self-contained local game.
        wrapper = OUT / 'viewport.html'; wrapper.write_text(markup)
        driver.get(wrapper.as_uri()); frame = driver.find_element('tag name', 'iframe'); driver.switch_to.frame(frame); ready()
        shot(f'{width}-title', frame)
        driver.execute_script('window.__ORRERY__.start()'); time.sleep(.4)
        # Pointer events mimic independent left-move and right-charge touches.
        driver.execute_script('''const c=document.getElementById('game');
            const event=(type,id,x,y)=>c.dispatchEvent(new PointerEvent(type,{pointerId:id,pointerType:'touch',clientX:x,clientY:y,bubbles:true}));
            event('pointerdown',31,50,220);event('pointermove',31,100,220);
            event('pointerdown',32,innerWidth-60,200);''')
        time.sleep(.7)
        assert state()['runStats']['moved'] and state()['orbit']['folding'], state()
        shot(f'{width}-playing', frame)
        driver.execute_script('window.__ORRERY__.extinguish()'); time.sleep(.3)
        assert state()['mode'] == 'lost'
        driver.find_element('id', 'homeButton').location_once_scrolled_into_view
        shot(f'{width}-result', frame)
        driver.switch_to.default_content()
    (OUT / 'visual-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
