"""Estadísticas descriptivas de fútbol: clasificación, equipos, liga y enfrentamientos."""

from collections import Counter
from dataclasses import dataclass, field

from ..comun import pct
from .datos import ESTADISTICAS

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
    sin_marcar: int = 0
    ambos_marcan: int = 0
    mas_1_5: int = 0
    mas_2_5: int = 0
    mas_3_5: int = 0
    resultados: list = field(default_factory=list)  # "G", "E", "P" en orden cronológico
    marcadores: Counter = field(default_factory=Counter)  # (favor, contra) -> veces
    # Descanso / segunda parte
    con_descanso: int = 0
    ganando_descanso: int = 0
    empatando_descanso: int = 0
    perdiendo_descanso: int = 0
    gano_tras_ganar_descanso: int = 0
    no_perdio_tras_perder_descanso: int = 0  # remontadas (empate o victoria)
    gano_tras_perder_descanso: int = 0
    goles_favor_1t: int = 0
    goles_contra_1t: int = 0
    goles_favor_2t: int = 0
    goles_contra_2t: int = 0
    # Estadísticas de juego: nombre -> [a favor, en contra, partidos con dato]
    juego: dict = field(default_factory=lambda: {n: [0, 0, 0] for n in ESTADISTICAS})

    @property
    def puntos(self):
        return self.ganados * PUNTOS_VICTORIA + self.empatados * PUNTOS_EMPATE

    @property
    def diferencia(self):
        return self.goles_favor - self.goles_contra

    @property
    def puntos_por_partido(self):
        return self.puntos / self.jugados if self.jugados else 0.0

    @property
    def porcentaje_victorias(self):
        return pct(self.ganados, self.jugados)

    @property
    def goles_favor_por_partido(self):
        return self.goles_favor / self.jugados if self.jugados else 0.0

    @property
    def goles_contra_por_partido(self):
        return self.goles_contra / self.jugados if self.jugados else 0.0

    def forma(self, ultimos=5):
        return "".join(self.resultados[-ultimos:])

    def tiene(self, nombre):
        return self.juego[nombre][2] > 0

    def favor_pp(self, nombre):
        f, _, n = self.juego[nombre]
        return f / n if n else 0.0

    def contra_pp(self, nombre):
        _, c, n = self.juego[nombre]
        return c / n if n else 0.0

    def conversion(self):
        """% de tiros convertidos en gol (solo partidos con dato de tiros)."""
        return pct(self._goles_con("tiros"), self.juego["tiros"][0])

    def precision(self):
        """% de tiros que van a puerta."""
        return pct(self.juego["tiros_puerta"][0], self.juego["tiros"][0])

    def eficacia_a_puerta(self):
        return pct(self._goles_con("tiros_puerta"), self.juego["tiros_puerta"][0])

    def paradas(self):
        """% de tiros a puerta rivales que no terminaron en gol (aprox. rendimiento del portero)."""
        tiros_contra = self.juego["tiros_puerta"][1]
        return pct(tiros_contra - self._goles_contra_con("tiros_puerta"), tiros_contra)

    def dominio_tiros(self):
        """Cuota de tiros del equipo sobre el total de tiros de sus partidos (TSR)."""
        f, c, _ = self.juego["tiros"]
        return pct(f, f + c)

    # Goles anotados solo en los partidos que tienen el dato, para no distorsionar ratios
    def _goles_con(self, nombre):
        return self._goles_por_dato.get(nombre, (0, 0))[0]

    def _goles_contra_con(self, nombre):
        return self._goles_por_dato.get(nombre, (0, 0))[1]

    def __post_init__(self):
        self._goles_por_dato = {}

    def _registrar(self, partido, es_local):
        gf, gc = (partido.goles_local, partido.goles_visitante) if es_local else (partido.goles_visitante, partido.goles_local)
        self.jugados += 1
        self.goles_favor += gf
        self.goles_contra += gc
        self.marcadores[(gf, gc)] += 1
        self.porterias_cero += gc == 0
        self.sin_marcar += gf == 0
        self.ambos_marcan += gf > 0 and gc > 0
        self.mas_1_5 += gf + gc > 1.5
        self.mas_2_5 += gf + gc > 2.5
        self.mas_3_5 += gf + gc > 3.5
        if gf > gc:
            self.ganados += 1
            self.resultados.append("G")
        elif gf == gc:
            self.empatados += 1
            self.resultados.append("E")
        else:
            self.perdidos += 1
            self.resultados.append("P")

        if partido.tiene_descanso:
            hf, hc = (partido.descanso_local, partido.descanso_visitante) if es_local else (partido.descanso_visitante, partido.descanso_local)
            self.con_descanso += 1
            self.goles_favor_1t += hf
            self.goles_contra_1t += hc
            self.goles_favor_2t += gf - hf
            self.goles_contra_2t += gc - hc
            if hf > hc:
                self.ganando_descanso += 1
                self.gano_tras_ganar_descanso += gf > gc
            elif hf == hc:
                self.empatando_descanso += 1
            else:
                self.perdiendo_descanso += 1
                self.no_perdio_tras_perder_descanso += gf >= gc
                self.gano_tras_perder_descanso += gf > gc

        for nombre, (vl, vv) in partido.estadisticas.items():
            favor, contra = (vl, vv) if es_local else (vv, vl)
            dato = self.juego[nombre]
            dato[0] += favor
            dato[1] += contra
            dato[2] += 1
            g = self._goles_por_dato.get(nombre, (0, 0))
            self._goles_por_dato[nombre] = (g[0] + gf, g[1] + gc)


