import unittest
from datetime import date, timedelta

from analisis_deportivo import base
from analisis_deportivo.nba import analisis, modelos
from analisis_deportivo.nba.datos import Partido, descansos, leer_temporada, texto_temporada

INICIO = date(2025, 10, 21)


def P(dia, local, visitante, pl, pv, temporada=2026, **kw):
    return Partido(temporada, INICIO + timedelta(days=dia), local, visitante, pl, pv, id=f"{dia}{local}{visitante}", **kw)


PARTIDOS = [
    P(0, "BOS", "NY", 110, 100),
    P(1, "NY", "BOS", 120, 118, prorrogas=1),
    P(2, "LAL", "BOS", 99, 105),  # BOS juega tres días seguidos
    P(3, "OKC", "LAL", 130, 100),
    P(5, "NY", "OKC", None, None),
]


class TestDatos(unittest.TestCase):
    def test_temporadas(self):
        self.assertEqual(texto_temporada(2026), "2025-26")
        self.assertEqual(leer_temporada("2025-26"), 2026)
        self.assertEqual(leer_temporada("2026"), 2026)

    def test_descansos(self):
        dias = descansos(PARTIDOS)
        self.assertEqual(dias[("2LALBOS", "BOS")], 1)
        self.assertNotIn(("0BOSNY", "BOS"), dias)
        self.assertEqual(dias[("5NYOKC", "OKC")], 2)

    def test_marcador(self):
        self.assertEqual(PARTIDOS[1].marcador(), "BOS 118 @ NY 120 (pró.)")
        self.assertFalse(PARTIDOS[-1].jugado)


class TestAnalisis(unittest.TestCase):
    def test_clasificacion(self):
        filas = analisis.clasificacion(PARTIDOS, 2026)
        self.assertEqual(filas["BOS"].total.texto(), "2-1")
        self.assertEqual(filas["LAL"].total.texto(), "0-2")
        self.assertEqual(filas["BOS"].conferencia.texto(), "1-1")  # NY es del Este, LAL del Oeste
        este = analisis.por_conferencia(filas, 2026)["Este"]
        self.assertEqual([f.equipo for f in este], ["BOS", "NY"])

    def test_splits(self):
        splits = dict(analisis.splits([p for p in PARTIDOS], "BOS"))
        self.assertEqual(splits["Segundo de dos días seguidos"].texto(), "1-1")  # días 1 y 2
        self.assertEqual(splits["Con prórroga"].texto(), "0-1")

    def test_conferencia_historica(self):
        from analisis_deportivo.nba.equipos import conferencia
        self.assertEqual(conferencia("NO", 2003), "Este")
        self.assertEqual(conferencia("NO", 2026), "Oeste")


class TestModelos(unittest.TestCase):
    def test_elo_suma_cero(self):
        elo = modelos.EloNBA().procesar(PARTIDOS)
        self.assertAlmostEqual(sum(elo.rating.values()) / len(elo.rating), 1500)
        self.assertGreater(elo.rating["OKC"], elo.rating["LAL"])

    def test_prediccion(self):
        elo = modelos.EloNBA().procesar(PARTIDOS)
        ratings = modelos.RatingsNBA().ajustar(PARTIDOS, 2026)
        pr = modelos.predecir(elo, ratings, "OKC", "LAL")
        self.assertGreater(pr["prob_local"], 0.5)
        self.assertAlmostEqual(pr["puntos_local"] - pr["puntos_visitante"], pr["margen"])
        cansado = modelos.predecir(elo, ratings, "OKC", "LAL", ajuste=modelos.ajuste_descanso(1, 3))
        self.assertLess(cansado["prob_local"], pr["prob_local"])

    def test_moneyline(self):
        self.assertEqual(modelos.moneyline_justa(0.5), "-100")
        self.assertEqual(modelos.moneyline_justa(0.2), "+400")


@unittest.skipUnless(base.disponible(), "requiere la base de datos")
class TestBaseReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from analisis_deportivo.nba.datos import cargar_desde_base

        try:
            cls.partidos = cargar_desde_base(base.conectar())
        except base.sqlite3.OperationalError:
            raise unittest.SkipTest("la base no tiene la NBA")

    def test_temporada_completa(self):
        filas = analisis.clasificacion(self.partidos, 2025)
        self.assertEqual(len(filas), 30)
        self.assertEqual(sum(f.total.g for f in filas.values()), 1230)
        self.assertTrue(all(f.total.jugados == 82 for f in filas.values()))

    def test_simulacion(self):
        res, pendientes = modelos.simular_temporada(self.partidos, 2025, simulaciones=200, semilla=1)
        self.assertEqual(pendientes, 0)
        self.assertAlmostEqual(sum(r.get("campeon", 0) for r in res.values()), 1)
        self.assertAlmostEqual(sum(r.get("playoffs", 0) for r in res.values()), 16)

    def test_evaluar(self):
        from analisis_deportivo.nba.jugadores import por_partido

        m = modelos.evaluar(self.partidos, 2025)
        self.assertGreater(m["n"], 1300)
        self.assertLess(m["brier"] / m["n"], 0.215)
        datos = por_partido(base.conectar())
        if datos:
            con = modelos.evaluar(self.partidos, 2025, jugadores=datos)
            self.assertLess(con["brier"], m["brier"])


class TestJugadores(unittest.TestCase):
    def _ctx(self, ultimo):
        from analisis_deportivo.nba.jugadores import ContextoJugadores

        ctx = ContextoJugadores(n_habitual=3)
        estrella, normal = ("A", "Estrella", 36, 30.0), ("B", "Normal", 30, 10.0)
        for d in range(3):
            ctx.agregar(INICIO + timedelta(days=d), "BOS", [estrella, normal] if d < 2 or ultimo else [normal])
        return ctx

    def test_baja_resta(self):
        con, sin = self._ctx(True), self._ctx(False)
        hoy = INICIO + timedelta(days=3)
        self.assertLess(sin.ajuste("BOS", hoy), con.ajuste("BOS", hoy))
        self.assertLess(sin.ajuste("BOS", hoy), 0)
        self.assertEqual([n for n, *_ in sin.ausentes("BOS", hoy)], ["Estrella"])

    def test_tras_el_verano_no_supone_bajas(self):
        ctx = self._ctx(False)
        otoño = INICIO + timedelta(days=150)
        self.assertEqual(ctx.ajuste("BOS", otoño), 0.0)
        self.assertEqual(ctx.ausentes("BOS", otoño), [])

    def test_game_score(self):
        from analisis_deportivo.nba.jugadores import game_score

        self.assertAlmostEqual(game_score({"points": 20, "field_goals_made": 8, "field_goals_attempted": 15,
                                           "assists": 5, "turnovers": 2}), 20 + 3.2 - 10.5 + 3.5 - 2)
