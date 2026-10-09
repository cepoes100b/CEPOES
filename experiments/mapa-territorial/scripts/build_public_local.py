#!/usr/bin/env python3
"""Read-only public CEPOES capture and canonical LOCAL build. Never deploys.

base-public is a bounded HTTPS capture, never a private/SFTP backup. The builder
runs a copied snapshot of trusted repository inputs; it never edits the source
checkout. No credential/environment discovery, login, subscriber, or API calls.
"""
from __future__ import annotations
import argparse, ast, concurrent.futures, hashlib, html, json, os, re, shutil
import subprocess, sys, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ORIGIN = 'https://cepoes.org'
BLOCKED = {'privado', 'private', 'admin', 'login', 'logout', 'auth', 'api', 'subscribers',
           'suscriptores', 'suscripcion', 'subscribe', 'unsubscribe', 'borradores', 'revision',
           '.git', '.env', 'supabase', 'node_modules'}
EXT = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.geojson', '.svg', '.png', '.jpg',
       '.jpeg', '.webp', '.ico', '.woff', '.woff2', '.ttf', '.pdf', '.csv', '.webmanifest', '.xml', '.txt'}
TEXT = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.geojson', '.svg', '.webmanifest'}
MARKER = '/.well-known/cepoes-release.json'
MAX_RESOURCE = 64 * 1024 * 1024
USER_AGENT = 'CEPOES-local-preview-audit/1.0 (public read-only)'

def now(): return datetime.now(timezone.utc).isoformat()
def sha(data): return hashlib.sha256(data).hexdigest()
def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
def canonical(value, source=ORIGIN + '/'):
    value = html.unescape(value.strip()).replace('\\/', '/')
    if not value or any(x in value for x in ['${','{','}', '<', '>', '\\', '\n']): return None
    p = urllib.parse.urlsplit(urllib.parse.urljoin(source, value))
    if p.scheme != 'https' or p.netloc != 'cepoes.org' or p.username or p.password: return None
    path = urllib.parse.unquote(p.path)
    if '%' in path or '\\' in path or any(ord(c) < 32 for c in path): return None
    parts = Path(path).parts
    if any(part.lower() in BLOCKED for part in parts) or '..' in parts: return None
    if any(part.startswith('.') for part in parts if part != '.well-known'): return None
    if path.startswith('/.well-known/') and path != MARKER: return None
    if Path(path).suffix.lower() in {'.csv', '.txt'} and any(x in Path(path).name.lower() for x in ['padron', 'deudores', 'microdatos']): return None
    if path.startswith('/assets/') and path.endswith('/'): return None  # JS base paths are not resources or directory-listing requests.
    if not path.endswith('/') and Path(path).suffix.lower() not in EXT: return None
    return ORIGIN + urllib.parse.quote(path, safe="/-._~")

def relpath(url):
    path = urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip('/')
    return path + 'index.html' if not path or path.endswith('/') else path

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe = canonical(newurl, req.full_url)
        if safe is None: raise ValueError('Redirect outside the public CEPOES allowlist')
        return super().redirect_request(req, fp, code, msg, headers, safe)

def fetch(url):
    assert canonical(url) == url, url
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.build_opener(SafeRedirect()).open(request, timeout=45) as r:
                body = r.read(MAX_RESOURCE + 1)
                if len(body) > MAX_RESOURCE: raise ValueError('Resource exceeds 64 MiB limit')
                if canonical(r.url) is None: raise ValueError('Disallowed final URL')
                return body, dict(url=url, final_url=r.url, status=r.status,
                    content_type=r.headers.get('Content-Type'), bytes=len(body), sha256=sha(body),
                    fetched_at=now(), etag=r.headers.get('ETag'), last_modified=r.headers.get('Last-Modified'))
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 2: raise
        except (TimeoutError, OSError):
            if attempt == 2: raise
        time.sleep(attempt + 1)

def references(body, source):
    try: text = body.decode('utf-8')
    except UnicodeDecodeError: return set()
    values = re.findall(r'''(?:src|href|poster)\s*=\s*["']([^"']+)["']''', text, flags=re.I)
    values += re.findall(r'''url\(\s*["']?([^\s)"']+)''', text, flags=re.I)
    # Literal paths in fetch calls, scripts, JSON catalogues and CSS. Never evaluate code.
    values += re.findall(r'''["'`]((?:https://cepoes\.org/|/|\./|\.\./)[^\s"'`<>]+)["'`]''', text)
    result = set()
    for value in values:
        u = canonical(value, source)
        if u: result.add(u)
    return result

