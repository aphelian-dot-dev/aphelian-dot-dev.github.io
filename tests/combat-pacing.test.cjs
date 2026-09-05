const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const frame = html.match(/    function frame\(now\) \{[\s\S]*?(?=\n    function adjustRenderQuality)/)[0];

function replay(impactPause) {
  const game = {mode:'playing', freeze:0, elapsed:0};
  const context = {game, lastFrame:0, accumulator:0, STEP:1/60,
    clamp:(n,a,b)=>Math.max(a,Math.min(b,n)),
    update:dt=>{game.elapsed+=dt;}, draw:()=>{}, adjustRenderQuality:()=>{}, requestAnimationFrame:()=>{}};
  vm.createContext(context); vm.runInContext(frame,context);
  for(let i=1;i<=120;i++) {
    // Frequent ordinary/heavy collisions set these inherited feedback timers.
    if(i%3===1) game.freeze=impactPause;
    context.frame(i*1000/60);
  }
  return game.elapsed;
}

test('repeated weapon impacts do not consume simulation time',()=>{
  const quiet=replay(0), impacts=replay(.028);
  console.log(JSON.stringify({quietSeconds:quiet,impactSeconds:impacts}));
  assert.ok(quiet>1.95);
  assert.ok(Math.abs(quiet-impacts)<1e-8,`Impacts lost ${quiet-impacts} seconds of input/simulation`);
});
test('combat rendering retains restrained screen flashes',()=>{
  const draw=html.match(/    function draw\(realDt\) \{[\s\S]*?(?=\n    function drawAmbientGeometry)/)[0];
  assert.doesNotMatch(draw,/game\.flash \* \.34/);
});

test('impact shake is subtle, deterministic, visual-only and reduced-motion safe',()=>{
  const context={window:{}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'..','renderer-3d.js'),'utf8'),context);
  const offset=context.window.orreryImpactOffset;
  assert.equal(typeof offset,'function','Missing shared visual-only impact offset');
  const game=Object.freeze({mode:'playing',shake:4.5,freeze:0,time:12});
  const first=offset(game,.12,false);
  assert.ok(Math.hypot(first.x,first.y)>.1,'Ordinary impacts should visibly nudge the field');
  assert.deepEqual(first,offset(game,.12,false),'No random gameplay state should be consumed');
  for(let i=0;i<240;i++) {
    const p=offset({...game,shake:100},i/60,false);
    assert.ok(Math.hypot(p.x,p.y)<=3+1e-9,'Even stacked impacts must stay within three CSS pixels');
  }
  for(const g of [{...game,shake:0},{...game,mode:'title'},{...game,mode:'paused'},{...game,mode:'won'}]) {
    const p=offset(g,.12,false);assert.equal(Math.hypot(p.x,p.y),0);
  }
  const reduced=offset(game,.12,true);assert.equal(Math.hypot(reduced.x,reduced.y),0);
  assert.equal(game.freeze,0);assert.equal(game.time,12);assert.equal(game.shake,4.5);
});

test('taking damage does not freeze movement or the rite clock',()=>{
  assert.ok(Math.abs(replay(0)-replay(.075))<1e-8);
});
