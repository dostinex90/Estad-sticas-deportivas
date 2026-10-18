"""Comandos de línea de comandos para la NFL."""

import argparse

from ..comun import barra, chispa, elegir_equipo, linea_pct, normal_cdf, pct, salir
from . import analisis, modelos
from .datos import NOMBRE_TIPO, cargar_juegos, equipos, jugados, temporadas
from .equipos import DIVISIONES, conferencia, division, nombre


def _titulo(texto):
    print(f"\n{texto}\n{'═' * len(texto)}")


def _seccion(texto):
    print(f"\n── {texto} " + "─" * max(0, 60 - len(texto)))


def _pct3(valor):
    return f"{valor:.3f}".lstrip("0") if valor < 1 else "1.000"


def _equipo(texto, juegos):
    disponibles = equipos(juegos)
    t = texto.strip().upper()
    if t in disponibles:
        return t
    por_nombre = {nombre(e): e for e in disponibles}
    return por_nombre[elegir_equipo(texto, list(por_nombre))]


def _de_temporada(juegos, args):
    return [j for j in juegos if j.temporada == args.temporada]


def cmd_equipos(juegos, args):
    for div, eqs in DIVISIONES.items():
        print(f"{div}: " + ", ".join(f"{e} ({nombre(e)})" for e in eqs))


def cmd_clasificacion(juegos, args):
    filas = analisis.clasificacion(juegos, args.temporada)
    if not filas:
        salir(f"No hay partidos de temporada regular en {args.temporada}.")
    cab = f"  {'Equipo':<6}{'Récord':>9}{'PCT':>6}{'PF':>5}{'PC':>5}{'DIF':>6}{'Local':>8}{'Visit.':>8}{'Div.':>7}{'Conf.':>7}{'Racha':>7}  Últ.5"

    def fila(f, prefijo="  "):
        t = f.total
        return (f"{prefijo}{f.equipo:<6}{t.texto():>9}{_pct3(t.porcentaje):>6}{t.pf:>5}{t.pc:>5}{t.diferencia:>+6}"
                f"{f.local.texto():>8}{f.visitante.texto():>8}{f.division.texto():>7}{f.conferencia.texto():>7}"
                f"{f.racha:>7}  {f.ultimos}")

    if args.vista == "playoffs":
        _titulo(f"Clasificación de playoffs {args.temporada}")
        for conf in ("AFC", "NFC"):
            dentro, fuera = analisis.siembra_playoffs(filas, conf)
            _seccion(conf)
            print(cab)
            for i, f in enumerate(dentro, 1):
                marca = "x" if i <= 4 else "*"
                print(fila(f, f"{i}{marca}"))
            print("  " + "·" * 70)
            for f in fuera:
                print(fila(f))
        print("\n  x = campeón de división · * = comodín")
    elif args.vista == "liga":
        _titulo(f"Clasificación general {args.temporada}")
        print(cab)
        for f in sorted(filas.values(), key=lambda f: f.clave_orden):
            print(fila(f))
    else:
        _titulo(f"Clasificación por divisiones {args.temporada}")
        for div, lista in analisis.por_division(filas).items():
            if lista:
                _seccion(div)
                print(cab)
                for f in lista:
                    print(fila(f))
    print("\n  Desempates simplificados: % victorias, % en división, % en conferencia, diferencia de puntos.")