def inventory(root):
    return [dict(path=p.relative_to(root).as_posix(), bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(root.rglob('*')) if p.is_file()]

def capture(repo, out, refresh=False):
    base, evidence = out/'base-public', out/'evidence'
    manifest_path = evidence/'capture.json'
    if manifest_path.exists() and not refresh:
        old = json.loads(manifest_path.read_text())
        for record in old['resources']:
            p = base / record['path']
            if not p.is_file() or sha(p.read_bytes()) != record['sha256']:
                raise RuntimeError(f'Cached public capture changed: {p}')
        print(f'Using verified capture: {len(old["resources"])} resources', flush=True)
        return old
    if base.exists(): raise RuntimeError('Use a fresh --output for a new capture; existing evidence is immutable')
    base.mkdir(parents=True)
    records, errors, skipped = {}, [], []
    initial_marker, initial_meta = fetch(ORIGIN+MARKER)
    initial = json.loads(initial_marker)
    dump(evidence/'release-before.json', initial)
    initial_meta['path'] = relpath(ORIGIN+MARKER)
    (base/initial_meta['path']).parent.mkdir(parents=True, exist_ok=True)
    (base/initial_meta['path']).write_bytes(initial_marker)
    records[ORIGIN+MARKER] = initial_meta
    sitemap, smeta = fetch(ORIGIN+'/sitemap.xml')
    (base/'sitemap.xml').write_bytes(sitemap)
    smeta['path'] = 'sitemap.xml'; records[ORIGIN+'/sitemap.xml'] = smeta
    locations = [n.text for n in ET.fromstring(sitemap).iter() if n.tag.endswith('}loc')]
    pending = set(filter(None, (canonical(x) for x in locations)))
    pending |= {ORIGIN+p for p in ['/404.html','/robots.txt','/site.webmanifest','/assets/data/search-index.json',
                               '/assets/data/lo-nuevo.json','/indexnow-key.txt','/assets/data/estructura-productiva/actual.json']}
    # Public assets explicitly required by the complete canonical site validator.
    tree = ast.parse((repo/'validar_sitio_despliegue.py').read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(x,ast.Name) and x.id=='required' for x in node.targets):
            pending |= {ORIGIN+'/'+x for x in ast.literal_eval(node.value) if canonical(ORIGIN+'/'+x)}
    for report in json.loads((repo/'deploy/reports-registry.json').read_text())['reports']:
        for key in ['url','cover','pdf']:
            if key in report and canonical(ORIGIN+report[key]): pending.add(ORIGIN+report[key])
    seen = set(records)
    rounds = 0
    while pending:
        rounds += 1
        current = sorted(pending - seen)
        pending = set()
        if not current: break
        if len(seen)+len(current) > 1600: raise RuntimeError('Public resource bound exceeded; inspect capture scope')
        print(f'Capture round {rounds}: {len(current)} resources ({len(records)} saved)', flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch, u):u for u in current}
            for future in concurrent.futures.as_completed(futures):
                u = futures[future]; seen.add(u)
                try:
                    body, meta = future.result()
                    rel = relpath(u); p=base/rel
                    # Avoid alias duplicates overwriting a canonical capture with different bytes.
                    if p.exists() and p.read_bytes()!=body: raise RuntimeError('Conflicting public aliases for '+rel)
                    p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(body)
                    meta['path']=rel; records[u]=meta
                    if p.suffix in TEXT: pending |= references(body, meta['final_url']) - seen
                except Exception as e:
                    errors.append(dict(url=u, error=f'{type(e).__name__}: {e}'))
                    print('Capture warning:', u, str(e)[:100], flush=True)
        dump(evidence/'capture-progress.json', dict(resources=list(records.values()),errors=errors))
    final_marker, final_meta = fetch(ORIGIN+MARKER)
    final = json.loads(final_marker); dump(evidence/'release-after.json',final)
    marker_same = initial_marker == final_marker
    marker_checks=[]
    for rel, expected in initial['files'].items():
        p=base/rel
        marker_checks.append(dict(path=rel, expected=expected,
            observed={'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} if p.is_file() else None,
            matches=p.is_file() and p.stat().st_size==expected['bytes'] and sha(p.read_bytes())==expected['sha256']))
    result=dict(schema_version=1, provenance='public HTTPS capture; NOT an SFTP/private backup',
        started_at=initial_meta['fetched_at'],finished_at=now(),public_release_sha=initial['commit_sha'],
        marker_stable=marker_same,marker_checks=marker_checks,
        sitemap_urls=len(locations),sitemap_paths_missing=[x for x in locations if canonical(x) and not (base/relpath(canonical(x))).is_file()],
        resources=sorted(records.values(),key=lambda r:r['path']),errors=errors,
        exclusions=['All blocked path segments; private/login/subscriber/API resources',
                    'External hosts and runtime-generated URLs are not crawled',
                    'No SFTP, private registry, credentials, subscriber data or internal Drive'],
        complete_public_backup=False)
    dump(manifest_path,result); dump(evidence/'base-checksums.json',inventory(base))
    print(f'Capture saved: {len(records)} resources; {len(errors)} fetch failures; stable marker={marker_same}',flush=True)
    return result

def copy_safe_tree(src, dst):
    for p in src.rglob('*'):
        rel=p.relative_to(src)
        if any(x.lower() in BLOCKED or x=='__pycache__' for x in rel.parts): continue
        if p.is_symlink(): raise RuntimeError('Unexpected symlink: '+str(p))
        if p.is_file():
            target=dst/rel; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p,target)

