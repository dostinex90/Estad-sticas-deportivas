"""Modelos predictivos de la NFL.

* EloNFL: rating Elo al estilo FiveThirtyEight (multiplicador por margen, regresión a la media
  entre temporadas, ventaja de campo).
* RatingsNFL: ratings ofensivo y defensivo ajustados por rival (mínimos cuadrados con
  regularización), de los que salen el SRS, el spread y el total esperados.
* ContextoQB / ajuste_juego: ajustes previos al partido (QB titular distinto del habitual,
  valor del QB según su EPA de pase previo, semana de descanso).
* predecir: combina ambos modelos (+ ajustes); la probabilidad de victoria sale de una normal
  sobre el margen esperado. Parámetros ajustados con 2012-2019 (ver experimentos/nfl_ajuste.py).
* simular_temporada: Monte Carlo de los partidos pendientes → probabilidades de playoffs.
* evaluar: validación semana a semana sin usar información futura.
"""

import math
import random
from collections import Counter, defaultdict, deque

from ..comun import media, normal_cdf
from . import analisis
from .equipos import conferencia, division

DESVIACION_MARGEN = 13.5  # dispersión histórica del margen y del total (spread, over/under)
DESVIACION_PROB = 12.25  # desviación con la que el margen combinado da la prob. de victoria mejor calibrada
PESO_ELO = 0.4
FACTOR_PLAYOFF = 1.3  # en playoffs las diferencias entre equipos pesan más
PUNTOS_BYE = 1.0  # ventaja por venir de semana de descanso (13+ días)
PUNTOS_CAMBIO_QB = 2.0  # penalización por titular distinto del QB habitual
PESO_VALOR_QB = 0.5  # fracción de la diferencia de EPA por partido entre el titular y el habitual


class EloNFL:
    def __init__(self, k=20, ventaja_campo=84, regresion=1 / 3, inicial=1500, mov=3.0):
        """mov: constante del multiplicador por margen de victoria (mayor = menos corrección por
        autocorrelación de favoritos que ganan por mucho)."""
        self.k = k
        self.ventaja_campo = ventaja_campo
        self.regresion = regresion
        self.inicial = inicial
        self.mov = mov
        self.rating = {}
        self.historial = defaultdict(list)  # equipo -> [(temporada, semana, rating)]
        self._temporada = None

    def _r(self, e):
        return self.rating.get(e, self.inicial)

    def diferencia(self, local, visitante, neutral=False):
        return self._r(local) - self._r(visitante) + (0 if neutral else self.ventaja_campo)

    def prob_local(self, local, visitante, neutral=False):
        return 1 / (1 + 10 ** (-self.diferencia(local, visitante, neutral) / 400))

    def margen(self, local, visitante, neutral=False):
        """Ventaja esperada del local en puntos (25 puntos Elo ≈ 1 punto)."""
        return self.diferencia(local, visitante, neutral) / 25

    def _nueva_temporada(self, temporada):
        if self._temporada is not None and temporada != self._temporada:
            self.rating = {e: r + (self.inicial - r) * self.regresion for e, r in self.rating.items()}
        self._temporada = temporada

    def actualizar(self, j):
        self._nueva_temporada(j.temporada)
        dif = self.diferencia(j.local, j.visitante, j.neutral)
        esperado = 1 / (1 + 10 ** (-dif / 400))
        real = 1.0 if j.margen > 0 else 0.0 if j.margen < 0 else 0.5
        dif_ganador = dif if j.margen > 0 else -dif
        multiplicador = math.log(abs(j.margen) + 1) * self.mov / (dif_ganador * 0.001 + self.mov) if j.margen else 1.0
        delta = self.k * multiplicador * (real - esperado)
        self.rating[j.local] = self._r(j.local) + delta
        self.rating[j.visitante] = self._r(j.visitante) - delta
        for e in (j.local, j.visitante):
            self.historial[e].append((j.temporada, j.semana, self.rating[e]))

    def procesar(self, juegos):
        for j in juegos:
            if j.jugado:
                self.actualizar(j)
        return self

    def ranking(self):
        return sorted(self.rating.items(), key=lambda kv: -kv[1])


