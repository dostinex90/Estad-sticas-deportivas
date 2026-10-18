"""Carga de partidos de la NFL.

Formatos admitidos (detección automática):
  * games.csv de nflverse (game_id, season, week, home_team, away_score, spread_line...).
  * CSV propio en español: temporada,semana,fecha,local,visitante,puntos_local,puntos_visitante
    y opcionalmente tipo, neutral, linea (puntos de ventaja del local según el mercado),
    total_linea, prorroga.
Los partidos sin marcador se conservan como pendientes.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..comun import entero_opcional, leer_csv, real_opcional
from .equipos import conferencia, division, normalizar

PLAYOFFS = {"WC", "DIV", "CON", "SB"}
NOMBRE_TIPO = {"REG": "Temporada regular", "WC": "Wild Card", "DIV": "Divisional", "CON": "Campeonato de conferencia", "SB": "Super Bowl"}


@dataclass(frozen=True)
class Juego:
    temporada: int
    semana: int
    fecha: date
    local: str
    visitante: str
    puntos_local: Optional[int] = None
    puntos_visitante: Optional[int] = None
    tipo: str = "REG"
    neutral: bool = False
    prorroga: bool = False
    linea: Optional[float] = None  # ventaja esperada del local según el mercado (positivo = local favorito)
    total_linea: Optional[float] = None
    descanso_local: Optional[int] = None
    descanso_visitante: Optional[int] = None
    techo: str = ""
    superficie: str = ""
    temperatura: Optional[float] = None
    viento: Optional[float] = None
    qb_local: str = ""
    qb_visitante: str = ""
    entrenador_local: str = ""
    entrenador_visitante: str = ""
    estadio: str = ""

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
        if self.margen > 0:
            return self.local
        if self.margen < 0:
            return self.visitante
        return None

    @property
    def es_playoff(self):
        return self.tipo in PLAYOFFS

    @property
    def divisional(self):
        return division(self.local) is not None and division(self.local) == division(self.visitante)

    @property
    def misma_conferencia(self):
        return conferencia(self.local) is not None and conferencia(self.local) == conferencia(self.visitante)

    @property
    def bajo_techo(self):
        return self.techo in ("dome", "closed")

    def participa(self, equipo):
        return equipo in (self.local, self.visitante)

    def marcador(self):
        if not self.jugado:
            return f"{self.visitante} @ {self.local}"
        extra = " (pró.)" if self.prorroga else ""
        return f"{self.visitante} {self.puntos_visitante} @ {self.local} {self.puntos_local}{extra}"


def _desde_nflverse(filas):
    juegos = []
    for num, f in enumerate(filas, start=2):
        try:
            juegos.append(
                Juego(
                    temporada=int(f["season"]),
                    semana=int(f["week"]),
                    fecha=date.fromisoformat(f["gameday"]),
                    local=normalizar(f["home_team"]),
                    visitante=normalizar(f["away_team"]),
                    puntos_local=entero_opcional(f.get("home_score")),
                    puntos_visitante=entero_opcional(f.get("away_score")),
                    tipo=(f.get("game_type") or "REG").strip(),
                    neutral=(f.get("location") or "").strip() == "Neutral",
                    prorroga=(f.get("overtime") or "0").strip() == "1",
                    linea=real_opcional(f.get("spread_line")),
                    total_linea=real_opcional(f.get("total_line")),
                    descanso_local=entero_opcional(f.get("home_rest")),
                    descanso_visitante=entero_opcional(f.get("away_rest")),
                    techo=(f.get("roof") or "").strip(),
                    superficie=(f.get("surface") or "").strip(),
                    temperatura=real_opcional(f.get("temp")),
                    viento=real_opcional(f.get("wind")),
                    qb_local=(f.get("home_qb_name") or "").strip(),
                    qb_visitante=(f.get("away_qb_name") or "").strip(),
                    entrenador_local=(f.get("home_coach") or "").strip(),
                    entrenador_visitante=(f.get("away_coach") or "").strip(),
                    estadio=(f.get("stadium") or "").strip(),
                )
            )
        except (ValueError, KeyError) as e:
            raise ValueError(f"Fila {num} inválida: {e}") from e
    return juegos


def _desde_propio(filas, cabecera):
    faltan = {"temporada", "semana", "fecha", "local", "visitante", "puntos_local", "puntos_visitante"} - set(cabecera)
    if faltan:
        raise ValueError(f"Faltan columnas: {', '.join(sorted(faltan))}")
    si = ("1", "si", "sí", "true", "x")
    juegos = []
    for num, f in enumerate(filas, start=2):
        try:
            juegos.append(
                Juego(
                    temporada=int(f["temporada"]),
                    semana=int(f["semana"]),
                    fecha=date.fromisoformat(f["fecha"].strip()),
                    local=normalizar(f["local"]),
                    visitante=normalizar(f["visitante"]),
                    puntos_local=entero_opcional(f["puntos_local"]),
                    puntos_visitante=entero_opcional(f["puntos_visitante"]),
                    tipo=(f.get("tipo") or "REG").strip().upper(),
                    neutral=(f.get("neutral") or "").strip().lower() in si,
                    prorroga=(f.get("prorroga") or "").strip().lower() in si,
                    linea=real_opcional(f.get("linea")),
                    total_linea=real_opcional(f.get("total_linea")),
                    techo=(f.get("techo") or "").strip(),
                    temperatura=real_opcional(f.get("temperatura")),
                    qb_local=(f.get("qb_local") or "").strip(),
                    qb_visitante=(f.get("qb_visitante") or "").strip(),
                )
            )
        except (ValueError, KeyError, AttributeError) as e:
            raise ValueError(f"Fila {num} inválida: {e}") from e
    return juegos


def cargar_juegos(ruta):
    """Carga todos los partidos (jugados y pendientes) ordenados por fecha."""
    try:
        cabecera, filas = leer_csv(ruta)
        if "home_team" in cabecera:
            juegos = _desde_nflverse(filas)
        else:
            juegos = _desde_propio(filas, cabecera)
    except ValueError as e:
        raise ValueError(f"{ruta}: {e}") from e
    return sorted(juegos, key=lambda j: (j.fecha, j.local))


def jugados(juegos):
    return [j for j in juegos if j.jugado]


def temporadas(juegos):
    return sorted({j.temporada for j in juegos})


def equipos(juegos):
    return sorted({j.local for j in juegos} | {j.visitante for j in juegos})
