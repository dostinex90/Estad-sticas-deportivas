import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from analisis_deportivo.futbol import analisis, modelos
from analisis_deportivo.futbol.datos import Partido, cargar_partidos, pendientes


def P(dia, local, visitante, gl, gv, hl=None, hv=None, **stats):
    return Partido(date(2026, 1, dia), local, visitante, gl, gv, hl, hv, estadisticas=stats)


PARTIDOS = [
    P(1, "A", "B", 2, 0, 1, 0, tiros=(10, 4), tiros_puerta=(5, 1)),
    P(2, "B", "C", 1, 1, 0, 1),
    P(3, "C", "A", 0, 3, 0, 2),
    P(4, "B", "A", 2, 1, 0, 1),
    P(5, "A", "C", 1, 1, 1, 0),
    P(6, "C", "B", 0, 2, 0, 0),
]


class TestEstadisticas(unittest.TestCase):
    def test_tabla(self):
        tabla = analisis.tabla_posiciones(PARTIDOS)
        self.assertEqual([s.equipo for s in tabla], ["A", "B", "C"])
        a = tabla[0]
        self.assertEqual((a.jugados, a.ganados, a.empatados, a.perdidos, a.puntos), (4, 2, 1, 1, 7))
        self.assertEqual(a.diferencia, 4)

    def test_condicion_local(self):
        stats = analisis.calcular_estadisticas(PARTIDOS, "local")
        self.assertEqual((stats["A"].jugados, stats["A"].goles_favor), (2, 3))

    def test_forma_mercados_y_descanso(self):
        b = analisis.calcular_estadisticas(PARTIDOS)["B"]
        self.assertEqual(b.forma(), "PEGG")
        self.assertEqual(b.porterias_cero, 1)
        self.assertEqual(b.ambos_marcan, 2)
        # B perdía al descanso contra A (día 4) y ganó: remontada
        self.assertEqual(b.gano_tras_perder_descanso, 1)
        a = analisis.calcular_estadisticas(PARTIDOS)["A"]
        self.assertEqual(a.ganando_descanso, 4)
        self.assertEqual(a.gano_tras_ganar_descanso, 2)

    def test_estadisticas_de_juego(self):
        a = analisis.calcular_estadisticas(PARTIDOS)["A"]
        self.assertEqual(a.juego["tiros"], [10, 4, 1])
        self.assertAlmostEqual(a.conversion(), 20.0)  # 2 goles en 10 tiros
        self.assertAlmostEqual(a.paradas(), 100.0)

    def test_h2h_y_resumen(self):
        duelos, r = analisis.enfrentamientos_directos(PARTIDOS, "A", "B")
        self.assertEqual((len(duelos), r["A"], r["B"], r["empates"]), (2, 1, 1, 0))
        res = analisis.resumen_liga(PARTIDOS)
        self.assertEqual(res["goles"], 14)
        self.assertEqual(res["descanso"]["matriz"]["2/1"], 1)  # B 0-1 A al descanso, 2-1 final
        self.assertEqual(res["descanso"]["remontadas"], 1)

    def test_tabla_descanso(self):
        tabla = analisis.tabla_descanso(PARTIDOS)
        self.assertEqual(tabla[0].equipo, "A")
        self.assertEqual(tabla[0].puntos, 12)  # A iba ganando al descanso en sus 4 partidos


