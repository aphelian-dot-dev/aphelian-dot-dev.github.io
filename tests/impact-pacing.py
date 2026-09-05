"""Controlled real-browser impact stress: report clock pacing, not a GPU benchmark."""
import json,tempfile
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
html=(ROOT/'index.html').read_text().replace('window.__ORRERY__ = Object.freeze(debugApi);','window.__ORRERY__ = Object.freeze(debugApi); window.__PACETEST__ = {game, hitEnemy, spawnEnemy, keys};')
options=Options();options.add_argument('-headless');options.set_preference('webgl.force-enabled',True)
results=[]
with tempfile.TemporaryDirectory() as folder,webdriver.Firefox(options=options) as d:
    file=Path(folder)/'index.html';file.write_text(html);d.set_window_size(1280,900)
    for view in ['2D','3D']:
        for impacts in [False,True]:
            d.get(file.as_uri());WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__PACETEST__'))
            d.find_element('id','view'+view).click();d.find_element('id','riteButton').click()
            result=d.execute_async_script('''const done=arguments[arguments.length-1], impacts=arguments[0];
              const {game,hitEnemy,spawnEnemy,keys}=window.__PACETEST__;
              const enemy=spawnEnemy('ram',game.player.x+130,game.player.y);
              enemy.hp=enemy.maxHp=10000; enemy.speed=0; enemy.damage=0;
              game.player.invuln=99; keys.add('KeyD');
              const started=performance.now(),startTime=game.time,startX=game.player.x; let hits=0;
              const interval=impacts?setInterval(()=>{hitEnemy(enemy,.01,enemy.x,enemy.y,'aphelion');hits++;},50):null;
              setTimeout(()=>{clearInterval(interval);keys.clear();
                done({wall:(performance.now()-started)/1000,sim:game.time-startTime,moved:game.player.x-startX,hits,fps:game.fps,kind:window.__ORRERY__.renderer().kind});
              },2000);''',impacts)
            result.update(view=view,impacts=impacts);results.append(result)
            assert result['moved']>100,result
            assert result['sim']/result['wall']>.90,result
            if impacts:assert result['hits']>=30,result
            if impacts:d.save_screenshot(str(OUT/f'impact-{view}.png'))
    (OUT/'impact-pacing.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
