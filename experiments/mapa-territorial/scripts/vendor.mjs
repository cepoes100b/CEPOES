// Exact dependency from package-lock; no CDN or implicit latest version at runtime.
import {readFile, mkdir, copyFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const root = new URL('../', import.meta.url);
const pkg = JSON.parse(await readFile(new URL('node_modules/maplibre-gl/package.json', root)));
if (pkg.version !== '6.13.0') throw new Error('Unexpected MapLibre version');
const dest = new URL('public/assets/mapa-territorial/vendor/', root);
await mkdir(dest, {recursive: true});
const files = ['maplibre-gl.mjs', 'maplibre-gl-shared.mjs', 'maplibre-gl-worker.mjs', 'maplibre-gl.css'];
const manifest = {name: pkg.name, version: pkg.version, license: pkg.license, files: {}};
for (const file of files) {
  const source = new URL(`node_modules/maplibre-gl/dist/${file}`, root);
  await copyFile(source, new URL(file, dest));
  const bytes = await readFile(source);
  manifest.files[file] = {bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex')};
}
await copyFile(new URL('node_modules/maplibre-gl/LICENSE.txt', root), new URL('LICENSE-MapLibre.txt', dest));
await writeFile(new URL('manifest.json', dest), JSON.stringify(manifest, null, 2) + '\n');
console.log(JSON.stringify(manifest, null, 2));
