"""Comprueba la integridad de la base de datos y muestra la cobertura de cada liga.

Errores (terminan con código 1): partidos duplicados, un equipo jugando dos veces el mismo día,
fechas con el día y el mes intercambiados, resultados con fecha futura o marcadores imposibles.
Avisos: temporadas incompletas y resultados recientes que aún faltan. La usa la actualización diaria antes de publicar nada.

Uso: python3 scripts/verificar_datos.py
"""

import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo import base  # noqa: E402

PRINCIPALES = ["SP1", "E0", "I1", "D1", "F1", "P1", "N1"]


# Partidos de la fase regular de la NFL por temporada (la de 2022 tuvo 271: se canceló el Bills-Bengals)
NFL_REGULAR = {2020: 256, 2022: 271}
NFL_PRIMERA = 2020  # los datos de jugadores (bajas, snaps) y la comprobación de cobertura empiezan aquí


def cobertura(con, hoy=None):
    """Compara la base con el calendario oficial y comprueba que las tablas de equipo y de jugadores
    cubren los partidos jugados desde 2020. Devuelve (errores, avisos).

    Error: faltan o sobran partidos en una temporada ya terminada de la NFL (256/272/271 de fase regular) o de la NBA
    (1230 desde 2021-22), o un partido de las dos últimas temporadas sin estadísticas de equipo o sin datos de jugadores
    (la web y los modelos los usan). Aviso: huecos antiguos de la fuente y datos de la última semana que aún no llegan."""
    hoy = hoy or date.today()
    reciente = (hoy - timedelta(days=4)).isoformat()
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731
    errores, avisos = [], []

    def existe(tabla):
        return bool(q("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", tabla))

    # --- NFL ---
    if existe("nfl_partidos"):
        actual = q("SELECT MAX(season) FROM nfl_partidos WHERE home_score IS NOT NULL")[0][0]
        for temporada, n, jugados in q("SELECT season, COUNT(*), SUM(home_score IS NOT NULL) FROM nfl_partidos "
                                       "WHERE game_type = 'REG' AND season >= ? GROUP BY 1 ORDER BY 1", NFL_PRIMERA):
            esperado = NFL_REGULAR.get(temporada, 272)
            if n != esperado:
                (errores if temporada < actual or jugados == n else avisos).append(
                    f"NFL {temporada}: {n} partidos de fase regular en el calendario y se esperaban {esperado}")
        jugados = q("SELECT game_id, season FROM nfl_partidos WHERE home_score IS NOT NULL AND season >= ? AND gameday < ?",
                    NFL_PRIMERA, reciente)
        if existe("nfl_estadisticas_equipo"):
            equipos = Counter(g for (g,) in q("SELECT game_id FROM nfl_estadisticas_equipo"))
            sin = Counter(t for g, t in jugados if equipos[g] != 2)
            if sin:
                errores.append(f"NFL: partidos jugados sin estadísticas de los dos equipos {dict(sorted(sin.items()))}")
        if existe("nfl_snaps"):
            con_snaps = {g for (g,) in q("SELECT DISTINCT game_id FROM nfl_snaps")}
            sin = Counter(t for g, t in jugados if g not in con_snaps)
            if sin:
                avisos.append(f"NFL: partidos jugados sin snaps por jugador {dict(sorted(sin.items()))} "
                              "(el ajuste por bajas los trata como sin datos)")
            fuera = len(con_snaps - {g for (g,) in q("SELECT game_id FROM nfl_partidos")})
            if fuera:
                errores.append(f"NFL: {fuera} partidos de nfl_snaps que no están en nfl_partidos")
        if existe("nfl_lesiones"):
            # semanas con partidos jugados y ninguna baja en el parte (hueco de la fuente, p. ej. la postemporada de 2023)
            con_parte = {tuple(r) for r in q("SELECT DISTINCT season, week FROM nfl_lesiones")}
            vacias = sorted({tuple(r) for r in q("SELECT season, week FROM nfl_partidos WHERE home_score IS NOT NULL "
                                                 "AND season >= ? AND gameday < ?", NFL_PRIMERA, reciente)} - con_parte)
            if vacias:
                por = defaultdict(list)
                for t, w in vacias:
                    por[t].append(w)
                avisos.append("NFL: semanas con partidos y sin ningún parte de lesionados en la fuente: "
                              + "; ".join(f"{t} semanas {', '.join(map(str, w))}" for t, w in por.items()))
            equipos_nfl = {t for (t,) in q("SELECT home_team FROM nfl_partidos UNION SELECT away_team FROM nfl_partidos")}
            otros = [t for (t,) in q("SELECT DISTINCT team FROM nfl_lesiones") if t not in equipos_nfl]
            if otros:
                errores.append(f"NFL: lesiones de equipos que no existen en nfl_partidos (nombre distinto): {otros}")

    # --- NBA ---
    if existe("nba_partidos"):
        ultima = q("SELECT MAX(temporada) FROM nba_partidos WHERE puntos_local IS NOT NULL")[0][0]
        for temporada, n in q("SELECT temporada, COUNT(*) FROM nba_partidos WHERE tipo = 'REG' AND temporada BETWEEN 2022 AND ? "
                              "AND (puntos_local IS NOT NULL OR temporada < ?) GROUP BY 1 ORDER BY 1", ultima, ultima):
            if n != 1230 and (temporada < ultima or not q("SELECT 1 FROM nba_partidos WHERE tipo = 'REG' AND temporada = ? "
                                                         "AND puntos_local IS NULL LIMIT 1", temporada)):
                errores.append(f"NBA {temporada - 1}-{str(temporada)[2:]}: {n} partidos de fase regular y se esperaban 1230")
        sin_resultado = q("SELECT COUNT(*) FROM nba_partidos WHERE temporada < ? AND puntos_local IS NULL", ultima)[0][0]
        if sin_resultado:
            errores.append(f"NBA: {sin_resultado} partidos de temporadas ya terminadas sin resultado")
        # los ids de las tablas de equipo y jugadores se comparan como texto igual que en la tabla de partidos
        jugados = q("SELECT id, temporada, tipo FROM nba_partidos WHERE puntos_local IS NOT NULL AND temporada >= 2020 AND fecha < ?",
                    reciente)
        for tabla, etiqueta in (("nba_estadisticas_equipo", "estadísticas de equipo"), ("nba_jugadores_partido", "datos de jugadores")):
            if not existe(tabla):
                continue
            con_datos = {str(i) for (i,) in q(f"SELECT DISTINCT id FROM {tabla}")}
            sin = Counter((t, tipo) for i, t, tipo in jugados if i not in con_datos)
            graves = sorted((k, n) for k, n in sin.items() if k[0] >= ultima - 1)
            antiguos = sorted((k, n) for k, n in sin.items() if k[0] < ultima - 1)
            nombre = lambda k: (f"{k[0] - 1}-{str(k[0])[2:]}", k[1])  # noqa: E731
            if graves:
                errores.append(f"NBA: partidos de las dos últimas temporadas sin {etiqueta}: {[(*nombre(k), n) for k, n in graves]}")
            if antiguos:
                avisos.append(f"NBA: huecos antiguos de la fuente sin {etiqueta}: {[(*nombre(k), n) for k, n in antiguos]}")
        if existe("nba_jugadores_partido"):
            raros = q("SELECT COUNT(*) FROM (SELECT id, equipo FROM nba_jugadores_partido GROUP BY 1, 2 "
                      "HAVING SUM(minutos) < 150 OR SUM(minutos) > 400)")[0][0]
            if raros:
                avisos.append(f"NBA: {raros} plantillas de un partido con minutos totales imposibles (menos de 150 o más de 400)")
            un_equipo = q("SELECT COUNT(*) FROM (SELECT id FROM nba_jugadores_partido GROUP BY 1 HAVING COUNT(DISTINCT equipo) != 2)")[0][0]
            if un_equipo:
                errores.append(f"NBA: {un_equipo} partidos con jugadores de un solo equipo (o de más de dos)")
            sin_nombre = q("SELECT COUNT(*) FROM nba_jugadores_partido WHERE jugador NOT IN (SELECT jugador FROM nba_jugadores)")[0][0]
            if sin_nombre:
                errores.append(f"NBA: {sin_nombre} registros de jugadores sin nombre en nba_jugadores")
    return errores, avisos


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
    por_liga = defaultdict(list)
    for c, f, t, l, v in q("SELECT competicion, fecha, temporada, local, visitante FROM futbol_partidos"):
        por_liga[c].append((date.fromisoformat(f), t, l, v))
    giradas = sorted(c for c, partidos in por_liga.items() if base.fechas_intercambiadas(partidos))
    if giradas:
        errores.append(f"Fechas con el día y el mes intercambiados en: {', '.join(giradas)}")
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
    try:
        sin_jugadores = q("SELECT COUNT(*) FROM nba_partidos p WHERE puntos_local IS NOT NULL AND tipo != 'COPA' AND fecha >= ? "
                          "AND NOT EXISTS (SELECT 1 FROM nba_jugadores_partido j WHERE CAST(j.id AS TEXT) = p.id)",
                          (date.today() - timedelta(days=30)).isoformat())[0][0]
        if sin_jugadores:
            avisos.append(f"NBA: {sin_jugadores} partidos del último mes sin datos de jugadores (el ajuste por bajas los ignora)")
    except sqlite3.OperationalError:
        pass

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

    err_cob, av_cob = cobertura(con)
    errores += err_cob
    avisos += av_cob
    for a in avisos:
        print(f"AVISO: {a}")
    for e in errores:
        print(f"ERROR: {e}")
    print("Datos correctos." if not errores else f"{len(errores)} errores de integridad.")
    return not errores


if __name__ == "__main__":
    conexion = base.conectar()
    sys.exit(0 if verificar(conexion) else 1)
