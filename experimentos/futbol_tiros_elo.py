"""Evaluación walk-forward del ModeloPoisson con tiros a puerta ("xG aproximado") y Elo previo.

Protocolo: ligas E0, SP1, I1, D1, F1. Cada temporada se evalúa con modelos.evaluar(partidos, minimo=0,
previos=temporada anterior), como el CLI. Los parámetros se eligen con las temporadas de
entrenamiento (2018-19 a 2022-23) y se informan en validación (2023-24 a 2025-26).

Uso:
  python3 experimentos/futbol_tiros_elo.py            # rejilla en entrenamiento + validación
  python3 experimentos/futbol_tiros_elo.py --rapido   # solo línea base y configuración elegida en validación
"""

import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analisis_deportivo import base  # noqa: E402
from analisis_deportivo.futbol import modelos  # noqa: E402
from analisis_deportivo.futbol.datos import cargar_desde_base, jugados  # noqa: E402

LIGAS = ["E0", "SP1", "I1", "D1", "F1"]
ENTRENAMIENTO = ["2018-19", "2019-20", "2020-21", "2021-22", "2022-23"]
VALIDACION = ["2023-24", "2024-25", "2025-26"]

BASE = {"peso_tiros": 0.0, "peso_elo": 0.0}  # equivale al código original
REJILLA = [
    {"peso_tiros": t, "peso_elo": e}
    for t in (0.0, 0.3, 0.5, 0.7)
    for e in (0.0, 0.3, 0.5, 0.7, 0.9)
]
ELEGIDA = {"peso_tiros": 0.7, "peso_elo": 0.7}  # mejor RPS de la rejilla en entrenamiento (valores por defecto del modelo)

_CACHE = {}


def _cargar(liga, temporada):
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
    liga, temporada, opciones = args
    partidos, previos = _cargar(liga, temporada)
    r = modelos.evaluar(partidos, minimo=0, previos=previos, **opciones)
    return liga, temporada, tuple(sorted(opciones.items())), r


def _resumen(resultados):
    """Promedia las métricas ponderando por número de partidos."""
    tot = {"n": 0, "rps": 0.0, "logloss": 0.0, "brier": 0.0, "aciertos": 0, "mercado_rps": 0.0, "n_mercado": 0,
           "modelo_vs_mercado_rps": 0.0}
    for r in resultados:
        m = r["modelo"]
        tot["n"] += m["n"]
        tot["aciertos"] += m["aciertos"]
        for c in ("rps", "logloss", "brier"):
            tot[c] += m[c] * m["n"]
        tot["n_mercado"] += r["mercado"]["n"]
        tot["mercado_rps"] += r["mercado"]["rps"] * r["mercado"]["n"]
        tot["modelo_vs_mercado_rps"] += r["modelo_vs_mercado"]["rps"] * r["modelo_vs_mercado"]["n"]
    n, nm = tot["n"], max(tot["n_mercado"], 1)
    return {"n": n, "rps": tot["rps"] / n, "logloss": tot["logloss"] / n, "brier": tot["brier"] / n,
            "acierto": 100 * tot["aciertos"] / n, "n_mercado": tot["n_mercado"],
            "rps_mercado": tot["mercado_rps"] / nm, "rps_modelo_mismos": tot["modelo_vs_mercado_rps"] / nm}


def ejecutar(configs, temporadas, procesos=4):
    tareas = [(l, t, c) for c in configs for l in LIGAS for t in temporadas]
    agrupado = {}
    with Pool(procesos) as pool:
        for liga, temporada, clave, r in pool.imap_unordered(_tarea, tareas, chunksize=1):
            agrupado.setdefault(clave, []).append(r)
    return {clave: _resumen(rs) for clave, rs in agrupado.items()}


def _imprimir(titulo, resumenes):
    print(f"\n{titulo}")
    print(f"  {'configuración':<38}{'n':>6}{'RPS':>9}{'logloss':>9}{'Brier':>8}{'acierto':>9}{'RPS merc.':>11}")
    for clave, s in sorted(resumenes.items(), key=lambda kv: kv[1]["rps"]):
        nombre = ", ".join(f"{k}={v}" for k, v in clave)
        print(f"  {nombre:<38}{s['n']:>6}{s['rps']:>9.5f}{s['logloss']:>9.4f}{s['brier']:>8.4f}"
              f"{s['acierto']:>8.2f}%{s['rps_mercado']:>11.5f}")


def main():
    base.conectar()  # descomprime la base antes de lanzar procesos
    inicio = time.time()
    if "--rapido" not in sys.argv:
        ent = ejecutar(REJILLA, ENTRENAMIENTO)
        _imprimir("ENTRENAMIENTO 2018-19 a 2022-23 (para elegir parámetros)", ent)
        mejor = min(ent.items(), key=lambda kv: kv[1]["rps"])[0]
        print(f"  mejor en entrenamiento: {dict(mejor)} (fijada en el código: {ELEGIDA})")
    val = ejecutar([BASE, ELEGIDA], VALIDACION)
    _imprimir("VALIDACIÓN 2023-24 a 2025-26 (holdout)", val)
    b, e = val[tuple(sorted(BASE.items()))], val[tuple(sorted(ELEGIDA.items()))]
    print(f"\n  RPS línea base {b['rps']:.5f} -> nuevo {e['rps']:.5f} ({e['rps'] - b['rps']:+.5f}); "
          f"mercado {b['rps_mercado']:.5f} en {b['n_mercado']} partidos")
    print(f"  ({time.time() - inicio:.0f} s)")


if __name__ == "__main__":
    main()
