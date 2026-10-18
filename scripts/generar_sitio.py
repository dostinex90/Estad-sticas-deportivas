"""Genera la versión web estática (carpeta sitio/) que se publica en GitHub Pages.

Una web estática no puede ejecutar Python, así que se calculan de antemano las respuestas
de la API para la temporada actual de las ligas principales y de la NFL (incluidas las
predicciones de todos los partidos posibles) y se guardan como archivos JSON. La interfaz
es la misma que la de `python3 -m analisis_deportivo web`, en modo estático.

Uso: python3 scripts/generar_sitio.py [carpeta_destino]
"""

import itertools
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo.web import api  # noqa: E402

LIGAS = ["SP1", "E0", "I1", "D1", "F1", "P1", "N1"]
ESTATICOS = RAIZ / "analisis_deportivo" / "web" / "static"


def slug(nombre):
    """Debe coincidir con slug() de app.js."""
    return re.sub(r"[^A-Za-z0-9]+", "_", str(nombre)).strip("_") or "_"


class Sitio:
    def __init__(self, destino):
        self.destino = destino
        self.archivos = 0

    def guardar(self, ruta, datos):
        archivo = self.destino / "api" / f"{ruta}.json"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        self.archivos += 1


def futbol(sitio, opciones_completas):
    competiciones = []
    for liga in LIGAS:
        info = next((c for c in opciones_completas["competiciones"] if c["codigo"] == liga), None)
        if not info:
            continue
        q = {"liga": liga}
        tabla = api.futbol_tabla(q)
        temporada = tabla["descripcion"].split(" · ")[-1]
        competiciones.append({**info, "temporadas": [temporada]})
        sitio.guardar(f"futbol/tabla/{liga}", tabla)
        for condicion in ("local", "visitante", "descanso"):
            sitio.guardar(f"futbol/tabla/{liga}-{condicion}", api.futbol_tabla({**q, "condicion": condicion}))
        equipos = api.futbol_equipos(q)
        sitio.guardar(f"futbol/equipos/{liga}", equipos)
        for ruta in ("liga", "ranking", "pronosticos"):
            sitio.guardar(f"futbol/{ruta}/{liga}", api.ejecutar(f"futbol/{ruta}", q))
        jugados = {f["equipo"] for f in tabla["filas"]}
        for equipo in equipos["equipos"]:
            if equipo in jugados:
                sitio.guardar(f"futbol/equipo/{liga}/{slug(equipo)}", api.futbol_equipo({**q, "equipo": equipo}))
        for local, visitante in itertools.permutations(equipos["equipos"], 2):
            sitio.guardar(f"futbol/predecir/{liga}/{slug(local)}__{slug(visitante)}",
                          api.futbol_predecir({**q, "local": local, "visitante": visitante}))
        # Cara a cara con todo el historial; un archivo por pareja (orden alfabético, la web lo invierte si hace falta)
        for a, b in itertools.combinations(sorted(equipos["equipos"]), 2):
            sitio.guardar(f"futbol/h2h/{liga}/{slug(a)}__{slug(b)}", api.futbol_h2h({"liga": liga, "a": a, "b": b}))
        print(f"  {info['nombre']}: {len(equipos['equipos'])} equipos")
    sitio.guardar("futbol/opciones", {"competiciones": competiciones, "torneos": [], "anios_selecciones": []})


def nfl(sitio):
    opciones = api.nfl_opciones({})
    temporada = opciones["temporadas"][0]
    q = {"temporada": str(temporada)}
    sitio.guardar("nfl/opciones", {**opciones, "temporadas": [temporada]})
    for ruta in ("clasificacion", "ranking", "liga", "simular"):
        sitio.guardar(f"nfl/{ruta}/{temporada}", api.ejecutar(f"nfl/{ruta}", q))
    try:
        sitio.guardar(f"nfl/estadisticas/{temporada}", api.nfl_estadisticas(q))
    except ValueError:
        pass  # aún no hay estadísticas de juego de esta temporada
    pron = api.nfl_pronosticos(q)
    sitio.guardar(f"nfl/pronosticos/{temporada}", pron)
    for semana in pron.get("semanas") or []:
        sitio.guardar(f"nfl/pronosticos/{temporada}-{semana}", api.nfl_pronosticos({**q, "semana": str(semana)}))
    codigos = [e["codigo"] for e in opciones["equipos"]]
    for equipo in codigos:
        try:
            sitio.guardar(f"nfl/equipo/{temporada}/{equipo}", api.nfl_equipo({**q, "equipo": equipo}))
        except ValueError:
            pass  # equipo sin partidos todavía
    for local, visitante in itertools.permutations(codigos, 2):
        sitio.guardar(f"nfl/predecir/{temporada}/{local}__{visitante}",
                      api.nfl_predecir({**q, "local": local, "visitante": visitante}))
    print(f"  NFL {temporada}: {len(codigos)} equipos")


def generar(destino):
    if destino.exists():
        shutil.rmtree(destino)
    destino.mkdir(parents=True)
    for nombre in ("index.html", "app.js", "estilos.css"):
        shutil.copy(ESTATICOS / nombre, destino / nombre)
    sello = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    (destino / "config.js").write_text(
        f'window.MODO_ESTATICO = {{actualizado: "{sello}"}};\n', encoding="utf-8")
    html = (destino / "index.html").read_text(encoding="utf-8")
    (destino / "index.html").write_text(html.replace('<script src="app.js">', '<script src="config.js"></script>\n  <script src="app.js">'),
                                        encoding="utf-8")
    sitio = Sitio(destino)
    print("Generando la web estática...")
    futbol(sitio, api.futbol_opciones({}))
    nfl(sitio)
    tam = sum(f.stat().st_size for f in destino.rglob("*") if f.is_file())
    print(f"Web generada en {destino}: {sitio.archivos:,} archivos de datos, {tam / 1e6:.1f} MB ({sello})")


if __name__ == "__main__":
    generar(Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "sitio")
