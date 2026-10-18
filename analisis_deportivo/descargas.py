"""Descarga de datos reales de partidos.

Fútbol:
  * football-data.co.uk: resultados con tiros, córners, faltas, tarjetas y cuotas.
  * openfootball (football.json): resultados y descanso, incluye partidos pendientes.
NFL:
  * nflverse (nfldata/games.csv): resultados, líneas de apuestas, clima, QB, etc.
"""

import csv
import io
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "datos" / "descargas"
EJEMPLO_FUTBOL = RAIZ / "datos" / "futbol_ejemplo.csv"
EJEMPLO_NFL = RAIZ / "datos" / "nfl_ejemplo.csv"

# nombre -> (código football-data.co.uk, código openfootball)
LIGAS = {
    "espana": ("SP1", "es.1"),
    "espana2": ("SP2", "es.2"),
    "inglaterra": ("E0", "en.1"),
    "inglaterra2": ("E1", "en.2"),
    "alemania": ("D1", "de.1"),
    "italia": ("I1", "it.1"),
    "francia": ("F1", "fr.1"),
    "portugal": ("P1", "pt.1"),
    "holanda": ("N1", "nl.1"),
    "belgica": ("B1", "be.1"),
    "turquia": ("T1", "tr.1"),
    "escocia": ("SC0", "sco.1"),
}

URL_FOOTBALL_DATA = "https://www.football-data.co.uk/mmz4281/{temporada}/{codigo}.csv"
URL_OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/football.json/master/{temporada}/{codigo}.json"
URL_NFLVERSE = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"


def _bajar(url):
    peticion = urllib.request.Request(url, headers={"User-Agent": "analisis-deportivo/1.0"})
    with urllib.request.urlopen(peticion, timeout=60) as r:
        return r.read()


def normalizar_temporada(texto):
    """Acepta '2025-26', '2025/26', '2526' o '2025' y devuelve ('2025-26', '2526')."""
    t = texto.replace("/", "-").strip()
    if "-" in t:
        inicio = int(t.split("-")[0])
    elif len(t) == 4 and int(t[:2]) + 1 == int(t[2:]) % 100:
        inicio = 2000 + int(t[:2])
    else:
        inicio = int(t)
    return f"{inicio}-{str(inicio + 1)[2:]}", f"{str(inicio)[2:]}{str(inicio + 1)[2:]}"


def descargar_futbol(liga, temporada, fuente="auto"):
    if liga not in LIGAS:
        raise ValueError(f"Liga desconocida {liga!r}. Opciones: {', '.join(LIGAS)}")
    larga, corta = normalizar_temporada(temporada)
    cod_fd, cod_of = LIGAS[liga]
    CARPETA.mkdir(parents=True, exist_ok=True)
    errores = []
    if fuente in ("auto", "football-data"):
        url = URL_FOOTBALL_DATA.format(temporada=corta, codigo=cod_fd)
        try:
            contenido = _bajar(url)
            destino = CARPETA / f"futbol_{liga}_{larga}.csv"
            destino.write_bytes(contenido)
            return destino, url, errores
        except (urllib.error.URLError, OSError) as e:
            errores.append(f"{url}: {e}")
    if fuente in ("auto", "openfootball"):
        url = URL_OPENFOOTBALL.format(temporada=larga, codigo=cod_of)
        try:
            contenido = _bajar(url)
            destino = CARPETA / f"futbol_{liga}_{larga}.json"
            destino.write_bytes(contenido)
            return destino, url, errores
        except (urllib.error.URLError, OSError) as e:
            errores.append(f"{url}: {e}")
    raise ValueError("No se pudo descargar:\n  " + "\n  ".join(errores))


def descargar_nfl(desde, hasta=None):
    """Descarga los partidos de nflverse de las temporadas [desde, hasta]."""
    contenido = _bajar(URL_NFLVERSE).decode("utf-8")
    lector = csv.DictReader(io.StringIO(contenido))
    filas = [f for f in lector if int(f["season"]) >= desde and (hasta is None or int(f["season"]) <= hasta)]
    if not filas:
        raise ValueError("No hay partidos en ese rango de temporadas.")
    CARPETA.mkdir(parents=True, exist_ok=True)
    temporadas = sorted({int(f["season"]) for f in filas})
    destino = CARPETA / f"nfl_{temporadas[0]}-{temporadas[-1]}.csv"
    with open(destino, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=lector.fieldnames)
        escritor.writeheader()
        escritor.writerows(filas)
    return destino, URL_NFLVERSE, len(filas)


def datos_recientes(prefijo, ejemplo):
    """Último archivo descargado con ese prefijo; si no hay ninguno, los datos de ejemplo."""
    if CARPETA.exists():
        candidatos = sorted(CARPETA.glob(prefijo + "*"), key=lambda p: p.stat().st_mtime)
        if candidatos:
            return candidatos[-1]
    return ejemplo
