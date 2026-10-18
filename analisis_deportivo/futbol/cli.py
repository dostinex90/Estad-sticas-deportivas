"""Comandos de línea de comandos para fútbol."""

import argparse
from datetime import date

from ..comun import barra, chispa, elegir_equipo, linea_pct, pct, racha_actual, racha_maxima, salir
from . import analisis, modelos
from .. import base
from .datos import cargar_desde_base, cargar_partidos, equipos, jugados, pendientes

NOMBRES_RACHA = {"G": ("victoria", "victorias"), "E": ("empate", "empates"), "P": ("derrota", "derrotas")}
NOMBRES_JUEGO = {
    "tiros": "Tiros", "tiros_puerta": "Tiros a puerta", "corners": "Córners",
    "faltas": "Faltas", "amarillas": "Amarillas", "rojas": "Rojas",
}


def _titulo(texto):
    print(f"\n{texto}\n{'═' * len(texto)}")


def _seccion(texto):
    print(f"\n── {texto} " + "─" * max(0, 60 - len(texto)))


def total_equipos(partidos):
    return set(equipos(partidos))


def _para_modelo(jug, args):
    """Partidos para entrenar modelos: los analizados más la temporada anterior, si la base la tiene."""
    return list(getattr(args, "previos", [])) + jug


def _filtrar(partidos, args):
    if args.desde:
        partidos = [p for p in partidos if p.fecha >= args.desde]
    if args.hasta:
        partidos = [p for p in partidos if p.fecha <= args.hasta]
    return partidos


def cmd_equipos(partidos, args):
    for e in equipos(partidos):
        print(e)


def cmd_tabla(partidos, args):
    if args.condicion == "descanso":
        tabla = analisis.tabla_descanso(partidos)
        titulo = "Clasificación si los partidos acabaran al descanso"
    else:
        tabla = analisis.tabla_posiciones(partidos, args.condicion)
        titulo = {None: "Clasificación general", "local": "Clasificación como local",
                  "visitante": "Clasificación como visitante"}[args.condicion]
    _titulo(titulo)
    ancho = max([len(s.equipo) for s in tabla] + [6])
    print(f"{'#':>3}  {'Equipo':<{ancho}}{'PJ':>4}{'G':>4}{'E':>4}{'P':>4}{'GF':>5}{'GC':>5}{'DG':>5}{'Pts':>5}{'PPP':>6}  Forma")
    print("─" * (ancho + 55))
    for pos, s in enumerate(tabla, 1):
        print(
            f"{pos:>3}  {s.equipo:<{ancho}}{s.jugados:>4}{s.ganados:>4}{s.empatados:>4}{s.perdidos:>4}"
            f"{s.goles_favor:>5}{s.goles_contra:>5}{s.diferencia:>+5}{s.puntos:>5}{s.puntos_por_partido:>6.2f}  {s.forma()}"
        )


def _bloque_basico(s):
    print(f"  Partidos {s.jugados}: {s.ganados}G {s.empatados}E {s.perdidos}P   Puntos {s.puntos} ({s.puntos_por_partido:.2f} por partido)")
    print(f"  Goles {s.goles_favor}-{s.goles_contra} (DG {s.diferencia:+d})   "
          f"a favor {s.goles_favor_por_partido:.2f}/p · en contra {s.goles_contra_por_partido:.2f}/p")
    print(linea_pct("% victorias", s.porcentaje_victorias))


