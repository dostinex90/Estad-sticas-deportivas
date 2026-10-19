"""Ajuste del modelo NBA con 2012-13 a 2018-19 y validación en 2021-22 a 2025-26.

Uso:  python3 experimentos/nba_ajuste.py             (búsqueda + validación, ~10 min con 4 núcleos)
      python3 experimentos/nba_ajuste.py --verificar (solo línea base frente al modelo del paquete)

Las temporadas 2019-20 (burbuja) y 2020-21 (sin público, 72 partidos) no se usan ni para
ajustar ni para validar, pero sí como historial previo.

1. Componentes: para cada partido se calcula, solo con partidos anteriores a ese día, el margen
   del Elo, el de los ratings y quién juega dos días seguidos.
2. Búsqueda (solo entrenamiento): primero Elo (K, ventaja de campo, regresión) y ratings (vida
   media, peso de la temporada anterior, regularización); con los mejores, el peso de la mezcla,
   la penalización por jugar dos días seguidos y la desviación de la normal.
3. Validación: línea base (Elo al estilo FiveThirtyEight con sus parámetros publicados: K=20,
   +100 de campo, regresión 1/4, probabilidad logística) frente a modelos.evaluar del paquete.
La NBA no tiene líneas de apuestas en la base: no se usan en ningún caso.
"""

import itertools
import math
import sys
from multiprocessing import Pool
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo import base  # noqa: E402
from analisis_deportivo.comun import normal_cdf  # noqa: E402
from analisis_deportivo.nba import modelos  # noqa: E402
from analisis_deportivo.nba.datos import cargar_desde_base, descansos  # noqa: E402

ENTRENAMIENTO = list(range(2013, 2020))  # 2012-13 a 2018-19
VALIDACION = list(range(2022, 2027))  # 2021-22 a 2025-26
PARTIDOS = None


def _partidos():
    global PARTIDOS
    if PARTIDOS is None:
        PARTIDOS = cargar_desde_base(base.conectar())
    return PARTIDOS


def componentes(temporada, elo_params, ratings_params):
    """[(margen Elo, prob. Elo, margen ratings, b2b visitante - b2b local, margen real)] de la temporada."""
    partidos = _partidos()
    jug = sorted((p for p in partidos if p.jugado and p.temporada <= temporada), key=lambda p: p.fecha)
    objetivo = [p for p in jug if p.temporada == temporada]
    dias = descansos([p for p in partidos if p.temporada == temporada])
    elo, ratings = modelos.EloNBA(**elo_params), modelos.RatingsNBA(**ratings_params)
    idx, primera, res = 0, True, []
    for fecha in sorted({p.fecha for p in objetivo}):
        while idx < len(jug) and jug[idx].fecha < fecha:
            elo.actualizar(jug[idx])
            idx += 1
        elo.nueva_temporada(temporada)
        ratings.ajustar(jug[:idx] if primera else jug[max(0, idx - 3000):idx], temporada, fecha)
        if primera:
            ratings.iteraciones, primera = 8, False
        for p in (p for p in objetivo if p.fecha == fecha):
            pl, pv = ratings.puntos(p.local, p.visitante, p.neutral)
            b2b = (dias.get((p.id, p.visitante)) == 1) - (dias.get((p.id, p.local)) == 1)
            res.append((elo.margen(p.local, p.visitante, p.neutral), elo.prob_local(p.local, p.visitante, p.neutral),
                        pl - pv, b2b, p.margen))
    return res


def _tarea(args):
    temporada, elo_params, ratings_params = args
    return componentes(temporada, elo_params, ratings_params)


def todos(pool, temporadas, elo_params, ratings_params):
    return [c for lista in pool.map(_tarea, [(t, elo_params, ratings_params) for t in temporadas]) for c in lista]


def brier(comp, peso_elo, b2b, sigma):
    return sum((normal_cdf(peso_elo * me + (1 - peso_elo) * mr + b2b * d, 0, sigma) - (real > 0)) ** 2
               for me, _, mr, d, real in comp) / len(comp)


def mejor_mezcla(comp):
    """Peso de la mezcla, b2b y desviación con menor Brier (búsqueda en rejilla)."""
    rejilla = itertools.product([0.0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0], [0.0, 1.0, 1.5, 2.0, 2.5, 3.0],
                                [8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0])
    return min((brier(comp, *g), g) for g in rejilla)


