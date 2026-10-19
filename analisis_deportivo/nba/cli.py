"""Comandos de línea de comandos para la NBA (requieren la base de datos)."""

import argparse
import sqlite3
from datetime import date

from ..comun import barra, chispa, elegir_equipo, linea_pct, normal_cdf, pct, salir
from .. import base
from . import analisis, estadisticas, jugadores, modelos
from .datos import NOMBRE_TIPO, cargar_desde_base, descansos, equipos, jugados, leer_temporada, temporadas, texto_temporada
from .equipos import CONFERENCIAS, DIVISIONES, conferencia, division, nombre


def _titulo(texto):
    print(f"\n{texto}\n{'═' * len(texto)}")


def _seccion(texto):
    print(f"\n── {texto} " + "─" * max(0, 60 - len(texto)))


def _pct3(valor):
    return f"{valor:.3f}".lstrip("0") if valor < 1 else "1.000"


def equipo_de(texto, partidos):
    """Resuelve una abreviatura (LAL), un nombre completo o parcial (Lakers)."""
    disponibles = equipos(partidos)
    t = texto.strip().upper()
    if t in disponibles:
        return t
    por_nombre = {nombre(e): e for e in disponibles}
    return por_nombre[elegir_equipo(texto, list(por_nombre))]


def _de_temporada(partidos, args):
    return [p for p in partidos if p.temporada == args.temporada]


def _t(args):
    return texto_temporada(args.temporada)


def _jugadores(args):
    """ContextoJugadores con todos los partidos jugados, solo para la temporada más reciente (en las
    pasadas no tiene sentido usar las bajas de hoy). None si la base no tiene jugadores."""
    if not hasattr(args, "_ctx_jugadores"):
        args._ctx_jugadores = (jugadores.contexto(jugadores.por_partido(args.conexion))
                               if args.temporada == args.ultima_temporada else None)
    return args._ctx_jugadores


def _bajas(ctx, equipo, hoy):
    """Texto con los jugadores importantes que no jugaron el último partido del equipo."""
    lista = [f"{n} ({v:+.1f})" for n, _, v in ctx.ausentes(equipo, hoy) if v >= 0.3] if ctx else []
    return ", ".join(lista[:4])


def cmd_equipos(partidos, args):
    for div, eqs in DIVISIONES.items():
        print(f"{div}: " + ", ".join(f"{e} ({nombre(e)})" for e in eqs))


def cmd_clasificacion(partidos, args):
    filas = analisis.clasificacion(partidos, args.temporada)
    if not filas:
        salir(f"No hay partidos de temporada regular en {_t(args)}.")
    cab = (f"   {'Equipo':<6}{'Récord':>8}{'PCT':>6}{'PF/p':>7}{'PC/p':>7}{'DIF/p':>7}{'Local':>8}{'Visit.':>8}"
           f"{'Conf.':>8}{'Racha':>7}  Últ.10")

    def fila(f, prefijo="   "):
        t = f.total
        return (f"{prefijo}{f.equipo:<6}{t.texto():>8}{_pct3(t.porcentaje):>6}{t.pf_pp:>7.1f}{t.pc_pp:>7.1f}{t.dif_pp:>+7.1f}"
                f"{f.local.texto():>8}{f.visitante.texto():>8}{f.conferencia.texto():>8}{f.racha:>7}  {f.ultimos}")

    if args.vista == "division":
        _titulo(f"Clasificación por divisiones {_t(args)}")
        for div, lista in analisis.por_division(filas).items():
            if lista:
                _seccion(div)
                print(cab)
                for f in lista:
                    print(fila(f))
    elif args.vista == "liga":
        _titulo(f"Clasificación general {_t(args)}")
        print(cab)
        for f in sorted(filas.values(), key=lambda f: f.clave_orden):
            print(fila(f))
    else:
        _titulo(f"Clasificación por conferencias {_t(args)}")
        playin = args.temporada >= 2021
        for conf, lista in analisis.por_conferencia(filas, args.temporada).items():
            _seccion(conf)
            print(cab)
            for i, f in enumerate(lista, 1):
                print(fila(f, f"{i:>2} "))
                if i == (6 if playin else 8) or (playin and i == 10):
                    print("  " + "·" * 70)
        if playin:
            print("\n  1-6: playoffs directos · 7-10: play-in · línea de puntos = corte")
    print("  Desempates simplificados: % victorias, victorias, diferencia de puntos por partido.")


