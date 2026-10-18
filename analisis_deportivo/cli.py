"""Interfaz de línea de comandos."""

import argparse
import sys
from pathlib import Path

from . import analisis
from .datos import cargar_partidos, equipos

DATOS_EJEMPLO = Path(__file__).resolve().parent.parent / "datos" / "partidos_ejemplo.csv"


def _barra(pct, ancho=20):
    llenos = round(pct / 100 * ancho)
    return "█" * llenos + "░" * (ancho - llenos)


def _comprobar_equipo(nombre, partidos):
    disponibles = equipos(partidos)
    if nombre not in disponibles:
        sys.exit(f"Equipo desconocido: {nombre!r}. Disponibles: {', '.join(disponibles)}")


def cmd_tabla(partidos, args):
    tabla = analisis.tabla_posiciones(partidos, args.condicion)
    titulo = {None: "General", "local": "Como local", "visitante": "Como visitante"}[args.condicion]
    print(f"\nTabla de posiciones — {titulo}\n")
    print(f"{'#':>2}  {'Equipo':<20}{'PJ':>4}{'G':>4}{'E':>4}{'P':>4}{'GF':>5}{'GC':>5}{'DG':>5}{'Pts':>5}  Forma")
    print("-" * 72)
    for pos, s in enumerate(tabla, 1):
        print(
            f"{pos:>2}  {s.equipo:<20}{s.jugados:>4}{s.ganados:>4}{s.empatados:>4}{s.perdidos:>4}"
            f"{s.goles_favor:>5}{s.goles_contra:>5}{s.diferencia:>+5}{s.puntos:>5}  {s.forma()}"
        )


def cmd_equipo(partidos, args):
    _comprobar_equipo(args.equipo, partidos)
    print(f"\nEstadísticas de {args.equipo}\n")
    for etiqueta, cond in (("Total", None), ("Local", "local"), ("Visitante", "visitante")):
        s = analisis.calcular_estadisticas(partidos, cond).get(args.equipo)
        if not s:
            continue
        print(f"[{etiqueta}]")
        print(f"  Partidos: {s.jugados}  ({s.ganados}G {s.empatados}E {s.perdidos}P)  Puntos: {s.puntos}")
        print(f"  % victorias: {_barra(s.porcentaje_victorias)} {s.porcentaje_victorias:.1f}%")
        print(f"  Goles a favor/partido: {s.goles_favor_por_partido:.2f}   en contra/partido: {s.goles_contra_por_partido:.2f}")
        print(f"  Porterías a cero: {s.porterias_cero}")
        if cond is None:
            r, n = s.racha_actual()
            nombres = {"G": "victorias", "E": "empates", "P": "derrotas"}
            print(f"  Forma (últimos 5): {s.forma()}   Racha actual: {n} {nombres[r]}")
        print()

    print("Últimos partidos:")
    for p in [p for p in partidos if p.participa(args.equipo)][-args.ultimos:]:
        print(f"  {p.fecha}  {p.local} {p.goles_local}-{p.goles_visitante} {p.visitante}")


def cmd_h2h(partidos, args):
    _comprobar_equipo(args.equipo_a, partidos)
    _comprobar_equipo(args.equipo_b, partidos)
    duelos, resumen = analisis.enfrentamientos_directos(partidos, args.equipo_a, args.equipo_b)
    print(f"\n{args.equipo_a} vs {args.equipo_b} — {len(duelos)} enfrentamientos\n")
    for p in duelos:
        print(f"  {p.fecha}  {p.local} {p.goles_local}-{p.goles_visitante} {p.visitante}")
    print(f"\n  Victorias {args.equipo_a}: {resumen[args.equipo_a]}")
    print(f"  Victorias {args.equipo_b}: {resumen[args.equipo_b]}")
    print(f"  Empates: {resumen['empates']}")


