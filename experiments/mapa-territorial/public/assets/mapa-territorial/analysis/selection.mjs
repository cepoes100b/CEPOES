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
    this.name.textContent=state.name;this.description.textContent=`Seleccionada · ${state.value}`;
    this.element.style.left=`${p.x}px`;this.element.style.top=`${p.y}px`;this.element.dataset.territory=state.id;this.element.dataset.elevation=String(state.height);this.element.hidden=false;
  }
  onRemove(){this.element?.remove();this.element=null;this.map=null;}
}