class RatingsNFL:
    def __init__(self, peso_temporada_anterior=0.15, regularizacion=4.0, iteraciones=60):
        """peso_temporada_anterior: cuánto cuenta cada partido de la temporada previa (se
        multiplica por temporada hacia atrás). regularizacion: partidos ficticios contra un
        rival medio que estabilizan los ratings al principio de la temporada."""
        self.peso_anterior = peso_temporada_anterior
        self.regularizacion = regularizacion
        self.iteraciones = iteraciones
        self.ofensa = {}
        self.defensa = {}
        self.media = 22.0
        self.ventaja_campo = 2.0

    def ajustar(self, juegos, temporada=None):
        jug = [j for j in juegos if j.jugado]
        if not jug:
            raise ValueError("No hay partidos jugados para ajustar los ratings.")
        temporada = temporada or max(j.temporada for j in jug)
        datos = []
        for j in jug:
            if j.temporada > temporada:
                continue
            w = self.peso_anterior ** (temporada - j.temporada)
            if w >= 0.01:
                datos.append((j, w))
        peso = sum(w for _, w in datos)
        self.media = sum(w * j.total for j, w in datos) / (2 * peso)
        equipos = {j.local for j, _ in datos} | {j.visitante for j, _ in datos}
        o = {e: 0.0 for e in equipos}
        d = {e: 0.0 for e in equipos}
        h = 0.0
        lam = self.regularizacion
        for _ in range(self.iteraciones):
            num, den = defaultdict(float), defaultdict(float)
            for j, w in datos:
                hh = 0 if j.neutral else h / 2
                num[j.local] += w * (j.puntos_local - self.media - hh + d[j.visitante])
                den[j.local] += w
                num[j.visitante] += w * (j.puntos_visitante - self.media + hh + d[j.local])
                den[j.visitante] += w
            o = {e: num[e] / (den[e] + lam) for e in equipos}
            num, den = defaultdict(float), defaultdict(float)
            for j, w in datos:
                hh = 0 if j.neutral else h / 2
                num[j.local] += w * (self.media - hh + o[j.visitante] - j.puntos_visitante)
                den[j.local] += w
                num[j.visitante] += w * (self.media + hh + o[j.local] - j.puntos_local)
                den[j.visitante] += w
            d = {e: num[e] / (den[e] + lam) for e in equipos}
            num_h = den_h = 0.0
            for j, w in datos:
                if not j.neutral:
                    esperado = (o[j.local] - d[j.visitante]) - (o[j.visitante] - d[j.local])
                    num_h += w * (j.margen - esperado)
                    den_h += w
            h = num_h / (den_h + 20 * lam) if den_h else 0.0
        self.ofensa, self.defensa, self.ventaja_campo = o, d, h
        return self

    def srs(self, equipo):
        return self.ofensa.get(equipo, 0.0) + self.defensa.get(equipo, 0.0)

    def puntos(self, local, visitante, neutral=False):
        hh = 0 if neutral else self.ventaja_campo / 2
        pl = self.media + hh + self.ofensa.get(local, 0.0) - self.defensa.get(visitante, 0.0)
        pv = self.media - hh + self.ofensa.get(visitante, 0.0) - self.defensa.get(local, 0.0)
        return pl, pv

    def ranking(self):
        return sorted(((e, self.ofensa[e], self.defensa[e], self.srs(e)) for e in self.ofensa), key=lambda f: -f[3])


class ContextoQB:
    """Historial de QB titulares previo a cada partido: el habitual de cada equipo (el más
    frecuente en sus últimos `ventana` partidos) y el EPA de pase por dropback de cada QB en sus
    titularidades anteriores, encogido hacia `previo` con `m0` dropbacks ficticios."""

    def __init__(self, ventana=8, m0=150, previo=-0.05, jugadas=35):
        self.ultimos = defaultdict(lambda: deque(maxlen=ventana))
        self.epa = defaultdict(float)
        self.dropbacks = defaultdict(float)
        self.m0, self.previo, self.jugadas = m0, previo, jugadas

    def agregar(self, j):
        for eq, qb, epa, db in ((j.local, j.qb_local, j.epa_pase_local, j.jugadas_pase_local),
                                (j.visitante, j.qb_visitante, j.epa_pase_visitante, j.jugadas_pase_visitante)):
            if qb:
                self.ultimos[eq].append(qb)
                self.epa[qb] += epa or 0.0
                self.dropbacks[qb] += db or 0

    def habitual(self, equipo):
        hist = self.ultimos.get(equipo)
        return Counter(hist).most_common(1)[0][0] if hist else None

    def valor(self, qb):
        """EPA de pase esperado por dropback del QB."""
        return (self.epa[qb] + self.m0 * self.previo) / (self.dropbacks[qb] + self.m0)

    def ajuste(self, equipo, qb):
        """Puntos que pierde (negativo) o gana el equipo por su titular frente al habitual."""
        habitual = self.habitual(equipo)
        if not (habitual and qb and qb != habitual):
            return 0.0
        return -PUNTOS_CAMBIO_QB + PESO_VALOR_QB * self.jugadas * (self.valor(qb) - self.valor(habitual))


