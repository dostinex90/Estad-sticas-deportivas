"""Modelos predictivos de la NBA.

* EloNBA: rating Elo al estilo FiveThirtyEight (multiplicador por margen, regresión a la media
  entre temporadas, ventaja de campo).
* RatingsNBA: ratings ofensivo y defensivo ajustados por rival, con más peso para los partidos
  recientes (vida media en días). De ellos salen el margen y el total de puntos esperados.
* ajuste_descanso: puntos que pierde el equipo que juega el segundo de dos días seguidos.
* predecir: combina ambos modelos; la probabilidad de victoria sale de una normal sobre el
  margen esperado. Parámetros ajustados con 2012-13 a 2018-19 (ver experimentos/nba_ajuste.py).
* simular_temporada: Monte Carlo de lo que queda de temporada regular, play-in y playoffs.
* evaluar: validación día a día sin usar información futura.
"""

import math
import random
from collections import defaultdict

from ..comun import normal_cdf
from . import analisis
from .datos import descansos
from .equipos import CONFERENCIAS, conferencia

# Dispersión del margen y del total reales alrededor de los esperados (1.25 × error medio en 2015-16 a 2018-19);
# solo se usan para las líneas y totales que indique el usuario
DESVIACION_MARGEN = 12.5
DESVIACION_TOTAL = 18.0
DESVIACION_PROB = 10.0  # desviación con la que el margen combinado da la prob. de victoria mejor calibrada
PESO_ELO = 0.6
PUNTOS_B2B = 1.5  # penalización por jugar el segundo de dos días seguidos
# Incertidumbre sobre la fuerza real de cada equipo antes de empezar la temporada (puntos). En 2012-13
# a 2018-19 las victorias previstas en pretemporada fallaron 9.4 de media cuadrática, 8.4 más de lo que
# explica el azar de los partidos, unos 3 puntos de fuerza (ver experimentos/nba_incertidumbre.py).
INCERTIDUMBRE_FUERZA = 3.0
ELO_POR_PUNTO = 28  # 28 puntos Elo ≈ 1 punto de margen


class EloNBA:
    def __init__(self, k=15, ventaja_campo=70, regresion=0.25, inicial=1500):
        self.k = k
        self.ventaja_campo = ventaja_campo
        self.regresion = regresion
        self.inicial = inicial
        self.rating = {}
        self.historial = defaultdict(list)  # equipo -> [(temporada, fecha, rating)]
        self._temporada = None

    def _r(self, e):
        return self.rating.get(e, self.inicial)

    def diferencia(self, local, visitante, neutral=False):
        return self._r(local) - self._r(visitante) + (0 if neutral else self.ventaja_campo)

    def prob_local(self, local, visitante, neutral=False):
        return 1 / (1 + 10 ** (-self.diferencia(local, visitante, neutral) / 400))

    def margen(self, local, visitante, neutral=False):
        return self.diferencia(local, visitante, neutral) / ELO_POR_PUNTO

    def nueva_temporada(self, temporada):
        if self._temporada is not None and temporada != self._temporada:
            self.rating = {e: r + (self.inicial - r) * self.regresion for e, r in self.rating.items()}
        self._temporada = temporada

    def actualizar(self, p):
        self.nueva_temporada(p.temporada)
        dif = self.diferencia(p.local, p.visitante, p.neutral)
        esperado = 1 / (1 + 10 ** (-dif / 400))
        real = 1.0 if p.margen > 0 else 0.0
        dif_ganador = dif if p.margen > 0 else -dif
        multiplicador = (abs(p.margen) + 3) ** 0.8 / (7.5 + 0.006 * dif_ganador)
        delta = self.k * multiplicador * (real - esperado)
        self.rating[p.local] = self._r(p.local) + delta
        self.rating[p.visitante] = self._r(p.visitante) - delta
        for e in (p.local, p.visitante):
            self.historial[e].append((p.temporada, p.fecha, self.rating[e]))

    def procesar(self, partidos):
        for p in partidos:
            if p.jugado:
                self.actualizar(p)
        return self

    def ranking(self):
        return sorted(self.rating.items(), key=lambda kv: -kv[1])


