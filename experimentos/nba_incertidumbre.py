"""Cuánto se equivocan las previsiones de victorias de pretemporada de la NBA (2012-13 a 2018-19).

Para cada temporada de entrenamiento se ajustan los modelos solo con las temporadas anteriores y se
suman las probabilidades de victoria de todos los partidos de temporada regular. El error frente a
las victorias reales tiene dos partes: el azar de los partidos (varianza binomial) y no conocer la
fuerza real de cada equipo. La segunda, pasada a puntos, es modelos.INCERTIDUMBRE_FUERZA.

Uso: python3 experimentos/nba_incertidumbre.py
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analisis_deportivo import base  # noqa: E402
from analisis_deportivo.nba import analisis, modelos  # noqa: E402
from analisis_deportivo.nba.datos import cargar_desde_base, descansos  # noqa: E402

partidos = cargar_desde_base(base.conectar())
errores, varianzas = [], []
for t in range(2013, 2020):
    elo, ratings = modelos.ajustar_modelos([p for p in partidos if p.temporada < t], t - 1)
    elo.nueva_temporada(t)
    dias = descansos([p for p in partidos if p.temporada == t])
    esperadas, varianza = {}, {}
    for p in (p for p in partidos if p.temporada == t and p.tipo == "REG"):
        q = modelos.predecir_partido(elo, ratings, p, dias)["prob_local"]
        for e, pr in ((p.local, q), (p.visitante, 1 - q)):
            esperadas[e] = esperadas.get(e, 0) + pr
            varianza[e] = varianza.get(e, 0) + pr * (1 - pr)
    filas = analisis.clasificacion(partidos, t)
    for e in esperadas:
        errores.append(filas[e].total.g - esperadas[e])
        varianzas.append(varianza[e])
error = math.sqrt(sum(x * x for x in errores) / len(errores))
azar = sum(varianzas) / len(varianzas)
extra = math.sqrt(max(error ** 2 - azar, 0))
victorias_por_punto = 82 / math.sqrt(2 * math.pi) / modelos.DESVIACION_PROB  # pendiente cerca de un 50 %
print(f"Error cuadrático medio: {error:.2f} victorias · azar de los partidos: {math.sqrt(azar):.2f} · "
      f"resto: {extra:.2f} victorias ≈ {extra / victorias_por_punto:.2f} puntos de fuerza "
      "(algo más, porque la pendiente es menor en partidos desiguales)")
