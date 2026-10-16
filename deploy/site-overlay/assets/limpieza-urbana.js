/* Explorador de agregados SUACI: cantidades absolutas, sin datos personales. */
(async()=>{'use strict';
 const $=id=>document.getElementById(id),fmt=n=>n.toLocaleString('es-AR'),esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 try{
 const res=await fetch('/assets/data/limpieza-urbana.json');if(!res.ok)throw Error('HTTP '+res.status);const d=await res.json();
 if(d.schema!==1||d.features.length!==48||d.counts.reduce((s,r)=>s+r[4],0)!==d.total)throw Error('Datos inconsistentes');
 const comuna=$('lu-comuna'),barrio=$('lu-barrio'),names=d.features.map(f=>f.name).sort((a,b)=>a.localeCompare(b,'es'));
 const totals=Object.fromEntries(names.map(b=>[b,d.counts.filter(r=>r[0]===b).reduce((s,r)=>s+r[4],0)])),max=Math.max(...Object.values(totals));
 function options(){const prev=barrio.value;barrio.innerHTML='<option value="">Todos los barrios</option>'+names.filter(n=>!comuna.value||d.features.find(f=>f.name===n).comuna===comuna.value).map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join('');if([...barrio.options].some(o=>o.value===prev))barrio.value=prev;}
 options();
 const all=d.features.flatMap(f=>f.rings.flat()),xs=all.map(p=>p[0]),ys=all.map(p=>p[1]),lo=Math.min(...xs),hi=Math.max(...xs),bottom=Math.min(...ys),top=Math.max(...ys),cos=Math.cos(-34.6*Math.PI/180),scale=Math.min(600/((hi-lo)*cos),600/(top-bottom)),width=(hi-lo)*cos*scale,height=(top-bottom)*scale;
 const project=p=>[(650-width)/2+(p[0]-lo)*cos*scale,(650-height)/2+(top-p[1])*scale];
 for(const f of d.features){const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',f.rings.map(r=>'M'+r.map(v=>project(v).map(n=>n.toFixed(2)).join(',')).join('L')+'Z').join(''));p.setAttribute('fill',`rgb(${[215,233,233].map((v,i)=>Math.round(v+([8,108,115][i]-v)*totals[f.name]/max)).join(',')})`);p.setAttribute('tabindex','0');p.setAttribute('role','button');p.setAttribute('aria-label',`${f.name}, comuna ${f.comuna}: ${fmt(totals[f.name])} reclamos`);p.dataset.barrio=f.name;const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=`${f.name}: ${fmt(totals[f.name])} reclamos`;p.append(title);const select=()=>{comuna.value='';options();barrio.value=f.name;render();};p.addEventListener('click',select);p.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select();}});$('lu-map').append(p);}
 $('lu-scale').textContent=`0 → ${fmt(max)} reclamos · escala fija`;
 const months=[...new Set(d.counts.map(r=>r[2]))].sort(),monthLabel=m=>new Intl.DateTimeFormat('es-AR',{month:'short',year:'2-digit',timeZone:'UTC'}).format(new Date(m+'-01T12:00:00Z')).replace(' de ',' ');
 const labels={'INSTALACION/REPARACION DE CONTENEDOR':'Instalación o reparación','LIMPIEZA/VACIADO DE CONTENEDOR':'Limpieza o vaciado','RECOLECCION DE RESIDUOS FUERA DEL CONTENEDOR':'Residuos fuera del contenedor','REPOSICION DE CONTENEDOR':'Reposición','REPOSICION/REUBICACION DE CONTENEDOR':'Reposición o reubicación'};
 function render(){const rows=d.counts.filter(r=>(!comuna.value||r[1]===comuna.value)&&(!barrio.value||r[0]===barrio.value)),total=rows.reduce((s,r)=>s+r[4],0),scope=barrio.value||(comuna.value?'Comuna '+comuna.value:'Toda CABA');
 $('lu-total').textContent=fmt(total);$('lu-scope').textContent=scope;$('lu-status').textContent=`${scope}: ${fmt(total)} contactos · mayo 2025 a abril 2026`;
 $('lu-types').innerHTML=d.types.map(t=>[t,rows.filter(r=>r[3]===t).reduce((s,r)=>s+r[4],0)]).sort((a,b)=>b[1]-a[1]).map(([t,n])=>`<div class="lu-type"><div><span>${esc(labels[t]||t)}</span><strong>${fmt(n)} · ${total?(n/total*100).toFixed(1).replace('.',','):0}%</strong></div><i style="width:${total?n/total*100:0}%"></i></div>`).join('');
 const series=months.map(m=>[m,rows.filter(r=>r[2]===m).reduce((s,r)=>s+r[4],0)]),peak=Math.max(...series.map(r=>r[1]),1),p=series.find(r=>r[1]===peak);
 $('lu-peak').textContent=p?`Pico: ${monthLabel(p[0])} · ${fmt(p[1])}`:'Sin registros';
 $('lu-months').innerHTML=series.map(([m,n])=>`<div class="lu-month" role="listitem" aria-label="${esc(monthLabel(m))}: ${fmt(n)}"><b>${fmt(n)}</b><i style="height:${n/peak*170}px" aria-hidden="true"></i><span>${esc(monthLabel(m))}</span></div>`).join('');
 $('lu-month-table').innerHTML='<table><thead><tr><th>Mes</th><th>Reclamos</th></tr></thead><tbody>'+series.map(([m,n])=>`<tr><td>${esc(monthLabel(m))}</td><td>${fmt(n)}</td></tr>`).join('')+'</tbody></table>';
 const bs=new Map();for(const r of rows){const key=r[0]+'|'+r[1];bs.set(key,(bs.get(key)||0)+r[4]);}
 $('lu-ranking').innerHTML=[...bs].sort((a,b)=>b[1]-a[1]).map(([key,n])=>{const [b,c]=key.split('|');return `<tr><td>${esc(b||'Sin barrio informado')}</td><td>${esc(c||'—')}</td><td>${fmt(n)}</td></tr>`;}).join('');
 $('lu-streets').innerHTML=d.topStreets.filter(r=>(!comuna.value||r[1]===comuna.value)&&(!barrio.value||r[0]===barrio.value)).sort((a,b)=>b[3]-a[3]).slice(0,10).map(r=>`<div class="lu-street"><span>${esc(r[2])}<small>${esc(r[0]||'Sin barrio informado')}</small></span><b>${fmt(r[3])}</b></div>`).join('')||'<p>Sin cuadras identificadas.</p>';
 for(const p of $('lu-map').querySelectorAll('path')){const selected=barrio.value?p.dataset.barrio===barrio.value:comuna.value?d.features.find(f=>f.name===p.dataset.barrio).comuna===comuna.value:false;p.setAttribute('aria-pressed',String(selected));p.style.opacity=(comuna.value||barrio.value)&&!selected?'.3':'1';}
 }
 comuna.addEventListener('change',()=>{barrio.value='';options();render();});barrio.addEventListener('change',render);$('lu-reset').addEventListener('click',()=>{comuna.value='';options();barrio.value='';render();});render();
 }catch(error){$('lu-status').classList.add('lu-error');$('lu-status').innerHTML='No pudimos cargar los datos. <a href="">Volver a intentar</a>. El alcance y las fuentes se encuentran al final de la página.';console.error('Limpieza urbana:',error.message);}
})();