def cmd_equipo(partidos, args):
    jug = jugados(partidos)
    equipo = elegir_equipo(args.equipo, equipos(jug))
    total = analisis.calcular_estadisticas(jug)[equipo]
    local = analisis.calcular_estadisticas(jug, "local").get(equipo)
    visit = analisis.calcular_estadisticas(jug, "visitante").get(equipo)
    tabla = analisis.tabla_posiciones(jug)
    posicion = next(i for i, s in enumerate(tabla, 1) if s.equipo == equipo)

    _titulo(f"Informe de {equipo} — {posicion}º de {len(tabla)}")

    _seccion("Rendimiento")
    for nombre, s in (("Total", total), ("Local", local), ("Visitante", visit)):
        if s:
            print(f" [{nombre}]")
            _bloque_basico(s)

    _seccion("Forma y rachas")
    r, n = racha_actual(total.resultados)
    print(f"  Últimos 10: {total.forma(10)}   Racha actual: {n} {NOMBRES_RACHA[r][n != 1]}")
    print(f"  Mejor racha de victorias: {racha_maxima(total.resultados, 'G')}   "
          f"Mayor racha invicto: {racha_maxima(total.resultados, 'GE')}   "
          f"Mayor racha sin ganar: {racha_maxima(total.resultados, 'EP')}")
    ultimos = total.resultados[-5:]
    previos = total.resultados[:-5]
    if previos:
        ppp = lambda rs: sum(3 if x == "G" else 1 if x == "E" else 0 for x in rs) / len(rs)
        print(f"  Puntos por partido: últimos 5 = {ppp(ultimos):.2f}  vs  resto = {ppp(previos):.2f}")

    _seccion("Mercados de goles (% de sus partidos)")
    print(linea_pct("Porterías a cero", pct(total.porterias_cero, total.jugados)))
    print(linea_pct("Se queda sin marcar", pct(total.sin_marcar, total.jugados)))
    print(linea_pct("Marcan ambos", pct(total.ambos_marcan, total.jugados)))
    print(linea_pct("Más de 1.5 goles", pct(total.mas_1_5, total.jugados)))
    print(linea_pct("Más de 2.5 goles", pct(total.mas_2_5, total.jugados)))
    print(linea_pct("Más de 3.5 goles", pct(total.mas_3_5, total.jugados)))
    frec = ", ".join(f"{a}-{b} ({v})" for (a, b), v in total.marcadores.most_common(5))
    print(f"  Marcadores más repetidos: {frec}")

    if total.con_descanso:
        _seccion("Primera y segunda parte")
        print(f"  Goles 1ª parte: {total.goles_favor_1t}-{total.goles_contra_1t}   "
              f"2ª parte: {total.goles_favor_2t}-{total.goles_contra_2t}")
        print(f"  Al descanso: ganando {total.ganando_descanso}, empatando {total.empatando_descanso}, "
              f"perdiendo {total.perdiendo_descanso}")
        if total.ganando_descanso:
            print(linea_pct("Gana si va ganando", pct(total.gano_tras_ganar_descanso, total.ganando_descanso), 26))
        if total.perdiendo_descanso:
            print(linea_pct("Puntúa si va perdiendo", pct(total.no_perdio_tras_perder_descanso, total.perdiendo_descanso), 26))
            print(f"  Remontadas completas (perdía al descanso y ganó): {total.gano_tras_perder_descanso}")

    disponibles = [n for n in NOMBRES_JUEGO if total.tiene(n)]
    if disponibles:
        _seccion("Estadísticas de juego (por partido)")
        print(f"  {'':<16}{'A favor':>9}{'En contra':>11}")
        for n in disponibles:
            print(f"  {NOMBRES_JUEGO[n]:<16}{total.favor_pp(n):>9.2f}{total.contra_pp(n):>11.2f}")
        if total.tiene("tiros"):
            print(linea_pct("Dominio de tiros (TSR)", total.dominio_tiros(), 26))
            print(linea_pct("Conversión de tiros", total.conversion(), 26))
        if total.tiene("tiros_puerta"):
            print(linea_pct("Precisión (a puerta)", total.precision(), 26))
            print(linea_pct("Gol por tiro a puerta", total.eficacia_a_puerta(), 26))
            print(linea_pct("Paradas del portero", total.paradas(), 26))

    _seccion("Contra rivales según su posición")
    for g in analisis.rendimiento_por_nivel(jug, equipo):
        print(f"  {g.equipo:<12} {g.jugados:>2} PJ  {g.ganados}G {g.empatados}E {g.perdidos}P  "
              f"goles {g.goles_favor}-{g.goles_contra}  {g.puntos_por_partido:.2f} pts/p")

    _seccion("Evolución en la clasificación")
    evo = analisis.evolucion_posiciones(jug, equipo)
    posiciones = [pos for _, pos, _ in evo]
    print(f"  Posición (alto = mejor): {chispa([-x for x in posiciones])}  "
          f"mejor {min(posiciones)}º, peor {max(posiciones)}º, actual {posiciones[-1]}º")
    print(f"  Puntos acumulados:       {chispa([pts for _, _, pts in evo])}")

    _seccion("Modelos")
    elo = modelos.EloFutbol().procesar(_para_modelo(jug, args))
    ranking_elo = [e for e, _ in elo.ranking() if e in total_equipos(jug)]
    print(f"  Elo: {elo.rating[equipo]:.0f} ({ranking_elo.index(equipo) + 1}º)  "
          f"tendencia {chispa([r for _, r in elo.historial[equipo]])}")
    mp = modelos.ModeloPoisson().ajustar(_para_modelo(jug, args))
    print(f"  Fuerza de ataque: {mp.ataque[equipo]:.2f}   Fuerza defensiva: {mp.defensa[equipo]:.2f} "
          "(1.00 = media; en defensa, menos es mejor)")

    _seccion(f"Últimos {args.ultimos} partidos")
    for p in [p for p in jug if p.participa(equipo)][-args.ultimos:]:
        r = "G" if p.ganador == equipo else "E" if p.ganador is None else "P"
        ht = f" (desc. {p.descanso_local}-{p.descanso_visitante})" if p.tiene_descanso else ""
        print(f"  {p.fecha}  {r}  {p.marcador()}{ht}")

    proximos = [p for p in pendientes(partidos) if p.participa(equipo)][:3]
    if proximos:
        _seccion("Próximos partidos")
        for p in proximos:
            pr = mp.predecir(p.local, p.visitante, p.neutral, p.elo_local, p.elo_visitante)
            print(f"  {p.fecha}  {p.local} vs {p.visitante}   1 {100 * pr['p1']:.0f}% · X {100 * pr['px']:.0f}% · 2 {100 * pr['p2']:.0f}%")


