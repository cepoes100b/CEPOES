export function validateEdition(item) {
  if (!Number.isInteger(item.edition) || item.edition < 1 || !/^\/publicaciones\/boletines\/boletin-\d+-[a-z]+-\d{4}\/$/.test(item.url)) throw Error('invalid_edition');
  if (!item.title || item.title.length > 300 || typeof item.summary !== 'string' || item.summary.length > 2000) throw Error('invalid_content');
  return {edition:item.edition,url:item.url,title:item.title,summary:item.summary};
}
export const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function newsletterEmail(edition, unsubscribe) {
  const url='https://cepoes.org'+edition.url;
  return {subject:`Boletín CEPOES N.º ${edition.edition}: ${edition.title}`,
    html:`<h1>${escapeHtml(edition.title)}</h1><p>${escapeHtml(edition.summary)}</p><p><a href="${url}">Leer el boletín completo</a></p><hr><p>Recibís este correo porque te suscribiste al boletín de CEPOES.</p><p><a href="${escapeHtml(unsubscribe)}">Dar de baja mi suscripción</a></p>`,
    text:`${edition.title}\n\n${edition.summary}\n\nLeer el boletín: ${url}\n\nDar de baja mi suscripción: ${unsubscribe}`};
}
export async function deliverOne(job, adapters) {
  if (!(await adapters.isActive(job.subscription_id))) {await adapters.finish(job,'cancelled');return 'cancelled';}
  // The immutable snapshot and stable key are reused after an uncertain response.
  try {
    const result=await adapters.send(job,`cepoes-boletin-${job.edition}-${job.subscription_id}`);
    if(!result?.id) throw Error('missing_provider_id');
    await adapters.finish(job,'accepted',result.id);return 'accepted';
  } catch {
    await adapters.retry(job);return 'retry';
  }
}