def cmd_equipo(juegos, args):
    equipo = _equipo(args.equipo, juegos)
    temporada = _de_temporada(juegos, args)
    vs = analisis.vistas(temporada, equipo)
    if not vs:
        salir(f"{equipo} no tiene partidos jugados en {args.temporada}.")
    filas = analisis.clasificacion(juegos, args.temporada)
    elo, ratings = modelos.ajustar_modelos(juegos, args.temporada)
    total = analisis.Registro.de([v for v in vs if v.juego.tipo == "REG"])
    _titulo(f"{nombre(equipo)} ({equipo}) — {division(equipo) or '?'} — temporada {args.temporada}")

    _seccion("Resumen")
    if total.jugados:
        div_filas = analisis.por_division(filas).get(division(equipo), [])
        pos_div = next((i for i, f in enumerate(div_filas, 1) if f.equipo == equipo), None)
        print(f"  Temporada regular: {total.texto()} ({_pct3(total.porcentaje)})"
              + (f"  ·  {pos_div}º en su división" if pos_div else ""))
        print(f"  Puntos: {total.pf} a favor ({total.pf_pp:.1f}/p) · {total.pc} en contra ({total.pc_pp:.1f}/p) · "
              f"diferencia {total.diferencia:+d}")
        reales = total.g + 0.5 * total.e
        print(f"  Victorias pitagóricas: {total.victorias_pitagoricas:.1f} (reales {reales:g}) → "
              f"{'más' if reales > total.victorias_pitagoricas else 'menos'} suerte de la esperada "
              f"({reales - total.victorias_pitagoricas:+.1f})")
    print(f"  Racha: {analisis.racha(vs)}   Margen por partido: {chispa([v.margen for v in vs])}")

    _seccion("Ratings y fuerza")
    ranking_elo = [e for e, _ in elo.ranking()]
    ranking_srs = [e for e, *_ in ratings.ranking()]
    print(f"  Elo: {elo.rating[equipo]:.0f} ({ranking_elo.index(equipo) + 1}º)   "
          f"evolución {chispa([r for t, _, r in elo.historial[equipo] if t == args.temporada])}")
    print(f"  SRS (margen frente a un equipo medio): {ratings.srs(equipo):+.1f} ({ranking_srs.index(equipo) + 1}º)")
    print(f"     Ofensa ajustada {ratings.ofensa[equipo]:+.1f} pts · Defensa ajustada {ratings.defensa[equipo]:+.1f} pts "
          "(positivo = mejor que la media)")
    sos, n = modelos.fuerza_calendario(juegos, ratings, equipo, args.temporada)
    if n:
        print(f"  Dificultad del calendario jugado: {sos:+.1f} (SRS medio de {n} rivales)")
    sos_r, n_r = modelos.fuerza_calendario(juegos, ratings, equipo, args.temporada, pendientes=True)
    if n_r:
        print(f"  Dificultad del calendario restante: {sos_r:+.1f} ({n_r} partidos)")

    _seccion("Récords por situación")
    print(f"  {'Situación':<34}{'Récord':>9}{'PF/p':>7}{'PC/p':>7}{'ATS':>9}{'O/U':>9}")
    for nom, r in analisis.splits(temporada, equipo):
        print(f"  {nom:<34}{r.texto():>9}{r.pf_pp:>7.1f}{r.pc_pp:>7.1f}{r.texto_ats():>9}{r.texto_ou():>9}")
    print("  ATS = contra el spread (cubre-no cubre-push) · O/U = over-under del total")

    qbs = analisis.registro_por_qb(temporada, equipo)
    if qbs:
        _seccion("Récord por quarterback titular")
        for qb, r in qbs:
            print(f"  {qb:<28}{r.texto():>8}  {r.pf_pp:5.1f} pts/p")

    _seccion("Partido a partido")
    print(f"  {'Sem.':<6}{'Fecha':<12}{'Rival':<9}{'Res.':<5}{'Marcador':<10}{'Línea':>7}{'ATS':>5}{'Total':>7}{'O/U':>5}")
    for v in vs:
        j = v.juego
        sem = j.tipo if j.es_playoff else str(j.semana)
        rival = ("vs " if v.es_local else "@ ") + v.rival
        linea = "" if v.linea is None else f"{-v.linea or 0.0:+.1f}"
        print(f"  {sem:<6}{str(j.fecha):<12}{rival:<9}{v.resultado.replace('G', 'W').replace('P', 'L').replace('E', 'T'):<5}"
              f"{v.pf:>2}-{v.pc:<7}{linea:>7}{v.ats or '':>5}{'' if j.total_linea is None else j.total_linea:>7}{v.over_under or '':>5}")
    print("  Línea desde el punto de vista del equipo (negativa = favorito), como en las casas de apuestas.")

    proximos = [j for j in temporada if not j.jugado and j.participa(equipo)][:4]
    if proximos:
        _seccion("Próximos partidos")
        for j in proximos:
            pr = modelos.predecir(elo, ratings, j.local, j.visitante, j.neutral)
            p_eq = pr["prob_local"] if j.local == equipo else 1 - pr["prob_local"]
            m_eq = pr["margen"] if j.local == equipo else -pr["margen"]
            print(f"  Sem. {j.semana:<3} {j.fecha}  {j.marcador():<12} prob. victoria {100 * p_eq:4.1f}%  margen {m_eq:+.1f}")