def cmd_h2h(partidos, args):
    disponibles = equipos(partidos)
    a = elegir_equipo(args.equipo_a, disponibles)
    b = elegir_equipo(args.equipo_b, disponibles)
    duelos, r = analisis.enfrentamientos_directos(partidos, a, b)
    _titulo(f"{a} vs {b} — {len(duelos)} enfrentamientos")
    for p in duelos:
        ht = f" (desc. {p.descanso_local}-{p.descanso_visitante})" if p.tiene_descanso else ""
        print(f"  {p.fecha}  {p.marcador()}{ht}")
    if duelos:
        n = len(duelos)
        print()
        print(linea_pct(f"Victorias {a}", pct(r[a], n), 30) + f"  ({r[a]})")
        print(linea_pct("Empates", pct(r['empates'], n), 30) + f"  ({r['empates']})")
        print(linea_pct(f"Victorias {b}", pct(r[b], n), 30) + f"  ({r[b]})")
        print(f"  Goles: {a} {r['goles_' + a]} - {r['goles_' + b]} {b}  "
              f"(media {(r['goles_' + a] + r['goles_' + b]) / n:.2f} por partido)")
        ambos = sum(1 for p in duelos if p.goles_local and p.goles_visitante)
        print(linea_pct("Marcan ambos", pct(ambos, n), 30))
        print(linea_pct("Más de 2.5 goles", pct(sum(p.total_goles > 2.5 for p in duelos), n), 30))


