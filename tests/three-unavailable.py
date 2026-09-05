"""Without WebGL, explain the fallback and keep the 2D game playable."""
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1]
options=Options();options.add_argument('-headless');options.set_preference('webgl.disabled',True)
with webdriver.Firefox(options=options) as driver:
    driver.get((ROOT/'index.html').as_uri())
    WebDriverWait(driver,5).until(lambda d:d.execute_script('return document.readyState==="complete"'))
    assert driver.execute_script('return !!window.__ORRERY__'), 'WebGL failure must not prevent 2D startup'
    assert driver.find_element('id','graphicsError').is_displayed()
    assert 'WebGL' in driver.find_element('id','graphicsError').text
    assert driver.execute_script('return window.__ORRERY__.renderer().kind')=='canvas2d'
    assert not driver.find_element('id','view3D').is_enabled()
    assert driver.find_element('id','riteButton').is_enabled()
    driver.find_element('id','riteButton').click()
    WebDriverWait(driver,5).until(lambda d:d.execute_script('return window.__ORRERY__.snapshot().time > .1'))
    assert driver.execute_script('return window.__ORRERY__.snapshot().mode')=='playing'
    print('PASS: WebGL unavailable explains fallback and permits a real 2D run.')
