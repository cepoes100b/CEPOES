import {createClient} from 'npm:@supabase/supabase-js@2.95.0';
const headers={'content-type':'text/html; charset=utf-8','cache-control':'no-store','referrer-policy':'no-referrer','content-security-policy':"default-src 'none'; form-action 'self'; frame-ancestors 'none'"};
Deno.serve(async req=>{
 try {
  const url=new URL(req.url),id=url.searchParams.get('id')||'',token=url.searchParams.get('token')||'';
  if(!/^[a-f0-9-]{36}$/.test(id)||!/^[a-f0-9]{64}$/.test(token))return new Response('Enlace inválido',{status:400,headers});
  const secret=Deno.env.get('NEWSLETTER_UNSUBSCRIBE_SECRET');if(!secret)throw Error('missing_config');
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['verify']);
  const signature=new Uint8Array(token.match(/../g)!.map(x=>parseInt(x,16)));
  if(!await crypto.subtle.verify('HMAC',key,signature,new TextEncoder().encode(id)))return new Response('Enlace inválido',{status:400,headers});
  // GET renders a confirmation: mail scanners must not unsubscribe readers.
  if(req.method==='GET')return new Response('<h1>Baja de las novedades de CEPOES</h1><form method="post"><button type="submit">Confirmar baja</button></form>',{headers});
  if(req.method!=='POST')return new Response('',{status:405,headers});
  const db=createClient(Deno.env.get('SUPABASE_URL')!,Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);
  const r=await db.from('newsletter_subscriptions').update({status:'unsubscribed'}).eq('id',id);if(r.error)throw Error('database_failed');
  return new Response('<h1>Suscripción dada de baja</h1><p>Ya no recibirás publicaciones ni avisos de CEPOES.</p>',{headers});
 }catch {return new Response('No se pudo completar la baja. Intentá nuevamente.',{status:503,headers});}
});
