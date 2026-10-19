"""¿Mejora el modelo NBA si sabe qué jugadores faltan? Ajuste con 2012-13 a 2018-19, validación 2021-22 a 2025-26.

Uso: python3 experimentos/nba_jugadores.py [carpeta con player_box_AAAA.csv]   (búsqueda, ~15 min)
     (si faltan, se descargan de sportsdataverse-data, unos 18 MB por temporada)
     python3 experimentos/nba_jugadores.py --verificar   (modelos.evaluar del paquete con la base,
                                                          sin y con el ajuste por jugadores)

Valor de cada jugador: Game Score de Hollinger por minuto, solo con partidos anteriores, con
decaimiento temporal y encogido hacia un valor previo. Para cada partido y equipo:
  * valor de una plantilla = minutos habituales × valor de sus jugadores de rotación (ver ajustes());
  * habitual = valor medio de las plantillas de los últimos partidos del equipo;
  * hoy = valor de la plantilla de hoy, según dos supuestos:
      - "ideal": se sabe quién juega (el parte de lesionados acertaría del todo);
      - "realista": se supone que juega quien jugó alguno de los últimos `recientes` partidos del
        equipo (solo información anterior al día del partido, sin parte de lesionados).
  ajuste = k × (hoy − habitual), en puntos; k se ajusta con las temporadas de entrenamiento.
El resto del modelo (Elo, ratings, descanso) es el del paquete, con sus parámetros.
"""

import csv
import io
import itertools
import math
import sys
import urllib.request
from collections import defaultdict, deque
from datetime import date
from multiprocessing import Pool
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from analisis_deportivo import base  # noqa: E402
from analisis_deportivo.comun import normal_cdf  # noqa: E402
from analisis_deportivo.nba import modelos  # noqa: E402
from analisis_deportivo.nba.datos import cargar_desde_base, descansos  # noqa: E402
from analisis_deportivo.nba.equipos import POR_ID  # noqa: E402

URL = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_nba_player_boxscores/player_box_{}.csv"
ENTRENAMIENTO = list(range(2013, 2020))
VALIDACION = list(range(2022, 2027))
PRIMERA = 2008  # historial previo para el valor de los jugadores


