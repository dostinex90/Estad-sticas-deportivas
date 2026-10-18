"""Modelos predictivos de fútbol.

* ModeloPoisson: fuerzas de ataque y defensa ajustadas por rival (modelo de Maher),
  con ventaja de local, ponderación temporal, contracción hacia la media y la corrección
  de Dixon-Coles para marcadores bajos (rho estimado por máxima verosimilitud).
* EloFutbol: rating Elo con multiplicador por diferencia de goles (estilo World Football Elo).
* evaluar: validación "walk-forward" que solo usa información anterior a cada partido.
"""

import math
from collections import defaultdict

from ..comun import poisson

MAX_GOLES = 10


def _tau(i, j, lam, mu, rho):
    if i == 0 and j == 0:
        return 1 - lam * mu * rho
    if i == 0 and j == 1:
        return 1 + lam * rho
    if i == 1 and j == 0:
        return 1 + mu * rho
    if i == 1 and j == 1:
        return 1 - rho
    return 1.0


class ModeloPoisson:
    def __init__(self, vida_media_dias=240, previa=4.0, iteraciones=40):
        """vida_media_dias: un partido de hace X días pesa la mitad que uno de hoy (None = sin decaimiento).
        previa: partidos ficticios "de equipo medio" que estabilizan equipos con pocos datos."""
        self.vida_media_dias = vida_media_dias
        self.previa = previa
        self.iteraciones = iteraciones
        self.ataque = {}
        self.defensa = {}
        self.media_local = 1.4
        self.media_visitante = 1.1
        self.rho = 0.0
        self.partidos_usados = 0

    def _peso(self, partido, referencia):
        if not self.vida_media_dias:
            return 1.0
        return 0.5 ** ((referencia - partido.fecha).days / self.vida_media_dias)

    def ajustar(self, partidos, referencia=None):
        jug = [p for p in partidos if p.jugado]
        if not jug:
            raise ValueError("No hay partidos jugados para ajustar el modelo.")
        referencia = referencia or max(p.fecha for p in jug)
        datos = [(p, self._peso(p, referencia)) for p in jug]
        peso_total = sum(w for _, w in datos)
        self.media_local = sum(p.goles_local * w for p, w in datos) / peso_total
        self.media_visitante = sum(p.goles_visitante * w for p, w in datos) / peso_total
        self.media_local = max(self.media_local, 0.05)
        self.media_visitante = max(self.media_visitante, 0.05)

        equipos = {p.local for p in jug} | {p.visitante for p in jug}
        att = {e: 1.0 for e in equipos}
        dfn = {e: 1.0 for e in equipos}
        k = self.previa
        for _ in range(self.iteraciones):
            num, den = defaultdict(float), defaultdict(float)
            for p, w in datos:
                num[p.local] += w * p.goles_local
                den[p.local] += w * self.media_local * dfn[p.visitante]
                num[p.visitante] += w * p.goles_visitante
                den[p.visitante] += w * self.media_visitante * dfn[p.local]
            att = {e: (num[e] + k) / (den[e] + k) for e in equipos}
            m = sum(att.values()) / len(att)
            att = {e: v / m for e, v in att.items()}

            num, den = defaultdict(float), defaultdict(float)
            for p, w in datos:
                num[p.local] += w * p.goles_visitante
                den[p.local] += w * self.media_visitante * att[p.visitante]
                num[p.visitante] += w * p.goles_local
                den[p.visitante] += w * self.media_local * att[p.local]
            dfn = {e: (num[e] + k) / (den[e] + k) for e in equipos}
            m = sum(dfn.values()) / len(dfn)
            dfn = {e: v / m for e, v in dfn.items()}

        self.ataque, self.defensa = att, dfn
        self.partidos_usados = len(jug)
        self.rho = self._estimar_rho(datos)
        return self

    def _estimar_rho(self, datos):
        mejor, mejor_ll = 0.0, -math.inf
        lambdas = [(self.goles_esperados(p.local, p.visitante), p, w) for p, w in datos]
        for paso in range(-25, 16):
            rho = paso / 100
            ll = 0.0
            for (lam, mu), p, w in lambdas:
                t = _tau(p.goles_local, p.goles_visitante, lam, mu, rho)
                if t <= 0:
                    ll = -math.inf
                    break
                ll += w * math.log(t)
            if ll > mejor_ll:
                mejor, mejor_ll = rho, ll
        return mejor

    def goles_esperados(self, local, visitante, neutral=False):
        att_l, def_l = self.ataque.get(local, 1.0), self.defensa.get(local, 1.0)
        att_v, def_v = self.ataque.get(visitante, 1.0), self.defensa.get(visitante, 1.0)
        if neutral:
            base = (self.media_local + self.media_visitante) / 2
            return base * att_l * def_v, base * att_v * def_l
        return self.media_local * att_l * def_v, self.media_visitante * att_v * def_l

    def matriz(self, local, visitante, neutral=False):
        lam, mu = self.goles_esperados(local, visitante, neutral)
        m = [[poisson(i, lam) * poisson(j, mu) * _tau(i, j, lam, mu, self.rho) for j in range(MAX_GOLES + 1)]
             for i in range(MAX_GOLES + 1)]
        total = sum(map(sum, m))
        return [[v / total for v in fila] for fila in m], lam, mu

    def predecir(self, local, visitante, neutral=False):
        m, lam, mu = self.matriz(local, visitante, neutral)
        rango = range(MAX_GOLES + 1)
        celdas = [(i, j, m[i][j]) for i in rango for j in rango]
        p1 = sum(v for i, j, v in celdas if i > j)
        px = sum(v for i, j, v in celdas if i == j)
        p2 = sum(v for i, j, v in celdas if i < j)
        mas = {linea: sum(v for i, j, v in celdas if i + j > linea) for linea in (0.5, 1.5, 2.5, 3.5, 4.5)}
        return {
            "goles_local": lam,
            "goles_visitante": mu,
            "p1": p1, "px": px, "p2": p2,
            "p1x": p1 + px, "px2": px + p2, "p12": p1 + p2,
            "mas": mas,
            "ambos_marcan": sum(v for i, j, v in celdas if i > 0 and j > 0),
            "porteria_cero_local": sum(m[i][0] for i in rango),
            "porteria_cero_visitante": sum(m[0][j] for j in rango),
            "handicap": {
                h: sum(v for i, j, v in celdas if i - j > h) for h in (-1.5, -0.5, 0.5, 1.5)
            },
            "marcadores": sorted(celdas, key=lambda c: -c[2])[:6],
            "goles_local_dist": [sum(m[i]) for i in range(6)],
            "goles_visitante_dist": [sum(m[i][j] for i in rango) for j in range(6)],
        }

    def ranking(self):
        """Equipos ordenados por diferencia esperada de goles contra un rival medio en campo neutral."""
        base = (self.media_local + self.media_visitante) / 2
        filas = [(e, self.ataque[e], self.defensa[e], base * (self.ataque[e] - self.defensa[e])) for e in self.ataque]
        return sorted(filas, key=lambda f: -f[3])


