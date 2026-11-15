'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context={window:{}};vm.createContext(context);vm.runInContext(fs.readFileSync('static/vnext/workspace.js','utf8'),context);
const ui=context.window.ThemeScopeUI;
const a={ticker:'A',theme_id:'one',role:'Core',relative:{w:'.1'}},b={ticker:'A',theme_id:'two',role:'Enabler',relative:{w:'-.2'}},c={ticker:'B',theme_id:'two',role:'Core',relative:{w:'.3'}};
assert.equal(ui.displayRows([a,b,c],[a,c],'')[0],a);
assert.equal(ui.displayRows([a,b,c],[a,c],'two')[0],b);
assert.equal(ui.displayRows([a,b,c],[a,c],'two')[1],c);
assert.equal(a.theme_id,'one');assert.equal(b.role,'Enabler');
const axis=ui.axis(-.3913,1.237,5);
assert.ok(axis.low<=-.3913&&axis.high>=1.237);
assert.ok(axis.ticks.some(v=>v===0));assert.ok(axis.ticks.every(v=>Number.isInteger(v*100)));
const {execFileSync}=require('node:child_process');
const python=process.env.THEMESCOPE_TEST_PYTHON||(['runtime/qa-python312/Scripts/python.exe','.venv-vnext/Scripts/python.exe'].find(p=>fs.existsSync(p)))||'python';
const cases=JSON.parse(execFileSync(python,['tests/research_v2_contract_fixture.py'],{encoding:'utf8',maxBuffer:4*1024*1024,env:{...process.env,PYTHONUTF8:'1'}}));
for(const [direction,snapshot] of Object.entries(cases)){
  const expected=direction.includes('Long')?'long':direction.includes('Short')?'short':null;
  assert.equal(ui.currentSide(snapshot),expected);
  const rows=ui.researchRows(snapshot),source=snapshot.research_v2.list.rows;
  assert.equal(rows.length,source.length);
  for(let i=0;i<rows.length;i++){
    assert.equal(rows[i].list_order,i);assert.equal(rows[i].research_order_index,source[i].research_order_index);
    assert.equal(rows[i].ticker,source[i].ticker);
  }
  if(!expected){assert.equal(rows.length,0);assert.equal(ui.themeState(snapshot,'a'),'Non-directional');}
}
assert.equal(ui.themeState(cases['Short Bias'],'e'),'Leading');
assert.equal(ui.themeState(cases['Short Bias'],'a'),'Lagging');
assert.equal(ui.researchRows({}).length,0);
const previous={research_v2:{themes:{one:{state:'Leading',short_state:'Lagging'}},list:{side:'short',rows:[{ticker:'A',theme_id:'one'}]}}};
assert.equal(ui.themeState(previous,'one'),'Unavailable');assert.equal(ui.researchRows(previous).length,0);
assert.equal(ui.comparisonMessage('ranked_universe_changed'),'Scored theme universe changed');
assert.equal(ui.comparisonMessage('methodology_or_membership_changed'),'Methodology or reviewed membership changed');
assert.equal(ui.comparisonMessage('insufficient_completed_history'),'Not enough completed history');
assert.equal(ui.comparisonMessage('unavailable_score'),'Structural strength unavailable');
assert.equal(ui.themeState(cases['Neutral'],'missing'),'Unavailable');
assert.ok(!fs.readFileSync('static/vnext/index.html','utf8').includes('countertrend-tab'));
assert.ok(!fs.readFileSync('static/vnext/index.html','utf8').includes('candidate-w'));
console.log('Workspace presentation, selected-theme context and axis checks passed.');