def cmd_equipo(partidos, args):
    equipo = equipo_de(args.equipo, partidos)
    temporada = _de_temporada(partidos, args)
    filas = analisis.clasificacion(partidos, args.temporada)
    elo, ratings = modelos.ajustar_modelos(partidos, args.temporada)
    vs = analisis.vistas(temporada, equipo)
    total = analisis.Registro.de([v for v in vs if v.partido.tipo == "REG"])
    _titulo(f"{nombre(equipo)} ({equipo}) — {division(equipo) or '?'} — temporada {_t(args)}")

    _seccion("Resumen")
    if total.jugados:
        conf = analisis.por_conferencia(filas, args.temporada)
        pos = next((i for lista in conf.values() for i, f in enumerate(lista, 1) if f.equipo == equipo), None)
        print(f"  Temporada regular: {total.texto()} ({_pct3(total.porcentaje)})" + (f"  ·  {pos}º en su conferencia" if pos else ""))
        print(f"  Puntos: {total.pf_pp:.1f} a favor y {total.pc_pp:.1f} en contra por partido · diferencia {total.dif_pp:+.1f}")
        print(f"  Victorias pitagóricas: {total.victorias_pitagoricas:.1f} (reales {total.g}) → "
              f"{'más' if total.g > total.victorias_pitagoricas else 'menos'} suerte de la esperada "
              f"({total.g - total.victorias_pitagoricas:+.1f})")
        print(f"  Racha: {analisis.racha(vs)}   Margen por partido: {chispa([v.margen for v in vs][-30:])}")
    else:
        print("  Aún no ha jugado partidos esta temporada; los ratings vienen de las temporadas anteriores.")

    _seccion("Ratings y fuerza")
    ranking_elo = [e for e, _ in elo.ranking()]
    ranking_neto = [e for e, *_ in ratings.ranking()]
    print(f"  Elo: {elo.rating.get(equipo, 1500):.0f} ({ranking_elo.index(equipo) + 1}º)   "
          f"evolución {chispa([r for t, _, r in elo.historial[equipo] if t == args.temporada][-40:])}")
    print(f"  Rating neto (margen frente a un equipo medio): {ratings.neto(equipo):+.1f} ({ranking_neto.index(equipo) + 1}º)")
    print(f"     Ataque {ratings.ofensa[equipo]:+.1f} pts · Defensa {ratings.defensa[equipo]:+.1f} pts (positivo = mejor que la media)")

    if args.conexion is not None:
        resumenes = estadisticas.por_equipo(estadisticas.cargar(args.conexion, args.temporada))
        r = resumenes.get(equipo)
        if r:
            _seccion("Estadísticas de juego (temporada regular)")
            print(f"  {'':<30}{'Ataque':>9}{'Puesto':>8}{'Rival':>9}{'Puesto':>8}")
            for m, (etiqueta, mayor) in estadisticas.METRICAS.items():
                fav = sorted(resumenes.values(), key=lambda x: -x.favor_de(m) if mayor else x.favor_de(m))
                con = sorted(resumenes.values(), key=lambda x: x.contra_de(m) if mayor else -x.contra_de(m))
                pf = [x.equipo for x in fav].index(equipo) + 1
                pc = [x.equipo for x in con].index(equipo) + 1
                fmt = ".2f" if m == "tasa_libres" else ".1f"
                print(f"  {etiqueta:<30}{format(r.favor_de(m), fmt):>9}{pf:>7}º{format(r.contra_de(m), fmt):>9}{pc:>7}º")
            print(f"  Rating neto por 100 posesiones: {r.neto:+.1f}. Rival = lo que permite (puesto 1 = el que menos concede).")

    if vs:
        _seccion("Récords por situación")
        print(f"  {'Situación':<36}{'Récord':>9}{'PF/p':>8}{'PC/p':>8}")
        for nom, rr in analisis.splits(temporada, equipo, filas):
            print(f"  {nom:<36}{rr.texto():>9}{rr.pf_pp:>8.1f}{rr.pc_pp:>8.1f}")

        _seccion(f"Últimos {min(len(vs), args.ultimos)} partidos")
        for v in vs[-args.ultimos:]:
            p = v.partido
            fase = "" if p.tipo == "REG" else f"  [{p.ronda or NOMBRE_TIPO[p.tipo]}]"
            pro = " (pró.)" if p.prorrogas else ""
            print(f"  {p.fecha}  {'vs' if v.es_local else '@ '} {v.rival:<5} {v.resultado.replace('G', 'V').replace('P', 'D')} "
                  f"{v.pf}-{v.pc}{pro}{fase}")

    ctx = _jugadores(args)
    hoy = date.today()
    if ctx and ctx.historial.get(equipo):
        _seccion("Jugadores de rotación (los que suelen jugar 20+ minutos)")
        recientes = {j for g in list(ctx.historial[equipo])[-10:] for j in g}
        ultimo = set(ctx.historial[equipo][-1])
        filas_j = sorted(((ctx.nombres[j], ctx.minutos_habituales(j), 36 * ctx.valor(j, hoy), j in ultimo) for j in recientes
                          if ctx.minutos_habituales(j) >= ctx.rotacion), key=lambda f: -f[1] * f[2])
        print(f"  {'Jugador':<26}{'Min.':>6}{'Valoración/36':>15}  Último partido")
        for n, m, v, jugo in filas_j:
            print(f"  {n[:25]:<26}{m:>6.1f}{v:>15.1f}  {'jugó' if jugo else 'NO JUGÓ'}")
        print(f"  Ajuste por plantilla para su próximo partido: {ctx.ajuste(equipo, hoy):+.1f} puntos frente a lo habitual"
              + ("" if ctx.vigente(equipo, hoy) else " (su último partido fue hace más de 60 días: no se suponen bajas)"))
        print("  Valoración/36: Game Score de Hollinger cada 36 minutos (unos 10 es un titular normal).")

    proximos = [p for p in temporada if not p.jugado and p.participa(equipo)][:5]
    if proximos:
        _seccion("Próximos partidos")
        dias = descansos(temporada)
        for p in proximos:
            pr = modelos.predecir_partido(elo, ratings, p, dias, ctx)
            p_eq = pr["prob_local"] if p.local == equipo else 1 - pr["prob_local"]
            m_eq = pr["margen"] if p.local == equipo else -pr["margen"]
            print(f"  {p.fecha}  {p.marcador():<12} prob. victoria {100 * p_eq:4.1f}%  margen {m_eq:+.1f}")


