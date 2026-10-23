// Adapter contract against a fake engine; no browser/WebGL pass is implied.
import test from 'node:test';
import assert from 'node:assert/strict';
import {TerritorialMap} from '../../experiments/mapa-territorial/public/assets/mapa-territorial/engine.mjs';
class FakeMap {
  constructor(options){this.options=options;this.sources=new Map();this.layers=new Map();this.events={};this.paints=[];this.filters=[];this.canvas={style:{},setAttribute(){}};this.touchZoomRotate={disableRotation(){}};}
  addControl(){}getCanvas(){return this.canvas;}on(name,fn){this.events[name]=fn;}once(name,fn){this.events[`once:${name}`]=fn;}
  addSource(id,s){this.sources.set(id,{...s,setData(data){this.data=data;}});}getSource(id){return this.sources.get(id);}
  addLayer(l){this.layers.set(l.id,l);}getLayer(id){return this.layers.get(id);}setLayoutProperty(){}
  setPaintProperty(...a){this.paints.push(a);}setFilter(...a){this.filters.push(a);}queryRenderedFeatures(){return this.hits||[];}getContainer(){return {clientWidth:700,clientHeight:500};}
  project(){return {x:0,y:0};}fitBounds(bounds,options){this.fit={bounds,options};}easeTo(options){this.ease=options;}isStyleLoaded(){return true;}
  setStyle(style){this.style=style;}areTilesLoaded(){return true;}remove(){this.removed=true;}
}
const fakeGL={Map:FakeMap,NavigationControl:class{},AttributionControl:class{},ScaleControl:class{}};
test('map adapter: local-only style, clusters, safe filters, fallback and teardown',async()=>{
  Object.assign(globalThis,{document:{documentElement:{dataset:{theme:'light'}}},matchMedia:()=>({matches:true}),requestAnimationFrame:fn=>fn(),MutationObserver:class{observe(){}disconnect(){}}});
  const features=[{properties:{id:'barrio:test',level:'barrio',name:'Test',area_km2:2},geometry:{type:'Polygon',coordinates:[[[-58.4,-34.6],[-58.5,-34.6],[-58.4,-34.7],[-58.4,-34.6]]]}}];
  let status;const m=new TerritorialMap(fakeGL,{container:'map',territories:features,onTerritory(){},onRecord(){},onReady(){},onFailure(){},onBaseStatus:(s,b)=>{status={s,b};}});
  assert.deepEqual(m.map.options.style.sources,{});assert.equal(m.map.options.cooperativeGestures,true);assert.equal(m.map.options.renderWorldCopies,false);
  m.addLayers();assert.equal(m.map.getSource('services').cluster,true);assert.equal(m.map.getSource('comuna').promoteId,'id','string territorial IDs must survive vector tiling for feature-state');
  const point={properties:{id:'p1'},geometry:{type:'Point',coordinates:[-58.4,-34.6]}};
  const bad={properties:{id:'p2',position_territory_warning:true},geometry:point.geometry};
  m.update({level:'barrio',territory:'barrio:test',records:[point,bad],stats:{rows:new Map([['barrio:test',{rate:3}]])}});
  assert.equal(m.map.getSource('services').data.features.length,1);assert.deepEqual(m.map.filters.find(x=>x[0]==='barrio-selected'),['barrio-selected',['==',['get','id'],'barrio:test']]);
  m.fit(features[0]);assert.equal(m.map.fit.options.duration,0,'respects reduced motion');
  m.base='streets';m.map.style={version:8,name:'external-style'};
  globalThis.fetch=async()=>{throw new Error('offline');};await m.setStreets(true);assert.equal(m.base,'local');assert.equal(status.b,false);assert.match(status.s,/no está disponible/);assert.equal(m.map.style.layers[0].id,'background');assert.equal(m.map.style.name,undefined);
  let resolveZoom;m.map.hits=[{layer:{id:'clusters'},properties:{cluster_id:1},geometry:{coordinates:[-58.4,-34.6]}}];
  m.map.getSource('services').getClusterExpansionZoom=()=>new Promise(r=>{resolveZoom=r;});
  const pending=m.pick({point:{x:10,y:10}});m.fit(features[0]);resolveZoom(15);await pending;assert.equal(m.map.ease,undefined,'stale cluster cannot override newer fit');
  m.analysis={active:false,pick(){},destroy(){}};const pendingAnalysis=m.pick({point:{x:10,y:10}});m.analysis.active=true;resolveZoom(15);await pendingAnalysis;assert.equal(m.map.ease,undefined,'stale cluster cannot override analytical camera');
  m.destroy();assert.equal(m.map.removed,true);
});
