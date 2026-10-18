import sqlite3
import unittest
from datetime import date

from analisis_deportivo import base
from analisis_deportivo.futbol.datos import cargar_desde_base
from analisis_deportivo.nfl import estadisticas
from analisis_deportivo.nfl.datos import Juego


def _base_en_memoria():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(base.ESQUEMA)
    columnas = "competicion, temporada, fecha, local, visitante, goles_local, goles_visitante, tiros_local, tiros_visitante, fuente"
    con.executemany(f"INSERT INTO futbol_partidos ({columnas}) VALUES (?,?,?,?,?,?,?,?,?,?)", [
        ("SP1", "2024-25", "2025-03-01", "Betis", "Sevilla", 2, 1, 12, 8, "clubes"),
        ("SP1", "2025-26", "2025-09-01", "Betis", "Getafe", 0, 0, None, None, "clubes"),
        ("SP1", "2025-26", "2025-09-08", "Getafe", "Sevilla", 1, 3, 5, 9, "clubes"),
        ("SP1", "2025-26", "2025-09-15", "Sevilla", "Betis", None, None, None, None, "openfootball"),
    ])
    con.executemany("INSERT INTO futbol_selecciones VALUES (?,?,?,?,?,?,?,?,?,?)", [
        ("2022-12-18", "Argentina", "France", 3, 3, "FIFA World Cup", "Lusail", "Qatar", 1, "Argentina"),
        ("2023-03-23", "Argentina", "Panama", 2, 0, "Friendly", "Buenos Aires", "Argentina", 0, None),
    ])
    return con


class TestBase(unittest.TestCase):
    def test_temporada_de(self):
        self.assertEqual(base.temporada_de(date(2025, 8, 20)), "2025-26")
        self.assertEqual(base.temporada_de(date(2026, 5, 20)), "2025-26")
        self.assertEqual(base.temporada_de(date(2020, 7, 20)), "2019-20")  # temporada alargada por la pandemia
        self.assertEqual(base.temporada_de(date(2026, 5, 20), anual=True), "2026")

    def test_resolver(self):
        self.assertEqual(base.resolver_competicion("espana"), "SP1")
        self.assertEqual(base.resolver_competicion("e0"), "E0")
        self.assertEqual(base.resolver_competicion("LaLiga"), "SP1")
        with self.assertRaises(ValueError):
            base.resolver_competicion("marte")
        self.assertEqual(base.resolver_torneo("mundial"), "FIFA World Cup")

    def test_mapear_nombres(self):
        existentes = [("2026-08-29", "Elversberg", "Leverkusen", 3, 2), ("2026-08-29", "FC Koln", "Hoffenheim", 3, 2),
                      ("2026-08-30", "Bayern Munich", "Mainz", 1, 0)]
        of = [("2026-08-29", "SV 07 Elversberg", "Bayer 04 Leverkusen", 3, 2),
              ("2026-08-29", "1. FC Köln", "TSG 1899 Hoffenheim", 3, 2),
              ("2026-08-30", "FC Bayern München", "1. FSV Mainz 05", 1, 0)]
        mapa = base._mapear_nombres(of, existentes)
        self.assertEqual(mapa["FC Bayern München"], "Bayern Munich")  # partido único con ese marcador
        self.assertEqual(mapa["1. FC Köln"], "FC Koln")  # desempate por parecido del nombre
        self.assertEqual(mapa["Bayer 04 Leverkusen"], "Leverkusen")

    def test_cargar_clubes(self):
        con = _base_en_memoria()
        self.addCleanup(con.close)
        partidos, desc = cargar_desde_base(con, "SP1")
        self.assertEqual(desc, "SP1 · 2025-26")
        self.assertEqual(len(partidos), 3)
        self.assertEqual(partidos[1].estadisticas, {"tiros": (5, 9)})
        self.assertFalse(partidos[2].jugado)
        todas, _ = cargar_desde_base(con, "SP1", "todas")
        self.assertEqual(len(todas), 4)
        rango, _ = cargar_desde_base(con, "SP1", "2024-25:2024-25")
        self.assertEqual(len(rango), 1)

    def test_cargar_selecciones(self):
        con = _base_en_memoria()
        self.addCleanup(con.close)
        partidos, _ = cargar_desde_base(con, None, None, torneo="FIFA World Cup")
        final = partidos[0]
        self.assertTrue(final.neutral)
        self.assertEqual(final.penaltis, "Argentina")
        self.assertIn("penaltis", final.marcador())
        todos, _ = cargar_desde_base(con, "selecciones", "2022:2023")
        self.assertEqual(len(todos), 2)


class TestEstadisticasNFL(unittest.TestCase):
    def _fila(self, equipo, rival, yardas_pase, carrera, perdidas, epa):
        return {"id": "g1", "equipo": equipo, "rival": rival, "temporada": 2025, "semana": 1,
                **estadisticas.metricas_partido({"passing_yards": yardas_pase, "sack_yards_lost": -10, "rushing_yards": carrera,
                                                 "attempts": 30, "sacks_suffered": 2, "carries": 28,
                                                 "passing_interceptions": perdidas, "fumbles_lost_total": 0,
                                                 "passing_epa": epa, "rushing_epa": 0})}

    def test_metricas_y_factores(self):
        a = self._fila("KC", "BUF", 300, 120, 0, 8.0)
        b = self._fila("BUF", "KC", 200, 80, 2, -4.0)
        self.assertEqual(a["yardas"], 410)  # 300 - 10 de sacks + 120
        self.assertAlmostEqual(a["epa_jugada"], 8 / 60)
        res = estadisticas.por_equipo([a, b])
        self.assertEqual(res["KC"].diferencial_perdidas, 2)
        self.assertEqual(res["KC"].contra_pp("yardas"), 270)
        juego = Juego(2025, 1, date(2025, 9, 7), "KC", "BUF", 27, 20, id="g1")
        f = estadisticas.factores_victoria([a, b], [juego])
        self.assertEqual(f["perdidas"], (100.0, 1))
        self.assertEqual(f["yardas"], (100.0, 1))


if __name__ == "__main__":
    unittest.main()