def contexto_qb(juegos, antes_de=None):
    """ContextoQB con los partidos jugados (anteriores a la fecha `antes_de`, si se indica)."""
    ctx = ContextoQB()
    for j in sorted((j for j in juegos if j.jugado), key=lambda j: j.fecha):
        if antes_de is not None and j.fecha >= antes_de:
            break
        ctx.agregar(j)
    return ctx


def ajuste_juego(j, contexto=None):
    """Puntos de ventaja extra para el local con información previa al partido (descanso y QB)."""
    bye = (1.0 if (j.descanso_local or 0) >= 13 else 0.0) - (1.0 if (j.descanso_visitante or 0) >= 13 else 0.0)
    a = PUNTOS_BYE * bye
    if contexto is not None:
        a += contexto.ajuste(j.local, j.qb_local) - contexto.ajuste(j.visitante, j.qb_visitante)
    return a


def predecir(elo, ratings, local, visitante, neutral=False, peso_elo=PESO_ELO, ajuste=0.0, playoff=False):
    """ajuste: puntos extra para el local (ver ajuste_juego); playoff: aplica FACTOR_PLAYOFF."""
    pl, pv = ratings.puntos(local, visitante, neutral)
    margen_ratings = pl - pv
    margen_elo = elo.margen(local, visitante, neutral)
    margen = peso_elo * margen_elo + (1 - peso_elo) * margen_ratings + ajuste
    if playoff:
        margen *= FACTOR_PLAYOFF
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


def ajustar_modelos(juegos, temporada):
    jug = [j for j in juegos if j.jugado and j.temporada <= temporada]
    elo = EloNFL().procesar(jug)
    ratings = RatingsNFL().ajustar(jug, temporada)
    return elo, ratings


def predecir_juego(elo, ratings, j, contexto=None):
    """predecir() para un partido del calendario, con sus ajustes previos."""
    return predecir(elo, ratings, j.local, j.visitante, j.neutral, ajuste=ajuste_juego(j, contexto), playoff=j.es_playoff)


def simular_temporada(juegos, temporada, simulaciones=5000, semilla=None):
    """Simula los partidos pendientes de temporada regular. Devuelve, por equipo, la
    probabilidad de playoffs, de ganar la división, de ser 1º de conferencia y las victorias medias."""
    rng = random.Random(semilla)
    elo, ratings = ajustar_modelos(juegos, temporada)
    reg = [j for j in juegos if j.temporada == temporada and j.tipo == "REG"]
    pendientes = [j for j in reg if not j.jugado]
    base = analisis.clasificacion(juegos, temporada)
    equipos = list(base)
    ctx = contexto_qb(juegos)
    probs = [(j, predecir_juego(elo, ratings, j, ctx)["prob_local"]) for j in pendientes]

    contador = {e: defaultdict(float) for e in equipos}
    for _ in range(simulaciones):
        victorias = {e: base[e].total.g + 0.5 * base[e].total.e for e in equipos}
        div_v = {e: base[e].division.g + 0.5 * base[e].division.e for e in equipos}
        for j, p in probs:
            ganador, perdedor = (j.local, j.visitante) if rng.random() < p else (j.visitante, j.local)
            if ganador in victorias:
                victorias[ganador] += 1
                if division(ganador) == division(perdedor):
                    div_v[ganador] += 1
        # Desempate: victorias, victorias divisionales, sorteo
        azar = {e: rng.random() for e in equipos}
        clave = lambda e: (-victorias[e], -div_v[e], azar[e])  # noqa: E731
        for conf in ("AFC", "NFC"):
            eq_conf = [e for e in equipos if conferencia(e) == conf]
            campeones = []
            for div in {division(e) for e in eq_conf}:
                campeones.append(min((e for e in eq_conf if division(e) == div), key=clave))
            campeones.sort(key=clave)
            comodines = sorted((e for e in eq_conf if e not in campeones), key=clave)[:3]
            for e in campeones:
                contador[e]["division"] += 1
                contador[e]["playoffs"] += 1
            for e in comodines:
                contador[e]["playoffs"] += 1
            if campeones:
                contador[campeones[0]]["primero"] += 1
        for e in equipos:
            contador[e]["victorias"] += victorias[e]
    return {e: {k: v / simulaciones for k, v in c.items()} for e, c in contador.items()}, len(pendientes)