class TestModelos(unittest.TestCase):
    def setUp(self):
        self.modelo = modelos.ModeloPoisson(vida_media_dias=None).ajustar(PARTIDOS)

    def test_probabilidades_coherentes(self):
        pr = self.modelo.predecir("A", "C")
        self.assertAlmostEqual(pr["p1"] + pr["px"] + pr["p2"], 1.0, places=6)
        self.assertGreater(pr["p1"], pr["p2"])
        self.assertGreater(pr["mas"][1.5], pr["mas"][2.5])
        self.assertAlmostEqual(pr["handicap"][-0.5], pr["p1x"], places=9)

    def test_fuerzas_normalizadas(self):
        self.assertAlmostEqual(sum(self.modelo.ataque.values()) / 3, 1.0)
        self.assertGreater(self.modelo.ataque["A"], self.modelo.ataque["C"])

    def test_elo_suma_cero(self):
        elo = modelos.EloFutbol().procesar(PARTIDOS)
        self.assertAlmostEqual(sum(elo.rating.values()), 1500 * 3)
        self.assertEqual(elo.ranking()[0][0], "A")

    def test_cuotas(self):
        probs, margen = modelos.probabilidades_mercado((2.0, 3.5, 4.0))
        self.assertAlmostEqual(sum(probs), 1.0)
        self.assertGreater(margen, 0)

    def test_evaluar(self):
        partidos = cargar_partidos(Path(__file__).parent.parent / "datos" / "futbol_ejemplo.csv")
        r = modelos.evaluar(partidos, minimo=30)
        self.assertGreater(r["modelo"]["n"], 0)
        self.assertLess(r["modelo"]["rps"], 0.3)


class TestCarga(unittest.TestCase):
    def _archivo(self, contenido, sufijo=".csv"):
        f = tempfile.NamedTemporaryFile("w", suffix=sufijo, delete=False, encoding="utf-8")
        f.write(contenido)
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name

    def test_formato_propio_con_pendientes(self):
        ruta = self._archivo(
            "fecha,local,visitante,goles_local,goles_visitante,tiros_local,tiros_visitante\n"
            "2026-01-05,A,B,1,0,9,3\n2026-01-01,B,A,2,2,,\n2026-01-09,A,C,,,,\n"
        )
        partidos = cargar_partidos(ruta)
        self.assertEqual(partidos[0].fecha, date(2026, 1, 1))
        self.assertEqual(partidos[1].estadisticas, {"tiros": (9, 3)})
        self.assertEqual(len(pendientes(partidos)), 1)

    def test_football_data(self):
        ruta = self._archivo(
            "Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HTHG,HTAG,HS,AS,HST,AST,HC,AC,HY,AY,HR,AR,B365H,B365D,B365A\n"
            "SP1,15/08/2025,Girona,Vallecano,1,3,A,0,3,10,12,4,6,5,3,2,1,0,0,2.1,3.3,3.5\n"
        )
        p = cargar_partidos(ruta)[0]
        self.assertEqual((p.local, p.goles_visitante, p.descanso_visitante), ("Girona", 3, 3))
        self.assertEqual(p.estadisticas["tiros_puerta"], (4, 6))
        self.assertEqual(p.cuotas, (2.1, 3.3, 3.5))
        self.assertEqual(p.fecha, date(2025, 8, 15))

    def test_openfootball(self):
        datos = {"name": "Liga", "matches": [
            {"round": "1", "date": "2025-08-15", "team1": "A", "team2": "B", "score": {"ft": [1, 3], "ht": [0, 3]}},
            {"round": "1", "date": "2025-08-16", "team1": "C", "team2": "D", "score": [0, 0]},
            {"round": "2", "date": "2025-08-22", "team1": "B", "team2": "C"},
        ]}
        partidos = cargar_partidos(self._archivo(json.dumps(datos), ".json"))
        self.assertEqual(partidos[0].descanso_visitante, 3)
        self.assertTrue(partidos[1].jugado and not partidos[1].tiene_descanso)
        self.assertFalse(partidos[2].jugado)

    def test_errores(self):
        with self.assertRaises(ValueError):
            cargar_partidos(self._archivo("fecha,local\n2026-01-01,A\n"))
        with self.assertRaisesRegex(ValueError, "Fila 2"):
            cargar_partidos(self._archivo("fecha,local,visitante,goles_local,goles_visitante\n2026-01-01,A,B,x,0\n"))


if __name__ == "__main__":
    unittest.main()
