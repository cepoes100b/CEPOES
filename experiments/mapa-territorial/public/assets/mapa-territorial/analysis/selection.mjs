/** Project a selected roof anchor with MapLibre's public custom-layer matrix.
 * No private transform API, repaint loop, added geometry or changed data color.
 */
export function roofPosition(matrix,point,width,height){
  const {x,y,z}=point,w=matrix[3]*x+matrix[7]*y+matrix[11]*z+matrix[15];
  if(!Number.isFinite(w)||w<=0)return null;
  const px=(matrix[0]*x+matrix[4]*y+matrix[8]*z+matrix[12])/w;
  const py=(matrix[1]*x+matrix[5]*y+matrix[9]*z+matrix[13])/w;
  const pz=(matrix[2]*x+matrix[6]*y+matrix[10]*z+matrix[14])/w;
  if(![px,py,pz].every(Number.isFinite)||Math.abs(px)>1||Math.abs(py)>1||Math.abs(pz)>1)return null;
  return {x:(px+1)*width/2,y:(1-py)*height/2};
}
export class SelectionCallout {
  constructor(engine,state){this.id='analysis-selection-callout';this.type='custom';this.renderingMode='3d';this.engine=engine;this.state=state;this.element=null;}
  onAdd(map){
    this.element?.remove(); // Full style replacement can omit a custom layer's onRemove.
    this.map=map;this.element=document.createElement('div');this.element.className='mt-analysis-selection';this.element.hidden=true;this.element.setAttribute('aria-hidden','true');
    this.name=document.createElement('strong');this.description=document.createElement('span');this.element.append(this.name,this.description);map.getContainer().append(this.element);
  }
  hide(){if(this.element)this.element.hidden=true;}
  render(_gl,args){
    const state=this.state(),container=this.map?.getContainer();
    if(!this.element||!container||this.engine.destroyed||!state.visible||!state.center){this.hide();return;}
    const point=this.engine.gl.MercatorCoordinate.fromLngLat(state.center,state.height);
    const p=roofPosition(args.defaultProjectionData.mainMatrix,point,container.clientWidth,container.clientHeight);
    if(!p){this.hide();return;}
    const front=this.map.queryRenderedFeatures([p.x,p.y],{layers:['analysis-volume']})[0];
    if(String(front?.properties.id)!==state.id){this.hide();return;} // Never label a roof hidden by another commune.
    const description=`Seleccionada · ${state.value}`;
    if(this.name.textContent!==state.name)this.name.textContent=state.name;
    if(this.description.textContent!==description)this.description.textContent=description;
    this.element.style.transform=`translate3d(${p.x}px,${p.y}px,0) translate(-50%,calc(-100% - 22px))`;this.element.dataset.territory=state.id;this.element.dataset.elevation=String(state.height);this.element.hidden=false;
  }
  onRemove(){this.element?.remove();this.element=null;this.map=null;}
}

/** Lightweight, aria-hidden commune IDs positioned on the actual extruded roofs.
 * Positions reuse the public MapLibre projection matrix, with no private API,
 * extra render loop, new geometry or change to the analysis data.
 */
export class ComunaRoofLabels {
  constructor(engine,state){
    this.id='analysis-roof-labels';this.type='custom';this.renderingMode='3d';
    this.engine=engine;this.state=state;this.root=null;this.elements=new Map();
  }
  onAdd(map){
    this.onRemove();this.map=map;
    this.root=document.createElement('div');
    this.root.className='mt-roof-label-layer';this.root.setAttribute('aria-hidden','true');
    for(const feature of this.engine.territories.filter(t=>t.properties.level==='comuna')){
      const id=feature.properties.id;
      const el=document.createElement('span');el.className='mt-roof-label';
      el.textContent='C'+String(id).split(':')[1];el.hidden=true;
      this.root.append(el);this.elements.set(id,{el,center:feature.properties.center});
    }
    map.getContainer().append(this.root);
  }
  hide(){for(const {el} of this.elements.values())el.hidden=true;}
  render(_gl,args){
    const state=this.state(),container=this.map?.getContainer();
    if(!container||!this.root||!state.visible||this.engine.destroyed){
      this.hide();return;
    }
    const matrix=args.defaultProjectionData?.mainMatrix;
    if(!matrix){this.hide();return;}
    const width=container.clientWidth,height=container.clientHeight;
    for(const [id,{el,center}] of this.elements){
      const ratio=state.values.get(id);
      if(!Array.isArray(center)||id===state.selected||ratio==null||ratio<=0){
        el.hidden=true;continue;
      }
      const coords=this.engine.gl.MercatorCoordinate.fromLngLat(center,ratio*state.maxHeight);
      const pt=roofPosition(matrix,coords,width,height);
      if(!pt||pt.x<12||pt.x>width-12||pt.y<10||pt.y>height-12){
        el.hidden=true;continue;
      }
      el.style.transform=`translate3d(${pt.x}px,${pt.y}px,0) translate(-50%,-100%)`;
      el.hidden=false;
    }
  }
  onRemove(){
    this.root?.remove();this.root=null;this.map=null;this.elements.clear();
  }
}
