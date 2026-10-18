# Estadísticas deportivas: fútbol y NFL

Programa en Python para analizar partidos de **fútbol (soccer)** y de la **NFL**: clasificaciones, informes completos de equipos, estadísticas de liga, rankings de fuerza, predicciones y validación de los modelos con datos históricos.

Solo necesita Python 3.9 o posterior. No usa librerías externas.

## Inicio rápido

```bash
# 1. Descargar datos reales (opcional; sin esto se usan los datos de ejemplo simulados)
python3 -m analisis_deportivo descargar futbol espana 2025-26
python3 -m analisis_deportivo descargar nfl 2023-2026

# 2. Analizar
python3 -m analisis_deportivo futbol tabla
python3 -m analisis_deportivo futbol equipo "Real Madrid"
python3 -m analisis_deportivo nfl clasificacion --vista playoffs
python3 -m analisis_deportivo nfl equipo Chiefs
```

Por defecto, cada deporte usa el **último archivo descargado** y, si no hay ninguno, los datos de ejemplo de `datos/`. Para usar otro archivo, añade `--datos RUTA` a cualquier comando. Los nombres de equipo pueden ser parciales: `betis`, `Chiefs` o `KC`.

## Fútbol

| Comando | Qué muestra |
|---|---|
| `tabla [--condicion local\|visitante\|descanso]` | Clasificación con puntos por partido y forma. Con `descanso`, cómo iría la tabla si los partidos terminaran en el descanso. |
| `equipo NOMBRE` | Informe completo del equipo (ver lista abajo) |
| `h2h EQUIPO_A EQUIPO_B` | Enfrentamientos directos, goles, marcan ambos y más de 2.5 goles |
| `liga` | Resumen de la competición (ver lista abajo) |
| `lideres [METRICA] [-n N]` | Mejores equipos en ataque, defensa, porterías a cero, tiros, TSR, conversión, paradas, córners, tarjetas, remontadas, etc. |
| `ranking` | Elo, fuerza de ataque, fuerza de defensa y diferencia de goles esperada |
| `predecir LOCAL VISITANTE [--neutral] [--cuotas 1 X 2]` | 1X2, doble oportunidad, más/menos goles, marcan ambos, hándicap, marcadores más probables y valor esperado frente a las cuotas que indiques |
| `pronosticos [-n N]` | Pronóstico de los partidos pendientes del archivo |
| `evaluar` | Validación histórica del modelo (ver más abajo) |

Opciones comunes: `--datos`, más `--desde AAAA-MM-DD` y `--hasta AAAA-MM-DD` para filtrar fechas.

El **informe de equipo** incluye:

- Rendimiento total, como local y como visitante.
- Forma, racha actual y rachas máximas.
- Porcentajes de goles: porterías a cero, marcan ambos, más de 1.5, 2.5 y 3.5 goles, y marcadores más repetidos.
- Primera y segunda parte: resultado al descanso, cuántas veces gana cuando va ganando y cuántas puntúa cuando va perdiendo, y remontadas.
- Estadísticas de juego: tiros, tiros a puerta, córners, faltas y tarjetas, a favor y en contra. También el dominio de tiros (TSR: porcentaje de los tiros del partido que hace el equipo), la conversión de tiros, la precisión y el porcentaje de paradas.
- Resultados frente a rivales de la parte alta, media y baja de la tabla.
- Evolución de la posición y de los puntos a lo largo de la temporada.
- Elo, fuerza de ataque y fuerza de defensa.
- Últimos partidos y pronóstico de los próximos.

El **resumen de liga** incluye:

- Porcentaje de victorias locales, empates y victorias visitantes, y ventaja de jugar en casa.
- Distribución de goles por partido y marcadores más frecuentes.
- Matriz de resultado al descanso frente a resultado final, y remontadas.
- Medias de tiros, córners, faltas y tarjetas.
- Porcentaje de partidos que gana el favorito de las casas de apuestas.

Las estadísticas de juego y las cuotas aparecen solo si el archivo las trae. Los archivos de football-data.co.uk las incluyen.

## NFL

| Comando | Qué muestra |
|---|---|
| `clasificacion [--vista division\|playoffs\|liga]` | Récord, PCT, puntos, local, visitante, división, conferencia, racha y últimos 5. La vista `playoffs` muestra la siembra de cada conferencia. |
| `equipo EQUIPO` | Informe completo del equipo (ver lista abajo) |
| `h2h A B` | Historial entre dos equipos en todas las temporadas del archivo, contra el spread y over/under |
| `liga [--solo-regular]` | Resumen de la temporada (ver lista abajo) |
| `lideres [METRICA]` | Ataque, defensa, diferencia, victorias pitagóricas, suerte, % ATS y % over |
| `ranking` | Power ranking con Elo, SRS, ofensa y defensa ajustadas, y victorias pitagóricas |
| `predecir LOCAL VISITANTE [--linea X] [--total Y] [--neutral]` | Marcador esperado, spread, total, probabilidad de victoria, moneyline justa y probabilidad de cubrir la línea del mercado |
| `pronosticos [--semana N]` | Pronósticos de la próxima semana comparados con las líneas del mercado |
| `simular [-n N]` | Simulación Monte Carlo del resto de la temporada: victorias esperadas y probabilidad de playoffs, de ganar la división y de ser primero de conferencia |
| `evaluar` | Validación semana a semana frente a las casas de apuestas |

Opciones comunes: `--datos` y `-t/--temporada` (por defecto, la más reciente del archivo).

Algunos términos:

