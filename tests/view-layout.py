"""Measure home selector placement with consent on desktop and cramped screens."""
import importlib.util,json,time
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('upstream_browser',ROOT/'tests/browser-regressions.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
C=m.ResultScreenBrowserTests;C.setUpClass();d=C.driver
d.set_window_size(1600,1100)  # Fit every iframe in the screenshot's host viewport.
results=[];failures=[]
try:
    for width,height in [(1440,900),(390,844),(844,390),(320,234)]:
        d.get(C.base_url+f'/__score_notice_frame__?width={width}&height={height}')
        frame=d.find_element('id','gameFrame');d.switch_to.frame(frame)
        WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__ORRERY__'))
        for view in ['2D','3D']:
            d.find_element('id','view'+view).click();time.sleep(.15)
            result=d.execute_script('''const sels=['.title-block','#viewSelector','#view2D','#view3D','.controls','#scoreArchive','#riteButton','#soundButton'];
              const boxes=Object.fromEntries(sels.map(s=>{const e=document.querySelector(s),r=e.getBoundingClientRect();return [s,{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height,display:getComputedStyle(e).display}]}));
              return {width:innerWidth,height:innerHeight,boxes,overflow:document.documentElement.scrollWidth>innerWidth};''')
            result['view']=view;results.append(result)
            buttons=[result['boxes'][s] for s in ['#view2D','#view3D','#riteButton']]
            sound=result['boxes']['#soundButton']
            for b in buttons:
                if b['x']<0 or b['y']<0 or b['right']>width+1 or b['bottom']>height+1:failures.append(result)
                if sound['display']!='none' and b['x']<sound['right'] and b['right']>sound['x'] and b['y']<sound['bottom'] and b['bottom']>sound['y']:failures.append(result)
            d.switch_to.default_content();frame.screenshot(str(OUT/f'home-{width}-{view}.png'));d.switch_to.frame(frame)
        d.switch_to.default_content()
    (OUT/'view-layout.json').write_text(json.dumps(results,indent=2))
    assert not failures,json.dumps(failures,indent=2)
    print('PASS: both view choices and Begin fit without sound-button overlap at all four measured sizes.')
finally:C.tearDownClass()
