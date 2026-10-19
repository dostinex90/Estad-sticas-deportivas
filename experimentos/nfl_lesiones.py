"""¿Mejora la predicción NFL si se tienen en cuenta los lesionados de cada partido?

Datos (nflverse, solo información previa al partido):
  * parte de lesionados oficial de cada semana (injuries_AAAA.csv): jugadores Out, Doubtful o
    Questionable; se publica antes del partido.
  * porcentaje de jugadas (snaps) de cada jugador en cada partido (snap_counts_AAAA.csv, desde 2013):
    sirve para saber cuánto juega normalmente cada lesionado, con sus partidos ANTERIORES.

Rasgo de cada equipo y grupo de posiciones: suma del % de snaps habitual (media de sus últimas
4 apariciones en el último año) de los jugadores de baja. Los QB no cuentan: el modelo ya usa el
QB titular real. Se ajusta el peso de cada grupo con mínimos cuadrados sobre el residuo del modelo
actual (margen real − margen previsto) en 2013-2019 y se valida en 2020-2025.

Uso: python3 experimentos/nfl_lesiones.py
"""

import csv
import io
import math
import re
import sys
import urllib.request
from collections import defaultdict, deque
from datetime import date
from multiprocessing import Pool
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo import base  # noqa: E402
from analisis_deportivo.comun import normal_cdf  # noqa: E402
from analisis_deportivo.nfl import datos, modelos  # noqa: E402
from analisis_deportivo.nfl.equipos import normalizar  # noqa: E402

ENTRENAMIENTO = range(2013, 2020)
VALIDACION = range(2020, 2026)
CACHE = RAIZ / "datos" / "descargas" / "nfl_jugadores"
URL = "https://github.com/nflverse/nflverse-data/releases/download/{0}/{0}_{1}.csv"

GRUPOS = {
    "OL": {"T", "G", "C", "OT", "OG", "OL"},
    "WR": {"WR"}, "TE": {"TE"}, "RB": {"RB", "FB", "HB"},
    "DL": {"DE", "DT", "NT", "DL"}, "LB": {"LB", "OLB", "ILB", "MLB"},
    "DB": {"CB", "S", "FS", "SS", "DB", "SAF"},
}
OFENSIVOS = {"OL", "WR", "TE", "RB"}


def grupo(pos):
    return next((g for g, p in GRUPOS.items() if pos in p), None)


def bajar(tipo, t):
    archivo = CACHE / f"{tipo}_{t}.csv"
    if not archivo.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(urllib.request.urlopen(URL.format(tipo, t), timeout=120).read())
    return list(csv.DictReader(io.StringIO(archivo.read_text(encoding="utf-8-sig"))))


def clave_nombre(nombre):
    n = re.sub(r"[.'’\-]", "", nombre.lower())
    n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", n)
    return " ".join(n.split())


def rasgos(juegos):
    """{(id, equipo): {grupo: snaps perdidos}} con los partidos de juegos (ordenados por fecha)."""
    fecha_de = {j.id: j.fecha for j in juegos}
    por_semana = {}  # (temporada, semana, equipo) -> id del partido
    for j in juegos:
        for eq in (j.local, j.visitante):
            por_semana[(j.temporada, j.semana, eq)] = j.id
    # historial de snaps: (fecha, nombre normalizado, equipo) en orden cronológico
    snaps = []
    for t in range(ENTRENAMIENTO.start - 1, VALIDACION.stop):
        try:
            filas = bajar("snap_counts", t)
        except Exception:
            continue
        for f in filas:
            gid = f["game_id"]
            if gid not in fecha_de:
                continue
            g = grupo(f["position"])
            if not g:
                continue
            pct = float(f["offense_pct"] or 0) if g in OFENSIVOS else float(f["defense_pct"] or 0)
            snaps.append((fecha_de[gid], clave_nombre(f["player"]), g, pct))
    snaps.sort(key=lambda s: s[0])
    bajas = defaultdict(list)  # id partido -> [(equipo, nombre, estado, posición)]
    for t in range(ENTRENAMIENTO.start, VALIDACION.stop):
        for f in bajar("injuries", t):
            estado = f["report_status"]
            if estado not in ("Out", "Doubtful", "Questionable"):
                continue
            eq = normalizar(f["team"])
            gid = por_semana.get((int(f["season"]), int(f["week"]), eq))
            if gid:
                bajas[gid].append((eq, clave_nombre(f["full_name"]), estado, f["position"]))
    # recorrido cronológico: rasgos de cada partido solo con snaps de fechas anteriores
    historial = defaultdict(lambda: deque(maxlen=4))  # nombre -> [(fecha, pct)]
    res = {}
    idx = 0
    for j in sorted(juegos, key=lambda j: j.fecha):
        while idx < len(snaps) and snaps[idx][0] < j.fecha:
            fch, nombre, g, pct = snaps[idx]
            historial[nombre].append((fch, pct))
            idx += 1
        for eq in (j.local, j.visitante):
            res[(j.id, eq)] = defaultdict(float)
        for eq, nombre, estado, pos in bajas.get(j.id, []):
            g = grupo(pos)
            if not g:
                continue
            h = [p for f, p in historial.get(nombre, ()) if (j.fecha - f).days <= 365]
            if not h:
                continue
            habitual = sum(h) / len(h)
            clave = g if estado != "Questionable" else "Q"
            res[(j.id, eq)][clave] += habitual
    return res