def metricas(comp, peso_elo, b2b, sigma):
    n = len(comp)
    probs = [normal_cdf(peso_elo * me + (1 - peso_elo) * mr + b2b * d, 0, sigma) for me, _, mr, d, _ in comp]
    reales = [real > 0 for *_, real in comp]
    return {"n": n, "brier": sum((p - r) ** 2 for p, r in zip(probs, reales)) / n,
            "logloss": -sum(math.log(p if r else 1 - p) for p, r in zip(probs, reales)) / n,
            "acierto": sum((p > 0.5) == r for p, r in zip(probs, reales)) / n}


def linea_base(comp):
    n = len(comp)
    return {"n": n, "brier": sum((pe - (real > 0)) ** 2 for _, pe, _, _, real in comp) / n,
            "logloss": -sum(math.log(pe if real > 0 else 1 - pe) for _, pe, _, _, real in comp) / n,
            "acierto": sum((pe > 0.5) == (real > 0) for _, pe, _, _, real in comp) / n}


ELO_BASE = {"k": 20, "ventaja_campo": 100, "regresion": 0.25}


def buscar(pool):
    ratings = {"vida_media": 60, "peso_temporada_anterior": 0.5, "regularizacion": 3.0}
    elo = dict(ELO_BASE)
    print("Búsqueda en entrenamiento (2012-13 a 2018-19), Brier tras optimizar la mezcla:")
    mejor = mejor_mezcla(todos(pool, ENTRENAMIENTO, elo, ratings))
    print(f"  inicial {elo} {ratings}: {mejor[0]:.5f} {mejor[1]}")
    candidatos = [("k", [15, 25, 30]), ("ventaja_campo", [70, 85, 115]), ("regresion", [0.33, 0.4, 0.5]),
                  ("vida_media", [30, 45, 90, 120]), ("peso_temporada_anterior", [0.3, 0.7, 1.0]),
                  ("regularizacion", [1.0, 6.0, 10.0])]
    for clave, valores in candidatos:
        destino = elo if clave in elo else ratings
        for v in valores:
            prueba = dict(destino, **{clave: v})
            e, r = (prueba, ratings) if destino is elo else (elo, prueba)
            res = mejor_mezcla(todos(pool, ENTRENAMIENTO, e, r))
            print(f"  {clave}={v}: {res[0]:.5f} {res[1]}")
            if res[0] < mejor[0] - 1e-5:
                mejor = res
                destino[clave] = v
        print(f"  → {clave} = {destino[clave]}")
    print(f"\nElegido: Elo {elo} · ratings {ratings} · (peso Elo, b2b, desviación) = {mejor[1]}")
    return elo, ratings, mejor[1]


def validar(pool, elo, ratings, mezcla):
    print("\nTemporada   Partidos  Brier base  Brier nuevo  Log-loss base/nuevo  Acierto base/nuevo")
    for nombre, temporadas in (("Entrenamiento", ENTRENAMIENTO), ("Validación", VALIDACION)):
        totales = [[], []]
        for t in temporadas:
            comp = todos(pool, [t], elo, ratings)
            comp_base = todos(pool, [t], ELO_BASE, ratings)
            b, m = linea_base(comp_base), metricas(comp, *mezcla)
            totales[0] += comp_base
            totales[1] += comp
            print(f"  {t - 1}-{str(t)[2:]}   {m['n']:>8}  {b['brier']:.4f}      {m['brier']:.4f}       "
                  f"{b['logloss']:.4f}/{m['logloss']:.4f}      {b['acierto']:.3f}/{m['acierto']:.3f}")
        b, m = linea_base(totales[0]), metricas(totales[1], *mezcla)
        print(f"  {nombre}: {m['n']} partidos · Brier {b['brier']:.4f} → {m['brier']:.4f} · "
              f"log-loss {b['logloss']:.4f} → {m['logloss']:.4f} · acierto {b['acierto']:.3f} → {m['acierto']:.3f}\n")


if __name__ == "__main__":
    with Pool() as pool:
        if "--verificar" in sys.argv:
            e, r = modelos.EloNBA(), modelos.RatingsNBA()  # los valores por defecto del paquete
            parametros = ({"k": e.k, "ventaja_campo": e.ventaja_campo, "regresion": e.regresion},
                          {"vida_media": r.vida_media, "peso_temporada_anterior": r.peso_anterior,
                           "regularizacion": r.regularizacion},
                          (modelos.PESO_ELO, modelos.PUNTOS_B2B, modelos.DESVIACION_PROB))
        else:
            parametros = buscar(pool)
        validar(pool, *parametros)