class RatingsNBA:
    def __init__(self, vida_media=90, peso_temporada_anterior=0.5, regularizacion=3.0, iteraciones=40):
        """vida_media: días tras los que un partido pesa la mitad. peso_temporada_anterior: factor
        extra para cada temporada hacia atrás (cambian las plantillas). regularizacion: partidos
        ficticios contra un rival medio que estabilizan los ratings a principio de temporada."""
        self.vida_media = vida_media
        self.peso_anterior = peso_temporada_anterior
        self.regularizacion = regularizacion
        self.iteraciones = iteraciones
        self.ofensa = {}
        self.defensa = {}
        self.media = 110.0
        self.ventaja_campo = 2.5

    def ajustar(self, partidos, temporada=None, fecha=None):
        """Ajusta con los partidos jugados de `temporada` y anteriores (antes de `fecha`, si se indica)."""
        jug = [p for p in partidos if p.jugado and (temporada is None or p.temporada <= temporada)
               and (fecha is None or p.fecha < fecha)]
        if not jug:
            raise ValueError("No hay partidos jugados para ajustar los ratings.")
        temporada = temporada or max(p.temporada for p in jug)
        referencia = fecha or max(p.fecha for p in jug)
        datos = []
        for p in jug:
            w = 0.5 ** ((referencia - p.fecha).days / self.vida_media) * self.peso_anterior ** (temporada - p.temporada)
            if w >= 0.01:
                datos.append((p, w))
        if not datos:
            datos = [(p, 1.0) for p in jug[-500:]]
        peso = sum(w for _, w in datos)
        self.media = sum(w * p.total for p, w in datos) / (2 * peso)
        equipos = {p.local for p, _ in datos} | {p.visitante for p, _ in datos}
        o = {e: self.ofensa.get(e, 0.0) for e in equipos}  # parte de la solución anterior si la hay
        d = {e: self.defensa.get(e, 0.0) for e in equipos}
        h = self.ventaja_campo
        lam = self.regularizacion
        for _ in range(self.iteraciones):
            num, den = defaultdict(float), defaultdict(float)
            for p, w in datos:
                hh = 0 if p.neutral else h / 2
                num[p.local] += w * (p.puntos_local - self.media - hh + d[p.visitante])
                den[p.local] += w
                num[p.visitante] += w * (p.puntos_visitante - self.media + hh + d[p.local])
                den[p.visitante] += w
            o = {e: num[e] / (den[e] + lam) for e in equipos}
            num, den = defaultdict(float), defaultdict(float)
            for p, w in datos:
                hh = 0 if p.neutral else h / 2
                num[p.local] += w * (self.media - hh + o[p.visitante] - p.puntos_visitante)
                den[p.local] += w
                num[p.visitante] += w * (self.media + hh + o[p.local] - p.puntos_local)
                den[p.visitante] += w
            d = {e: num[e] / (den[e] + lam) for e in equipos}
            num_h = den_h = 0.0
            for p, w in datos:
                if not p.neutral:
                    esperado = (o[p.local] - d[p.visitante]) - (o[p.visitante] - d[p.local])
                    num_h += w * (p.margen - esperado)
                    den_h += w
            h = num_h / (den_h + 20 * lam) if den_h else 0.0
        self.ofensa, self.defensa, self.ventaja_campo = o, d, h
        return self

    def neto(self, equipo):
        """Margen esperado frente a un equipo medio en campo neutral."""
        return self.ofensa.get(equipo, 0.0) + self.defensa.get(equipo, 0.0)

    def puntos(self, local, visitante, neutral=False):
        hh = 0 if neutral else self.ventaja_campo / 2
        pl = self.media + hh + self.ofensa.get(local, 0.0) - self.defensa.get(visitante, 0.0)
        pv = self.media - hh + self.ofensa.get(visitante, 0.0) - self.defensa.get(local, 0.0)
        return pl, pv

    def ranking(self):
        return sorted(((e, self.ofensa[e], self.defensa[e], self.neto(e)) for e in self.ofensa), key=lambda f: -f[3])


def ajuste_descanso(descanso_local, descanso_visitante, puntos_b2b=PUNTOS_B2B):
    """Puntos de ventaja extra para el local según quién juega dos días seguidos."""
    return puntos_b2b * ((descanso_visitante == 1) - (descanso_local == 1))


def predecir(elo, ratings, local, visitante, neutral=False, ajuste=0.0, peso_elo=PESO_ELO):
    pl, pv = ratings.puntos(local, visitante, neutral)
    margen_ratings = pl - pv
    margen_elo = elo.margen(local, visitante, neutral)
    margen = peso_elo * margen_elo + (1 - peso_elo) * margen_ratings + ajuste
    total = pl + pv
    return {
        "margen": margen,
        "margen_elo": margen_elo,
        "margen_ratings": margen_ratings,
        "ajuste": ajuste,
        "prob_local": normal_cdf(margen, 0, DESVIACION_PROB),
        "prob_elo": elo.prob_local(local, visitante, neutral),
        "total": total,
        "puntos_local": (total + margen) / 2,
        "puntos_visitante": (total - margen) / 2,
    }