def cmd_liga(partidos, args):
    r = analisis.resumen_liga(partidos)
    if not r["partidos"]:
        salir("No hay partidos jugados.")
    _titulo("Resumen de la competición")
    print(f"  Partidos jugados: {r['partidos']}  (pendientes: {r['pendientes']})")
    print(f"  Goles: {r['goles']}  →  {r['goles_por_partido']:.2f} por partido "
          f"(local {r['goles_local_pp']:.2f} · visitante {r['goles_visitante_pp']:.2f})")

    _seccion("Resultados")
    print(linea_pct("Gana local", r["pct_local"]))
    print(linea_pct("Empate", r["pct_empate"]))
    print(linea_pct("Gana visitante", r["pct_visitante"]))
    print(f"  Ventaja de local: {r['ppp_local']:.2f} pts/partido en casa vs {r['ppp_visitante']:.2f} fuera")
    if "pct_favorito_gana" in r:
        print(linea_pct("Gana el favorito", r["pct_favorito_gana"]) + f"  ({r['partidos_con_cuotas']} con cuotas)")

    _seccion("Goles")
    for clave, texto in (("pct_mas_1_5", "Más de 1.5"), ("pct_mas_2_5", "Más de 2.5"), ("pct_mas_3_5", "Más de 3.5"),
                         ("pct_ambos_marcan", "Marcan ambos"), ("pct_0_0", "0-0")):
        print(linea_pct(texto, r[clave]))
    dist = r["distribucion_goles"]
    print("  Goles por partido:")
    for g in range(max(dist) + 1):
        print(f"    {g:>2} {barra(pct(dist[g], max(dist.values())), 30)} {dist[g]}")
    print("  Marcadores más frecuentes: " + ", ".join(f"{a}-{b} ({v})" for (a, b), v in r["marcadores"]))
    m = r["mayor_goleada"]
    print(f"  Mayor goleada: {m.fecha} {m.marcador()}")
    m = r["mas_goles"]
    print(f"  Partido con más goles: {m.fecha} {m.marcador()}")

    if "descanso" in r:
        d = r["descanso"]
        _seccion("Descanso → final")
        print(f"  Goles por partido: 1ª parte {d['goles_1t_pp']:.2f} · 2ª parte {d['goles_2t_pp']:.2f}")
        print("  Matriz descanso/final (1 = local, X = empate, 2 = visitante):")
        print("            " + "".join(f"{'final ' + f:>10}" for f in "1X2"))
        for h in "1X2":
            print(f"    desc. {h} " + "".join(f"{d['matriz'][h + '/' + f]:>10}" for f in "1X2"))
        print(f"  Remontadas (el que perdía al descanso ganó): {d['remontadas']} "
              f"({pct(d['remontadas'], d['partidos']):.1f}%)")

    if r["juego"]:
        _seccion("Estadísticas de juego (media por partido)")
        print(f"  {'':<16}{'Local':>8}{'Visitante':>11}{'Total':>8}")
        for n, (l, v, _) in r["juego"].items():
            print(f"  {NOMBRES_JUEGO[n]:<16}{l:>8.2f}{v:>11.2f}{l + v:>8.2f}")


def cmd_lideres(partidos, args):
    metricas = [args.metrica] if args.metrica else list(analisis.METRICAS)
    cantidad = args.n if args.metrica else 3
    for metrica in metricas:
        descripcion, filas = analisis.lideres(jugados(partidos), metrica, cantidad)
        if not filas:
            continue
        _seccion(f"{descripcion}  [{metrica}]")
        for i, (equipo, valor) in enumerate(filas, 1):
            print(f"  {i:>2}. {equipo:<28} {valor:8.2f}")


def cmd_ranking(partidos, args):
    jug = jugados(partidos)
    actuales = total_equipos(partidos)
    elo = modelos.EloFutbol().procesar(_para_modelo(jug, args))
    mp = modelos.ModeloPoisson().ajustar(_para_modelo(jug, args))
    fuerza = {e: (a, d, dg) for e, a, d, dg in mp.ranking()}
    _titulo("Ranking de fuerza")
    print("  Elo: rating dinámico (más alto = mejor). Ataque/Defensa: 1.00 = media (en defensa, menos es mejor).")
    print("  DG esp.: diferencia de goles esperada por partido contra un rival medio en campo neutral.\n")
    ancho = max(len(e) for e in elo.rating)
    print(f"  {'#':>2}  {'Equipo':<{ancho}}{'Elo':>7}{'Ataque':>8}{'Defensa':>9}{'DG esp.':>9}  Tendencia Elo")
    for i, (e, r) in enumerate([x for x in elo.ranking() if x[0] in actuales], 1):
        a, d, dg = fuerza[e]
        tendencia = chispa([x for _, x in elo.historial[e][-12:]])
        print(f"  {i:>2}  {e:<{ancho}}{r:>7.0f}{a:>8.2f}{d:>9.2f}{dg:>+9.2f}  {tendencia}")


