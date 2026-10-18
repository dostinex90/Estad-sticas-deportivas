"""Exploración de parámetros NFL (ajuste con 2012-2019; validación 2020-2025 solo para informar).

Uso: python3 experimentos/nfl_explorar.py
"""

import itertools
import math
import sys
from collections import Counter, defaultdict, deque
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nfl_componentes as c  # noqa: E402
from analisis_deportivo.nfl import modelos  # noqa: E402

TODAS = range(2012, 2026)


# ---------- Elo parametrizado ----------
class EloVar(modelos.EloNFL):
    def __init__(self, k=20, ventaja_campo=48, regresion=1 / 3, mov=2.2, k_playoff=1.0, qb_elo=0.0, ras=None):
        super().__init__(k=k, ventaja_campo=ventaja_campo, regresion=regresion)
        self.mov = mov
        self.k_playoff = k_playoff
        self.qb_elo = qb_elo  # puntos Elo por cambio de QB tenidos en cuenta al actualizar
        self.ras = ras

    def actualizar(self, j):
        self._nueva_temporada(j.temporada)
        dif = self.diferencia(j.local, j.visitante, j.neutral)
        if self.qb_elo and self.ras:
            dif += self.qb_elo * self.ras[j.id]["qb"]
        esperado = 1 / (1 + 10 ** (-dif / 400))
        real = 1.0 if j.margen > 0 else 0.0 if j.margen < 0 else 0.5
        dif_ganador = dif if j.margen > 0 else -dif
        mult = math.log(abs(j.margen) + 1) * self.mov / (dif_ganador * 0.001 + self.mov) if j.margen else 1.0
        k = self.k * (self.k_playoff if j.es_playoff else 1.0)
        delta = k * mult * (real - esperado)
        self.rating[j.local] = self._r(j.local) + delta
        self.rating[j.visitante] = self._r(j.visitante) - delta


def elo_sin_campo(params, ras=None):
    """{id: (diferencia Elo sin ventaja de campo)/25}."""
    return c.margenes_elo(TODAS, lambda: EloVar(ras=ras, **params),
                          margen=lambda e, j: (e._r(j.local) - e._r(j.visitante)) / 25)


# ---------- Rasgos previos al partido ----------
def epa_pase():
    """{(game_id, equipo): (EPA de pase, dropbacks)} de nfl_estadisticas_equipo."""
    from analisis_deportivo import base
    from analisis_deportivo.nfl.equipos import normalizar
    con = base.conectar()
    res = {}
    for g, t, e, a, s in con.execute("SELECT game_id, team, passing_epa, attempts, sacks_suffered FROM nfl_estadisticas_equipo"):
        if t:
            res[(g, normalizar(t))] = (e or 0.0, (a or 0) + (s or 0))
    return res


def rasgos(ventana=8, m0=300, previo=-0.05, jugadas=35):
    """Por partido: descanso, y cambio de QB titular respecto al habitual (el más frecuente en
    los últimos `ventana` partidos del equipo, solo con partidos anteriores)."""
    jug = c.jugados()
    todos = sorted(c.juegos(), key=lambda j: j.fecha)
    ultimos = defaultdict(lambda: deque(maxlen=ventana))
    salidas = Counter()  # titularidades previas de cada QB
    epa = epa_pase()
    suma_epa, suma_db = defaultdict(float), defaultdict(float)

    def valor(qb):  # EPA por dropback previo del QB, encogido hacia `previo`
        return (suma_epa[qb] + m0 * previo) / (suma_db[qb] + m0)
    res = {}
    i = 0
    por_fecha = defaultdict(list)
    for j in jug:
        por_fecha[j.fecha].append(j)
    for fecha in sorted(por_fecha):
        grupo = por_fecha[fecha]
        for j in grupo:
            f = {}
            for lado, eq, qb in (("l", j.local, j.qb_local), ("v", j.visitante, j.qb_visitante)):
                hist = ultimos[eq]
                habitual = Counter(hist).most_common(1)[0][0] if hist else None
                f["cambio_" + lado] = 1.0 if habitual and qb and qb != habitual else 0.0
                f["nuevo_" + lado] = 1.0 if f["cambio_" + lado] and salidas[qb] < 8 else 0.0
                f["valor_" + lado] = jugadas * (valor(qb) - valor(habitual)) if f["cambio_" + lado] else 0.0
            dl, dv = j.descanso_local, j.descanso_visitante
            f["descanso"] = max(-7, min(7, (dl or 7) - (dv or 7))) if dl and dv else 0.0
            f["bye"] = (1.0 if (dl or 0) >= 13 else 0.0) - (1.0 if (dv or 0) >= 13 else 0.0)
            f["qb"] = f["cambio_v"] - f["cambio_l"]
            f["qb_nuevo"] = f["nuevo_v"] - f["nuevo_l"]
            f["qb_valor"] = f["valor_l"] - f["valor_v"]
            f["playoff"] = 1.0 if j.es_playoff else 0.0
            f["neutral"] = 1.0 if j.neutral else 0.0
            res[j.id] = f
        for j in grupo:
            for eq, qb in ((j.local, j.qb_local), (j.visitante, j.qb_visitante)):
                if qb:
                    ultimos[eq].append(qb)
                    salidas[qb] += 1
                    e, d = epa.get((j.id, eq), (0.0, 0))
                    suma_epa[qb] += e
                    suma_db[qb] += d
    return res


