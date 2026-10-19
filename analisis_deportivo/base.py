"""Base de datos local (SQLite) con todos los partidos que se pueden recopilar de fuentes abiertas.

Tablas:
  futbol_partidos           Clubes: 38 ligas desde 2000 (resultado, descanso, tiros, córners,
                            faltas, tarjetas, cuotas y Elo previo al partido). La temporada en
                            curso se completa con openfootball, que también trae el calendario.
  futbol_selecciones        Selecciones nacionales desde 1872 (torneo, sede, campo neutral, penaltis).
  futbol_goleadores_selecciones  Goles de selecciones con autor, minuto, penalti y autogol.
  nfl_partidos              NFL desde 1999 (resultado, líneas de apuestas, clima, QB, entrenadores).
  nfl_estadisticas_equipo   Estadísticas de cada equipo en cada partido NFL (yardas, pérdidas,
                            sacks, EPA, penalizaciones, goles de campo...).
  fuentes                   Origen, licencia y fecha de cada carga.
"""

import csv
import difflib
import gzip
import io
import re
import shutil
import sqlite3
import unicodedata
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_BASE = RAIZ / "datos" / "base_deportiva.sqlite"
RUTA_COMPRIMIDA = RUTA_BASE.with_suffix(".sqlite.gz")

URL_CLUBES = "https://raw.githubusercontent.com/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv"
URL_SELECCIONES = "https://raw.githubusercontent.com/martj42/international_results/master/{}.csv"
URL_OPENFOOTBALL = "https://raw.githubusercontent.com/openfootball/football.json/master/{temporada}/{codigo}.json"
URL_NFL_PARTIDOS = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
URL_NFL_EQUIPOS = "https://github.com/nflverse/nflverse-data/releases/download/stats_team/stats_team_week_{}.csv"

# código -> (nombre, país, alias en español, código openfootball, calendario anual)
COMPETICIONES = {
    "E0": ("Premier League", "Inglaterra", "inglaterra", "en.1", False),
    "E1": ("Championship", "Inglaterra", "inglaterra2", "en.2", False),
    "E2": ("League One", "Inglaterra", "inglaterra3", "en.3", False),
    "E3": ("League Two", "Inglaterra", "inglaterra4", "en.4", False),
    "EC": ("National League", "Inglaterra", "inglaterra5", None, False),
    "SP1": ("LaLiga", "España", "espana", "es.1", False),
    "SP2": ("Segunda División", "España", "espana2", "es.2", False),
    "I1": ("Serie A", "Italia", "italia", "it.1", False),
    "I2": ("Serie B", "Italia", "italia2", "it.2", False),
    "D1": ("Bundesliga", "Alemania", "alemania", "de.1", False),
    "D2": ("2. Bundesliga", "Alemania", "alemania2", "de.2", False),
    "F1": ("Ligue 1", "Francia", "francia", "fr.1", False),
    "F2": ("Ligue 2", "Francia", "francia2", "fr.2", False),
    "N1": ("Eredivisie", "Países Bajos", "holanda", "nl.1", False),
    "P1": ("Primeira Liga", "Portugal", "portugal", "pt.1", False),
    "B1": ("Pro League", "Bélgica", "belgica", "be.1", False),
    "T1": ("Süper Lig", "Turquía", "turquia", "tr.1", False),
    "G1": ("Super League", "Grecia", "grecia", "gr.1", False),
    "SC0": ("Premiership", "Escocia", "escocia", "sco.1", False),
    "SC1": ("Championship", "Escocia", "escocia2", None, False),
    "SC2": ("League One", "Escocia", "escocia3", None, False),
    "SC3": ("League Two", "Escocia", "escocia4", None, False),
    "AUT": ("Bundesliga", "Austria", "austria", "at.1", False),
    "SUI": ("Super League", "Suiza", "suiza", "ch.1", False),
    "DEN": ("Superliga", "Dinamarca", "dinamarca", "dk.1", False),
    "POL": ("Ekstraklasa", "Polonia", "polonia", "pl.1", False),
    "ROM": ("Liga 1", "Rumanía", "rumania", "ro.1", False),
    "RUS": ("Premier Liga", "Rusia", "rusia", "ru.1", False),
    "MEX": ("Liga MX", "México", "mexico", "mx.1", False),
    "ARG": ("Liga Profesional", "Argentina", "argentina", "ar.1", True),
    "BRA": ("Série A", "Brasil", "brasil", "br.1", True),
    "USA": ("MLS", "Estados Unidos", "mls", "us.1", True),
    "JAP": ("J1 League", "Japón", "japon", "jp.1", True),
    "CHN": ("Super League", "China", "china", "cn.1", True),
    "SWE": ("Allsvenskan", "Suecia", "suecia", "se.1", True),
    "NOR": ("Eliteserien", "Noruega", "noruega", "no.1", True),
    "FIN": ("Veikkausliiga", "Finlandia", "finlandia", "fi.1", True),
    "IRL": ("Premier Division", "Irlanda", "irlanda", "ie.1", True),
}