def calcular_estadisticas(partidos, condicion=None):
    """Estadísticas por equipo. condicion: None (todos), "local" o "visitante"."""
    stats = {}
    for p in partidos:
        if not p.jugado:
            continue
        if condicion in (None, "local"):
            stats.setdefault(p.local, EstadisticasEquipo(p.local))._registrar(p, True)
        if condicion in (None, "visitante"):
            stats.setdefault(p.visitante, EstadisticasEquipo(p.visitante))._registrar(p, False)
    return stats


def ordenar_tabla(stats):
    return sorted(stats, key=lambda s: (-s.puntos, -s.diferencia, -s.goles_favor, s.equipo))


def tabla_posiciones(partidos, condicion=None):
    """Clasificación ordenada por puntos, diferencia de goles, goles a favor y nombre."""
    return ordenar_tabla(calcular_estadisticas(partidos, condicion).values())


def tabla_descanso(partidos):
    """Clasificación hipotética si los partidos hubieran terminado al descanso."""
    from dataclasses import replace

    al_descanso = [
        replace(p, goles_local=p.descanso_local, goles_visitante=p.descanso_visitante, estadisticas={})
        for p in partidos if p.jugado and p.tiene_descanso
    ]
    return tabla_posiciones(al_descanso)


def evolucion_posiciones(partidos, equipo):
    """Lista de (fecha, posición, puntos) después de cada partido del equipo."""
    jug = [p for p in partidos if p.jugado]
    evolucion = []
    for p in jug:
        if not p.participa(equipo):
            continue
        tabla = tabla_posiciones([q for q in jug if q.fecha <= p.fecha])
        for pos, s in enumerate(tabla, 1):
            if s.equipo == equipo:
                evolucion.append((p.fecha, pos, s.puntos))
                break
    return evolucion


def rendimiento_por_nivel(partidos, equipo):
    """Récord del equipo frente a rivales de la parte alta, media y baja de la tabla actual."""
    tabla = [s.equipo for s in tabla_posiciones(partidos)]
    n = len(tabla)
    tercio = {e: ("Parte alta" if i < n / 3 else "Parte media" if i < 2 * n / 3 else "Parte baja") for i, e in enumerate(tabla)}
    grupos = {}
    for p in partidos:
        if not (p.jugado and p.participa(equipo)):
            continue
        es_local = p.local == equipo
        nivel = tercio[p.rival(equipo)]
        grupos.setdefault(nivel, EstadisticasEquipo(nivel))._registrar(p, es_local)
    return [grupos[k] for k in ("Parte alta", "Parte media", "Parte baja") if k in grupos]


def enfrentamientos_directos(partidos, equipo_a, equipo_b):
    """Partidos entre dos equipos y resumen de victorias, empates y goles."""
    duelos = [p for p in partidos if p.jugado and p.participa(equipo_a) and p.participa(equipo_b)]
    resumen = {equipo_a: 0, equipo_b: 0, "empates": 0, "goles_" + equipo_a: 0, "goles_" + equipo_b: 0}
    for p in duelos:
        resumen[p.ganador or "empates"] += 1
        resumen["goles_" + p.local] += p.goles_local
        resumen["goles_" + p.visitante] += p.goles_visitante
    return duelos, resumen