# ---------- Combinación ----------
def combinar(elo, rat, ras, p):
    """Margen combinado. p: peso_elo, campo (pts Elo; None = usar la estimada por los ratings),
    b_descanso, b_bye, b_qb, b_qb_nuevo, f_playoff."""
    res = {}
    for k, e in elo.items():
        mr, _, h = rat[k]
        f = ras[k]
        campo = 0 if f["neutral"] else (h if p["campo"] is None else p["campo"] / 25)
        m = p["peso_elo"] * (e + campo) + (1 - p["peso_elo"]) * mr
        m += p.get("b_descanso", 0) * f["descanso"] + p.get("b_bye", 0) * f["bye"]
        m += p.get("b_qb", 0) * f["qb"] + p.get("b_qb_nuevo", 0) * f["qb_nuevo"] + p.get("b_qb_valor", 0) * f["qb_valor"]
        if f["playoff"]:
            m *= p.get("f_playoff", 1.0)
        res[k] = m
    return res


ENT = None
VAL = None


def brier(elo, rat, ras, p, partidos):
    return c.metricas(partidos, combinar(elo, rat, ras, p), p["sigma"])["brier"]


def optimizar(elo, rat, ras, p, claves, rejillas, partidos, rondas=2):
    """Búsqueda por coordenadas sobre rejillas pequeñas (solo partidos de entrenamiento)."""
    p = dict(p)
    mejor = brier(elo, rat, ras, p, partidos)
    for _ in range(rondas):
        for k in claves:
            for v in rejillas[k]:
                q = dict(p, **{k: v})
                b = brier(elo, rat, ras, q, partidos)
                if b < mejor - 1e-9:
                    mejor, p = b, q
    return p, mejor


REJ = {
    "peso_elo": [i / 10 for i in range(0, 11)],
    "sigma": [10.5 + 0.25 * i for i in range(15)],
    "b_descanso": [0, 0.05, 0.1, 0.15, 0.2, 0.3],
    "b_bye": [0, 0.5, 1.0, 1.5],
    "b_qb": [0, 1, 1.5, 2, 2.5, 3, 4, 5],
    "b_qb_nuevo": [0, 1, 2, 3, 4],
    "b_qb_valor": [0, 0.25, 0.5, 0.75, 1.0, 1.25],
    "f_playoff": [0.9, 1.0, 1.1, 1.2, 1.3],
    "campo": [None, 48, 60, 72, 84],
}


def _ratings(args):
    peso, reg = args
    return args, c.margenes_ratings(TODAS, lambda: modelos.RatingsNFL(peso, reg))


def informe(nombre, elo, rat, ras, p):
    mt = c.metricas(ENT, combinar(elo, rat, ras, p), p["sigma"])
    mv = c.metricas(VAL, combinar(elo, rat, ras, p), p["sigma"])
    print(f"{nombre:<40} ent {mt['brier']:.5f}  val {mv['brier']:.5f} ll {mv['logloss']:.4f} "
          f"acierto {mv['acierto']:.2f} emm {mv['error_margen']:.3f}")
    return mt, mv


