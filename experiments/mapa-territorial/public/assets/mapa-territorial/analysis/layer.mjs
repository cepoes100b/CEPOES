import {COLORS,MISSING_COLOR,MAX_HEIGHT,normalized,scaleForIndicator} from './model.mjs';
import {number as fmt} from '../model.mjs';
import {SelectionCallout} from './selection.mjs';
const SUFFIXES=['fill','line','selected-halo','selected'];
const value=['coalesce',['feature-state','ratio'],0];
const color=['case',['boolean',['feature-state','available'],false],['interpolate',['linear'],value,...COLORS.flatMap((c,i)=>[i/4,c])],MISSING_COLOR];
/** An optional adapter on the existing TerritorialMap. Uses only public MapLibre APIs. */
export class AnalyticalLayer {
  constructor(engine,{onState=()=>{}}={}){
    this.engine=engine;this.map=engine.map;this.onState=onState;this.active=false;this.initialized=false;this.view='flat';this.values=new Map();this.frame=0;this.orbitFrame=0;this.generation=0;this.currentKey='';
    this.callout=new SelectionCallout(engine,()=>({visible:this.active&&this.view==='3d'&&this.level==='comuna'&&!!this.selected,center:this.selectedFeature?.properties.center,name:this.selectedFeature?.properties.name,id:this.selected,height:(this.values.get(this.selected)??0)*MAX_HEIGHT,value:this.selectedValue}));
    this.motion=matchMedia('(prefers-reduced-motion: reduce)');
    this.onMotion=()=>{if(this.motion.matches&&this.active){this.stopOrbit();this.finish();this.map.stop();this.map.easeTo({pitch:this.view==='3d'?48:0,bearing:this.view==='3d'?-22:0,duration:0});}this.report();};
    this.motion.addEventListener('change',this.onMotion);
    this.onVisibility=()=>{if(document.hidden){this.stopOrbit();this.finish();}};
    document.addEventListener('visibilitychange',this.onVisibility);
    this.onInteract=()=>{if(this.orbitFrame)this.stopOrbit();};
    for(const type of ['pointerdown','wheel','keydown','touchstart'])this.map.getContainer().addEventListener(type,this.onInteract,{capture:true,passive:true});
    engine.analysis=this;this.mount();
  }
  mount(){
    if(!this.map.getSource('comuna'))return;
    if(!this.map.getLayer('analysis-volume'))this.map.addLayer({id:'analysis-volume',source:'comuna',type:'fill-extrusion',layout:{visibility:'none'},paint:{'fill-extrusion-color':color,'fill-extrusion-height':['*',value,MAX_HEIGHT],'fill-extrusion-base':0,'fill-extrusion-opacity':.96,'fill-extrusion-vertical-gradient':true,'fill-extrusion-height-transition':{duration:0},'fill-extrusion-color-transition':{duration:0}}});
    if(!this.map.getLayer(this.callout.id))this.map.addLayer(this.callout);
    // Style swaps discard feature-state; restore the current visible values immediately.
    for(const [id,ratio] of this.values)this.apply(id,ratio);
    if(this.active)this.refresh();
  }
  report(extra={}){this.onState({view:this.view,animation:this.frame?'running':'idle',orbit:!!this.orbitFrame,reducedMotion:this.motion.matches,...extra});}
  apply(id,ratio){this.values.set(id,ratio);this.map.setFeatureState({source:'comuna',id},{ratio:ratio??0,available:ratio!==null});}
  set(ind,{view='flat',level='comuna',selected=''}={}){
    const opening=!this.initialized;const previousView=this.view;
    this.active=true;this.indicator=ind;this.level=level;this.selected=selected;this.view=level==='comuna'?view:'flat';
    this.selectedFeature=this.engine.territories?.find(f=>f.properties.id===selected);
    const selectedRow=ind.rows.find(r=>r.id===selected);this.selectedValue=selectedRow?.value==null?'s/d':`${fmt(selectedRow.value,ind.digits??1)} ${ind.unit_short||ind.unit||''}`;
    this.callout.hide();
    if(!this.map.getSource('comuna'))return;
    this.mount();
    if(opening){this.initialized=true;this.oldPixelRatio=this.map.getPixelRatio();this.map.setPixelRatio(Math.min(devicePixelRatio||1,1.5));}
    const scale=scaleForIndicator(ind);const key=`${ind.id}:${ind.period}`;
    if(key!==this.currentKey){this.stopOrbit();this.currentKey=key;this.target=new Map(ind.rows.map(r=>[r.id,normalized(r.value,scale)]));this.animate();}
    this.refresh();
    if(opening||previousView!==this.view){this.stopOrbit();this.map.stop();this.map.easeTo({pitch:this.view==='3d'?48:0,bearing:this.view==='3d'?-22:0,duration:this.motion.matches?0:450});}
    this.report();
  }
  animate(){
    cancelAnimationFrame(this.frame);this.frame=0;const token=++this.generation;
    if(this.motion.matches||document.hidden||this.view==='flat'){this.finish();return;}
    const from=new Map(this.values),start=performance.now();
    const step=now=>{
      if(!this.active||token!==this.generation)return;
      const p=Math.min(1,(now-start)/550),ease=1-(1-p)**3;
      for(const [id,to] of this.target){const a=from.get(id);this.apply(id,to===null?null:(a??0)+(to-(a??0))*ease);}
      if(p<1)this.frame=requestAnimationFrame(step);else{this.frame=0;this.report();}
    };
    this.frame=requestAnimationFrame(step);this.report();
  }
  finish(){
    cancelAnimationFrame(this.frame);this.frame=0;this.generation++;
    if(this.target&&this.map.getSource('comuna'))for(const [id,ratio] of this.target)this.apply(id,ratio);
    this.report();
  }
  refresh(){
    if(!this.active||!this.map.getLayer('analysis-volume'))return;
    const supported=this.level==='comuna';
    for(const level of ['barrio','comuna']){
      for(const suffix of SUFFIXES)this.map.setLayoutProperty(`${level}-${suffix}`,'visibility',this.level===level?'visible':'none');
      this.map.setFilter(`${level}-selected-halo`,['==',['get','id'],this.selected]);
      this.map.setFilter(`${level}-selected`,['==',['get','id'],this.selected]);
      this.map.setPaintProperty(`${level}-selected`,'line-color','#b75118');
    }
    this.map.setPaintProperty(`${this.level}-fill`,'fill-color',supported?color:MISSING_COLOR);
    this.map.setPaintProperty(`${this.level}-fill`,'fill-opacity',1);
    this.map.setLayoutProperty('analysis-volume','visibility',supported&&this.view==='3d'?'visible':'none');
    for(const id of ['clusters','points'])this.map.setLayoutProperty(id,'visibility','none');
    this.map.setLight({anchor:'viewport',position:[1.5,200,45],color:'#ffffff',intensity:.32});
    this.engine.scheduleLabels();
  }
  hitLayers(){return this.level==='comuna'&&this.view==='3d'?['analysis-volume','comuna-fill']:[`${this.level}-fill`];}
  pick(event){
    this.stopOrbit();const hit=this.map.queryRenderedFeatures(event.point,{layers:this.hitLayers().filter(id=>this.map.getLayer(id))})[0];
    if(hit)this.engine.onTerritory(String(hit.properties.id));
  }
  toggleOrbit(){
    if(this.orbitFrame){this.stopOrbit();return;}
    if(!this.active||this.view!=='3d'||this.motion.matches||document.hidden)return;
    let previous=performance.now();
    const step=now=>{
      if(!this.active||document.hidden||this.motion.matches||this.view!=='3d'){this.stopOrbit();return;}
      const dt=Math.min(50,now-previous);previous=now;
      if(!this.map.isMoving())this.map.setBearing(this.map.getBearing()+dt*.0025);
      this.orbitFrame=requestAnimationFrame(step);
    };
    this.orbitFrame=requestAnimationFrame(step);this.report();
  }
  stopOrbit(){cancelAnimationFrame(this.orbitFrame);this.orbitFrame=0;this.report();}
  deactivate(){
    if(!this.active)return;this.active=false;this.initialized=false;this.stopOrbit();this.finish();
    this.callout.hide();
    if(this.map.getLayer('analysis-volume'))this.map.setLayoutProperty('analysis-volume','visibility','none');
    for(const id of ['clusters','points'])if(this.map.getLayer(id))this.map.setLayoutProperty(id,'visibility','visible');
    this.map.stop();this.map.easeTo({pitch:0,bearing:0,duration:this.motion.matches?0:350});
    if(this.oldPixelRatio)this.map.setPixelRatio(this.oldPixelRatio);
    this.engine.refresh();
  }
  destroy(){
    this.active=false;this.stopOrbit();cancelAnimationFrame(this.frame);this.frame=0;this.generation++;
    this.callout.onRemove();
    this.motion.removeEventListener('change',this.onMotion);document.removeEventListener('visibilitychange',this.onVisibility);
    for(const type of ['pointerdown','wheel','keydown','touchstart'])this.map.getContainer().removeEventListener(type,this.onInteract,true);
  }
}