def snapshot(repo, out, expected):
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if actual!=expected: raise RuntimeError(f'Expected source HEAD {expected}, got {actual}')
    dest=out/'pipeline-source'
    if dest.exists(): shutil.rmtree(dest)
    dest.mkdir()
    for p in repo.iterdir():
        if p.is_file() and p.suffix in {'.py','.json'}: shutil.copy2(p,dest/p.name)
    for name in ['deploy','scripts','.github']:
        copy_safe_tree(repo/name,dest/name)
    # Only public debt aggregates; no raw data, padron, matrix or compressed source.
    debt=repo/'datos/endeudamiento'
    for p in debt.iterdir():
        if p.name=='manifest.json' or re.fullmatch(r'\d{4}-\d{2}\.json',p.name):
            target=dest/'datos/endeudamiento'/p.name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,target)
    equipment=repo/'equipamientos'; (dest/'equipamientos').mkdir()
    catalog=json.loads((equipment/'catalogo.json').read_text())
    names={'catalogo.json','resumen-territorial.json'}
    for layer in catalog.get('layers',[]):
        if layer.get('id') not in {'vados','rampas-accesibilidad-2016'}:
            names.add(layer.get('file') or layer['id']+'.json')
    for name in names:
        p=equipment/name
        if p.is_file(): shutil.copy2(p,dest/'equipamientos'/name)
    dump(out/'evidence/pipeline-input-checksums.json', inventory(dest))
    return dest

