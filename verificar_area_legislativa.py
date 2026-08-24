#!/usr/bin/env python3
"""Validaciones estáticas de seguridad y consistencia para el Área Legislativa."""
from pathlib import Path
from html.parser import HTMLParser
import re

ROOT = Path(__file__).resolve().parent
HTML = ROOT / 'deploy/site-overlay/legislativa/index.html'
JS = ROOT / 'deploy/site-overlay/assets/legislativa.js'
CSS = ROOT / 'deploy/site-overlay/assets/legislativa.css'
EXAMPLE = ROOT / 'deploy/site-overlay/assets/legislativa-config.example.js'
SQL = ROOT / 'infra/supabase/legislativa.sql'
DOC = ROOT / 'docs/AREA-LEGISLATIVA.md'

required = [HTML, JS, CSS, EXAMPLE, SQL, DOC]
for p in required:
    assert p.is_file() and p.stat().st_size > 100, f'Falta o está vacío: {p.relative_to(ROOT)}'

html = HTML.read_text(encoding='utf-8')
js = JS.read_text(encoding='utf-8')
sql = SQL.read_text(encoding='utf-8').lower()
example = EXAMPLE.read_text(encoding='utf-8')

class IdParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids = set()
    def handle_starttag(self, _tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])

parser = IdParser(); parser.feed(html)
refs = set(re.findall(r"el\('([^']+)'\)", js))
missing = sorted(refs - parser.ids)
assert not missing, f'IDs DOM referenciados por JS que no existen: {missing}'

# La página privada jamás debe indexarse.
robots = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']+)', html, re.I)
assert robots and 'noindex' in robots.group(1).lower() and 'nofollow' in robots.group(1).lower(), 'Falta noindex/nofollow'

# Debe fallar cerrada cuando no existe configuración de autenticación y validar perfil activo.
assert 'failClosed' in js and 'supabaseUrl' in js and 'supabaseAnonKey' in js, 'No se detecta fail-closed de autenticación'
assert "from('profiles')" in js, 'No se consulta el perfil autorizado'
assert "!data.active" in js, 'No se valida profiles.active'

# El acceso debe ser passwordless y volver únicamente a la ruta privada.
assert 'signInWithOtp' in js, 'El acceso no usa Magic Link/OTP'
assert 'signInWithPassword' not in js, 'No debe quedar login por contraseña en el frontend'
assert "new URL('/legislativa/',window.location.origin)" in js, 'El Magic Link no vuelve a /legislativa/'
assert 'shouldCreateUser:true' in js, 'El primer Magic Link no puede crear el usuario autorizado'

# No aceptar secretos administrativos en archivos servidos al navegador.
for forbidden in ['service_role', 'sftp_password', 'database_password', 'jwt_secret']:
    assert forbidden not in html.lower(), f'Secreto prohibido en HTML: {forbidden}'
    assert forbidden not in js.lower(), f'Secreto prohibido en JS: {forbidden}'

# El ejemplo puede mencionar service_role sólo como advertencia, nunca asignarlo.
assert 'TU_SUPABASE_ANON_KEY' in example
assert 'supabaseAnonKey' in example
assert not re.search(r'service[_-]?role\s*[:=]\s*["\'][A-Za-z0-9._-]{12,}', example, re.I), 'Parece haber una service role key en el ejemplo'

# RLS y revocación anónima en todas las tablas privadas.
tables = ['profiles','expediente_analyses','session_briefs','session_brief_items','project_bank','internal_comments']
for table in tables:
    assert f'alter table public.{table} enable row level security' in sql, f'RLS no habilitado: {table}'
    assert f'revoke all on public.{table} from anon' in sql, f'anon no revocado: {table}'

assert "default false" in sql, 'Los perfiles nuevos deben nacer inactivos'
assert 'is_active_member' in sql and 'can_write_intelligence' in sql and 'is_app_admin' in sql

# Capa privada no debe agregarse al sitemap versionado.
for rel in ['deploy/site-overlay/sitemap.xml','deploy/site-overlay/sitemap.txt']:
    p = ROOT / rel
    if p.exists():
        assert '/legislativa/' not in p.read_text(encoding='utf-8',errors='replace'), f'Área privada incluida en {rel}'

print('Área Legislativa · validación estática OK')
print(f'  HTML IDs: {len(parser.ids)} · referencias JS: {len(refs)}')
print(f'  Tablas privadas con RLS: {len(tables)}')
print('  Acceso: passwordless por Magic Link')
