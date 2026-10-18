"""Ajuste de los modelos NFL con 2012-2019 y validación en 2020-2025.

Uso:  python3 experimentos/nfl_ajuste.py            (búsqueda + verificación, ~5 min)
      python3 experimentos/nfl_ajuste.py --verificar (solo compara línea base y paquete con modelos.evaluar)

1. Búsqueda (solo partidos de 2012-2019): ratings (peso temporada anterior, regularización),
   Elo (K, ventaja de campo, regresión, multiplicador por margen), y después, de forma conjunta,
   peso de la mezcla, desviación típica, descanso, bye, playoffs y cambio/valor del QB titular.
2. Verificación: la línea base es modelos.evaluar del commit original (cargado desde git) y el
   modelo nuevo es modelos.evaluar del paquete actual, ambos en 2012-2019 y 2020-2025.
Las líneas de apuestas solo se usan para comparar.
"""

import importlib.util
import itertools
import subprocess
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import nfl_componentes as c  # noqa: E402
import nfl_explorar as x  # noqa: E402
from analisis_deportivo.nfl import modelos  # noqa: E402

COMMIT_BASE = "b915cd3"  # código original sin cambios
PARAMS_BASE = {"peso_elo": 0.5, "sigma": 13.5, "campo": 48}
REJ = dict(x.REJ, campo=[None])


def _ratings(args):
    return args, c.margenes_ratings(x.TODAS, lambda: modelos.RatingsNFL(*args))


def buscar():
    c.juegos()
    ent = c.de_temporadas(c.ENTRENAMIENTO)
    x.ENT = ent
    variantes = {(m0, pr): x.rasgos(m0=m0, previo=pr) for m0 in (150, 400) for pr in (-0.15, -0.05)}
    ras0 = variantes[(400, -0.05)]
    elo_base = dict(k=20, ventaja_campo=48, regresion=1 / 3, mov=2.2)
    elo0 = x.elo_sin_campo(elo_base)
    with Pool(4) as pool:
        rats = dict(pool.map(_ratings, [(a, b) for a in (0.15, 0.3, 0.45, 0.6) for b in (1.0, 2.0, 4.0, 8.0)]))

    def opt(elo, rat, ras, p, claves, rondas=2):
        return x.optimizar(elo, rat, ras, p, claves, REJ, ent, rondas)

    print("Brier de entrenamiento (2012-2019) de la línea base:", round(x.brier(elo0, rats[(0.3, 2.0)], ras0, PARAMS_BASE, ent), 5))
    # 1) ratings
    res = sorted(((opt(elo0, r, ras0, PARAMS_BASE, ["peso_elo", "sigma"])[1], k) for k, r in rats.items()))
    rat_k = res[0][1]
    print("1) ratings (peso anterior, regularización):", rat_k, round(res[0][0], 5))
    rat = rats[rat_k]
    # 2) Elo
    res = []
    for kk, hfa, reg, mov in itertools.product((16, 20, 24), (48, 60, 72, 84, 96), (1 / 3, 0.45, 0.6), (2.2, 3.0)):
        ep = dict(k=kk, ventaja_campo=hfa, regresion=reg, mov=mov)
        b = opt(x.elo_sin_campo(ep), rat, ras0, dict(PARAMS_BASE, campo=hfa), ["peso_elo", "sigma"])[1]
        res.append((b, ep))
    res.sort(key=lambda t: t[0])
    elo_p = res[0][1]
    print("2) Elo:", elo_p, round(res[0][0], 5))
    elo = x.elo_sin_campo(elo_p)
    # 3) mezcla, desviación y ajustes, conjuntamente, para cada variante del valor del QB
    claves = ["peso_elo", "sigma", "b_descanso", "b_bye", "b_qb", "b_qb_valor", "f_playoff"]
    res = []
    for k, ras in variantes.items():
        p, b = opt(elo, rat, ras, dict(PARAMS_BASE, campo=elo_p["ventaja_campo"]), claves, rondas=3)
        print("   valor QB (m0, previo)", k, round(b, 5), p)
        res.append((b, k, p))
    res.sort(key=lambda t: t[0])
    b, k, p = res[0]
    print("3) elegido:", {"qb_m0": k[0], "qb_previo": k[1], **p}, "Brier ent", round(b, 5))