# Alias en español para torneos de selecciones
TORNEOS = {
    "mundial": "FIFA World Cup",
    "eliminatorias": "FIFA World Cup qualification",
    "eurocopa": "UEFA Euro",
    "copa-america": "Copa América",
    "nations-league": "UEFA Nations League",
    "copa-africa": "African Cup of Nations",
    "copa-asia": "AFC Asian Cup",
    "copa-oro": "Gold Cup",
    "amistosos": "Friendly",
}

LICENCIAS = {
    "clubes": "Football-Data.co.uk y ClubElo, recopilado por xgabora/Club-Football-Match-Data-2000-2025",
    "openfootball": "openfootball/football.json (dominio público, CC0)",
    "football_data": "Football-Data.co.uk (resultados, estadísticas y cuotas)",
    "selecciones": "martj42/international_results (CC0)",
    "nfl_partidos": "nflverse/nfldata (Lee Sharpe)",
    "nfl_equipos": "nflverse/nflverse-data (CC-BY 4.0)",
}


def temporada_de(fecha, anual=False):
    """'2025-26' para ligas europeas (empiezan en julio) o '2025' para ligas de calendario anual."""
    if anual:
        return str(fecha.year)
    # En 2020 la pandemia alargó las temporadas 2019-20 hasta agosto
    corte = date(fecha.year, 8, 15) if fecha.year == 2020 else date(fecha.year, 7, 1)
    inicio = fecha.year if fecha >= corte else fecha.year - 1
    return f"{inicio}-{str(inicio + 1)[2:]}"


def resolver_competicion(texto):
    """Acepta código (SP1), alias en español (espana) o nombre (LaLiga)."""
    t = texto.strip()
    if t.upper() in COMPETICIONES:
        return t.upper()
    for codigo, (nombre, pais, alias, *_) in COMPETICIONES.items():
        if t.lower() in (alias, nombre.lower(), f"{nombre} {pais}".lower()):
            return codigo
    raise ValueError(f"Competición desconocida {texto!r}. Usa el comando 'ligas' para ver las disponibles.")


def resolver_torneo(texto):
    return TORNEOS.get(texto.strip().lower(), texto.strip())


# ── Descarga ──────────────────────────────────────────────────────────────────

def _bajar(url):
    peticion = urllib.request.Request(url, headers={"User-Agent": "analisis-deportivo/1.0"})
    with urllib.request.urlopen(peticion, timeout=120) as r:
        return r.read()


def _csv(url):
    return list(csv.DictReader(io.StringIO(_bajar(url).decode("utf-8-sig"))))


def _num(v, tipo=float):
    if v is None:
        return None
    v = v.strip()
    if v in ("", "NA", "nan"):
        return None
    try:
        return tipo(float(v)) if tipo is int else float(v)
    except ValueError:
        return None


