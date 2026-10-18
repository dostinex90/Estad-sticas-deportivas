"""Pruebas de humo: cada comando se ejecuta sin errores sobre los datos de ejemplo."""

import contextlib
import io
import unittest
from pathlib import Path

from analisis_deportivo.cli import main

DATOS = Path(__file__).parent.parent / "datos"
FUTBOL = ["tabla", "tabla --condicion descanso", "equipo Costa", "h2h Costa Norte", "liga", "lideres",
          "lideres corners -n 3", "ranking", "predecir Costa Norte --cuotas 2 3.4 3.8", "pronosticos",
          "evaluar --minimo 30", "equipos", "tabla --desde 2025-10-01"]
NFL = ["clasificacion", "clasificacion --vista playoffs", "equipo KC", "h2h KC DEN", "liga", "lideres",
       "ranking", "predecir KC BUF --linea 3 --total 47.5", "pronosticos", "simular -n 50 --semilla 1",
       "evaluar", "equipos", "liga -t 2024"]


class TestComandos(unittest.TestCase):
    def _ejecutar(self, deporte, comando, archivo):
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            main([deporte, *comando.split(), "--datos", str(DATOS / archivo)])
        return salida.getvalue()

    def test_futbol(self):
        for comando in FUTBOL:
            with self.subTest(comando=comando):
                self.assertTrue(self._ejecutar("futbol", comando, "futbol_ejemplo.csv"))

    def test_nfl(self):
        for comando in NFL:
            with self.subTest(comando=comando):
                self.assertTrue(self._ejecutar("nfl", comando, "nfl_ejemplo.csv"))


if __name__ == "__main__":
    unittest.main()