def cmd_h2h(juegos, args):
    a = _equipo(args.equipo_a, juegos)
    b = _equipo(args.equipo_b, juegos)
    duelos = [j for j in juegos if j.jugado and j.participa(a) and j.participa(b)]
    _titulo(f"{a} vs {b} — {len(duelos)} partidos en los datos")
    for j in duelos[-args.ultimos:]:
        tipo = "" if j.tipo == "REG" else f"  [{NOMBRE_TIPO.get(j.tipo, j.tipo)}]"
        print(f"  {j.temporada} sem.{j.semana:<3} {j.marcador()}{tipo}")
    if duelos:
        ra = analisis.Registro.de(analisis.vistas(duelos, a))
        print(f"\n  Récord de {a}: {ra.texto()}   Puntos {ra.pf}-{ra.pc}  (media {ra.pf_pp:.1f}-{ra.pc_pp:.1f})")
        print(f"  {a} contra el spread: {ra.texto_ats()}   Over-under: {ra.texto_ou()}")


def cmd_liga(juegos, args):
    temporada = _de_temporada(juegos, args)
    if args.solo_regular:
        temporada = [j for j in temporada if j.tipo == "REG"]
    r = analisis.resumen_liga(temporada)
    if not r["partidos"]:
        salir("No hay partidos jugados.")
    _titulo(f"Resumen de la NFL {args.temporada}")
    print(f"  Partidos: {r['partidos']} (pendientes {r['pendientes']})")
    print(f"  Puntos por partido: {r['puntos_pp']:.1f} (local {r['puntos_local_pp']:.1f} · visitante {r['puntos_visitante_pp']:.1f})")

    _seccion("Resultados")
    print(linea_pct("Gana el local", r["pct_gana_local"], 30) + f"   margen medio local {r['margen_local']:+.1f}")
    print(linea_pct(f"Decididos por ≤{analisis.PARTIDO_AJUSTADO} puntos", r["pct_ajustados"], 30))
    print(linea_pct(f"Decididos por {analisis.PALIZA}+ puntos", r["pct_palizas"], 30))
    print(linea_pct("Con prórroga", r["pct_prorroga"], 30))
    print(linea_pct("Empates", r["pct_empates"], 30))
    print("  Márgenes finales más frecuentes (números clave): "
          + ", ".join(f"{m} ({v})" for m, v in r["margenes_frecuentes"]))
    j = r["mas_puntos"]
    print(f"  Más puntos: {j.marcador()} (sem. {j.semana})")
    j = r["menos_puntos"]
    print(f"  Menos puntos: {j.marcador()} (sem. {j.semana})")
    j = r["mayor_paliza"]
    print(f"  Mayor paliza: {j.marcador()} (sem. {j.semana})")

    if "pct_favorito_gana" in r:
        _seccion("Mercado de apuestas")
        print(linea_pct("Gana el favorito", r["pct_favorito_gana"], 30))
        print(linea_pct("El favorito cubre el spread", r["pct_favorito_cubre"], 30))
        print(linea_pct("El local cubre el spread", r["pct_local_cubre"], 30))
        if "pct_sorpresa_7" in r:
            print(linea_pct("Gana el underdog de 7+ pts", r["pct_sorpresa_7"], 30))
        print(f"  Ventaja de campo que asigna el mercado: {r['linea_media_local']:+.1f} pts de media")
        print(f"  Error medio del spread: {r['error_linea']:.1f} pts")
    if "pct_over" in r:
        print(linea_pct("Se supera el total (over)", r["pct_over"], 30))
        print(f"  Total medio del mercado: {r['total_linea_media']:.1f} · error medio {r['error_total']:.1f} pts")

    _seccion("Puntos según condiciones")
    for k, (m, n) in r["puntos_por_techo"].items():
        print(f"  {k:<26}{m:6.1f} pts/partido ({n})")
    for clave, texto in (("puntos_frio", "Frío (≤40 °F)"), ("puntos_viento", "Viento (≥15 mph)"),
                         ("puntos_divisionales", "Partidos divisionales")):
        if clave in r:
            m, n = r[clave]
            print(f"  {texto:<26}{m:6.1f} pts/partido ({n})")


def cmd_lideres(juegos, args):
    temporada = [j for j in _de_temporada(juegos, args) if j.tipo == "REG"]
    metricas = [args.metrica] if args.metrica else list(analisis.METRICAS)
    cantidad = args.n if args.metrica else 5
    for metrica in metricas:
        descripcion, filas = analisis.lideres(temporada, metrica, cantidad)
        _seccion(f"{descripcion}  [{metrica}]")
        for i, (e, valor, r) in enumerate(filas, 1):
            print(f"  {i:>2}. {e:<4} {nombre(e):<24} {valor:8.2f}   ({r.texto()})")


