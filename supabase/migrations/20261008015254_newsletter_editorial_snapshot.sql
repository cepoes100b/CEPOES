-- The email body is frozen before its first send so retries keep the same payload.
alter table public.newsletter_editions add column email_content jsonb;
alter table public.newsletter_editions add constraint newsletter_email_content_object
check (email_content is null or jsonb_typeof(email_content)='object');
