"""Estadísticas de juego de la NBA por equipo (tabla nba_estadisticas_equipo de la base).

Incluye los "cuatro factores" de Dean Oliver (acierto efectivo, pérdidas, rebote ofensivo y
tiros libres), el ritmo y la eficiencia ofensiva y defensiva por 100 posesiones.
"""

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field

from ..comun import pct

CAMPOS = ["puntos", "tiros_campo", "intentos_campo", "triples", "intentos_triple", "tiros_libres", "intentos_libres",
          "rebotes_ofensivos", "rebotes_defensivos", "asistencias", "robos", "tapones", "perdidas", "faltas",
          "puntos_pintura", "puntos_contraataque"]

# métrica -> (etiqueta, True si más es mejor para quien la consigue)
METRICAS = {
    "eficiencia": ("Puntos por 100 posesiones", True),
    "ritmo": ("Posesiones por partido", True),
    "efg": ("% tiro efectivo (eFG%)", True),
    "pct_perdidas": ("% posesiones con pérdida", False),
    "pct_rebote_of": ("% rebote ofensivo", True),
    "tasa_libres": ("Tiros libres por tiro de campo", True),
    "pct_triple": ("% de triples", True),
    "tasa_triples": ("% de tiros que son triples", True),
    "asistencias": ("Asistencias por partido", True),
    "robos": ("Robos por partido", True),
    "tapones": ("Tapones por partido", True),
    "puntos_pintura": ("Puntos en la pintura", True),
}


def cargar(con, temporada, solo_regular=True):
    """[(id, equipo, {campo: valor} propio, {campo: valor} del rival)] de la temporada."""
    tipos = ("REG", "COPA") if solo_regular else ("REG", "COPA", "PLAYIN", "PO")
    try:
        filas = con.execute(f"SELECT * FROM nba_estadisticas_equipo WHERE temporada = ? AND tipo IN ({','.join('?' * len(tipos))})",
                            (temporada, *tipos)).fetchall()
    except sqlite3.OperationalError:  # base sin tabla de la NBA
        return []
    por_partido = defaultdict(dict)
    for f in filas:
        if f["intentos_campo"]:
            por_partido[f["id"]][f["equipo"]] = {c: f[c] or 0 for c in CAMPOS}
    res = []
    for pid, eqs in por_partido.items():
        if len(eqs) == 2:
            (a, da), (b, db) = eqs.items()
            res += [(pid, a, da, db), (pid, b, db, da)]
    return res


def posesiones(d):
    return d["intentos_campo"] - d["rebotes_ofensivos"] + d["perdidas"] + 0.44 * d["intentos_libres"]


@dataclass
class Resumen:
    equipo: str
    partidos: int = 0
    favor: dict = field(default_factory=lambda: defaultdict(float))
    contra: dict = field(default_factory=lambda: defaultdict(float))

    def _valor(self, propio, rival, metrica):
        pos = (posesiones(propio) + posesiones(rival)) / 2
        if metrica == "eficiencia":
            return 100 * propio["puntos"] / pos if pos else 0.0
        if metrica == "ritmo":
            return pos / self.partidos if self.partidos else 0.0
        if metrica == "efg":
            return pct(propio["tiros_campo"] + 0.5 * propio["triples"], propio["intentos_campo"])
        if metrica == "pct_perdidas":
            return pct(propio["perdidas"], pos)
        if metrica == "pct_rebote_of":
            return pct(propio["rebotes_ofensivos"], propio["rebotes_ofensivos"] + rival["rebotes_defensivos"])
        if metrica == "tasa_libres":
            return propio["tiros_libres"] / propio["intentos_campo"] if propio["intentos_campo"] else 0.0
        if metrica == "pct_triple":
            return pct(propio["triples"], propio["intentos_triple"])
        if metrica == "tasa_triples":
            return pct(propio["intentos_triple"], propio["intentos_campo"])
        return propio[metrica] / self.partidos if self.partidos else 0.0

    def favor_de(self, metrica):
        return self._valor(self.favor, self.contra, metrica)

    def contra_de(self, metrica):
        """Lo que consigue el rival (defensa)."""
        return self._valor(self.contra, self.favor, metrica)

    @property
    def neto(self):
        return self.favor_de("eficiencia") - self.contra_de("eficiencia")


def por_equipo(filas):
    res = {}
    for _, equipo, propio, rival in filas:
        r = res.setdefault(equipo, Resumen(equipo))
        r.partidos += 1
        for c in CAMPOS:
            r.favor[c] += propio[c]
            r.contra[c] += rival[c]
    return res


def factores_victoria(filas):
    """{métrica: (% de partidos que gana quien es mejor en ella, partidos)} con los cuatro factores."""
    cuenta = defaultdict(lambda: [0, 0])
    vistos = set()
    for pid, equipo, propio, rival in filas:
        if pid in vistos or propio["puntos"] == rival["puntos"]:
            continue
        vistos.add(pid)
        gana = propio["puntos"] > rival["puntos"]
        uno = Resumen(equipo, 1, propio, rival)
        for m in ("efg", "pct_perdidas", "pct_rebote_of", "tasa_libres", "pct_triple", "asistencias"):
            a, b = uno.favor_de(m), uno.contra_de(m)
            if a == b:
                continue
            mejor_propio = (a > b) == METRICAS[m][1]
            cuenta[m][0] += mejor_propio == gana
            cuenta[m][1] += 1
    return {m: (pct(g, n), n) for m, (g, n) in cuenta.items() if n}
