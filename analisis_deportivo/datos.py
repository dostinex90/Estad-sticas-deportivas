"""Carga y validación de resultados de partidos desde CSV."""

import csv
from dataclasses import dataclass
from datetime import date

COLUMNAS = ("fecha", "local", "visitante", "goles_local", "goles_visitante")


@dataclass(frozen=True)
class Partido:
    fecha: date
    local: str
    visitante: str
    goles_local: int
    goles_visitante: int

    @property
    def ganador(self):
        """Nombre del equipo ganador, o None si fue empate."""
        if self.goles_local > self.goles_visitante:
            return self.local
        if self.goles_visitante > self.goles_local:
            return self.visitante
        return None

    def participa(self, equipo):
        return equipo in (self.local, self.visitante)


def cargar_partidos(ruta):
    """Lee un CSV con las columnas de COLUMNAS y devuelve los partidos ordenados por fecha."""
    with open(ruta, newline="", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        faltan = set(COLUMNAS) - set(lector.fieldnames or [])
        if faltan:
            raise ValueError(f"Faltan columnas en {ruta}: {', '.join(sorted(faltan))}")

        partidos = []
        for num, fila in enumerate(lector, start=2):
            try:
                partidos.append(
                    Partido(
                        fecha=date.fromisoformat(fila["fecha"].strip()),
                        local=fila["local"].strip(),
                        visitante=fila["visitante"].strip(),
                        goles_local=int(fila["goles_local"]),
                        goles_visitante=int(fila["goles_visitante"]),
                    )
                )
            except (ValueError, TypeError) as e:
                raise ValueError(f"Fila {num} inválida en {ruta}: {e}") from e

    return sorted(partidos, key=lambda p: p.fecha)


def equipos(partidos):
    return sorted({p.local for p in partidos} | {p.visitante for p in partidos})
