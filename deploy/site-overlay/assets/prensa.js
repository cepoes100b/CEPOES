(function(){
  const esc=s=>String(s??'').replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const card=n=>`<a class="press-card" href="/prensa/${n.slug}/"><span class="press-tag">${esc(n.topic)}</span><h2>${esc(n.title)}</h2><p>${esc(n.summary)}</p><span class="press-meta"><span>${new Date(n.published_at).toLocaleDateString('es-AR')}</span><span>·</span><span>Fuente verificable</span></span></a>`;
  const url='https://nriexnijkjamrmfivfmd.supabase.co/rest/v1/press_notes?select=slug,topic,title,summary,published_at&status=eq.publicada&order=published_at.desc';
  fetch(url,{headers:{apikey:'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq'}}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(notes=>{const el=document.getElementById('press-list');if(el)el.innerHTML=notes.map(card).join('')}).catch(()=>{fetch('/assets/data/prensa.json?v=1').then(r=>r.json()).then(d=>{const el=document.getElementById('press-list');if(el)el.innerHTML=d.notas.filter(n=>n.estado==='aprobada').map(n=>card({slug:n.slug,topic:n.tema,title:n.titulo,summary:n.bajada,published_at:n.fecha+'T12:00:00'})).join('')})});
})();
