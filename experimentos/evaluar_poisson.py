"""Evaluación walk-forward de ModeloPoisson en las cinco grandes ligas.

Protocolo: para cada liga y temporada se carga la temporada con cargar_desde_base y la
anterior como 'previos' (igual que el CLI) y se llama a modelos.evaluar(partidos, minimo=0,
previos=previos). Cada predicción solo usa partidos de fechas anteriores; las cuotas solo
se usan para la referencia del mercado.

La línea base es modelos.py tal como estaba antes de los cambios (copia en
experimentos/modelos_linea_base.py, sacada del commit ac7e457).

Uso:
  python3 experimentos/evaluar_poisson.py                         # línea base vs. nuevo (validación)
  python3 experimentos/evaluar_poisson.py --tramo entrenamiento
  python3 experimentos/evaluar_poisson.py --opciones '{"vida_media_dias": 180}'   # variantes nuevas
"""

import argparse
import importlib.util
import json
import sys
from multiprocessing import Pool
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent))

from analisis_deportivo import base  # noqa: E402
from analisis_deportivo.futbol import modelos  # noqa: E402
from analisis_deportivo.futbol.datos import cargar_desde_base, jugados  # noqa: E402

LIGAS = ["E0", "SP1", "I1", "D1", "F1"]
TRAMOS = {
    "entrenamiento": ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23"],
    "validacion": ["2023-24", "2024-25", "2025-26"],
}
_CACHE = {}
_MODULOS = {}


def _modelos(variante):
    if variante == "nuevo":
        return modelos
    if "base" not in _MODULOS:
        # Se importa dentro del paquete para que funcionen sus imports relativos
        spec = importlib.util.spec_from_file_location("analisis_deportivo.futbol._modelos_linea_base",
                                                      AQUI / "modelos_linea_base.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _MODULOS["base"] = mod
    return _MODULOS["base"]


def cargar(liga, temporada):
    """(partidos de la temporada, partidos jugados de la temporada anterior), como hace el CLI."""
    clave = (liga, temporada)
    if clave not in _CACHE:
        con = base.conectar()
        partidos, _ = cargar_desde_base(con, liga, temporada)
        anterior = con.execute("SELECT MAX(temporada) FROM futbol_partidos WHERE competicion = ? AND temporada < ?",
                               (liga, temporada)).fetchone()[0]
        previos = jugados(cargar_desde_base(con, liga, anterior)[0]) if anterior else []
        _CACHE[clave] = (partidos, previos)
    return _CACHE[clave]


def _tarea(args):
    nombre, variante, opciones, liga, temporada = args
    partidos, previos = cargar(liga, temporada)
    r = _modelos(variante).evaluar(partidos, minimo=0, previos=previos, **opciones)
    return nombre, liga, temporada, {k: r[k] for k in ("modelo", "mercado", "modelo_vs_mercado")}


def _sumar(lista):
    tot = {"n": 0, "aciertos": 0, "brier": 0.0, "logloss": 0.0, "rps": 0.0}
    for m in lista:
        tot["n"] += m["n"]
        tot["aciertos"] += m["aciertos"]
        for c in ("brier", "logloss", "rps"):
            tot[c] += m[c] * m["n"]
    for c in ("brier", "logloss", "rps"):
        tot[c] /= max(tot["n"], 1)
    tot["acierto"] = tot["aciertos"] / max(tot["n"], 1)
    return tot


def evaluar_variantes(variantes, temporadas, procesos=4):
    """variantes: {nombre: ("base" | "nuevo", opciones)} -> {nombre: métricas agregadas}."""
    tareas = [(n, v, o, liga, t) for n, (v, o) in variantes.items() for liga in LIGAS for t in temporadas]
    with Pool(procesos) as pool:
        salida = pool.map(_tarea, tareas, chunksize=1)
    res = {}
    for nombre in variantes:
        filas = [(l, r) for n, l, _, r in salida if n == nombre]
        res[nombre] = {
            "total": _sumar([r["modelo"] for _, r in filas]),
            "mercado": _sumar([r["mercado"] for _, r in filas]),
            "modelo_vs_mercado": _sumar([r["modelo_vs_mercado"] for _, r in filas]),
            "por_liga": {liga: _sumar([r["modelo"] for l, r in filas if l == liga]) for liga in LIGAS},
        }
    return res


def linea(nombre, m):
    return (f"{nombre:<44} n={m['n']:>5}  RPS={m['rps']:.5f}  logloss={m['logloss']:.5f}  "
            f"Brier={m['brier']:.5f}  acierto={m['acierto']:.2%}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tramo", choices=list(TRAMOS), default="validacion")
    ap.add_argument("--opciones", nargs="*", help="JSON con opciones de ModeloPoisson (una variante por argumento)")
    ap.add_argument("--sin-base", action="store_true", help="no evaluar la línea base")
    ap.add_argument("--por-liga", action="store_true")
    ap.add_argument("--procesos", type=int, default=4)
    a = ap.parse_args()
    temporadas = TRAMOS[a.tramo]
    variantes = {} if a.sin_base else {"linea base (ac7e457)": ("base", {})}
    if a.opciones:
        for texto in a.opciones:
            variantes[texto] = ("nuevo", json.loads(texto))
    else:
        variantes["nuevo (valores por defecto)"] = ("nuevo", {})
    res = evaluar_variantes(variantes, temporadas, a.procesos)
    print(f"Tramo: {a.tramo} ({', '.join(temporadas)}) · ligas {', '.join(LIGAS)}")
    for nombre, r in res.items():
        print(linea(nombre, r["total"]))
        if a.por_liga or not a.opciones:
            for liga, m in r["por_liga"].items():
                print("   " + linea(liga, m))
    print(linea("mercado (cuotas sin margen)", next(iter(res.values()))["mercado"]))


if __name__ == "__main__":
    main()