def cmd_h2h(partidos, args):
    a = equipo_de(args.equipo_a, partidos)
    b = equipo_de(args.equipo_b, partidos)
    duelos = [p for p in partidos if p.jugado and p.participa(a) and p.participa(b)]
    _titulo(f"{a} vs {b} — {len(duelos)} partidos desde 2001-02")
    for p in duelos[-args.ultimos:]:
        fase = "" if p.tipo == "REG" else f"  [{p.ronda or NOMBRE_TIPO[p.tipo]}]"
        print(f"  {texto_temporada(p.temporada)} {p.fecha}  {p.marcador()}{fase}")
    if duelos:
        ra = analisis.Registro.de(analisis.vistas(duelos, a))
        print(f"\n  Récord de {a}: {ra.texto()}   Puntos por partido {ra.pf_pp:.1f}-{ra.pc_pp:.1f}")
        po = analisis.Registro.de(analisis.vistas([p for p in duelos if p.es_playoff], a))
        if po.jugados:
            print(f"  En playoffs: {po.texto()}")


def cmd_liga(partidos, args):
    temporada = _de_temporada(partidos, args)
    if args.solo_regular:
        temporada = [p for p in temporada if p.tipo == "REG"]
    r = analisis.resumen_liga(temporada)
    if not r["partidos"]:
        salir(f"No hay partidos jugados en {_t(args)}.")
    _titulo(f"Resumen de la NBA {_t(args)}")
    print(f"  Partidos: {r['partidos']} (pendientes {r['pendientes']})")
    print(f"  Puntos por partido: {r['puntos_pp']:.1f} (local {r['puntos_local_pp']:.1f} · visitante {r['puntos_visitante_pp']:.1f})")
    _seccion("Resultados")
    print(linea_pct("Gana el local", r["pct_gana_local"], 32) + f"   margen medio local {r['margen_local']:+.1f}")
    print(linea_pct(f"Decididos por ≤{analisis.PARTIDO_AJUSTADO} puntos", r["pct_ajustados"], 32))
    print(linea_pct(f"Decididos por {analisis.PALIZA}+ puntos", r["pct_palizas"], 32))
    print(linea_pct("Con prórroga", r["pct_prorroga"], 32))
    if "pct_gana_descansado" in r:
        print(linea_pct("Gana el que no jugó el día antes", r["pct_gana_descansado"], 32)
              + f"  ({r['partidos_b2b']} partidos con un solo equipo en días seguidos)")
    print("  Márgenes finales más frecuentes: " + ", ".join(f"{m} ({v})" for m, v in r["margenes_frecuentes"]))
    print(f"  Más puntos: {r['mas_puntos'].marcador()} ({r['mas_puntos'].fecha})")
    print(f"  Menos puntos: {r['menos_puntos'].marcador()} ({r['menos_puntos'].fecha})")
    print(f"  Mayor paliza: {r['mayor_paliza'].marcador()} ({r['mayor_paliza'].fecha})")
    if args.conexion is not None:
        factores = estadisticas.factores_victoria(estadisticas.cargar(args.conexion, args.temporada, args.solo_regular))
        if factores:
            _seccion("Qué decide los partidos (% que gana quien domina cada estadística)")
            for m, (p, n) in sorted(factores.items(), key=lambda kv: -kv[1][0]):
                print(linea_pct(estadisticas.METRICAS[m][0], p, 32) + f"  ({n})")


