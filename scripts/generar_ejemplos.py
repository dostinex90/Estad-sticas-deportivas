"""Genera los datos de ejemplo SIMULADOS de datos/ (reproducibles con semilla fija).

Uso: python3 scripts/generar_ejemplos.py
"""

import csv
import datetime
import itertools
import math
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo.nfl.equipos import DIVISIONES  # noqa: E402


def poisson(rng, lam):
    limite, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limite:
            return k
        k += 1


def futbol(rng):
    fuerza = {
        "Atlético Norte": (1.55, 0.75), "Real Costa": (1.45, 0.80), "Deportivo Sur": (1.25, 0.90),
        "Unión Valle": (1.05, 0.85), "Sporting Río": (1.10, 1.05), "Racing Puerto": (1.00, 1.00),
        "CF Llanura": (0.90, 1.00), "Club Ribera": (0.95, 1.15), "Ciudad Alta FC": (0.80, 1.15),
        "CD Montaña": (0.75, 1.30),
    }
    equipos = list(fuerza)
    # Calendario de liga a doble vuelta (método del círculo)
    rondas = []
    lista = equipos[:]
    for _ in range(len(lista) - 1):
        rondas.append([(lista[i], lista[-1 - i]) for i in range(len(lista) // 2)])
        lista = [lista[0]] + [lista[-1]] + lista[1:-1]
    rondas += [[(b, a) for a, b in r] for r in rondas]

    filas = []
    inicio = datetime.date(2025, 8, 16)
    for n, ronda in enumerate(rondas, 1):
        fecha = inicio + datetime.timedelta(days=7 * (n - 1))
        for local, visit in ronda:
            lam = 1.45 * fuerza[local][0] * fuerza[visit][1]
            mu = 1.10 * fuerza[visit][0] * fuerza[local][1]
            fila = {"fecha": fecha, "jornada": n, "local": local, "visitante": visit}
            # Cuotas con un 5 % de margen a partir de las probabilidades "reales"
            p = [0.0, 0.0, 0.0]
            for i in range(11):
                for j in range(11):
                    v = math.exp(-lam) * lam**i / math.factorial(i) * math.exp(-mu) * mu**j / math.factorial(j)
                    p[0 if i > j else 1 if i == j else 2] += v
            fila["cuota_local"], fila["cuota_empate"], fila["cuota_visitante"] = (round(1 / (x * 1.05), 2) for x in p)
            if n <= len(rondas) - 2:  # las dos últimas jornadas quedan pendientes
                gl, gv = poisson(rng, lam), poisson(rng, mu)
                fila.update(goles_local=gl, goles_visitante=gv,
                            descanso_local=sum(rng.random() < 0.44 for _ in range(gl)),
                            descanso_visitante=sum(rng.random() < 0.44 for _ in range(gv)))
                for lado, g, l_ in (("local", gl, lam), ("visitante", gv, mu)):
                    tp = g + poisson(rng, l_ * 2.2)
                    fila[f"tiros_puerta_{lado}"] = tp
                    fila[f"tiros_{lado}"] = tp + poisson(rng, l_ * 5)
                    fila[f"corners_{lado}"] = poisson(rng, 3.2 * l_ / 1.25)
                    fila[f"faltas_{lado}"] = poisson(rng, 11.5)
                    fila[f"amarillas_{lado}"] = poisson(rng, 2.1)
                    fila[f"rojas_{lado}"] = int(rng.random() < 0.06)
            filas.append(fila)
    campos = ["fecha", "jornada", "local", "visitante", "goles_local", "goles_visitante",
              "descanso_local", "descanso_visitante"]
    campos += [f"{s}_{lado}" for s in ("tiros", "tiros_puerta", "corners", "faltas", "amarillas", "rojas")
               for lado in ("local", "visitante")]
    campos += ["cuota_local", "cuota_empate", "cuota_visitante"]
    with open(RAIZ / "datos" / "futbol_ejemplo.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def nfl(rng):
    equipos = [e for eqs in DIVISIONES.values() for e in eqs]
    fuerza = {e: rng.gauss(0, 6) for e in equipos}
    filas = []
    for temporada, jugadas in ((2024, 18), (2025, 12)):
        for e in equipos:
            fuerza[e] = 0.75 * fuerza[e] + rng.gauss(0, 3)
        inicio = datetime.date(temporada, 9, 8)
        for semana in range(1, 18):
            orden = equipos[:]
            rng.shuffle(orden)
            for local, visit in zip(orden[::2], orden[1::2]):
                dif = fuerza[local] - fuerza[visit] + 1.8
                fila = {"temporada": temporada, "semana": semana, "tipo": "REG",
                        "fecha": inicio + datetime.timedelta(days=7 * (semana - 1)),
                        "local": local, "visitante": visit,
                        "linea": round(2 * (dif + rng.gauss(0, 1.5))) / 2,
                        "total_linea": round(2 * rng.gauss(44.5, 3)) / 2}
                if semana <= jugadas:
                    margen = round(rng.gauss(dif, 13.5))
                    total = max(abs(margen) + 3, round(rng.gauss(45, 10)))
                    if (total + margen) % 2:
                        total += 1
                    pl, pv = (total + margen) // 2, (total - margen) // 2
                    prorroga = abs(margen) <= 3 and rng.random() < 0.25
                    if pl == pv:
                        pl += 3
                    fila.update(puntos_local=pl, puntos_visitante=pv, prorroga=int(prorroga))
                filas.append(fila)
    campos = ["temporada", "semana", "tipo", "fecha", "local", "visitante", "puntos_local",
              "puntos_visitante", "prorroga", "linea", "total_linea"]
    with open(RAIZ / "datos" / "nfl_ejemplo.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


if __name__ == "__main__":
    futbol(random.Random(7))
    nfl(random.Random(11))
    print("Datos de ejemplo generados en datos/")