def main():
    global ENT, VAL
    c.juegos()
    ENT, VAL = c.de_temporadas(c.ENTRENAMIENTO), c.de_temporadas(c.VALIDACION)
    ras = rasgos()
    base_p = {"peso_elo": 0.5, "sigma": 13.5, "campo": 48}
    elo0 = elo_sin_campo({})
    with Pool(4) as pool:
        rats = dict(pool.map(_ratings, [(0.3, 2.0)] + [(a, b) for a in (0.15, 0.3, 0.45, 0.6) for b in (1.0, 2.0, 4.0, 8.0) if (a, b) != (0.3, 2.0)]))
    informe("linea base", elo0, rats[(0.3, 2.0)], ras, base_p)

    # 1) ratings con mezcla/sigma optimizadas
    res = []
    for k, rat in rats.items():
        p, b = optimizar(elo0, rat, ras, base_p, ["peso_elo", "sigma"], REJ, ENT)
        res.append((b, k, p))
    res.sort(key=lambda x: x[0])
    for b, k, p in res[:6]:
        print("ratings", k, round(b, 5), p)
    rat_k = res[0][1]
    rat = rats[rat_k]

    # 2) Elo
    res = []
    for kk, hfa, reg, mov, kp in itertools.product((16, 20, 24), (48, 60, 72, 84), (1 / 3, 0.45, 0.6), (2.2,), (1.0,)):
        params = dict(k=kk, ventaja_campo=hfa, regresion=reg, mov=mov, k_playoff=kp)
        e = elo_sin_campo(params)
        p, b = optimizar(e, rat, ras, dict(base_p, campo=hfa), ["peso_elo", "sigma"], REJ, ENT)
        res.append((b, params, p))
    res.sort(key=lambda x: x[0])
    for b, params, p in res[:6]:
        print("elo", params, round(b, 5), p)
    elo_p = res[0][1]
    for mov, kp, qe in itertools.product((1.5, 2.2, 3.0), (1.0, 1.5), (0, 25, 50, 75)):
        params = dict(elo_p, mov=mov, k_playoff=kp, qb_elo=qe)
        e = elo_sin_campo(params, ras)
        p, b = optimizar(e, rat, ras, dict(base_p, campo=params["ventaja_campo"]), ["peso_elo", "sigma"], REJ, ENT)
        print("elo mov/kp/qb", mov, kp, qe, round(b, 5))
        if b < res[0][0] - 1e-9:
            res.insert(0, (b, params, p))
    elo_p, p = res[0][1], res[0][2]
    elo = elo_sin_campo(elo_p, ras)
    print("elo elegido", elo_p)
    informe("elo+ratings+mezcla", elo, rat, ras, p)

    # 3) extras uno a uno (cada uno solo si mejora en entrenamiento)
    for extra in ("campo", "b_descanso", "b_bye", "b_qb", "b_qb_nuevo", "f_playoff"):
        q, b = optimizar(elo, rat, ras, p, [extra, "peso_elo", "sigma"], REJ, ENT, rondas=1)
        print("extra", extra, q.get(extra), round(b, 5))
        informe(f"  con {extra}", elo, rat, ras, q)
    q, b = optimizar(elo, rat, ras, p, ["campo", "b_descanso", "b_bye", "b_qb", "b_qb_nuevo", "f_playoff", "peso_elo", "sigma"], REJ, ENT)
    print("todo", q, round(b, 5))
    informe("todo junto", elo, rat, ras, q)

    # 4) valor del QB (EPA de pase previo) frente al binario
    for m0, previo in itertools.product((150, 400), (-0.15, -0.05)):
        r2 = rasgos(m0=m0, previo=previo)
        q2, b2 = optimizar(elo, rat, r2, p, ["b_qb", "b_qb_valor", "peso_elo", "sigma"], REJ, ENT)
        print("qb valor", m0, previo, q2.get("b_qb"), q2.get("b_qb_valor"), round(b2, 5))
        informe("  con valor QB", elo, rat, r2, q2)


if __name__ == "__main__":
    main()
