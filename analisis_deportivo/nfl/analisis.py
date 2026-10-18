"""Estadísticas descriptivas de la NFL: récords, clasificación, splits, apuestas y liga."""

from collections import Counter, defaultdict
from dataclasses import dataclass

from ..comun import media, pct
from .equipos import DIVISIONES, conferencia, division

EXPONENTE_PITAGORICO = 2.37
PARTIDO_AJUSTADO = 8  # diferencia máxima de una posesión
PALIZA = 17


@dataclass(frozen=True)
class Vista:
    """Un partido visto desde un equipo."""
    juego: object
    equipo: str
    rival: str
    pf: int
    pc: int
    es_local: bool
    linea: object  # ventaja esperada del equipo según el mercado (positivo = favorito)
    descanso: object
    qb: str

    @property
    def margen(self):
        return self.pf - self.pc

    @property
    def resultado(self):
        return "G" if self.pf > self.pc else "P" if self.pf < self.pc else "E"

    @property
    def ats(self):
        """Resultado contra la línea: "C" cubre, "N" no cubre, "E" push, None sin línea."""
        if self.linea is None:
            return None
        d = self.margen - self.linea
        return "C" if d > 0 else "N" if d < 0 else "E"

    @property
    def over_under(self):
        tl = self.juego.total_linea
        if tl is None:
            return None
        t = self.pf + self.pc
        return "O" if t > tl else "U" if t < tl else "E"


def vistas(juegos, equipo):
    res = []
    for j in juegos:
        if not (j.jugado and j.participa(equipo)):
            continue
        local = j.local == equipo
        linea = None if j.linea is None else (j.linea if local else -j.linea)
        res.append(Vista(
            juego=j, equipo=equipo, rival=j.visitante if local else j.local,
            pf=j.puntos_local if local else j.puntos_visitante,
            pc=j.puntos_visitante if local else j.puntos_local,
            es_local=local and not j.neutral, linea=linea,
            descanso=j.descanso_local if local else j.descanso_visitante,
            qb=j.qb_local if local else j.qb_visitante,
        ))
    return res


@dataclass
class Registro:
    g: int = 0
    p: int = 0
    e: int = 0
    pf: int = 0
    pc: int = 0
    cubre: int = 0
    no_cubre: int = 0
    push: int = 0
    over: int = 0
    under: int = 0
    push_total: int = 0

    @classmethod
    def de(cls, vs):
        r = cls()
        for v in vs:
            r.pf += v.pf
            r.pc += v.pc
            if v.resultado == "G":
                r.g += 1
            elif v.resultado == "P":
                r.p += 1
            else:
                r.e += 1
            a = v.ats
            if a == "C":
                r.cubre += 1
            elif a == "N":
                r.no_cubre += 1
            elif a == "E":
                r.push += 1
            o = v.over_under
            if o == "O":
                r.over += 1
            elif o == "U":
                r.under += 1
            elif o == "E":
                r.push_total += 1
        return r

    @property
    def jugados(self):
        return self.g + self.p + self.e

    @property
    def porcentaje(self):
        """Porcentaje de victorias al estilo NFL (los empates cuentan media victoria)."""
        return (self.g + 0.5 * self.e) / self.jugados if self.jugados else 0.0

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
    def victorias_pitagoricas(self):
        if not self.jugados or (self.pf == 0 and self.pc == 0):
            return 0.0
        x = EXPONENTE_PITAGORICO
        return self.jugados * self.pf**x / (self.pf**x + self.pc**x)

    def texto(self):
        base = f"{self.g}-{self.p}"
        return base + (f"-{self.e}" if self.e else "")

    def texto_ats(self):
        if not (self.cubre or self.no_cubre or self.push):
            return "—"
        return f"{self.cubre}-{self.no_cubre}" + (f"-{self.push}" if self.push else "")

    def texto_ou(self):
        if not (self.over or self.under or self.push_total):
            return "—"
        return f"{self.over}-{self.under}" + (f"-{self.push_total}" if self.push_total else "")


