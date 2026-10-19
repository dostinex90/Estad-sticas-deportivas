"""Funciones de la API web: leen la base de datos y devuelven diccionarios listos para JSON.

Reutilizan los mismos módulos de análisis y modelos que el CLI. Las cargas y los modelos
se guardan en caché porque los datos no cambian mientras el servidor está en marcha.
"""

import threading
from datetime import date
from functools import lru_cache

from .. import base
from ..comun import elegir_equipo, normal_cdf, pct, racha_actual, racha_maxima
from ..futbol import analisis as fa
from ..futbol import modelos as fm
from ..futbol.datos import ESTADISTICAS, cargar_para_analisis, equipos as f_equipos, jugados as f_jugados, pendientes
from ..nba import analisis as ba
from ..nba import estadisticas as be
from ..nba import modelos as bm
from ..nba.datos import NOMBRE_TIPO as NBA_TIPO, cargar_desde_base as nba_cargar, descansos, leer_temporada, texto_temporada
from ..nba.equipos import CONFERENCIAS, DIVISIONES as NBA_DIVISIONES, division as nba_division, nombre as nba_nombre
from ..nfl import analisis as na
from ..nfl import estadisticas as ne
from ..nfl import modelos as nm
from ..nfl.datos import cargar_desde_base as nfl_cargar, temporadas as nfl_temporadas
from ..nfl.equipos import DIVISIONES, conferencia, division, nombre as nfl_nombre

_bloqueo = threading.Lock()


def _con():
    with _bloqueo:  # la primera vez puede descomprimir la base; que solo lo haga un hilo
        return base.conectar()


def _r(x, d=3):
    return None if x is None else round(x, d)


# ── Fútbol ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=64)
def _futbol(liga, temporada, torneo):
    con = _con()
    try:
        partidos, descripcion, previos, codigo = cargar_para_analisis(con, liga, temporada, torneo)
    finally:
        con.close()
    return tuple(partidos), descripcion, tuple(previos), codigo


@lru_cache(maxsize=32)
def _futbol_modelos(liga, temporada, torneo):
    partidos, _, previos, _ = _futbol(liga, temporada, torneo)
    entrenamiento = list(previos) + f_jugados(partidos)
    return fm.ModeloPoisson().ajustar(entrenamiento), fm.EloFutbol().procesar(entrenamiento)


def _f_args(q):
    liga = q.get("liga") or None
    torneo = q.get("torneo") or None
    temporada = q.get("temporada") or None
    return liga, temporada, torneo


def _f_cargar(q, temporada=None):
    liga, temp, torneo = _f_args(q)
    partidos, descripcion, _, codigo = _futbol(liga, temporada or temp, torneo)
    return list(partidos), descripcion, codigo


def futbol_opciones(q):
    con = _con()
    try:
        temporadas = {}
        for comp, temp in con.execute("SELECT DISTINCT competicion, temporada FROM futbol_partidos "
                                      "WHERE goles_local IS NOT NULL ORDER BY 1, 2 DESC"):
            temporadas.setdefault(comp, []).append(temp)
        anios = con.execute("SELECT MIN(substr(fecha,1,4)), MAX(substr(fecha,1,4)) FROM futbol_selecciones").fetchone()
        torneos_n = dict(con.execute("SELECT torneo, COUNT(*) FROM futbol_selecciones GROUP BY torneo").fetchall())
        ediciones = {}
        for t in base.TORNEOS.values():
            ediciones[t] = [r[0] for r in con.execute(
                "SELECT DISTINCT substr(fecha,1,4) FROM futbol_selecciones WHERE torneo = ? AND goles_local IS NOT NULL "
                "ORDER BY 1 DESC", (t,))]
    finally:
        con.close()
    competiciones = [{"codigo": c, "nombre": n, "pais": p, "alias": a, "temporadas": temporadas.get(c, [])}
                     for c, (n, p, a, *_) in base.COMPETICIONES.items() if c in temporadas]
    competiciones.sort(key=lambda c: (c["pais"], c["codigo"]))
    torneos = [{"alias": a, "nombre": t, "partidos": torneos_n.get(t, 0), "ediciones": ediciones.get(t, [])}
               for a, t in base.TORNEOS.items()]
    return {"competiciones": competiciones, "torneos": torneos, "anios_selecciones": list(anios)}


def futbol_tabla(q):
    partidos, descripcion, _ = _f_cargar(q)
    condicion = q.get("condicion") or None
    if condicion == "descanso":
        tabla = fa.tabla_descanso(partidos)
    else:
        tabla = fa.tabla_posiciones(partidos, condicion if condicion in ("local", "visitante") else None)
    return {
        "descripcion": descripcion,
        "partidos": len(f_jugados(partidos)),
        "pendientes": len(pendientes(partidos)),
        "filas": [{"pos": i, "equipo": s.equipo, "pj": s.jugados, "g": s.ganados, "e": s.empatados, "p": s.perdidos,
                   "gf": s.goles_favor, "gc": s.goles_contra, "dg": s.diferencia, "pts": s.puntos,
                   "ppp": _r(s.puntos_por_partido, 2), "forma": s.forma()} for i, s in enumerate(tabla, 1)],
    }


def futbol_equipos(q):
    partidos, descripcion, _ = _f_cargar(q)
    return {"descripcion": descripcion, "equipos": f_equipos(partidos)}


def _bloque(s):
    if not s:
        return None
    return {"pj": s.jugados, "g": s.ganados, "e": s.empatados, "p": s.perdidos, "gf": s.goles_favor,
            "gc": s.goles_contra, "pts": s.puntos, "ppp": _r(s.puntos_por_partido, 2),
            "gf_pp": _r(s.goles_favor_por_partido, 2), "gc_pp": _r(s.goles_contra_por_partido, 2),
            "pct_victorias": _r(s.porcentaje_victorias, 1)}