ESQUEMA = """
CREATE TABLE IF NOT EXISTS fuentes (tabla TEXT PRIMARY KEY, origen TEXT, filas INTEGER, actualizado TEXT);
CREATE TABLE IF NOT EXISTS futbol_partidos (
    competicion TEXT, temporada TEXT, fecha TEXT, hora TEXT, local TEXT, visitante TEXT,
    goles_local INTEGER, goles_visitante INTEGER, descanso_local INTEGER, descanso_visitante INTEGER,
    tiros_local INTEGER, tiros_visitante INTEGER, tiros_puerta_local INTEGER, tiros_puerta_visitante INTEGER,
    faltas_local INTEGER, faltas_visitante INTEGER, corners_local INTEGER, corners_visitante INTEGER,
    amarillas_local INTEGER, amarillas_visitante INTEGER, rojas_local INTEGER, rojas_visitante INTEGER,
    cuota_local REAL, cuota_empate REAL, cuota_visitante REAL,
    cuota_max_local REAL, cuota_max_empate REAL, cuota_max_visitante REAL,
    cuota_mas_2_5 REAL, cuota_menos_2_5 REAL,
    elo_local REAL, elo_visitante REAL, fuente TEXT);
CREATE INDEX IF NOT EXISTS ix_fp ON futbol_partidos (competicion, temporada, fecha);
CREATE TABLE IF NOT EXISTS futbol_selecciones (
    fecha TEXT, local TEXT, visitante TEXT, goles_local INTEGER, goles_visitante INTEGER,
    torneo TEXT, ciudad TEXT, pais TEXT, neutral INTEGER, ganador_penaltis TEXT);
CREATE INDEX IF NOT EXISTS ix_fs ON futbol_selecciones (torneo, fecha);
CREATE TABLE IF NOT EXISTS futbol_goleadores_selecciones (
    fecha TEXT, local TEXT, visitante TEXT, equipo TEXT, goleador TEXT, minuto INTEGER,
    autogol INTEGER, penalti INTEGER);
CREATE INDEX IF NOT EXISTS ix_fg ON futbol_goleadores_selecciones (equipo, goleador);
"""


def _clubes(con, avisar):
    filas = _csv(URL_CLUBES)
    datos = []
    for f in filas:
        codigo = f["Division"].strip()
        if codigo not in COMPETICIONES or not f["MatchDate"]:
            continue
        fecha = date.fromisoformat(f["MatchDate"])
        i = lambda c: _num(f.get(c), int)  # noqa: E731
        r = lambda c: _num(f.get(c))  # noqa: E731
        datos.append((
            codigo, temporada_de(fecha, COMPETICIONES[codigo][4]), f["MatchDate"], f["MatchTime"] or None,
            f["HomeTeam"].strip(), f["AwayTeam"].strip(), i("FTHome"), i("FTAway"), i("HTHome"), i("HTAway"),
            i("HomeShots"), i("AwayShots"), i("HomeTarget"), i("AwayTarget"), i("HomeFouls"), i("AwayFouls"),
            i("HomeCorners"), i("AwayCorners"), i("HomeYellow"), i("AwayYellow"), i("HomeRed"), i("AwayRed"),
            r("OddHome"), r("OddDraw"), r("OddAway"), r("MaxHome"), r("MaxDraw"), r("MaxAway"),
            r("Over25"), r("Under25"), r("HomeElo"), r("AwayElo"), "clubes",
        ))
    con.executemany(f"INSERT INTO futbol_partidos VALUES ({','.join('?' * 33)})", datos)
    avisar(f"  Clubes: {len(datos):,} partidos de {len({d[0] for d in datos})} competiciones")
    return len(datos)


URL_FD_TEMPORADA = "https://www.football-data.co.uk/mmz4281/{temporada}/{codigo}.csv"
URL_FD_NUEVAS = "https://www.football-data.co.uk/new/{codigo}.csv"
NUEVAS_FD = {"ARG", "BRA", "USA", "MEX", "JAP", "CHN", "SWE", "NOR", "FIN", "IRL", "AUT", "SUI", "DEN", "POL", "ROM", "RUS"}


def _texto_csv(contenido):
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return contenido.decode("latin-1", "replace")


def _fecha_fd(texto):
    for formato in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto.strip(), formato).date()
        except ValueError:
            pass
    return None


