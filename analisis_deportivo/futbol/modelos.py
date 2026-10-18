"""Modelos predictivos de fútbol.

* ModeloPoisson: fuerzas de ataque y defensa ajustadas por rival (modelo de Maher),
  con ventaja de local, ponderación temporal, contracción hacia la media y la corrección
  de Dixon-Coles para marcadores bajos (rho estimado por máxima verosimilitud). Las fuerzas se
  estiman con una mezcla de goles y tiros a puerta ("xG aproximado") y los goles esperados se
  combinan con los que implica el Elo previo de ClubElo; sin tiros o sin Elo usa solo los goles.
  Pesos elegidos en 2018-19 a 2022-23 (ver experimentos/futbol_tiros_elo.py).
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


def _resolver3(a, b):
    """Resuelve el sistema lineal 3x3 a·x = b (Cramer); None si es singular."""
    def det(m):
        return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    d = det(a)
    if abs(d) < 1e-12:
        return None
    return [det([[b[i] if j == c else a[i][j] for j in range(3)] for i in range(3)]) / d for c in range(3)]


class ModeloPoisson:
    def __init__(self, vida_media_dias=240, previa=4.0, iteraciones=40, peso_tiros=0.7, peso_elo=0.7):
        """vida_media_dias: un partido de hace X días pesa la mitad que uno de hoy (None = sin decaimiento).
        previa: partidos ficticios "de equipo medio" que estabilizan equipos con pocos datos.
        peso_tiros: 0-1, cuánto pesan los tiros a puerta (convertidos a goles con la tasa de la liga)
            frente a los goles al estimar ataque y defensa ("xG aproximado"). Sin tiros se usan goles.
        peso_elo: 0-1, mezcla geométrica de los goles esperados con los que implica el Elo previo
            (ClubElo). Sin Elo se usa solo el Poisson."""
        self.vida_media_dias = vida_media_dias
        self.previa = previa
        self.iteraciones = iteraciones
        self.peso_tiros = peso_tiros
        self.peso_elo = peso_elo
        self.ataque = {}
        self.defensa = {}
        self.media_local = 1.4
        self.media_visitante = 1.1
        self.rho = 0.0
        self.partidos_usados = 0
        self.elo_coef = None  # (intercepto local, intercepto visitante, pendiente por 100 puntos de Elo)
        self.elo_ultimo = {}  # equipo -> último Elo previo conocido

    def _peso(self, partido, referencia):
        if not self.vida_media_dias:
            return 1.0
        return 0.5 ** ((referencia - partido.fecha).days / self.vida_media_dias)

    def _objetivos(self, datos):
        """Goles "efectivos" de cada partido: mezcla de goles y tiros a puerta convertidos a goles."""
        a = self.peso_tiros
        con_tiros = [(p, w) for p, w in datos if "tiros_puerta" in p.estadisticas]
        tiros = sum(w * sum(p.estadisticas["tiros_puerta"]) for p, w in con_tiros)
        if not a or not tiros:
            return {id(p): (p.goles_local, p.goles_visitante) for p, _ in datos}
        conversion = sum(w * p.total_goles for p, w in con_tiros) / tiros
        obj = {}
        for p, _ in datos:
            tp = p.estadisticas.get("tiros_puerta")
            if tp is None:
                obj[id(p)] = (p.goles_local, p.goles_visitante)
            else:
                obj[id(p)] = ((1 - a) * p.goles_local + a * conversion * tp[0],
                              (1 - a) * p.goles_visitante + a * conversion * tp[1])
        return obj

    def _ajustar_elo(self, datos):
        """Regresión de Poisson ponderada: log(goles) = c + b·(diferencia de Elo / 100), por Newton."""
        filas = [(p, w, (p.elo_local - p.elo_visitante) / 100) for p, w in datos
                 if p.elo_local is not None and p.elo_visitante is not None and not p.neutral]
        if len(filas) < 30:
            return None
        cl, cv, b = math.log(self.media_local), math.log(self.media_visitante), 0.0
        for _ in range(8):
            g = [0.0, 0.0, 0.0]
            h = [[0.0] * 3 for _ in range(3)]
            for p, w, x in filas:
                ml, mv = math.exp(cl + b * x), math.exp(cv - b * x)
                rl, rv = w * (p.goles_local - ml), w * (p.goles_visitante - mv)
                g[0] += rl
                g[1] += rv
                g[2] += x * (rl - rv)
                h[0][0] += w * ml
                h[1][1] += w * mv
                h[0][2] += w * ml * x
                h[1][2] -= w * mv * x
                h[2][2] += w * x * x * (ml + mv)
            h[2][0], h[2][1] = h[0][2], h[1][2]
            paso = _resolver3(h, g)
            if paso is None:
                return None
            cl, cv, b = cl + paso[0], cv + paso[1], b + paso[2]
            if max(map(abs, paso)) < 1e-7:
                break
        return cl, cv, b

    def ajustar(self, partidos, referencia=None):
        jug = [p for p in partidos if p.jugado]
        if not jug:
            raise ValueError("No hay partidos jugados para ajustar el modelo.")
        referencia = referencia or max(p.fecha for p in jug)
        # Los partidos casi sin peso (muy antiguos) no aportan y ralentizan el ajuste
        datos = [(p, w) for p in jug if (w := self._peso(p, referencia)) >= 0.02]
        if not datos:
            raise ValueError("No hay partidos recientes para ajustar el modelo.")
        con_campo = [(p, w) for p, w in datos if not p.neutral] or datos
        peso_total = sum(w for _, w in con_campo)
        self.media_local = sum(p.goles_local * w for p, w in con_campo) / peso_total
        self.media_visitante = sum(p.goles_visitante * w for p, w in con_campo) / peso_total
        self.media_local = max(self.media_local, 0.05)
        self.media_visitante = max(self.media_visitante, 0.05)

        equipos = {p.local for p, _ in datos} | {p.visitante for p, _ in datos}
        neutra = (self.media_local + self.media_visitante) / 2
        base = {id(p): (neutra, neutra) if p.neutral else (self.media_local, self.media_visitante) for p, _ in datos}
        obj = self._objetivos(datos)
        att = {e: 1.0 for e in equipos}
        dfn = {e: 1.0 for e in equipos}
        k = self.previa
        for _ in range(self.iteraciones):
            num, den = defaultdict(float), defaultdict(float)
            for p, w in datos:
                bl, bv = base[id(p)]
                gl, gv = obj[id(p)]
                num[p.local] += w * gl
                den[p.local] += w * bl * dfn[p.visitante]
                num[p.visitante] += w * gv
                den[p.visitante] += w * bv * dfn[p.local]
            att = {e: (num[e] + k) / (den[e] + k) for e in equipos}
            m = sum(att.values()) / len(att)
            att = {e: v / m for e, v in att.items()}

            num, den = defaultdict(float), defaultdict(float)
            for p, w in datos:
                bl, bv = base[id(p)]
                gl, gv = obj[id(p)]
                num[p.local] += w * gv
                den[p.local] += w * bv * att[p.visitante]
                num[p.visitante] += w * gl
                den[p.visitante] += w * bl * att[p.local]
            dfn = {e: (num[e] + k) / (den[e] + k) for e in equipos}
            m = sum(dfn.values()) / len(dfn)
            dfn = {e: v / m for e, v in dfn.items()}

        self.ataque, self.defensa = att, dfn
        self.partidos_usados = len(datos)
        self.elo_coef, self.elo_ultimo = None, {}
        if self.peso_elo:
            self.elo_coef = self._ajustar_elo(datos)
            for p in sorted(jug, key=lambda q: q.fecha):
                if p.elo_local is not None:
                    self.elo_ultimo[p.local] = p.elo_local
                if p.elo_visitante is not None:
                    self.elo_ultimo[p.visitante] = p.elo_visitante
        self.rho = self._estimar_rho(datos)
        return self

    def _estimar_rho(self, datos):
        mejor, mejor_ll = 0.0, -math.inf
        lambdas = [(self.goles_esperados(p.local, p.visitante, p.neutral, p.elo_local, p.elo_visitante), p, w)
                   for p, w in datos]
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

    def goles_esperados(self, local, visitante, neutral=False, elo_local=None, elo_visitante=None):
        """Goles esperados (local, visitante). El Elo previo, si no se da, es el último conocido del equipo."""
        att_l, def_l = self.ataque.get(local, 1.0), self.defensa.get(local, 1.0)
        att_v, def_v = self.ataque.get(visitante, 1.0), self.defensa.get(visitante, 1.0)
        if neutral:
            base = (self.media_local + self.media_visitante) / 2
            lam, mu = base * att_l * def_v, base * att_v * def_l
        else:
            lam, mu = self.media_local * att_l * def_v, self.media_visitante * att_v * def_l
        if self.elo_coef and self.peso_elo:
            el = elo_local if elo_local is not None else self.elo_ultimo.get(local)
            ev = elo_visitante if elo_visitante is not None else self.elo_ultimo.get(visitante)
            if el is not None and ev is not None:
                cl, cv, b = self.elo_coef
                if neutral:
                    cl = cv = (cl + cv) / 2
                x = (el - ev) / 100
                w = self.peso_elo
                lam = lam ** (1 - w) * math.exp(cl + b * x) ** w
                mu = mu ** (1 - w) * math.exp(cv - b * x) ** w
        return lam, mu

    def matriz(self, local, visitante, neutral=False, elo_local=None, elo_visitante=None):
        lam, mu = self.goles_esperados(local, visitante, neutral, elo_local, elo_visitante)
        m = [[poisson(i, lam) * poisson(j, mu) * _tau(i, j, lam, mu, self.rho) for j in range(MAX_GOLES + 1)]
             for i in range(MAX_GOLES + 1)]
        total = sum(map(sum, m))
        return [[v / total for v in fila] for fila in m], lam, mu

    def predecir(self, local, visitante, neutral=False, elo_local=None, elo_visitante=None):
        m, lam, mu = self.matriz(local, visitante, neutral, elo_local, elo_visitante)
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
        we = self.esperado(p.local, p.visitante, p.neutral)
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


def evaluar(partidos, minimo=60, previos=(), **opciones_modelo):
    """Valida el modelo partido a partido usando solo datos previos a cada fecha.

    Devuelve métricas del modelo Poisson, de una referencia ingenua (frecuencias históricas
    de 1/X/2) y del mercado de apuestas si el archivo trae cuotas. `previos` son partidos
    anteriores (p. ej. la temporada pasada) que solo se usan para entrenar.
    """
    previos = [p for p in previos if p.jugado]
    jug = [p for p in partidos if p.jugado]
    if len(jug) <= minimo:
        raise ValueError(f"Se necesitan más de {minimo} partidos jugados para evaluar (hay {len(jug)}).")
    fechas = sorted({p.fecha for p in jug[minimo:]})
    res = {"modelo": _metricas(), "referencia": _metricas(), "mercado": _metricas(), "modelo_vs_mercado": _metricas()}
    over = {"n": 0, "aciertos": 0}
    calibracion = defaultdict(lambda: [0, 0.0, 0])  # tramo -> [n, prob sumada, aciertos]
    for fecha in fechas:
        anteriores = [p for p in jug if p.fecha < fecha]
        if len(anteriores) < minimo:
            continue
        entrenamiento = previos + anteriores
        if not entrenamiento:
            continue
        modelo = ModeloPoisson(**opciones_modelo).ajustar(entrenamiento, referencia=fecha)
        n = len(entrenamiento)
        freq = [sum(p.resultado_1x2 == r for p in entrenamiento) / n for r in "1X2"]
        for p in (q for q in jug if q.fecha == fecha):
            pr = modelo.predecir(p.local, p.visitante, p.neutral, p.elo_local, p.elo_visitante)
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
