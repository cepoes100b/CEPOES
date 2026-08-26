-- CEPOES · Endurecimiento de funciones editoriales.
-- Un search_path vacío evita que una función privilegiada resuelva objetos
-- controlables por el llamador. Todos los objetos usados están calificados.

alter function private.current_press_role() set search_path='';
alter function private.press_role_rank() set search_path='';
alter function private.guard_press_note() set search_path='';
alter function private.capture_press_version() set search_path='';
alter function private.log_press_activity() set search_path='';
alter function private.manage_press_invite_internal(text,text,boolean) set search_path='';
alter function private.list_press_team_internal() set search_path='';
alter function private.handle_new_user() set search_path='';
alter function public.manage_press_invite(text,text,boolean) set search_path='';
alter function public.list_press_team() set search_path='';

revoke all on function private.manage_press_invite_internal(text,text,boolean) from public,anon;
revoke all on function private.list_press_team_internal() from public,anon;
revoke all on function public.manage_press_invite(text,text,boolean) from public,anon;
revoke all on function public.list_press_team() from public,anon;
grant execute on function public.manage_press_invite(text,text,boolean) to authenticated;
grant execute on function public.list_press_team() to authenticated;