def futbol_equipo(q):
    partidos, descripcion, _ = _f_cargar(q)
    jug = f_jugados(partidos)
    equipo = elegir_equipo(q.get("equipo", ""), f_equipos(jug))
    total = fa.calcular_estadisticas(jug)[equipo]
    tabla = fa.tabla_posiciones(jug)
    mp, elo = _futbol_modelos(*_f_args(q))
    r, n = racha_actual(total.resultados)
    jugadas = total.jugados
    res = {
        "descripcion": descripcion,
        "equipo": equipo,
        "posicion": next(i for i, s in enumerate(tabla, 1) if s.equipo == equipo),
        "equipos_liga": len(tabla),
        "total": _bloque(total),
        "local": _bloque(fa.calcular_estadisticas(jug, "local").get(equipo)),
        "visitante": _bloque(fa.calcular_estadisticas(jug, "visitante").get(equipo)),
        "forma": total.forma(10),
        "racha": {"tipo": r, "n": n},
        "rachas_max": {"victorias": racha_maxima(total.resultados, "G"), "invicto": racha_maxima(total.resultados, "GE"),
                       "sin_ganar": racha_maxima(total.resultados, "EP")},
        "mercados": {
            "Porterías a cero": _r(pct(total.porterias_cero, jugadas), 1),
            "Se queda sin marcar": _r(pct(total.sin_marcar, jugadas), 1),
            "Marcan ambos": _r(pct(total.ambos_marcan, jugadas), 1),
            "Más de 1.5 goles": _r(pct(total.mas_1_5, jugadas), 1),
            "Más de 2.5 goles": _r(pct(total.mas_2_5, jugadas), 1),
            "Más de 3.5 goles": _r(pct(total.mas_3_5, jugadas), 1),
        },
        "marcadores": [{"marcador": f"{a}-{b}", "veces": v} for (a, b), v in total.marcadores.most_common(6)],
        "descanso": None,
        "juego": [],
        "ratios": {},
        "niveles": [{"nivel": g.equipo, "pj": g.jugados, "g": g.ganados, "e": g.empatados, "p": g.perdidos,
                     "gf": g.goles_favor, "gc": g.goles_contra, "ppp": _r(g.puntos_por_partido, 2)}
                    for g in fa.rendimiento_por_nivel(jug, equipo)],
        "evolucion": [{"fecha": str(f), "posicion": p, "puntos": pts} for f, p, pts in fa.evolucion_posiciones(jug, equipo)],
        "elo": {"rating": _r(elo.rating.get(equipo), 0),
                "puesto": [e for e, _ in elo.ranking() if e in set(f_equipos(jug))].index(equipo) + 1,
                "historial": [{"fecha": str(f), "rating": _r(x, 0)} for f, x in elo.historial[equipo]]},
        "fuerza": {"ataque": _r(mp.ataque.get(equipo), 2), "defensa": _r(mp.defensa.get(equipo), 2)},
        "ultimos": [],
        "proximos": [],
    }
    if total.con_descanso:
        res["descanso"] = {
            "goles_1t": [total.goles_favor_1t, total.goles_contra_1t], "goles_2t": [total.goles_favor_2t, total.goles_contra_2t],
            "ganando": total.ganando_descanso, "empatando": total.empatando_descanso, "perdiendo": total.perdiendo_descanso,
            "gana_si_gana": _r(pct(total.gano_tras_ganar_descanso, total.ganando_descanso), 1) if total.ganando_descanso else None,
            "puntua_si_pierde": _r(pct(total.no_perdio_tras_perder_descanso, total.perdiendo_descanso), 1) if total.perdiendo_descanso else None,
            "remontadas": total.gano_tras_perder_descanso,
        }
    nombres = {"tiros": "Tiros", "tiros_puerta": "Tiros a puerta", "corners": "Córners", "faltas": "Faltas",
               "amarillas": "Amarillas", "rojas": "Rojas"}
    for k in ESTADISTICAS:
        if total.tiene(k):
            res["juego"].append({"nombre": nombres[k], "favor": _r(total.favor_pp(k), 2), "contra": _r(total.contra_pp(k), 2)})
    if total.tiene("tiros"):
        res["ratios"]["Dominio de tiros (TSR)"] = _r(total.dominio_tiros(), 1)
        res["ratios"]["Conversión de tiros"] = _r(total.conversion(), 1)
    if total.tiene("tiros_puerta"):
        res["ratios"]["Precisión (a puerta)"] = _r(total.precision(), 1)
        res["ratios"]["Paradas del portero"] = _r(total.paradas(), 1)
    for p in [p for p in jug if p.participa(equipo)][-10:][::-1]:
        res["ultimos"].append({"fecha": str(p.fecha), "resultado": "G" if p.ganador == equipo else "E" if p.ganador is None else "P",
                               "local": p.local, "visitante": p.visitante, "goles_local": p.goles_local,
                               "goles_visitante": p.goles_visitante, "competicion": p.competicion})
    for p in _futuros([p for p in pendientes(partidos) if p.participa(equipo)])[:5]:
        pr = mp.predecir(p.local, p.visitante, p.neutral, p.elo_local, p.elo_visitante)
        res["proximos"].append({"fecha": str(p.fecha), "local": p.local, "visitante": p.visitante,
                                "p1": _r(pr["p1"]), "px": _r(pr["px"]), "p2": _r(pr["p2"])})
    return res


def _futuros(pend):
    futuros = [p for p in pend if p.fecha >= date.today()]
    return futuros or pend


def _prediccion_futbol(mp, elo, local, visitante, neutral):
    pr = mp.predecir(local, visitante, neutral)
    return {
        "local": local, "visitante": visitante, "neutral": neutral,
        "goles_local": _r(pr["goles_local"], 2), "goles_visitante": _r(pr["goles_visitante"], 2),
        "p1": _r(pr["p1"]), "px": _r(pr["px"]), "p2": _r(pr["p2"]),
        "p1x": _r(pr["p1x"]), "px2": _r(pr["px2"]), "p12": _r(pr["p12"]),
        "mas": {str(k): _r(v) for k, v in pr["mas"].items()},
        "ambos_marcan": _r(pr["ambos_marcan"]),
        "porteria_cero_local": _r(pr["porteria_cero_local"]), "porteria_cero_visitante": _r(pr["porteria_cero_visitante"]),
        "handicap": {str(k): _r(v) for k, v in pr["handicap"].items()},
        "marcadores": [{"marcador": f"{i}-{j}", "prob": _r(v)} for i, j, v in pr["marcadores"]],
        "dist_local": [_r(v) for v in pr["goles_local_dist"]],
        "dist_visitante": [_r(v) for v in pr["goles_visitante_dist"]],
        "elo_local": _r(elo.esperado(local, visitante, neutral)),
    }