def _fila_fd(codigo, f):
    """Convierte una fila de football-data.co.uk (ligas principales o 'new') en una fila de futbol_partidos."""
    fecha = _fecha_fd(f.get("Date") or "")
    local = (f.get("HomeTeam") or f.get("Home") or "").strip()
    visitante = (f.get("AwayTeam") or f.get("Away") or "").strip()
    if not fecha or not local or not visitante:
        return None
    i = lambda c: _num(f.get(c), int)  # noqa: E731
    r = lambda *cs: next((v for v in (_num(f.get(c)) for c in cs) if v), None)  # noqa: E731
    return (
        codigo, temporada_de(fecha, COMPETICIONES[codigo][4]), fecha.isoformat(), (f.get("Time") or "").strip() or None,
        local, visitante, i("FTHG") if f.get("FTHG") is not None else i("HG"), i("FTAG") if f.get("FTAG") is not None else i("AG"),
        i("HTHG"), i("HTAG"), i("HS"), i("AS"), i("HST"), i("AST"), i("HF"), i("AF"), i("HC"), i("AC"),
        i("HY"), i("AY"), i("HR"), i("AR"),
        r("AvgH", "BbAvH", "AvgCH", "B365H", "PSH"), r("AvgD", "BbAvD", "AvgCD", "B365D", "PSD"),
        r("AvgA", "BbAvA", "AvgCA", "B365A", "PSA"), r("MaxH", "BbMxH", "MaxCH"), r("MaxD", "BbMxD", "MaxCD"),
        r("MaxA", "BbMxA", "MaxCA"), r("Avg>2.5", "BbAv>2.5"), r("Avg<2.5", "BbAv<2.5"), None, None, "football-data",
    )


def _temporadas_a_completar(con, codigo, actual):
    """Temporadas que faltan o están incompletas en la base, más la actual y la anterior."""
    filas = con.execute("SELECT temporada, local, visitante, goles_local FROM futbol_partidos WHERE competicion = ?",
                        (codigo,)).fetchall()
    por_temp = defaultdict(Counter)
    for temp, l, v, g in filas:
        if g is not None:
            por_temp[temp][l] += 1
            por_temp[temp][v] += 1
    inicio = int(min(por_temp, default=actual)[:4])
    fin = int(actual[:4])
    resultado = []
    for anio in range(min(inicio, 2000), fin + 1):
        temp = f"{anio}-{str(anio + 1)[2:]}"
        conteo = por_temp.get(temp)
        completa = conteo and len(set(conteo.values())) == 1 and min(conteo.values()) >= 2 * (len(conteo) - 1)
        if not completa or anio >= fin - 1:
            resultado.append(anio)
    return resultado


