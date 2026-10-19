"""Carga de partidos de la NBA desde la base de datos (tabla nba_partidos).

Las temporadas se guardan con el año en que terminan, como hace ESPN: 2026 es la 2025-26.
Los partidos sin marcador se conservan como pendientes.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

NOMBRE_TIPO = {"REG": "Temporada regular", "COPA": "Final de la NBA Cup", "PLAYIN": "Play-in", "PO": "Playoffs"}


@dataclass(frozen=True)
class Partido:
    temporada: int
    fecha: date
    local: str
    visitante: str
    puntos_local: Optional[int] = None
    puntos_visitante: Optional[int] = None
    tipo: str = "REG"
    ronda: str = ""
    prorrogas: int = 0
    neutral: bool = False
    estadio: str = ""
    id: str = ""

    @property
    def jugado(self):
        return self.puntos_local is not None and self.puntos_visitante is not None

    @property
    def margen(self):
        """Puntos del local menos puntos del visitante."""
        return self.puntos_local - self.puntos_visitante

    @property
    def total(self):
        return self.puntos_local + self.puntos_visitante

    @property
    def ganador(self):
        return self.local if self.margen > 0 else self.visitante

    @property
    def es_playoff(self):
        return self.tipo == "PO"

    def participa(self, equipo):
        return equipo in (self.local, self.visitante)

    def marcador(self):
        if not self.jugado:
            return f"{self.visitante} @ {self.local}"
        extra = f" ({self.prorrogas}pró.)" if self.prorrogas > 1 else " (pró.)" if self.prorrogas else ""
        return f"{self.visitante} {self.puntos_visitante} @ {self.local} {self.puntos_local}{extra}"


def texto_temporada(t):
    """2026 -> "2025-26"."""
    return f"{t - 1}-{str(t)[2:]}"


def leer_temporada(texto):
    """Acepta "2025-26", "2025-2026" o el año en que termina ("2026")."""
    texto = str(texto).strip()
    if "-" in texto:
        return int(texto.split("-")[0]) + 1
    return int(texto)


def cargar_desde_base(con):
    """Todos los partidos (jugados y pendientes) ordenados por fecha."""
    partidos = [Partido(temporada=f["temporada"], fecha=date.fromisoformat(f["fecha"]), local=f["local"],
                        visitante=f["visitante"], puntos_local=f["puntos_local"], puntos_visitante=f["puntos_visitante"],
                        tipo=f["tipo"], ronda=f["ronda"] or "", prorrogas=f["prorrogas"] or 0, neutral=bool(f["neutral"]),
                        estadio=f["estadio"] or "", id=f["id"])
                for f in con.execute("SELECT * FROM nba_partidos")]
    return sorted(partidos, key=lambda p: (p.fecha, p.id))


def jugados(partidos):
    return [p for p in partidos if p.jugado]


def temporadas(partidos):
    return sorted({p.temporada for p in partidos})


def equipos(partidos):
    return sorted({p.local for p in partidos} | {p.visitante for p in partidos})


def descansos(partidos):
    """{(id, equipo): días desde su partido anterior} usando el calendario (se conoce antes del partido)."""
    ultimo, res = {}, {}
    for p in sorted(partidos, key=lambda p: p.fecha):
        for e in (p.local, p.visitante):
            if e in ultimo:
                res[(p.id, e)] = (p.fecha - ultimo[e]).days
            ultimo[e] = p.fecha
    return res
