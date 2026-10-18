"""Punto de entrada: python -m analisis_deportivo {futbol|nfl|descargar} ..."""

import argparse
import os
import sys

from . import descargas
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


def construir_parser():
    parser = argparse.ArgumentParser(
        prog="analisis_deportivo",
        description="Análisis estadístico y predicción de partidos de fútbol y de la NFL.",
    )
    sub = parser.add_subparsers(dest="deporte_cmd", required=True)
    futbol_cli.registrar(sub, lambda: descargas.datos_recientes("futbol_", descargas.EJEMPLO_FUTBOL))
    nfl_cli.registrar(sub, lambda: descargas.datos_recientes("nfl_", descargas.EJEMPLO_NFL))

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