def futbol_predecir(q):
    partidos, descripcion, _ = _f_cargar(q)
    disponibles = f_equipos(partidos)
    local = elegir_equipo(q.get("local", ""), disponibles)
    visitante = elegir_equipo(q.get("visitante", ""), disponibles)
    if local == visitante:
        raise ValueError("Elige dos equipos distintos.")
    mp, elo = _futbol_modelos(*_f_args(q))
    res = _prediccion_futbol(mp, elo, local, visitante, q.get("neutral") in ("1", "true", "si"))
    res["descripcion"] = descripcion
    return res


def futbol_pronosticos(q):
    partidos, descripcion, _ = _f_cargar(q)
    pend = pendientes(partidos)
    futuros = _futuros(pend)
    mp, _ = _futbol_modelos(*_f_args(q))
    filas = []
    for p in futuros[: int(q.get("n", 20))]:
        pr = mp.predecir(p.local, p.visitante, p.neutral, p.elo_local, p.elo_visitante)
        i, j, _ = pr["marcadores"][0]
        filas.append({"fecha": str(p.fecha), "local": p.local, "visitante": p.visitante, "p1": _r(pr["p1"]),
                      "px": _r(pr["px"]), "p2": _r(pr["p2"]), "mas_2_5": _r(pr["mas"][2.5]),
                      "ambos": _r(pr["ambos_marcan"]), "marcador": f"{i}-{j}"})
    return {"descripcion": descripcion, "omitidos": len(pend) - len(futuros), "filas": filas}


def futbol_liga(q):
    partidos, descripcion, _ = _f_cargar(q)
    r = fa.resumen_liga(partidos)
    if not r["partidos"]:
        raise ValueError("No hay partidos jugados.")
    m, mg = r["mayor_goleada"], r["mas_goles"]
    res = {k: (_r(v, 2) if isinstance(v, float) else v) for k, v in r.items()
           if k not in ("mayor_goleada", "mas_goles", "marcadores", "distribucion_goles", "descanso", "juego")}
    res.update({
        "descripcion": descripcion,
        "mayor_goleada": {"fecha": str(m.fecha), "texto": m.marcador()},
        "mas_goles": {"fecha": str(mg.fecha), "texto": mg.marcador()},
        "marcadores": [{"marcador": f"{a}-{b}", "veces": v} for (a, b), v in r["marcadores"]],
        "distribucion_goles": [{"goles": g, "partidos": r["distribucion_goles"][g]} for g in range(max(r["distribucion_goles"]) + 1)],
        "juego": [{"nombre": n, "local": _r(l, 2), "visitante": _r(v, 2)} for n, (l, v, _) in r["juego"].items()],
        "descanso": None,
    })
    if "descanso" in r:
        d = r["descanso"]
        res["descanso"] = {"goles_1t_pp": _r(d["goles_1t_pp"], 2), "goles_2t_pp": _r(d["goles_2t_pp"], 2),
                           "remontadas": d["remontadas"], "partidos": d["partidos"],
                           "matriz": {k: d["matriz"].get(k, 0) for k in (f"{a}/{b}" for a in "1X2" for b in "1X2")}}
    return res


def futbol_h2h(q):
    liga, temp, torneo = _f_args(q)
    partidos, descripcion, _, _ = _futbol(liga, temp or "todas", torneo)
    partidos = list(partidos)
    disponibles = f_equipos(partidos)
    a = elegir_equipo(q.get("a", ""), disponibles)
    b = elegir_equipo(q.get("b", ""), disponibles)
    duelos, r = fa.enfrentamientos_directos(partidos, a, b)
    n = len(duelos)
    return {
        "descripcion": descripcion, "a": a, "b": b, "n": n,
        "victorias_a": r[a], "victorias_b": r[b], "empates": r["empates"],
        "goles_a": r["goles_" + a], "goles_b": r["goles_" + b],
        "ambos_marcan": _r(pct(sum(1 for p in duelos if p.goles_local and p.goles_visitante), n), 1),
        "mas_2_5": _r(pct(sum(p.total_goles > 2.5 for p in duelos), n), 1),
        "partidos": [{"fecha": str(p.fecha), "local": p.local, "visitante": p.visitante, "goles_local": p.goles_local,
                      "goles_visitante": p.goles_visitante, "penaltis": p.penaltis, "competicion": p.competicion}
                     for p in duelos[::-1]],
    }


def futbol_ranking(q):
    partidos, descripcion, _ = _f_cargar(q)
    mp, elo = _futbol_modelos(*_f_args(q))
    actuales = set(f_equipos(partidos))
    fuerza = {e: (a, d, dg) for e, a, d, dg in mp.ranking()}
    filas = []
    for e, r in elo.ranking():
        if e in actuales and e in fuerza:
            a, d, dg = fuerza[e]
            filas.append({"equipo": e, "elo": _r(r, 0), "ataque": _r(a, 2), "defensa": _r(d, 2), "dg": _r(dg, 2),
                          "historial": [_r(x, 0) for _, x in elo.historial[e][-12:]]})
    return {"descripcion": descripcion, "filas": filas}


def futbol_goleadores(q):
    partidos, descripcion, _ = _f_cargar(q)
    claves = {(str(p.fecha), p.local, p.visitante) for p in partidos}
    con = _con()
    try:
        goles = [dict(g) for g in con.execute("SELECT * FROM futbol_goleadores_selecciones WHERE autogol = 0")
                 if (g["fecha"], g["local"], g["visitante"]) in claves]
    finally:
        con.close()
    if q.get("equipo"):
        equipo = elegir_equipo(q["equipo"], sorted({g["equipo"] for g in goles}))
        goles = [g for g in goles if g["equipo"] == equipo]
    conteo = {}
    for g in goles:
        c = conteo.setdefault((g["goleador"], g["equipo"]), [0, 0, set()])
        c[0] += 1
        c[1] += g["penalti"]
        c[2].add((g["fecha"], g["local"]))
    filas = sorted(conteo.items(), key=lambda kv: (-kv[1][0], kv[1][1], kv[0][0]))[: int(q.get("n", 25))]
    tramos = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90), (91, 200)]
    minutos = [g["minuto"] for g in goles if g["minuto"] is not None]
    return {
        "descripcion": descripcion, "goles": len(goles),
        "filas": [{"jugador": j, "equipo": e, "goles": n, "penaltis": pen, "partidos": len(part)}
                  for (j, e), (n, pen, part) in filas],
        "minutos": [{"tramo": f"{a}-{b}'" if b < 200 else "90+'", "goles": sum(a <= m <= b for m in minutos)} for a, b in tramos],
    }


