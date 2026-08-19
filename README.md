# Observatorio CEPOES — pipeline de datos

Genera `datos.json`, el archivo que alimenta el observatorio de la Ciudad de
Buenos Aires publicado en https://cepoes.tiiny.site.

Todos los días a las 9 de la mañana (hora de Buenos Aires) un GitHub Action baja
las planillas oficiales de IDECBA, las procesa, verifica el resultado y commitea
`datos.json` si cambió algo. La página lo lee directo desde este repositorio, así
que **el sitio se actualiza solo: no hay que volver a subir nada a tiiny.host**.

## Cómo se conecta con la web

En `observatorio.html` y en `index.html` hay una línea con el nombre del repo:

```js
repo: 'USUARIO/REPOSITORIO',
```

De ahí se arman las URLs `raw.githubusercontent.com`, que GitHub sirve con las
cabeceras CORS necesarias. Si el repo no responde, la página usa los datos que
tiene embebidos y marca en amarillo el indicador de antigüedad.

## Archivos

| Archivo | Qué hace |
|---|---|
| `fuentes.py` | Catálogo de datasets: la URL de cada página del Banco de Datos de IDECBA |
| `descargar.py` | Baja los `.xlsx` y arma `calendario.json` |
| `parsers.py` | Convierte cada planilla al formato del observatorio |
| `generar_datos.py` | Arma `datos.json` |
| `verificar.py` | Control de calidad antes de publicar |
| `idecba/*.xlsx` | Última copia de cada planilla oficial |
| `datos.json` | **La salida.** Lo que consume la web |

## Uso local

```bash
pip install -r requirements.txt
python descargar.py        # baja las planillas
python generar_datos.py    # arma datos.json
python verificar.py        # control de calidad
```

`generar_datos.py` funciona sin conexión: si no bajaste nada, procesa los `.xlsx`
que ya están en `idecba/`.

## Cómo está pensado para no romperse

IDECBA reescribe el mismo post del Banco de Datos cada vez que publica un período
nuevo y sólo cambia la ruta del adjunto. Por eso `fuentes.py` guarda la URL de la
**página**, no la del archivo, y el descargador lee de ahí el link al `.xlsx`.

Además, en cada capa hay una red:

- **Descarga fallida** → se conserva la copia commiteada de esa planilla.
- **Parser que falla** → se hereda ese bloque del `datos.json` anterior. El resto
  se actualiza igual. Nada de que un dataset roto tire abajo los otros ocho.
- **Verificación fallida** → no se commitea. La web sigue con el archivo previo.

El verificador no sólo mira que el archivo exista: chequea largos mínimos de cada
serie, que las series de un mismo bloque midan lo mismo, que estén las 15 comunas,
que los porcentajes caigan en rangos plausibles y que ninguna serie se haya
acortado respecto de la versión publicada.

## Qué se actualiza solo y qué no

Se regenera en cada corrida: IPCBA y sus divisiones, canastas, empleo (ETOI),
pobreza, PGB, comercio exterior, industria, masa salarial, locales por eje
comercial, locales por comuna y el calendario de publicaciones.

Se conserva y se edita a mano:

- `presupuesto` — viene de BA Data y cierra por trimestre.
- `censo` — Censo 2022 de INDEC, no cambia hasta el próximo censo.
- `poblacion` — proyecciones, se actualizan muy de vez en cuando.

Para tocarlos, editá `datos.json` a mano y commiteá: el generador los respeta.

## Notas sobre las planillas

Cosas del formato de IDECBA que los parsers ya contemplan:

- `///`, `.`, `-` y `s/d` significan "sin dato".
- Los años provisorios vienen marcados con asterisco (`2025*`).
- Algunos valores traen la llamada al pie pegada al número (`6,8a`).
- La coma es el separador decimal en varias planillas.
- `pobreza_tasas.xlsx` trae una hoja por año, con un bloque por trimestre.
- `canastas.xlsx` viene transpuesta: los meses son columnas.
- La variación interanual del IPCBA no está publicada: se calcula acá contra el
  índice del mismo mes del año anterior.
- Las exportaciones se publican en dólares y el gráfico las muestra en millones.

## Fuentes

Instituto de Estadística y Censos de la Ciudad Autónoma de Buenos Aires (IDECBA),
Banco de Datos — https://www.estadisticaciudad.gob.ar/eyc/arbol-tematico/

Presupuesto: BA Data, Ministerio de Economía y Finanzas GCBA.
Censo: INDEC, Censo Nacional 2022.