def splits(juegos, equipo):
    """Récords del equipo en múltiples situaciones. Devuelve lista de (nombre, Registro)."""
    vs = vistas(juegos, equipo)
    div = division(equipo)
    conf = conferencia(equipo)
    filtros = [
        ("Todos los partidos", lambda v: True),
        ("Local", lambda v: v.es_local),
        ("Visitante", lambda v: not v.es_local and not v.juego.neutral),
        ("Campo neutral", lambda v: v.juego.neutral),
        ("División", lambda v: division(v.rival) == div),
        ("Conferencia", lambda v: conferencia(v.rival) == conf),
        ("Otra conferencia", lambda v: conferencia(v.rival) not in (conf, None)),
        (f"Partidos ajustados (≤{PARTIDO_AJUSTADO})", lambda v: abs(v.margen) <= PARTIDO_AJUSTADO),
        (f"Por {PALIZA}+ puntos", lambda v: abs(v.margen) >= PALIZA),
        ("Prórroga", lambda v: v.juego.prorroga),
        ("Como favorito", lambda v: v.linea is not None and v.linea > 0),
        ("Como underdog", lambda v: v.linea is not None and v.linea < 0),
        ("Tras semana de descanso", lambda v: v.descanso is not None and v.descanso >= 13),
        ("Semana corta (≤5 días)", lambda v: v.descanso is not None and v.descanso <= 5),
        ("Bajo techo", lambda v: v.juego.bajo_techo),
        ("Aire libre", lambda v: v.juego.techo in ("outdoors", "open")),
        ("Frío (≤40 °F)", lambda v: v.juego.temperatura is not None and v.juego.temperatura <= 40),
        ("Viento (≥15 mph)", lambda v: v.juego.viento is not None and v.juego.viento >= 15),
        ("Contra equipos con récord ganador", None),  # se rellena abajo
        ("Playoffs", lambda v: v.juego.es_playoff),
    ]
    # Récord de los rivales en la(s) temporada(s) analizada(s), sin contar el partido contra este equipo
    regs = {e: Registro.de(vistas([j for j in juegos if j.tipo == "REG"], e)) for e in {v.rival for v in vs}}
    resultado = []
    for nombre, f in filtros:
        if f is None:
            f = lambda v: regs[v.rival].porcentaje > 0.5  # noqa: E731
        seleccion = [v for v in vs if f(v)]
        if seleccion:
            resultado.append((nombre, Registro.de(seleccion)))
    return resultado


def registro_por_qb(juegos, equipo):
    por_qb = defaultdict(list)
    for v in vistas(juegos, equipo):
        if v.qb:
            por_qb[v.qb].append(v)
    return sorted(((qb, Registro.de(vs)) for qb, vs in por_qb.items()), key=lambda x: -x[1].jugados)


def racha(vs):
    if not vs:
        return ""
    ultimo = vs[-1].resultado
    n = 0
    for v in reversed(vs):
        if v.resultado != ultimo:
            break
        n += 1
    return f"{'W' if ultimo == 'G' else 'L' if ultimo == 'P' else 'T'}{n}"


@dataclass
class FilaClasificacion:
    equipo: str
    total: Registro
    local: Registro
    visitante: Registro
    division: Registro
    conferencia: Registro
    racha: str
    ultimos: str

    @property
    def clave_orden(self):
        # Desempates simplificados: % victorias, % en división, % en conferencia, diferencia de puntos
        return (-self.total.porcentaje, -self.division.porcentaje, -self.conferencia.porcentaje,
                -self.total.diferencia, self.equipo)


def clasificacion(juegos, temporada):
    """Filas de clasificación de la temporada regular para cada equipo con división conocida."""
    reg = [j for j in juegos if j.temporada == temporada and j.tipo == "REG"]
    filas = {}
    for equipo in sorted({j.local for j in reg} | {j.visitante for j in reg}):
        if division(equipo) is None:
            continue
        vs = vistas(reg, equipo)
        filas[equipo] = FilaClasificacion(
            equipo=equipo,
            total=Registro.de(vs),
            local=Registro.de([v for v in vs if v.es_local]),
            visitante=Registro.de([v for v in vs if not v.es_local]),
            division=Registro.de([v for v in vs if division(v.rival) == division(equipo)]),
            conferencia=Registro.de([v for v in vs if conferencia(v.rival) == conferencia(equipo)]),
            racha=racha(vs),
            ultimos="".join("W" if v.resultado == "G" else "L" if v.resultado == "P" else "T" for v in vs[-5:]),
        )
    return filas


def por_division(filas):
    return {div: sorted((filas[e] for e in eqs if e in filas), key=lambda f: f.clave_orden)
            for div, eqs in DIVISIONES.items()}


def siembra_playoffs(filas, conf, plazas=7):
    """Cabezas de serie: 4 campeones de división (1-4) y comodines (5-7)."""
    divisiones = por_division(filas)
    campeones = sorted((d[0] for nombre, d in divisiones.items() if nombre.startswith(conf) and d),
                       key=lambda f: f.clave_orden)
    resto = sorted((f for nombre, d in divisiones.items() if nombre.startswith(conf) for f in d[1:]),
                   key=lambda f: f.clave_orden)
    return campeones + resto[: plazas - len(campeones)], resto[plazas - len(campeones):]