def evaluar(juegos, temporada):
    """Predice cada semana de `temporada` usando solo los partidos anteriores a esa semana."""
    jug = sorted((j for j in juegos if j.jugado and j.temporada <= temporada), key=lambda j: j.fecha)
    objetivo = [j for j in jug if j.temporada == temporada]
    if not objetivo:
        raise ValueError(f"No hay partidos jugados en {temporada}.")
    if not any(j.temporada < temporada for j in jug):
        print("  Aviso: sin temporada anterior en los datos, las primeras semanas parten de cero.")
    elo = EloNFL()
    ctx = ContextoQB()
    idx = idx_qb = 0
    m = defaultdict(float)
    semanas = sorted({(j.tipo != "REG", j.semana) for j in objetivo})
    for clave in semanas:
        de_semana = [j for j in objetivo if (j.tipo != "REG", j.semana) == clave]
        inicio = min(j.fecha for j in de_semana)
        while idx < len(jug) and jug[idx].fecha < inicio:
            elo.actualizar(jug[idx])
            idx += 1
        previos = jug[:idx]
        if not previos:
            continue
        ratings = RatingsNFL().ajustar(previos, temporada)
        elo._nueva_temporada(temporada)
        for j in de_semana:
            while idx_qb < len(jug) and jug[idx_qb].fecha < j.fecha:  # QB: hasta el día anterior
                ctx.agregar(jug[idx_qb])
                idx_qb += 1
            pr = predecir_juego(elo, ratings, j, ctx)
            if j.margen == 0:
                continue
            gana_local = j.margen > 0
            p = min(max(pr["prob_local"], 1e-12), 1 - 1e-12)
            m["n"] += 1
            m["logloss"] -= math.log(p if gana_local else 1 - p)
            m["aciertos"] += (pr["margen"] > 0) == gana_local
            m["aciertos_elo"] += (pr["margen_elo"] > 0) == gana_local
            m["aciertos_ratings"] += (pr["margen_ratings"] > 0) == gana_local
            m["brier"] += (pr["prob_local"] - gana_local) ** 2
            m["error_margen"] += abs(j.margen - pr["margen"])
            m["error_total"] += abs(j.total - pr["total"])
            if j.linea is not None:
                m["n_linea"] += 1
                m["error_margen_m"] += abs(j.margen - pr["margen"])
                m["error_linea"] += abs(j.margen - j.linea)
                if j.linea != 0:
                    m["n_fav"] += 1
                    m["aciertos_mercado"] += (j.linea > 0) == gana_local
                    m["aciertos_modelo_fav"] += (pr["margen"] > 0) == gana_local
                ventaja = pr["margen"] - j.linea
                if ventaja != 0 and j.margen != j.linea:
                    acierto = (ventaja > 0) == (j.margen > j.linea)
                    m["ats_n"] += 1
                    m["ats_aciertos"] += acierto
                    if abs(ventaja) >= 3:
                        m["ats3_n"] += 1
                        m["ats3_aciertos"] += acierto
            if j.total_linea is not None:
                m["n_total"] += 1
                m["error_total_m"] += abs(j.total - pr["total"])
                m["error_total_linea"] += abs(j.total - j.total_linea)
                if pr["total"] != j.total_linea and j.total != j.total_linea:
                    m["ou_n"] += 1
                    m["ou_aciertos"] += (pr["total"] > j.total_linea) == (j.total > j.total_linea)
    return dict(m)


def fuerza_calendario(juegos, ratings, equipo, temporada, pendientes=False):
    """SRS medio de los rivales del equipo (jugados o pendientes)."""
    rivales = [j.visitante if j.local == equipo else j.local for j in juegos
               if j.temporada == temporada and j.tipo == "REG" and j.participa(equipo) and j.jugado != pendientes]
    return media(ratings.srs(r) for r in rivales), len(rivales)