def _imprimir_prediccion(mp, elo, local, visitante, neutral):
    pr = mp.predecir(local, visitante, neutral)
    sede = "campo neutral" if neutral else f"en casa de {local}"
    _titulo(f"{local} vs {visitante} ({sede})")
    print(f"  Goles esperados: {pr['goles_local']:.2f} - {pr['goles_visitante']:.2f}")

    _seccion("1X2")
    print(linea_pct(f"Gana {local}", 100 * pr["p1"], 30) + f"   cuota justa {1 / pr['p1']:.2f}")
    print(linea_pct("Empate", 100 * pr["px"], 30) + f"   cuota justa {1 / pr['px']:.2f}")
    print(linea_pct(f"Gana {visitante}", 100 * pr["p2"], 30) + f"   cuota justa {1 / pr['p2']:.2f}")
    print(f"  Doble oportunidad: 1X {100 * pr['p1x']:.1f}% · X2 {100 * pr['px2']:.1f}% · 12 {100 * pr['p12']:.1f}%")
    print(f"  Elo (expectativa de puntos del local): {100 * elo.esperado(local, visitante, neutral):.1f}%")

    _seccion("Goles")
    for linea, prob in pr["mas"].items():
        print(f"  Más de {linea}: {100 * prob:5.1f}%   Menos de {linea}: {100 * (1 - prob):5.1f}%")
    print(f"  Marcan ambos: sí {100 * pr['ambos_marcan']:.1f}% · no {100 * (1 - pr['ambos_marcan']):.1f}%")
    print(f"  Portería a cero: {local} {100 * pr['porteria_cero_local']:.1f}% · {visitante} {100 * pr['porteria_cero_visitante']:.1f}%")
    print(f"  Hándicap {local}: -1.5 → {100 * pr['handicap'][1.5]:.1f}%   -0.5 → {100 * pr['handicap'][0.5]:.1f}%   "
          f"+0.5 → {100 * pr['handicap'][-0.5]:.1f}%   +1.5 → {100 * pr['handicap'][-1.5]:.1f}%")

    _seccion("Marcadores más probables")
    for i, j, v in pr["marcadores"]:
        print(f"  {i}-{j}  {barra(100 * v / pr['marcadores'][0][2], 20)} {100 * v:.1f}%")
    print("\n  " + f"{'Goles de cada equipo':<24}" + "".join(f"{g:>5}" for g in range(6)))
    print(f"  {local[:22]:<24}" + "".join(f"{100 * v:>4.0f}%" for v in pr["goles_local_dist"]))
    print(f"  {visitante[:22]:<24}" + "".join(f"{100 * v:>4.0f}%" for v in pr["goles_visitante_dist"]))
    return pr


def cmd_predecir(partidos, args):
    jug = jugados(partidos)
    disponibles = equipos(jug)
    local = elegir_equipo(args.local, disponibles)
    visitante = elegir_equipo(args.visitante, disponibles)
    mp = modelos.ModeloPoisson().ajustar(_para_modelo(jug, args))
    elo = modelos.EloFutbol().procesar(_para_modelo(jug, args))
    _imprimir_prediccion(mp, elo, local, visitante, args.neutral)
    if args.cuotas:
        pr = mp.predecir(local, visitante, args.neutral)
        mercado, margen = modelos.probabilidades_mercado(args.cuotas)
        _seccion(f"Comparación con cuotas (margen de la casa {100 * margen:.1f}%)")
        for nombre, cuota, prob, pm in zip(("1", "X", "2"), args.cuotas, (pr["p1"], pr["px"], pr["p2"]), mercado):
            valor = prob * cuota - 1
            print(f"  {nombre}: cuota {cuota:.2f} → mercado {100 * pm:.1f}% · modelo {100 * prob:.1f}% · "
                  f"valor esperado {100 * valor:+.1f}%")
    print("\n  Modelo Poisson con corrección Dixon-Coles (rho = "
          f"{mp.rho:+.2f}), ajustado con {mp.partidos_usados} partidos. Orientativo.")


