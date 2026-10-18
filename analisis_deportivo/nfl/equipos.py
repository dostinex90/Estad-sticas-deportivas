"""Equipos, conferencias y divisiones de la NFL (alineación vigente desde 2002)."""

DIVISIONES = {
    "AFC Este": ["BUF", "MIA", "NE", "NYJ"],
    "AFC Norte": ["BAL", "CIN", "CLE", "PIT"],
    "AFC Sur": ["HOU", "IND", "JAX", "TEN"],
    "AFC Oeste": ["DEN", "KC", "LV", "LAC"],
    "NFC Este": ["DAL", "NYG", "PHI", "WAS"],
    "NFC Norte": ["CHI", "DET", "GB", "MIN"],
    "NFC Sur": ["ATL", "CAR", "NO", "TB"],
    "NFC Oeste": ["ARI", "LA", "SF", "SEA"],
}

# Abreviaturas antiguas que usan los datos históricos
ALIAS = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA", "JAC": "JAX", "WSH": "WAS"}

NOMBRES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}

DIVISION_DE = {equipo: div for div, equipos in DIVISIONES.items() for equipo in equipos}


def normalizar(abreviatura):
    a = abreviatura.strip().upper()
    return ALIAS.get(a, a)


def division(equipo):
    return DIVISION_DE.get(equipo)


def conferencia(equipo):
    d = DIVISION_DE.get(equipo)
    return d.split()[0] if d else None


def nombre(equipo):
    return NOMBRES.get(equipo, equipo)
