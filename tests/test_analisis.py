import tempfile
import unittest
from datetime import date
from pathlib import Path

from analisis_deportivo import analisis
from analisis_deportivo.datos import Partido, cargar_partidos


def P(dia, local, visitante, gl, gv):
    return Partido(date(2026, 1, dia), local, visitante, gl, gv)


PARTIDOS = [
    P(1, "A", "B", 2, 0),
    P(2, "B", "C", 1, 1),
    P(3, "C", "A", 0, 3),
    P(4, "B", "A", 2, 1),
    P(5, "A", "C", 1, 1),
    P(6, "C", "B", 0, 2),
]


class TestTabla(unittest.TestCase):
    def test_orden_y_puntos(self):
        tabla = analisis.tabla_posiciones(PARTIDOS)
        self.assertEqual([s.equipo for s in tabla], ["A", "B", "C"])
        a = tabla[0]
        self.assertEqual((a.jugados, a.ganados, a.empatados, a.perdidos), (4, 2, 1, 1))
        self.assertEqual(a.puntos, 7)
        self.assertEqual(a.diferencia, 7 - 3)

    def test_condicion_local(self):
        stats = analisis.calcular_estadisticas(PARTIDOS, "local")
        self.assertEqual(stats["A"].jugados, 2)
        self.assertEqual(stats["A"].goles_favor, 3)

    def test_forma_y_racha(self):
        b = analisis.calcular_estadisticas(PARTIDOS)["B"]
        self.assertEqual(b.forma(), "PEGG")
        self.assertEqual(b.racha_actual(), ("G", 2))


class TestOtros(unittest.TestCase):
    def test_h2h(self):
        duelos, resumen = analisis.enfrentamientos_directos(PARTIDOS, "A", "B")
        self.assertEqual(len(duelos), 2)
        self.assertEqual(resumen, {"A": 1, "B": 1, "empates": 0})

    def test_resumen(self):
        r = analisis.resumen_liga(PARTIDOS)
        self.assertEqual(r["goles"], 14)
        self.assertAlmostEqual(r["pct_empate"], 100 * 2 / 6)
        self.assertEqual(r["mayor_goleada"], PARTIDOS[2])

    def test_prediccion_suma_uno(self):
        pr = analisis.predecir_partido(PARTIDOS, "A", "C")
        total = pr["prob_local"] + pr["prob_empate"] + pr["prob_visitante"]
        self.assertAlmostEqual(total, 1.0)
        self.assertGreater(pr["prob_local"], pr["prob_visitante"])


class TestCarga(unittest.TestCase):
    def _csv(self, contenido):
        f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(contenido)
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name

    def test_carga_ordena_por_fecha(self):
        ruta = self._csv(
            "fecha,local,visitante,goles_local,goles_visitante\n"
            "2026-01-05,A,B,1,0\n2026-01-01,B,A,2,2\n"
        )
        partidos = cargar_partidos(ruta)
        self.assertEqual(partidos[0].fecha, date(2026, 1, 1))

    def test_columnas_faltantes(self):
        with self.assertRaises(ValueError):
            cargar_partidos(self._csv("fecha,local\n2026-01-01,A\n"))

    def test_fila_invalida(self):
        ruta = self._csv("fecha,local,visitante,goles_local,goles_visitante\n2026-01-01,A,B,x,0\n")
        with self.assertRaisesRegex(ValueError, "Fila 2"):
            cargar_partidos(ruta)


if __name__ == "__main__":
    unittest.main()
