export function validateEdition(item) {
  if (!Number.isInteger(item.edition) || item.edition < 1 || !/^\/publicaciones\/boletines\/boletin-\d+-[a-z]+-\d{4}\/$/.test(item.url)) throw Error('invalid_edition');
  if (!item.title || item.title.length > 300 || typeof item.summary !== 'string' || item.summary.length > 2000) throw Error('invalid_content');
  return {edition:item.edition,url:item.url,title:item.title,summary:item.summary,email_content:validateContent(item.email_content)};
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
import {validateContent} from './template.js';
export {newsletterEmail,escapeHtml} from './template.js';
