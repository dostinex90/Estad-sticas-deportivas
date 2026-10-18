"""Cálculos estadísticos sobre una lista de partidos."""

import math
from dataclasses import dataclass, field

PUNTOS_VICTORIA = 3
PUNTOS_EMPATE = 1


@dataclass
class EstadisticasEquipo:
    equipo: str
    jugados: int = 0
    ganados: int = 0
    empatados: int = 0
    perdidos: int = 0
    goles_favor: int = 0
    goles_contra: int = 0
    porterias_cero: int = 0
    resultados: list = field(default_factory=list)  # "G", "E", "P" en orden cronológico

    @property
    def puntos(self):
        return self.ganados * PUNTOS_VICTORIA + self.empatados * PUNTOS_EMPATE

    @property
    def diferencia(self):
        return self.goles_favor - self.goles_contra

    @property
    def porcentaje_victorias(self):
        return 100 * self.ganados / self.jugados if self.jugados else 0.0

    @property
    def goles_favor_por_partido(self):
        return self.goles_favor / self.jugados if self.jugados else 0.0

    @property
    def goles_contra_por_partido(self):
        return self.goles_contra / self.jugados if self.jugados else 0.0

    def forma(self, ultimos=5):
        return "".join(self.resultados[-ultimos:])

    def racha_actual(self):
        """Devuelve (resultado, longitud) de la racha vigente, p. ej. ("G", 3)."""
        if not self.resultados:
            return None, 0
        ultimo = self.resultados[-1]
        n = 0
        for r in reversed(self.resultados):
            if r != ultimo:
                break
            n += 1
        return ultimo, n

    def _registrar(self, gf, gc):
        self.jugados += 1
        self.goles_favor += gf
        self.goles_contra += gc
        if gc == 0:
            self.porterias_cero += 1
        if gf > gc:
            self.ganados += 1
            self.resultados.append("G")
        elif gf == gc:
            self.empatados += 1
            self.resultados.append("E")
        else:
            self.perdidos += 1
            self.resultados.append("P")


def calcular_estadisticas(partidos, condicion=None):
    """Estadísticas por equipo. condicion: None (todos), "local" o "visitante"."""
    stats = {}

    def obtener(equipo):
        if equipo not in stats:
            stats[equipo] = EstadisticasEquipo(equipo)
        return stats[equipo]

    for p in partidos:
        if condicion in (None, "local"):
            obtener(p.local)._registrar(p.goles_local, p.goles_visitante)
        if condicion in (None, "visitante"):
            obtener(p.visitante)._registrar(p.goles_visitante, p.goles_local)
    return stats


def tabla_posiciones(partidos, condicion=None):
    """Clasificación ordenada por puntos, diferencia de goles, goles a favor y nombre."""
    stats = calcular_estadisticas(partidos, condicion)
    return sorted(
        stats.values(),
        key=lambda s: (-s.puntos, -s.diferencia, -s.goles_favor, s.equipo),
    )


def enfrentamientos_directos(partidos, equipo_a, equipo_b):
    """Partidos entre dos equipos y resumen de victorias/empates."""
    duelos = [p for p in partidos if p.participa(equipo_a) and p.participa(equipo_b)]
    resumen = {equipo_a: 0, equipo_b: 0, "empates": 0}
    for p in duelos:
        resumen[p.ganador or "empates"] += 1
    return duelos, resumen


def resumen_liga(partidos):
    """Métricas globales de la competición."""
    n = len(partidos)
    if n == 0:
        return {"partidos": 0}
    goles = [p.goles_local + p.goles_visitante for p in partidos]
    locales = sum(1 for p in partidos if p.goles_local > p.goles_visitante)
    visitantes = sum(1 for p in partidos if p.goles_visitante > p.goles_local)
    mayor = max(partidos, key=lambda p: (abs(p.goles_local - p.goles_visitante), p.goles_local + p.goles_visitante))
    return {
        "partidos": n,
        "goles": sum(goles),
        "goles_por_partido": sum(goles) / n,
        "pct_local": 100 * locales / n,
        "pct_empate": 100 * (n - locales - visitantes) / n,
        "pct_visitante": 100 * visitantes / n,
        "pct_ambos_marcan": 100 * sum(1 for p in partidos if p.goles_local and p.goles_visitante) / n,
        "pct_mas_2_5": 100 * sum(1 for g in goles if g > 2.5) / n,
        "mayor_goleada": mayor,
    }


def _poisson(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)


def predecir_partido(partidos, local, visitante, max_goles=10):
    """Predicción con un modelo de Poisson basado en fuerzas de ataque y defensa.

    Fuerza de ataque local = (goles marcados en casa por partido) / (media de goles locales de la liga), etc.
    Devuelve goles esperados, probabilidades 1X2 y el marcador más probable.
    """
    en_casa = calcular_estadisticas(partidos, "local")
    fuera = calcular_estadisticas(partidos, "visitante")
    if local not in en_casa or visitante not in fuera:
        raise ValueError("No hay suficientes datos: el local debe haber jugado en casa y el visitante fuera.")

    n = len(partidos)
    media_local = sum(p.goles_local for p in partidos) / n
    media_visit = sum(p.goles_visitante for p in partidos) / n
    if media_local == 0 or media_visit == 0:
        raise ValueError("La liga no tiene goles suficientes para estimar el modelo.")

    l, v = en_casa[local], fuera[visitante]
    ataque_local = l.goles_favor_por_partido / media_local
    defensa_visit = v.goles_contra_por_partido / media_local
    ataque_visit = v.goles_favor_por_partido / media_visit
    defensa_local = l.goles_contra_por_partido / media_visit

    lam_local = ataque_local * defensa_visit * media_local
    lam_visit = ataque_visit * defensa_local * media_visit

    p_local = p_empate = p_visit = 0.0
    mejor = (0, 0, -1.0)
    for i in range(max_goles + 1):
        for j in range(max_goles + 1):
            prob = _poisson(i, lam_local) * _poisson(j, lam_visit)
            if i > j:
                p_local += prob
            elif i == j:
                p_empate += prob
            else:
                p_visit += prob
            if prob > mejor[2]:
                mejor = (i, j, prob)

    total = p_local + p_empate + p_visit
    return {
        "goles_esperados_local": lam_local,
        "goles_esperados_visitante": lam_visit,
        "prob_local": p_local / total,
        "prob_empate": p_empate / total,
        "prob_visitante": p_visit / total,
        "marcador_probable": mejor[:2],
        "prob_marcador": mejor[2],
    }