def _football_data(con, avisar, hoy):
    """Completa la base con football-data.co.uk: la temporada en curso (se actualiza dos veces por semana,
    con estadísticas y cuotas) y las temporadas que faltan o están incompletas. Empareja cada partido por
    (competición, temporada, local, visitante): si ya existe sin resultado lo completa; si no existe lo añade."""
    columnas = ("competicion, temporada, fecha, hora, local, visitante, goles_local, goles_visitante, descanso_local, "
                "descanso_visitante, tiros_local, tiros_visitante, tiros_puerta_local, tiros_puerta_visitante, faltas_local, "
                "faltas_visitante, corners_local, corners_visitante, amarillas_local, amarillas_visitante, rojas_local, "
                "rojas_visitante, cuota_local, cuota_empate, cuota_visitante, cuota_max_local, cuota_max_empate, "
                "cuota_max_visitante, cuota_mas_2_5, cuota_menos_2_5, elo_local, elo_visitante, fuente")
    descargas, añadidos, completados, fallos = 0, 0, 0, 0

    # Nombre canónico de cada club (la variante más usada) para no duplicar partidos por grafías distintas
    usos = defaultdict(Counter)
    for columna in ("local", "visitante"):
        for nombre, n in con.execute(f"SELECT {columna}, COUNT(*) FROM futbol_partidos GROUP BY 1"):
            usos[_clave_nombre(nombre)][nombre] += n
    canonico = {k: c.most_common(1)[0][0] for k, c in usos.items()}

    def incorporar(codigo, filas, clave_fecha):
        nonlocal añadidos, completados
        filas = [f[:4] + (canonico.get(_clave_nombre(f[4]), f[4]), canonico.get(_clave_nombre(f[5]), f[5])) + f[6:]
                 for f in filas if f]
        existentes = {}
        for rowid, temp, fecha, l, v, g in con.execute(
                "SELECT rowid, temporada, fecha, local, visitante, goles_local FROM futbol_partidos WHERE competicion = ?", (codigo,)):
            existentes[(temp, fecha if clave_fecha else "", l, v)] = (rowid, g)
        for fila in filas:
            if not fila:
                continue
            clave = (fila[1], fila[2] if clave_fecha else "", fila[4], fila[5])
            previo = existentes.get(clave)
            if previo is None:
                con.execute(f"INSERT INTO futbol_partidos ({columnas}) VALUES ({','.join('?' * 33)})", fila)
                existentes[clave] = (None, fila[6])
                añadidos += 1
            elif previo[1] is None and fila[6] is not None and previo[0] is not None:
                con.execute(f"UPDATE futbol_partidos SET ({columnas}) = ({','.join('?' * 33)}) WHERE rowid = ?",
                            (*fila, previo[0]))
                completados += 1

    for codigo, info in COMPETICIONES.items():
        try:
            if codigo in NUEVAS_FD:
                try:
                    contenido = _bajar(URL_FD_NUEVAS.format(codigo=codigo))
                except urllib.error.HTTPError:
                    continue
                descargas += 1
                filas = [_fila_fd(codigo, f) for f in csv.DictReader(io.StringIO(_texto_csv(contenido)))]
                incorporar(codigo, filas, clave_fecha=True)  # ligas con más de dos cruces por temporada
                continue
            for anio in _temporadas_a_completar(con, codigo, temporada_de(hoy)):
                url = URL_FD_TEMPORADA.format(temporada=f"{anio % 100:02d}{(anio + 1) % 100:02d}", codigo=codigo)
                try:
                    contenido = _bajar(url)
                except urllib.error.HTTPError:
                    continue  # la liga no existe en esa temporada
                descargas += 1
                filas = [_fila_fd(codigo, f) for f in csv.DictReader(io.StringIO(_texto_csv(contenido)))]
                incorporar(codigo, filas, clave_fecha=codigo.startswith("SC"))  # en Escocia se repiten cruces
        except (urllib.error.URLError, OSError, ValueError) as e:
            fallos += 1
            if fallos == 1:
                avisar(f"  football-data.co.uk no disponible ({e}); se sigue con las demás fuentes")
            if fallos >= 3:
                break
    avisar(f"  football-data.co.uk: {descargas} archivos, +{añadidos} partidos nuevos, {completados} resultados completados")
    return añadidos + completados


def _mapear_nombres(of_partidos, existentes):
    """Aprende la equivalencia de nombres openfootball → football-data con los partidos que
    aparecen en ambas fuentes (misma fecha y mismo marcador)."""
    por_clave = defaultdict(list)
    for fecha, l, v, gl, gv in existentes:
        por_clave[(fecha, gl, gv)].append((l, v))
    votos = defaultdict(Counter)
    for fecha, l, v, gl, gv in of_partidos:
        candidatos = por_clave.get((fecha, gl, gv), [])
        if len(candidatos) == 1:
            votos[l][candidatos[0][0]] += 1
            votos[v][candidatos[0][1]] += 1
    mapa = {nombre: c.most_common(1)[0][0] for nombre, c in votos.items()}
    # Segunda pasada: si en un partido ya se conoce un equipo, el rival de ese día es el otro
    por_fecha = defaultdict(list)
    for fecha, l, v, *_ in existentes:
        por_fecha[fecha].append((l, v))
    for _ in range(3):
        for fecha, l, v, *_ in of_partidos:
            for conocido, desconocido, es_local in ((l, v, True), (v, l, False)):
                if conocido in mapa and desconocido not in mapa:
                    for el, ev in por_fecha.get(fecha, []):
                        if (el if es_local else ev) == mapa[conocido]:
                            mapa[desconocido] = ev if es_local else el
    # Última pasada: parecido de nombres entre los equipos que quedan sin pareja
    libres = ({l for _, l, *_ in existentes} | {v for _, _, v, *_ in existentes}) - set(mapa.values())
    for nombre in sorted({n for p in of_partidos for n in p[1:3]} - set(mapa)):
        candidato = max(libres, key=lambda e: _parecido(nombre, e), default=None)
        if candidato and _parecido(nombre, candidato) >= 0.6:
            mapa[nombre] = candidato
            libres.discard(candidato)
    return mapa