def cmd_ranking(partidos, args):
    elo, ratings = modelos.ajustar_modelos(partidos, args.temporada)
    filas = analisis.clasificacion(partidos, args.temporada)
    netos = {e: (o, d, s) for e, o, d, s in ratings.ranking()}
    pos_elo = {e: i for i, (e, _) in enumerate(elo.ranking())}
    pos_neto = {e: i for i, e in enumerate(netos)}
    eqs = [e for e in netos if e in filas or not filas]
    orden = sorted(eqs, key=lambda e: (pos_elo.get(e, 99) + pos_neto[e], -netos[e][2]))
    _titulo(f"Power ranking {_t(args)}")
    print("  Elo: rating dinámico. Neto: margen esperado frente a un equipo medio en campo neutral.")
    print("  At./Def.: puntos por encima de la media que anota / evita. Pit.: victorias pitagóricas.\n")
    print(f"  {'#':>2}  {'Equipo':<26}{'Récord':>8}{'Elo':>7}{'Neto':>7}{'At.':>7}{'Def.':>7}{'Pit.':>6}  Elo (temporada)")
    for i, e in enumerate(orden, 1):
        o, d, s = netos[e]
        f = filas.get(e)
        rec = f.total.texto() if f and f.total.jugados else ""
        pit = f"{f.total.victorias_pitagoricas:.1f}" if f and f.total.jugados else ""
        tendencia = chispa([r for t, _, r in elo.historial[e] if t == args.temporada][-40:])
        print(f"  {i:>2}  {nombre(e)[:25]:<26}{rec:>8}{elo.rating.get(e, 1500):>7.0f}{s:>+7.1f}{o:>+7.1f}{d:>+7.1f}{pit:>6}  {tendencia}")
    print(f"\n  Ventaja de campo estimada: {ratings.ventaja_campo:+.1f} pts · media de la liga {ratings.media:.1f} pts por equipo")