def build(repo, out, expected):
    if not (out/'evidence/capture.json').is_file(): raise RuntimeError('No existing capture; run --mode capture first')
    capture_info=capture(repo,out)  # Cache verification only; no network when capture.json exists.
    if not capture_info['marker_stable'] or not all(x['matches'] for x in capture_info['marker_checks']):
        raise RuntimeError('Production marker changed or public fingerprint mismatch; do not build from an inconsistent capture')
    if capture_info['sitemap_paths_missing']: raise RuntimeError('Capture is missing sitemap HTML')
    base=out/'base-public'; source=snapshot(repo,out,expected); candidate=out/'candidate'
    if candidate.exists(): shutil.rmtree(candidate)
    shutil.copytree(base,candidate)
    # A local build must not misrepresent itself as the production release.
    (candidate/MARKER.lstrip('/')).unlink(missing_ok=True)
    logdir=out/'logs'; logdir.mkdir(exist_ok=True)
    steps=[]
    def run(label, command):
        print('BUILD:',label,flush=True)
        process=subprocess.run(command,cwd=source,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                               env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        (logdir/(label+'.log')).write_text(process.stdout)
        steps.append(dict(step=label,command=command,exit_code=process.returncode,log=str(logdir/(label+'.log'))))
        dump(out/'evidence/build-steps.json',steps)
        if process.returncode: raise RuntimeError(label+' failed; see '+str(logdir/(label+'.log')))
    py=sys.executable
    run('01_debt',[py,'deploy/validar_endeudamiento_publico.py','--root','.'])
    run('02_equipment_search',[py,'generar_indice_busqueda_equipamientos.py'])
    copy_safe_tree(source/'deploy/site-overlay',candidate)
    for line in (source/'deploy/delete-paths.txt').read_text().splitlines():
        rel=line.partition('#')[0].strip()
        if not rel: continue
        if rel.startswith('/') or '..' in rel: raise RuntimeError('Unsafe delete path')
        if any(p.lower() in BLOCKED for p in Path(rel).parts): raise RuntimeError('Delete outside public scope')
        target=candidate/rel
        if target.is_dir(): shutil.rmtree(target)
        else: target.unlink(missing_ok=True)
    # The canonical normalizer needs historical route files absent from a public HTTP capture.
    # Populate only local compatibility aliases with the corresponding canonical HTTP bytes.
    aliases=[]
    for old,new in [('observatorio/presupuesto','presupuesto/ejecucion'),('territorio/presupuesto','presupuesto/territorio')]:
        if not (candidate/old).is_dir():
            shutil.copytree(base/new,candidate/old)
            aliases.append(dict(local_alias=old,public_source=new,reason='Canonical normalizer legacy route prerequisite; not an SFTP reconstruction'))
    dump(out/'evidence/local-compatibility-aliases.json',aliases)
    run('03_legislature',[py,'deploy/preparar_legislatura_publica.py',str(candidate)])
    run('04_global_search',[py,'generar_indice_busqueda_global.py',str(candidate)])
    run('05_data_status',[py,'generar_estado_datos.py',str(candidate)])
    workflow=(source/'.github/workflows/desplegar-hostinger.yml').read_text()
    section=workflow.split('name: Ajustar texto público de seguimiento institucional',1)[1].split('name: Normalizar navegación',1)[0]
    inline=section.split("python - <<'PY'\n",1)[1].rsplit('\n          PY',1)[0]
    inline='\n'.join(line[10:] for line in inline.splitlines()).replace('Path("_site")',f'Path({str(candidate)!r})')
    run('06_institutional_text',[py,'-c',inline])
    run('07_normalizer',[py,'deploy/preparar_sitio_publico.py',str(candidate)])
    for label,args in [
        ('08_health_bridge',['deploy/parche_observatorio_salud.py',str(candidate/'observatorio/index.html')]),
        ('09_legislature_bridge',['deploy/preparar_puente_legislatura.py',str(candidate)]),
        ('10_catalog_tests',['-m','unittest','test_catalogo_informes.py']),
        ('11_catalog',['generar_catalogo_informes.py',str(candidate)]),
        ('12_news_tests',['-m','unittest','test_lo_nuevo.py']),
        ('13_news',['generar_lo_nuevo.py',str(candidate),'--previous',str(base)]),
        ('14_publications_feed',['-m','scripts.generar_publications_feed',str(candidate)]),
        ('15_canonical_validator',['deploy/validar_publicacion_canonica.py',str(candidate)]),
        ('16_contrast_validator',['validar_contraste_visual.py']),
        ('17_search_validator',['validar_busqueda_global.py',str(candidate)]),
        ('18_r1_validator',['validar_r1_runtime.py',str(candidate)]),
        ('19_site_validator',['validar_sitio_despliegue.py',str(candidate)])]:
        run(label,[py,*args])
    leak_checks=[]
    for rel in ['sitemap.xml','sitemap.txt','assets/data/search-index.json','assets/data/lo-nuevo.json',
                'assets/data/newsletter-publications.json','assets/data/newsletter-editions.json','assets/data/newsletter-config.json']:
        path=candidate/rel
        if path.exists():
            found='/laboratorio/mapa-territorial' in path.read_text()
            leak_checks.append(dict(path=rel,prototype_found=found))
            if found: raise RuntimeError('Prototype leaked into index/feed: '+rel)
    missing=set()
    for p in candidate.rglob('*'):
        if not p.is_file() or p.suffix not in {'.html','.css','.js','.mjs'}: continue
        origin=ORIGIN+'/'+p.relative_to(candidate).as_posix()
        for u in references(p.read_bytes(),origin):
            if not (candidate/relpath(u)).is_file(): missing.add(u)
    dump(out/'evidence/unresolved-public-references.json',sorted(missing))
    files=inventory(candidate); dump(out/'evidence/candidate-checksums.json',files)
    summary=dict(schema_version=1,finished_at=now(),source_checkout_sha=expected,
        public_release_sha=capture_info['public_release_sha'],candidate=str(candidate),
        html_pages=len(list(candidate.rglob('*.html'))),barrios=len(list((candidate/'territorio/barrios').glob('*/index.html'))),
        files=len(files),bytes=sum(x['bytes'] for x in files),steps_passed=len(steps),
        prototype_injected=False,prototype_index_checks=leak_checks,
        local_aliases=aliases,public_capture_errors=capture_info['errors'],
        unresolved_literal_public_references=sorted(missing),
        local_only=True,publication_performed=False,sftp_backup_used=False,
        omissions=['No private overlay paths or production .htaccess are captured',
                   'No private rollback, durable OCI release, production marker generation, SFTP, deploy or live smoke tests',
                   'External CDN assets and computed runtime URLs are outside the bounded capture'],
        status='canonical public validators passed; LOCAL preview only')
    dump(out/'evidence/build-summary.json',summary)
    baseline=out/'canonical-baseline'
    if baseline.exists(): shutil.rmtree(baseline)
    shutil.copytree(candidate,baseline)
    dump(out/'evidence/canonical-baseline-checksums.json',files)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    return summary

def integrate(repo, out, expected, prototype):
    """Overlay only the isolated prototype on the validated baseline, offline."""
    if prototype is None: raise RuntimeError('integrate requires --prototype-dir containing public overlay roots')
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    if actual!=expected: raise RuntimeError(f'Expected source HEAD {expected}, got {actual}')
    baseline=out/'canonical-baseline'; candidate=out/'candidate'; source=out/'pipeline-source'
    hashes=out/'evidence/canonical-baseline-checksums.json'
    if not hashes.is_file() or not baseline.is_dir(): raise RuntimeError('Preserve a validated canonical-baseline before integration')
    expected_files=json.loads(hashes.read_text())
    if inventory(baseline)!=expected_files: raise RuntimeError('Canonical baseline checksum mismatch')
    relevant=['deploy/preparar_sitio_publico.py','deploy/validar_publicacion_canonica.py',
              'validar_contraste_visual.py','validar_busqueda_global.py','validar_r1_runtime.py','validar_sitio_despliegue.py']
    for rel in relevant:
        if sha((repo/rel).read_bytes())!=sha((source/rel).read_bytes()):
            raise RuntimeError('Canonical pipeline changed since baseline; rebuild before integration: '+rel)
    inputs=inventory(prototype)
    allowed=('laboratorio/mapa-territorial/','assets/mapa-territorial/')
    if not inputs or any(not row['path'].startswith(allowed) for row in inputs):
        raise RuntimeError('Prototype overlay may contain only laboratorio/mapa-territorial and assets/mapa-territorial')
    html_path=prototype/'laboratorio/mapa-territorial/index.html'
    if not html_path.is_file(): raise RuntimeError('Missing prototype index.html')
    def noindex(path):
        return bool(re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex',path.read_text(),re.I))
    if not noindex(html_path): raise RuntimeError('Prototype requires noindex')
    if candidate.exists(): shutil.rmtree(candidate)
    shutil.copytree(baseline,candidate)
    copy_safe_tree(prototype,candidate)
    if inventory(prototype)!=inputs: raise RuntimeError('Prototype inputs changed during copy; retry after writer finishes')
    dump(out/'evidence/prototype-input-checksums.json',inputs)
    logs=out/'logs/integration'; logs.mkdir(parents=True,exist_ok=True)
    steps=[]
    def run(label, args):
        print('INTEGRATE:',label,flush=True)
        proc=subprocess.run([sys.executable,*args],cwd=source,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        path=logs/(label+'.log'); path.write_text(proc.stdout)
        steps.append(dict(step=label,command=[sys.executable,*args],exit_code=proc.returncode,log=str(path)))
        dump(out/'evidence/integration-steps.json',steps)
        if proc.returncode: raise RuntimeError(f'Integration {label} failed; see {path}')
    code=("from pathlib import Path; import importlib.util; "
          f"spec=importlib.util.spec_from_file_location('cepoes_local_normalizer', {str(source/'deploy/preparar_sitio_publico.py')!r}); "
          "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
          f"module.normalize_html(Path({str(candidate/'laboratorio/mapa-territorial/index.html')!r}), Path({str(candidate)!r}))")
    run('01_normalize_prototype_only',['-c',code])
    if not noindex(candidate/'laboratorio/mapa-territorial/index.html'): raise RuntimeError('Normalizer removed noindex')
    for label,args in [('02_canonical',['deploy/validar_publicacion_canonica.py',str(candidate)]),
                       ('03_contrast',['validar_contraste_visual.py']),
                       ('04_search',['validar_busqueda_global.py',str(candidate)]),
                       ('05_r1',['validar_r1_runtime.py',str(candidate)]),
                       ('06_site',['validar_sitio_despliegue.py',str(candidate)])]: run(label,args)
    old={row['path']:row for row in expected_files}; files=inventory(candidate); new={row['path']:row for row in files}
    changed=[rel for rel in old if new.get(rel)!=old[rel]]
    added=sorted(set(new)-set(old))
    if changed: raise RuntimeError('Prototype integration changed pre-existing public files: '+', '.join(changed))
    if any(not rel.startswith(allowed) for rel in added): raise RuntimeError('Files outside prototype scope added')
    protected=[]
    for rel in ['sitemap.xml','sitemap.txt','assets/data/search-index.json','assets/data/lo-nuevo.json',
                'assets/data/newsletter-publications.json','assets/data/newsletter-editions.json','assets/data/newsletter-config.json']:
        p=candidate/rel
        if p.is_file():
            if '/laboratorio/mapa-territorial' in p.read_text(): raise RuntimeError('Prototype entered index/feed: '+rel)
            protected.append(dict(path=rel,sha256=new[rel]['sha256'],matches_baseline=True,prototype_present=False))
    missing=set()
    for p in candidate.rglob('*'):
        if p.is_file() and p.suffix in {'.html','.css','.js','.mjs'}:
            for url in references(p.read_bytes(),ORIGIN+'/'+p.relative_to(candidate).as_posix()):
                if not (candidate/relpath(url)).is_file(): missing.add(url)
    if missing: raise RuntimeError('Missing public references after integration: '+', '.join(sorted(missing)))
    dump(out/'evidence/integrated-candidate-checksums.json',files)
    result=dict(schema_version=1,finished_at=now(),source_checkout_sha=expected,
                baseline_sha=json.loads((out/'evidence/build-summary.json').read_text())['source_checkout_sha'],
                public_release_sha=json.loads((out/'evidence/capture.json').read_text())['public_release_sha'],
                html_pages=len(list(candidate.rglob('*.html'))),barrios=len(list((candidate/'territorio/barrios').glob('*/index.html'))),
                candidate=str(candidate),baseline=str(baseline),files=len(files),bytes=sum(x['bytes'] for x in files),
                added=added,changed_baseline_files=changed,steps_passed=len(steps),protected_indexes=protected,
                unresolved_public_references=sorted(missing),full_normalizer_rerun=False,feeds_regenerated=False,
                local_only=True,publication_performed=False,status='isolated prototype integrated; complete public validators passed')
    dump(out/'evidence/integration-summary.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected-sha',required=True)
    p.add_argument('--mode',choices=['all','capture','build','integrate'],default='all')
    p.add_argument('--prototype-dir',type=Path)
    a=p.parse_args(); a.repo=a.repo.resolve(); a.output=a.output.resolve()
    if a.output==a.repo or a.repo in a.output.parents: raise SystemExit('Output must be outside source checkout')
    a.output.mkdir(parents=True,exist_ok=True)
    try:
        if a.mode in ['all','capture']: capture(a.repo,a.output)
        if a.mode in ['all','build']:
            if a.prototype_dir: raise RuntimeError('Use --mode integrate for prototype injection after the complete baseline build')
            build(a.repo,a.output,a.expected_sha)
        if a.mode == 'integrate': integrate(a.repo,a.output,a.expected_sha,a.prototype_dir.resolve() if a.prototype_dir else None)
    except Exception as e:
        dump(a.output/'evidence/failure.json',dict(at=now(),error=f'{type(e).__name__}: {e}'))
        raise

if __name__=='__main__': main()
