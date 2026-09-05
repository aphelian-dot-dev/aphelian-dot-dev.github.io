"""Capture and measure the actual overheated HUD in exact desktop/mobile iframe viewports."""
import json,tempfile
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
html=(ROOT/'index.html').read_text().replace('window.__ORRERY__ = Object.freeze(debugApi);','window.__ORRERY__ = Object.freeze(debugApi);window.__HEAT_QA__={game,calculateOrbs,draw,ctx};window.requestAnimationFrame=()=>0;')
options=Options();options.add_argument('-headless');options.set_preference('webgl.force-enabled',True)
results=[]
with tempfile.TemporaryDirectory() as folder,webdriver.Firefox(options=options) as d:
    path=Path(folder);(path/'game.html').write_text(html);d.set_window_size(1600,1100)
    for w,h in [(1440,900),(390,844),(844,390),(320,234)]:
        (path/'frame.html').write_text(f'<html><body style="margin:0"><iframe id="frame" style="border:0;width:{w}px;height:{h}px" src="game.html"></iframe></body></html>')
        for view in ['2D','3D']:
            d.get((path/'frame.html').as_uri());frame=d.find_element('id','frame');d.switch_to.frame(frame)
            WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__HEAT_QA__'))
            d.find_element('id','view'+view).click();d.find_element('id','riteButton').click()
            WebDriverWait(d,5).until(lambda d:d.execute_script("return getComputedStyle(document.getElementById('overlay')).opacity==='0'"))
            r=d.execute_script('''const q=window.__HEAT_QA__,g=q.game,p=g.player,c=q.ctx,labels=[];
              p.overheated=true;p.burst=p.burstDuration=.58;p.burstCharge=1;p.radius=Math.min(innerWidth,innerHeight)*.2;
              g.chapter=null;g.enemies=[];g.waves=[];g.particles=[];g.flash=g.shake=0;q.calculateOrbs(p);g.mode='playing';
              const fill=c.fillText;c.fillText=function(t,x,y,...args){if(t.includes('OVERHEATED')){const m=c.measureText(t),matrix=c.getTransform(),rect=c.canvas.getBoundingClientRect();const project=(x,y)=>({x:rect.left+(matrix.a*x+matrix.c*y+matrix.e)*rect.width/c.canvas.width,y:rect.top+(matrix.b*x+matrix.d*y+matrix.f)*rect.height/c.canvas.height});const a=project(x-m.actualBoundingBoxLeft,y-m.actualBoundingBoxAscent),b=project(x+m.actualBoundingBoxRight,y+m.actualBoundingBoxDescent);labels.push({text:t,left:a.x,right:b.x,top:a.y,bottom:b.y});}return fill.call(this,t,x,y,...args)};
              try{q.draw(0)}finally{c.fillText=fill}
              const b=document.getElementById('soundButton').getBoundingClientRect();
              return {w:innerWidth,h:innerHeight,labels,overflow:document.documentElement.scrollWidth>innerWidth,sound:{left:b.left,right:b.right,top:b.top,bottom:b.bottom}};''')
            assert (r['w'],r['h'])==(w,h) and not r['overflow'],r
            assert len(r['labels'])==1,r
            b=r['labels'][0];s=r['sound'];assert b['left']>=0 and b['right']<=w and b['top']>=0 and b['bottom']<=h,r
            assert not(b['left']<s['right'] and b['right']>s['left'] and b['top']<s['bottom'] and b['bottom']>s['top']),r
            d.switch_to.default_content();assert frame.screenshot(str(OUT/f'overheated-{w}-{view}.png'));results.append(dict(view=view,**r))
(OUT/'overheat-layout.json').write_text(json.dumps(results,indent=2));print(f'PASS: overheat HUD fits in {len(results)} exact viewport/view combinations.')
