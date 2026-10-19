"""Estadísticas descriptivas de la NBA: récords, clasificación, situaciones y resumen de liga."""

from collections import Counter
from dataclasses import dataclass, field

from ..comun import media, pct
from .datos import descansos
from .equipos import CONFERENCIAS, DIVISIONES, conferencia, division

EXPONENTE_PITAGORICO = 14  # el habitual en baloncesto (Daryl Morey usaba 13.91)
PARTIDO_AJUSTADO = 5
PALIZA = 15


@dataclass(frozen=True)
class Vista:
    """Un partido visto desde un equipo."""
    partido: object
    equipo: str
    rival: str
    pf: int
    pc: int
    es_local: bool

    @property
    def margen(self):
        return self.pf - self.pc

    @property
    def resultado(self):
        return "G" if self.pf > self.pc else "P"


def vistas(partidos, equipo):
    res = []
    for p in partidos:
        if not (p.jugado and p.participa(equipo)):
            continue
        local = p.local == equipo
        res.append(Vista(partido=p, equipo=equipo, rival=p.visitante if local else p.local,
                         pf=p.puntos_local if local else p.puntos_visitante,
                         pc=p.puntos_visitante if local else p.puntos_local, es_local=local and not p.neutral))
    return res


@dataclass
class Registro:
    g: int = 0
    p: int = 0
    pf: int = 0
    pc: int = 0

    @classmethod
    def de(cls, vs):
        r = cls()
        for v in vs:
            r.pf += v.pf
            r.pc += v.pc
            if v.resultado == "G":
                r.g += 1
            else:
                r.p += 1
        return r

    @property
    def jugados(self):
        return self.g + self.p

    @property
    def porcentaje(self):
        return self.g / self.jugados if self.jugados else 0.0

    @property
    def diferencia(self):
        return self.pf - self.pc

    @property
    def pf_pp(self):
        return self.pf / self.jugados if self.jugados else 0.0

    @property
    def pc_pp(self):
        return self.pc / self.jugados if self.jugados else 0.0

    @property
    def dif_pp(self):
        return self.diferencia / self.jugados if self.jugados else 0.0

    @property
    def victorias_pitagoricas(self):
        if not self.jugados or (self.pf == 0 and self.pc == 0):
            return 0.0
        x = EXPONENTE_PITAGORICO
        return self.jugados * self.pf**x / (self.pf**x + self.pc**x)

    def texto(self):
        return f"{self.g}-{self.p}"


@dataclass
class FilaClasificacion:
    equipo: str
    total: Registro = field(default_factory=Registro)
    local: Registro = field(default_factory=Registro)
    visitante: Registro = field(default_factory=Registro)
    conferencia: Registro = field(default_factory=Registro)
    division: Registro = field(default_factory=Registro)
    ultimos: str = ""
    racha: str = ""

    @property
    def clave_orden(self):
        return (-self.total.porcentaje, -self.total.g, -self.total.dif_pp, self.equipo)


def _racha(vs):
    if not vs:
        return ""
    ultimo = vs[-1].resultado
    n = 0
    for v in reversed(vs):
        if v.resultado != ultimo:
            break
        n += 1
    return f"{'G' if ultimo == 'G' else 'P'}{n}"


def racha(vs):
    return _racha(vs)


def clasificacion(partidos, temporada):
    """{equipo: FilaClasificacion} de la temporada regular. Incluye a los equipos con partidos
    pendientes aunque aún no hayan jugado. Desempates simplificados: % victorias, diferencia por partido."""
    reg = [p for p in partidos if p.temporada == temporada and p.tipo == "REG"]
    eqs = {p.local for p in reg} | {p.visitante for p in reg}
    filas = {}
    for e in eqs:
        vs = vistas(reg, e)
        filas[e] = FilaClasificacion(
            equipo=e, total=Registro.de(vs),
            local=Registro.de([v for v in vs if v.partido.local == e]),
            visitante=Registro.de([v for v in vs if v.partido.visitante == e]),
            conferencia=Registro.de([v for v in vs if conferencia(v.rival, temporada) == conferencia(e, temporada)]),
            division=Registro.de([v for v in vs if division(v.rival) == division(e)]),
            ultimos="".join(v.resultado for v in vs[-10:]), racha=_racha(vs),
        )
    return filas