class EloFutbol:
    def __init__(self, k=20, ventaja_local=60, inicial=1500):
        self.k = k
        self.ventaja_local = ventaja_local
        self.inicial = inicial
        self.rating = {}
        self.historial = defaultdict(list)  # equipo -> [(fecha, rating)]

    def esperado(self, local, visitante, neutral=False):
        dr = self.rating.get(local, self.inicial) - self.rating.get(visitante, self.inicial)
        if not neutral:
            dr += self.ventaja_local
        return 1 / (1 + 10 ** (-dr / 400))

    def actualizar(self, p):
        rl = self.rating.get(p.local, self.inicial)
        rv = self.rating.get(p.visitante, self.inicial)
        we = self.esperado(p.local, p.visitante)
        w = 1.0 if p.goles_local > p.goles_visitante else 0.5 if p.goles_local == p.goles_visitante else 0.0
        dif = abs(p.goles_local - p.goles_visitante)
        g = 1 if dif <= 1 else 1.5 if dif == 2 else (11 + dif) / 8
        delta = self.k * g * (w - we)
        self.rating[p.local] = rl + delta
        self.rating[p.visitante] = rv - delta
        self.historial[p.local].append((p.fecha, self.rating[p.local]))
        self.historial[p.visitante].append((p.fecha, self.rating[p.visitante]))

    def procesar(self, partidos):
        for p in partidos:
            if p.jugado:
                self.actualizar(p)
        return self

    def ranking(self):
        return sorted(self.rating.items(), key=lambda kv: -kv[1])


