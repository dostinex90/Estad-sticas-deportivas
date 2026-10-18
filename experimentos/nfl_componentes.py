"""Componentes de predicción NFL calculados semana a semana sin datos futuros.

Replica exactamente el procedimiento de modelos.evaluar (Elo actualizado con los partidos
anteriores al inicio de cada semana, ratings reajustados cada semana con los partidos previos),
pero guarda por partido los márgenes de cada modelo para poder probar mezclas, desviaciones
y ajustes sin repetir los reajustes. Las líneas de apuestas solo se guardan para comparar.
"""

import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analisis_deportivo import base  # noqa: E402
from analisis_deportivo.nfl import datos, modelos  # noqa: E402

ENTRENAMIENTO = range(2012, 2020)
VALIDACION = range(2020, 2026)
_JUEGOS = None


def juegos():
    global _JUEGOS
    if _JUEGOS is None:
        _JUEGOS = datos.cargar_desde_base(base.conectar())
    return _JUEGOS


def jugados():
    return sorted((j for j in juegos() if j.jugado), key=lambda j: j.fecha)


def semanas(jug, temporadas):
    """[(temporada, partidos de la semana, fecha de inicio)] en orden cronológico."""
    res = []
    for t in temporadas:
        obj = [j for j in jug if j.temporada == t]
        for clave in sorted({(j.tipo != "REG", j.semana) for j in obj}):
            de_semana = [j for j in obj if (j.tipo != "REG", j.semana) == clave]
            res.append((t, de_semana, min(j.fecha for j in de_semana)))
    return res


def margenes_elo(temporadas, crear_elo, margen=None):
    """{id: margen Elo previo} con el Elo que devuelve crear_elo(). `margen(elo, j)` permite
    predicciones con información extra previa al partido (descanso, QB...)."""
    jug = jugados()
    elo = crear_elo()
    idx = 0
    res = {}
    for t, de_semana, inicio in semanas(jug, temporadas):
        while idx < len(jug) and jug[idx].fecha < inicio:
            elo.actualizar(jug[idx])
            idx += 1
        elo._nueva_temporada(t)
        for j in de_semana:
            res[j.id] = margen(elo, j) if margen else elo.margen(j.local, j.visitante, j.neutral)
    return res


def margenes_ratings(temporadas, crear_ratings):
    """{id: (margen, total, ventaja de campo estimada)} de los ratings reajustados cada semana con los partidos previos."""
    jug = jugados()
    idx = 0
    res = {}
    for t, de_semana, inicio in semanas(jug, temporadas):
        while idx < len(jug) and jug[idx].fecha < inicio:
            idx += 1
        r = crear_ratings().ajustar(jug[:idx], t)
        for j in de_semana:
            pl, pv = r.puntos(j.local, j.visitante, j.neutral)
            res[j.id] = (pl - pv, pl + pv, r.ventaja_campo)
    return res


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def metricas(partidos, margen, sigma):
    """Métricas de un conjunto de partidos dado {id: margen predicho} y la desviación típica."""
    m = defaultdict(float)
    for j in partidos:
        if j.margen == 0:
            continue
        mg = margen[j.id]
        p = min(max(phi(mg / sigma), 1e-9), 1 - 1e-9)
        y = j.margen > 0
        m["n"] += 1
        m["brier"] += (p - y) ** 2
        m["logloss"] -= math.log(p if y else 1 - p)
        m["acierto"] += (mg > 0) == y
        m["error_margen"] += abs(j.margen - mg)
        if j.linea is not None:
            m["n_linea"] += 1
            m["error_linea"] += abs(j.margen - j.linea)
            m["error_modelo_linea"] += abs(j.margen - mg)
            if j.linea != 0:
                m["n_fav"] += 1
                m["acierto_mercado"] += (j.linea > 0) == y
            v = mg - j.linea
            if v != 0 and j.margen != j.linea:
                m["ats_n"] += 1
                m["ats"] += (v > 0) == (j.margen > j.linea)
    n = m["n"]
    return {
        "n": int(n),
        "brier": m["brier"] / n,
        "logloss": m["logloss"] / n,
        "acierto": 100 * m["acierto"] / n,
        "error_margen": m["error_margen"] / n,
        "acierto_mercado": 100 * m["acierto_mercado"] / max(m["n_fav"], 1),
        "error_modelo_linea": m["error_modelo_linea"] / max(m["n_linea"], 1),
        "error_linea": m["error_linea"] / max(m["n_linea"], 1),
        "ats": 100 * m["ats"] / max(m["ats_n"], 1),
    }


def de_temporadas(temporadas):
    ts = set(temporadas)
    return [j for j in jugados() if j.temporada in ts]


if __name__ == "__main__":
    # Comprobación: la reimplementación coincide con modelos.evaluar en una temporada.
    t = int(sys.argv[1]) if len(sys.argv) > 1 else 2020
    e = margenes_elo([t], modelos.EloNFL)
    r = margenes_ratings([t], modelos.RatingsNFL)
    mg = {k: 0.5 * e[k] + 0.5 * r[k][0] for k in e}
    mi = metricas(de_temporadas([t]), mg, modelos.DESVIACION_MARGEN)
    ref = modelos.evaluar(juegos(), t)
    print("reimplementación", mi["brier"], " evaluar", ref["brier"] / ref["n"])
