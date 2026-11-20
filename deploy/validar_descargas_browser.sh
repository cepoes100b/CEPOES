#!/usr/bin/env bash
# Replica únicamente las entradas públicas heredadas de Hostinger, sin SFTP.
set -euo pipefail
site="$(mktemp -d)"
trap 'rm -rf -- "$site"' EXIT
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
# Las rutas de navegador se sirven sólo desde el candidato y el JSON del
# checkout. No se envía tráfico del navegador a servicios públicos.
SITE_ROOT="$site" CHART_JS="$site/chart.js" REQUIRE_CHART=1 \
  node tests/verificar_indicadores_browser.cjs datos.json