def _mostrar_prediccion(local, visitante, neutral, pr, linea=None, total_linea=None):
    sede = "campo neutral" if neutral else f"en {local}"
    _titulo(f"{nombre(visitante)} @ {nombre(local)} ({sede})")
    favorito = local if pr["margen"] > 0 else visitante
    print(f"  Marcador esperado: {local} {pr['puntos_local']:.1f} - {pr['puntos_visitante']:.1f} {visitante}")
    print(f"  Spread del modelo: {favorito} -{abs(pr['margen']):.1f}   (Elo {pr['margen_elo']:+.1f} · ratings "
          f"{pr['margen_ratings']:+.1f} · descanso {pr.get('ajuste_descanso', 0.0):+.1f} · jugadores "
          f"{pr.get('ajuste_jugadores', 0.0):+.1f}, desde el local)")
    print(f"  Total esperado: {pr['total']:.1f} puntos")
    _seccion("Probabilidad de victoria")
    print(linea_pct(local, 100 * pr["prob_local"], 8) + f"   moneyline justa {modelos.moneyline_justa(pr['prob_local'])}")
    print(linea_pct(visitante, 100 * (1 - pr["prob_local"]), 8) + f"   moneyline justa {modelos.moneyline_justa(1 - pr['prob_local'])}")
    if linea is not None:
        _seccion("Contra la línea que indicas")
        p = modelos.prob_cubrir(pr["margen"], linea)
        print(f"  Diferencia con el modelo: {pr['margen'] - linea:+.1f} pts para el local")
        print(f"  Prob. de que {local} cubra: {100 * p:.1f}% · {visitante}: {100 * (1 - p):.1f}%")
    if total_linea is not None:
        p_over = 1 - normal_cdf(total_linea, pr["total"], modelos.DESVIACION_TOTAL)
        print(f"  Total {total_linea}: over {100 * p_over:.1f}% · under {100 * (1 - p_over):.1f}%")


def cmd_predecir(partidos, args):
    local = equipo_de(args.local, partidos)
    visitante = equipo_de(args.visitante, partidos)
    if local == visitante:
        salir("Elige dos equipos distintos.")
    elo, ratings = modelos.ajustar_modelos(partidos, args.temporada)
    temporada = _de_temporada(partidos, args)
    programado = next((p for p in temporada if not p.jugado and p.local == local and p.visitante == visitante), None)
    ctx = _jugadores(args)
    if programado and not args.neutral:
        pr = modelos.predecir_partido(elo, ratings, programado, descansos(temporada), ctx)
        print(f"  (partido del calendario: {programado.fecha}; incluye el descanso de cada equipo)")
    else:
        plantilla = modelos.ajuste_jugadores(ctx, local, visitante, date.today())
        pr = {**modelos.predecir(elo, ratings, local, visitante, args.neutral, plantilla), "ajuste_jugadores": plantilla}
    _mostrar_prediccion(local, visitante, args.neutral, pr, args.linea, args.total)
    for e in (local, visitante):
        bajas = _bajas(ctx, e, date.today())
        if bajas:
            print(f"  No jugaron el último partido de {e}: {bajas}")
    print("\n  Orientativo: combina Elo, ratings ajustados por rival, descanso y jugadores disponibles. Sin parte de")
    print("  lesionados, supone que cada equipo juega con los mismos que en su partido anterior.")


