import tempfile
import unittest
from datetime import date
from pathlib import Path

from analisis_deportivo.nfl import analisis, modelos
from analisis_deportivo.nfl.datos import Juego, cargar_juegos

EJEMPLO = Path(__file__).parent.parent / "datos" / "nfl_ejemplo.csv"


def J(semana, local, visitante, pl, pv, linea=None, total=None, temporada=2025, **kw):
    return Juego(temporada, semana, date(temporada, 9, 1 + semana), local, visitante, pl, pv,
                 linea=linea, total_linea=total, **kw)


JUEGOS = [
    J(1, "KC", "DEN", 27, 20, linea=6.5, total=45.5),   # KC gana y cubre, over
    J(2, "DEN", "KC", 24, 21, linea=-3.0, total=47.0),  # DEN gana como underdog, under
    J(3, "KC", "BUF", 20, 23, linea=1.5, total=50.0, prorroga=True),
    J(4, "BUF", "DEN", 30, 10, linea=7.0),
    J(5, "LV", "KC", 17, 17),
]


class TestAnalisis(unittest.TestCase):
    def test_registro_y_ats(self):
        r = analisis.Registro.de(analisis.vistas(JUEGOS, "KC"))
        self.assertEqual((r.g, r.p, r.e), (1, 2, 1))
        self.assertAlmostEqual(r.porcentaje, 1.5 / 4)
        self.assertEqual((r.cubre, r.no_cubre, r.push), (1, 2, 0))
        self.assertEqual((r.over, r.under), (1, 2))
        self.assertEqual(r.texto(), "1-2-1")

    def test_vista_linea_desde_el_equipo(self):
        v = analisis.vistas(JUEGOS[:1], "DEN")[0]
        self.assertEqual(v.linea, -6.5)
        self.assertEqual(v.ats, "N")

    def test_pitagoricas(self):
        r = analisis.Registro(g=10, p=7, pf=400, pc=400)
        self.assertAlmostEqual(r.victorias_pitagoricas, 8.5)

    def test_splits(self):
        nombres = dict(analisis.splits(JUEGOS, "KC"))
        self.assertEqual(nombres["División"].texto(), "1-1-1")
        self.assertEqual(nombres["Prórroga"].texto(), "0-1")
        self.assertEqual(nombres["Como favorito"].jugados, 3)

    def test_clasificacion(self):
        filas = analisis.clasificacion(JUEGOS, 2025)
        oeste = analisis.por_division(filas)["AFC Oeste"]
        # LV 0-0-1 (.500), KC 1-2-1 (.375), DEN 1-2 (.333)
        self.assertEqual([f.equipo for f in oeste], ["LV", "KC", "DEN"])

    def test_resumen(self):
        r = analisis.resumen_liga(JUEGOS)
        self.assertEqual(r["partidos"], 5)
        self.assertAlmostEqual(r["pct_prorroga"], 20.0)
        self.assertAlmostEqual(r["pct_favorito_gana"], 50.0)


class TestModelos(unittest.TestCase):
    def test_elo_suma_cero_y_regresion(self):
        elo = modelos.EloNFL().procesar(JUEGOS)
        self.assertAlmostEqual(sum(elo.rating.values()), 1500 * len(elo.rating))
        antes = elo.rating["BUF"]
        elo._nueva_temporada(2026)
        self.assertAlmostEqual(elo.rating["BUF"], antes + (1500 - antes) / 3)

    def test_ratings(self):
        juegos = cargar_juegos(EJEMPLO)
        r = modelos.RatingsNFL().ajustar(juegos)
        self.assertAlmostEqual(sum(r.srs(e) for e in r.ofensa) / len(r.ofensa), 0, delta=1)
        pl, pv = r.puntos("KC", "BUF")
        self.assertTrue(10 < pl < 40 and 10 < pv < 40)

    def test_prediccion(self):
        juegos = cargar_juegos(EJEMPLO)
        elo, ratings = modelos.ajustar_modelos(juegos, 2025)
        a = modelos.predecir(elo, ratings, "KC", "BUF")
        b = modelos.predecir(elo, ratings, "BUF", "KC", neutral=True)
        self.assertTrue(0 < a["prob_local"] < 1)
        self.assertAlmostEqual(a["puntos_local"] - a["puntos_visitante"], a["margen"])
        self.assertAlmostEqual(modelos.prob_cubrir(0, 0), 0.5)
        self.assertEqual(modelos.moneyline_justa(0.5), "-100")
        self.assertIsNotNone(b)

    def test_simulacion(self):
        juegos = cargar_juegos(EJEMPLO)
        res, pendientes = modelos.simular_temporada(juegos, 2025, simulaciones=200, semilla=1)
        self.assertGreater(pendientes, 0)
        self.assertAlmostEqual(sum(r.get("playoffs", 0) for r in res.values()), 14)
        self.assertAlmostEqual(sum(r.get("division", 0) for r in res.values()), 8)

    def test_evaluar(self):
        m = modelos.evaluar(cargar_juegos(EJEMPLO), 2025)
        self.assertGreater(m["n"], 100)


