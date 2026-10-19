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
  nba_partidos              NBA desde 2001-02 (resultado, prórrogas, fase, sede) y calendario pendiente.
  nba_estadisticas_equipo   Estadísticas de cada equipo en cada partido NBA (tiros, rebotes,
                            asistencias, pérdidas...).
  nba_jugadores_partido     Minutos y valoración (Game Score) de cada jugador NBA que jugó cada partido.
  nba_jugadores             Nombre de cada jugador NBA.
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
URL_NBA_PARTIDOS = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nba_schedules/nba_schedule_{}.csv"
URL_NBA_EQUIPOS = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nba_team_boxscores/team_box_{}.csv"
URL_NBA_JUGADORES = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nba_player_boxscores/player_box_{}.csv"
PRIMERA_NBA_JUGADORES = 2012  # 2011-12: da historial a las temporadas de validación del modelo (2021-22 en adelante)

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
    "nba": "sportsdataverse/hoopR-nba-data (datos de ESPN)",
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
CREATE TABLE IF NOT EXISTS nba_partidos (
    id TEXT, temporada INTEGER, tipo TEXT, ronda TEXT, fecha TEXT, local TEXT, visitante TEXT,
    puntos_local INTEGER, puntos_visitante INTEGER, prorrogas INTEGER, neutral INTEGER, estadio TEXT, ciudad TEXT);
CREATE INDEX IF NOT EXISTS ix_nbp ON nba_partidos (temporada, fecha);
CREATE TABLE IF NOT EXISTS nba_estadisticas_equipo (
    id TEXT, temporada INTEGER, tipo TEXT, fecha TEXT, equipo TEXT, rival TEXT, local INTEGER, puntos INTEGER,
    tiros_campo INTEGER, intentos_campo INTEGER, triples INTEGER, intentos_triple INTEGER,
    tiros_libres INTEGER, intentos_libres INTEGER, rebotes_ofensivos INTEGER, rebotes_defensivos INTEGER,
    asistencias INTEGER, robos INTEGER, tapones INTEGER, perdidas INTEGER, faltas INTEGER,
    puntos_pintura INTEGER, puntos_contraataque INTEGER);
