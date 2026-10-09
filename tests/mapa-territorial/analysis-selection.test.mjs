// Public matrix projection and lifecycle contracts; real appearance is checked in Actions.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {roofPosition,SelectionCallout} from '../../experiments/mapa-territorial/public/assets/mapa-territorial/analysis/selection.mjs';
const require=createRequire(new URL('../../experiments/mapa-territorial/package.json',import.meta.url));
const {JSDOM}=require('jsdom');
const identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1];
test('roof projection uses altitude and rejects clipping and behind-camera anchors',()=>{
 assert.deepEqual(roofPosition(identity,{x:0,y:0,z:0},400,300),{x:200,y:150});
 const m=[...identity];m[9]=.5;assert.equal(roofPosition(m,{x:0,y:0,z:.5},400,300).y,112.5);
 for(const point of [{x:2,y:0,z:0},{x:0,y:2,z:0},{x:0,y:0,z:2},{x:NaN,y:0,z:0}])assert.equal(roofPosition(identity,point,400,300),null);
 m[15]=-1;assert.equal(roofPosition(m,{x:0,y:0,z:0},400,300),null);
});
test('roof label stays unique through style replacement, respects depth, and cleans up',()=>{
 const dom=new JSDOM('<div id="map"></div>');globalThis.document=dom.window.document;
 const container=document.getElementById('map');Object.defineProperties(container,{clientWidth:{value:400},clientHeight:{value:300}});
 let front='comuna:8',elevation;const state={visible:true,center:[-58.4,-34.6],height:1234,id:'comuna:8',name:'Comuna 8',value:'41,6 %'};
 const engine={gl:{MercatorCoordinate:{fromLngLat(center,height){assert.deepEqual(center,state.center);elevation=height;return{x:0,y:0,z:0};}}}};
 const map={getContainer:()=>container,queryRenderedFeatures:()=>[{properties:{id:front}}]};
 const label=new SelectionCallout(engine,()=>state),args={defaultProjectionData:{mainMatrix:identity}};
 label.onAdd(map);label.render(null,args);assert.equal(elevation,1234);assert.equal(label.element.hidden,false);assert.match(label.element.textContent,/Comuna 8Seleccionada · 41,6 %/);assert.equal(label.element.getAttribute('aria-hidden'),'true');
 label.onAdd(map);assert.equal(container.querySelectorAll('.mt-analysis-selection').length,1,'style replacement cannot leave a duplicate orphan');
 front='comuna:4';label.render(null,args);assert.equal(label.element.hidden,true,'occluded roof must not be labelled as the front commune');
 front=state.id;state.visible=false;label.render(null,args);assert.equal(label.element.hidden,true);
 state.visible=true;label.render(null,args);assert.equal(label.element.hidden,false);engine.destroyed=true;label.render(null,args);assert.equal(label.element.hidden,true);
 label.onRemove();label.onRemove();assert.equal(container.children.length,0);dom.window.close();
});
