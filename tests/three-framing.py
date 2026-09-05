"""Regression for camera depth and the clipped narrow chapter announcement."""
import tempfile
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT = Path(__file__).resolve().parents[1]
options = Options(); options.add_argument('-headless'); options.set_preference('webgl.force-enabled', True)
with tempfile.TemporaryDirectory() as tmp, webdriver.Firefox(options=options) as driver:
    wrapper = Path(tmp) / 'frame.html'
    wrapper.write_text(f'<iframe width="390" height="844" src="{(ROOT / "index.html").as_uri()}?debug=1"></iframe>')
    driver.get(wrapper.as_uri()); driver.switch_to.frame(driver.find_element('tag name', 'iframe'))
    WebDriverWait(driver, 10).until(lambda d: d.execute_script('return !!window.__ORRERY__'))
    driver.execute_script('''window.chapterBounds=[];const original=CanvasRenderingContext2D.prototype.fillText;
      CanvasRenderingContext2D.prototype.fillText=function(text,x,y,maxWidth){
        if(text==='CONTACT DAMAGES VOIDCRAFT') {
          const w=Math.min(this.measureText(text).width,maxWidth||Infinity);
          chapterBounds.push({left:x-w/2,right:x+w/2,font:this.font});
        }
        return original.apply(this,arguments);
      };window.__ORRERY__.start();''')
    time.sleep(.3)
    bounds=driver.execute_script('return chapterBounds')
    assert bounds and all(b['left']>=16 and b['right']<=374 for b in bounds), bounds
    camera=driver.execute_script('return window.__ORRERY__.renderer().camera')
    assert camera=='PerspectiveCamera', camera
    print('PASS: narrow chapter fits actual draw bounds; perspective camera active.')
