const test=require('node:test');
const assert=require('node:assert/strict');
const rules=require('../game-rules.js');
test('only reaching the meter endpoint overheats, not the orange window or early forced release',()=>{
  assert.equal(typeof rules.isOverheatedCharge,'function');
  for(const charge of [0,.36,.72,.96,.999]) assert.equal(rules.isOverheatedCharge(charge),false);
  for(const charge of [1,1.035,1.04]) assert.equal(rules.isOverheatedCharge(charge),true);
});
test('overheat modifiers match the requested percentages only during the overheated burst',()=>{
  assert.equal(typeof rules.attackModifiers,'function');
  const hot={overheated:true,burst:.58,burstCharge:1};
  assert.deepEqual(rules.attackModifiers(hot),{movement:1-5/100,radius:1-10/100,spin:1-25/100,damage:1-50/100});
  for(const p of [{},{overheated:false,burst:.58},{overheated:true,burst:0}]) {
    assert.deepEqual(rules.attackModifiers(p),{movement:1,radius:1,spin:1,damage:1});
  }
});
test('overheated damage uses the maximum orange charge as its comparison, not extra overcharge damage',()=>{
  assert.equal(typeof rules.attackCharge,'function');
  const hot={overheated:true,burst:.58,burstCharge:1};
  const orange={overheated:false,burst:.58,burstCharge:.96};
  for(const [base,gain] of [[1.05,2.65],[.95,1.15]]) {
    const a=(base+rules.attackCharge(hot)*gain)*rules.attackModifiers(hot).damage;
    const b=base+rules.attackCharge(orange)*gain;
    assert.equal(a/b,.5);
  }
  assert.equal(rules.attackCharge({...orange,burstCharge:.5}),.5);
});
