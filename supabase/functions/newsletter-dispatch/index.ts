import {createClient} from 'npm:@supabase/supabase-js@2.95.0';
import {validateEdition,newsletterEmail,deliverOne} from './logic.js';
const env=(name:string)=>{const v=Deno.env.get(name);if(!v)throw Error('missing_'+name);return v;};
async function sign(id:string){const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env('NEWSLETTER_UNSUBSCRIBE_SECRET')),{name:'HMAC',hash:'SHA-256'},false,['sign']);const value=await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(id));return Array.from(new Uint8Array(value),b=>b.toString(16).padStart(2,'0')).join('');}
Deno.serve(async req=>{
  try {
    if(req.method!=='POST'||req.headers.get('authorization')!==`Bearer ${env('NEWSLETTER_DISPATCH_SECRET')}`)return Response.json({ok:false},{status:401});
    if(Deno.env.get('NEWSLETTER_ENABLED')!=='true')return Response.json({ok:false,reason:'disabled'},{status:503});
    env('RESEND_API_KEY');env('NEWSLETTER_FROM');env('NEWSLETTER_UNSUBSCRIBE_SECRET');
    const db=createClient(env('SUPABASE_URL'),env('SUPABASE_SERVICE_ROLE_KEY'),{auth:{persistSession:false}});
    const rpc=async(name:string,args:unknown)=>{const r=await db.rpc(name,args);if(r.error)throw Error('database_failed');return r.data;};
    const response=await fetch('https://cepoes.org/assets/data/newsletter-editions.json',{signal:AbortSignal.timeout(15000)});
    if(!response.ok)throw Error('published_feed_unavailable');
    const feed=await response.json();if(feed.version!==1||!Array.isArray(feed.editions)||feed.editions.length>200)throw Error('invalid_feed');
    const editions=feed.editions.map(validateEdition).sort((a:any,b:any)=>a.edition-b.edition);
    for(const edition of editions)await rpc('newsletter_enqueue_edition',{p_edition:edition.edition,p_url:edition.url,p_title:edition.title,p_summary:edition.summary});
    const jobs=await rpc('newsletter_claim_deliveries',{p_limit:5});
    let accepted=0,retry=0,cancelled=0;
    for(const job of jobs){
      const {data:edition,error}=await db.from('newsletter_editions').select('*').eq('edition',job.edition).single();if(error)throw Error('edition_missing');
      const result=await deliverOne(job,{
        isActive:async(id:string)=>{const r=await db.from('newsletter_subscriptions').select('status').eq('id',id).single();return !r.error&&r.data.status==='active';},
        send:async(j:any,key:string)=>{
          const {data:s,error}=await db.from('newsletter_subscriptions').select('email').eq('id',j.subscription_id).single();if(error)throw Error('subscriber_missing');
          const unsubscribe=`${env('SUPABASE_URL')}/functions/v1/newsletter-unsubscribe?id=${j.subscription_id}&token=${await sign(j.subscription_id)}`;
          const content=newsletterEmail(edition,unsubscribe);
          const r=await fetch('https://api.resend.com/emails',{method:'POST',signal:AbortSignal.timeout(12000),headers:{authorization:`Bearer ${env('RESEND_API_KEY')}`,'content-type':'application/json','idempotency-key':key},body:JSON.stringify({from:env('NEWSLETTER_FROM'),reply_to:'contacto@cepoes.org',to:[s.email],...content,headers:{'List-Unsubscribe':`<${unsubscribe}>`,'List-Unsubscribe-Post':'List-Unsubscribe=One-Click'}})});
          if(!r.ok)throw Error('provider_failed');return await r.json();
        },
        finish:async(j:any,state:string,id?:string)=>{await rpc('newsletter_finish_delivery',{p_edition:j.edition,p_subscription:j.subscription_id,p_lease:j.lease_token,p_state:state,p_provider_id:id||null});},
        retry:async(j:any)=>{await rpc('newsletter_finish_delivery',{p_edition:j.edition,p_subscription:j.subscription_id,p_lease:j.lease_token,p_state:'pending',p_provider_id:null});}
      });
      if(result==='accepted')accepted++;else if(result==='retry')retry++;else cancelled++;
    }
    const {count:review,error:reviewError}=await db.from('newsletter_deliveries').select('*',{count:'exact',head:true}).eq('state','review');
    if(reviewError)throw Error('review_check_failed');
    return Response.json({ok:true,accepted,retry,cancelled,review});
  }catch {console.error('newsletter_dispatch_failed');return Response.json({ok:false},{status:503});}
});
