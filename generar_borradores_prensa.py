#!/usr/bin/env python3
"""Detecta hallazgos actualizados sin publicarlos como notas aprobadas."""
import json
import hashlib
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
FUNCTION_URL = os.environ.get("PRESS_DRAFT_FUNCTION_URL", "")
OIDC_AUDIENCE = "cepoes-supabase-press-drafts"

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def main():
    mig = load("deploy/site-overlay/assets/data/migraciones.json")
    sport = load("deploy/site-overlay/assets/data/deporte-accesibilidad-peatonal.json")
    prod = load("deploy/site-overlay/assets/data/estructura-productiva/actual.json")
    debt_manifest = load("datos/endeudamiento/manifest.json")
    debt = load("datos/endeudamiento/" + debt_manifest["archivos"][debt_manifest["ultimo_periodo"]])

    mvals = sorted(((v["eah"]["migracion_internacional_pct"], k) for k, v in mig["communes"].items()), reverse=True)
    cov = sport["cobertura"]["clubes"]["distancias"]["800"]["ciudad"]
    series = prod["panorama"]["empresas_registradas"]["serie"]
    base = next(x for x in debt["segmentos"] if all(v is None for v in x["filtros"].values()))
    mora = sorted(((row[1] / row[0] * 100, barrio) for barrio, row in zip(debt["barrios"], base["datos"])), reverse=True)

    def draft(slug, topic, tags, title, summary, source, section, period, body, methodology):
        return {"slug":slug,"topic":topic,"tags":tags,"title":title,"summary":summary,
                "body":[body],"methodology":methodology,"source_label":source,
                "source_section":section,"source_period":str(period)}

    intl = sorted(((v["eah"]["migracion_internacional_pct"], k) for k, v in mig["communes"].items()), reverse=True)
    internal = sorted(((v["eah"]["migracion_interna_pct"], k) for k, v in mig["communes"].items()), reverse=True)
    countries = sorted(mig["countries"]["rows"], key=lambda x:x["pct_2024"], reverse=True)
    club_communes = sport["cobertura"]["clubes"]["distancias"]["800"]["comunas"]
    club_rank = sorted(((v["cobertura_pct"], k) for k, v in club_communes.items()))
    club_city = sport["cobertura"]["clubes"]["distancias"]["800"]["ciudad"]
    club_geom = sport["cobertura"]["clubes"]["distancias"]["800"]["comparacion_geometrica"]["ciudad"]
    poly_city = sport["cobertura"]["polideportivos"]["distancias"]["1000"]["ciudad"]
    network_city = sport["cobertura"]["red_deportiva"]["distancias"]["800"]["ciudad"]
    commercial = prod["panorama"]["ejes_comerciales"]
    commercial_rank = sorted(((v["variacion_interanual_pp"], k) for k, v in commercial["comunas"].items()))
    sectors = sorted(prod["panorama"]["empresas_registradas"]["sectores"], key=lambda x:x["empresas"], reverse=True)
    debt_city = debt["caba"]["total"]
    debt_by_name = {name:row for name,row in zip(debt["barrios"],base["datos"])}

    raw = [
      draft(f"mora-maxima-{debt['periodo']}","Precios y consumo",["Endeudamiento","Mora","Barrios"],f"{mora[0][1]} presenta la mayor incidencia barrial estimada de mora",f"La proporción alcanza al {mora[0][0]:.1f}% de las personas deudoras.","BCRA y Padrón ARCA · Elaboración CEPOES","/territorio/endeudamiento/",debt["periodo"],"La mora dibuja una geografía desigual y se concentra en los barrios con menores márgenes económicos.","Estimación territorial agregada mediante matriz CP4–barrio."),
      draft(f"mora-minima-{debt['periodo']}","Precios y consumo",["Endeudamiento","Mora","Barrios"],f"{mora[-1][1]} registra la menor incidencia barrial estimada de mora",f"La proporción es {mora[-1][0]:.1f}% de las personas deudoras.","BCRA y Padrón ARCA · Elaboración CEPOES","/territorio/endeudamiento/",debt["periodo"],"El extremo inferior permite comparar la capacidad de sostener pagos entre territorios.","Estimación territorial agregada mediante matriz CP4–barrio."),
      draft(f"brecha-mora-barrios-{debt['periodo']}","Precios y consumo",["Endeudamiento","Desigualdad","Barrios"],"La incidencia de mora varía casi tres veces entre barrios porteños",f"El rango va de {mora[-1][0]:.1f}% a {mora[0][0]:.1f}% en el último período.","BCRA y Padrón ARCA · Elaboración CEPOES","/territorio/endeudamiento/",debt["periodo"],"La comparación de extremos muestra que el promedio de Ciudad oculta brechas territoriales persistentes.","Estimación territorial agregada; no identifica personas ni domicilios."),
      draft(f"mora-ciudad-{debt['periodo']}","Precios y consumo",["Endeudamiento","CABA","Mora"],f"Más de {debt_city['personas_mora']:,.0f} personas deudoras presentan mora en CABA".replace(",","."),f"Representan el {debt_city['incidencia_mora_pct']:.1f}% de las personas deudoras registradas.","BCRA · Elaboración CEPOES","/territorio/endeudamiento/",debt["periodo"],"El dato de Ciudad funciona como referencia, pero debe leerse junto con las diferencias entre barrios.","Agregado de la Central de Deudores del BCRA."),
      draft(f"la-boca-nunez-mora-{debt['periodo']}","Precios y consumo",["Endeudamiento","La Boca","Núñez"],"La mora estimada en La Boca casi triplica la de Núñez",f"Alcanza {debt_by_name['Boca'][1]/debt_by_name['Boca'][0]*100:.1f}% frente a {debt_by_name['Nunez'][1]/debt_by_name['Nunez'][0]*100:.1f}%.","BCRA y Padrón ARCA · Elaboración CEPOES","/territorio/endeudamiento/",debt["periodo"],"La comparación sintetiza cómo la desigualdad territorial condiciona la capacidad de sostener las deudas.","Estimación territorial agregada mediante matriz CP4–barrio."),
      draft(f"migracion-internacional-comuna-{intl[0][1]}-{mig['latest']['place_birth_commune_eah']}","Trabajo e ingresos",["Migraciones",f"Comuna {intl[0][1]}","EAH"],f"La Comuna {intl[0][1]} encabeza el peso de la migración internacional",f"La EAH estima que el {intl[0][0]:.1f}% de su población nació en otro país.","IDECBA · Elaboración CEPOES","/territorio/migraciones/",mig["latest"]["place_birth_commune_eah"],"La distribución territorial de la migración internacional presenta diferencias marcadas entre comunas.","EAH; las estimaciones comunales están sujetas a error muestral."),
      draft(f"migracion-interna-comuna-{internal[0][1]}-{mig['latest']['place_birth_commune_eah']}","Trabajo e ingresos",["Migraciones",f"Comuna {internal[0][1]}","Migración interna"],f"La Comuna {internal[0][1]} concentra el mayor peso de la migración interna",f"El {internal[0][0]:.1f}% de su población nació fuera de CABA pero dentro del país.","IDECBA · Elaboración CEPOES","/territorio/migraciones/",mig["latest"]["place_birth_commune_eah"],"La movilidad interna y la internacional dibujan geografías diferentes dentro de la Ciudad.","EAH; estimaciones comunales sujetas a error muestral."),
      draft(f"migracion-internacional-brecha-comunal-{mig['latest']['place_birth_commune_eah']}","Trabajo e ingresos",["Migraciones","Comunas","Desigualdad"],"El peso de la migración internacional cambia fuertemente entre comunas",f"La diferencia entre los extremos alcanza {intl[0][0]-intl[-1][0]:.1f} puntos porcentuales.","IDECBA · Elaboración CEPOES","/territorio/migraciones/",mig["latest"]["place_birth_commune_eah"],"El promedio porteño no describe por sí solo la distribución territorial de la población nacida en otro país.","EAH; estimaciones comunales sujetas a error muestral."),
      draft(f"comunidad-venezolana-{mig['countries']['year']}","Trabajo e ingresos",["Migraciones","Venezuela","Comunidades"],"Venezuela es el principal país de origen entre la población migrante relevada",f"Representa el {countries[0]['pct_2024']:.1f}% en {mig['countries']['year']}.","IDECBA · Elaboración CEPOES","/territorio/migraciones/",mig["countries"]["year"],"La composición por países cambió sustancialmente durante la última década.","Distribución porcentual de la población nacida en el exterior según EAH."),
      draft(f"pobreza-migracion-limitrofe-{mig['socioeconomic']['poverty_multidimensional']['year']}","Trabajo e ingresos",["Migraciones","Pobreza multidimensional","Condiciones de vida"],"La pobreza multidimensional alcanza al 45,2% de quienes nacieron en países limítrofes","La proporción supera ampliamente el 19,0% observado entre quienes nacieron en CABA.","IDECBA · Elaboración CEPOES","/territorio/migraciones/",mig["socioeconomic"]["poverty_multidimensional"]["year"],"El lugar de nacimiento se cruza con desigualdades persistentes en las condiciones de vida.","Indicador multidimensional de IDECBA; no equivale a pobreza monetaria."),
      draft(f"acceso-clubes-{sport['generado']}","Salud y cuidados",["Deporte y salud","Clubes de barrio","Accesibilidad"],f"Más de {club_city['poblacion_fuera_cobertura_estimada']:,.0f} porteños viven a más de 800 metros caminables de un club".replace(",","."),f"La cobertura peatonal estimada alcanza al {club_city['cobertura_pct']:.1f}% de la población.","BA Data, INDEC y OpenStreetMap · Elaboración CEPOES","/territorio/deporte-salud/",sport["generado"],"La medición sobre la red peatonal permite observar barreras que la distancia en línea recta no registra.","Radios censales 2022 y recorridos estimados sobre OpenStreetMap."),
      draft(f"clubes-comuna-{club_rank[0][1]}-{sport['generado']}","Salud y cuidados",["Deporte y salud",f"Comuna {club_rank[0][1]}","Accesibilidad"],f"Sólo el {club_rank[0][0]:.1f}% de la Comuna {club_rank[0][1]} vive a distancia caminable de un club","Es la cobertura estimada más baja entre las 15 comunas.","BA Data, INDEC y OpenStreetMap · Elaboración CEPOES","/territorio/deporte-salud/",sport["generado"],"La oferta deportiva no se traduce en el mismo nivel de proximidad en toda la Ciudad.","Cobertura a 800 metros sobre red peatonal."),
      draft(f"clubes-brecha-comunal-{sport['generado']}","Salud y cuidados",["Deporte y salud","Comunas","Brechas"],"La cobertura caminable de clubes difiere más de 60 puntos entre comunas",f"Va de {club_rank[0][0]:.1f}% a {club_rank[-1][0]:.1f}% de la población.","BA Data, INDEC y OpenStreetMap · Elaboración CEPOES","/territorio/deporte-salud/",sport["generado"],"La comparación territorial muestra que contar establecimientos no alcanza para medir acceso.","Cobertura a 800 metros sobre red peatonal."),
      draft(f"distancia-peatonal-clubes-{sport['generado']}","Salud y cuidados",["Deporte y salud","Metodología","Accesibilidad"],"La distancia en línea recta sobreestima en 14,6 puntos el acceso a clubes",f"La cobertura geométrica es {club_geom['euclidiana_pct']:.1f}% y la peatonal, {club_geom['peatonal_pct']:.1f}%.","BA Data, INDEC y OpenStreetMap · Elaboración CEPOES","/territorio/deporte-salud/",sport["generado"],"Cruces, vías y barreras urbanas modifican la accesibilidad efectiva.","Comparación entre radios euclidianos y recorridos sobre la red peatonal."),
      draft(f"polideportivos-cobertura-{sport['generado']}","Salud y cuidados",["Deporte y salud","Polideportivos","Accesibilidad"],"Menos del 10% de la población vive a un kilómetro caminable de un polideportivo público",f"La cobertura estimada es {poly_city['cobertura_pct']:.1f}%.","BA Data, INDEC y OpenStreetMap · Elaboración CEPOES","/territorio/deporte-salud/",sport["generado"],"La baja proximidad de la red pública obliga a mirar capacidad, transporte y distribución territorial.","Cobertura a 1.000 metros sobre red peatonal."),
      draft(f"empresas-registradas-{series[-1]['anio']}","Producción y comercio",["Estructura productiva","Empresas","Empleo registrado"],f"CABA registra {series[-1]['empresas']:,} empresas privadas con empleo asalariado".replace(",","."),f"Son {series[0]['empresas']-series[-1]['empresas']:,} menos que en {series[0]['anio']}.".replace(",","."),"OEDE/SIPA · Elaboración CEPOES","/territorio/estructura-productiva/",series[-1]["anio"],"La serie permite observar la evolución del stock de empresas privadas registradas.","Empresas privadas con empleo asalariado registrado según OEDE/SIPA."),
      draft(f"caida-empresas-2015-{series[-1]['anio']}","Producción y comercio",["Estructura productiva","Empresas","Serie histórica"],"La Ciudad perdió más de 8.000 empresas privadas registradas desde 2015",f"El stock pasó de {series[0]['empresas']:,} a {series[-1]['empresas']:,}.".replace(",","."),"OEDE/SIPA · Elaboración CEPOES","/territorio/estructura-productiva/",series[-1]["anio"],"La recuperación posterior a 2020 no alcanzó para volver al nivel de 2015.","Empresas privadas con empleo asalariado registrado según OEDE/SIPA."),
      draft(f"vacancia-comercial-{commercial['periodo']['anio']}-{commercial['periodo']['cuatrimestre']}","Producción y comercio",["Comercio urbano","Locales","Vacancia"],f"Uno de cada diez locales relevados en los ejes comerciales porteños no está ocupado",f"Son {commercial['locales_relevados']-commercial['locales_ocupados']:,} sobre {commercial['locales_relevados']:,} locales.".replace(",","."),"IDECBA · Elaboración CEPOES","/territorio/estructura-productiva/",commercial["periodo"]["anio"],"La vacancia comercial funciona como señal de actividad, pero no representa a todos los locales de la Ciudad.","Relevamiento de 48 ejes comerciales de IDECBA."),
      draft(f"ocupacion-comercial-comuna-{commercial_rank[0][1]}-{commercial['periodo']['anio']}","Producción y comercio",["Comercio urbano",f"Comuna {commercial_rank[0][1]}","Locales"],f"La Comuna {commercial_rank[0][1]} registra la mayor caída interanual de ocupación comercial",f"La variación fue de {commercial_rank[0][0]:.1f} puntos porcentuales.","IDECBA · Elaboración CEPOES","/territorio/estructura-productiva/",commercial["periodo"]["anio"],"La evolución por comuna permite detectar cambios que se pierden en el promedio porteño.","Relevamiento de ejes comerciales; no equivale al universo completo de locales."),
      draft(f"principal-sector-empresas-{series[-1]['anio']}","Producción y comercio",["Estructura productiva","Empresas","Servicios"],"Los servicios inmobiliarios y empresariales reúnen más de 55.000 empresas registradas",f"Es el sector más numeroso, con {sectors[0]['empresas']:,} firmas.".replace(",","."),"OEDE/SIPA · Elaboración CEPOES","/territorio/estructura-productiva/",series[-1]["anio"],"La estructura empresarial porteña mantiene una fuerte especialización en servicios.","Empresas privadas con empleo asalariado registrado según OEDE/SIPA.")
    ]
    for d in raw:
        d.update({"facts":[],"quote":""})
        d["source_hash"] = hashlib.sha256(json.dumps(d,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if not FUNCTION_URL:
        print(json.dumps({"drafts":raw},ensure_ascii=False,indent=2)); return
    base=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL"); token=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not base or not token: raise RuntimeError("GitHub OIDC no está disponible")
    sep="&" if "?" in base else "?"
    oidc_req=Request(f"{base}{sep}audience={OIDC_AUDIENCE}",headers={"Authorization":f"Bearer {token}"})
    with urlopen(oidc_req,timeout=30) as response: oidc=json.loads(response.read())["value"]
    results=[]
    for start in range(0,len(raw),5):
        batch=raw[start:start+5]
        ingest_req=Request(FUNCTION_URL,data=json.dumps({"drafts":batch}).encode(),headers={"Authorization":f"Bearer {oidc}","Content-Type":"application/json"},method="POST")
        with urlopen(ingest_req,timeout=30) as response: results.append(json.loads(response.read()))
    print(f"Bandeja privada · {len(raw)} borradores · {results}")

if __name__ == "__main__":
    main()
