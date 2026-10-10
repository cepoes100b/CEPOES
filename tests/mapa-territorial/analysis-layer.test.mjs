// State/adapter contracts only; no claim of a WebGL or visual pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import {AnalyticalLayer} from '../../experiments/mapa-territorial/public/assets/mapa-territorial/analysis/layer.mjs';
const ind=(id,values)=>({id,period:'2022',rows:values.map((value,i)=>({id:`comuna:${i+1}`,value}))});
test('analytical adapter animates actual state, interrupts, honors live reduced motion and stops idle loops',()=>{
  let now=0,seq=0;const frames=new Map(),canvasEvents=new Map(),docEvents=new Map();
  const motion={matches:false,addEventListener(type,fn){this.listener=fn;},removeEventListener(){this.listener=null;}};
  Object.assign(globalThis,{devicePixelRatio:3,matchMedia:()=>motion,document:{hidden:false,addEventListener:(t,f)=>docEvents.set(t,f),removeEventListener:t=>docEvents.delete(t)},performance:{now:()=>now},requestAnimationFrame:fn=>{frames.set(++seq,fn);return seq;},cancelAnimationFrame:id=>frames.delete(id)});
  const step=ms=>{now=ms;const pending=[...frames.values()];frames.clear();pending.forEach(f=>f(now));};
  const state=new Map(),layouts=new Map(),layers=new Map();let sourceReady=false;
  const map={getSource:()=>sourceReady?{}:undefined,getLayer:id=>layers.get(id)||{id},addLayer:l=>layers.set(l.id,l),setFeatureState:({id},s)=>state.set(id,s),setLayoutProperty:(id,p,v)=>layouts.set(id+':'+p,v),setPaintProperty(){},setFilter(){},getPixelRatio:()=>3,setPixelRatio(r){this.pixelRatio=r;},easeTo(o){this.camera=o;},stop(){},setLight(){},getContainer:()=>({addEventListener:(t,f)=>canvasEvents.set(t,f),removeEventListener:t=>canvasEvents.delete(t)}),queryRenderedFeatures:()=>[{properties:{id:'comuna:2'}}],isMoving:()=>false,getBearing:()=>0,setBearing(v){this.bearing=v;}};
  let picked='';const engine={map,scheduleLabels(){},refresh(){this.refreshed=true;},onTerritory:id=>picked=id};
  const a=new AnalyticalLayer(engine);a.set(ind('first',[0,10]),{view:'3d'});
  assert.equal(map.pixelRatio,undefined);assert.equal(map.camera,undefined);assert.equal(a.initialized,false);
  sourceReady=true;a.mount();a.set(ind('first',[0,10]),{view:'3d'});assert.equal(map.camera.pitch,48,'deep link initializes camera after style/load');
  assert.equal(engine.analysis,a);assert.equal(map.pixelRatio,1.5);assert.equal(a.orbitFrame,0,'rotation is opt-in');assert.equal(frames.size,1);
  step(250);assert.ok(state.get('comuna:2').ratio>0&&state.get('comuna:2').ratio<1,'height-driving feature state changes progressively');
  a.set(ind('second',[10,0]),{view:'3d'});assert.equal(frames.size,1,'old animation cancelled');step(1000);assert.equal(state.get('comuna:2').ratio,0);assert.equal(state.get('comuna:1').ratio,1);assert.equal(frames.size,0,'no idle animation loop');
  a.toggleOrbit();assert.equal(frames.size,1);canvasEvents.get('keydown')();assert.equal(frames.size,0,'keyboard interaction stops orbit until explicit restart');
  a.toggleOrbit();motion.matches=true;motion.listener();assert.equal(frames.size,0);a.toggleOrbit();assert.equal(frames.size,0,'motion preference prevents orbit');
  a.set(ind('third',[4,2]),{view:'3d'});assert.equal(frames.size,0,'reduced motion applies final heights immediately');assert.equal(state.get('comuna:2').ratio,.5);
  a.pick({point:[0,0]});assert.equal(picked,'comuna:2');
  a.set(ind('third',[4,2]),{view:'3d',level:'barrio',selected:'barrio:test'});assert.equal(a.view,'flat');assert.equal(layouts.get('analysis-volume:visibility'),'none');
  a.deactivate();assert.equal(map.pixelRatio,3);assert.equal(map.camera.pitch,0);assert.equal(layouts.get('points:visibility'),'visible');assert.equal(engine.refreshed,true);
  a.destroy();assert.equal(frames.size,0);assert.equal(canvasEvents.size,0);assert.equal(docEvents.size,0);assert.equal(motion.listener,null);
});