def cmd_pronosticos(partidos, args):
    jug = jugados(partidos)
    pend = pendientes(partidos)
    futuros = [p for p in pend if p.fecha >= date.today()]
    if futuros and len(futuros) < len(pend):
        print(f"  ({len(pend) - len(futuros)} partidos ya disputados aún no tienen resultado en la fuente; se omiten)")
        pend = futuros
    if not pend:
        salir("No hay partidos pendientes en el archivo. Usa 'predecir LOCAL VISITANTE' para un partido concreto.")
    mp = modelos.ModeloPoisson().ajustar(_para_modelo(jug, args))
    _titulo(f"Pronósticos de los próximos {min(args.n, len(pend))} partidos")
    print(f"  {'Fecha':<11}{'Partido':<46}{'1':>6}{'X':>6}{'2':>6}{'+2.5':>7}{'AM':>6}  Marcador")
    for p in pend[: args.n]:
        pr = mp.predecir(p.local, p.visitante, p.neutral, p.elo_local, p.elo_visitante)
        i, j, _ = pr["marcadores"][0]
        nombre = f"{p.local} vs {p.visitante}"[:45]
        print(f"  {str(p.fecha):<11}{nombre:<46}{100 * pr['p1']:>5.0f}%{100 * pr['px']:>5.0f}%{100 * pr['p2']:>5.0f}%"
              f"{100 * pr['mas'][2.5]:>6.0f}%{100 * pr['ambos_marcan']:>5.0f}%  {i}-{j}")
    print("\n  +2.5 = más de 2.5 goles · AM = marcan ambos")


def cmd_evaluar(partidos, args):
    try:
        previos = getattr(args, "previos", [])
        minimo = args.minimo if args.minimo is not None else (0 if previos else 60)
        r = modelos.evaluar(partidos, minimo=minimo, previos=previos)
    except ValueError as e:
        salir(str(e))
    _titulo("Validación histórica del modelo (sin mirar el futuro)")
    print("  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.")
    print("  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.\n")
    print(f"  {'':<28}{'Partidos':>9}{'Acierto':>9}{'Brier':>8}{'LogLoss':>9}{'RPS':>8}")
    nombres = {"modelo": "Modelo Poisson", "referencia": "Referencia (frecuencias)",
               "modelo_vs_mercado": "Modelo (partidos c/cuotas)", "mercado": "Mercado de apuestas"}
    for clave, nombre in nombres.items():
        m = r[clave]
        if m["n"]:
            print(f"  {nombre:<28}{m['n']:>9}{pct(m['aciertos'], m['n']):>8.1f}%{m['brier']:>8.3f}{m['logloss']:>9.3f}{m['rps']:>8.3f}")
    o = r["over_2_5"]
    print(f"\n  Acierto en más/menos de 2.5 goles: {pct(o['aciertos'], o['n']):.1f}% ({o['n']} partidos)")
    _seccion("Calibración (¿lo que el modelo dice 60% ocurre ~60%?)")
    for tramo, (n, suma, aciertos) in r["calibracion"].items():
        print(f"  Predicho {10 * tramo:>2}-{10 * tramo + 10:<3}%  media {pct(suma, n):5.1f}%  →  real {pct(aciertos, n):5.1f}%  ({n})")


