"""Genera los informes automáticos de la carpeta informes/ (los usa la tarea diaria de GitHub Actions).

Ejecuta los mismos comandos del programa y guarda su salida en archivos Markdown que se
pueden leer directamente en GitHub. Uso: python3 scripts/generar_informes.py
"""

import contextlib
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo.cli import main  # noqa: E402

CARPETA = RAIZ / "informes"
LIGAS = [("espana", "LaLiga"), ("inglaterra", "Premier League"), ("italia", "Serie A"),
         ("alemania", "Bundesliga"), ("francia", "Ligue 1"), ("portugal", "Primeira Liga"), ("holanda", "Eredivisie")]


def ejecutar(*argumentos):
    """Salida de texto de un comando del programa (o el error, si falla)."""
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            main(list(argumentos))
    except SystemExit as e:
        if e.code not in (None, 0):
            salida.write(f"\n{e.code}\n")
    lineas = [l for l in salida.getvalue().splitlines() if not l.startswith("(base de datos")]
    return "\n".join(lineas).strip()


def bloque(titulo, texto):
    return f"## {titulo}\n\n```\n{texto}\n```\n"


def escribir(nombre, titulo, secciones, sello):
    contenido = f"# {titulo}\n\n_Actualizado automáticamente: {sello}_\n\n" + "\n".join(secciones)
    (CARPETA / nombre).write_text(contenido, encoding="utf-8")


def generar():
    CARPETA.mkdir(exist_ok=True)
    sello = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    indice = []

    for alias, nombre in LIGAS:
        archivo = f"futbol_{alias}.md"
        escribir(archivo, f"{nombre}: pronósticos y clasificación", [
            bloque("Pronósticos de los próximos partidos", ejecutar("futbol", "pronosticos", "-l", alias, "-n", "15")),
            bloque("Clasificación", ejecutar("futbol", "tabla", "-l", alias)),
            bloque("Ranking de fuerza", ejecutar("futbol", "ranking", "-l", alias)),
        ], sello)
        indice.append(f"- [{nombre}]({archivo})")

    escribir("nfl.md", "NFL: pronósticos, playoffs y ranking", [
        bloque("Pronósticos de la próxima semana", ejecutar("nfl", "pronosticos")),
        bloque("Probabilidades de playoffs", ejecutar("nfl", "simular", "--semilla", "1")),
        bloque("Clasificación por puestos de playoffs", ejecutar("nfl", "clasificacion", "--vista", "playoffs")),
        bloque("Power ranking", ejecutar("nfl", "ranking")),
    ], sello)
    indice.append("- [NFL](nfl.md)")

    secciones = [bloque(f"{nombre} (temporada en curso)", ejecutar("futbol", "evaluar", "-l", alias)) for alias, nombre in LIGAS[:5]]
    secciones.append(bloque("NFL (temporada en curso)", ejecutar("nfl", "evaluar")))
    escribir("evaluacion.md", "Precisión de los modelos", secciones, sello)
    indice.append("- [Precisión de los modelos (validación sin datos futuros)](evaluacion.md)")

    (CARPETA / "README.md").write_text(
        "# Informes automáticos\n\n"
        f"_Última actualización: {sello}_\n\n"
        "Una tarea de GitHub Actions actualiza cada día la base de datos con los partidos nuevos y "
        "regenera estos informes. No usa IA ni consume uso de Claude.\n\n" + "\n".join(indice) + "\n",
        encoding="utf-8")
    print(f"Informes generados en {CARPETA} ({sello})")


if __name__ == "__main__":
    generar()