def _normalizar_nombre(nombre):
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower()
    palabras = [w for w in re.split(r"[^a-z]+", sin_tildes) if w and w not in
                ("fc", "cf", "sv", "tsg", "vfl", "vfb", "sc", "ac", "ss", "us", "afc", "cd", "ud", "rcd", "club", "de", "and")]
    return " ".join(palabras)


def _parecido(a, b):
    a, b = _normalizar_nombre(a), _normalizar_nombre(b)
    if a and b and (a in b or b in a):
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _openfootball_actual(con, avisar, hoy):
    """Añade la temporada en curso (resultados recientes y calendario pendiente) desde openfootball."""
    total = 0
    for codigo, (nombre, _, _, cod_of, anual) in COMPETICIONES.items():
        if not cod_of:
            continue
        temporada = temporada_de(hoy, anual)
        try:
            datos = __import__("json").loads(_bajar(URL_OPENFOOTBALL.format(temporada=temporada, codigo=cod_of)))
        except (urllib.error.URLError, OSError, ValueError):
            continue
        partidos = []
        for m in datos.get("matches", []):
            marcador = m.get("score") or {}
            if isinstance(marcador, list):
                marcador = {"ft": marcador}
            ft, ht = marcador.get("ft"), marcador.get("ht")
            partidos.append((m["date"], m["team1"], m["team2"], ft[0] if ft else None, ft[1] if ft else None,
                             ht[0] if ht else None, ht[1] if ht else None, m.get("time")))
        if not partidos:
            continue
        existentes = con.execute(
            "SELECT fecha, local, visitante, goles_local, goles_visitante FROM futbol_partidos "
            "WHERE competicion = ? AND temporada = ?", (codigo, temporada)).fetchall()
        mapa = _mapear_nombres([p[:5] for p in partidos if p[3] is not None], [e for e in existentes if e[3] is not None])
        # En una liga a doble vuelta cada pareja local-visitante se juega una vez por temporada
        pendientes_previos = {(e[1], e[2]) for e in existentes if e[3] is None}
        ya = {(e[1], e[2]) for e in existentes} | {(e[0], e[1]) for e in existentes}
        nuevos = []
        for p in partidos:
            l, v = mapa.get(p[1], p[1]), mapa.get(p[2], p[2])
            if (l, v) in pendientes_previos and p[3] is not None:  # otra fuente lo tiene sin resultado
                con.execute("UPDATE futbol_partidos SET goles_local = ?, goles_visitante = ?, descanso_local = ?, "
                            "descanso_visitante = ? WHERE competicion = ? AND temporada = ? AND local = ? AND visitante = ?",
                            (p[3], p[4], p[5], p[6], codigo, temporada, l, v))
            elif (l, v) not in ya and (p[0], l) not in ya:
                nuevos.append(p)
        for fecha, l, v, gl, gv, hl, hv, hora in nuevos:
            con.execute(
                "INSERT INTO futbol_partidos (competicion, temporada, fecha, hora, local, visitante, goles_local, "
                "goles_visitante, descanso_local, descanso_visitante, fuente) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (codigo, temporada, fecha, hora, mapa.get(l, l), mapa.get(v, v), gl, gv, hl, hv, "openfootball"))
        sin_mapear = {n for p in nuevos for n in p[1:3]} - set(mapa)
        aviso = f" (nombres sin equivalencia: {', '.join(sorted(sin_mapear))})" if sin_mapear and existentes else ""
        avisar(f"  {nombre} ({codigo}) {temporada}: +{len(nuevos)} partidos de openfootball{aviso}")
        total += len(nuevos)
    return total


def _clave_nombre(nombre):
    """Clave que ignora signos, mayúsculas y tildes ("Nott'm Forest" y "Nottm Forest" coinciden)."""
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode().lower())


