"""Pruebas de la interfaz web: API sobre la base de datos y servidor HTTP."""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from analisis_deportivo import base

CONSULTAS = [
    ("futbol/opciones", {}), ("futbol/tabla", {"liga": "E0", "temporada": "2024-25"}),
    ("futbol/equipo", {"liga": "E0", "temporada": "2024-25", "equipo": "Arsenal"}),
    ("futbol/predecir", {"liga": "E0", "temporada": "2024-25", "local": "Arsenal", "visitante": "Chelsea"}),
    ("futbol/liga", {"liga": "SP1", "temporada": "2024-25"}), ("futbol/h2h", {"liga": "SP1", "a": "Betis", "b": "Sevilla"}),
    ("futbol/ranking", {"liga": "D1", "temporada": "2024-25"}), ("futbol/goleadores", {"torneo": "mundial", "temporada": "2022"}),
    ("futbol/pronosticos", {"liga": "SP1"}),
    ("nfl/opciones", {}), ("nfl/clasificacion", {"temporada": "2024"}), ("nfl/equipo", {"temporada": "2024", "equipo": "KC"}),
    ("nfl/predecir", {"temporada": "2024", "local": "KC", "visitante": "BUF", "linea": "3", "total": "47.5"}),
    ("nfl/ranking", {"temporada": "2024"}), ("nfl/estadisticas", {"temporada": "2024"}), ("nfl/liga", {"temporada": "2024"}),
    ("nfl/simular", {"temporada": "2024", "n": "200"}), ("nfl/pronosticos", {"temporada": "2024"}),
]


@unittest.skipUnless(base.disponible(), "requiere la base de datos")
class TestApi(unittest.TestCase):
    def test_rutas(self):
        from analisis_deportivo.web import api

        for ruta, consulta in CONSULTAS:
            with self.subTest(ruta=ruta):
                json.dumps(api.ejecutar(ruta, consulta))  # debe ser serializable

    def test_contenido(self):
        from analisis_deportivo.web import api

        tabla = api.ejecutar("futbol/tabla", {"liga": "E0", "temporada": "2024-25"})
        self.assertEqual(len(tabla["filas"]), 20)
        self.assertEqual(sum(f["pj"] for f in tabla["filas"]), 760)
        pred = api.ejecutar("futbol/predecir", {"liga": "E0", "temporada": "2024-25", "local": "Arsenal", "visitante": "Chelsea"})
        self.assertAlmostEqual(pred["p1"] + pred["px"] + pred["p2"], 1, places=2)
        clas = api.ejecutar("nfl/clasificacion", {"temporada": "2024"})
        self.assertEqual(sum(len(d["filas"]) for d in clas["divisiones"]), 32)
        self.assertEqual(len(clas["playoffs"][0]["dentro"]), 7)

    def test_errores(self):
        from analisis_deportivo.web import api

        with self.assertRaises(KeyError):
            api.ejecutar("nada", {})
        with self.assertRaises(ValueError):
            api.ejecutar("nfl/equipo", {"temporada": "1900", "equipo": "KC"})


@unittest.skipUnless(base.disponible(), "requiere la base de datos")
class TestServidor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from analisis_deportivo.web.servidor import Manejador

        cls.servidor = ThreadingHTTPServer(("127.0.0.1", 0), Manejador)
        cls.url = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()

    def _get(self, ruta):
        try:
            with urllib.request.urlopen(self.url + ruta) as r:
                return r.status, r.headers.get("Content-Type"), r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type"), e.read()

    def test_estaticos(self):
        for ruta, tipo in (("/", "text/html"), ("/app.js", "text/javascript"), ("/estilos.css", "text/css")):
            codigo, ctype, _ = self._get(ruta)
            self.assertEqual(codigo, 200)
            self.assertTrue(ctype.startswith(tipo))

    def test_no_sale_de_static(self):
        for ruta in ("/../api.py", "/%2e%2e/api.py", "/servidor.py", "/nada.html"):
            self.assertEqual(self._get(ruta)[0], 404, ruta)

    def test_api_y_errores(self):
        codigo, _, cuerpo = self._get("/api/nfl/opciones")
        self.assertEqual(codigo, 200)
        self.assertIn("temporadas", json.loads(cuerpo))
        codigo, _, cuerpo = self._get("/api/futbol/equipo?liga=E0&temporada=2024-25&equipo=Nadie")
        self.assertEqual(codigo, 400)
        self.assertIn("error", json.loads(cuerpo))
        self.assertEqual(self._get("/api/no-existe")[0], 404)


if __name__ == "__main__":
    unittest.main()