def prob_cubrir(margen_esperado, linea):
    """Probabilidad de que el local gane por más de `linea` puntos."""
    return 1 - normal_cdf(linea, margen_esperado, DESVIACION_MARGEN)


def moneyline_justa(prob):
    """Cuota americana equivalente a una probabilidad."""
    if prob >= 0.5:
        return f"{-100 * prob / (1 - prob):.0f}"
    return f"+{100 * (1 - prob) / prob:.0f}"


def ajustar_modelos(partidos, temporada):
    """Elo y ratings con todos los partidos jugados hasta `temporada` (incluida)."""
    jug = [p for p in partidos if p.jugado and p.temporada <= temporada]
    elo = EloNBA().procesar(jug)
    elo.nueva_temporada(temporada)  # si la temporada aún no ha empezado, aplica la regresión a la media
    ratings = RatingsNBA().ajustar(jug, temporada)
    return elo, ratings


def predecir_partido(elo, ratings, p, dias=None):
    """predecir() para un partido del calendario, con el ajuste por descanso. dias: descansos()."""
    dias = dias if dias is not None else {}
    ajuste = ajuste_descanso(dias.get((p.id, p.local)), dias.get((p.id, p.visitante)))
    return predecir(elo, ratings, p.local, p.visitante, p.neutral, ajuste)


def _gana_serie(rng, p_mejor_en_casa, p_mejor_fuera, partidos=7):
    """True si gana la serie el equipo con ventaja de campo (formato 2-2-1-1-1)."""
    necesarias = partidos // 2 + 1
    casa = [True, True, False, False, True, False, True][:partidos]
    v = d = 0
    for en_casa in casa:
        if rng.random() < (p_mejor_en_casa if en_casa else p_mejor_fuera):
            v += 1
        else:
            d += 1
        if v == necesarias or d == necesarias:
            break
    return v == necesarias


def simular_temporada(partidos, temporada, simulaciones=5000, semilla=None):
    """Simula los partidos pendientes de temporada regular, el play-in (desde 2020-21) y los
    playoffs. Devuelve por equipo: victorias medias y probabilidad de top 6, de entrar en
    playoffs, de ser 1º de conferencia, de llegar a la final y de ser campeón.
    En cada simulación la fuerza de cada equipo varía al azar (INCERTIDUMBRE_FUERZA, menos cuanto
    más avanzada está la temporada), porque no se conoce con exactitud."""
    rng = random.Random(semilla)
    elo, ratings = ajustar_modelos(partidos, temporada)
    de_temporada = [p for p in partidos if p.temporada == temporada]
    reg = [p for p in de_temporada if p.tipo == "REG"]
    pendientes = [p for p in reg if not p.jugado]
    base = analisis.clasificacion(partidos, temporada)
    equipos = list(base)
    dias = descansos(de_temporada)
    margenes = [(p, predecir_partido(elo, ratings, p, dias)["margen"]) for p in pendientes]
    neto = {e: ratings.neto(e) for e in equipos}
    incertidumbre = INCERTIDUMBRE_FUERZA * math.sqrt(len(pendientes) / len(reg)) if reg else 0.0
    cache = {}

    def duelo(a, b):
        """Prob. de que gane `a` jugando en casa contra `b` (con la fuerza de esta simulación)."""
        if (a, b) not in cache:
            cache[(a, b)] = predecir(elo, ratings, a, b)["margen"]
        return normal_cdf(cache[(a, b)] + extra[a] - extra[b], 0, DESVIACION_PROB)

    con_playin = temporada >= 2021
    contador = {e: defaultdict(float) for e in equipos}
    for _ in range(simulaciones):
        extra = defaultdict(float, {e: rng.gauss(0, incertidumbre) for e in equipos})
        victorias = {e: base[e].total.g for e in equipos}
        for p, margen in margenes:
            prob = normal_cdf(margen + extra[p.local] - extra[p.visitante], 0, DESVIACION_PROB)
            ganador = p.local if rng.random() < prob else p.visitante
            if ganador in victorias:
                victorias[ganador] += 1
        azar = {e: rng.random() for e in equipos}
        clave = lambda e: (-victorias[e], -neto[e], azar[e])  # noqa: E731
        finalistas = []
        for conf in CONFERENCIAS:
            orden = sorted((e for e in equipos if conferencia(e, temporada) == conf), key=clave)
            if not orden:
                continue
            contador[orden[0]]["primero"] += 1
            for e in orden[:6]:
                contador[e]["top6"] += 1
            if con_playin:
                s7, s8, s9, s10 = orden[6:10]
                ganador_78 = s7 if rng.random() < duelo(s7, s8) else s8
                perdedor_78 = s8 if ganador_78 == s7 else s7
                ganador_910 = s9 if rng.random() < duelo(s9, s10) else s10
                octavo = perdedor_78 if rng.random() < duelo(perdedor_78, ganador_910) else ganador_910
                semillas = orden[:6] + [ganador_78, octavo]
            else:
                semillas = orden[:8]
            for e in semillas:
                contador[e]["playoffs"] += 1
            # Cuadro: 1-8, 4-5, 3-6, 2-7; el de mejor siembra tiene ventaja de campo
            ronda = [(semillas[0], semillas[7]), (semillas[3], semillas[4]), (semillas[2], semillas[5]), (semillas[1], semillas[6])]
            while True:
                vivos = []
                for a, b in ronda:
                    if semillas.index(b) < semillas.index(a):
                        a, b = b, a
                    vivos.append(a if _gana_serie(rng, duelo(a, b), 1 - duelo(b, a)) else b)
                if len(vivos) == 1:
                    break
                ronda = [(vivos[i], vivos[i + 1]) for i in range(0, len(vivos), 2)]
            finalistas.append(vivos[0])
        for e in finalistas:
            contador[e]["final"] += 1
        if len(finalistas) == 2:
            a, b = sorted(finalistas, key=clave)  # ventaja de campo para el de mejor récord
            contador[a if _gana_serie(rng, duelo(a, b), 1 - duelo(b, a)) else b]["campeon"] += 1
        for e in equipos:
            contador[e]["victorias"] += victorias[e]
    return {e: {k: v / simulaciones for k, v in c.items()} for e, c in contador.items()}, len(pendientes)