def _unificar_nombres(con, avisar):
    """La fuente escribe a veces un mismo club de dos formas ("Nott'm Forest" y "Nottm Forest").
    Se unifican las variantes que solo difieren en signos, mayúsculas o tildes con la más frecuente."""
    clave = _clave_nombre
    variantes = defaultdict(Counter)
    for columna in ("local", "visitante"):
        for nombre, n in con.execute(f"SELECT {columna}, COUNT(*) FROM futbol_partidos GROUP BY 1"):
            variantes[clave(nombre)][nombre] += n
    cambios = 0
    for conteo in variantes.values():
        if len(conteo) < 2:
            continue
        principal = conteo.most_common(1)[0][0]
        for nombre in conteo:
            if nombre != principal:
                for columna in ("local", "visitante"):
                    cambios += con.execute(f"UPDATE futbol_partidos SET {columna} = ? WHERE {columna} = ?",
                                           (principal, nombre)).rowcount
    if cambios:
        avisar(f"  Nombres de clubes unificados en {cambios} partidos")


def _selecciones(con, avisar):
    resultados = _csv(URL_SELECCIONES.format("results"))
    penaltis = {(f["date"], f["home_team"], f["away_team"]): f["winner"] for f in _csv(URL_SELECCIONES.format("shootouts"))}
    datos = [(f["date"], f["home_team"], f["away_team"], _num(f["home_score"], int), _num(f["away_score"], int),
              f["tournament"], f["city"], f["country"], int(f["neutral"].upper() == "TRUE"),
              penaltis.get((f["date"], f["home_team"], f["away_team"]))) for f in resultados]
    con.executemany("INSERT INTO futbol_selecciones VALUES (?,?,?,?,?,?,?,?,?,?)", datos)
    goles = [(f["date"], f["home_team"], f["away_team"], f["team"], f["scorer"], _num(f["minute"], int),
              int(f["own_goal"].upper() == "TRUE"), int(f["penalty"].upper() == "TRUE"))
             for f in _csv(URL_SELECCIONES.format("goalscorers"))]
    con.executemany("INSERT INTO futbol_goleadores_selecciones VALUES (?,?,?,?,?,?,?,?)", goles)
    avisar(f"  Selecciones: {len(datos):,} partidos y {len(goles):,} goles con autor")
    return len(datos), len(goles)


def _valor(v):
    """Convierte texto numérico en número para que SQLite compare y ordene correctamente."""
    if v is None or v in ("", "NA"):
        return None
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def _tabla_desde_filas(con, tabla, filas, columnas):
    con.execute(f'DROP TABLE IF EXISTS {tabla}')
    con.execute(f'CREATE TABLE {tabla} ({", ".join(f"[{c}]" for c in columnas)})')
    con.executemany(f'INSERT INTO {tabla} VALUES ({",".join("?" * len(columnas))})',
                    [[_valor(f.get(c)) for c in columnas] for f in filas])


def _nfl(con, avisar, hoy):
    partidos = _csv(URL_NFL_PARTIDOS)
    columnas = list(partidos[0].keys())
    _tabla_desde_filas(con, "nfl_partidos", partidos, columnas)
    con.execute("CREATE INDEX ix_np ON nfl_partidos (season, week)")
    avisar(f"  NFL: {len(partidos):,} partidos ({partidos[0]['season']}-{partidos[-1]['season']})")

    filas, columnas = [], None
    for temporada in range(1999, hoy.year + 1):
        try:
            datos = _csv(URL_NFL_EQUIPOS.format(temporada))
        except (urllib.error.URLError, OSError):
            continue
        if datos:
            columnas = columnas or list(datos[0].keys())
            filas.extend(datos)
    if filas:
        _tabla_desde_filas(con, "nfl_estadisticas_equipo", filas, columnas)
        con.execute("CREATE INDEX ix_ne ON nfl_estadisticas_equipo (season, team)")
        avisar(f"  NFL: {len(filas):,} registros de estadísticas de equipo por partido")
    return len(partidos), len(filas)


