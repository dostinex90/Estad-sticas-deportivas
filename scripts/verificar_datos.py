"""Comprueba la integridad de la base de datos y muestra la cobertura de cada liga.

Errores (terminan con código 1): partidos duplicados, un equipo jugando dos veces el mismo día,
resultados con fecha futura o marcadores imposibles. Avisos: temporadas incompletas y resultados
recientes que aún faltan. La usa la actualización diaria antes de publicar nada.

Uso: python3 scripts/verificar_datos.py
"""

import sqlite3
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo import base  # noqa: E402

PRINCIPALES = ["SP1", "E0", "I1", "D1", "F1", "P1", "N1"]


def verificar(con):
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731
    hoy = date.today().isoformat()
    errores, avisos = [], []

    # Ligas a doble vuelta: cada pareja local-visitante se juega una sola vez por temporada
    excluidas = tuple(base.CRUCES_REPETIDOS)
    marcas = ",".join("?" * len(excluidas))
    dup = q(f"SELECT competicion, temporada, local, visitante, COUNT(*) FROM futbol_partidos "
            f"WHERE competicion NOT IN ({marcas}) GROUP BY 1, 2, 3, 4 HAVING COUNT(*) > 1", *excluidas)
    if dup:
        errores.append(f"{len(dup)} cruces repetidos en la misma temporada, p. ej. {[tuple(d) for d in dup[:3]]}")
    dup = q("SELECT competicion, fecha, local, visitante, COUNT(*) FROM futbol_partidos GROUP BY 1, 2, 3, 4 HAVING COUNT(*) > 1")
    if dup:
        errores.append(f"{len(dup)} partidos duplicados (misma fecha y equipos), p. ej. {[tuple(d) for d in dup[:3]]}")
    doble = q("SELECT competicion, fecha, equipo, COUNT(*) FROM (SELECT competicion, fecha, local AS equipo FROM futbol_partidos "
              "UNION ALL SELECT competicion, fecha, visitante FROM futbol_partidos) GROUP BY 1, 2, 3 HAVING COUNT(*) > 1")
    if doble:
        por_liga = Counter(d[0] for d in doble)
        errores.append(f"{len(doble)} casos de un equipo con dos partidos el mismo día ({dict(por_liga)}), "
                       f"p. ej. {[tuple(d) for d in doble[:3]]}")
    futuro = q("SELECT COUNT(*) FROM futbol_partidos WHERE goles_local IS NOT NULL AND fecha > ?", hoy)[0][0]
    if futuro:
        errores.append(f"{futuro} partidos con resultado y fecha futura")
    imposibles = q("SELECT COUNT(*) FROM futbol_partidos WHERE goles_local < 0 OR goles_visitante < 0 "
                   "OR descanso_local > goles_local OR descanso_visitante > goles_visitante")[0][0]
    if imposibles:
        errores.append(f"{imposibles} marcadores imposibles")
    nfl_dup = q("SELECT COUNT(*) FROM (SELECT game_id FROM nfl_partidos GROUP BY 1 HAVING COUNT(*) > 1)")[0][0]
    if nfl_dup:
        errores.append(f"{nfl_dup} partidos de la NFL duplicados")
    try:
        nba_dup = q("SELECT COUNT(*) FROM (SELECT id FROM nba_partidos GROUP BY 1 HAVING COUNT(*) > 1)")[0][0]
        nba_doble = q("SELECT temporada, fecha, equipo, COUNT(*) FROM (SELECT temporada, fecha, local AS equipo FROM nba_partidos "
                      "UNION ALL SELECT temporada, fecha, visitante FROM nba_partidos) GROUP BY 2, 3 HAVING COUNT(*) > 1")
        # Las temporadas pasadas ya no cambian: sus fallos de la fuente (p. ej. un PHX-GS de 2019-20 con
        # fecha errónea) solo se avisan; en las dos últimas temporadas son un error
        ultima = q("SELECT MAX(temporada) FROM nba_partidos")[0][0]
        antiguos = [d for d in nba_doble if d[0] < ultima - 1]
        nba_doble = [d for d in nba_doble if d[0] >= ultima - 1]
        if antiguos:
            avisos.append(f"NBA: {len(antiguos)} casos antiguos de un equipo con dos partidos el mismo día en la fuente, "
                          f"p. ej. {[tuple(d[1:3]) for d in antiguos[:3]]}")
        nba_futuro = q("SELECT COUNT(*) FROM nba_partidos WHERE puntos_local IS NOT NULL AND fecha > ?", hoy)[0][0]
    except sqlite3.OperationalError:
        nba_dup, nba_doble, nba_futuro = 0, [], 0
        avisos.append("la base no tiene partidos de la NBA")
    if nba_dup:
        errores.append(f"{nba_dup} partidos de la NBA duplicados")
    if nba_doble:
        errores.append(f"{len(nba_doble)} casos de un equipo NBA con dos partidos el mismo día, p. ej. {[tuple(d[1:3]) for d in nba_doble[:3]]}")
    if nba_futuro:
        errores.append(f"{nba_futuro} partidos de la NBA con resultado y fecha futura")

    # Cobertura de las ligas principales
    print(f"{'Liga':<6}{'Temporadas':>11}{'Partidos':>10}{'Incompletas':>13}  Último resultado  Pendientes ya jugados")
    hace3 = (date.today() - timedelta(days=3)).isoformat()
    for codigo in PRINCIPALES:
        temporadas = [t for (t,) in q("SELECT DISTINCT temporada FROM futbol_partidos WHERE competicion = ? ORDER BY 1", codigo)]
        incompletas = []
        for t in temporadas[:-1]:  # la temporada en curso aún no está completa
            cuenta = Counter()
            for l, v in q("SELECT local, visitante FROM futbol_partidos WHERE competicion = ? AND temporada = ? "
                          "AND goles_local IS NOT NULL", codigo, t):
                cuenta[l] += 1
                cuenta[v] += 1
            if len(set(cuenta.values())) != 1 or min(cuenta.values()) < 2 * (len(cuenta) - 1):
                incompletas.append(t)
        total = q("SELECT COUNT(*) FROM futbol_partidos WHERE competicion = ?", codigo)[0][0]
        ultimo = q("SELECT MAX(fecha) FROM futbol_partidos WHERE competicion = ? AND goles_local IS NOT NULL", codigo)[0][0]
        atrasados = q("SELECT COUNT(*) FROM futbol_partidos WHERE competicion = ? AND goles_local IS NULL AND fecha < ?",
                      codigo, hace3)[0][0]
        print(f"{codigo:<6}{len(temporadas):>11}{total:>10,}{len(incompletas):>13}  {ultimo:<17} {atrasados}")
        if incompletas:
            avisos.append(f"{codigo}: temporadas incompletas en las fuentes: {', '.join(incompletas)}")
        if atrasados:
            avisos.append(f"{codigo}: {atrasados} partidos de hace más de 3 días aún sin resultado en las fuentes")
    nfl = q("SELECT MAX(gameday), SUM(home_score IS NULL AND gameday < ?) FROM nfl_partidos WHERE home_score IS NOT NULL "
            "OR gameday < ?", hace3, hace3)[0]
    print(f"NFL: último resultado {nfl[0]}, {nfl[1] or 0} partidos de hace más de 3 días sin resultado")
    try:
        nba = q("SELECT MAX(CASE WHEN puntos_local IS NOT NULL THEN fecha END), SUM(puntos_local IS NULL AND fecha < ?) "
                "FROM nba_partidos", hace3)[0]
        print(f"NBA: último resultado {nba[0]}, {nba[1] or 0} partidos de hace más de 3 días sin resultado")
        if nba[1]:
            avisos.append(f"NBA: {nba[1]} partidos de hace más de 3 días aún sin resultado en las fuentes")
        incompletas = q("SELECT temporada, COUNT(*) FROM nba_partidos WHERE tipo = 'REG' AND puntos_local IS NOT NULL "
                        "AND temporada < (SELECT MAX(temporada) FROM nba_partidos WHERE puntos_local IS NOT NULL) "
                        "GROUP BY 1 HAVING COUNT(*) NOT IN (1189, 1230) ORDER BY 1")
        if incompletas:
            avisos.append("NBA: temporadas regulares con un número de partidos distinto del habitual (cierres patronales, "
                          f"pandemia): {', '.join(f'{t - 1}-{str(t)[2:]} ({n})' for t, n in incompletas)}")
    except sqlite3.OperationalError:
        pass

    for a in avisos:
        print(f"AVISO: {a}")
    for e in errores:
        print(f"ERROR: {e}")
    print("Datos correctos." if not errores else f"{len(errores)} errores de integridad.")
    return not errores


if __name__ == "__main__":
    conexion = base.conectar()
    sys.exit(0 if verificar(conexion) else 1)