def cmd_goleadores(partidos, args):
    """Máximos goleadores de selecciones en los partidos cargados (torneo y años)."""
    if args.conexion is None:
        salir("Este comando necesita la base de datos: python3 -m analisis_deportivo recopilar")
    claves = {(str(p.fecha), p.local, p.visitante) for p in partidos}
    if not claves:
        salir("No hay partidos de selecciones con esos filtros (usa --liga selecciones o --torneo).")
    goles = [g for g in args.conexion.execute("SELECT * FROM futbol_goleadores_selecciones WHERE autogol = 0")
             if (g["fecha"], g["local"], g["visitante"]) in claves]
    if args.equipo:
        equipo = elegir_equipo(args.equipo, sorted({g["equipo"] for g in goles}))
        goles = [g for g in goles if g["equipo"] == equipo]
    conteo = {}
    for g in goles:
        c = conteo.setdefault((g["goleador"], g["equipo"]), [0, 0, set()])
        c[0] += 1
        c[1] += g["penalti"]
        c[2].add((g["fecha"], g["local"], g["visitante"]))
    filas = sorted(conteo.items(), key=lambda kv: (-kv[1][0], kv[1][1], kv[0][0]))[: args.n]
    _titulo(f"Máximos goleadores ({len(goles):,} goles con autor registrado)")
    print(f"  {'#':>3}  {'Jugador':<30}{'Selección':<22}{'Goles':>6}{'Pen.':>6}{'Partidos c/gol':>16}")
    for i, ((jugador, equipo), (n, pen, part)) in enumerate(filas, 1):
        print(f"  {i:>3}  {jugador[:29]:<30}{equipo[:21]:<22}{n:>6}{pen:>6}{len(part):>16}")
    minutos = [g["minuto"] for g in goles if g["minuto"] is not None]
    if minutos:
        _seccion("Goles por tramo de minutos")
        tramos = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90), (91, 200)]
        cuenta = [sum(a <= m <= b for m in minutos) for a, b in tramos]
        for (a, b), c in zip(tramos, cuenta):
            etiqueta = f"{a}-{b}'" if b < 200 else "90+' y prórroga"
            print(f"  {etiqueta:<16} {barra(pct(c, max(cuenta)), 30)} {pct(c, len(minutos)):5.1f}%")


def _fecha_arg(texto):
    return date.fromisoformat(texto)


def registrar(subparsers, datos_por_defecto):
    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("-d", "--datos", default=None,
                        help="CSV (formato propio o football-data.co.uk) o JSON de openfootball. "
                             "Por defecto, el último archivo descargado o los datos de ejemplo.")
    comunes.add_argument("-l", "--liga", default=None,
                         help="Competición de la base de datos: código (SP1, E0...), alias (espana, inglaterra...) "
                              "o 'selecciones'. Por defecto, espana.")
    comunes.add_argument("--torneo", default=None,
                         help="Torneo de selecciones: mundial, eurocopa, copa-america, eliminatorias... o su nombre en inglés")
    comunes.add_argument("-t", "--temporada", default=None,
                         help="Temporada (2025-26), rango (2020-21:2025-26) o 'todas'. Selecciones: años (2022:2026). "
                              "Por defecto, la más reciente.")
    comunes.add_argument("--desde", type=_fecha_arg, help="Solo partidos desde esta fecha (AAAA-MM-DD)")
    comunes.add_argument("--hasta", type=_fecha_arg, help="Solo partidos hasta esta fecha (AAAA-MM-DD)")
    parser = subparsers.add_parser("futbol", help="Análisis de fútbol (soccer)", aliases=["soccer"])
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("tabla", parents=[comunes], help="Clasificación")
    p.add_argument("--condicion", choices=["local", "visitante", "descanso"])
    p.set_defaults(func=cmd_tabla)

    p = sub.add_parser("equipo", parents=[comunes], help="Informe completo de un equipo")
    p.add_argument("equipo")
    p.add_argument("--ultimos", type=int, default=8)
    p.set_defaults(func=cmd_equipo)

    p = sub.add_parser("h2h", parents=[comunes], help="Enfrentamientos directos")
    p.add_argument("equipo_a")
    p.add_argument("equipo_b")
    p.set_defaults(func=cmd_h2h)

    p = sub.add_parser("liga", parents=[comunes], help="Resumen estadístico de la competición", aliases=["resumen"])
    p.set_defaults(func=cmd_liga)

    p = sub.add_parser("lideres", parents=[comunes], help="Mejores equipos en cada métrica")
    p.add_argument("metrica", nargs="?", choices=list(analisis.METRICAS))
    p.add_argument("-n", type=int, default=10)
    p.set_defaults(func=cmd_lideres)

    p = sub.add_parser("ranking", parents=[comunes], help="Ranking de fuerza (Elo y modelo de goles)")
    p.set_defaults(func=cmd_ranking)

    p = sub.add_parser("predecir", parents=[comunes], help="Probabilidades detalladas de un partido")
    p.add_argument("local")
    p.add_argument("visitante")
    p.add_argument("--neutral", action="store_true", help="Partido en campo neutral")
    p.add_argument("--cuotas", type=float, nargs=3, metavar=("C1", "CX", "C2"),
                   help="Cuotas decimales 1X2 para comparar con el modelo")
    p.set_defaults(func=cmd_predecir)

    p = sub.add_parser("pronosticos", parents=[comunes], help="Pronósticos de los partidos pendientes del archivo")
    p.add_argument("-n", type=int, default=10)
    p.set_defaults(func=cmd_pronosticos)

    p = sub.add_parser("evaluar", parents=[comunes], help="Valida la precisión del modelo con datos históricos")
    p.add_argument("--minimo", type=int, default=None,
                   help="Partidos iniciales usados solo para entrenar (por defecto 60, o 0 si hay temporada anterior en la base)")
    p.set_defaults(func=cmd_evaluar)

    p = sub.add_parser("goleadores", parents=[comunes], help="Máximos goleadores de selecciones (base de datos)")
    p.add_argument("--equipo", help="Solo una selección")
    p.add_argument("-n", type=int, default=25)
    p.set_defaults(func=cmd_goleadores)

    p = sub.add_parser("equipos", parents=[comunes], help="Lista los equipos")
    p.set_defaults(func=cmd_equipos)

    parser.set_defaults(ejecutar=lambda args: _ejecutar(args, datos_por_defecto))


