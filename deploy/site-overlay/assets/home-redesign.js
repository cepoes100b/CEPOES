document.addEventListener('DOMContentLoaded',()=>{
  const neighborhoodForm=document.getElementById('home-neighborhood-form');
  const neighborhood=document.getElementById('home-neighborhood');
  if(neighborhoodForm&&neighborhood) neighborhoodForm.addEventListener('submit',event=>{
    event.preventDefault();
    if(neighborhood.value) location.href=`/territorio/barrios/${encodeURIComponent(neighborhood.value)}/`;
  });

  const form=document.getElementById('home-subscription-form');
  const status=document.getElementById('home-subscription-status');
  if(!form||!status)return;
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if(form.elements.company.value)return;
    const button=form.querySelector('button[type="submit"]');
    button.disabled=true;status.textContent='Guardando tu suscripción…';
    try{
      const response=await fetch('https://nriexnijkjamrmfivfmd.supabase.co/rest/v1/newsletter_subscriptions',{
        method:'POST',
        headers:{'apikey':'sb_publishable_i2WWiop8sCom0yVZZ7xC8g_NGJCiddq','Content-Type':'application/json','Prefer':'return=minimal'},
        body:JSON.stringify({email:String(form.elements.email.value).trim().toLowerCase(),source:'home',privacy_version:'2026-08'})
      });
      if(response.ok){form.reset();status.textContent='Listo. Te sumamos a las novedades de CEPOES.';}
      else if(response.status===409){status.textContent='Ese correo ya estaba suscripto.';}
      else throw new Error(String(response.status));
    }catch(error){status.textContent='No pudimos guardar la suscripción. Podés escribirnos a contacto@cepoes.org.';}
    finally{button.disabled=false;}
  });
});
