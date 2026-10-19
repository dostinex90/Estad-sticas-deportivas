import importlib.util
import sqlite3
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("verificar_datos", RAIZ / "scripts" / "verificar_datos.py")
verificar_datos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verificar_datos)

HOY = date(2026, 10, 19)


def _base():
    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE nfl_partidos (game_id, season, game_type, week, gameday, home_team, away_team, home_score, away_score);
        CREATE TABLE nfl_estadisticas_equipo (game_id, team);
        CREATE TABLE nfl_snaps (game_id, player);
        CREATE TABLE nfl_lesiones (season, week, team);
        CREATE TABLE nba_partidos (id, temporada, tipo, fecha, local, visitante, puntos_local, puntos_visitante);
        CREATE TABLE nba_estadisticas_equipo (id, equipo);
        CREATE TABLE nba_jugadores_partido (id INTEGER, equipo, jugador INTEGER, minutos INTEGER);
        CREATE TABLE nba_jugadores (jugador INTEGER, nombre);
    """)
    return con


def _nfl_temporada(con, temporada, n, jugados=True):
    for i in range(n):
        gid = f"{temporada}_{i}"
        con.execute("INSERT INTO nfl_partidos VALUES (?,?,?,?,?,?,?,?,?)",
                    (gid, temporada, "REG", 1 + i // 16, f"{temporada}-10-01", f"L{i}", f"V{i}", 20 if jugados else None, 10))
        if jugados:
            con.executemany("INSERT INTO nfl_estadisticas_equipo VALUES (?,?)", [(gid, f"L{i}"), (gid, f"V{i}")])
            con.execute("INSERT INTO nfl_snaps VALUES (?,?)", (gid, "x"))
            con.execute("INSERT OR IGNORE INTO nfl_lesiones VALUES (?,?,?)", (temporada, 1 + i // 16, f"L{i}"))


class TestCobertura(unittest.TestCase):
    def test_base_correcta_sin_errores(self):
        con = _base()
        _nfl_temporada(con, 2020, 256)
        _nfl_temporada(con, 2022, 271)  # la de 2022 tuvo 271 partidos
        errores, avisos = verificar_datos.cobertura(con, HOY)
        self.assertEqual(errores, [])

    def test_nfl_partidos_que_faltan(self):
        con = _base()
        _nfl_temporada(con, 2023, 270)
        _nfl_temporada(con, 2024, 272)
        errores, _ = verificar_datos.cobertura(con, HOY)
        self.assertTrue(any("NFL 2023: 270" in e for e in errores), errores)

    def test_nfl_partido_sin_estadisticas_es_error_y_sin_snaps_aviso(self):
        con = _base()
        _nfl_temporada(con, 2024, 272)
        con.execute("DELETE FROM nfl_estadisticas_equipo WHERE game_id = '2024_5'")
        con.execute("DELETE FROM nfl_snaps WHERE game_id = '2024_6'")
        errores, avisos = verificar_datos.cobertura(con, HOY)
        self.assertTrue(any("sin estadísticas" in e for e in errores), errores)
        self.assertTrue(any("sin snaps" in a for a in avisos), avisos)

    def test_nfl_semana_sin_parte_de_lesionados_es_aviso(self):
        con = _base()
        _nfl_temporada(con, 2024, 272)
        con.execute("DELETE FROM nfl_lesiones WHERE week = 3")
        errores, avisos = verificar_datos.cobertura(con, HOY)
        self.assertEqual(errores, [])
        self.assertTrue(any("2024 semanas 3" in a for a in avisos), avisos)

    def test_nba_temporada_incompleta_y_huecos(self):
        con = _base()
        for temporada, n in ((2025, 1230), (2026, 1229)):
            for i in range(n):
                con.execute("INSERT INTO nba_partidos VALUES (?,?,?,?,?,?,?,?)",
                            (str(temporada * 10000 + i), temporada, "REG", f"{temporada - 1}-12-01", "A", "B", 100, 90))
                con.execute("INSERT INTO nba_estadisticas_equipo VALUES (?,?)", (str(temporada * 10000 + i), "A"))
        con.execute("INSERT INTO nba_partidos VALUES ('1','2027','REG','2026-10-20','A','B',NULL,NULL)")
        errores, avisos = verificar_datos.cobertura(con, HOY)
        self.assertTrue(any("2025-26: 1229" in e for e in errores), errores)
        self.assertTrue(any("sin datos de jugadores" in e for e in errores), errores)

    def test_nba_jugadores_de_un_solo_equipo(self):
        con = _base()
        con.execute("INSERT INTO nba_partidos VALUES ('7',2026,'PO','2026-05-01','A','B',100,90)")
        con.execute("INSERT INTO nba_estadisticas_equipo VALUES ('7','A')")
        con.executemany("INSERT INTO nba_jugadores_partido VALUES (7,?,?,?)", [("A", 1, 240), ("A", 2, 100)])
        con.execute("INSERT INTO nba_jugadores VALUES (1,'Uno')")
        errores, _ = verificar_datos.cobertura(con, HOY)
        self.assertTrue(any("un solo equipo" in e for e in errores), errores)
        self.assertTrue(any("sin nombre" in e for e in errores), errores)


if __name__ == "__main__":
    unittest.main()