# ── NFL ───────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _nfl():
    con = _con()
    try:
        return tuple(nfl_cargar(con))
    finally:
        con.close()


@lru_cache(maxsize=8)
def _nfl_modelos(temporada):
    juegos = list(_nfl())
    elo, ratings = nm.ajustar_modelos(juegos, temporada)
    return elo, ratings, nm.contexto_qb(juegos)


@lru_cache(maxsize=8)
def _nfl_stats(temporada):
    con = _con()
    try:
        return tuple(ne.cargar(con, temporada, solo_regular=True))
    finally:
        con.close()


def _temporada_nfl(q):
    disponibles = nfl_temporadas(_nfl())
    t = int(q.get("temporada") or max(disponibles))
    if t not in disponibles:
        raise ValueError(f"Temporada {t} no disponible ({disponibles[0]}-{disponibles[-1]}).")
    return t


def _nfl_equipo(texto):
    t = (texto or "").strip().upper()
    todos = {e for div in DIVISIONES.values() for e in div}
    if t in todos:
        return t
    por_nombre = {nfl_nombre(e): e for e in todos}
    return por_nombre[elegir_equipo(texto or "", list(por_nombre))]


def nfl_opciones(q):
    return {"temporadas": nfl_temporadas(_nfl())[::-1],
            "equipos": [{"codigo": e, "nombre": nfl_nombre(e), "division": d} for d, eqs in DIVISIONES.items() for e in eqs]}


def _fila_clasificacion(f, siembra=None):
    t = f.total
    return {"equipo": f.equipo, "nombre": nfl_nombre(f.equipo), "siembra": siembra, "g": t.g, "p": t.p, "e": t.e,
            "pct": _r(t.porcentaje), "pf": t.pf, "pc": t.pc, "dif": t.diferencia, "local": f.local.texto(),
            "visitante": f.visitante.texto(), "division": f.division.texto(), "conferencia": f.conferencia.texto(),
            "racha": f.racha, "ultimos": f.ultimos}


def nfl_clasificacion(q):
    t = _temporada_nfl(q)
    filas = na.clasificacion(list(_nfl()), t)
    if not filas:
        raise ValueError(f"No hay partidos de temporada regular en {t}.")
    res = {"temporada": t, "divisiones": [], "playoffs": []}
    for div, lista in na.por_division(filas).items():
        res["divisiones"].append({"division": div, "filas": [_fila_clasificacion(f) for f in lista]})
    for conf in ("AFC", "NFC"):
        dentro, fuera = na.siembra_playoffs(filas, conf)
        res["playoffs"].append({"conferencia": conf,
                                "dentro": [_fila_clasificacion(f, i) for i, f in enumerate(dentro, 1)],
                                "fuera": [_fila_clasificacion(f) for f in fuera]})
    return res


def _registro(r):
    return {"texto": r.texto(), "pf_pp": _r(r.pf_pp, 1), "pc_pp": _r(r.pc_pp, 1), "ats": r.texto_ats(), "ou": r.texto_ou()}


def nfl_equipo(q):
    t = _temporada_nfl(q)
    equipo = _nfl_equipo(q.get("equipo"))
    juegos = list(_nfl())
    temporada = [j for j in juegos if j.temporada == t]
    vs = na.vistas(temporada, equipo)
    if not vs:
        raise ValueError(f"{equipo} no tiene partidos jugados en {t}.")
    elo, ratings, ctx = _nfl_modelos(t)
    reg = na.Registro.de([v for v in vs if v.juego.tipo == "REG"])
    ranking_elo = [e for e, _ in elo.ranking() if division(e)]
    ranking_srs = [e for e, *_ in ratings.ranking() if division(e)]
    res = {
        "temporada": t, "equipo": equipo, "nombre": nfl_nombre(equipo), "division": division(equipo),
        "registro": {"texto": reg.texto(), "pct": _r(reg.porcentaje), "pf": reg.pf, "pc": reg.pc, "dif": reg.diferencia,
                     "pf_pp": _r(reg.pf_pp, 1), "pc_pp": _r(reg.pc_pp, 1),
                     "pitagoricas": _r(reg.victorias_pitagoricas, 1), "reales": reg.g + 0.5 * reg.e},
        "racha": na.racha(vs),
        "elo": {"rating": _r(elo.rating.get(equipo), 0), "puesto": ranking_elo.index(equipo) + 1 if equipo in ranking_elo else None,
                "historial": [_r(r, 0) for tt, _, r in elo.historial[equipo] if tt == t]},
        "srs": {"valor": _r(ratings.srs(equipo), 1), "puesto": ranking_srs.index(equipo) + 1 if equipo in ranking_srs else None,
                "ofensa": _r(ratings.ofensa.get(equipo), 1), "defensa": _r(ratings.defensa.get(equipo), 1)},
        "splits": [{"situacion": n, **_registro(r)} for n, r in na.splits(temporada, equipo)],
        "qbs": [{"qb": qb, **_registro(r)} for qb, r in na.registro_por_qb(temporada, equipo)],
        "partidos": [],
        "proximos": [],
        "juego": None,
    }
    for v in vs:
        j = v.juego
        res["partidos"].append({"semana": j.tipo if j.es_playoff else j.semana, "fecha": str(j.fecha), "rival": v.rival,
                                "local": v.es_local, "resultado": {"G": "W", "P": "L", "E": "T"}[v.resultado],
                                "pf": v.pf, "pc": v.pc, "linea": None if v.linea is None else -v.linea or 0.0,
                                "ats": v.ats, "total_linea": j.total_linea, "ou": v.over_under})
    for j in [j for j in temporada if not j.jugado and j.participa(equipo)][:4]:
        pr = nm.predecir_juego(elo, ratings, j, ctx)
        p_eq = pr["prob_local"] if j.local == equipo else 1 - pr["prob_local"]
        m_eq = pr["margen"] if j.local == equipo else -pr["margen"]
        res["proximos"].append({"semana": j.semana, "fecha": str(j.fecha), "rival": j.visitante if j.local == equipo else j.local,
                                "local": j.local == equipo, "prob": _r(p_eq), "margen": _r(m_eq, 1)})
    resumenes = ne.por_equipo(list(_nfl_stats(t)))
    r = resumenes.get(equipo)
    if r:
        filas = []
        for m, (etiqueta, mayor) in ne.METRICAS.items():
            if m in ("sacks", "sacks_recibidos", "penalizaciones", "yardas_penalizacion"):
                continue
            fav = sorted(resumenes.values(), key=lambda x: -x.favor_pp(m) if mayor else x.favor_pp(m))
            con = sorted(resumenes.values(), key=lambda x: x.contra_pp(m) if mayor else -x.contra_pp(m))
            filas.append({"metrica": etiqueta, "ataque": _r(r.favor_pp(m), 3), "puesto_ataque": [x.equipo for x in fav].index(equipo) + 1,
                          "defensa": _r(r.contra_pp(m), 3), "puesto_defensa": [x.equipo for x in con].index(equipo) + 1})
        res["juego"] = {"filas": filas, "sacks": _r(r.favor_pp("sacks"), 1), "sacks_recibidos": _r(r.favor_pp("sacks_recibidos"), 1),
                        "dif_perdidas": r.diferencial_perdidas, "penalizaciones": _r(r.favor_pp("penalizaciones"), 1),
                        "fg": f"{r.favor['fg_hechos']:.0f}/{r.favor['fg_intentos']:.0f}"}
    return res


