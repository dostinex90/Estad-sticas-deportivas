import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

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

    def test_fechas_intercambiadas(self):
        # Liga de 8 equipos de marzo a noviembre con una jornada cada 3 días
        equipos, partidos = list("ABCDEFGH"), []
        for jornada in range(80):
            dia = date(2019, 3, 2) + timedelta(days=3 * jornada)
            ronda = equipos[:1] + equipos[1:][jornada % 7:] + equipos[1:][:jornada % 7]  # método del círculo
            partidos += [(dia, "2019", ronda[k], ronda[7 - k]) for k in range(4)]
        self.assertFalse(base.fechas_intercambiadas(partidos))
        girados = [(base._girar_fecha(d), t, l, v) for d, t, l, v in partidos]  # como los trae la fuente
        self.assertTrue(base.fechas_intercambiadas(girados))
        self.assertEqual(base._girar_fecha(date(2019, 1, 4)), date(2019, 4, 1))
        self.assertEqual(base._girar_fecha(date(2019, 3, 31)), date(2019, 3, 31))

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


class TestFootballData(unittest.TestCase):
    """football-data.co.uk completa resultados pendientes y añade partidos sin duplicar."""

    CSV = (
        "Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HS,AS,HST,AST,HF,AF,HC,AC,HY,AY,HR,AR,AvgH,AvgD,AvgA\n"
        "E0,16/08/2025,15:00,Arsenal,Chelsea,2,1,H,1,0,15,9,6,3,10,12,7,4,1,2,0,0,1.9,3.6,4.1\n"
        "E0,23/08/2025,15:00,Nott'm Forest,Arsenal,0,3,A,0,1,8,17,2,7,11,9,3,8,2,1,0,0,4.5,3.8,1.8\n"
        "E0,30/08/2025,17:30,Chelsea,Nott'm Forest,1,1,D,0,0,14,6,5,2,9,13,9,2,3,2,0,1,1.6,4.0,5.5\n"
    ).encode()

    def setUp(self):
        import urllib.error

        self.con = sqlite3.connect(":memory:")
        self.addCleanup(self.con.close)
        self.con.executescript(base.ESQUEMA)
        cols = "competicion, temporada, fecha, local, visitante, goles_local, goles_visitante, fuente"
        self.con.executemany(f"INSERT INTO futbol_partidos ({cols}) VALUES (?,?,?,?,?,?,?,?)", [
            ("E0", "2025-26", "2025-08-16", "Arsenal", "Chelsea", 2, 1, "clubes"),            # ya está completo
            ("E0", "2025-26", "2025-08-24", "Nottm Forest", "Arsenal", None, None, "openfootball"),  # pendiente, otra fecha
            ("E0", "2024-25", "2025-03-01", "Nottm Forest", "Chelsea", 1, 0, "clubes"),
        ])
        original = base._bajar

        def falso(url):
            if "mmz4281/2526/E0" in url:
                return self.CSV
            raise urllib.error.HTTPError(url, 404, "no", None, None)

        base._bajar = falso
        self.addCleanup(setattr, base, "_bajar", original)
        cache = base.CACHE_FD
        base.CACHE_FD = Path(tempfile.mkdtemp())  # no ensuciar datos/football_data
        self.addCleanup(setattr, base, "CACHE_FD", cache)

    def test_completa_y_anade(self):
        avisos = []
        n = base._football_data(self.con, avisos.append, date(2025, 10, 1))
        filas = self.con.execute("SELECT fecha, local, visitante, goles_local, goles_visitante, tiros_local, fuente "
                                 "FROM futbol_partidos WHERE temporada = '2025-26' ORDER BY fecha").fetchall()
        self.assertEqual(len(filas), 3)  # 1 existente + 1 completado + 1 nuevo, sin duplicados
        self.assertEqual(filas[0][6], "clubes")  # el partido completo no se toca
        self.assertEqual(filas[1][1:6], ("Nottm Forest", "Arsenal", 0, 3, 8))  # nombre canónico y estadísticas
        self.assertEqual(filas[2][1:5], ("Chelsea", "Nottm Forest", 1, 1))
        self.assertEqual(n, 2)
        self.assertIn("+1 partidos nuevos, 1 resultados completados", avisos[-1])

    def test_sin_red_usa_guardados(self):
        import gzip
        import urllib.error

        (base.CACHE_FD / "E0_2223.csv.gz").write_bytes(gzip.compress(self.CSV.replace(b"/2025", b"/2022")))

        def sin_red(url):
            raise urllib.error.URLError("sin conexión")

        base._bajar = sin_red
        avisos = []
        base._football_data(self.con, avisos.append, date(2025, 10, 1))
        n = self.con.execute("SELECT COUNT(*) FROM futbol_partidos WHERE temporada = '2022-23'").fetchone()[0]
        self.assertEqual(n, 3)  # la temporada guardada se carga aunque no haya red
        self.assertTrue(any("no disponible" in a for a in avisos))

    def test_error_pasajero_no_marca_inexistente(self):
        import urllib.error

        def caido(url):
            raise urllib.error.HTTPError(url, 500, "error", None, None)

        base._bajar = caido
        estado = {"descargas": 0, "cache": 0, "sin_red": False, "error": None}
        self.assertIsNone(base._bajar_fd("url", "E0_0405", True, estado))
        self.assertFalse((base.CACHE_FD / "E0_0405.none").exists())  # se reintentará
        base._bajar = lambda url: (_ for _ in ()).throw(urllib.error.HTTPError(url, 404, "no", None, None))
        self.assertIsNone(base._bajar_fd("url", "E0_0405", True, estado))
        self.assertTrue((base.CACHE_FD / "E0_0405.none").exists())  # 404: no existe


class TestLigasNuevas(unittest.TestCase):
    def test_solo_posteriores_traduce_nombres(self):
        con = sqlite3.connect(":memory:")
        self.addCleanup(con.close)
        con.executescript(base.ESQUEMA)
        cols = "competicion, temporada, fecha, local, visitante, goles_local, goles_visitante, fuente"
        con.executemany(f"INSERT INTO futbol_partidos ({cols}) VALUES (?,?,?,?,?,?,?,?)", [
            ("ARG", "2024", "2024-05-01", "Argentinos Jrs", "Racing Club", 2, 1, "clubes"),
            ("ARG", "2024", "2024-05-08", "Racing Club", "Godoy Cruz", 0, 0, "clubes"),
        ])
        fila = lambda f, l, v, gl, gv: ("ARG", f[:4], f, None, l, v, gl, gv) + (None,) * 24 + ("football-data",)  # noqa: E731
        filas = [fila("2024-05-01", "Argentinos Juniors", "Racing", 2, 1), fila("2024-05-08", "Racing", "Godoy Cruz", 0, 0),
                 fila("2025-02-01", "Racing", "Argentinos Juniors", 1, 1)]
        nuevas = base._solo_posteriores(con, "ARG", filas)
        self.assertEqual(len(nuevas), 1)  # los dos partidos ya presentes no se repiten
        self.assertEqual(nuevas[0][4:6], ("Racing Club", "Argentinos Jrs"))  # nombres de la base
