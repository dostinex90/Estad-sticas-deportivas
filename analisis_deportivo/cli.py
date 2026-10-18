"""Punto de entrada: python -m analisis_deportivo {futbol|nfl|descargar} ..."""

import argparse
import os
import sys

from . import base, descargas
from .futbol import cli as futbol_cli
from .nfl import cli as nfl_cli


def cmd_descargar(args):
    try:
        if args.deporte == "futbol":
            destino, url, errores = descargas.descargar_futbol(args.liga, args.temporada, args.fuente)
            for e in errores:
                print(f"Aviso: no se pudo usar {e}")
            if errores:
                print("Se usa openfootball: resultados y descanso, sin tiros, córners, tarjetas ni cuotas.")
            print(f"Descargado {url}\n→ {destino}")
            print(f"\nYa puedes usarlo: python3 -m analisis_deportivo futbol tabla  (o --datos {destino})")
        else:
            desde, _, hasta = args.temporadas.partition("-")
            destino, url, n = descargas.descargar_nfl(int(desde), int(hasta) if hasta else int(desde))
            print(f"Descargados {n} partidos de {url}\n→ {destino}")
            print(f"\nYa puedes usarlo: python3 -m analisis_deportivo nfl clasificacion  (o --datos {destino})")
    except (OSError, ValueError) as e:
        sys.exit(f"Error en la descarga: {e}")


def cmd_recopilar(args):
    try:
        ruta = base.recopilar(avisar=print, comprimir=not args.sin_comprimir)
    except (OSError, ValueError) as e:
        sys.exit(f"Error al recopilar: {e}")
    print(f"\nBase de datos lista: {ruta} ({ruta.stat().st_size / 1e6:.1f} MB)")


def cmd_base(args):
    try:
        con = base.conectar()
    except FileNotFoundError as e:
        sys.exit(str(e))
    r = base.resumen(con)
    print("\nContenido de la base de datos\n═════════════════════════════")
    for f in r["fuentes"]:
        print(f"  {f['tabla']:<40}{f['filas']:>9,}  {f['actualizado']}  ({f['origen']})")
    print(f"\n  {'Código':<7}{'Competición':<34}{'Partidos':>9}{'Temporadas':>22}{'Pend.':>7}{'% tiros':>9}{'% cuotas':>10}")
    for c in r["competiciones"]:
        nombre, pais, alias, *_ = base.COMPETICIONES[c["competicion"]]
        print(f"  {c['competicion']:<7}{(nombre + ' (' + pais + ')')[:33]:<34}{c['n']:>9,}{c['desde'] + ' a ' + c['hasta']:>22}"
              f"{c['pendientes']:>7}{100 * c['con_tiros'] / c['n']:>8.0f}%{100 * c['con_cuotas'] / c['n']:>9.0f}%")
    print(f"\n  Selecciones: {r['n_torneos']} torneos. Los más frecuentes:")
    for t in r["torneos"][:12]:
        print(f"    {t['torneo']:<40}{t['n']:>7,}  {t['desde'][:4]}-{t['hasta'][:4]}")
    n, desde, hasta, pend = r["nfl"]
    print(f"\n  NFL: {n:,} partidos {desde}-{hasta} ({pend} pendientes)")
    if r["nfl_estadisticas"]:
        n, desde, hasta = r["nfl_estadisticas"]
        print(f"  NFL: {n:,} registros de estadísticas por equipo y partido {desde}-{hasta}")
    print("\n  Alias de competiciones: " + ", ".join(v[2] for v in base.COMPETICIONES.values()))
    print("  Alias de torneos: " + ", ".join(base.TORNEOS))


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="analisis_deportivo",
        description="Análisis estadístico y predicción de partidos de fútbol y de la NFL.",
    )
    sub = parser.add_subparsers(dest="deporte_cmd", required=True)
    futbol_cli.registrar(sub, lambda: descargas.datos_recientes("futbol_", descargas.EJEMPLO_FUTBOL))
    nfl_cli.registrar(sub, lambda: descargas.datos_recientes("nfl_", descargas.EJEMPLO_NFL))

    p = sub.add_parser("recopilar", help="Descarga todas las fuentes y construye la base de datos local")
    p.add_argument("--sin-comprimir", action="store_true", help="No generar la copia comprimida .gz")
    p.set_defaults(ejecutar=cmd_recopilar)

    p = sub.add_parser("base", help="Muestra el contenido de la base de datos")
    p.set_defaults(ejecutar=cmd_base)

    p = sub.add_parser("descargar", help="Descarga datos reales")
    dep = p.add_subparsers(dest="deporte", required=True)
    f = dep.add_parser("futbol", help="Liga de fútbol (football-data.co.uk u openfootball)")
    f.add_argument("liga", choices=list(descargas.LIGAS))
    f.add_argument("temporada", help="Ej.: 2025-26")
    f.add_argument("--fuente", choices=["auto", "football-data", "openfootball"], default="auto",
                   help="auto: prueba football-data.co.uk (más estadísticas) y si falla openfootball")
    n = dep.add_parser("nfl", help="Temporadas de la NFL (nflverse)")
    n.add_argument("temporadas", help="Una temporada (2025) o un rango (2022-2026)")
    p.set_defaults(ejecutar=cmd_descargar)
    return parser


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        args.ejecutar(args)
    except BrokenPipeError:  # salida cortada (p. ej. con | head)
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
