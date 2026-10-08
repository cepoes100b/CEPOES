document.addEventListener('DOMContentLoaded',()=>{
  const track=document.getElementById('home-publications-track');
  if(track){
    const cards=[...track.children],position=document.getElementById('home-publications-position');
    const current=()=>cards.reduce((best,c,i)=>Math.abs(c.offsetLeft-track.offsetLeft-track.scrollLeft)<Math.abs(cards[best].offsetLeft-track.offsetLeft-track.scrollLeft)?i:best,0);
    document.querySelectorAll('[data-home-slide]').forEach(button=>button.addEventListener('click',()=>{
      const i=Math.max(0,Math.min(cards.length-1,current()+Number(button.dataset.homeSlide)));
      track.scrollTo({left:cards[i].offsetLeft-track.offsetLeft,behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
    }));
    track.addEventListener('scroll',()=>{position.textContent=`${current()+1} de ${cards.length}`;},{passive:true});
  }
  const neighborhoodForm=document.getElementById('home-neighborhood-form');
  const neighborhood=document.getElementById('home-neighborhood');
  if(neighborhoodForm&&neighborhood) neighborhoodForm.addEventListener('submit',event=>{
    event.preventDefault();
    if(neighborhood.value) location.href=`/territorio/barrios/${encodeURIComponent(neighborhood.value)}/`;
  });

});

// Keep subscription independent from optional carousel/navigation components.
document.addEventListener('DOMContentLoaded',()=>{
  const form=document.getElementById('home-subscription-form');
  const status=document.getElementById('home-subscription-status');
  if(!form||!status)return;
  let widget, token='', config;
  const failMessage='No pudimos cargar la verificación de seguridad. Recargá la página y volvé a intentar. Si continúa, escribinos a contacto@cepoes.org.';
  const timedFetch=(url,options={})=>{
    const controller=new AbortController();
    const timer=setTimeout(()=>controller.abort(),12000);
    return fetch(url,{...options,signal:controller.signal}).finally(()=>clearTimeout(timer));
  };
  form.addEventListener('invalid',event=>{
    status.textContent=event.target.name==='consent'?'Marcá la casilla de aceptación para suscribirte.':'Ingresá un correo electrónico válido para suscribirte.';
  },true);
  const result=new URLSearchParams(location.search).get('suscripcion');
  if(result==='confirmed')status.textContent='Tu correo quedó confirmado. Recibirás los próximos boletines de CEPOES.';
  if(result==='invalid')status.textContent='El enlace venció o ya fue utilizado. Podés solicitar otro desde este formulario.';
  const ready=timedFetch('/assets/data/newsletter-config.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('config');return r.json();}).then(async c=>{
    config=c;if(c.enabled!==true)return;
    if(!c.turnstile_site_key)throw Error('site_key');
    await new Promise((resolve,reject)=>{
      const script=document.createElement('script');script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      const timer=setTimeout(()=>reject(Error('challenge_timeout')),12000);
      script.onload=()=>{clearTimeout(timer);resolve();};
      script.onerror=()=>{clearTimeout(timer);reject(Error('challenge_load'));};
      document.head.appendChild(script);
    });
    const challenge=document.createElement('div');challenge.setAttribute('aria-label','Verificación de seguridad');form.querySelector('.home-consent').after(challenge);
    widget=window.turnstile.render(challenge,{sitekey:c.turnstile_site_key,action:'newsletter_subscribe',callback:t=>{token=t;},'expired-callback':()=>{token='';status.textContent='La verificación venció. Completala nuevamente antes de suscribirte.';},'error-callback':()=>{token='';status.textContent=failMessage;}});
  }).catch(()=>{config=null;status.textContent=failMessage;});
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if(form.elements.company.value){status.textContent='No pudimos validar el formulario. Recargá la página y escribí tu correo manualmente. Si continúa, escribinos a contacto@cepoes.org.';return;}
    const button=form.querySelector('button[type="submit"]');
    button.disabled=true;status.textContent='Procesando tu solicitud…';
    try{
      await ready;
      if(!config){status.textContent=failMessage;return;}
      if(config.enabled!==true){status.textContent='La suscripción está temporalmente en mantenimiento. Podés escribirnos a contacto@cepoes.org.';return;}
      if(!token){status.textContent='Completá la verificación de seguridad antes de continuar.';return;}
      const response=await timedFetch('https://nriexnijkjamrmfivfmd.supabase.co/functions/v1/newsletter-subscribe',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({email:String(form.elements.email.value).trim().toLowerCase(),consent:form.elements.consent.checked,company:'',turnstile_token:token})
      });
      if(response.ok){form.reset();status.textContent='Revisá tu correo para confirmar la suscripción, incluida la carpeta de spam. Si ya estaba confirmada, no recibirás otro mensaje.';}
      else if(response.status===429){status.textContent='Hubo demasiados intentos. Volvé a probar en una hora.';}
      else throw Error('subscription_failed');
    }catch{status.textContent='No pudimos completar la solicitud. Probá nuevamente o escribinos a contacto@cepoes.org.';}
    finally{button.disabled=false;token='';if(widget!==undefined&&window.turnstile){try{window.turnstile.reset(widget);}catch{status.textContent=failMessage;}}}
  });
});