CREATE INDEX IF NOT EXISTS ix_nbe ON nba_estadisticas_equipo (temporada, equipo);
CREATE TABLE IF NOT EXISTS nba_jugadores_partido (id INTEGER, equipo TEXT, jugador INTEGER, minutos INTEGER, valoracion REAL);
CREATE TABLE IF NOT EXISTS nba_jugadores (jugador INTEGER PRIMARY KEY, nombre TEXT);
"""


def _girar_fecha(fecha):
    """Intercambia día y mes (el 4 de enero pasa a ser el 1 de abril) si el día puede ser un mes."""
    return date(fecha.year, fecha.day, fecha.month) if fecha.day <= 12 else fecha


def choques_calendario(partidos):
    """Veces que un equipo juega dos partidos el mismo día o en días seguidos.
    `partidos` son tuplas (fecha, temporada, local, visitante) con la fecha como date."""
    por_equipo = defaultdict(list)
    for fecha, temporada, local, visitante in partidos:
        por_equipo[(temporada, local)].append(fecha)
        por_equipo[(temporada, visitante)].append(fecha)
    total = 0
    for fechas in por_equipo.values():
        fechas.sort()
        total += sum(1 for a, b in zip(fechas, fechas[1:]) if (b - a).days < 2)
    return total


def fechas_intercambiadas(partidos):
    """True si las fechas con día ≤ 12 tienen el día y el mes cambiados. Le pasa a la fuente de clubes
    con las ligas 'new' (MLS, Brasil, Suecia...): "LA Galaxy - Portland" del 31-3-2019 aparece el
    4-1-2019. Se nota en que, con esas fechas, los equipos juegan a menudo dos días seguidos;
    al girarlas el calendario vuelve a ser normal."""
    actuales = choques_calendario(partidos)
    girados = choques_calendario([(_girar_fecha(f), t, l, v) for f, t, l, v in partidos])
    return actuales > 2 * girados + 5


def _clubes(con, avisar):
    filas = _csv(URL_CLUBES)
    por_liga = defaultdict(list)
    for f in filas:
        codigo = f["Division"].strip()
        if codigo in COMPETICIONES and f["MatchDate"]:
            por_liga[codigo].append(f)
    datos, corregidas = [], []
    for codigo, filas_liga in por_liga.items():
        anual = COMPETICIONES[codigo][4]
        fechas = [date.fromisoformat(f["MatchDate"]) for f in filas_liga]
        partidos = [(d, temporada_de(d, anual), f["HomeTeam"].strip(), f["AwayTeam"].strip()) for d, f in zip(fechas, filas_liga)]
        if fechas_intercambiadas(partidos):
            fechas = [_girar_fecha(d) for d in fechas]
            corregidas.append(codigo)
        datos.extend(_fila_clubes(codigo, f, d) for f, d in zip(filas_liga, fechas))
    con.executemany(f"INSERT INTO futbol_partidos VALUES ({','.join('?' * 33)})", datos)
    avisar(f"  Clubes: {len(datos):,} partidos de {len(por_liga)} competiciones")
    if corregidas:
        avisar(f"  Fechas con día y mes intercambiados corregidas en: {', '.join(sorted(corregidas))}")
    return len(datos)


def _fila_clubes(codigo, f, fecha):
    i = lambda c: _num(f.get(c), int)  # noqa: E731
    r = lambda c: _num(f.get(c))  # noqa: E731
    return (
        codigo, temporada_de(fecha, COMPETICIONES[codigo][4]), fecha.isoformat(), f["MatchTime"] or None,
        f["HomeTeam"].strip(), f["AwayTeam"].strip(), i("FTHome"), i("FTAway"), i("HTHome"), i("HTAway"),
        i("HomeShots"), i("AwayShots"), i("HomeTarget"), i("AwayTarget"), i("HomeFouls"), i("AwayFouls"),
        i("HomeCorners"), i("AwayCorners"), i("HomeYellow"), i("AwayYellow"), i("HomeRed"), i("AwayRed"),
        r("OddHome"), r("OddDraw"), r("OddAway"), r("MaxHome"), r("MaxDraw"), r("MaxAway"),
        r("Over25"), r("Under25"), r("HomeElo"), r("AwayElo"), "clubes",
    )


URL_FD_TEMPORADA = "https://www.football-data.co.uk/mmz4281/{temporada}/{codigo}.csv"
URL_FD_NUEVAS = "https://www.football-data.co.uk/new/{codigo}.csv"
NUEVAS_FD = {"ARG", "BRA", "USA", "MEX", "JAP", "CHN", "SWE", "NOR", "FIN", "IRL", "AUT", "SUI", "DEN", "POL", "ROM", "RUS"}
# Ligas donde un mismo cruce local-visitante puede repetirse en una temporada (más de dos vueltas o
# playoffs): en ellas los partidos se emparejan también por fecha
CRUCES_REPETIDOS = {"SC0", "SC1", "SC2", "SC3", "G1", "B1"} | NUEVAS_FD


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


CACHE_FD = RAIZ / "datos" / "football_data"


class _SinRed(Exception):
    pass


def _bajar_fd(url, nombre, historico, estado):
    """Descarga un CSV de football-data.co.uk. Las temporadas terminadas se guardan comprimidas en
    datos/football_data/ (incluidas en el repositorio) y no se vuelven a descargar; también sirven
    sin conexión. Devuelve None si la liga no existe esa temporada."""
    archivo, vacio = CACHE_FD / f"{nombre}.csv.gz", CACHE_FD / f"{nombre}.none"
    if historico and archivo.exists():
        estado["cache"] += 1
        return gzip.decompress(archivo.read_bytes())
    if historico and vacio.exists():
        return None
    if estado["sin_red"]:
        raise _SinRed
    try:
        contenido = _bajar(url)
    except urllib.error.HTTPError as e:
        # Solo un 404 significa que la liga no existe esa temporada; otros errores (429, 500...) son
        # pasajeros y se reintenta en la próxima actualización
        if historico and e.code == 404:
            CACHE_FD.mkdir(parents=True, exist_ok=True)
            vacio.touch()
        return None
    except (urllib.error.URLError, OSError) as e:
        estado["sin_red"] = True
        estado["error"] = e
        raise _SinRed from e
    estado["descargas"] += 1
    if historico:
        CACHE_FD.mkdir(parents=True, exist_ok=True)
        archivo.write_bytes(gzip.compress(contenido, compresslevel=9))
    return contenido


def _solo_posteriores(con, codigo, filas):
    """Para las ligas 'new' (un archivo con todas las temporadas, a veces con otros nombres de equipo):
    se añaden solo los partidos posteriores a los que ya hay, con los nombres traducidos a los de la base
    gracias a los partidos que coinciden en fecha y marcador."""
    existentes = con.execute("SELECT fecha, local, visitante, goles_local, goles_visitante FROM futbol_partidos "
                             "WHERE competicion = ? AND goles_local IS NOT NULL", (codigo,)).fetchall()
    if not existentes:
        return filas
    ultima = max(e[0] for e in existentes)
    mapa = _mapear_nombres([(f[2], f[4], f[5], f[6], f[7]) for f in filas if f[6] is not None], existentes)
    return [f[:4] + (mapa.get(f[4], f[4]), mapa.get(f[5], f[5])) + f[6:] for f in filas if f[2] > ultima]


def _football_data(con, avisar, hoy):
    """Completa la base con football-data.co.uk: la temporada en curso (se actualiza dos veces por semana,
    con estadísticas y cuotas) y las temporadas que faltan o están incompletas. Empareja cada partido por
    (competición, temporada, local, visitante): si ya existe sin resultado lo completa; si no existe lo añade."""
    columnas = ("competicion, temporada, fecha, hora, local, visitante, goles_local, goles_visitante, descanso_local, "
                "descanso_visitante, tiros_local, tiros_visitante, tiros_puerta_local, tiros_puerta_visitante, faltas_local, "
                "faltas_visitante, corners_local, corners_visitante, amarillas_local, amarillas_visitante, rojas_local, "
                "rojas_visitante, cuota_local, cuota_empate, cuota_visitante, cuota_max_local, cuota_max_empate, "
                "cuota_max_visitante, cuota_mas_2_5, cuota_menos_2_5, elo_local, elo_visitante, fuente")
    añadidos, completados = 0, 0

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
        # Nombres que siguen sin coincidir ("Man Utd" / "Man United"): se aprenden de los partidos que
        # coinciden en fecha y marcador con los que ya hay
        conocidos = {n for (n,) in con.execute("SELECT local FROM futbol_partidos WHERE competicion = ? UNION "
                                               "SELECT visitante FROM futbol_partidos WHERE competicion = ?", (codigo, codigo))}
        if conocidos and {n for f in filas for n in f[4:6]} - conocidos:
            fechas = sorted({f[2] for f in filas})
            referencia = con.execute("SELECT fecha, local, visitante, goles_local, goles_visitante FROM futbol_partidos "
                                     "WHERE competicion = ? AND goles_local IS NOT NULL AND fecha BETWEEN ? AND ?",
                                     (codigo, fechas[0], fechas[-1])).fetchall()
            mapa = {n: m for n, m in _mapear_nombres([(f[2], f[4], f[5], f[6], f[7]) for f in filas if f[6] is not None],
                                                     referencia).items() if n not in conocidos}
            filas = [f[:4] + (mapa.get(f[4], f[4]), mapa.get(f[5], f[5])) + f[6:] for f in filas]
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

    estado = {"descargas": 0, "cache": 0, "sin_red": False, "error": None}
    actual = int(temporada_de(hoy)[:4])
    for codigo in COMPETICIONES:
        try:
            if codigo in NUEVAS_FD:
                contenido = _bajar_fd(URL_FD_NUEVAS.format(codigo=codigo), f"nuevas_{codigo}", False, estado)
                if contenido:
                    filas = [f for f in (_fila_fd(codigo, r) for r in csv.DictReader(io.StringIO(_texto_csv(contenido)))) if f]
                    incorporar(codigo, _solo_posteriores(con, codigo, filas), clave_fecha=True)
                continue
            for anio in _temporadas_a_completar(con, codigo, temporada_de(hoy)):
                corta = f"{anio % 100:02d}{(anio + 1) % 100:02d}"
                try:
                    contenido = _bajar_fd(URL_FD_TEMPORADA.format(temporada=corta, codigo=codigo),
                                          f"{codigo}_{corta}", anio < actual - 1, estado)
                except _SinRed:
                    continue  # sin conexión: se siguen usando los archivos guardados
                if contenido:
                    filas = [_fila_fd(codigo, f) for f in csv.DictReader(io.StringIO(_texto_csv(contenido)))]
                    incorporar(codigo, filas, clave_fecha=codigo in CRUCES_REPETIDOS)
        except _SinRed:
            continue
    if estado["error"]:
        avisar(f"  football-data.co.uk no disponible ({estado['error']}); se usan solo los archivos guardados")
    descargas = estado["descargas"]
    avisar(f"  football-data.co.uk: {descargas} descargados y {estado['cache']} guardados, +{añadidos} partidos nuevos, "
           f"{completados} resultados completados")
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
        if codigo in CRUCES_REPETIDOS:  # el cruce no identifica el partido: se empareja por fecha
            pendientes_previos = set()
            ya = {(e[0], e[1]) for e in existentes}
        else:
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


# Letras que la normalización Unicode no descompone en ASCII
_LETRAS = str.maketrans({"ß": "ss", "ø": "o", "Ø": "O", "æ": "ae", "Æ": "AE", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D",
                         "ı": "i", "œ": "oe", "Œ": "OE", "þ": "th", "ð": "d"})


def _clave_nombre(nombre):
    """Clave que ignora signos, mayúsculas y tildes ("Nott'm Forest" y "Nottm Forest",
    "Preußen Münster" y "Preussen Munster" coinciden)."""
    texto = unicodedata.normalize("NFKD", nombre.translate(_LETRAS)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", texto)


# Clubes que la fuente escribe de dos formas demasiado distintas para unificarlas solas
# (cambian de nombre a mitad de temporada y nunca se enfrentan entre sí)
ALIAS_CLUBES = {"Gornik Z.": "Gornik Zabrze", "U Craiova": "Univ. Craiova", "Raith": "Raith Rvs"}


def _unificar_nombres(con, avisar):
    """La fuente escribe a veces un mismo club de dos formas ("Nott'm Forest" y "Nottm Forest").
    Se unifican las variantes que solo difieren en signos, mayúsculas o tildes con la más frecuente,
    y las de ALIAS_CLUBES."""
    clave = _clave_nombre
    cambios = 0
    for alias, nombre in ALIAS_CLUBES.items():
        for columna in ("local", "visitante"):
            cambios += con.execute(f"UPDATE futbol_partidos SET {columna} = ? WHERE {columna} = ?", (nombre, alias)).rowcount
    variantes = defaultdict(Counter)
    for columna in ("local", "visitante"):
        for nombre, n in con.execute(f"SELECT {columna}, COUNT(*) FROM futbol_partidos GROUP BY 1"):
            variantes[clave(nombre)][nombre] += n
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


def _tipo_nba(f):
    """REG, COPA (final de la NBA Cup, no cuenta en la clasificación), PLAYIN o PO; None si no se usa."""
    if f["season_type"] == "3":
        return "PO"
    if f["season_type"] == "5":
        return "PLAYIN"
    if f["season_type"] == "2":
        return {"1": "REG", "39": "COPA"}.get(f["type_id"])  # 4 = partido de las estrellas
    return None  # pretemporada


def _nba(con, avisar, hoy):
    from .nba.equipos import POR_ID

    partidos = []
    for temporada in range(2002, hoy.year + 2):  # la temporada 2026 es la 2025-26
        try:
            filas = _csv(URL_NBA_PARTIDOS.format(temporada))
        except (urllib.error.URLError, OSError):
            continue
        for f in filas:
            local, visitante, tipo = POR_ID.get(f["home_id"]), POR_ID.get(f["away_id"]), _tipo_nba(f)
            estado = f["status_type_name"]
            if not (local and visitante and tipo) or estado in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED"):
                continue
            final = estado == "STATUS_FINAL"
            periodos = _num(f.get("status_period"), int) or 4
            # 2019-20 se terminó en la "burbuja" de Orlando, sin ventaja de campo
            neutral = f["neutral_site"] == "true" or (temporada == 2020 and f["game_date"] >= "2020-07-30")
            partidos.append((
                f["game_id"], temporada, tipo, f.get("notes_headline") or None, f["game_date"], local, visitante,
                _num(f["home_score"], int) if final else None, _num(f["away_score"], int) if final else None,
                max(0, periodos - 4) if final else None, int(neutral), f.get("venue_full_name") or None,
                f.get("venue_address_city") or None,
            ))
    con.executemany(f"INSERT INTO nba_partidos VALUES ({','.join('?' * 13)})", partidos)
    if partidos:
        avisar(f"  NBA: {len(partidos):,} partidos (temporadas {partidos[0][1] - 1}-{str(partidos[0][1])[2:]} "
               f"a {partidos[-1][1] - 1}-{str(partidos[-1][1])[2:]})")

    tipos = {p[0]: p[2] for p in partidos}
    estadisticas = []
    for temporada in range(2002, hoy.year + 2):
        try:
            filas = _csv(URL_NBA_EQUIPOS.format(temporada))
        except (urllib.error.URLError, OSError):
            continue
        for f in filas:
            equipo, rival = POR_ID.get(f["team_id"]), POR_ID.get(f["opponent_team_id"])
            if not (equipo and rival and f["game_id"] in tipos):
                continue
            i = lambda c: _num(f.get(c), int)  # noqa: E731
            estadisticas.append((
                f["game_id"], temporada, tipos[f["game_id"]], f["game_date"], equipo, rival, int(f["team_home_away"] == "home"),
                i("team_score"), i("field_goals_made"), i("field_goals_attempted"), i("three_point_field_goals_made"),
                i("three_point_field_goals_attempted"), i("free_throws_made"), i("free_throws_attempted"),
                i("offensive_rebounds"), i("defensive_rebounds"), i("assists"), i("steals"), i("blocks"),
                i("total_turnovers"), i("fouls"), i("points_in_paint"), i("fast_break_points"),
            ))
    con.executemany(f"INSERT INTO nba_estadisticas_equipo VALUES ({','.join('?' * 23)})", estadisticas)
    if estadisticas:
        avisar(f"  NBA: {len(estadisticas):,} registros de estadísticas de equipo por partido")

    from .nba.jugadores import game_score

    jugadores, nombres = 0, {}
    for temporada in range(PRIMERA_NBA_JUGADORES, hoy.year + 2):
        try:
            filas = _csv(URL_NBA_JUGADORES.format(temporada))
        except (urllib.error.URLError, OSError):
            continue
        datos = []
        for f in filas:
            equipo, minutos = POR_ID.get(f["team_id"]), _num(f.get("minutes"))
            if equipo and minutos and f["game_id"] in tipos and f["athlete_id"].isdigit():
                datos.append((int(f["game_id"]), equipo, int(f["athlete_id"]), round(minutos),
                              round(game_score({k: _num(v) or 0.0 for k, v in f.items() if k in GS_CAMPOS}), 1)))
                nombres[int(f["athlete_id"])] = f["athlete_display_name"]
        con.executemany("INSERT INTO nba_jugadores_partido VALUES (?,?,?,?,?)", datos)
        jugadores += len(datos)
    con.executemany("INSERT INTO nba_jugadores VALUES (?,?)", nombres.items())
    if jugadores:
        avisar(f"  NBA: {jugadores:,} registros de jugadores por partido")
    return len(partidos), len(estadisticas), jugadores


GS_CAMPOS = {"points", "field_goals_made", "field_goals_attempted", "free_throws_made", "free_throws_attempted",
             "offensive_rebounds", "defensive_rebounds", "steals", "assists", "blocks", "fouls", "turnovers"}


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
    _unificar_nombres(con, avisar)  # antes de emparejar, para no duplicar partidos por grafías distintas
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
    avisar("Descargando NBA...")
    n_p, n_e, n_j = _nba(con, avisar, hoy)
    registrar("nba_partidos", LICENCIAS["nba"], n_p)
    registrar("nba_estadisticas_equipo", LICENCIAS["nba"], n_e)
    registrar("nba_jugadores_partido", LICENCIAS["nba"], n_j)
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
    try:
        r["nba"] = con.execute("SELECT COUNT(*), MIN(temporada), MAX(temporada), SUM(puntos_local IS NULL) FROM nba_partidos").fetchone()
        r["nba_estadisticas"] = con.execute("SELECT COUNT(*), MIN(temporada), MAX(temporada) FROM nba_estadisticas_equipo").fetchone()
    except sqlite3.OperationalError:  # base creada antes de añadir la NBA
        r["nba"] = r["nba_estadisticas"] = None
    return r