def resumen_liga(partidos):
    """Métricas globales de la competición."""
    jug = [p for p in partidos if p.jugado]
    n = len(jug)
    if n == 0:
        return {"partidos": 0}
    goles = [p.total_goles for p in jug]
    locales = sum(p.resultado_1x2 == "1" for p in jug)
    visitantes = sum(p.resultado_1x2 == "2" for p in jug)
    r = {
        "partidos": n,
        "pendientes": len(partidos) - n,
        "goles": sum(goles),
        "goles_por_partido": sum(goles) / n,
        "goles_local_pp": sum(p.goles_local for p in jug) / n,
        "goles_visitante_pp": sum(p.goles_visitante for p in jug) / n,
        "pct_local": pct(locales, n),
        "pct_empate": pct(n - locales - visitantes, n),
        "pct_visitante": pct(visitantes, n),
        "ppp_local": (3 * locales + (n - locales - visitantes)) / n,
        "ppp_visitante": (3 * visitantes + (n - locales - visitantes)) / n,
        "pct_ambos_marcan": pct(sum(1 for p in jug if p.goles_local and p.goles_visitante), n),
        "pct_mas_1_5": pct(sum(g > 1.5 for g in goles), n),
        "pct_mas_2_5": pct(sum(g > 2.5 for g in goles), n),
        "pct_mas_3_5": pct(sum(g > 3.5 for g in goles), n),
        "pct_0_0": pct(sum(g == 0 for g in goles), n),
        "mayor_goleada": max(jug, key=lambda p: (abs(p.goles_local - p.goles_visitante), p.total_goles)),
        "mas_goles": max(jug, key=lambda p: (p.total_goles, -abs(p.goles_local - p.goles_visitante))),
        "marcadores": Counter((p.goles_local, p.goles_visitante) for p in jug).most_common(8),
        "distribucion_goles": Counter(goles),
    }

    con_ht = [p for p in jug if p.tiene_descanso]
    if con_ht:
        def signo(a, b):
            return "1" if a > b else "2" if a < b else "X"

        matriz = Counter(signo(p.descanso_local, p.descanso_visitante) + "/" + p.resultado_1x2 for p in con_ht)
        goles_1t = sum(p.descanso_local + p.descanso_visitante for p in con_ht)
        goles_2t = sum(p.total_goles for p in con_ht) - goles_1t
        r["descanso"] = {
            "partidos": len(con_ht),
            "matriz": matriz,
            "goles_1t_pp": goles_1t / len(con_ht),
            "goles_2t_pp": goles_2t / len(con_ht),
            "remontadas": sum(
                1 for p in con_ht
                if signo(p.descanso_local, p.descanso_visitante) in "12"
                and p.resultado_1x2 not in ("X", signo(p.descanso_local, p.descanso_visitante))
            ),
        }

    juego = {}
    for nombre in ESTADISTICAS:
        con = [p.estadisticas[nombre] for p in jug if nombre in p.estadisticas]
        if con:
            juego[nombre] = (
                sum(a for a, _ in con) / len(con),
                sum(b for _, b in con) / len(con),
                len(con),
            )
    r["juego"] = juego

    con_cuotas = [p for p in jug if p.cuotas]
    if con_cuotas:
        favorito_gana = 0
        for p in con_cuotas:
            c1, _, c2 = p.cuotas
            favorito = "1" if c1 < c2 else "2"
            favorito_gana += p.resultado_1x2 == favorito
        r["pct_favorito_gana"] = pct(favorito_gana, len(con_cuotas))
        r["partidos_con_cuotas"] = len(con_cuotas)
    return r


# Métricas para el comando "lideres": nombre -> (descripción, función, mayor es mejor, requiere estadística)
METRICAS = {
    "puntos_pp": ("Puntos por partido", lambda s: s.puntos_por_partido, True, None),
    "ataque": ("Goles a favor por partido", lambda s: s.goles_favor_por_partido, True, None),
    "defensa": ("Goles en contra por partido", lambda s: s.goles_contra_por_partido, False, None),
    "porterias_cero": ("% porterías a cero", lambda s: pct(s.porterias_cero, s.jugados), True, None),
    "ambos_marcan": ("% partidos en que marcan ambos", lambda s: pct(s.ambos_marcan, s.jugados), True, None),
    "mas_2_5": ("% partidos con más de 2.5 goles", lambda s: pct(s.mas_2_5, s.jugados), True, None),
    "remontadas": ("Puntos rescatados perdiendo al descanso", lambda s: s.no_perdio_tras_perder_descanso, True, None),
    "segunda_parte": ("Diferencia de goles en 2ª parte", lambda s: s.goles_favor_2t - s.goles_contra_2t, True, None),
    "tiros": ("Tiros por partido", lambda s: s.favor_pp("tiros"), True, "tiros"),
    "tiros_contra": ("Tiros concedidos por partido", lambda s: s.contra_pp("tiros"), False, "tiros"),
    "dominio": ("% de los tiros del partido (TSR)", lambda s: s.dominio_tiros(), True, "tiros"),
    "conversion": ("% conversión de tiros", lambda s: s.conversion(), True, "tiros"),
    "precision": ("% tiros a puerta", lambda s: s.precision(), True, "tiros_puerta"),
    "paradas": ("% paradas (tiros a puerta rivales sin gol)", lambda s: s.paradas(), True, "tiros_puerta"),
    "corners": ("Córners por partido", lambda s: s.favor_pp("corners"), True, "corners"),
    "faltas": ("Faltas cometidas por partido", lambda s: s.favor_pp("faltas"), True, "faltas"),
    "amarillas": ("Amarillas por partido", lambda s: s.favor_pp("amarillas"), True, "amarillas"),
    "rojas": ("Rojas totales", lambda s: s.juego["rojas"][0], True, "rojas"),
}


def lideres(partidos, metrica, cantidad=10):
    descripcion, funcion, mayor_mejor, requiere = METRICAS[metrica]
    stats = [s for s in calcular_estadisticas(partidos).values() if requiere is None or s.tiene(requiere)]
    ordenados = sorted(stats, key=lambda s: (-funcion(s) if mayor_mejor else funcion(s), s.equipo))
    return descripcion, [(s.equipo, funcion(s)) for s in ordenados[:cantidad]]
