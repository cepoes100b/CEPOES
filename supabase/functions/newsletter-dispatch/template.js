// Table layout and inline styles keep the editorial identity in email clients.
export const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function validateContent(content) {
  if(content==null)return null;
  const string=(v,max)=>{if(typeof v!=='string'||v.length>max)throw Error('invalid_email_content');return v;};
  const list=(v,max)=>{if(!Array.isArray(v)||v.length>max)throw Error('invalid_email_content');return v;};
  return {date:string(content.date,80),intro:string(content.intro,2000),
    metrics:list(content.metrics,3).map(x=>({value:string(x.value,80),label:string(x.label,300),source:string(x.source,400)})),
    sections:list(content.sections,4).map(x=>({title:string(x.title,300),body:string(x.body,900),source:string(x.source,800)})),
    agenda:list(content.agenda,5).map(x=>string(x,600))};
}
export function newsletterEmail(edition,unsubscribe) {
  const e=escapeHtml,url='https://cepoes.org'+edition.url;
  const content=validateContent(edition.email_content)||{date:'',intro:edition.summary,metrics:[],sections:[],agenda:[]};
  const paragraph=(text,extra='')=>`<p style="margin:0 0 16px;font-size:16px;line-height:1.65;color:#263c45;${extra}">${e(text)}</p>`;
  const metrics=content.metrics.map(m=>`<tr><td width="112" valign="top" style="padding:18px 12px 18px 0;border-bottom:1px solid #dce7e8;font-size:28px;font-weight:bold;color:#0b485a;line-height:1.2">${e(m.value)}</td><td style="padding:18px 0;border-bottom:1px solid #dce7e8;font-size:15px;line-height:1.45;color:#263c45"><strong>${e(m.label)}</strong><br><span style="font-size:12px;color:#526771">${e(m.source)}</span></td></tr>`).join('');
  const sections=content.sections.map((s,i)=>`<tr><td style="padding:26px 24px 4px;border-bottom:1px solid #e1e8eb"><p style="margin:0 0 9px;font-size:12px;font-weight:bold;letter-spacing:2px;color:#137b80">0${i+1} / EN ESTE NÚMERO</p><h2 style="margin:0 0 14px;font-size:23px;line-height:1.3;color:#0b485a">${e(s.title)}</h2>${paragraph(s.body)}${s.source?paragraph(s.source,'font-size:12px;color:#526771;'):''}</td></tr>`).join('');
  const agenda=content.agenda.length?`<tr><td style="padding:26px 24px;background:#edf6f4"><h2 style="margin:0 0 14px;color:#0b485a;font-size:22px">Una agenda para los barrios</h2>${paragraph('Las propuestas de este número:')}<ul style="padding-left:20px;margin:0;color:#263c45;font-size:15px;line-height:1.6">${content.agenda.map(x=>`<li style="margin-bottom:9px">${e(x)}</li>`).join('')}</ul></td></tr>`:'';
  const subject=`Boletín CEPOES N.º ${edition.edition}: ${edition.title}`;
  const html=`<!doctype html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${e(subject)}</title></head><body style="margin:0;padding:0;background:#edf1f3;font-family:Arial,Helvetica,sans-serif"><div style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;mso-hide:all">${e(edition.summary)}</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#edf1f3"><tr><td align="center" style="padding:20px 8px">
<!--[if mso]><table role="presentation" width="600" align="center"><tr><td><![endif]-->
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width:600px;background:#ffffff">
<tr><td style="padding:24px;background:#0b485a;border-bottom:5px solid #edb521"><a href="https://cepoes.org/" style="text-decoration:none;font-size:32px;letter-spacing:-1px;font-weight:bold;color:#ffffff">CEP<span style="color:#edb521">OES</span></a><p style="margin:8px 0 0;color:#ffffff;font-size:11px;letter-spacing:1px;line-height:1.5">CENTRO DE ESTUDIOS DE SOMOS 100 BARRIOS</p></td></tr>
<tr><td style="padding:28px 24px;background:#0b485a"><p style="margin:0 0 16px;color:#edb521;font-size:12px;letter-spacing:1px;font-weight:bold">LA CIUDAD QUE HABITAMOS · N.º ${edition.edition}${content.date?' · '+e(content.date.toUpperCase()):''}</p><h1 style="margin:0 0 18px;color:#ffffff;font-size:32px;line-height:1.2">${e(edition.title)}</h1><p style="margin:0;color:#ffffff;font-size:17px;line-height:1.6">${e(content.intro||edition.summary)}</p></td></tr>
${metrics?`<tr><td style="padding:12px 24px 22px;background:#f6f9fa"><h2 style="font-size:13px;letter-spacing:1px;color:#0b485a;margin:10px 0 2px">TRES DATOS PARA ENTENDER LA CIUDAD</h2><table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">${metrics}</table></td></tr>`:''}
${sections}${agenda}
<tr><td align="center" style="padding:30px 24px"><table role="presentation" cellspacing="0" cellpadding="0" border="0"><tr><td align="center" bgcolor="#0b485a" style="background:#0b485a;border-radius:4px"><a href="${url}" style="display:inline-block;padding:17px 22px;color:#ffffff;text-decoration:none;font-size:16px;font-weight:bold;line-height:1.4">Leer el boletín completo →</a></td></tr></table><p style="margin:14px 0 0;color:#526771;font-size:12px;line-height:1.6">Datos, análisis y propuestas desde el territorio.</p></td></tr>
<tr><td style="padding:24px;background:#e7edef;color:#405560;font-size:12px;line-height:1.7"><strong style="color:#0b485a">CEPOES · La Ciudad que habitamos</strong><br>Recibís este correo porque te suscribiste a nuestras publicaciones.<br><a href="https://cepoes.org/" style="color:#0b485a">cepoes.org</a> · <a href="mailto:contacto@cepoes.org" style="color:#0b485a">Contacto</a><br><a href="${e(unsubscribe)}" style="color:#0b485a;text-decoration:underline">Dar de baja mi suscripción</a></td></tr>
</table><!--[if mso]></td></tr></table><![endif]--></td></tr></table></body></html>`;
  const text=[`CEPOES · La Ciudad que habitamos · N.º ${edition.edition}`,content.date,edition.title,content.intro||edition.summary,
    ...content.metrics.map(m=>`${m.value} — ${m.label}. ${m.source}`),
    ...content.sections.map(s=>`${s.title}\n${s.body}\n${s.source}`),
    ...(content.agenda.length?['Una agenda para los barrios',...content.agenda.map(x=>'• '+x)]:[]),
    `Leer el boletín completo: ${url}`,'Recibís este correo porque te suscribiste a nuestras publicaciones.',`Dar de baja mi suscripción: ${unsubscribe}`,'Contacto: contacto@cepoes.org'].filter(Boolean).join('\n\n');
  return {subject,html,text};
}