def _predicciones(t):
    """[(juego, margen previsto)] de la temporada t con el procedimiento de modelos.evaluar."""
    juegos = datos.cargar_desde_base(base.conectar())
    jug = sorted((j for j in juegos if j.jugado and j.temporada <= t), key=lambda j: j.fecha)
    objetivo = [j for j in jug if j.temporada == t]
    elo, ctx = modelos.EloNFL(), modelos.ContextoQB()
    idx = idx_qb = 0
    res = []
    for clave in sorted({(j.tipo != "REG", j.semana) for j in objetivo}):
        de_semana = [j for j in objetivo if (j.tipo != "REG", j.semana) == clave]
        inicio = min(j.fecha for j in de_semana)
        while idx < len(jug) and jug[idx].fecha < inicio:
            elo.actualizar(jug[idx])
            idx += 1
        ratings = modelos.RatingsNFL().ajustar(jug[:idx], t)
        elo._nueva_temporada(t)
        for j in de_semana:
            while idx_qb < len(jug) and jug[idx_qb].fecha < j.fecha:
                ctx.agregar(jug[idx_qb])
                idx_qb += 1
            pr = modelos.predecir_juego(elo, ratings, j, ctx)
            res.append((j.id, pr["margen"], j.margen, j.es_playoff))
    return res


def resolver(A, b):
    n = len(b)
    M = [fila[:] + [b[i]] for i, fila in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c:
                f = M[r][c] / M[c][c]
                M[r] = [a - f * x for a, x in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def metricas(filas, pesos, claves):
    n = brier = ll = 0.0
    for gid, m, real, po, x in filas:
        if real == 0:
            continue
        a = sum(pesos[k] * x[k] for k in claves)
        margen = m + (a * modelos.FACTOR_PLAYOFF if po else a)
        p = min(max(normal_cdf(margen, 0, modelos.DESVIACION_PROB), 1e-12), 1 - 1e-12)
        g = real > 0
        n += 1
        brier += (p - g) ** 2
        ll -= math.log(p if g else 1 - p)
    return brier / n, ll / n, int(n)


def main():
    temporadas = list(ENTRENAMIENTO) + list(VALIDACION)
    with Pool(4) as pool:
        preds = dict(zip(temporadas, pool.map(_predicciones, temporadas)))
    juegos = [j for j in datos.cargar_desde_base(base.conectar()) if j.jugado]
    ras = rasgos(juegos)
    local = {j.id: (j.local, j.visitante) for j in juegos}
    claves = list(GRUPOS) + ["Q"]
    filas = {}
    for t, ps in preds.items():
        filas[t] = []
        for gid, m, real, po in ps:
            l, v = local[gid]
            rl, rv = ras.get((gid, l), {}), ras.get((gid, v), {})
            # positivo = el local tiene más bajas (se espera un peso negativo)
            x = {k: rl.get(k, 0.0) - rv.get(k, 0.0) for k in claves}
            filas[t].append((gid, m, real, po, x))
    ent = [f for t in ENTRENAMIENTO for f in filas[t]]
    val = [f for t in VALIDACION for f in filas[t]]
    cobertura = sum(1 for f in ent + val if any(f[4].values())) / len(ent + val)
    print(f"Partidos con alguna baja relevante: {100 * cobertura:.0f} %")
    # mínimos cuadrados con regularización (ridge) del residuo sobre los rasgos
    for lam in (10.0, 50.0, 200.0):
        A = [[sum(f[4][a] * f[4][b] for f in ent) + (lam if a == b else 0) for b in claves] for a in claves]
        b = [sum(f[4][a] * (f[2] - f[1]) for f in ent) for a in claves]
        w = dict(zip(claves, resolver(A, b)))
        print(f"\nRidge λ={lam}: pesos (puntos por jugador titular de baja)",
              {k: round(v, 2) for k, v in w.items()})
        cero = dict.fromkeys(claves, 0.0)
        for nombre, conj in (("entrenamiento 2013-2019", ent), ("validación 2020-2025", val)):
            b0, l0, n = metricas(conj, cero, claves)
            b1, l1, _ = metricas(conj, w, claves)
            print(f"  {nombre:<24} n={n}  Brier {b0:.4f} → {b1:.4f}   log-loss {l0:.4f} → {l1:.4f}")


if __name__ == "__main__":
    main()