- **ATS** ("against the spread"): resultado contra la línea de apuestas. Un equipo "cubre" si supera la ventaja que le daba el mercado.
- **Over/under**: si los puntos del partido superan o no el total que marca el mercado.
- **Victorias pitagóricas**: las victorias que "merecía" un equipo según sus puntos a favor y en contra.
- **SRS** ("Simple Rating System"): cuántos puntos es mejor o peor un equipo que la media, ajustado por la dificultad de sus rivales.

El **informe de equipo** incluye:

- Récord, victorias pitagóricas y "suerte" (victorias reales menos pitagóricas).
- Elo, SRS, ofensa y defensa ajustadas, y dificultad del calendario jugado y del restante.
- Récords en más de 15 situaciones: local, visitante, división, conferencia, partidos ajustados, palizas, prórroga, como favorito o underdog, tras la semana de descanso, en semana corta, bajo techo, con frío, con viento, contra equipos con récord ganador y en playoffs. Cada una con su récord contra el spread y su over/under.
- Récord por quarterback titular.
- Partido a partido con la línea, el ATS y el over/under.
- Próximos partidos con su probabilidad de victoria.

El **resumen de liga** incluye:

- Porcentaje de victorias locales y márgenes más frecuentes (los "números clave", como 3 y 7).
- Porcentaje de partidos ajustados, palizas y prórrogas.
- Mercado de apuestas: con qué frecuencia gana y cubre el favorito, y error medio del spread y del total.
- Puntos según condiciones: bajo techo, al aire libre, con frío, con viento y en partidos divisionales.

## Modelos

**Fútbol**

- **Poisson con corrección Dixon-Coles.** Calcula una fuerza de ataque y una de defensa para cada equipo, ajustadas por la calidad de sus rivales. Tiene en cuenta la ventaja de jugar en casa y da más peso a los partidos recientes (un partido de hace 240 días pesa la mitad). También acerca a la media a los equipos con pocos datos. La corrección de Dixon-Coles mejora la estimación de los marcadores bajos; su parámetro se estima con los propios datos.
- **Elo.** Un rating que sube o baja después de cada partido, y más cuanto mayor es la diferencia de goles.

**NFL**

- **Elo** al estilo FiveThirtyEight: tiene en cuenta el margen de victoria y la ventaja de campo, y acerca a los equipos a la media un tercio entre temporadas.
- **Ratings de ofensa y defensa** ajustados por la calidad de los rivales. De ellos salen el SRS, el spread esperado y el total de puntos esperado. La ventaja de campo se estima con los datos, y la temporada anterior cuenta un 30 % para estabilizar las primeras semanas.
- **Predicción.** Es la media de los dos modelos. La probabilidad de victoria se calcula con una distribución normal de 13.5 puntos de desviación, que es la dispersión típica del margen final en la NFL.

**Validación.** El comando `evaluar` predice cada jornada o semana usando solo los partidos anteriores, como si fuera en tiempo real. Después compara el resultado con una referencia ingenua y con las casas de apuestas.

- **NFL, datos reales:** el modelo acierta el ganador en el 62–68 % de los partidos de 2023, 2024 y 2025. El favorito de las casas de apuestas acierta entre el 66 % y el 70 %.
- **La Liga 2025-26:** el modelo mejora a la referencia en todas las métricas. El RPS, la medida habitual para predicciones de 1X2 donde menos es mejor, baja de 0.225 a 0.212.

Batir al mercado de apuestas es muy difícil. Úsalo como herramienta de análisis, no como garantía.

## Fuentes de datos

- **football-data.co.uk:** resultados, descanso, tiros, córners, faltas, tarjetas y cuotas. Es la fuente preferida de `descargar futbol`.
- **openfootball (football.json):** resultados y descanso, incluidos los partidos pendientes. Se usa si football-data.co.uk no está disponible.
- **nflverse:** resultados de la NFL desde 1999, con líneas de apuestas, descanso entre partidos, estadio, techo, clima, quarterbacks y entrenadores.

Ligas disponibles para descargar: `espana`, `espana2`, `inglaterra`, `inglaterra2`, `alemania`, `italia`, `francia`, `portugal`, `holanda`, `belgica`, `turquia` y `escocia`.

### Formatos propios en CSV

Fútbol. Las columnas opcionales son `descanso_*`, `tiros_*`, `tiros_puerta_*`, `corners_*`, `faltas_*`, `amarillas_*`, `rojas_*` (con `_local` o `_visitante`), `cuota_local`, `cuota_empate`, `cuota_visitante` y `jornada`. Si dejas vacíos los goles, el partido cuenta como pendiente.

```csv
fecha,local,visitante,goles_local,goles_visitante,descanso_local,descanso_visitante,tiros_local,tiros_visitante
2025-08-16,Real Costa,Atlético Norte,2,1,1,0,14,9
```

NFL. Las columnas opcionales son `tipo` (REG, WC, DIV, CON o SB), `linea` (puntos de ventaja del local según el mercado), `total_linea`, `prorroga` y `neutral`. Para los equipos se usan las abreviaturas oficiales (KC, BUF, SF…).

```csv
temporada,semana,fecha,local,visitante,puntos_local,puntos_visitante,linea,total_linea
2025,1,2025-09-07,KC,BUF,27,24,2.5,48.5
```

## Estructura

```
analisis_deportivo/
  cli.py, comun.py, descargas.py
  futbol/  datos.py · analisis.py · modelos.py · cli.py
  nfl/     datos.py · equipos.py · analisis.py · modelos.py · cli.py
datos/                  ejemplos simulados (regenerables con scripts/generar_ejemplos.py)
datos/descargas/        datos reales descargados (ignorados por git)
tests/
```

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```
