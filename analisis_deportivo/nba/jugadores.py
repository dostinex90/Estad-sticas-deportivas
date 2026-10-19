"""Ajuste de la NBA por jugadores disponibles (tabla nba_jugadores_partido de la base).

Valor de cada jugador: Game Score de Hollinger por minuto (una suma ponderada de puntos, tiros,
rebotes, asistencias, robos, tapones, faltas y pérdidas), solo con partidos anteriores, con más peso
para los recientes y encogido hacia un valor de reserva para quien ha jugado poco.

Valor de una plantilla: minutos habituales × valor de sus jugadores de rotación (los que suelen
jugar 20 minutos o más); los minutos que faltan hasta 240 se cubren con un reserva. El ajuste de
un equipo es k × (valor de la plantilla de hoy − valor medio de sus plantillas en los últimos 40
partidos): cuánto mejor o peor está que de costumbre. Como no hay parte de lesionados, se supone
que hoy juegan los mismos que en su partido anterior, salvo que ese partido fuera hace más de 60
días (después del verano las bajas de primavera ya no sirven). Ver experimentos/nba_jugadores.py.
"""

import sqlite3
from collections import defaultdict, deque
from datetime import date

N_HABITUAL = 40
ROTACION = 20.0
K = 0.2  # puntos de margen por punto de Game Score de diferencia
REINICIO_DIAS = 60


def game_score(f):
    """Game Score de Hollinger de una fila con los nombres de columna de ESPN."""
    g = lambda c: f.get(c) or 0.0  # noqa: E731
    return (g("points") + 0.4 * g("field_goals_made") - 0.7 * g("field_goals_attempted")
            - 0.4 * (g("free_throws_attempted") - g("free_throws_made")) + 0.7 * g("offensive_rebounds")
            + 0.3 * g("defensive_rebounds") + g("steals") + 0.7 * g("assists") + 0.7 * g("blocks")
            - 0.4 * g("fouls") - g("turnovers"))


class ContextoJugadores:
    def __init__(self, n_habitual=N_HABITUAL, rotacion=ROTACION, k=K, vida_media=365, m0=250, previo=0.2, n_minutos=20):
        """vida_media: días tras los que un partido pesa la mitad en el valor del jugador. m0: minutos
        ficticios a valor `previo` (un reserva) que encogen el valor de quien ha jugado poco.
        n_minutos: apariciones con las que se calculan los minutos habituales de cada jugador."""
        self.n_habitual, self.rotacion, self.k = n_habitual, rotacion, k
        self.vida_media, self.m0, self.previo = vida_media, m0, previo
        self.suma, self.minutos, self.fecha = defaultdict(float), defaultdict(float), {}
        self.apariciones = defaultdict(lambda: deque(maxlen=n_minutos))
        self.historial = defaultdict(lambda: deque(maxlen=n_habitual))  # equipo -> [jugadores de cada partido]
        self.ultima_fecha = {}  # equipo -> fecha de su último partido
        self.nombres = {}

    def agregar(self, fecha, equipo, jugadores):
        """Un partido jugado: jugadores = [(id, nombre, minutos, valoración)]. Hay que añadir los
        partidos de un día después de predecir los de ese día."""
        self.historial[equipo].append([j for j, *_ in jugadores])
        self.ultima_fecha[equipo] = fecha
        for j, nombre, minutos, gs in jugadores:
            if j in self.fecha:
                f = 0.5 ** ((fecha - self.fecha[j]).days / self.vida_media)
                self.suma[j] *= f
                self.minutos[j] *= f
            self.suma[j] += gs
            self.minutos[j] += minutos
            self.fecha[j] = fecha
            self.apariciones[j].append(minutos)
            self.nombres[j] = nombre

    def valor(self, j, fecha):
        """Game Score esperado por minuto."""
        f = 0.5 ** ((fecha - self.fecha[j]).days / self.vida_media) if j in self.fecha else 1.0
        return (self.suma[j] * f + self.m0 * self.previo) / (self.minutos[j] * f + self.m0)

    def minutos_habituales(self, j):
        a = self.apariciones.get(j)
        return sum(a) / len(a) if a else 0.0

    def plantilla(self, jugadores, fecha):
        esperado = {j: self.minutos_habituales(j) for j in jugadores}
        esperado = {j: m for j, m in esperado.items() if m >= self.rotacion}
        total = sum(esperado.values())
        escala = min(1.0, 240 / total) if total else 1.0
        return sum(m * escala * self.valor(j, fecha) for j, m in esperado.items()) + max(0.0, 240 - total) * self.previo

    def vigente(self, equipo, fecha):
        """True si el último partido del equipo es lo bastante reciente para suponer las mismas bajas."""
        return equipo in self.ultima_fecha and (fecha - self.ultima_fecha[equipo]).days <= REINICIO_DIAS

    def ajuste(self, equipo, fecha):
        """Puntos que gana (positivo) o pierde el equipo por sus jugadores disponibles frente a lo habitual."""
        hist = self.historial.get(equipo)
        if not hist or len(hist) < self.n_habitual or not self.vigente(equipo, fecha):
            return 0.0
        habitual = sum(self.plantilla(g, fecha) for g in hist) / len(hist)
        return self.k * (self.plantilla(hist[-1], fecha) - habitual)

    def ausentes(self, equipo, fecha):
        """[(nombre, minutos habituales, puntos que vale)] de los jugadores de rotación que jugaron
        con el equipo en sus últimos partidos pero no en el último (lesionados, traspasados...)."""
        hist = self.historial.get(equipo)
        if not hist or not self.vigente(equipo, fecha):
            return []
        ultimo = set(hist[-1])
        recientes = {j for g in list(hist)[-10:] for j in g} - ultimo
        res = []
        for j in recientes:
            m = self.minutos_habituales(j)
            if m >= self.rotacion:
                res.append((self.nombres.get(j, j), m, self.k * m * (self.valor(j, fecha) - self.previo)))
        return sorted(res, key=lambda r: -r[2])


def por_partido(con):
    """{id: (fecha, {equipo: [(jugador, nombre, minutos, valoración)]})}; {} si la base no tiene jugadores."""
    try:
        filas = con.execute("SELECT p.id, p.fecha, j.equipo, j.jugador, n.nombre, j.minutos, j.valoracion "
                            "FROM nba_jugadores_partido j JOIN nba_partidos p ON p.id = CAST(j.id AS TEXT) "
                            "LEFT JOIN nba_jugadores n ON n.jugador = j.jugador").fetchall()
    except sqlite3.OperationalError:
        return {}
    res = {}
    for gid, fecha, equipo, j, nombre, minutos, gs in filas:
        res.setdefault(gid, (date.fromisoformat(fecha), defaultdict(list)))[1][equipo].append((j, nombre, minutos, gs))
    return res


def contexto(datos, antes_de=None):
    """ContextoJugadores con los partidos de por_partido() anteriores a la fecha `antes_de` (todos si
    es None). Devuelve None si no hay datos de jugadores."""
    if not datos:
        return None
    ctx = ContextoJugadores()
    for gid, (fecha, equipos) in sorted(datos.items(), key=lambda kv: (kv[1][0], kv[0])):
        if antes_de is not None and fecha >= antes_de:
            break
        for equipo, jugadores in sorted(equipos.items()):
            ctx.agregar(fecha, equipo, jugadores)
    return ctx