def probabilidades_mercado(cuotas):
    """Convierte cuotas decimales 1X2 en probabilidades eliminando el margen de la casa."""
    inversas = [1 / c for c in cuotas]
    total = sum(inversas)
    return [v / total for v in inversas], total - 1


def _rps(probs, resultado):
    """Ranked Probability Score para 1X2 (menor es mejor)."""
    real = {"1": (1, 0, 0), "X": (0, 1, 0), "2": (0, 0, 1)}[resultado]
    acum_p = acum_r = suma = 0.0
    for p, r in zip(probs[:2], real[:2]):
        acum_p += p
        acum_r += r
        suma += (acum_p - acum_r) ** 2
    return suma / 2


def _metricas():
    return {"n": 0, "aciertos": 0, "brier": 0.0, "logloss": 0.0, "rps": 0.0}


def _acumular(m, probs, resultado):
    idx = "1X2".index(resultado)
    m["n"] += 1
    m["aciertos"] += max(range(3), key=lambda i: probs[i]) == idx
    m["brier"] += sum((p - (i == idx)) ** 2 for i, p in enumerate(probs))
    m["logloss"] += -math.log(max(probs[idx], 1e-12))
    m["rps"] += _rps(probs, resultado)


def evaluar(partidos, minimo=60, **opciones_modelo):
    """Valida el modelo partido a partido usando solo datos previos a cada fecha.

    Devuelve métricas del modelo Poisson, de una referencia ingenua (frecuencias históricas
    de 1/X/2) y del mercado de apuestas si el archivo trae cuotas.
    """
    jug = [p for p in partidos if p.jugado]
    if len(jug) <= minimo:
        raise ValueError(f"Se necesitan más de {minimo} partidos jugados para evaluar (hay {len(jug)}).")
    fechas = sorted({p.fecha for p in jug[minimo:]})
    res = {"modelo": _metricas(), "referencia": _metricas(), "mercado": _metricas(), "modelo_vs_mercado": _metricas()}
    over = {"n": 0, "aciertos": 0}
    calibracion = defaultdict(lambda: [0, 0.0, 0])  # tramo -> [n, prob sumada, aciertos]
    for fecha in fechas:
        previos = [p for p in jug if p.fecha < fecha]
        if len(previos) < minimo:
            continue
        modelo = ModeloPoisson(**opciones_modelo).ajustar(previos, referencia=fecha)
        n = len(previos)
        freq = [sum(p.resultado_1x2 == r for p in previos) / n for r in "1X2"]
        for p in (q for q in jug if q.fecha == fecha):
            pr = modelo.predecir(p.local, p.visitante)
            probs = [pr["p1"], pr["px"], pr["p2"]]
            _acumular(res["modelo"], probs, p.resultado_1x2)
            _acumular(res["referencia"], freq, p.resultado_1x2)
            if p.cuotas:
                mercado, _ = probabilidades_mercado(p.cuotas)
                _acumular(res["mercado"], mercado, p.resultado_1x2)
                _acumular(res["modelo_vs_mercado"], probs, p.resultado_1x2)
            over["n"] += 1
            over["aciertos"] += (pr["mas"][2.5] > 0.5) == (p.total_goles > 2.5)
            for i, r in enumerate("1X2"):
                tramo = min(int(probs[i] * 10), 9)
                c = calibracion[tramo]
                c[0] += 1
                c[1] += probs[i]
                c[2] += p.resultado_1x2 == r
    for m in res.values():
        if m["n"]:
            for clave in ("brier", "logloss", "rps"):
                m[clave] /= m["n"]
    res["over_2_5"] = over
    res["calibracion"] = dict(sorted(calibracion.items()))
    return res
