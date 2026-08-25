(function(){
  const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const card=n=>`<a class="press-card" href="/prensa/${n.slug}/"><span class="press-tag">${esc(n.tema)}</span><h2>${esc(n.titulo)}</h2><p>${esc(n.bajada)}</p><span class="press-meta"><span>${new Date(n.fecha+'T12:00:00').toLocaleDateString('es-AR')}</span><span>·</span><span>Fuente verificable</span></span></a>`;
  fetch('/assets/data/prensa.json?v=1').then(r=>r.json()).then(d=>{const el=document.getElementById('press-list');if(el)el.innerHTML=d.notas.filter(n=>n.estado==='aprobada').map(card).join('')}).catch(()=>{});
})();