def _pred_nfl(pr):
    return {"margen": _r(pr["margen"], 1), "margen_elo": _r(pr["margen_elo"], 1), "margen_ratings": _r(pr["margen_ratings"], 1),
            "prob_local": _r(pr["prob_local"]), "total": _r(pr["total"], 1),
            "puntos_local": _r(pr["puntos_local"], 1), "puntos_visitante": _r(pr["puntos_visitante"], 1)}


def nfl_predecir(q):
    t = _temporada_nfl(q)
    local, visitante = _nfl_equipo(q.get("local")), _nfl_equipo(q.get("visitante"))
    if local == visitante:
        raise ValueError("Elige dos equipos distintos.")
    neutral = q.get("neutral") in ("1", "true", "si")
    elo, ratings, ctx = _nfl_modelos(t)
    programado = next((j for j in _nfl() if j.temporada == t and not j.jugado
                       and j.local == local and j.visitante == visitante), None)
    if programado and not neutral:
        pr = nm.predecir_juego(elo, ratings, programado, ctx)
    else:
        pr = nm.predecir(elo, ratings, local, visitante, neutral)
    linea = q.get("linea") or (programado.linea if programado else None)
    total = q.get("total") or (programado.total_linea if programado else None)
    res = {"temporada": t, "local": local, "visitante": visitante, "nombre_local": nfl_nombre(local),
           "nombre_visitante": nfl_nombre(visitante), "neutral": neutral,
           "programado": {"semana": programado.semana, "fecha": str(programado.fecha)} if programado else None,
           **_pred_nfl(pr), "linea": None, "total_linea": None}
    if linea not in (None, ""):
        linea = float(linea)
        res["linea"] = linea
        res["prob_cubre_local"] = _r(nm.prob_cubrir(pr["margen"], linea))
    if total not in (None, ""):
        total = float(total)
        res["total_linea"] = total
        res["prob_over"] = _r(1 - normal_cdf(total, pr["total"], nm.DESVIACION_MARGEN))
    return res


def nfl_pronosticos(q):
    t = _temporada_nfl(q)
    pend = [j for j in _nfl() if j.temporada == t and not j.jugado]
    if not pend:
        return {"temporada": t, "semana": None, "filas": []}
    semana = int(q.get("semana") or min(j.semana for j in pend if j.tipo == pend[0].tipo))
    elo, ratings, ctx = _nfl_modelos(t)
    filas = []
    for j in [j for j in pend if j.semana == semana]:
        pr = nm.predecir_juego(elo, ratings, j, ctx)
        filas.append({"fecha": str(j.fecha), "local": j.local, "visitante": j.visitante, **_pred_nfl(pr),
                      "linea": j.linea, "total_linea": j.total_linea})
    return {"temporada": t, "semana": semana, "semanas": sorted({j.semana for j in pend}), "filas": filas}


@lru_cache(maxsize=8)
def _simulacion(t, n):
    return nm.simular_temporada(list(_nfl()), t, n, semilla=1)


def nfl_simular(q):
    t = _temporada_nfl(q)
    n = min(int(q.get("n", 5000)), 20000)
    res, pendientes_n = _simulacion(t, n)
    conferencias = []
    for conf in ("AFC", "NFC"):
        eqs = sorted((e for e in res if conferencia(e) == conf),
                     key=lambda e: (-res[e].get("playoffs", 0), -res[e].get("victorias", 0)))
        conferencias.append({"conferencia": conf, "filas": [
            {"equipo": e, "nombre": nfl_nombre(e), "victorias": _r(res[e].get("victorias", 0), 1),
             "playoffs": _r(res[e].get("playoffs", 0)), "division": _r(res[e].get("division", 0)),
             "primero": _r(res[e].get("primero", 0))} for e in eqs]})
    return {"temporada": t, "simulaciones": n, "pendientes": pendientes_n, "conferencias": conferencias}


def nfl_ranking(q):
    t = _temporada_nfl(q)
    elo, ratings, _ = _nfl_modelos(t)
    filas = na.clasificacion(list(_nfl()), t)
    srs = {e: (o, d, s) for e, o, d, s in ratings.ranking() if division(e)}
    pos_elo = {e: i for i, (e, _) in enumerate(elo.ranking())}
    pos_srs = {e: i for i, e in enumerate(srs)}
    orden = sorted(srs, key=lambda e: (pos_elo.get(e, 99) + pos_srs[e], -srs[e][2]))
    return {"temporada": t, "ventaja_campo": _r(ratings.ventaja_campo, 1), "filas": [
        {"equipo": e, "nombre": nfl_nombre(e), "registro": filas[e].total.texto() if e in filas else "",
         "elo": _r(elo.rating.get(e, 1500), 0), "srs": _r(srs[e][2], 1), "ofensa": _r(srs[e][0], 1), "defensa": _r(srs[e][1], 1),
         "pitagoricas": _r(filas[e].total.victorias_pitagoricas, 1) if e in filas else None,
         "historial": [_r(r, 0) for tt, _, r in elo.historial[e] if tt == t]} for e in orden]}


