import {collection,featureID,boundsFor,hasPoint,scaleFor} from './model.mjs';
const CABA=[[-58.552,-34.721],[-58.323,-34.519]];
const isDark=()=>document.documentElement.dataset.theme==='dark';
export const palette=()=>isDark()?['#244455','#346980','#4693ac','#72bdd0','#a3e4ed']:['#e0eef3','#b4d4e1','#7fb1c7','#42849f','#145675'];
const localStyle=()=>({version:8,sources:{},layers:[{id:'background',type:'background',paint:{'background-color':isDark()?'#0b1b27':'#e6eff3'}}]});
export class TerritorialMap {
  static async create(options){
    const gl=await import('./vendor/maplibre-gl.mjs');
    gl.setWorkerUrl(new URL('./vendor/maplibre-gl-worker.mjs',import.meta.url).href);
    return new TerritorialMap(gl,options);
  }
  constructor(gl,{container,territories,onTerritory,onRecord,onReady,onFailure,onBaseStatus}){
    this.gl=gl;this.territories=territories;this.onTerritory=onTerritory;this.onRecord=onRecord;this.onBaseStatus=onBaseStatus;
    this.level='barrio';this.selected='';this.records=[];this.stats=null;this.labels=[];this.base='local';this.destroyed=false;this.baseToken=0;this.actionToken=0;this.ready=false;this.analysis=null;
    this.map=new gl.Map({container,style:localStyle(),bounds:CABA,fitBoundsOptions:{padding:28},minZoom:9,maxZoom:17,maxBounds:[[-58.72,-34.85],[-58.15,-34.35]],renderWorldCopies:false,attributionControl:false,cooperativeGestures:true,dragRotate:false,pitchWithRotate:false,locale:{'NavigationControl.ZoomIn':'Acercar','NavigationControl.ZoomOut':'Alejar','NavigationControl.ResetBearing':'Orientar al norte','CooperativeGesturesHandler.WindowsHelpText':'Usá Ctrl + rueda para acercar el mapa','CooperativeGesturesHandler.MacHelpText':'Usá ⌘ + rueda para acercar el mapa','CooperativeGesturesHandler.MobileHelpText':'Usá dos dedos para mover el mapa'}});
    this.map.addControl(new gl.NavigationControl({showCompass:false}),'top-right');
    this.map.addControl(new gl.AttributionControl({compact:false,customAttribution:'Cartografía: <a href="https://data.buenosaires.gob.ar/dataset/barrios" target="_blank" rel="noopener">BA Data · GCBA</a> · CEPOES'}),'bottom-right');
    this.map.addControl(new gl.ScaleControl({maxWidth:85,unit:'metric'}),'bottom-left');
    this.map.touchZoomRotate.disableRotation();
    const canvas=this.map.getCanvas();canvas.setAttribute('aria-label','Mapa de CABA. Flechas para desplazar, + y − para zoom. Elegí territorios con los controles o la tabla.');canvas.setAttribute('role','img');
    this.map.on('style.load',()=>{this.addLayers();this.refresh();});
    this.map.once('load',()=>{this.ready=true;clearTimeout(this.startupTimer);onReady();});
    this.map.on('webglcontextlost',()=>onFailure(new Error('Se perdió el contexto gráfico. La tabla conserva todos los datos.')));
    this.map.on('move',()=>this.scheduleLabels());this.map.on('resize',()=>this.scheduleLabels());
    this.map.on('click',e=>this.pick(e));
    this.map.on('mousemove',e=>{const ids=(this.analysis?.active?this.analysis.hitLayers():['points','clusters',`${this.level}-fill`]).filter(id=>this.map.getLayer(id));const hit=ids.length&&this.map.queryRenderedFeatures(e.point,{layers:ids}).length;canvas.style.cursor=hit?'pointer':'';});
    this.map.on('error',e=>{if(this.base==='streets'&&!this.restoring){this.restoring=true;this.baseToken++;this.base='local';clearTimeout(this.baseTimer);this.map.setStyle(localStyle());this.onBaseStatus('No se pudo cargar la base de calles. Conservamos la cartografía local.',false);this.restoring=false;}else if(!this.ready&&e.error?.message?.includes('WebGL'))onFailure(e.error);});
    this.startupTimer=setTimeout(()=>{if(!this.ready)onFailure(new Error('El motor cartográfico no respondió a tiempo.'));},15000);
    this.themeObserver=new MutationObserver(()=>{if(this.base==='local'&&this.map.isStyleLoaded()){this.map.setPaintProperty('background','background-color',isDark()?'#0b1b27':'#e6eff3');this.refresh();}else if(this.base==='streets'){this.setStreets(true);}});
    this.themeObserver.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  }
  addLayers(){
    if(this.destroyed)return;
    for(const level of ['barrio','comuna']){
      this.map.addSource(level,{type:'geojson',data:collection(this.territories.filter(f=>f.properties.level===level).map(f=>({...f,id:featureID(f)}))),attribution:''});
      this.map.addLayer({id:`${level}-fill`,source:level,type:'fill',paint:{'fill-color':'#a3c8d9','fill-opacity':this.base==='streets'?.58:.95}});
      this.map.addLayer({id:`${level}-line`,source:level,type:'line',paint:{'line-color':isDark()?'#9cbac9':'#527b8d','line-width':level==='comuna'?1.5:.8}});
      this.map.addLayer({id:`${level}-selected-halo`,source:level,type:'line',paint:{'line-color':'#fff','line-width':7},filter:['==',['get','id'],'']});
      this.map.addLayer({id:`${level}-selected`,source:level,type:'line',paint:{'line-color':'#123b51','line-width':3},filter:['==',['get','id'],'']});
    }
    this.map.addSource('services',{type:'geojson',data:collection([]),cluster:true,clusterRadius:30,clusterMaxZoom:13});
    this.map.addLayer({id:'clusters',type:'circle',source:'services',filter:['has','point_count'],paint:{'circle-color':isDark()?'#ffac83':'#9b351e','circle-opacity':.88,'circle-radius':['step',['get','point_count'],13,10,17,50,21,150,26],'circle-stroke-width':2,'circle-stroke-color':isDark()?'#142a39':'#fff'}});
    this.map.addLayer({id:'points',type:'circle',source:'services',filter:['!',['has','point_count']],paint:{'circle-color':isDark()?'#ffac83':'#9b351e','circle-radius':['interpolate',['linear'],['zoom'],10,3.5,14,5,17,7],'circle-stroke-width':1.5,'circle-stroke-color':isDark()?'#142a39':'#fff'}});
    this.makeLabels();this.analysis?.mount();
  }
  update({level,territory,records,stats}){this.actionToken++;this.level=level;this.selected=territory;this.records=records;this.stats=stats;this.refresh();}
  refresh(){
    if(this.destroyed||!this.map.getSource('services'))return;
    if(this.analysis?.active){this.analysis.refresh();return;}
    const colors=palette();const vals=this.territories.filter(f=>f.properties.level===this.level).map(f=>this.stats?.rows.get(featureID(f))?.rate);const scale=scaleFor(vals);
    for(const level of ['barrio','comuna']){
      const visibility=this.level===level?'visible':'none';
      for(const suffix of ['fill','line','selected-halo','selected'])this.map.setLayoutProperty(`${level}-${suffix}`,'visibility',visibility);
      const expr=['match',['get','id']];for(const f of this.territories.filter(x=>x.properties.level===level)){expr.push(featureID(f),this.stats?.rows.get(featureID(f))?.rate??-1);}expr.push(-1);
      this.map.setPaintProperty(`${level}-fill`,'fill-color',['case',['<',expr,0],isDark()?'#3c4851':'#d6dce0',['interpolate',['linear'],expr,...scale.thresholds.flatMap((t,i)=>[t,colors[i]])]]);
      this.map.setPaintProperty(`${level}-fill`,'fill-opacity',this.base==='streets'?.58:.95);
      this.map.setPaintProperty(`${level}-line`,'line-color',isDark()?'#9cbac9':'#527b8d');
      this.map.setPaintProperty(`${level}-selected`,'line-color','#123b51');
      this.map.setFilter(`${level}-selected-halo`,['==',['get','id'],this.selected]);
      this.map.setFilter(`${level}-selected`,['==',['get','id'],this.selected]);
    }
    this.map.getSource('services').setData(collection(this.records.filter(hasPoint)));
    for(const layer of ['clusters','points']){this.map.setPaintProperty(layer,'circle-color',isDark()?'#ffac83':'#9b351e');this.map.setPaintProperty(layer,'circle-stroke-color',isDark()?'#142a39':'#fff');}
    this.scheduleLabels();
  }
  makeLabels(){
    this.labels.forEach(x=>x.marker.remove());this.labels=[];
    for(const f of this.territories){
      const center=f.properties.center;if(!Array.isArray(center))continue;
      const el=document.createElement('span');el.className='mt-map-label';el.textContent=f.properties.name;el.setAttribute('aria-hidden','true');
      const marker=new this.gl.Marker({element:el,anchor:'center'}).setLngLat(center).addTo(this.map);
      this.labels.push({feature:f,el,marker});
    }
    this.scheduleLabels();
  }
  scheduleLabels(){if(this.labelsScheduled)return;this.labelsScheduled=true;requestAnimationFrame(()=>{this.labelsScheduled=false;this.updateLabels();});}
  updateLabels(){
    if(this.destroyed)return;
    const rects=[],width=this.map.getContainer().clientWidth,height=this.map.getContainer().clientHeight;
    const labels=[...this.labels].sort((a,b)=>(featureID(b.feature)===this.selected)-(featureID(a.feature)===this.selected));
    for(const {feature,el} of labels){
      const selected=featureID(feature)===this.selected;el.dataset.selected=String(selected);
      if((this.analysis?.active&&this.analysis.view==='3d')||feature.properties.level!==this.level){el.style.visibility='hidden';continue;}
      const p=this.map.project(feature.properties.center);const w=Math.min(150,feature.properties.name.length*6+13),h=20;const r={x:p.x-w/2,y:p.y-h/2,w,h};
      const collision=rects.some(a=>r.x<a.x+a.w+4&&r.x+r.w+4>a.x&&r.y<a.y+a.h+3&&r.y+r.h+3>a.y);
      const visible=p.x>=10&&p.x<=width-10&&p.y>=10&&p.y<=height-10&&(selected||!collision);
      el.style.visibility=visible?'visible':'hidden';if(visible)rects.push(r);
    }
  }
  async pick(e){
    if(this.analysis?.active){this.analysis.pick(e);return;}
    const token=++this.actionToken;
    const layers=['clusters','points',`${this.level}-fill`].filter(id=>this.map.getLayer(id));
    const hits=this.map.queryRenderedFeatures(e.point,{layers});const hit=hits[0];if(!hit)return;
    if(hit.layer.id==='clusters'){try{const zoom=await this.map.getSource('services').getClusterExpansionZoom(hit.properties.cluster_id);if(token!==this.actionToken||this.destroyed||this.analysis?.active)return;this.map.easeTo({center:hit.geometry.coordinates,zoom,duration:this.duration()});}catch{}return;}
    if(hit.layer.id==='points'){const record=this.records.find(f=>featureID(f)===String(hit.properties.id));if(record)this.onRecord(record);return;}
    this.onTerritory(String(hit.properties.id));
  }
  duration(){return matchMedia('(prefers-reduced-motion: reduce)').matches?0:350;}
  fit(feature){this.actionToken++;this.analysis?.stopOrbit();const three=this.analysis?.active&&this.analysis.view==='3d';this.map.fitBounds(feature?boundsFor(feature):CABA,{padding:three?70:35,maxZoom:three?12:14,pitch:three?48:0,bearing:three?-22:0,duration:this.duration()});}
  focusRecord(feature){this.actionToken++;if(hasPoint(feature))this.map.easeTo({center:feature.geometry.coordinates,zoom:15,duration:this.duration()});}
  async setStreets(enabled){
    const token=++this.baseToken;clearTimeout(this.baseTimer);
    if(!enabled){this.base='local';this.map.setStyle(localStyle());this.onBaseStatus('Base territorial local · sin teselas externas',false);return;}
    this.onBaseStatus('Cargando calles de OpenFreeMap…',true);
    try{
      const response=await fetch(`https://tiles.openfreemap.org/styles/${isDark()?'dark':'positron'}`,{signal:AbortSignal.timeout(8000),credentials:'omit',referrerPolicy:'no-referrer'});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      const style=await response.json();if(token!==this.baseToken||this.destroyed)return;
      this.base='streets';this.map.setStyle(style);
      this.baseTimer=setTimeout(()=>{if(token===this.baseToken&&!this.map.areTilesLoaded())this.setStreets(false);},15000);
      this.map.once('idle',()=>{if(token===this.baseToken){clearTimeout(this.baseTimer);this.onBaseStatus('Calles: OpenFreeMap · OpenMapTiles · OpenStreetMap. El inventario conserva su propia fuente.',true);}});
    }catch{if(token===this.baseToken){this.base='local';this.map.setStyle(localStyle());this.onBaseStatus('La base de calles no está disponible. Conservamos la cartografía local.',false);}}
  }
  destroy(){this.analysis?.destroy();this.destroyed=true;this.actionToken++;this.baseToken++;clearTimeout(this.startupTimer);clearTimeout(this.baseTimer);this.themeObserver.disconnect();this.labels.forEach(x=>x.marker.remove());this.map.remove();}
}
