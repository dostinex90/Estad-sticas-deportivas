"""Servidor web local: sirve la interfaz (carpeta static/) y la API JSON (/api/...)."""

import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import api

ESTATICOS = Path(__file__).resolve().parent / "static"
TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml"}


class Manejador(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):  # silencia el registro de cada petición
        pass

    def _responder(self, codigo, cuerpo, tipo):
        datos = cuerpo.encode("utf-8") if isinstance(cuerpo, str) else cuerpo
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def _json(self, codigo, objeto):
        self._responder(codigo, json.dumps(objeto, ensure_ascii=False), "application/json; charset=utf-8")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            consulta = {k: v[-1] for k, v in parse_qs(url.query).items()}
            try:
                self._json(200, api.ejecutar(url.path[len("/api/"):], consulta))
            except KeyError as e:
                self._json(404, {"error": f"Ruta desconocida: {e}"})
            except (ValueError, LookupError) as e:
                self._json(400, {"error": str(e)})
            except SystemExit as e:  # elegir_equipo termina con un mensaje cuando el nombre no existe
                self._json(400, {"error": str(e.code)})
            except Exception:  # noqa: BLE001 - el servidor no debe caerse por una petición
                traceback.print_exc()
                self._json(500, {"error": "Error interno. Revisa la terminal donde corre el servidor."})
            return
        # Solo se sirven archivos que existan directamente dentro de static/ (sin rutas relativas)
        nombre = "index.html" if url.path in ("", "/") else url.path.lstrip("/")
        archivo = ESTATICOS / nombre
        if "/" in nombre or ".." in nombre or archivo.suffix not in TIPOS or not archivo.is_file():
            self._responder(404, "No encontrado", "text/plain; charset=utf-8")
            return
        self._responder(200, archivo.read_bytes(), TIPOS[archivo.suffix])


def iniciar(host="127.0.0.1", puerto=8000, abrir=True):
    servidor = ThreadingHTTPServer((host, puerto), Manejador)
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{puerto}/"
    print(f"Interfaz disponible en {url}\nPulsa Ctrl+C para detenerla.")
    if abrir:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