def nfl_estadisticas(q):
    t = _temporada_nfl(q)
    resumenes = ne.por_equipo(list(_nfl_stats(t)))
    if not resumenes:
        raise ValueError(f"No hay estadísticas de juego para {t}.")
    filas = [{"equipo": r.equipo, "nombre": nfl_nombre(r.equipo), "yardas": _r(r.favor_pp("yardas"), 1),
              "yardas_permitidas": _r(r.contra_pp("yardas"), 1), "yardas_jugada": _r(r.favor_pp("yardas_jugada"), 2),
              "epa_of": _r(r.favor_pp("epa_jugada"), 3), "epa_def": _r(r.contra_pp("epa_jugada"), 3),
              "dif_perdidas": r.diferencial_perdidas, "sacks": _r(r.favor_pp("sacks"), 1),
              "sacks_recibidos": _r(r.favor_pp("sacks_recibidos"), 1), "pase": _r(r.favor_pp("yardas_pase"), 1),
              "carrera": _r(r.favor_pp("yardas_carrera"), 1), "explosivas": _r(r.favor_pp("explosivas"), 1),
              "yardas_penalizacion": _r(r.favor_pp("yardas_penalizacion"), 1)} for r in resumenes.values()]
    filas.sort(key=lambda f: -f["epa_of"])
    return {"temporada": t, "filas": filas}


def nfl_liga(q):
    t = _temporada_nfl(q)
    temporada = [j for j in _nfl() if j.temporada == t]
    r = na.resumen_liga(temporada)
    if not r["partidos"]:
        raise ValueError("No hay partidos jugados.")
    res = {k: (_r(v, 2) if isinstance(v, float) else v) for k, v in r.items()
           if k not in ("mas_puntos", "menos_puntos", "mayor_paliza", "margenes_frecuentes", "puntos_por_techo",
                        "puntos_frio", "puntos_viento", "puntos_divisionales")}
    res["temporada"] = t
    res["margenes_frecuentes"] = [{"margen": m, "partidos": v} for m, v in r["margenes_frecuentes"]]
    for k in ("mas_puntos", "menos_puntos", "mayor_paliza"):
        res[k] = {"texto": r[k].marcador(), "semana": r[k].semana}
    condiciones = [{"condicion": k, "puntos": _r(m, 1), "partidos": n} for k, (m, n) in r["puntos_por_techo"].items()]
    for clave, texto in (("puntos_frio", "Frío (≤40 °F)"), ("puntos_viento", "Viento (≥15 mph)"),
                         ("puntos_divisionales", "Partidos divisionales")):
        if clave in r:
            condiciones.append({"condicion": texto, "puntos": _r(r[clave][0], 1), "partidos": r[clave][1]})
    res["condiciones"] = condiciones
    factores = ne.factores_victoria(list(_nfl_stats(t)), temporada)
    res["factores"] = [{"metrica": ne.METRICAS[m][0], "pct": _r(p, 1), "partidos": n}
                       for m, (p, n) in sorted(factores.items(), key=lambda kv: -kv[1][0])]
    return res


# ── NBA ───────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _nba():
    con = _con()
    try:
        return tuple(nba_cargar(con))
    finally:
        con.close()


@lru_cache(maxsize=8)
def _nba_modelos(temporada):
    return bm.ajustar_modelos(list(_nba()), temporada)


@lru_cache(maxsize=8)
def _nba_stats(temporada):
    con = _con()
    try:
        return tuple(be.cargar(con, temporada))
    finally:
        con.close()


def _nba_temporadas():
    return sorted({p.temporada for p in _nba()})


def _temporada_nba(q, con_resultados=False):
    """Temporada pedida (2026 o "2025-26"). con_resultados: si aún no ha empezado, la anterior."""
    disponibles = _nba_temporadas()
    t = leer_temporada(q.get("temporada")) if q.get("temporada") else max(disponibles)
    if t not in disponibles:
        raise ValueError(f"Temporada {texto_temporada(t)} no disponible "
                         f"({texto_temporada(disponibles[0])} a {texto_temporada(disponibles[-1])}).")
    if con_resultados and not any(p.jugado for p in _nba() if p.temporada == t) and t - 1 in disponibles:
        return t - 1, f"La temporada {texto_temporada(t)} aún no ha empezado: se muestra la {texto_temporada(t - 1)}."
    return t, None


def _nba_equipo(texto):
    t = (texto or "").strip().upper()
    todos = {e for div in NBA_DIVISIONES.values() for e in div}
    if t in todos:
        return t
    por_nombre = {nba_nombre(e): e for e in todos}
    return por_nombre[elegir_equipo(texto or "", list(por_nombre))]


def nba_opciones(q):
    return {"temporadas": [{"valor": t, "texto": texto_temporada(t)} for t in _nba_temporadas()[::-1]],
            "equipos": [{"codigo": e, "nombre": nba_nombre(e), "division": d} for d, eqs in NBA_DIVISIONES.items() for e in eqs]}


def _fila_nba(f, pos=None):
    t = f.total
    return {"equipo": f.equipo, "nombre": nba_nombre(f.equipo), "pos": pos, "g": t.g, "p": t.p, "pct": _r(t.porcentaje),
            "pf_pp": _r(t.pf_pp, 1), "pc_pp": _r(t.pc_pp, 1), "dif_pp": _r(t.dif_pp, 1), "local": f.local.texto(),
            "visitante": f.visitante.texto(), "conferencia": f.conferencia.texto(), "racha": f.racha, "ultimos": f.ultimos}


def nba_clasificacion(q):
    t, _ = _temporada_nba(q)
    filas = ba.clasificacion(list(_nba()), t)
    if not filas:
        raise ValueError(f"No hay partidos de temporada regular en {texto_temporada(t)}.")
    return {"temporada": texto_temporada(t), "playin": t >= 2021,
            "conferencias": [{"conferencia": c, "filas": [_fila_nba(f, i) for i, f in enumerate(lista, 1)]}
                             for c, lista in ba.por_conferencia(filas, t).items()],
            "divisiones": [{"division": d, "filas": [_fila_nba(f) for f in lista]} for d, lista in ba.por_division(filas).items()]}