def cmd_ranking(juegos, args):
    elo, ratings = modelos.ajustar_modelos(juegos, args.temporada)
    filas = analisis.clasificacion(juegos, args.temporada)
    srs = {e: (o, d, s) for e, o, d, s in ratings.ranking()}
    # Power ranking: media de las posiciones en Elo y SRS
    pos_elo = {e: i for i, (e, _) in enumerate(elo.ranking())}
    pos_srs = {e: i for i, e in enumerate(srs)}
    eqs = [e for e in srs if e in filas or not filas]
    orden = sorted(eqs, key=lambda e: (pos_elo.get(e, 99) + pos_srs[e], -srs[e][2]))
    _titulo(f"Power ranking {args.temporada}")
    print("  Elo: rating dinámico. SRS: margen esperado frente a un equipo medio en campo neutral.")
    print("  Of./Def.: puntos por encima de la media que anota / evita. Pit.: victorias pitagóricas.\n")
    print(f"  {'#':>2}  {'Equipo':<26}{'Récord':>8}{'Elo':>7}{'SRS':>7}{'Of.':>7}{'Def.':>7}{'Pit.':>6}  Elo (temporada)")
    for i, e in enumerate(orden, 1):
        o, d, s = srs[e]
        f = filas.get(e)
        rec = f.total.texto() if f else ""
        pit = f"{f.total.victorias_pitagoricas:.1f}" if f else ""
        tendencia = chispa([r for t, _, r in elo.historial[e] if t == args.temporada])
        print(f"  {i:>2}  {nombre(e)[:25]:<26}{rec:>8}{elo.rating.get(e, 1500):>7.0f}{s:>+7.1f}{o:>+7.1f}{d:>+7.1f}{pit:>6}  {tendencia}")
    print(f"\n  Ventaja de campo estimada: {ratings.ventaja_campo:+.1f} pts · media de la liga {ratings.media:.1f} pts por equipo")


def _mostrar_prediccion(elo, ratings, local, visitante, neutral, linea=None, total_linea=None):
    pr = modelos.predecir(elo, ratings, local, visitante, neutral)
    sede = "campo neutral" if neutral else f"en {local}"
    _titulo(f"{nombre(visitante)} @ {nombre(local)} ({sede})")
    favorito = local if pr["margen"] > 0 else visitante
    print(f"  Marcador esperado: {local} {pr['puntos_local']:.1f} - {pr['puntos_visitante']:.1f} {visitante}")
    print(f"  Spread del modelo: {favorito} -{abs(pr['margen']):.1f}   (Elo {pr['margen_elo']:+.1f} · ratings {pr['margen_ratings']:+.1f}, "
          "desde el local)")
    print(f"  Total esperado: {pr['total']:.1f} puntos")
    _seccion("Probabilidad de victoria")
    print(linea_pct(local, 100 * pr["prob_local"], 8) + f"   moneyline justa {modelos.moneyline_justa(pr['prob_local'])}")
    print(linea_pct(visitante, 100 * (1 - pr["prob_local"]), 8) + f"   moneyline justa {modelos.moneyline_justa(1 - pr['prob_local'])}")
    print(f"  (Elo solo: {100 * pr['prob_elo']:.1f}% para {local})")
    if linea is not None:
        _seccion("Contra la línea del mercado")
        fav_m = local if linea > 0 else visitante
        p = modelos.prob_cubrir(pr["margen"], linea)
        print(f"  Mercado: {fav_m} -{abs(linea):.1f} · modelo: {favorito} -{abs(pr['margen']):.1f} · "
              f"diferencia {pr['margen'] - linea:+.1f} pts para el local")
        print(f"  Prob. de que {local} cubra: {100 * p:.1f}% · {visitante}: {100 * (1 - p):.1f}%")
    if total_linea is not None:
        p_over = 1 - normal_cdf(total_linea, pr["total"], modelos.DESVIACION_MARGEN)
        print(f"  Total del mercado {total_linea}: over {100 * p_over:.1f}% · under {100 * (1 - p_over):.1f}%")
    return pr


def cmd_predecir(juegos, args):
    local = _equipo(args.local, juegos)
    visitante = _equipo(args.visitante, juegos)
    elo, ratings = modelos.ajustar_modelos(juegos, args.temporada)
    _mostrar_prediccion(elo, ratings, local, visitante, args.neutral, args.linea, args.total)
    print("\n  Orientativo: combina Elo y ratings ajustados por rival; no incluye lesiones ni clima.")