def cmd_pronosticos(partidos, args):
    pend = [p for p in _de_temporada(partidos, args) if not p.jugado]
    if not pend:
        salir(f"No hay partidos pendientes en {_t(args)}.")
    desde = date.fromisoformat(args.fecha) if args.fecha else min(p.fecha for p in pend)
    fechas = sorted({p.fecha for p in pend if p.fecha >= desde})[:args.dias]
    elo, ratings = modelos.ajustar_modelos(partidos, args.temporada)
    dias = descansos(_de_temporada(partidos, args))
    ctx = _jugadores(args)
    _titulo(f"Pronósticos NBA {_t(args)} — " + (f"{fechas[0]}" if len(fechas) == 1 else f"{fechas[0]} a {fechas[-1]}"))
    print(f"  {'Fecha':<12}{'Partido':<14}{'Prob. local':>12}{'Spread':>9}{'Total':>8}{'Marcador':>10}{'Jug.':>6}  Notas")
    for p in (p for p in pend if p.fecha in fechas):
        pr = modelos.predecir_partido(elo, ratings, p, dias, ctx)
        d = pr["ajuste_descanso"]
        notas = ["local en días seguidos"] if d < 0 else ["visitante en días seguidos"] if d > 0 else []
        notas += [f"bajas {e}: {b}" for e in (p.visitante, p.local) for b in [_bajas(ctx, e, p.fecha)] if b]
        print(f"  {str(p.fecha):<12}{p.marcador():<14}{100 * pr['prob_local']:>11.1f}%{-pr['margen']:>+9.1f}{pr['total']:>8.1f}"
              f"{pr['puntos_visitante']:>6.0f}-{pr['puntos_local']:<3.0f}{pr['ajuste_jugadores']:>+6.1f}  {' · '.join(notas)}")
    print("\n  Spread desde el punto de vista del local (negativo = local favorito). Jug.: ajuste por jugadores")
    print("  disponibles, en puntos para el local. Bajas: jugadores importantes que no jugaron el último partido")
    print("  de su equipo (entre paréntesis, los puntos que vale cada uno); se supone que tampoco juegan este.")


def cmd_simular(partidos, args):
    resultados, pendientes = modelos.simular_temporada(partidos, args.temporada, args.n, args.semilla)
    _titulo(f"Simulación de la temporada {_t(args)} ({args.n} simulaciones, {pendientes} partidos pendientes)")
    if not pendientes:
        print("  La temporada regular está completa; se simulan solo el play-in y los playoffs.")
    for conf in CONFERENCIAS:
        _seccion(conf)
        print(f"  {'Equipo':<26}{'Vict. esp.':>11}  {'Playoffs':<30}{'Top 6':>8}{'1º':>8}{'Final':>8}{'Campeón':>9}")
        eqs = sorted((e for e in resultados if conferencia(e, args.temporada) == conf),
                     key=lambda e: (-resultados[e].get("playoffs", 0), -resultados[e].get("victorias", 0)))
        for e in eqs:
            r = resultados[e]
            p = 100 * r.get("playoffs", 0)
            print(f"  {nombre(e)[:25]:<26}{r.get('victorias', 0):>11.1f}  {barra(p, 20)} {p:5.1f}%"
                  f"{100 * r.get('top6', 0):>7.1f}%{100 * r.get('primero', 0):>7.1f}%{100 * r.get('final', 0):>7.1f}%"
                  f"{100 * r.get('campeon', 0):>8.1f}%")
    print("\n  Playoffs incluye pasar el play-in (puestos 7-10). Desempates simplificados.")
    print("  Final = llegar a las Finales de la NBA. Lesiones y traspasos futuros no se tienen en cuenta.")


def cmd_evaluar(partidos, args):
    try:
        m = modelos.evaluar(partidos, args.temporada, jugadores=jugadores.por_partido(args.conexion))
    except ValueError as e:
        salir(str(e))
    n = m.get("n", 0)
    if not n:
        salir("No hay partidos que evaluar.")
    _titulo(f"Validación del modelo en {_t(args)} (día a día, sin datos futuros)")
    print(f"  Partidos evaluados: {int(n)}")
    print(linea_pct("Acierto ganador (combinado)", pct(m["aciertos"], n), 34))
    print(linea_pct("Acierto ganador (solo Elo)", pct(m["aciertos_elo"], n), 34))
    print(linea_pct("Acierto ganador (solo ratings)", pct(m["aciertos_ratings"], n), 34))
    print(linea_pct("Gana siempre el local", pct(m["gana_local"], n), 34))
    print(f"  Brier score: {m['brier'] / n:.3f} (0.25 = lanzar una moneda; menor es mejor) · solo Elo {m['brier_elo'] / n:.3f}"
          f" · log-loss {m['logloss'] / n:.3f}")
    print(f"  Error medio del margen: {m['error_margen'] / n:.2f} pts · del total: {m['error_total'] / n:.2f} pts")
    print("  La base no tiene líneas de apuestas de la NBA, así que no hay comparación con el mercado.")