def por_conferencia(filas, temporada):
    return {c: sorted((f for f in filas.values() if conferencia(f.equipo, temporada) == c), key=lambda f: f.clave_orden)
            for c in CONFERENCIAS}


def por_division(filas):
    return {d: sorted((filas[e] for e in eqs if e in filas), key=lambda f: f.clave_orden) for d, eqs in DIVISIONES.items()}


def splits(partidos, equipo, filas=None):
    """Récords del equipo en distintas situaciones. filas: clasificación (para 'récord ganador')."""
    vs = vistas(partidos, equipo)
    reg = [v for v in vs if v.partido.tipo == "REG"]
    dias = descansos(partidos)
    temporada = vs[0].partido.temporada if vs else None
    ganadores = {e for e, f in (filas or {}).items() if f.total.porcentaje > 0.5}
    casos = [
        ("Temporada regular", reg),
        ("Local", [v for v in reg if v.es_local]),
        ("Visitante", [v for v in reg if not v.es_local and v.partido.visitante == equipo]),
        ("Contra el Este", [v for v in reg if conferencia(v.rival, temporada) == "Este"]),
        ("Contra el Oeste", [v for v in reg if conferencia(v.rival, temporada) == "Oeste"]),
        ("Contra su división", [v for v in reg if division(v.rival) == division(equipo)]),
        ("Contra equipos con récord ganador", [v for v in reg if v.rival in ganadores]),
        (f"Partidos ajustados (≤{PARTIDO_AJUSTADO} pts)", [v for v in reg if abs(v.margen) <= PARTIDO_AJUSTADO]),
        (f"Por {PALIZA}+ puntos", [v for v in reg if abs(v.margen) >= PALIZA]),
        ("Con prórroga", [v for v in reg if v.partido.prorrogas]),
        ("Segundo de dos días seguidos", [v for v in reg if dias.get((v.partido.id, equipo)) == 1]),
        ("Con 2 o más días de descanso", [v for v in reg if (dias.get((v.partido.id, equipo)) or 0) >= 3]),
        ("NBA Cup (final)", [v for v in vs if v.partido.tipo == "COPA"]),
        ("Play-in", [v for v in vs if v.partido.tipo == "PLAYIN"]),
        ("Playoffs", [v for v in vs if v.partido.tipo == "PO"]),
    ]
    return [(nombre, Registro.de(lista)) for nombre, lista in casos if lista]


def resumen_liga(partidos):
    """Resumen de una temporada: ventaja de campo, márgenes, puntos y extremos."""
    jug = [p for p in partidos if p.jugado]
    r = {"partidos": len(jug), "pendientes": sum(1 for p in partidos if not p.jugado)}
    if not jug:
        return r
    campo = [p for p in jug if not p.neutral]
    r["puntos_pp"] = media(p.total for p in jug)
    r["puntos_local_pp"] = media(p.puntos_local for p in campo)
    r["puntos_visitante_pp"] = media(p.puntos_visitante for p in campo)
    r["pct_gana_local"] = pct(sum(p.margen > 0 for p in campo), len(campo))
    r["margen_local"] = media(p.margen for p in campo)
    r["pct_ajustados"] = pct(sum(abs(p.margen) <= PARTIDO_AJUSTADO for p in jug), len(jug))
    r["pct_palizas"] = pct(sum(abs(p.margen) >= PALIZA for p in jug), len(jug))
    r["pct_prorroga"] = pct(sum(p.prorrogas > 0 for p in jug), len(jug))
    r["margenes_frecuentes"] = Counter(abs(p.margen) for p in jug).most_common(8)
    r["mas_puntos"] = max(jug, key=lambda p: p.total)
    r["menos_puntos"] = min(jug, key=lambda p: p.total)
    r["mayor_paliza"] = max(jug, key=lambda p: abs(p.margen))
    dias = descansos(partidos)
    b2b = [p for p in jug if (dias.get((p.id, p.local)) == 1) != (dias.get((p.id, p.visitante)) == 1)]
    if b2b:
        gana_descansado = sum((p.margen > 0) == (dias.get((p.id, p.visitante)) == 1) for p in b2b)
        r["pct_gana_descansado"] = pct(gana_descansado, len(b2b))
        r["partidos_b2b"] = len(b2b)
    return r
