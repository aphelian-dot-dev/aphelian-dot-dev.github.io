"""Exercise actual field transforms, HUD stability and aiming during impact shake."""
import json,tempfile
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1]
hook='''window.__ORRERY__ = Object.freeze(debugApi);
window.__SHAKE_QA__ = {game, draw, setReduced: value => {reducedMotion=value;}};
const normalHUD=drawHUD, normalEnemies=drawEnemies;
const capture=()=>{const m=ctx.getTransform();return {x:m.e/DPR,y:m.f/DPR};};
drawHUD=()=>{window.__SHAKE_QA__.hud=capture();normalHUD();};
drawEnemies=()=>{window.__SHAKE_QA__.world=capture();normalEnemies();};'''
html=(ROOT/'index.html').read_text().replace('window.__ORRERY__ = Object.freeze(debugApi);',hook)
options=Options();options.add_argument('-headless');options.set_preference('webgl.force-enabled',True)
results=[]
with tempfile.TemporaryDirectory() as folder,webdriver.Firefox(options=options) as d:
    file=Path(folder)/'index.html';file.write_text(html);d.set_window_size(1280,900)
    for view in ['2D','3D']:
        d.get(file.as_uri());WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__SHAKE_QA__'))
        d.find_element('id','view'+view).click();d.find_element('id','riteButton').click()
        result=d.execute_script('''const q=window.__SHAKE_QA__, api=window.__ORRERY__, is3D=arguments[0];
          const point=()=>is3D?api.project3D(300,250):{...q.world};
          q.setReduced(false);q.game.shake=0;q.draw(0);const rest=point(),restHUD={...q.hud};
          q.game.shake=18;q.draw(0);const hit=point(),hitHUD={...q.hud};
          const screen=is3D?hit:{x:300+hit.x,y:250+hit.y};
          document.getElementById('game').dispatchEvent(new PointerEvent('pointermove',{clientX:screen.x,clientY:screen.y,bubbles:true}));
          const aim=api.snapshot().aim;
          q.setReduced(true);q.game.shake=18;q.draw(0);const reduced=point();
          q.setReduced(false);q.game.mode='paused';q.draw(0);const paused=point();
          q.game.mode='playing';q.game.shake=.01;q.draw(0);const settled=point();
          return {rest,hit,restHUD,hitHUD,aim,reduced,paused,settled};''',view=='3D')
        distance=lambda a,b:((a['x']-b['x'])**2+(a['y']-b['y'])**2)**.5
        assert .1<distance(result['rest'],result['hit'])<=3.001,(view,result)
        assert result['restHUD']==result['hitHUD']=={'x':0,'y':0},(view,result)
        assert distance(result['aim'],{'x':300,'y':250})<.001,(view,result)
        for state in ['reduced','paused','settled']:assert distance(result['rest'],result[state])<.001,(view,state,result)
        result['view']=view;results.append(result)
    print(json.dumps(results,indent=2))
    print('PASS: subtle field shake in both renderers, stable HUD, accurate aim, reduced-motion suppression and no lingering pause/home drift.')
