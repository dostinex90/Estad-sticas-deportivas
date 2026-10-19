"""Ajuste de la NFL por jugadores de baja (tablas nfl_lesiones y nfl_snaps de la base).

El parte de lesionados oficial de cada semana se publica antes del partido y dice qué jugadores
no jugarán (Out), probablemente no jugarán (Doubtful) o están en duda (Questionable). Para saber
cuánto pesa cada baja se usa el porcentaje de jugadas (snaps) que ese jugador jugó en sus últimas
4 apariciones del último año, siempre de partidos anteriores. Cada grupo de posiciones tiene un
peso en puntos por titular de baja (un titular juega ~100 % de las jugadas), ajustado con
2013-2019 y validado en 2020-2025 (ver experimentos/nfl_lesiones.py). Los QB no cuentan aquí:
de ellos se encarga el ajuste por QB titular de modelos.py. La línea defensiva y los tight ends
no mejoraban la predicción y no tienen peso.
"""

import re
import sqlite3
from collections import defaultdict, deque

GRUPOS = {
    "OL": {"T", "G", "C", "OT", "OG", "OL"},
    "WR": {"WR"}, "TE": {"TE"}, "RB": {"RB", "FB", "HB"},
    "DL": {"DE", "DT", "NT", "DL"}, "LB": {"LB", "OLB", "ILB", "MLB"},
    "DB": {"CB", "S", "FS", "SS", "DB", "SAF"},
}
OFENSIVOS = {"OL", "WR", "TE", "RB"}
NOMBRE_GRUPO = {"OL": "línea ofensiva", "WR": "receptores", "TE": "tight ends", "RB": "corredores",
                "DL": "línea defensiva", "LB": "linebackers", "DB": "secundaria"}
PESOS = {"OL": -0.26, "WR": -0.88, "RB": -0.82, "LB": -0.72, "DB": -0.43}  # puntos por titular de baja
PESO_DUDA = -0.07  # Questionable (de cualquier posición con peso): casi siempre acaban jugando
ESTADOS = ("Out", "Doubtful", "Questionable")
APARICIONES = 4
VIGENCIA_DIAS = 365


def grupo(posicion):
    return next((g for g, p in GRUPOS.items() if posicion in p), None)


def clave_nombre(nombre):
    """Nombre comparable entre el parte de lesionados y los snaps ("D.J. Moore Jr." -> "dj moore")."""
    n = re.sub(r"[.'’\-]", "", (nombre or "").lower())
    n = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", n)
    return " ".join(n.split())


def puntos(baja):
    """Puntos que resta al equipo una baja (nombre, posición, estado, % de snaps habitual)."""
    _, posicion, estado, habitual = baja
    g = grupo(posicion)
    if g not in PESOS:
        return 0.0
    return habitual * (PESO_DUDA if estado == "Questionable" else PESOS[g])


def ajuste(bajas):
    """Puntos que pierde (negativo) un equipo por todas sus bajas."""
    return sum(puntos(b) for b in bajas or ())


def bajas_por_partido(con, juegos):
    """{(id del partido, equipo): ((nombre, posición, estado, % habitual), ...)} con el parte de
    lesionados de la semana y los snaps de partidos anteriores. {} si la base no tiene estas tablas."""
    try:
        snaps = con.execute("SELECT game_id, player, position, offense_pct, defense_pct FROM nfl_snaps").fetchall()
        lesiones = con.execute("SELECT season, week, team, full_name, position, report_status FROM nfl_lesiones").fetchall()
    except sqlite3.OperationalError:
        return {}
    from .equipos import normalizar

    por_semana = {}
    for j in juegos:
        for eq in (j.local, j.visitante):
            por_semana[(j.temporada, j.semana, eq)] = j
    del_partido = defaultdict(list)
    for gid, jugador, posicion, of, de in snaps:
        g = grupo(posicion)
        if g:
            del_partido[gid].append((clave_nombre(jugador), (of if g in OFENSIVOS else de) or 0.0))
    partes = defaultdict(list)
    for temporada, semana, equipo, nombre, posicion, estado in lesiones:
        eq = normalizar(equipo)
        j = por_semana.get((temporada, semana, eq))
        if j and estado in ESTADOS and grupo(posicion):
            partes[j.id].append((eq, nombre, posicion, estado))
    historial = defaultdict(lambda: deque(maxlen=APARICIONES))  # jugador -> [(fecha, % snaps)]
    res = {}
    # por fecha: primero se calculan las bajas de todos los partidos del día y después se añaden sus snaps
    por_fecha = defaultdict(list)
    for j in juegos:
        por_fecha[j.fecha].append(j)
    for fecha, del_dia in sorted(por_fecha.items()):
        for j in del_dia:
            for eq, nombre, posicion, estado in partes.get(j.id, ()):
                h = [p for f, p in historial.get(clave_nombre(nombre), ()) if (fecha - f).days <= VIGENCIA_DIAS]
                if h:
                    res.setdefault((j.id, eq), []).append((nombre, posicion, estado, sum(h) / len(h)))
        for j in del_dia:
            for clave, pct in del_partido.get(j.id, ()):
                historial[clave].append((fecha, pct))
    return {k: tuple(sorted(v, key=lambda b: puntos(b))) for k, v in res.items()}
