"""Carga de partidos de fútbol desde varios formatos.

Formatos admitidos (se detectan automáticamente):
  * CSV propio en español: fecha,local,visitante,goles_local,goles_visitante y,
    opcionalmente, columnas de estadísticas (ver ESTADISTICAS) con sufijo _local/_visitante.
  * CSV de football-data.co.uk (Date, HomeTeam, AwayTeam, FTHG, FTAG, HS, HST, HC...).
  * JSON de openfootball (football.json).
Los partidos sin marcador se conservan como pendientes (útiles para pronósticos).
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from ..comun import entero_opcional, leer_csv, real_opcional

# Estadística -> (columna local, columna visitante) en football-data.co.uk
ESTADISTICAS = {
    "tiros": ("HS", "AS"),
    "tiros_puerta": ("HST", "AST"),
    "corners": ("HC", "AC"),
    "faltas": ("HF", "AF"),
    "amarillas": ("HY", "AY"),
    "rojas": ("HR", "AR"),
}

# Cuotas 1X2 en orden de preferencia (media del mercado primero)
CUOTAS_FD = [("AvgH", "AvgD", "AvgA"), ("BbAvH", "BbAvD", "BbAvA"), ("B365H", "B365D", "B365A"), ("PSH", "PSD", "PSA")]


@dataclass(frozen=True)
class Partido:
    fecha: date
    local: str
    visitante: str
    goles_local: Optional[int] = None
    goles_visitante: Optional[int] = None
    descanso_local: Optional[int] = None
    descanso_visitante: Optional[int] = None
    estadisticas: dict = field(default_factory=dict, compare=False, hash=False)  # nombre -> (local, visitante)
    cuotas: Optional[tuple] = None  # (1, X, 2) decimales
    jornada: str = ""
    competicion: str = ""

    @property
    def jugado(self):
        return self.goles_local is not None and self.goles_visitante is not None

    @property
    def tiene_descanso(self):
        return self.descanso_local is not None and self.descanso_visitante is not None

    @property
    def ganador(self):
        if self.goles_local > self.goles_visitante:
            return self.local
        if self.goles_visitante > self.goles_local:
            return self.visitante
        return None

    @property
    def resultado_1x2(self):
        if self.goles_local > self.goles_visitante:
            return "1"
        if self.goles_local < self.goles_visitante:
            return "2"
        return "X"

    @property
    def total_goles(self):
        return self.goles_local + self.goles_visitante

    def participa(self, equipo):
        return equipo in (self.local, self.visitante)

    def rival(self, equipo):
        return self.visitante if equipo == self.local else self.local

    def marcador(self):
        if not self.jugado:
            return f"{self.local} vs {self.visitante}"
        return f"{self.local} {self.goles_local}-{self.goles_visitante} {self.visitante}"


def _fecha(texto):
    texto = texto.strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            pass
    raise ValueError(f"fecha no reconocida: {texto!r}")


def _desde_football_data(filas):
    partidos = []
    for num, f in enumerate(filas, start=2):
        if not (f.get("HomeTeam") or "").strip():
            continue
        try:
            stats = {}
            for nombre, (cl, cv) in ESTADISTICAS.items():
                vl, vv = entero_opcional(f.get(cl)), entero_opcional(f.get(cv))
                if vl is not None and vv is not None:
                    stats[nombre] = (vl, vv)
            cuotas = None
            for c1, cx, c2 in CUOTAS_FD:
                trio = tuple(real_opcional(f.get(c)) for c in (c1, cx, c2))
                if all(trio):
                    cuotas = trio
                    break
            partidos.append(
                Partido(
                    fecha=_fecha(f["Date"]),
                    local=f["HomeTeam"].strip(),
                    visitante=f["AwayTeam"].strip(),
                    goles_local=entero_opcional(f.get("FTHG")),
                    goles_visitante=entero_opcional(f.get("FTAG")),
                    descanso_local=entero_opcional(f.get("HTHG")),
                    descanso_visitante=entero_opcional(f.get("HTAG")),
                    estadisticas=stats,
                    cuotas=cuotas,
                    competicion=(f.get("Div") or "").strip(),
                )
            )
        except (ValueError, KeyError) as e:
            raise ValueError(f"Fila {num} inválida: {e}") from e
    return partidos


def _desde_propio(filas, cabecera):
    faltan = {"fecha", "local", "visitante", "goles_local", "goles_visitante"} - set(cabecera)
    if faltan:
        raise ValueError(f"Faltan columnas: {', '.join(sorted(faltan))}")
    partidos = []
    for num, f in enumerate(filas, start=2):
        try:
            stats = {}
            for nombre in ESTADISTICAS:
                vl = entero_opcional(f.get(f"{nombre}_local"))
                vv = entero_opcional(f.get(f"{nombre}_visitante"))
                if vl is not None and vv is not None:
                    stats[nombre] = (vl, vv)
            trio = tuple(real_opcional(f.get(c)) for c in ("cuota_local", "cuota_empate", "cuota_visitante"))
            partidos.append(
                Partido(
                    fecha=_fecha(f["fecha"]),
                    local=f["local"].strip(),
                    visitante=f["visitante"].strip(),
                    goles_local=entero_opcional(f["goles_local"]),
                    goles_visitante=entero_opcional(f["goles_visitante"]),
                    descanso_local=entero_opcional(f.get("descanso_local")),
                    descanso_visitante=entero_opcional(f.get("descanso_visitante")),
                    estadisticas=stats,
                    cuotas=trio if all(trio) else None,
                    jornada=(f.get("jornada") or "").strip(),
                    competicion=(f.get("competicion") or "").strip(),
                )
            )
        except (ValueError, TypeError, AttributeError) as e:
            raise ValueError(f"Fila {num} inválida: {e}") from e
    return partidos


def _desde_openfootball(datos):
    partidos = []
    for m in datos.get("matches", []):
        marcador = m.get("score") or {}
        if isinstance(marcador, list):  # algunos archivos guardan solo el resultado final como lista
            marcador = {"ft": marcador}
        ft, ht = marcador.get("ft"), marcador.get("ht")
        partidos.append(
            Partido(
                fecha=_fecha(m["date"]),
                local=m["team1"],
                visitante=m["team2"],
                goles_local=ft[0] if ft else None,
                goles_visitante=ft[1] if ft else None,
                descanso_local=ht[0] if ht else None,
                descanso_visitante=ht[1] if ht else None,
                jornada=str(m.get("round", "")),
                competicion=datos.get("name", ""),
            )
        )
    return partidos


def cargar_partidos(ruta):
    """Carga todos los partidos (jugados y pendientes) ordenados por fecha."""
    ruta = str(ruta)
    try:
        if ruta.lower().endswith(".json"):
            with open(ruta, encoding="utf-8") as f:
                partidos = _desde_openfootball(json.load(f))
        else:
            cabecera, filas = leer_csv(ruta)
            if "HomeTeam" in cabecera:
                partidos = _desde_football_data(filas)
            else:
                partidos = _desde_propio(filas, cabecera)
    except ValueError as e:
        raise ValueError(f"{ruta}: {e}") from e
    return sorted(partidos, key=lambda p: p.fecha)


def jugados(partidos):
    return [p for p in partidos if p.jugado]


def pendientes(partidos):
    return [p for p in partidos if not p.jugado]


def equipos(partidos):
    return sorted({p.local for p in partidos} | {p.visitante for p in partidos})
