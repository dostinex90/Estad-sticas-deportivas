"""Estadísticas de juego de la NFL por equipo y partido (tabla nfl_estadisticas_equipo de nflverse)."""

from collections import defaultdict

from ..comun import pct
from .equipos import normalizar


def _n(fila, columna):
    v = fila.get(columna)
    return v if isinstance(v, (int, float)) else 0


def metricas_partido(f):
    """Métricas de un equipo en un partido a partir de su fila de nflverse."""
    sacks_yardas = abs(_n(f, "sack_yards_lost"))
    pase_neto = _n(f, "passing_yards") - sacks_yardas
    carrera = _n(f, "rushing_yards")
    jugadas = _n(f, "attempts") + _n(f, "sacks_suffered") + _n(f, "carries")
    epa = _n(f, "passing_epa") + _n(f, "rushing_epa")
    return {
        "yardas": pase_neto + carrera,
        "yardas_pase": pase_neto,
        "yardas_carrera": carrera,
        "jugadas": jugadas,
        "yardas_jugada": (pase_neto + carrera) / jugadas if jugadas else 0.0,
        "epa": epa,
        "epa_jugada": epa / jugadas if jugadas else 0.0,
        "perdidas": _n(f, "passing_interceptions") + _n(f, "fumbles_lost_total"),
        "sacks_recibidos": _n(f, "sacks_suffered"),
        "sacks": _n(f, "def_sacks"),
        "primeros_downs": _n(f, "passing_first_downs") + _n(f, "rushing_first_downs"),
        "explosivas": _n(f, "passing_20") + _n(f, "rushing_20"),
        "penalizaciones": _n(f, "penalties"),
        "yardas_penalizacion": _n(f, "penalty_yards"),
        "fg_hechos": _n(f, "fg_made"),
        "fg_intentos": _n(f, "fg_att"),
        "intercepciones": _n(f, "def_interceptions"),
    }


# nombre -> (etiqueta, mayor es mejor para quien la consigue)
METRICAS = {
    "yardas": ("Yardas totales", True),
    "yardas_pase": ("Yardas de pase (netas)", True),
    "yardas_carrera": ("Yardas de carrera", True),
    "yardas_jugada": ("Yardas por jugada", True),
    "epa_jugada": ("EPA por jugada", True),
    "perdidas": ("Pérdidas de balón", False),
    "sacks_recibidos": ("Sacks recibidos", False),
    "sacks": ("Sacks conseguidos", True),
    "primeros_downs": ("Primeros downs", True),
    "explosivas": ("Jugadas de 20+ yardas", True),
    "penalizaciones": ("Penalizaciones", False),
    "yardas_penalizacion": ("Yardas de penalización", False),
}


POR_JUGADA = {"yardas_jugada": "yardas", "epa_jugada": "epa"}


def cargar(con, temporada=None, solo_regular=False):
    """Filas por equipo y partido, con abreviaturas normalizadas y métricas calculadas."""
    sql = "SELECT * FROM nfl_estadisticas_equipo"
    condiciones, params = [], []
    if temporada is not None:
        condiciones.append("season = ?")
        params.append(temporada)
    if solo_regular:
        condiciones.append("season_type = 'REG'")
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    filas = []
    for f in con.execute(sql, params):
        d = dict(f)
        filas.append({"id": d["game_id"], "temporada": d["season"], "semana": d["week"], "tipo": d["season_type"],
                      "equipo": normalizar(d["team"]), "rival": normalizar(d["opponent_team"]), **metricas_partido(d)})
    return filas


def emparejar(filas):
    """game_id -> {equipo: fila} para comparar a los dos equipos de cada partido."""
    partidos = defaultdict(dict)
    for f in filas:
        partidos[f["id"]][f["equipo"]] = f
    return partidos


class Resumen:
    """Medias por partido de un equipo: lo que produce (favor) y lo que concede (contra)."""

    def __init__(self, equipo):
        self.equipo = equipo
        self.favor = defaultdict(float)
        self.contra = defaultdict(float)
        self.partidos = 0

    def favor_pp(self, m):
        return self._media(self.favor, m)

    def contra_pp(self, m):
        return self._media(self.contra, m)

    def _media(self, acumulado, m):
        if m in POR_JUGADA:  # ratio sobre el total de jugadas, no media de ratios por partido
            return acumulado[POR_JUGADA[m]] / acumulado["jugadas"] if acumulado["jugadas"] else 0.0
        return acumulado[m] / self.partidos if self.partidos else 0.0

    @property
    def diferencial_perdidas(self):
        """Pérdidas provocadas al rival menos pérdidas propias (total)."""
        return self.contra["perdidas"] - self.favor["perdidas"]

    @property
    def fg_pct(self):
        return pct(self.favor["fg_hechos"], self.favor["fg_intentos"])


def por_equipo(filas):
    partidos = emparejar(filas)
    res = {}
    for f in filas:
        rival = partidos[f["id"]].get(f["rival"])
        if rival is None:
            continue
        r = res.setdefault(f["equipo"], Resumen(f["equipo"]))
        r.partidos += 1
        for clave, valor in f.items():
            if isinstance(valor, (int, float)) and clave not in ("temporada", "semana"):
                r.favor[clave] += valor
                r.contra[clave] += rival[clave]
    return res


def factores_victoria(filas, juegos):
    """Para cada métrica, % de partidos que gana el equipo que la domina (sin contar empates en la métrica)."""
    resultado = {j.id: j for j in juegos if j.jugado and j.id}
    conteo = {m: [0, 0] for m in METRICAS}
    for gid, equipos in emparejar(filas).items():
        j = resultado.get(gid)
        if j is None or len(equipos) != 2 or j.margen == 0:
            continue
        ganador = j.ganador
        a, b = equipos.values()
        for m, (_, mayor) in METRICAS.items():
            if a[m] == b[m]:
                continue
            mejor = a if (a[m] > b[m]) == mayor else b
            conteo[m][0] += mejor["equipo"] == ganador
            conteo[m][1] += 1
    return {m: (pct(g, n), n) for m, (g, n) in conteo.items() if n}
