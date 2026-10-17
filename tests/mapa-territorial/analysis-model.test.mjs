import test from 'node:test';
import assert from 'node:assert/strict';
import {validateAnalysis,scaleForIndicator,normalized,heightFor,ranks,cityRate,colorFor,MISSING_COLOR,MAX_HEIGHT} from '../../experiments/mapa-territorial/public/assets/mapa-territorial/analysis/model.mjs';
import {readState,stateQuery} from '../../experiments/mapa-territorial/public/assets/mapa-territorial/model.mjs';
const indicator=()=>({id:'test-rate',status:'verified',level:'comuna',name:'Test fixture only',unit:'%',period:'2022',universe:'Explicit universe',method:'N / D × 100',numerator_label:'N',denominator_label:'D',multiplier:100,digits:1,source_ids:['test'],rows:Array.from({length:15},(_,i)=>({id:`comuna:${i+1}`,numerator:i,denominator:100,value:i}))});
const source={id:'test',publisher:'Fixture',license:'Fixture only',checked_at:'2026-10-09',url:'https://example.org/data'};
const fixture=()=>({schema:'cepoes-territorial-analysis-v1',indicators:[indicator()],sources:[source]});
test('analytical dataset requires exact denominator, 15 rows and named sources',()=>{
  assert.equal(validateAnalysis(fixture()).indicators.length,1);
  for(const mutate of [d=>d.indicators[0].rows.pop(),d=>d.indicators[0].rows[2].value=0,d=>d.indicators[0].rows[2].denominator=0,d=>d.indicators[0].status='unverified',d=>d.indicators[0].universe='',d=>d.sources[0].url='javascript:alert(1)']){const d=structuredClone(fixture());mutate(d);assert.throws(()=>validateAnalysis(d));}
});
test('zero, missing, ratio and color have one common zero-based scale',()=>{
  const ind=indicator(),scale=scaleForIndicator(ind);
  assert.equal(heightFor(0,scale),0);assert.equal(heightFor(null,scale),0);assert.equal(normalized(null,scale),null);assert.notEqual(colorFor(0,scale),MISSING_COLOR);assert.equal(colorFor(null,scale),MISSING_COLOR);
  assert.equal(heightFor(4,scale)/heightFor(2,scale),2);assert.equal(heightFor(scale.max,scale),MAX_HEIGHT);assert.equal(scale.min,0);assert.equal(scale.ticks.length,5);
  const d=fixture();d.indicators[0].rows[0]={id:'comuna:1',value:null,missing_reason:'Unavailable'};validateAnalysis(d);assert.equal(cityRate(d.indicators[0]),null);
});
test('ranking shares positions at displayed precision and keeps missing outside ranking',()=>{
  const sorted=ranks([{id:'comuna:1',value:4},{id:'comuna:2',value:4.01},{id:'comuna:3',value:2},{id:'comuna:4',value:null}],1);
  assert.deepEqual(sorted.map(r=>r.rank),[1,1,3,null]);assert.deepEqual(sorted.map(r=>r.tied),[true,true,false,false]);
});
test('city rate is weighted ratio of sums, not unweighted mean of rates',()=>{
  assert.equal(cityRate({multiplier:100,rows:[{numerator:10,denominator:20,value:50},{numerator:10,denominator:80,value:12.5}]}),20);
});
test('analytical URL preserves public selection and never invents barrio rates',()=>{
  const ts=[{properties:{id:'barrio:la-boca',level:'barrio'}},{properties:{id:'comuna:4',level:'comuna'}}];
  const state=readState('?modo=analizar&vista=3d&territorio=barrio:la-boca&indicador=salud',ts);
  assert.equal(state.territory,'barrio:la-boca');assert.equal(state.level,'barrio');assert.equal(state.mode,'analyze');assert.equal(state.view,'3d');
  assert.match(stateQuery(state),/modo=analizar/);assert.match(stateQuery(state),/territorio=barrio%3Ala-boca/);assert.equal(readState('?modo=analizar&indicador=<script>',ts).indicator,'');
});
