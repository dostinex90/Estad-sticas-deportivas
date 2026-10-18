"""Utilidades compartidas por los módulos de fútbol y NFL."""

import csv
import math
import sys


def barra(pct, ancho=20):
    pct = max(0.0, min(100.0, pct))
    llenos = round(pct / 100 * ancho)
    return "█" * llenos + "░" * (ancho - llenos)


def linea_pct(etiqueta, pct, ancho_etiqueta=22):
    return f"  {etiqueta:<{ancho_etiqueta}} {barra(pct)} {pct:5.1f}%"


def pct(a, b):
    return 100 * a / b if b else 0.0


def media(valores):
    valores = list(valores)
    return sum(valores) / len(valores) if valores else 0.0


def poisson(k, lam):
    return math.exp(-lam) * lam**k / math.factorial(k)


def normal_cdf(x, mu=0.0, sigma=1.0):
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def racha_actual(resultados):
    """(resultado, longitud) de la racha vigente en una secuencia como "GGEP"."""
    if not resultados:
        return None, 0
    ultimo = resultados[-1]
    n = 0
    for r in reversed(resultados):
        if r != ultimo:
            break
        n += 1
    return ultimo, n


def racha_maxima(resultados, validos):
    """Longitud de la racha más larga formada solo por resultados en `validos`."""
    mejor = actual = 0
    for r in resultados:
        actual = actual + 1 if r in validos else 0
        mejor = max(mejor, actual)
    return mejor


def chispa(valores):
    """Mini gráfico de línea con caracteres de bloque."""
    if not valores:
        return ""
    bloques = "▁▂▃▄▅▆▇█"
    lo, hi = min(valores), max(valores)
    if hi == lo:
        return bloques[3] * len(valores)
    return "".join(bloques[round((v - lo) / (hi - lo) * (len(bloques) - 1))] for v in valores)


def leer_csv(ruta):
    """Lee un CSV tolerando BOM y archivos en latin-1. Devuelve (cabecera, filas como dict)."""
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            with open(ruta, newline="", encoding=codificacion) as f:
                lector = csv.DictReader(f)
                filas = list(lector)
                return lector.fieldnames or [], filas
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {ruta}")


def entero_opcional(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor in ("", "NA", "nan", "None"):
        return None
    return int(float(valor))


def real_opcional(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    if valor in ("", "NA", "nan", "None"):
        return None
    return float(valor)


def salir(mensaje):
    sys.exit(mensaje)


def elegir_equipo(nombre, disponibles):
    """Resuelve un nombre de equipo de forma tolerante (mayúsculas, coincidencia parcial)."""
    if nombre in disponibles:
        return nombre
    bajo = nombre.lower()
    exactos = [e for e in disponibles if e.lower() == bajo]
    if exactos:
        return exactos[0]
    parciales = [e for e in disponibles if bajo in e.lower()]
    if len(parciales) == 1:
        return parciales[0]
    # Si el texto cubre casi todo un único nombre ("barcelona" → "FC Barcelona"), se elige ese
    cobertura = sorted(((len(bajo) / len(e), e) for e in parciales), reverse=True)
    if cobertura and cobertura[0][0] >= 0.5 and (len(cobertura) == 1 or cobertura[1][0] < cobertura[0][0]):
        return cobertura[0][1]
    if parciales:
        salir(f"Nombre ambiguo {nombre!r}: {', '.join(parciales)}")
    salir(f"Equipo desconocido: {nombre!r}. Disponibles: {', '.join(sorted(disponibles))}")