def recopilar(ruta=RUTA_BASE, avisar=print, comprimir=True):
    """Descarga todas las fuentes y (re)construye la base de datos."""
    hoy = date.today()
    temporal = Path(str(ruta) + ".nuevo")
    temporal.unlink(missing_ok=True)
    con = sqlite3.connect(temporal)
    con.executescript(ESQUEMA)
    registrar = lambda tabla, origen, n: con.execute(  # noqa: E731
        "INSERT OR REPLACE INTO fuentes VALUES (?,?,?,?)", (tabla, origen, n, datetime.now().isoformat(timespec="seconds")))

    avisar("Descargando partidos de clubes...")
    registrar("futbol_partidos", LICENCIAS["clubes"], _clubes(con, avisar))
    avisar("Completando con football-data.co.uk (temporada en curso y huecos históricos)...")
    n = _football_data(con, avisar, hoy)
    registrar("futbol_partidos (football-data.co.uk)", LICENCIAS["football_data"], n)
    avisar("Completando la temporada en curso con openfootball...")
    n = _openfootball_actual(con, avisar, hoy)
    registrar("futbol_partidos (temporada en curso)", LICENCIAS["openfootball"], n)
    _unificar_nombres(con, avisar)
    avisar("Descargando partidos de selecciones...")
    n_sel, n_gol = _selecciones(con, avisar)
    registrar("futbol_selecciones", LICENCIAS["selecciones"], n_sel)
    registrar("futbol_goleadores_selecciones", LICENCIAS["selecciones"], n_gol)
    avisar("Descargando NFL...")
    n_p, n_e = _nfl(con, avisar, hoy)
    registrar("nfl_partidos", LICENCIAS["nfl_partidos"], n_p)
    registrar("nfl_estadisticas_equipo", LICENCIAS["nfl_equipos"], n_e)
    con.commit()
    con.execute("VACUUM")
    con.close()
    temporal.replace(ruta)
    if comprimir:
        with open(ruta, "rb") as origen, gzip.open(RUTA_COMPRIMIDA, "wb", compresslevel=9) as destino:
            shutil.copyfileobj(origen, destino)
    return ruta


# ── Consulta ──────────────────────────────────────────────────────────────────

def disponible():
    return RUTA_BASE.exists() or RUTA_COMPRIMIDA.exists()


def conectar(ruta=None):
    """Abre la base; si solo existe la versión comprimida del repositorio, la descomprime antes."""
    ruta = Path(ruta) if ruta else RUTA_BASE
    if not ruta.exists() and ruta == RUTA_BASE and RUTA_COMPRIMIDA.exists():
        with gzip.open(RUTA_COMPRIMIDA, "rb") as origen, open(ruta, "wb") as destino:
            shutil.copyfileobj(origen, destino)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe la base de datos {ruta}. Créala con: python3 -m analisis_deportivo recopilar")
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    return con


def es_base(ruta):
    return str(ruta).endswith((".sqlite", ".db"))


def resumen(con):
    """Resumen del contenido para el comando 'base'."""
    r = {"fuentes": [dict(f) for f in con.execute("SELECT * FROM fuentes")]}
    r["competiciones"] = con.execute(
        "SELECT competicion, COUNT(*) n, MIN(temporada) desde, MAX(temporada) hasta, "
        "SUM(goles_local IS NULL) pendientes, SUM(tiros_local IS NOT NULL) con_tiros, "
        "SUM(cuota_local IS NOT NULL) con_cuotas FROM futbol_partidos GROUP BY competicion ORDER BY n DESC").fetchall()
    r["torneos"] = con.execute(
        "SELECT torneo, COUNT(*) n, MIN(fecha) desde, MAX(fecha) hasta FROM futbol_selecciones "
        "GROUP BY torneo ORDER BY n DESC LIMIT 25").fetchall()
    r["n_torneos"] = con.execute("SELECT COUNT(DISTINCT torneo) FROM futbol_selecciones").fetchone()[0]
    r["nfl"] = con.execute("SELECT COUNT(*), MIN(season), MAX(season), SUM(home_score IS NULL) FROM nfl_partidos").fetchone()
    try:
        r["nfl_estadisticas"] = con.execute("SELECT COUNT(*), MIN(season), MAX(season) FROM nfl_estadisticas_equipo").fetchone()
    except sqlite3.OperationalError:
        r["nfl_estadisticas"] = None
    return r
