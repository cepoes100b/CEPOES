import {roofPosition} from './selection.mjs';
import {MAX_HEIGHT} from './model.mjs';
/** Roof names projected at statistical height; collision and occlusion are explicit. */
export class RoofLabels {
  constructor(adapter){this.adapter=adapter;this.id='analysis-roof-labels';this.type='custom';this.renderingMode='3d';this.labels=[];}
  onAdd(map){
    this.onRemove();this.map=map;
    for(const feature of this.adapter.engine.territories||[]){
      if(feature.properties.level!=='comuna')continue;
      const el=document.createElement('span');el.className='mt-roof-label';el.textContent=feature.properties.name;el.setAttribute('aria-hidden','true');el.hidden=true;map.getContainer().append(el);this.labels.push({feature,el});
    }
  }
  render(_gl,args){
    const a=this.adapter,c=this.map.getContainer(),rects=[];
    for(const {feature,el} of this.labels){
      el.hidden=true;
      const id=feature.properties.id;
      // During movement keep only the selected callout. Repeated depth queries for
      // every name compete with WebGL rendering on software/mobile GPUs.
      if(!a.active||a.view!=='3d'||a.level!=='comuna'||id===a.selected||a.frame||a.orbitFrame||this.map.isMoving())continue;
      const p=roofPosition(args.defaultProjectionData.mainMatrix,a.engine.gl.MercatorCoordinate.fromLngLat(feature.properties.center,(a.values.get(id)??0)*MAX_HEIGHT),c.clientWidth,c.clientHeight);
      if(!p||p.x<40||p.x>c.clientWidth-40||p.y<30||p.y>c.clientHeight-30)continue;
      if(rects.some(r=>Math.abs(r.x-p.x)<70&&Math.abs(r.y-p.y)<24))continue;
      const front=this.map.queryRenderedFeatures([p.x,p.y],{layers:['analysis-volume']})[0];
      if(front?.properties.id!==id)continue;
      el.style.left=p.x+'px';el.style.top=p.y+'px';el.hidden=false;rects.push(p);
    }
  }
  hide(){for(const {el} of this.labels)el.hidden=true;}
  onRemove(){for(const {el} of this.labels)el.remove();this.labels=[];}
}