def resumen_liga(juegos):
    jug = [j for j in juegos if j.jugado]
    n = len(jug)
    if not n:
        return {"partidos": 0}
    no_neutral = [j for j in jug if not j.neutral]
    con_linea = [j for j in jug if j.linea is not None]
    con_linea_no_pick = [j for j in con_linea if j.linea != 0]
    con_total = [j for j in jug if j.total_linea is not None]
    margenes = Counter(abs(j.margen) for j in jug)
    r = {
        "partidos": n,
        "pendientes": len(juegos) - n,
        "puntos_pp": media(j.total for j in jug),
        "puntos_local_pp": media(j.puntos_local for j in jug),
        "puntos_visitante_pp": media(j.puntos_visitante for j in jug),
        "pct_gana_local": pct(sum(j.margen > 0 for j in no_neutral), len(no_neutral)),
        "margen_local": media(j.margen for j in no_neutral),
        "pct_empates": pct(sum(j.margen == 0 for j in jug), n),
        "pct_prorroga": pct(sum(j.prorroga for j in jug), n),
        "pct_ajustados": pct(sum(abs(j.margen) <= PARTIDO_AJUSTADO for j in jug), n),
        "pct_palizas": pct(sum(abs(j.margen) >= PALIZA for j in jug), n),
        "margenes_frecuentes": margenes.most_common(10),
        "mas_puntos": max(jug, key=lambda j: j.total),
        "menos_puntos": min(jug, key=lambda j: j.total),
        "mayor_paliza": max(jug, key=lambda j: abs(j.margen)),
    }
    if con_linea_no_pick:
        fav_gana = sum((j.margen > 0) == (j.linea > 0) and j.margen != 0 for j in con_linea_no_pick)
        fav_cubre = sum((j.margen - j.linea) * (1 if j.linea > 0 else -1) > 0 for j in con_linea_no_pick)
        r["pct_favorito_gana"] = pct(fav_gana, len(con_linea_no_pick))
        r["pct_favorito_cubre"] = pct(fav_cubre, len(con_linea_no_pick))
        r["pct_local_cubre"] = pct(sum(j.margen > j.linea for j in con_linea), len(con_linea))
        r["error_linea"] = media(abs(j.margen - j.linea) for j in con_linea)
        r["linea_media_local"] = media(j.linea for j in con_linea if not j.neutral)
        underdogs = [j for j in con_linea_no_pick if abs(j.linea) >= 7]
        if underdogs:
            r["pct_sorpresa_7"] = pct(sum((j.margen > 0) != (j.linea > 0) and j.margen != 0 for j in underdogs), len(underdogs))
    if con_total:
        r["pct_over"] = pct(sum(j.total > j.total_linea for j in con_total), len(con_total))
        r["total_linea_media"] = media(j.total_linea for j in con_total)
        r["error_total"] = media(abs(j.total - j.total_linea) for j in con_total)
    por_techo = defaultdict(list)
    for j in jug:
        if j.techo:
            por_techo["Bajo techo" if j.bajo_techo else "Aire libre"].append(j.total)
    r["puntos_por_techo"] = {k: (media(v), len(v)) for k, v in por_techo.items()}
    frio = [j.total for j in jug if j.temperatura is not None and j.temperatura <= 40]
    if frio:
        r["puntos_frio"] = (media(frio), len(frio))
    viento = [j.total for j in jug if j.viento is not None and j.viento >= 15]
    if viento:
        r["puntos_viento"] = (media(viento), len(viento))
    div = [j for j in jug if j.divisional]
    if div:
        r["puntos_divisionales"] = (media(j.total for j in div), len(div))
    return r


# nombre -> (descripción, función sobre Registro, mayor es mejor)
METRICAS = {
    "ataque": ("Puntos anotados por partido", lambda r: r.pf_pp, True),
    "defensa": ("Puntos permitidos por partido", lambda r: r.pc_pp, False),
    "diferencia": ("Diferencia de puntos", lambda r: r.diferencia, True),
    "pitagoricas": ("Victorias pitagóricas", lambda r: r.victorias_pitagoricas, True),
    "suerte": ("Victorias reales - pitagóricas (suerte)", lambda r: r.g + 0.5 * r.e - r.victorias_pitagoricas, True),
    "ats": ("% cubre el spread", lambda r: pct(r.cubre, r.cubre + r.no_cubre), True),
    "over": ("% partidos over", lambda r: pct(r.over, r.over + r.under), True),
}


def lideres(juegos, metrica, cantidad=10):
    descripcion, f, mayor = METRICAS[metrica]
    regs = {e: Registro.de(vistas(juegos, e)) for e in {j.local for j in juegos} | {j.visitante for j in juegos}}
    regs = {e: r for e, r in regs.items() if r.jugados}
    orden = sorted(regs.items(), key=lambda kv: ((-f(kv[1])) if mayor else f(kv[1]), kv[0]))
    return descripcion, [(e, f(r), r) for e, r in orden[:cantidad]]