def cmd_estadisticas(partidos, args):
    if args.conexion is None:
        salir("Este comando necesita la base de datos: python3 -m analisis_deportivo recopilar")
    resumenes = estadisticas.por_equipo(estadisticas.cargar(args.conexion, args.temporada))
    if not resumenes:
        salir(f"No hay estadísticas de juego para {_t(args)}.")
    columnas = [
        ("Neto", lambda r: r.neto, True, "+.1f"),
        ("Ataque", lambda r: r.favor_de("eficiencia"), True, ".1f"),
        ("Defensa", lambda r: r.contra_de("eficiencia"), False, ".1f"),
        ("Ritmo", lambda r: r.favor_de("ritmo"), True, ".1f"),
        ("eFG%", lambda r: r.favor_de("efg"), True, ".1f"),
        ("eFG% riv", lambda r: r.contra_de("efg"), False, ".1f"),
        ("%Pérd", lambda r: r.favor_de("pct_perdidas"), False, ".1f"),
        ("%RebOf", lambda r: r.favor_de("pct_rebote_of"), True, ".1f"),
        ("TL/TC", lambda r: r.favor_de("tasa_libres"), True, ".3f"),
        ("%Triple", lambda r: r.favor_de("pct_triple"), True, ".1f"),
        ("Triples%", lambda r: r.favor_de("tasa_triples"), True, ".1f"),
        ("Asist", lambda r: r.favor_de("asistencias"), True, ".1f"),
    ]
    claves = {c[0].lower(): c for c in columnas}
    orden = claves.get((args.orden or "neto").lower())
    if orden is None:
        salir(f"Columna desconocida. Opciones: {', '.join(c[0] for c in columnas)}")
    filas = sorted(resumenes.values(), key=lambda r: -orden[1](r) if orden[2] else orden[1](r))
    _titulo(f"Estadísticas de juego {_t(args)} (temporada regular, ordenado por {orden[0]})")
    print(f"  {'#':>2} {'Eq.':<5}" + "".join(f"{c[0]:>9}" for c in columnas))
    for i, r in enumerate(filas, 1):
        print(f"  {i:>2} {r.equipo:<5}" + "".join(f"{format(c[1](r), c[3]):>9}" for c in columnas))
    print("\n  Ataque/Defensa: puntos anotados/permitidos por 100 posesiones · Neto: la diferencia · Ritmo: posesiones por partido")
    print("  eFG%: acierto de tiro contando el triple como 1.5 · %Pérd: posesiones que acaban en pérdida")
    print("  %RebOf: rebotes ofensivos capturados · TL/TC: tiros libres anotados por tiro de campo · Triples%: tiros que son triples")