def cmd_resumen(partidos, args):
    r = analisis.resumen_liga(partidos)
    if not r["partidos"]:
        print("No hay partidos.")
        return
    m = r["mayor_goleada"]
    print("\nResumen de la competición\n")
    print(f"  Partidos: {r['partidos']}   Goles: {r['goles']}   Media: {r['goles_por_partido']:.2f} por partido")
    print(f"  Gana local:     {_barra(r['pct_local'])} {r['pct_local']:.1f}%")
    print(f"  Empate:         {_barra(r['pct_empate'])} {r['pct_empate']:.1f}%")
    print(f"  Gana visitante: {_barra(r['pct_visitante'])} {r['pct_visitante']:.1f}%")
    print(f"  Ambos marcan:   {_barra(r['pct_ambos_marcan'])} {r['pct_ambos_marcan']:.1f}%")
    print(f"  Más de 2.5:     {_barra(r['pct_mas_2_5'])} {r['pct_mas_2_5']:.1f}%")
    print(f"  Mayor goleada: {m.fecha} {m.local} {m.goles_local}-{m.goles_visitante} {m.visitante}")


def cmd_predecir(partidos, args):
    _comprobar_equipo(args.local, partidos)
    _comprobar_equipo(args.visitante, partidos)
    try:
        pr = analisis.predecir_partido(partidos, args.local, args.visitante)
    except ValueError as e:
        sys.exit(str(e))
    gl, gv = pr["marcador_probable"]
    print(f"\nPredicción: {args.local} (local) vs {args.visitante} (visitante)\n")
    print(f"  Goles esperados: {pr['goles_esperados_local']:.2f} - {pr['goles_esperados_visitante']:.2f}")
    print(f"  Gana {args.local:<14} {_barra(100 * pr['prob_local'])} {100 * pr['prob_local']:.1f}%")
    print(f"  {'Empate':<19} {_barra(100 * pr['prob_empate'])} {100 * pr['prob_empate']:.1f}%")
    print(f"  Gana {args.visitante:<14} {_barra(100 * pr['prob_visitante'])} {100 * pr['prob_visitante']:.1f}%")
    print(f"  Marcador más probable: {gl}-{gv} ({100 * pr['prob_marcador']:.1f}%)")
    print("\n  Modelo de Poisson con fuerzas de ataque/defensa; orientativo, no garantiza resultados.")


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="analisis_deportivo",
        description="Análisis estadístico de resultados deportivos a partir de un CSV.",
    )
    parser.add_argument(
        "-d", "--datos", default=str(DATOS_EJEMPLO),
        help="CSV con columnas fecha,local,visitante,goles_local,goles_visitante (por defecto, datos de ejemplo)",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("tabla", help="Tabla de posiciones")
    p.add_argument("--condicion", choices=["local", "visitante"], help="Solo partidos como local o visitante")
    p.set_defaults(func=cmd_tabla)

    p = sub.add_parser("equipo", help="Estadísticas detalladas de un equipo")
    p.add_argument("equipo")
    p.add_argument("--ultimos", type=int, default=5, help="Número de partidos recientes a mostrar")
    p.set_defaults(func=cmd_equipo)

    p = sub.add_parser("h2h", help="Enfrentamientos directos entre dos equipos")
    p.add_argument("equipo_a")
    p.add_argument("equipo_b")
    p.set_defaults(func=cmd_h2h)

    p = sub.add_parser("resumen", help="Resumen global de la competición")
    p.set_defaults(func=cmd_resumen)

    p = sub.add_parser("predecir", help="Probabilidades de un partido futuro")
    p.add_argument("local")
    p.add_argument("visitante")
    p.set_defaults(func=cmd_predecir)

    p = sub.add_parser("equipos", help="Lista los equipos del archivo")
    p.set_defaults(func=lambda partidos, args: print("\n".join(equipos(partidos))))

    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        partidos = cargar_partidos(args.datos)
    except (OSError, ValueError) as e:
        sys.exit(f"Error al cargar datos: {e}")
    args.func(partidos, args)
