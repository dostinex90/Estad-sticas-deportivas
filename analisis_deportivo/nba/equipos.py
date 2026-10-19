"""Equipos, conferencias y divisiones de la NBA (alineación vigente desde 2004-05)."""

DIVISIONES = {
    "Este · Atlántico": ["BOS", "BKN", "NY", "PHI", "TOR"],
    "Este · Central": ["CHI", "CLE", "DET", "IND", "MIL"],
    "Este · Sudeste": ["ATL", "CHA", "MIA", "ORL", "WSH"],
    "Oeste · Noroeste": ["DEN", "MIN", "OKC", "POR", "UTAH"],
    "Oeste · Pacífico": ["GS", "LAC", "LAL", "PHX", "SAC"],
    "Oeste · Suroeste": ["DAL", "HOU", "MEM", "NO", "SA"],
}

# Identificador de franquicia de ESPN -> abreviatura actual. Así los traslados y cambios de nombre
# (New Jersey -> Brooklyn, Seattle -> Oklahoma City, New Orleans Hornets -> Pelicans) son el mismo equipo.
POR_ID = {
    "1": "ATL", "2": "BOS", "3": "NO", "4": "CHI", "5": "CLE", "6": "DAL", "7": "DEN", "8": "DET", "9": "GS",
    "10": "HOU", "11": "IND", "12": "LAC", "13": "LAL", "14": "MIA", "15": "MIL", "16": "MIN", "17": "BKN",
    "18": "NY", "19": "ORL", "20": "PHI", "21": "PHX", "22": "POR", "23": "SAC", "24": "SA", "25": "OKC",
    "26": "UTAH", "27": "WSH", "28": "TOR", "29": "MEM", "30": "CHA",
}

NOMBRES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets", "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers", "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets",
    "DET": "Detroit Pistons", "GS": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies", "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves", "NO": "New Orleans Pelicans", "NY": "New York Knicks",
    "OKC": "Oklahoma City Thunder", "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SA": "San Antonio Spurs", "SAC": "Sacramento Kings", "TOR": "Toronto Raptors",
    "UTAH": "Utah Jazz", "WSH": "Washington Wizards",
}

DIVISION_DE = {equipo: div for div, equipos in DIVISIONES.items() for equipo in equipos}
CONFERENCIAS = ("Este", "Oeste")


def division(equipo):
    return DIVISION_DE.get(equipo)


def conferencia(equipo, temporada=None):
    """Conferencia del equipo. Los New Orleans Hornets jugaron en el Este hasta 2003-04."""
    if equipo == "NO" and temporada is not None and temporada <= 2004:
        return "Este"
    d = DIVISION_DE.get(equipo)
    return d.split(" · ")[0] if d else None


def nombre(equipo):
    return NOMBRES.get(equipo, equipo)