def _ejecutar(args, datos_por_defecto):
    usar_base = (args.datos and base.es_base(args.datos)) or (not args.datos and base.disponible())
    if usar_base:
        try:
            con = base.conectar(args.datos)
            torneo = base.resolver_torneo(args.torneo) if args.torneo else None
            liga = None
            if not torneo:
                liga = "selecciones" if (args.liga or "").lower() == "selecciones" else base.resolver_competicion(args.liga or "espana")
            temporada = args.temporada
            if temporada is None and args.comando == "h2h":
                temporada = "todas"  # el historial completo es lo útil en un cara a cara
            partidos, descripcion = cargar_desde_base(con, liga, temporada, torneo)
            args.previos = []
            actual = descripcion.split(" · ")[1]
            if liga in base.COMPETICIONES and ":" not in actual and actual != "todas":
                anterior = con.execute("SELECT MAX(temporada) FROM futbol_partidos WHERE competicion = ? AND temporada < ?",
                                       (liga, actual)).fetchone()[0]
                if anterior:
                    args.previos = jugados(cargar_desde_base(con, liga, anterior)[0])
        except (OSError, ValueError) as e:
            salir(f"Error al cargar datos: {e}")
        if liga in base.COMPETICIONES:
            nombre, pais, *_ = base.COMPETICIONES[liga]
            descripcion = f"{nombre} ({pais}) · {descripcion.split(' · ')[1]}"
        print(f"(base de datos: {descripcion} · {len(partidos):,} partidos)")
        args.conexion = con
    else:
        ruta = args.datos or datos_por_defecto()
        try:
            partidos = cargar_partidos(ruta)
        except (OSError, ValueError) as e:
            salir(f"Error al cargar datos: {e}")
        if not args.datos:
            print(f"(datos: {ruta})")
        args.conexion = None
    partidos = _filtrar(partidos, args)
    if not jugados(partidos) and args.comando not in ("equipos", "goleadores"):
        salir("No hay partidos jugados con los filtros indicados.")
    args.func(partidos, args)
