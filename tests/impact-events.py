"""Shake belongs to real weapon contacts, not launch, reversal, damage or boss cues."""
import json,tempfile
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1]
hook='window.__ORRERY__ = Object.freeze(debugApi); window.__EVENT_QA__ = {game,beginFold,endFold,retrograde,hurtPlayer,spawnBoss,updateBoss,spawnEnemy,resolveCombat};'
html=(ROOT/'index.html').read_text().replace('window.__ORRERY__ = Object.freeze(debugApi);',hook)
options=Options();options.add_argument('-headless');options.set_preference('webgl.force-enabled',True)
with tempfile.TemporaryDirectory() as folder,webdriver.Firefox(options=options) as d:
    file=Path(folder)/'index.html';file.write_text(html)
    for view in ['2D','3D']:
        d.get(file.as_uri());WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__EVENT_QA__'))
        d.find_element('id','view'+view).click();d.find_element('id','riteButton').click()
        result=d.execute_script('''const q=window.__EVENT_QA__,g=q.game,p=g.player,observed={};
          g.enemies=[];g.shake=0;q.beginFold('qa');p.charge=.8;q.endFold('qa');
          observed.release=g.shake;observed.attackActive=p.burst>0;
          g.shake=0;q.retrograde();observed.emptyRetrograde=g.shake;
          g.shake=0;p.invuln=0;q.hurtPlayer(1,p.x+10,p.y);observed.damage=g.shake;
          g.shake=0;q.spawnBoss();observed.bossArrival=g.shake;
          const boss=g.boss;boss.state='telegraph';boss.stateTimer=0;
          g.shake=0;q.updateBoss(boss,1/60);observed.bossDash=g.shake;
          g.enemies=[];g.shake=0;g.victoryPending=0;
          const orb=p.orbs[0],enemy=q.spawnEnemy('ram',orb.x,orb.y);enemy.hp=enemy.maxHp=100;
          q.resolveCombat(1/60);observed.impact=g.shake;observed.hit=enemy.hp<100;
          return observed;''')
        assert result['attackActive'],(view,result)
        for event in ['release','emptyRetrograde','damage','bossArrival','bossDash']:assert result[event]==0,(view,event,result)
        assert result['impact']>0 and result['hit'],(view,result)
        print(view,json.dumps(result))
print('PASS: only actual attack impacts trigger shake in both views.')