def _pred_nba(pr):
    return {"margen": _r(pr["margen"], 1), "margen_elo": _r(pr["margen_elo"], 1), "margen_ratings": _r(pr["margen_ratings"], 1),
            "ajuste": _r(pr["ajuste"], 1), "prob_local": _r(pr["prob_local"]), "total": _r(pr["total"], 1),
            "puntos_local": _r(pr["puntos_local"], 1), "puntos_visitante": _r(pr["puntos_visitante"], 1)}


def nba_equipo(q):
    t, _ = _temporada_nba(q)
    equipo = _nba_equipo(q.get("equipo"))
    partidos = list(_nba())
    temporada = [p for p in partidos if p.temporada == t]
    filas = ba.clasificacion(partidos, t)
    elo, ratings = _nba_modelos(t)
    vs = ba.vistas(temporada, equipo)
    reg = ba.Registro.de([v for v in vs if v.partido.tipo == "REG"])
    pos = next((i for lista in ba.por_conferencia(filas, t).values() for i, f in enumerate(lista, 1) if f.equipo == equipo), None)
    ranking_elo = [e for e, _ in elo.ranking() if nba_division(e)]
    ranking_neto = [e for e, *_ in ratings.ranking() if nba_division(e)]
    res = {
        "temporada": texto_temporada(t), "equipo": equipo, "nombre": nba_nombre(equipo), "division": nba_division(equipo),
        "registro": {"texto": reg.texto(), "jugados": reg.jugados, "pct": _r(reg.porcentaje), "pf_pp": _r(reg.pf_pp, 1),
                     "pc_pp": _r(reg.pc_pp, 1), "dif_pp": _r(reg.dif_pp, 1), "pitagoricas": _r(reg.victorias_pitagoricas, 1),
                     "reales": reg.g, "puesto": pos if reg.jugados else None},
        "racha": ba.racha(vs),
        "elo": {"rating": _r(elo.rating.get(equipo, 1500), 0), "puesto": ranking_elo.index(equipo) + 1 if equipo in ranking_elo else None,
                "historial": [_r(r, 0) for tt, _, r in elo.historial[equipo] if tt == t]},
        "neto": {"valor": _r(ratings.neto(equipo), 1), "puesto": ranking_neto.index(equipo) + 1 if equipo in ranking_neto else None,
                 "ataque": _r(ratings.ofensa.get(equipo), 1), "defensa": _r(ratings.defensa.get(equipo), 1)},
        "splits": [{"situacion": n, "texto": r.texto(), "pf_pp": _r(r.pf_pp, 1), "pc_pp": _r(r.pc_pp, 1)}
                   for n, r in (ba.splits(temporada, equipo, filas) if vs else [])],
        "partidos": [{"fecha": str(v.partido.fecha), "rival": v.rival, "local": v.es_local, "resultado": "V" if v.resultado == "G" else "D",
                      "pf": v.pf, "pc": v.pc, "prorroga": v.partido.prorrogas > 0,
                      "fase": "" if v.partido.tipo == "REG" else (v.partido.ronda or NBA_TIPO[v.partido.tipo])} for v in vs][::-1],
        "proximos": [],
        "juego": None,
    }
    dias = descansos(temporada)
    for p in [p for p in temporada if not p.jugado and p.participa(equipo)][:5]:
        pr = bm.predecir_partido(elo, ratings, p, dias)
        p_eq = pr["prob_local"] if p.local == equipo else 1 - pr["prob_local"]
        m_eq = pr["margen"] if p.local == equipo else -pr["margen"]
        res["proximos"].append({"fecha": str(p.fecha), "rival": p.visitante if p.local == equipo else p.local,
                                "local": p.local == equipo, "prob": _r(p_eq), "margen": _r(m_eq, 1)})
    resumenes = be.por_equipo(list(_nba_stats(t)))
    r = resumenes.get(equipo)
    if r:
        filas_j = []
        for m, (etiqueta, mayor) in be.METRICAS.items():
            fav = sorted(resumenes.values(), key=lambda x: -x.favor_de(m) if mayor else x.favor_de(m))
            con = sorted(resumenes.values(), key=lambda x: x.contra_de(m) if mayor else -x.contra_de(m))
            filas_j.append({"metrica": etiqueta, "ataque": _r(r.favor_de(m), 3), "puesto_ataque": [x.equipo for x in fav].index(equipo) + 1,
                            "defensa": _r(r.contra_de(m), 3), "puesto_defensa": [x.equipo for x in con].index(equipo) + 1})
        res["juego"] = {"filas": filas_j, "neto": _r(r.neto, 1)}
    return res


def nba_predecir(q):
    t, _ = _temporada_nba(q)
    local, visitante = _nba_equipo(q.get("local")), _nba_equipo(q.get("visitante"))
    if local == visitante:
        raise ValueError("Elige dos equipos distintos.")
    neutral = q.get("neutral") in ("1", "true", "si")
    elo, ratings = _nba_modelos(t)
    temporada = [p for p in _nba() if p.temporada == t]
    programado = next((p for p in temporada if not p.jugado and p.local == local and p.visitante == visitante), None)
    if programado and not neutral:
        pr = bm.predecir_partido(elo, ratings, programado, descansos(temporada))
    else:
        pr = bm.predecir(elo, ratings, local, visitante, neutral)
    return {"temporada": texto_temporada(t), "local": local, "visitante": visitante, "nombre_local": nba_nombre(local),
            "nombre_visitante": nba_nombre(visitante), "neutral": neutral,
            "programado": {"fecha": str(programado.fecha)} if programado and not neutral else None,
            "moneyline_local": bm.moneyline_justa(pr["prob_local"]), "moneyline_visitante": bm.moneyline_justa(1 - pr["prob_local"]),
            **_pred_nba(pr)}


def nba_pronosticos(q):
    t, _ = _temporada_nba(q)
    temporada = [p for p in _nba() if p.temporada == t]
    pend = [p for p in temporada if not p.jugado]
    if not pend:
        return {"temporada": texto_temporada(t), "fecha": None, "fechas": [], "filas": []}
    fechas = sorted({str(p.fecha) for p in pend})
    fecha = q.get("fecha") if q.get("fecha") in fechas else fechas[0]
    elo, ratings = _nba_modelos(t)
    dias = descansos(temporada)
    filas = [{"fecha": str(p.fecha), "local": p.local, "visitante": p.visitante, "neutral": p.neutral,
              **_pred_nba(bm.predecir_partido(elo, ratings, p, dias))} for p in pend if str(p.fecha) == fecha]
    return {"temporada": texto_temporada(t), "fecha": fecha, "fechas": fechas, "filas": filas}


