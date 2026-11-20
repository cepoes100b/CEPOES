#!/usr/bin/env bash
# Replica únicamente las entradas públicas heredadas de Hostinger, sin SFTP.
set -euo pipefail
site="$(mktemp -d)"
server_pid=
cleanup() {
  if [[ -n "$server_pid" ]]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  rm -rf -- "$site" "$site.server.log"
}
trap cleanup EXIT
routes=(precios/canasta-consumo precios/ipc trabajo/empleo condiciones-de-vida/pobreza)
chart_url=https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js
chart_sha=d2af8974e95271638772e9e9524db5b9a6f58d6ec2d5d781400447b4a31c681e
get() {
  curl --proto '=https' --tlsv1.2 --fail --silent --show-error \
    --max-time 40 --retry 2 --retry-max-time 90 "$1" --output "$2"
}
for route in "${routes[@]}"; do
  mkdir -p "$site/observatorio/$route"
  get "https://cepoes.org/observatorio/$route/" "$site/observatorio/$route/index.html"
  grep -Fq "$chart_url" "$site/observatorio/$route/index.html"
  get "https://cepoes.org/observatorio/$route/datos.csv" "$site/observatorio/$route/datos.csv"
done
mkdir -p "$site/assets/data"
for file in assets/data.js assets/indicator.js assets/data/datos.json; do
  get "https://cepoes.org/$file" "$site/$file"
done
get "$chart_url" "$site/chart.js"
printf '%s  %s\n' "$chart_sha" "$site/chart.js" | sha256sum -c -
python -m deploy.preparar_indicadores "$site"
node --check "$site/assets/indicator.js"
# Chromium puede saltar la interceptación de la página para <a download>.
# Servir el candidato por TCP real acotado a loopback, también para el CSV.
python -u -m http.server 0 --bind 127.0.0.1 --directory "$site" >"$site.server.log" 2>&1 &
server_pid=$!
port=
for _ in {1..50}; do
  port="$(sed -nE 's/^Serving HTTP on 127[.]0[.]0[.]1 port ([0-9]+) .*/\1/p' "$site.server.log" | head -n1)"
  [[ -n "$port" ]] && break
  kill -0 "$server_pid" || break
  sleep 0.1
done
[[ -n "$port" ]] || { cat "$site.server.log" >&2; exit 1; }
origin="http://127.0.0.1:$port"
curl --noproxy '*' --fail --silent --show-error --max-time 5 \
  "$origin/observatorio/precios/canasta-consumo/datos.csv" | cmp - "$site/observatorio/precios/canasta-consumo/datos.csv"
SITE_ROOT="$site" CEPOES_URL="$origin" CHART_JS="$site/chart.js" REQUIRE_CHART=1 \
  node tests/verificar_indicadores_browser.cjs datos.json
