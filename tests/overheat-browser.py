"""Exercise the real overheat simulation and both renderers, not just rule constants."""
import json,tempfile
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
hook='''window.__ORRERY__ = Object.freeze(debugApi);
window.__HEAT_QA__={game,createPlayer,resetGame,updatePlayer,calculateOrbs,resolveCombat,spawnEnemy,castOrbit,retrograde,draw,keys,pointer};
const originalLattice=drawLattice;
drawLattice=(...args)=>{const stroke=ctx.stroke;window.__HEAT_QA__.strokes=[];ctx.stroke=function(){window.__HEAT_QA__.strokes.push(ctx.strokeStyle);return stroke.call(ctx)};try{return originalLattice(...args)}finally{ctx.stroke=stroke}};'''
html=(ROOT/'index.html').read_text().replace('window.__ORRERY__ = Object.freeze(debugApi);',hook)
html=html.replace('<script id="orrery3DSource">','''<script>
THREE.WebGLRenderer=new Proxy(THREE.WebGLRenderer,{construct(Type,args){const renderer=new Type(...args),render=renderer.render;renderer.render=function(scene,camera){window.__HEAT_SCENE__=scene;return render.call(this,scene,camera)};return renderer;}});
</script><script id="orrery3DSource">''')
options=Options();options.add_argument('-headless');options.set_preference('webgl.force-enabled',True)
with tempfile.TemporaryDirectory() as folder,webdriver.Firefox(options=options) as d:
    file=Path(folder)/'index.html';file.write_text(html);d.set_window_size(1440,1000)
    for view in ['2D','3D']:
        d.get(file.as_uri());WebDriverWait(d,10).until(lambda d:d.execute_script('return !!window.__HEAT_QA__'))
        d.find_element('id','view'+view).click();d.find_element('id','riteButton').click()
        WebDriverWait(d,5).until(lambda d:d.execute_script("return getComputedStyle(document.getElementById('overlay')).opacity==='0'"))
        result=d.execute_script('''const q=window.__HEAT_QA__,g=q.game,r={};
          let p=g.player;p.folding=true;p.charge=.995;p.focus=100;
          q.updatePlayer(p,1/60);r.endpoint={overheated:p.overheated,burst:p.burst,folding:p.folding};
          q.draw(0);
          if(arguments[0]==='2D')r.blue=q.strokes.includes('#5552ff');
          else {const lines=window.__HEAT_SCENE__.children.find(o=>o.isLineSegments&&o.geometry.getAttribute('color'));
            const a=lines.geometry.getAttribute('color').array,c=new THREE.Color('#5552ff');
            r.blue=Math.abs(a[0]-c.r)<1e-5&&Math.abs(a[1]-c.g)<1e-5&&Math.abs(a[2]-c.b)<1e-5;}
          function player(overheated,charge=1){const p=q.createPlayer();g.player=p;p.overheated=overheated;p.burst=.4;p.burstCharge=charge;p.radius=180;p.radiusV=0;q.calculateOrbs(p);return p;}
          const normal=player(false),cold=player(true);
          r.radius=Math.hypot(cold.orbs[0].x-cold.x,cold.orbs[0].y-cold.y)/Math.hypot(normal.orbs[0].x-normal.x,normal.orbs[0].y-normal.y);
          q.keys.add('KeyD');
          function step(hot,boosted=false){const p=player(hot),x=p.x,a=p.angle;if(boosted){p.fuelTime=1;p.orbitBoostTime=1;}q.pointer.x=p.x+200;q.pointer.y=p.y;q.updatePlayer(p,1/60);return {movement:p.x-x,spin:p.angle-a};}
          const a=step(false),b=step(true);r.movement=b.movement/a.movement;r.spin=b.spin/a.spin;const ba=step(false,true),bb=step(true,true);r.boostedMovement=bb.movement/ba.movement;r.boostedSpin=bb.spin/ba.spin;q.keys.clear();
          function aim(hot){const p=player(hot),axis=p.axis;q.pointer.x=p.x+100;q.pointer.y=p.y-200;q.updatePlayer(p,1/60);return p.axis-axis;}
          r.aimNormal=aim(false);r.aimOverheat=aim(true);
          function damage(hot,edge,retro=false){g.enemies=[];const p=player(hot,hot?1:.96),a=p.orbs[0],b=p.orbs[1];
            const e=q.spawnEnemy('ram',edge?(a.x+b.x)/2:a.x,edge?(a.y+b.y)/2:a.y);e.r=1;e.hp=e.maxHp=100;
            e.orbCD=edge?[99,99,99]:[0,99,99];e.latticeCD=edge?0:99;if(retro)q.retrograde();else q.resolveCombat(1/60);return 100-e.hp;}
          r.moonDamage=damage(true,false)/damage(false,false);r.edgeDamage=damage(true,true)/damage(false,true);r.retroDamage=damage(true,false,true)/damage(false,false,true);
          p=player(true);q.updatePlayer(p,.41);r.recovered=p.overheated===false&&p.burst===0;
          p=player(false);p.burst=0;p.folding=true;p.charge=.5;p.focus=0;q.updatePlayer(p,1/60);r.earlyForced=p.overheated===false;
          p=player(false);p.burst=0;p.folding=true;p.charge=.96;q.castOrbit(false);r.orange=p.overheated===false&&p.burst>0;
          p=player(false);p.burst=0;p.folding=true;p.charge=1;q.castOrbit(false);r.manualFull=p.overheated===true;
          q.resetGame();r.reset=g.player.overheated===false;
          return r;''',view)
        assert result['endpoint'].get('overheated') is True,(view,result)
        assert result['endpoint']['burst']>0 and not result['endpoint']['folding'],result
        assert result['blue'],('Overheated lattice must actually render blue',view,result)
        for key,expected in [('radius',.9),('movement',.95),('spin',.75),('moonDamage',.5),('edgeDamage',.5),('retroDamage',.5),('boostedMovement',.95),('boostedSpin',.75)]:assert abs(result[key]-expected)<1e-6,(view,key,result)
        assert abs(result['aimNormal']-result['aimOverheat'])<1e-9 and abs(result['aimNormal'])>.01,result
        assert all(result[k] for k in ['recovered','earlyForced','orange','manualFull','reset']),result
        # Capture the actual blue field at a large burst radius, paused for inspection.
        d.execute_script('''const q=window.__HEAT_QA__,p=q.game.player;p.burst=.4;p.burstCharge=1;p.overheated=true;p.radius=180;q.calculateOrbs(p);q.game.chapter=null;window.requestAnimationFrame=()=>0;q.game.mode='playing';q.draw(0);''')
        d.save_screenshot(str(OUT/f'overheated-{view}.png'));print(view,json.dumps(result))
print('PASS: real endpoint/early-release behavior, exact penalties, mouse aim, blue renderers and recovery.')