def cmd_pronosticos(juegos, args):
    pend = [j for j in juegos if j.temporada == args.temporada and not j.jugado]
    if not pend:
        salir(f"No hay partidos pendientes en {args.temporada}.")
    semana = args.semana or min(j.semana for j in pend if j.tipo == pend[0].tipo)
    partidos = [j for j in pend if j.semana == semana]
    elo, ratings = modelos.ajustar_modelos(juegos, args.temporada)
    _titulo(f"Pronósticos semana {semana} — {args.temporada}")
    print(f"  {'Partido':<12}{'Fecha':<12}{'Prob. local':>12}{'Modelo':>10}{'Mercado':>10}{'Dif.':>7}{'Total':>7}{'Mercado':>9}")
    for j in partidos:
        pr = modelos.predecir(elo, ratings, j.local, j.visitante, j.neutral)
        mercado = "" if j.linea is None else f"{-j.linea or 0.0:+.1f}"
        dif = "" if j.linea is None else f"{pr['margen'] - j.linea:+.1f}"
        tl = "" if j.total_linea is None else f"{j.total_linea:.1f}"
        print(f"  {j.marcador():<12}{str(j.fecha):<12}{100 * pr['prob_local']:>11.1f}%{-pr['margen']:>+10.1f}{mercado:>10}"
              f"{dif:>7}{pr['total']:>7.1f}{tl:>9}")
    print("\n  Spreads desde el punto de vista del local (negativo = local favorito).")
    print("  Dif. = ventaja del modelo para el local respecto al mercado (positivo = el modelo ve mejor al local).")


def cmd_simular(juegos, args):
    resultados, pendientes = modelos.simular_temporada(juegos, args.temporada, args.n, args.semilla)
    if not pendientes:
        print("  La temporada regular está completa; se muestra la clasificación final.")
    _titulo(f"Simulación de la temporada {args.temporada} ({args.n} simulaciones, {pendientes} partidos pendientes)")
    for conf in ("AFC", "NFC"):
        _seccion(conf)
        print(f"  {'Equipo':<26}{'Vict. esp.':>11}  {'Playoffs':<30}{'División':>10}{'1º conf.':>10}")
        eqs = sorted((e for e in resultados if conferencia(e) == conf),
                     key=lambda e: (-resultados[e].get("playoffs", 0), -resultados[e].get("victorias", 0)))
        for e in eqs:
            r = resultados[e]
            p = 100 * r.get("playoffs", 0)
            print(f"  {nombre(e)[:25]:<26}{r.get('victorias', 0):>11.1f}  {barra(p, 20)} {p:5.1f}%"
                  f"{100 * r.get('division', 0):>9.1f}%{100 * r.get('primero', 0):>9.1f}%")
    print("\n  Desempates simplificados (victorias, récord divisional, sorteo).")


def cmd_evaluar(juegos, args):
    try:
        m = modelos.evaluar(juegos, args.temporada)
    except ValueError as e:
        salir(str(e))
    n = m.get("n", 0)
    if not n:
        salir("No hay partidos que evaluar.")
    _titulo(f"Validación del modelo en {args.temporada} (semana a semana, sin datos futuros)")
    print(f"  Partidos evaluados: {int(n)}")
    print(linea_pct("Acierto ganador (combinado)", pct(m["aciertos"], n), 34))
    print(linea_pct("Acierto ganador (solo Elo)", pct(m["aciertos_elo"], n), 34))
    print(linea_pct("Acierto ganador (solo ratings)", pct(m["aciertos_ratings"], n), 34))
    if m.get("n_fav"):
        print(linea_pct("Acierto del favorito del mercado", pct(m["aciertos_mercado"], m["n_fav"]), 34))
    print(f"  Brier score: {m['brier'] / n:.3f} (0.25 = lanzar una moneda; menor es mejor)")
    print(f"  Error medio del margen: {m['error_margen'] / n:.2f} pts · del total: {m['error_total'] / n:.2f} pts")
    if m.get("n_linea"):
        k = m["n_linea"]
        _seccion("Frente a las casas de apuestas")
        print(f"  Error medio del margen: modelo {m['error_margen_m'] / k:.2f} pts vs mercado {m['error_linea'] / k:.2f} pts")
        if m.get("ats_n"):
            print(linea_pct("Acierto contra el spread", pct(m["ats_aciertos"], m["ats_n"]), 34) + f"  ({int(m['ats_n'])})")
        if m.get("ats3_n"):
            print(linea_pct("ATS con diferencia ≥3 pts", pct(m["ats3_aciertos"], m["ats3_n"]), 34) + f"  ({int(m['ats3_n'])})")
        if m.get("n_total"):
            t = m["n_total"]
            print(f"  Error medio del total: modelo {m['error_total_m'] / t:.2f} vs mercado {m['error_total_linea'] / t:.2f}")
        if m.get("ou_n"):
            print(linea_pct("Acierto over/under", pct(m["ou_aciertos"], m["ou_n"]), 34) + f"  ({int(m['ou_n'])})")
        print("  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.")