def registrar(subparsers):
    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("-d", "--datos", default=None, help="Base de datos .sqlite (por defecto, la del repositorio)")
    comunes.add_argument("-t", "--temporada", help="Temporada: 2025-26 o 2026 (por defecto, la más reciente)")
    parser = subparsers.add_parser("nba", help="Análisis de la NBA")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("clasificacion", parents=[comunes], help="Clasificación", aliases=["tabla"])
    p.add_argument("--vista", choices=["conferencia", "division", "liga"], default="conferencia")
    p.set_defaults(func=cmd_clasificacion)

    p = sub.add_parser("equipo", parents=[comunes], help="Informe completo de un equipo")
    p.add_argument("equipo", help="Abreviatura (LAL) o nombre (Lakers)")
    p.add_argument("--ultimos", type=int, default=15, help="Partidos recientes a mostrar")
    p.set_defaults(func=cmd_equipo)

    p = sub.add_parser("h2h", parents=[comunes], help="Historial entre dos equipos desde 2001-02")
    p.add_argument("equipo_a")
    p.add_argument("equipo_b")
    p.add_argument("--ultimos", type=int, default=20)
    p.set_defaults(func=cmd_h2h)

    p = sub.add_parser("liga", parents=[comunes], help="Resumen estadístico de la temporada", aliases=["resumen"])
    p.add_argument("--solo-regular", action="store_true", help="Excluir play-in y playoffs")
    p.set_defaults(func=cmd_liga)

    p = sub.add_parser("estadisticas", parents=[comunes], help="Eficiencia, ritmo y cuatro factores de todos los equipos")
    p.add_argument("--orden", help="Columna por la que ordenar (por defecto 'Neto')")
    p.set_defaults(func=cmd_estadisticas)

    p = sub.add_parser("ranking", parents=[comunes], help="Power ranking (Elo, rating neto, ataque, defensa)")
    p.set_defaults(func=cmd_ranking)

    p = sub.add_parser("predecir", parents=[comunes], help="Predicción de un partido")
    p.add_argument("local")
    p.add_argument("visitante")
    p.add_argument("--neutral", action="store_true")
    p.add_argument("--linea", type=float, help="Ventaja del local según una casa de apuestas (LAL -5.5 en casa → 5.5)")
    p.add_argument("--total", type=float, help="Total de puntos de una casa de apuestas")
    p.set_defaults(func=cmd_predecir)

    p = sub.add_parser("pronosticos", parents=[comunes], help="Pronósticos de los próximos días")
    p.add_argument("--fecha", help="Desde esta fecha (AAAA-MM-DD); por defecto, el próximo día con partidos")
    p.add_argument("--dias", type=int, default=1, help="Número de días con partidos a mostrar")
    p.set_defaults(func=cmd_pronosticos)

    p = sub.add_parser("simular", parents=[comunes], help="Probabilidades de playoffs y de título por simulación Monte Carlo")
    p.add_argument("-n", type=int, default=2000, help="Número de simulaciones")
    p.add_argument("--semilla", type=int, help="Semilla aleatoria para resultados reproducibles")
    p.set_defaults(func=cmd_simular)

    p = sub.add_parser("evaluar", parents=[comunes], help="Valida la precisión del modelo en una temporada")
    p.set_defaults(func=cmd_evaluar)

    p = sub.add_parser("equipos", parents=[comunes], help="Lista equipos por división")
    p.set_defaults(func=cmd_equipos)

    parser.set_defaults(ejecutar=_ejecutar)


def _ejecutar(args):
    if not (args.datos or base.disponible()):
        salir("La NBA necesita la base de datos: python3 -m analisis_deportivo recopilar")
    try:
        args.conexion = base.conectar(args.datos)
        partidos = cargar_desde_base(args.conexion)
    except (OSError, ValueError) as e:
        salir(f"Error al cargar datos: {e}")
    except sqlite3.OperationalError:
        salir("La base de datos no tiene partidos de la NBA. Actualízala con: python3 -m analisis_deportivo recopilar")
    if not jugados(partidos):
        salir("No hay partidos de la NBA en la base de datos.")
    disponibles = temporadas(partidos)
    print(f"(base de datos: NBA {texto_temporada(disponibles[0])} a {texto_temporada(disponibles[-1])} · {len(partidos):,} partidos)")
    args.ultima_temporada = max(disponibles)
    explicita = args.temporada is not None
    try:
        args.temporada = leer_temporada(args.temporada) if explicita else max(disponibles)
    except ValueError:
        salir(f"Temporada no válida: {args.temporada!r}. Usa el formato 2025-26.")
    if args.temporada not in disponibles:
        salir(f"Temporada {texto_temporada(args.temporada)} no está en los datos "
              f"({texto_temporada(disponibles[0])} a {texto_temporada(disponibles[-1])}).")
    # Antes del primer partido de la temporada, lo que necesita resultados usa la anterior
    sin_jugar = not any(p.jugado for p in partidos if p.temporada == args.temporada)
    if sin_jugar and not explicita and args.func in (cmd_evaluar, cmd_liga, cmd_estadisticas):
        args.temporada -= 1
        print(f"(la temporada {texto_temporada(args.temporada + 1)} aún no ha empezado: se muestra la {_t(args)})")
    args.func(partidos, args)