def evaluar(partidos, temporada, elo_params=None, ratings_params=None, peso_elo=PESO_ELO, puntos_b2b=PUNTOS_B2B,
            desviacion=None):
    """Predice cada día de `temporada` usando solo los partidos anteriores a ese día.
    Los parámetros opcionales permiten a experimentos/nba_ajuste.py probar variantes."""
    desviacion = desviacion or DESVIACION_PROB
    jug = sorted((p for p in partidos if p.jugado and p.temporada <= temporada), key=lambda p: p.fecha)
    objetivo = [p for p in jug if p.temporada == temporada]
    if not objetivo:
        raise ValueError(f"No hay partidos jugados en {temporada}.")
    dias = descansos([p for p in partidos if p.temporada == temporada])
    elo = EloNBA(**(elo_params or {}))
    ratings = RatingsNBA(**(ratings_params or {}))
    idx = 0
    m = defaultdict(float)
    fechas = sorted({p.fecha for p in objetivo})
    primera = True
    for fecha in fechas:
        while idx < len(jug) and jug[idx].fecha < fecha:
            elo.actualizar(jug[idx])
            idx += 1
        previos = jug[:idx]
        if not previos:
            continue
        elo.nueva_temporada(temporada)
        if primera:
            ratings.ajustar(previos, temporada, fecha)
            ratings.iteraciones, primera = 8, False  # después, cada día parte de la solución anterior
        else:
            ratings.ajustar(previos[-3000:], temporada, fecha)
        for p in (p for p in objetivo if p.fecha == fecha):
            ajuste = ajuste_descanso(dias.get((p.id, p.local)), dias.get((p.id, p.visitante)), puntos_b2b)
            pr = predecir(elo, ratings, p.local, p.visitante, p.neutral, ajuste, peso_elo)
            prob = normal_cdf(pr["margen"], 0, desviacion)
            gana_local = p.margen > 0
            q = min(max(prob, 1e-12), 1 - 1e-12)
            m["n"] += 1
            m["logloss"] -= math.log(q if gana_local else 1 - q)
            m["brier"] += (prob - gana_local) ** 2
            m["brier_elo"] += (pr["prob_elo"] - gana_local) ** 2
            m["aciertos"] += (pr["margen"] > 0) == gana_local
            m["aciertos_elo"] += (pr["margen_elo"] > 0) == gana_local
            m["aciertos_ratings"] += (pr["margen_ratings"] > 0) == gana_local
            m["error_margen"] += abs(p.margen - pr["margen"])
            m["error_total"] += abs(p.total - pr["total"])
            m["gana_local"] += gana_local
    return dict(m)