def registrar(subparsers, datos_por_defecto):
    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("-d", "--datos", default=None,
                        help="CSV de nflverse (games.csv) o formato propio. Por defecto, el último descargado o el ejemplo.")
    comunes.add_argument("-t", "--temporada", type=int, help="Temporada a analizar (por defecto, la más reciente)")
    parser = subparsers.add_parser("nfl", help="Análisis de la NFL")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("clasificacion", parents=[comunes], help="Clasificación", aliases=["tabla"])
    p.add_argument("--vista", choices=["division", "playoffs", "liga"], default="division")
    p.set_defaults(func=cmd_clasificacion)

    p = sub.add_parser("equipo", parents=[comunes], help="Informe completo de un equipo")
    p.add_argument("equipo", help="Abreviatura (KC) o nombre (Chiefs)")
    p.set_defaults(func=cmd_equipo)

    p = sub.add_parser("h2h", parents=[comunes], help="Historial entre dos equipos (todas las temporadas del archivo)")
    p.add_argument("equipo_a")
    p.add_argument("equipo_b")
    p.add_argument("--ultimos", type=int, default=20)
    p.set_defaults(func=cmd_h2h)

    p = sub.add_parser("liga", parents=[comunes], help="Resumen estadístico de la temporada", aliases=["resumen"])
    p.add_argument("--solo-regular", action="store_true", help="Excluir playoffs")
    p.set_defaults(func=cmd_liga)

    p = sub.add_parser("lideres", parents=[comunes], help="Mejores equipos por métrica")
    p.add_argument("metrica", nargs="?", choices=list(analisis.METRICAS))
    p.add_argument("-n", type=int, default=10)
    p.set_defaults(func=cmd_lideres)

    p = sub.add_parser("ranking", parents=[comunes], help="Power ranking (Elo, SRS, ofensa, defensa)")
    p.set_defaults(func=cmd_ranking)

    p = sub.add_parser("predecir", parents=[comunes], help="Predicción de un partido")
    p.add_argument("local")
    p.add_argument("visitante")
    p.add_argument("--neutral", action="store_true")
    p.add_argument("--linea", type=float, help="Ventaja del local según el mercado (KC -3 en casa → 3)")
    p.add_argument("--total", type=float, help="Total de puntos del mercado")
    p.set_defaults(func=cmd_predecir)

    p = sub.add_parser("pronosticos", parents=[comunes], help="Pronósticos de la próxima semana (o --semana N)")
    p.add_argument("--semana", type=int)
    p.set_defaults(func=cmd_pronosticos)

    p = sub.add_parser("simular", parents=[comunes], help="Probabilidades de playoffs por simulación Monte Carlo")
    p.add_argument("-n", type=int, default=5000, help="Número de simulaciones")
    p.add_argument("--semilla", type=int, help="Semilla aleatoria para resultados reproducibles")
    p.set_defaults(func=cmd_simular)

    p = sub.add_parser("evaluar", parents=[comunes], help="Valida la precisión del modelo en una temporada")
    p.set_defaults(func=cmd_evaluar)

    p = sub.add_parser("equipos", parents=[comunes], help="Lista equipos por división")
    p.set_defaults(func=cmd_equipos)

    parser.set_defaults(ejecutar=lambda args: _ejecutar(args, datos_por_defecto))


def _ejecutar(args, datos_por_defecto):
    ruta = args.datos or datos_por_defecto()
    try:
        juegos = cargar_juegos(ruta)
    except (OSError, ValueError) as e:
        salir(f"Error al cargar datos: {e}")
    if not args.datos:
        print(f"(datos: {ruta})")
    if not juegos:
        salir("El archivo no contiene partidos.")
    disponibles = temporadas(juegos)
    if args.temporada is None:
        args.temporada = max(disponibles)
    elif args.temporada not in disponibles:
        salir(f"Temporada {args.temporada} no está en los datos ({disponibles[0]}-{disponibles[-1]}).")
    if not jugados(juegos):
        salir("No hay partidos jugados.")
    args.func(juegos, args)