def evaluar_base():
    """modelos.evaluar del commit original, cargado desde git sin tocar el árbol de trabajo."""
    fuente = subprocess.run(["git", "-C", str(RAIZ), "show", f"{COMMIT_BASE}:analisis_deportivo/nfl/modelos.py"],
                            capture_output=True, text=True, check=True).stdout
    spec = importlib.util.spec_from_loader("analisis_deportivo.nfl.modelos_base", loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = "analisis_deportivo.nfl"
    exec(compile(fuente, "modelos_base.py", "exec"), mod.__dict__)
    return mod.evaluar


def _evaluar(args):
    cual, t = args
    if cual == "base_ll":  # el evaluar original no calcula log-loss: se reproduce con los componentes
        e = c.margenes_elo(range(t, t + 1), lambda: x.EloVar(k=20, ventaja_campo=48, regresion=1 / 3, mov=2.2))
        r = c.margenes_ratings(range(t, t + 1), lambda: modelos.RatingsNFL(0.3, 2.0))
        mi = c.metricas(c.de_temporadas([t]), {k: 0.5 * e[k] + 0.5 * r[k][0] for k in e}, 13.5)
        return cual, t, {"logloss": mi["logloss"] * mi["n"], "brier": mi["brier"] * mi["n"]}
    f = evaluar_base() if cual == "base" else modelos.evaluar
    return cual, t, f(c.juegos(), t)


def resumen(ms):
    s = defaultdict(float)
    for m in ms:
        for k, v in m.items():
            s[k] += v
    n = s["n"]
    return {
        "partidos": int(n),
        "brier": s["brier"] / n,
        "logloss": s["logloss"] / n,
        "acierto": 100 * s["aciertos"] / n,
        "error_margen": s["error_margen"] / n,
        "acierto_mercado": 100 * s["aciertos_mercado"] / s["n_fav"],
        "error_linea": s["error_linea"] / s["n_linea"],
        "error_modelo_vs_linea": s["error_margen_m"] / s["n_linea"],
        "ats": 100 * s["ats_aciertos"] / s["ats_n"],
    }


def verificar():
    tareas = [(cual, t) for cual in ("base", "nuevo", "base_ll") for t in list(c.ENTRENAMIENTO) + list(c.VALIDACION)]
    with Pool(4) as pool:
        res = pool.map(_evaluar, tareas)
    por = {(cual, t): m for cual, t, m in res}
    for t in list(c.ENTRENAMIENTO) + list(c.VALIDACION):
        ll = por[("base_ll", t)]
        assert abs(ll["brier"] - por[("base", t)]["brier"]) < 1e-6, "la reproducción de la línea base no coincide"
        por[("base", t)]["logloss"] = ll["logloss"]
    print("\nBrier por temporada (modelos.evaluar)        base     nuevo")
    for t in list(c.ENTRENAMIENTO) + list(c.VALIDACION):
        mb, mn = por[("base", t)], por[("nuevo", t)]
        print(f"  {t}{' (val)' if t in c.VALIDACION else ''}{'':<32}{mb['brier'] / mb['n']:.4f}   {mn['brier'] / mn['n']:.4f}")
    for nombre, ts in (("ENTRENAMIENTO 2012-2019", c.ENTRENAMIENTO), ("VALIDACIÓN 2020-2025", c.VALIDACION)):
        print(f"\n{nombre}")
        rb = resumen(por[("base", t)] for t in ts)
        rn = resumen(por[("nuevo", t)] for t in ts)
        for k in rb:
            print(f"  {k:<24}{rb[k]:>10.4f}{rn[k]:>10.4f}")


if __name__ == "__main__":
    if "--verificar" not in sys.argv:
        buscar()
    verificar()