@lru_cache(maxsize=8)
def _nba_simulacion(t, n):
    return bm.simular_temporada(list(_nba()), t, n, semilla=1)


def nba_simular(q):
    t, _ = _temporada_nba(q)
    n = min(int(q.get("n", 2000)), 10000)
    res, pendientes_n = _nba_simulacion(t, n)
    conferencias = []
    for conf in CONFERENCIAS:
        eqs = sorted((e for e in res if ba.conferencia(e, t) == conf),
                     key=lambda e: (-res[e].get("playoffs", 0), -res[e].get("victorias", 0)))
        conferencias.append({"conferencia": conf, "filas": [
            {"equipo": e, "nombre": nba_nombre(e), "victorias": _r(res[e].get("victorias", 0), 1),
             **{k: _r(res[e].get(k, 0)) for k in ("playoffs", "top6", "primero", "final", "campeon")}} for e in eqs]})
    return {"temporada": texto_temporada(t), "simulaciones": n, "pendientes": pendientes_n, "playin": t >= 2021,
            "conferencias": conferencias}


def nba_ranking(q):
    t, _ = _temporada_nba(q)
    elo, ratings = _nba_modelos(t)
    filas = ba.clasificacion(list(_nba()), t)
    netos = {e: (o, d, s) for e, o, d, s in ratings.ranking() if nba_division(e)}
    pos_elo = {e: i for i, (e, _) in enumerate(elo.ranking())}
    pos_neto = {e: i for i, e in enumerate(netos)}
    orden = sorted(netos, key=lambda e: (pos_elo.get(e, 99) + pos_neto[e], -netos[e][2]))
    jugado = lambda e: e in filas and filas[e].total.jugados  # noqa: E731
    return {"temporada": texto_temporada(t), "ventaja_campo": _r(ratings.ventaja_campo, 1), "filas": [
        {"equipo": e, "nombre": nba_nombre(e), "registro": filas[e].total.texto() if jugado(e) else "",
         "elo": _r(elo.rating.get(e, 1500), 0), "neto": _r(netos[e][2], 1), "ataque": _r(netos[e][0], 1),
         "defensa": _r(netos[e][1], 1), "pitagoricas": _r(filas[e].total.victorias_pitagoricas, 1) if jugado(e) else None,
         "historial": [_r(r, 0) for tt, _, r in elo.historial[e] if tt == t]} for e in orden]}


def nba_estadisticas(q):
    t, aviso = _temporada_nba(q, con_resultados=True)
    resumenes = be.por_equipo(list(_nba_stats(t)))
    if not resumenes:
        raise ValueError(f"No hay estadísticas de juego para {texto_temporada(t)}.")
    filas = [{"equipo": r.equipo, "nombre": nba_nombre(r.equipo), "neto": _r(r.neto, 1),
              "ataque": _r(r.favor_de("eficiencia"), 1), "defensa": _r(r.contra_de("eficiencia"), 1),
              "ritmo": _r(r.favor_de("ritmo"), 1), "efg": _r(r.favor_de("efg"), 1), "efg_rival": _r(r.contra_de("efg"), 1),
              "perdidas": _r(r.favor_de("pct_perdidas"), 1), "rebote_of": _r(r.favor_de("pct_rebote_of"), 1),
              "libres": _r(r.favor_de("tasa_libres"), 3), "pct_triple": _r(r.favor_de("pct_triple"), 1),
              "tasa_triples": _r(r.favor_de("tasa_triples"), 1), "asistencias": _r(r.favor_de("asistencias"), 1)}
             for r in resumenes.values()]
    filas.sort(key=lambda f: -f["neto"])
    return {"temporada": texto_temporada(t), "aviso": aviso, "filas": filas}


def nba_liga(q):
    t, aviso = _temporada_nba(q, con_resultados=True)
    r = ba.resumen_liga([p for p in _nba() if p.temporada == t])
    if not r["partidos"]:
        raise ValueError("No hay partidos jugados.")
    res = {k: (_r(v, 2) if isinstance(v, float) else v) for k, v in r.items()
           if k not in ("mas_puntos", "menos_puntos", "mayor_paliza", "margenes_frecuentes")}
    res.update({"temporada": texto_temporada(t), "aviso": aviso,
                "margenes_frecuentes": sorted(({"margen": m, "partidos": v} for m, v in r["margenes_frecuentes"]), key=lambda x: x["margen"])})
    for k in ("mas_puntos", "menos_puntos", "mayor_paliza"):
        res[k] = {"texto": r[k].marcador(), "fecha": str(r[k].fecha)}
    factores = be.factores_victoria(list(_nba_stats(t)))
    res["factores"] = [{"metrica": be.METRICAS[m][0], "pct": _r(p, 1), "partidos": n}
                       for m, (p, n) in sorted(factores.items(), key=lambda kv: -kv[1][0])]
    return res


RUTAS = {
    "futbol/opciones": futbol_opciones, "futbol/tabla": futbol_tabla, "futbol/equipos": futbol_equipos,
    "futbol/equipo": futbol_equipo, "futbol/predecir": futbol_predecir, "futbol/pronosticos": futbol_pronosticos,
    "futbol/liga": futbol_liga, "futbol/h2h": futbol_h2h, "futbol/ranking": futbol_ranking,
    "futbol/goleadores": futbol_goleadores,
    "nfl/opciones": nfl_opciones, "nfl/clasificacion": nfl_clasificacion, "nfl/equipo": nfl_equipo,
    "nfl/predecir": nfl_predecir, "nfl/pronosticos": nfl_pronosticos, "nfl/simular": nfl_simular,
    "nfl/ranking": nfl_ranking, "nfl/estadisticas": nfl_estadisticas, "nfl/liga": nfl_liga,
    "nba/opciones": nba_opciones, "nba/clasificacion": nba_clasificacion, "nba/equipo": nba_equipo,
    "nba/predecir": nba_predecir, "nba/pronosticos": nba_pronosticos, "nba/simular": nba_simular,
    "nba/ranking": nba_ranking, "nba/estadisticas": nba_estadisticas, "nba/liga": nba_liga,
}


def ejecutar(ruta, consulta):
    """Ejecuta una ruta de la API. Lanza KeyError si no existe y ValueError ante datos inválidos."""
    return RUTAS[ruta](consulta)

