(()=>{'use strict';
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const statusLabel={pendiente:'Pendiente',relevar:'A relevar',cumplido:'Cumplido',parcial:'Parcial',incumplido:'Incumplido'};
const fmt=n=>new Intl.NumberFormat('es-AR').format(n);
async function init(){
  try{
    const r=await fetch('/assets/data/analgesia-peridural.json?v=20260827',{cache:'no-store'});
    if(!r.ok)throw Error(r.status);
    const d=await r.json();
    const updated=$('[data-monitor-updated]'); if(updated)updated.textContent=`Actualización: ${new Date(d.updated_at+'T12:00:00').toLocaleDateString('es-AR',{day:'numeric',month:'long',year:'numeric'})}`;
    const rows=$('#implementation-rows');
    if(rows)rows.innerHTML=d.implementation_indicators.map(x=>`<tr><th scope="row">${esc(x.label)}</th><td><span class="monitor-status is-${esc(x.status)}">${esc(statusLabel[x.status]||x.status)}</span></td><td>${esc(x.value)}</td></tr>`).join('');
    const births=$('#birth-bars');
    if(births){
      const max=Math.max(...d.context.births_public_maternities.map(x=>x.value));
      births.innerHTML=d.context.births_public_maternities.map(x=>`<div class="birth-row"><span>${x.year}</span><div><i style="width:${(x.value/max*100).toFixed(1)}%"></i></div><strong>${fmt(x.value)}</strong></div>`).join('');
    }
    const hospitals=$('#maternity-list');
    if(hospitals)hospitals.innerHTML=d.maternities.map(x=>`<li>${esc(x)}</li>`).join('');
  }catch(e){
    const warning=$('#monitor-load-warning');
    if(warning){warning.hidden=false;warning.textContent='No se pudo refrescar el archivo de seguimiento. Se muestran los últimos valores incorporados en la página.';}
  }
}
document.addEventListener('DOMContentLoaded',init);
})();