def _n(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def game_score(f):
    return (_n(f["points"]) + 0.4 * _n(f["field_goals_made"]) - 0.7 * _n(f["field_goals_attempted"])
            - 0.4 * (_n(f["free_throws_attempted"]) - _n(f["free_throws_made"])) + 0.7 * _n(f["offensive_rebounds"])
            + 0.3 * _n(f["defensive_rebounds"]) + _n(f["steals"]) + 0.7 * _n(f["assists"]) + 0.7 * _n(f["blocks"])
            - 0.4 * _n(f["fouls"]) - _n(f["turnovers"]))


def cargar_jugadores(carpeta):
    """{game_id: {equipo: [(jugador, minutos, game_score)]}} de los que jugaron, y {game_id: fecha}."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    por_partido, fechas = defaultdict(lambda: defaultdict(list)), {}
    for t in range(PRIMERA, 2027):
        archivo = carpeta / f"player_box_{t}.csv"
        if not archivo.exists():
            archivo.write_bytes(urllib.request.urlopen(URL.format(t), timeout=300).read())
        for f in csv.DictReader(io.open(archivo, encoding="utf-8")):
            equipo, minutos = POR_ID.get(f["team_id"]), _n(f["minutes"])
            if equipo and minutos > 0:
                por_partido[f["game_id"]][equipo].append((f["athlete_id"], minutos, game_score(f)))
                fechas[f["game_id"]] = f["game_date"]
    return por_partido, fechas


def ajustes(partidos, por_partido, n_habitual=20, recientes=1, vida_media=365, m0=250, previo=0.2, rotacion=15.0,
            n_minutos=20, reinicio_dias=None):
    """{(game_id, equipo): (diferencia ideal, diferencia realista)} en unidades de Game Score.

    Valor de una plantilla = Σ minutos esperados × valor de sus jugadores de rotación (los que suelen
    jugar `rotacion` minutos o más, según sus últimas `n_minutos` apariciones) + los minutos que
    faltan hasta 240 a valor `previo`. Los suplentes de poco uso no cuentan, así que no influye
    quién sale en los minutos de la basura de una paliza (eso sí delataría el resultado).
    habitual = media del valor de las plantillas de los últimos `n_habitual` partidos del equipo.
    reinicio_dias: si el último partido del equipo fue hace más días (verano), el realista vale 0."""
    ultima_fecha = {}
    suma, minutos, fecha_j = defaultdict(float), defaultdict(float), {}
    apariciones = defaultdict(lambda: deque(maxlen=n_minutos))  # jugador -> minutos en sus últimos partidos
    historial = defaultdict(lambda: deque(maxlen=max(n_habitual, recientes)))  # equipo -> [jugadores]
    res = {}

    def valor(j, hoy):
        f = 0.5 ** ((hoy - fecha_j[j]).days / vida_media) if j in fecha_j else 1.0
        return (suma[j] * f + m0 * previo) / (minutos[j] * f + m0)

    def plantilla(jugadores, hoy):
        esperado = {j: sum(apariciones[j]) / len(apariciones[j]) for j in jugadores if apariciones.get(j)}
        esperado = {j: m for j, m in esperado.items() if m >= rotacion}
        total = sum(esperado.values())
        escala = min(1.0, 240 / total) if total else 1.0
        return sum(m * escala * valor(j, hoy) for j, m in esperado.items()) + max(0.0, 240 - total) * previo

    jugados = sorted((p for p in partidos if p.jugado and p.id in por_partido), key=lambda p: (p.fecha, p.id))
    for fecha, del_dia in itertools.groupby(jugados, key=lambda p: p.fecha):
        del_dia = list(del_dia)
        for p in del_dia:
            for e in (p.local, p.visitante):
                hist = list(historial[e])
                if len(hist) < n_habitual:
                    continue
                base_v = sum(plantilla(g, fecha) for g in hist[-n_habitual:]) / n_habitual
                ideal = [j for j, _, _ in por_partido[p.id][e]]
                realista = {j for g in hist[-recientes:] for j in g}
                parado = reinicio_dias is not None and (fecha - ultima_fecha[e]).days > reinicio_dias
                res[(p.id, e)] = (plantilla(ideal, fecha) - base_v, 0.0 if parado else plantilla(realista, fecha) - base_v)
        for p in del_dia:  # actualizar después de predecir todo el día
            for e in (p.local, p.visitante):
                historial[e].append([j for j, _, _ in por_partido[p.id][e]])
                ultima_fecha[e] = fecha
                for j, m, gs in por_partido[p.id][e]:
                    if j in fecha_j:
                        f = 0.5 ** ((fecha - fecha_j[j]).days / vida_media)
                        suma[j] *= f
                        minutos[j] *= f
                    suma[j] += gs
                    minutos[j] += m
                    fecha_j[j] = fecha
                    apariciones[j].append(m)
    return res


PARTIDOS = None


def componentes(temporada):
    """[(id, local, visitante, margen del modelo del paquete, margen real)] día a día sin datos futuros."""
    jug = sorted((p for p in PARTIDOS if p.jugado and p.temporada <= temporada), key=lambda p: p.fecha)
    objetivo = [p for p in jug if p.temporada == temporada]
    dias = descansos([p for p in PARTIDOS if p.temporada == temporada])
    elo, ratings = modelos.EloNBA(), modelos.RatingsNBA()
    idx, primera, res = 0, True, []
    for fecha in sorted({p.fecha for p in objetivo}):
        while idx < len(jug) and jug[idx].fecha < fecha:
            elo.actualizar(jug[idx])
            idx += 1
        elo.nueva_temporada(temporada)
        ratings.ajustar(jug[:idx] if primera else jug[max(0, idx - 3000):idx], temporada, fecha)
        if primera:
            ratings.iteraciones, primera = 8, False
        for p in (p for p in objetivo if p.fecha == fecha):
            res.append((p.id, p.local, p.visitante, modelos.predecir_partido(elo, ratings, p, dias)["margen"], p.margen))
    return res


def _inicio():
    global PARTIDOS
    PARTIDOS = cargar_desde_base(base.conectar())


def brier(comp, aj, k, cual):
    tot = 0.0
    for gid, l, v, m, real in comp:
        a = aj.get((gid, l), (0, 0))[cual] - aj.get((gid, v), (0, 0))[cual]
        tot += (normal_cdf(m + k * a, 0, modelos.DESVIACION_PROB) - (real > 0)) ** 2
    return tot / len(comp)


def acierto(comp, aj, k, cual):
    return sum(((m + k * (aj.get((g, l), (0, 0))[cual] - aj.get((g, v), (0, 0))[cual])) > 0) == (real > 0)
               for g, l, v, m, real in comp) / len(comp)


def main():
    carpeta = sys.argv[1] if len(sys.argv) > 1 else RAIZ / "datos" / "descargas" / "nba_jugadores"
    _inicio()
    print("Cargando jugadores...")
    por_partido, _ = cargar_jugadores(carpeta)
    print("Componentes del modelo actual (día a día)...")
    with Pool(initializer=_inicio) as pool:
        listas = pool.map(componentes, ENTRENAMIENTO + VALIDACION)
    comp = dict(zip(ENTRENAMIENTO + VALIDACION, listas))
    ent = [c for t in ENTRENAMIENTO for c in comp[t]]
    val = [c for t in VALIDACION for c in comp[t]]
    ks = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6, 0.8]

    print("\nBúsqueda en entrenamiento (Brier con el mejor k; ideal / realista):")
    mejor = {}
    for n_hab, rec, rot in itertools.product([10, 20, 40, 60], [1, 2], [10.0, 15.0, 20.0]):
        aj = ajustes(PARTIDOS, por_partido, n_habitual=n_hab, recientes=rec, rotacion=rot)
        for cual, nombre in ((0, "ideal"), (1, "realista")):
            b, k = min((brier(ent, aj, k, cual), k) for k in ks)
            print(f"  habitual={n_hab} recientes={rec} rotación={rot} {nombre}: {b:.5f} (k={k})")
            if nombre not in mejor or b < mejor[nombre][0]:
                mejor[nombre] = (b, k, aj, (n_hab, rec, rot))
    for cual, nombre in ((0, "ideal"), (1, "realista")):
        _, k, aj, params = mejor[nombre]
        print(f"\n{nombre.capitalize()} (habitual, recientes, rotación) = {params}, k = {k}")
        if cual == 1:  # ¿mejor sin suponer bajas tras el verano?
            n_hab, rec, rot = params
            for reinicio in (30, 60, 90):
                aj_r = ajustes(PARTIDOS, por_partido, n_habitual=n_hab, recientes=rec, rotacion=rot, reinicio_dias=reinicio)
                b = brier(ent, aj_r, k, cual)
                print(f"  sin bajas si el último partido fue hace más de {reinicio} días: entrenamiento {b:.5f}")
                if b < mejor[nombre][0]:
                    mejor[nombre] = (b, k, aj_r, params + (reinicio,))
                    aj = aj_r
            print(f"  → {mejor[nombre][3]}")
        for etiqueta, temporadas in (("Entrenamiento", ENTRENAMIENTO), ("Validación", VALIDACION)):
            for t in temporadas:
                c = comp[t]
                print(f"  {t - 1}-{str(t)[2:]}: Brier {brier(c, aj, 0, cual):.4f} → {brier(c, aj, k, cual):.4f} · "
                      f"acierto {acierto(c, aj, 0, cual):.3f} → {acierto(c, aj, k, cual):.3f}")
            c = ent if etiqueta == "Entrenamiento" else val
            print(f"  {etiqueta}: Brier {brier(c, aj, 0, cual):.4f} → {brier(c, aj, k, cual):.4f} · "
                  f"acierto {acierto(c, aj, 0, cual):.3f} → {acierto(c, aj, k, cual):.3f}")


def verificar():
    from analisis_deportivo.nba.jugadores import por_partido

    _inicio()
    datos = por_partido(base.conectar())
    print("Temporada   Brier sin / con jugadores   Acierto sin / con")
    for nombre, temporadas in (("Entrenamiento", ENTRENAMIENTO), ("Validación", VALIDACION)):
        tot = defaultdict(float)
        for t in temporadas:
            sin, con = modelos.evaluar(PARTIDOS, t), modelos.evaluar(PARTIDOS, t, jugadores=datos)
            for clave, m in (("sin", sin), ("con", con)):
                tot[clave + "_b"] += m["brier"]
                tot[clave + "_a"] += m["aciertos"]
            tot["n"] += sin["n"]
            print(f"  {t - 1}-{str(t)[2:]}   {sin['brier'] / sin['n']:.4f} / {con['brier'] / con['n']:.4f}"
                  f"             {sin['aciertos'] / sin['n']:.3f} / {con['aciertos'] / con['n']:.3f}")
        n = tot["n"]
        print(f"  {nombre}: Brier {tot['sin_b'] / n:.4f} → {tot['con_b'] / n:.4f} · "
              f"acierto {tot['sin_a'] / n:.3f} → {tot['con_a'] / n:.3f}\n")


if __name__ == "__main__":
    verificar() if "--verificar" in sys.argv else main()