class TestCarga(unittest.TestCase):
    def test_nflverse(self):
        contenido = (
            "game_id,season,game_type,week,gameday,away_team,away_score,home_team,home_score,location,overtime,"
            "spread_line,total_line,roof,temp,home_qb_name,away_qb_name\n"
            "2025_01_DAL_PHI,2025,REG,1,2025-09-04,DAL,20,PHI,24,Home,0,8.5,47.5,outdoors,75,Jalen Hurts,Dak Prescott\n"
            "2026_10_OAK_SD,2026,REG,10,2026-11-10,OAK,,SD,,Neutral,,,,,,,\n"
        )
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(contenido)
        f.close()
        self.addCleanup(Path(f.name).unlink)
        a, b = cargar_juegos(f.name)
        self.assertEqual((a.local, a.margen, a.linea, a.qb_local), ("PHI", 4, 8.5, "Jalen Hurts"))
        self.assertTrue(a.divisional)
        self.assertEqual((b.local, b.visitante), ("LAC", "LV"))  # abreviaturas antiguas normalizadas
        self.assertTrue(b.neutral and not b.jugado)


if __name__ == "__main__":
    unittest.main()


class TestBajas(unittest.TestCase):
    def test_bajas_con_snaps_anteriores(self):
        import sqlite3
        from analisis_deportivo.nfl import jugadores

        juegos = [J(1, "KC", "DEN", 27, 20, id="g1"), J(2, "DEN", "KC", 24, 21, id="g2"), J(3, "KC", "BUF", 20, 23, id="g3")]
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE nfl_snaps (game_id, player, position, offense_pct, defense_pct)")
        con.execute("CREATE TABLE nfl_lesiones (season, week, team, full_name, position, report_status)")
        con.executemany("INSERT INTO nfl_snaps VALUES (?,?,?,?,?)", [
            ("g1", "Travis Kelce", "TE", 0.9, 0), ("g1", "Xavier Worthy", "WR", 0.8, 0), ("g2", "Xavier Worthy", "WR", 0.6, 0),
            ("g3", "Xavier Worthy", "WR", 1.0, 0)])
        con.executemany("INSERT INTO nfl_lesiones VALUES (?,?,?,?,?,?)", [
            (2025, 1, "KC", "Xavier Worthy", "WR", "Out"),  # sin snaps anteriores: no cuenta
            (2025, 3, "KC", "Xavier Worthy Jr.", "WR", "Out"),  # solo cuentan g1 y g2, no el propio g3
            (2025, 3, "KC", "Travis Kelce", "TE", "Questionable"),
            (2025, 3, "BUF", "Josh Allen", "QB", "Out")])  # los QB los cubre el ajuste por QB titular
        bajas = jugadores.bajas_por_partido(con, juegos)
        self.assertNotIn(("g1", "KC"), bajas)
        self.assertEqual(bajas[("g3", "KC")][0], ("Xavier Worthy Jr.", "WR", "Out", 0.7))
        self.assertAlmostEqual(jugadores.ajuste(bajas[("g3", "KC")]), 0.7 * jugadores.PESOS["WR"])  # los TE no tienen peso
        self.assertNotIn(("g3", "BUF"), bajas)
        j = J(3, "KC", "BUF", None, None, bajas_local=bajas[("g3", "KC")])
        self.assertAlmostEqual(modelos.ajuste_juego(j), 0.7 * jugadores.PESOS["WR"])
