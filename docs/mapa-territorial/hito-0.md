# Mapa Territorial CEPOES 2.0 · Hito 0
Fecha de auditoría: 2026-10-09. Encargo: [issue #192](https://github.com/cepoes100b/CEPOES/issues/192).
Base auditada: `ddefe51f5ca5c5f9a0e058a6cafa065d407dfc2a`.
Rama: `feat/mapa-territorial-2-dot`. Estado: diseño / prototipo en curso; no candidata publicada.

## 1. Inventario y decisiones de reutilización
| Recurso | Evidencia encontrada | Decisión |
|---|---|---|
| `assets/thematic-map.js` | D3/SVG; busca 48 barrios en dos servidores; hay ramas que transforman faltantes a cero | Conservar producto vigente; no heredar esas conversiones ni dependencia de geometría remota |
| `assets/deporte-salud.js` | Mercator/SVG, 15 comunas y servicios; reconstruye SVG por filtro | Referencia interna de controles y rendimiento; no migrarlo en este PR |
| `assets/equipamientos.js` y página | Catálogo amplio, filtros, fuentes y metadatos | Enlazar fichas existentes; reutilizar registros sólo tras verificar geometría y licencia |
| `badata/barrios.geojson` | 48 features, IDs, nombre, comuna, área; 674 KB | Copia oficial versionada como insumo; controlar IDs, topología, CRS y cobertura |
| `assets/data/estructura-productiva/comunas.geojson` | 15 features, 517 KB | Validar contra disolución de barrios y fuente oficial; sin tocar bootstrap global |
| `estructura-productiva-bootstrap.js` | Intercepta globalmente fetch para una URL oficial | No reutilizar monkey patch; fuentes locales explícitas por componente |
| Capas educación, salud, verdes | Educación: 2.732 registros sin coordenadas en JSON derivado; salud: 86, sólo 50 ubicados; verdes: 2.176 puntos derivados | Auditar CRS y fuente original antes de incorporar. Un registro sin punto se conserva y se informa; nunca generar coordenadas ficticias |
| `site.css`, Poppins/Inter, navegación | Estilo compartido, pero CSS base y parte del HTML público no están en overlay | Consumir CSS base en copia de ensayo; no modificar identidad ni portada |
| R2 / build / backups | Publicador aplica overlay sobre respaldo, normaliza, valida, guarda release durable y sólo luego publica | Invariantes. No crear workflow de despliegue ni tocar credenciales, DNS, suscriptores |

No hay `.agents/skills` en este checkout. Se leyeron `AGENTS.md`, `deploy/README.md` y workflow canónico.

## 2. Arquitectura
Aplicación JavaScript modular sin framework global. Motor previsto: MapLibre GL JS local, versión exacta y licencia verificadas antes de incorporarla. WebGL para pan/zoom; GeoJSON territorial local; fuentes desacopladas de vista y de estado URL.
- Base inicial: cartografía administrativa local y simbología CEPOES. Funciona sin proveedor de teselas.
- Calles opcionales: OpenFreeMap, activadas por control explícito; atribución visible. Error o lentitud conserva base territorial y fichas.
- Alternativa sin WebGL: selección, búsqueda y tabla HTML siguen operativas; mensaje explica indisponibilidad del mapa.
- Sólo una capa inicial (salud), otras dos se descargan al activarlas. Caché en memoria y nombres/versiones de recursos; sin service worker global, geolocalización, coordenadas personales ni analítica.
- Selección de barrio/comuna por clic/toque y controles HTML equivalentes. Controles de encuadre, zoom y restablecer.
- Estado URL limitado a IDs públicos de territorio, capa y escala; restauración con Atrás/Adelante. Jamás incluir búsqueda libre, datos personales ni posición del dispositivo.
- Manifest de fuentes: URL canónica y recurso, licencia, fecha del recurso, fecha de descarga, hash, cobertura, campos, transformaciones y advertencias.
- Geometrías: nombres/IDs normalizados, 48 barrios y 15 comunas, límites validados. No simplificar hasta tener medidas que lo justifiquen.
- Servicios: puntos oficiales o reproyectados con CRS documentado. Polígonos verdes: punto representativo interior identificado como derivado; no confundirlo con entrada/acceso.
- Indicador candidato: registros geolocalizados por km² de superficie territorial verificada, comparado con comuna/Ciudad. Es densidad del inventario, no accesibilidad, calidad, capacidad ni cobertura poblacional. Si falta un denominador o ubicación, mostrar s/d y excluido explícito.

## 3. UI original y recorridos
Diseño CEPOES: tipografía existente, azul/tinta institucional, espacio editorial compacto. No se reutiliza diseño, código, íconos ni activos de Presupuesto Porteño.

Escritorio 1440:
```text
Navegación CEPOES
Territorio / Laboratorio                 Prototipo en revisión
Mapa territorial     Una Ciudad, 48 barrios
[Buscar barrio o comuna...]  [Barrios|Comunas] [Restablecer]
+-------------------+----------------------------------+---------------------+
| EXPLORAR          |                                  | FICHA TERRITORIAL   |
| Salud      (•)    |    Mapa CABA                      | nombre / comuna     |
| Educación  ( )    |    selección + nombres            | registros, densidad |
| Verdes     ( )    |    zoom/encuadre                    | comparación         |
| fuente / corte    |    leyenda / atribución            | servicios + fuente  |
+-------------------+----------------------------------+---------------------+
[Ver registros y alternativa textual]    [Método, calidad y fuentes]
```

Móvil 320/390/430:
```text
CEPOES                     menú/tema
Mapa territorial
[Buscar barrio/comuna               ]
[Salud] [Educación] [Verdes]
[Barrios / Comunas] [Restablecer]
+-----------------------------------+
| mapa, zoom y encuadre              |
| selección y leyenda               |
+-----------------------------------+
Ficha del territorio seleccionado
Comparación / registros / fuentes
[Lista accesible de territorios]
```
No panel modal que atrape foco ni controles flotantes sobre textos esenciales. Botones ≥44 px, foco visible, sin depender de hover ni sólo del color. Scroll de página disponible con gestos cooperativos; movimiento reducido respetado.

Recorridos: barrio → ficha → servicios/capa → ficha de fuente; capa → comparación → producto territorial existente; retorno conserva URL/selección. Alternativa textual con la misma información que el mapa.

## 4. Motor y proveedores: costos y límites
| Opción | Ventajas | Riesgos/costos | Decisión |
|---|---|---|---|
| MapLibre + base local | Sin API key ni costos por solicitudes; misma geometría en test y producción | Peso JS/WebGL; mantenimiento versión y licencia | Predeterminado, sujeto a prueba real |
| OpenFreeMap público | Sin registro, API key, cookies ni precio por vistas según sitio oficial | Sin SLA; red externa y atribución OSM/OpenMapTiles; disponibilidad no garantizada | Calles opcionales, fallback local |
| Autohospedar teselas | Control y menor dependencia externa | Almacenamiento, generación, distribución y mantenimiento; no presupuestado | Fuera de alcance; no contratar infraestructura |
| Proveedor comercial | Posible soporte/SLA | Cuenta, claves, cuota y compromisos | Fuera de alcance; requeriría decisión separada |
| D3/SVG actual | Liviano para 48/15 polígonos; conocido en CEPOES | Pan/zoom/etiquetado y grandes nubes de puntos requieren trabajo; rendimiento actual sin medir | Referencia y alternativa textual; no migrar productos |

Fuentes consultadas: [MapLibre oficial](https://maplibre.org/maplibre-gl-js/docs/), [OpenFreeMap](https://openfreemap.org/), [inicio/atribución](https://openfreemap.org/quick_start/).
Presupuesto orientativo: $0 de servicios/compromisos nuevos. Objetivo de recursos propios iniciales <2 MB sin compresión y <800 KB gzip (a medir, no resultado); capas diferidas compactas. Ningún recurso comunal de varios MB se carga de entrada.

## 5. Integración reversible
Todo el experimento queda bajo `experiments/mapa-territorial/`, fuera de `deploy/site-overlay`. Un constructor **sólo local** recibirá una copia pública, ejecutará normalizadores/validadores existentes y agregará después `/laboratorio/mapa-territorial/`. No incorpora enlace en menú, portada, buscador, sitemap, Lo nuevo ni feeds. No publica.
- No se modifica pipeline R2, respaldo, manifiestos de producción ni distribución.
- PR draft; issue abierto. Sin auto-merge ni workflow de escritura.
- Reversión del ensayo: descartar directorio de salida. Reversión de código: revertir este PR, sin migración de datos.
- La eventual integración pública requiere revisión y autorización final, otro diff explícito y el mismo build canónico con R2/backups. Ningún deploy paralelo.

## 6. Capacidades realmente verificadas
- GitHub oficial CEPOES: lectura completa issue/comentarios, HEAD main y creación de rama exitosas.
- Checkout aislado, Python 3.12.14, Node 24.19.0 disponibles. Se puede editar y ejecutar tests offline.
- `sites-preview`: no instalado en perfil portable; no se fabricará puente o daemon.
- `cua_repl`: conexión cloud disponible; smoke del navegador local en verificación. No asumir equivalencia hasta render real.
- Dependencia npm: lectura de metadatos bloqueada por interpretación de límite de destino. Aclaración solicitada, instalación detenida; no se elude.
- Build completo: repo es overlay, necesita base pública real (incluidos site.css e index.html). Su materialización y el render completo aún pendientes; una captura de producción no verifica el candidato.
- Capturas 320/390/430/1440 y ambos temas, WebGL, teclado, filtros y métricas: aún no ejecutadas. Se actualizará con evidencia, sin declarar listo anticipadamente.

## 7. Matriz de aceptación y siguiente trabajo
1. Normalización reproducible y controles 48/15, nombres/IDs, CRS, topología, solapes, puntos, fuente/licencia/corte.
2. Prototipo funcional aislado + test de estados faltantes/error y URL.
3. Build completo, sintaxis, R2 y regresión de menús/buscador/catálogo/publicaciones.
4. Render local real en 4 anchos × 2 temas; selección, filtros, zoom, teclado, gestos; comparación con mapa interno.
5. Transferencia inicial, latencia de mapa/filtros, FPS y memoria con navegador/red/CPU/contexto documentados. No extrapolar laboratorio a móviles reales.
6. PR draft con capturas/evidencias y límites. Detenerse antes de fusión/publicación y solicitar visto bueno.

Decisiones pendientes: ninguna de diseño menor. Bloqueo operativo puntual de destino para registro oficial y base pública; continuar lo independiente mientras se aclara.
