(() => {
  const root = document.querySelector("[data-sm-page]");
  if (!root) return;
  const DATA_URL = "/assets/data/salud-mental.json";
  const COMMUNES_URL = "/assets/data/estructura-productiva/comunas.geojson";
  const fmtInt = n => new Intl.NumberFormat("es-AR", {maximumFractionDigits:0}).format(Number(n));
  const fmt = (n,d=2) => new Intl.NumberFormat("es-AR", {minimumFractionDigits:d,maximumFractionDigits:d}).format(Number(n));
  const pct = n => `${Number(n) >= 0 ? "+" : ""}${fmt(n,1)}%`;
  const text = (id, value) => { const el=document.getElementById(id); if(el) el.textContent=value; };
  const ns = "http://www.w3.org/2000/svg";
  function svgEl(name, attrs={}) {
    const el=document.createElementNS(ns,name);
    Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));
    return el;
  }
  function drawSeries(data) {
    const svg=document.getElementById("sm-series-chart");
    if(!svg) return;
    const arg=data.series.argentina_snic||[], caba=data.series.caba_snic||[];
    const years=[...new Set([...arg,...caba].map(x=>Number(x.anio)))].sort();
    const vals=[...arg,...caba].map(x=>Number(x.tasa_100k_mayores_5)).filter(Number.isFinite);
    const min=Math.floor(Math.min(...vals)-1), max=Math.ceil(Math.max(...vals)+1);
    const W=920,H=430,L=58,R=24,T=28,B=48, pw=W-L-R, ph=H-T-B;
    const x=y=>L+(years.indexOf(Number(y))/(years.length-1))*pw;
    const yy=v=>T+(max-Number(v))/(max-min)*ph;
    svg.innerHTML="";
    for(let v=min;v<=max;v+=2){
      const y=yy(v);
      svg.append(svgEl("line",{x1:L,y1:y,x2:W-R,y2:y,class:"sm-gridline"}));
      const lab=svgEl("text",{x:L-10,y:y+4,"text-anchor":"end",class:"sm-axis-label"}); lab.textContent=fmt(v,0); svg.append(lab);
    }
    years.forEach(y=>{
      const lab=svgEl("text",{x:x(y),y:H-18,"text-anchor":"middle",class:"sm-axis-label"}); lab.textContent=y; svg.append(lab);
    });
    const pathFor=arr=>arr.map((p,i)=>`${i?"L":"M"}${x(p.anio)},${yy(p.tasa_100k_mayores_5)}`).join(" ");
    [["arg",arg],["caba",caba]].forEach(([key,arr])=>{
      svg.append(svgEl("path",{d:pathFor(arr),class:`sm-series-${key}`}));
      arr.forEach(p=>{
        const c=svgEl("circle",{cx:x(p.anio),cy:yy(p.tasa_100k_mayores_5),r:4,class:`sm-point-${key}`});
        const title=svgEl("title"); title.textContent=`${key==="arg"?"Argentina":"CABA"} ${p.anio}: ${fmt(p.tasa_100k_mayores_5)} por 100.000`; c.append(title); svg.append(c);
      });
    });
  }
  function renderJurisdictions(data){
    const box=document.getElementById("sm-jurisdiction-bars");
    if(!box) return;
    const rows=[...(data.jurisdicciones_2025||[])].sort((a,b)=>Number(b.tasa_100k_mayores_5_2025)-Number(a.tasa_100k_mayores_5_2025));
    const max=Math.max(...rows.map(x=>Number(x.tasa_100k_mayores_5_2025)));
    box.innerHTML="";
    rows.forEach(r=>{
      const name=String(r.provincia||"");
      const norm=name.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
      const row=document.createElement("div");
      row.className="sm-jur-row"+(norm.includes("ciudad autonoma")?" is-caba":"")+(norm==="buenos aires"?" is-pba":"");
      row.innerHTML=`<span class="sm-jur-name">${name}</span><span class="sm-jur-track"><span class="sm-jur-fill" style="width:${(Number(r.tasa_100k_mayores_5_2025)/max*100).toFixed(1)}%"></span></span><b class="sm-jur-value">${fmt(r.tasa_100k_mayores_5_2025)}</b>`;
      if(r.advertencia) row.title="Ruptura de serie 2025: ver advertencia metodológica";
      box.append(row);
    });
  }
  function parsePoint(s){
    const m=String(s||"").match(/POINT\s*\(\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*\)/i);
    return m ? {lon:Number(m[1]),lat:Number(m[2])}:null;
  }
  function communeNumber(v){
    const m=String(v||"").match(/(\d{1,2})/); return m?m[1]:"";
  }
  function geometryRings(geometry){
    if(!geometry) return [];
    if(geometry.type==="Polygon") return [geometry.coordinates];
    if(geometry.type==="MultiPolygon") return geometry.coordinates;
    return [];
  }
  function featurePoints(feature){
    const out=[];
    geometryRings(feature?.geometry).forEach(poly=>poly.forEach(ring=>ring.forEach(([lon,lat])=>{
      lon=Number(lon); lat=Number(lat);
      if(Number.isFinite(lon)&&Number.isFinite(lat)) out.push([lon,lat]);
    })));
    return out;
  }
  function renderCesac(data, communes){
    const items=(data.red_atencion_caba?.cesac_con_salud_mental||[]).map(x=>({...x,pt:parsePoint(x.geometry),cn:communeNumber(x.comuna)}));
    text("sm-cesac-summary",`${items.length} CeSAC con Psicología y/o Psiquiatría en la cartera oficial publicada.`);
    const select=document.getElementById("sm-cesac-comuna"), list=document.getElementById("sm-cesac-list"), svg=document.getElementById("sm-cesac-map");
    if(!select||!list||!svg) return;
    const features=(communes?.features||[]).filter(f=>Number.isFinite(Number(f?.properties?.comuna)));
    if(features.length!==15) throw new Error(`GeoJSON de comunas inválido: ${features.length} features`);
    [...new Set(items.map(x=>x.cn).filter(Boolean))].sort((a,b)=>Number(a)-Number(b)).forEach(c=>{
      const o=document.createElement("option"); o.value=c; o.textContent=`Comuna ${c}`; select.append(o);
    });
    const W=720,H=520,P=34;
    function makeProjection(targetFeatures){
      const pts=targetFeatures.flatMap(featurePoints);
      if(!pts.length) throw new Error("La geometría seleccionada no tiene coordenadas");
      const lons=pts.map(p=>p[0]), lats=pts.map(p=>p[1]);
      const minLon=Math.min(...lons),maxLon=Math.max(...lons),minLat=Math.min(...lats),maxLat=Math.max(...lats);
      const midLat=(minLat+maxLat)/2, xFactor=Math.cos(midLat*Math.PI/180);
      const spanX=Math.max((maxLon-minLon)*xFactor,1e-9), spanY=Math.max(maxLat-minLat,1e-9);
      const scale=Math.min((W-2*P)/spanX,(H-2*P)/spanY)*.93;
      const cx=(minLon+maxLon)/2, cy=(minLat+maxLat)/2;
      return ([lon,lat])=>({x:W/2+(Number(lon)-cx)*xFactor*scale,y:H/2-(Number(lat)-cy)*scale});
    }
    function pathForFeature(feature,project){
      const chunks=[];
      geometryRings(feature.geometry).forEach(poly=>poly.forEach(ring=>{
        const pts=ring.map(project);
        if(pts.length) chunks.push(`M${pts.map(p=>`${p.x.toFixed(2)},${p.y.toFixed(2)}`).join("L")}Z`);
      }));
      return chunks.join(" ");
    }
    function labelPoint(feature,project){
      const pts=featurePoints(feature);
      const lon=pts.reduce((a,p)=>a+p[0],0)/pts.length;
      const lat=pts.reduce((a,p)=>a+p[1],0)/pts.length;
      return project([lon,lat]);
    }
    function paint(){
      const c=select.value;
      const selectedFeature=c ? features.find(f=>String(f.properties.comuna)===String(c)) : null;
      const mapFeatures=selectedFeature ? [selectedFeature] : features;
      const shown=items.filter(x=>!c||x.cn===c);
      const project=makeProjection(mapFeatures);
      svg.innerHTML="";
      svg.append(svgEl("rect",{x:1,y:1,width:W-2,height:H-2,rx:16,class:"sm-map-background"}));
      mapFeatures.slice().sort((a,b)=>Number(a.properties.comuna)-Number(b.properties.comuna)).forEach(feature=>{
        const comuna=String(feature.properties.comuna);
        const path=svgEl("path",{d:pathForFeature(feature,project),class:`sm-map-commune${c&&comuna===String(c)?" is-selected":""}`,"fill-rule":"evenodd","data-comuna":comuna});
        const title=svgEl("title");
        title.textContent=`Comuna ${comuna}${feature.properties.barrios?` · ${feature.properties.barrios}`:""}`;
        path.append(title); svg.append(path);
      });
      mapFeatures.forEach(feature=>{
        const p=labelPoint(feature,project);
        const label=svgEl("text",{x:p.x,y:p.y+4,"text-anchor":"middle",class:`sm-map-label${c?" is-selected":""}`});
        label.textContent=c?`Comuna ${feature.properties.comuna}`:String(feature.properties.comuna);
        svg.append(label);
      });
      shown.filter(x=>x.pt).forEach(x=>{
        const p=project([x.pt.lon,x.pt.lat]);
        const circle=svgEl("circle",{cx:p.x,cy:p.y,r:c?7:5,class:"sm-map-point"});
        const title=svgEl("title"); title.textContent=`${x.nombre} · ${x.barrio} · ${x.comuna}`;
        circle.append(title); svg.append(circle);
      });
      list.innerHTML="";
      shown.sort((a,b)=>String(a.nombre).localeCompare(String(b.nombre),"es")).forEach(x=>{
        const d=document.createElement("div"); d.className="sm-cesac-item";
        d.innerHTML=`<strong>${x.nombre}</strong><span>${x.direccion} · ${x.barrio} · ${x.comuna}</span><small>${x.telefono||"Sin teléfono publicado"}</small>${x.web?`<a href="${x.web}" target="_blank" rel="noopener">Ficha oficial ↗</a>`:""}`;
        list.append(d);
      });
    }
    select.addEventListener("change",paint);
    paint();
  }
  async function init(){
    try{
      const [r,g]=await Promise.all([
        fetch(DATA_URL,{cache:"no-store"}),
        fetch(COMMUNES_URL,{cache:"no-store"})
      ]);
      if(!r.ok) throw new Error(`Salud mental HTTP ${r.status}`);
      if(!g.ok) throw new Error(`Comunas HTTP ${g.status}`);
      const d=await r.json();
      const communes=await g.json();
      if(d.schema!=="cepoes-salud-mental-v3"||d.status!=="VALIDADO") throw new Error("dataset no validado");
      const a=d.headline.argentina,c=d.headline.caba;
      text("sm-arg-count",fmtInt(a.suicidios_snic)); text("sm-arg-rate",fmt(a.tasa_100k_mayores_5)); text("sm-arg-change",pct(a.variacion_anual_pct));
      text("sm-caba-count",fmtInt(c.suicidios_snic)); text("sm-caba-rate",fmt(c.tasa_100k_mayores_5)); text("sm-caba-change",pct(c.variacion_anual_pct));
      const dt=new Date(d.generated_at); if(!Number.isNaN(dt.valueOf())) text("sm-generated-at",dt.toLocaleDateString("es-AR",{day:"numeric",month:"long",year:"numeric"}));
      drawSeries(d); renderJurisdictions(d); renderCesac(d, communes);
    }catch(err){
      console.error("Salud mental:",err);
      const box=document.getElementById("sm-cesac-list");
      if(box) box.insertAdjacentHTML("afterbegin",'<p><b>No se pudo actualizar la capa interactiva.</b> Se mantienen visibles los últimos valores validados incluidos en la página.</p>');
    }
  }
  init();
})();