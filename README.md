# Estadísticas deportivas

Programa en Python para analizar resultados de partidos (fútbol u otro deporte con marcador de goles/puntos) a partir de un archivo CSV. No necesita librerías externas: solo Python 3.9+.

## Uso rápido

```bash
python3 -m analisis_deportivo tabla                      # clasificación
python3 -m analisis_deportivo tabla --condicion local    # solo partidos en casa
python3 -m analisis_deportivo equipo "Real Costa"        # ficha de un equipo
python3 -m analisis_deportivo h2h "Real Costa" "Atlético Norte"
python3 -m analisis_deportivo resumen                    # métricas de la liga
python3 -m analisis_deportivo predecir "Atlético Norte" "CD Montaña"
python3 -m analisis_deportivo equipos                    # lista de equipos
```

Sin `--datos` se usa la liga ficticia de `datos/partidos_ejemplo.csv`. Para usar tus propios datos:

```bash
python3 -m analisis_deportivo --datos mi_liga.csv tabla
```

## Formato del CSV

```csv
fecha,local,visitante,goles_local,goles_visitante
2026-02-07,Real Costa,Atlético Norte,2,0
```

La fecha va en formato `AAAA-MM-DD`.

## Qué calcula

| Comando    | Contenido |
|------------|-----------|
| `tabla`    | Puntos (3/1/0), PJ, G, E, P, goles, diferencia y forma de los últimos 5 partidos |
| `equipo`   | Totales y separados local/visitante, % de victorias, goles por partido, porterías a cero, racha actual, últimos partidos |
| `h2h`      | Historial de enfrentamientos directos |
| `resumen`  | Goles por partido, % victorias local/empate/visitante, ambos marcan, más de 2.5 goles, mayor goleada |
| `predecir` | Probabilidades 1X2 y marcador más probable con un modelo de Poisson (fuerza de ataque y defensa local/visitante) |

## Estructura

```
analisis_deportivo/
  datos.py     # carga y validación del CSV
  analisis.py  # cálculos estadísticos (reutilizable desde otros scripts)
  cli.py       # interfaz de línea de comandos
datos/partidos_ejemplo.csv
tests/
```

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```
