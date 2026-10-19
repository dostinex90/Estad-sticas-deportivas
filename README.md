# Estadísticas deportivas: fútbol, NFL y NBA

Programa en Python para analizar partidos de **fútbol (soccer)**, de la **NFL** y de la **NBA**: clasificaciones, informes completos de equipos, estadísticas de liga, rankings de fuerza, predicciones y validación de los modelos con datos históricos.

Solo necesita Python 3.9 o posterior. No usa librerías externas.

## Ver el programa en la web (sin instalar nada)

👉 **https://dostinex90.github.io/Estad-sticas-deportivas/**

Esta versión publicada se actualiza sola cada día. Incluye la temporada actual de 7 ligas (LaLiga, Premier League, Serie A, Bundesliga, Ligue 1, Primeira Liga y Eredivisie), de la NFL y de la NBA:

- Clasificaciones e informes de cada equipo.
- Predicciones de cualquier partido entre dos equipos de la misma liga.
- Pronósticos y resúmenes de liga.
- Cara a cara con todo el historial desde 2000.
- Rankings.
- NFL: probabilidades de playoffs y estadísticas de juego.
- NBA: probabilidades de playoffs y de título, pronósticos día a día y estadísticas de juego.

Para temporadas antiguas, las otras 31 ligas o selecciones, usa la interfaz completa (abajo).

La genera `scripts/generar_sitio.py`. Una web publicada no puede ejecutar Python, así que el script calcula de antemano todas las respuestas como archivos JSON.

## Interfaz web

```bash
python3 -m analisis_deportivo web
```

Abre en el navegador (http://localhost:8000) una interfaz con todo el programa: clasificaciones, informes de equipo, predicciones con gráficos, pronósticos, resúmenes de liga, cara a cara, rankings, goleadores, probabilidades de playoffs y estadísticas de la NFL y de la NBA. Lee los datos directamente de la base de datos.

- **Menús:** se elige la competición (38 ligas, todas las selecciones o un torneo concreto) y la temporada.
- **Tablas:** se puede hacer clic en un equipo para ver su informe y ordenar las tablas por columnas.
- **Gráficos:** muestran el detalle al pasar el ratón.
- **Tema:** hay modo claro y modo oscuro.
- **Enlaces:** la dirección de la página guarda lo que estás viendo, así que puedes guardarla o compartirla.
- **Opciones:**
  - `--puerto 8001`: otro puerto.
  - `--no-abrir`: no abre el navegador automáticamente.
  - `--host 0.0.0.0`: permite abrirla desde el móvil u otro dispositivo de tu misma red, en `http://IP-de-tu-computadora:8000`.
- **En GitHub Codespaces:** ejecuta el comando y abre el puerto 8000 que te ofrece la pestaña *Puertos*.

No necesita instalar nada más que Python. Para detenerla, pulsa Ctrl+C en la terminal.

## Automatización diaria (GitHub Actions)

El repositorio se actualiza solo en los servidores de GitHub. No usa IA ni consume uso de Claude, y es gratis en repositorios públicos.

- **Cada día a las 09:17 UTC** (`.github/workflows/actualizacion-diaria.yml`):
  1. Descarga los partidos nuevos (`recopilar`).
  2. Comprueba la integridad de los datos (`scripts/verificar_datos.py`): duplicados, fechas imposibles, temporadas incompletas y resultados atrasados. Si algo está mal, no publica nada.
  3. Pasa las pruebas.
  4. Regenera los informes de la carpeta [`informes/`](informes/): pronósticos y clasificación de 7 ligas de fútbol, pronósticos, playoffs y ranking de la NFL y de la NBA, y la precisión de los modelos.
  5. Si algo cambió, los guarda en el repositorio.
  6. Publica la versión web en GitHub Pages.
  7. La base actualizada queda como descarga del propio workflow durante 30 días.
- **Con cada cambio de código** (`.github/workflows/pruebas.yml`): pasa todas las pruebas.
- **Para lanzarla a mano:** pestaña **Actions** del repositorio → *Actualización diaria* → **Run workflow**.
- **Para pausarla:** en la misma pantalla, menú **···** → *Disable workflow*.

Los informes también se pueden generar en local con `python3 scripts/generar_informes.py`.

## Base de datos incluida

El repositorio trae una base de datos SQLite comprimida, `datos/base_deportiva.sqlite.gz`, con todo lo que se puede recopilar de fuentes abiertas. Se descomprime sola la primera vez que se usa.

| Contenido | Volumen | Periodo |
|---|---|---|
| Partidos de clubes de 38 ligas de 27 países, con resultado, descanso, tiros, tiros a puerta, córners, faltas, tarjetas, cuotas 1X2 y de más/menos 2.5 goles, y el Elo previo de cada equipo | 238.858 partidos | 2000 – septiembre de 2026 |
| Temporada 2026-27 en curso (resultados recientes y calendario pendiente) de las 8 ligas principales y Brasil | 3.082 partidos | 2026-27 |
| Partidos de selecciones nacionales en 225 torneos, con sede, campo neutral y ganador de la tanda de penaltis | 49.945 partidos | 1872 – 2026 |
| Goles de selecciones con autor, minuto, penalti y autogol | 47.914 goles | 1916 – 2026 |
| Partidos de la NFL con líneas de apuestas, descanso entre partidos, clima, estadio, quarterbacks y entrenadores | 7.548 partidos | 1999 – 2026 |
| Estadísticas de cada equipo en cada partido de la NFL: yardas, EPA, pérdidas de balón, sacks, penalizaciones, goles de campo y más (unas 130 columnas) | 14.707 registros | 1999 – 2026 |
| Parte oficial de lesionados de la NFL de cada semana (Out, Doubtful, Questionable) | 35.356 bajas | 2012 – 2026 |
| % de jugadas (snaps) que jugó cada jugador de la NFL en cada partido | 301.608 registros | 2013 – 2026 |
| Partidos de la NBA (temporada regular, final de la NBA Cup, play-in y playoffs) con prórrogas y sede, y el calendario de la temporada en curso | 33.390 partidos | 2001-02 – 2026-27 |
| Estadísticas de cada equipo en cada partido de la NBA: tiros de campo, triples, tiros libres, rebotes, asistencias, robos, tapones, pérdidas, faltas y puntos en la pintura | 64.352 registros | 2001-02 – 2025-26 |
| Minutos y valoración (Game Score) de cada jugador de la NBA en cada partido | 404.702 registros | 2011-12 – 2025-26 |

```bash
python3 -m analisis_deportivo base        # qué contiene: ligas, temporadas, cobertura de tiros y cuotas
python3 -m analisis_deportivo recopilar   # vuelve a descargarlo todo para actualizarla (~1 minuto)
```

Cuando la base existe, todos los comandos la usan. Se elige qué analizar con estas opciones:

- **`--liga`**: código (`SP1`, `E0`, `D1`...), alias en español (`espana`, `inglaterra`, `alemania`, `mexico`, `argentina`, `brasil`, `mls`...) o `selecciones`. Por defecto, `espana`.
- **`--torneo`**: un torneo de selecciones, con alias como `mundial`, `eurocopa`, `copa-america`, `eliminatorias`, `nations-league`, `copa-oro` o `amistosos`.
- **`-t/--temporada`**: una temporada (`2025-26`), un rango (`2015-16:2025-26`) o `todas`. En selecciones son años (`2018:2026`). Por defecto, la más reciente con partidos jugados.

```bash
python3 -m analisis_deportivo futbol tabla -l inglaterra -t 2003-04
python3 -m analisis_deportivo futbol h2h Barcelona "Real Madrid"            # los 48 clásicos desde 2000
python3 -m analisis_deportivo futbol liga -l alemania -t todas              # 26 temporadas de Bundesliga
python3 -m analisis_deportivo futbol tabla --torneo mundial -t 2022
python3 -m analisis_deportivo futbol goleadores --torneo mundial -t todas
python3 -m analisis_deportivo futbol predecir Argentina France -l selecciones --neutral
python3 -m analisis_deportivo nfl estadisticas -t 2025 --orden "Dif.pérd"
python3 -m analisis_deportivo nba simular
python3 -m analisis_deportivo nba equipo Lakers -t 2025-26
```

Para predecir una temporada, los modelos de fútbol también usan la temporada anterior. Así los pronósticos de principio de temporada no dependen solo de unas pocas jornadas.

**Limitaciones de las fuentes:**

- Faltan algunas temporadas o partes de ellas: por ejemplo, LaLiga 2006-07 y parte de la Premier League 2003-05.
- Las ligas no europeas no traen tiros ni córners.
- Los nombres de clubes siguen la nomenclatura de football-data.co.uk ("Ath Madrid", "Man United").
- Los goleadores de selecciones cubren sobre todo partidos oficiales, no todos los amistosos.

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

Por defecto se usa la **base de datos incluida**. Si no existe, se usa el último archivo descargado y, si tampoco hay ninguno, los datos de ejemplo de `datos/`. Para usar otro archivo, añade `--datos RUTA` a cualquier comando. Los nombres de equipo pueden ser parciales: `betis`, `Chiefs` o `KC`.

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
| `goleadores [--equipo X]` | Máximos goleadores de selecciones y reparto de los goles por minuto (requiere la base) |

Opciones comunes: `--liga`, `--torneo` y `--temporada` (con la base), `--datos`, y `--desde AAAA-MM-DD` y `--hasta AAAA-MM-DD` para filtrar fechas.

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
| `estadisticas [--orden COLUMNA]` | Tabla de los 32 equipos con yardas, yardas permitidas, EPA por jugada en ataque y defensa, diferencial de pérdidas, sacks, juego de pase y de carrera, jugadas explosivas y penalizaciones (requiere la base) |

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
- Estadísticas de juego por partido, en ataque y en defensa, con su puesto en la liga: yardas, EPA, pérdidas, primeros downs, jugadas explosivas, sacks, penalizaciones y goles de campo (requiere la base).
- Récord por quarterback titular.
- Partido a partido con la línea, el ATS y el over/under.
- Próximos partidos con su probabilidad de victoria.

El **resumen de liga** incluye:

- Porcentaje de victorias locales y márgenes más frecuentes (los "números clave", como 3 y 7).
- Porcentaje de partidos ajustados, palizas y prórrogas.
- Mercado de apuestas: con qué frecuencia gana y cubre el favorito, y error medio del spread y del total.
- Qué decide los partidos: con qué frecuencia gana el equipo que domina cada estadística. En 2025, el que tuvo mejor EPA por jugada ganó el 82 % de los partidos, y el que perdió menos balones, el 78 %.
- Puntos según condiciones: bajo techo, al aire libre, con frío, con viento y en partidos divisionales.

## NBA

Requiere la base de datos. Los equipos se escriben con su abreviatura de ESPN (`LAL`, `BOS`, `GS`, `NY`, `SA`, `UTAH`…) o con su nombre (`Lakers`, `celtics`). Las temporadas se escriben `2025-26` (también vale `2026`, el año en que termina). Por defecto se usa la más reciente; antes de que empiece, `liga`, `estadisticas` y `evaluar` muestran la anterior.

| Comando | Qué muestra |
|---|---|
| `clasificacion [--vista conferencia\|division\|liga]` | Récord, PCT, puntos a favor y en contra por partido, local, visitante, conferencia, racha y últimos 10, con los cortes de playoffs (1-6) y play-in (7-10) |
| `equipo EQUIPO` | Récord y puesto, victorias pitagóricas, Elo y rating neto, jugadores de rotación (y si jugaron el último partido), estadísticas de juego con su puesto en la liga, récords por situación (local, visitante, contra cada conferencia, partidos ajustados, prórrogas, dos días seguidos, playoffs...), últimos partidos y próximos con su probabilidad |
| `h2h A B` | Historial entre dos equipos desde 2001-02, también en playoffs |
| `liga [--solo-regular]` | Ventaja de jugar en casa, partidos ajustados y palizas, prórrogas, efecto de jugar dos días seguidos y qué estadísticas deciden los partidos |
| `ranking` | Power ranking con Elo, rating neto, ataque, defensa y victorias pitagóricas |
| `predecir LOCAL VISITANTE [--neutral] [--linea X] [--total Y]` | Marcador esperado, spread, total, probabilidad de victoria y moneyline justa. Si el partido está en el calendario, tiene en cuenta el descanso de cada equipo |
| `pronosticos [--fecha AAAA-MM-DD] [--dias N]` | Pronósticos del próximo día (o días) con partidos, con las bajas importantes de cada equipo |
| `simular [-n N]` | Simulación Monte Carlo del resto de la temporada, del play-in y de los playoffs: victorias esperadas y probabilidad de playoffs, de top 6, de ser primero, de llegar a la final y de ser campeón |
| `evaluar` | Validación día a día sin datos futuros |
| `estadisticas [--orden COLUMNA]` | Tabla de los 30 equipos con eficiencia ofensiva y defensiva (puntos por 100 posesiones), ritmo y los "cuatro factores" (acierto efectivo, pérdidas, rebote ofensivo y tiros libres) |

Algunos términos:

- **Rating neto**: cuántos puntos es mejor o peor un equipo que la media en campo neutral, ajustado por la dificultad de sus rivales.
- **Posesiones**: cada vez que un equipo tiene el balón. Permiten comparar equipos que juegan a ritmos distintos.
- **eFG%** (acierto efectivo): porcentaje de tiro contando el triple como 1.5 tiros, porque vale más.

## Modelos

**Fútbol**

- **Poisson con corrección Dixon-Coles.** Calcula una fuerza de ataque y una de defensa para cada equipo, ajustadas por la calidad de sus rivales. Tiene en cuenta la ventaja de jugar en casa y da más peso a los partidos recientes (un partido de hace 240 días pesa la mitad). También acerca a la media a los equipos con pocos datos; a los recién ascendidos, hacia un nivel algo inferior a la media.
- **"xG aproximado".** Si los datos traen tiros a puerta, las fuerzas se estiman con una mezcla de goles (30 %) y tiros a puerta convertidos a goles (70 %). Los tiros reflejan mejor el nivel real que los goles, que tienen mucha suerte.
- **Elo de ClubElo.** Si los datos traen el Elo previo al partido, los goles esperados se combinan con los que implica ese Elo.
- Sin tiros ni Elo (ligas no europeas, archivos CSV propios), el modelo usa solo los goles.
- **Elo propio.** Un rating que sube o baja después de cada partido, y más cuanto mayor es la diferencia de goles.

**NFL**

- **Elo** al estilo FiveThirtyEight: tiene en cuenta el margen de victoria y la ventaja de campo, y acerca a los equipos a la media un tercio entre temporadas.
- **Ratings de ofensa y defensa** ajustados por la calidad de los rivales. De ellos salen el SRS, el spread esperado y el total de puntos esperado. La ventaja de campo se estima con los datos.
- **Ajustes previos al partido:**
  - Quarterback titular: −2 puntos si no es el habitual, más la diferencia de rendimiento (EPA por dropback) entre el titular y el habitual, calculada solo con sus partidos anteriores.
  - Semana de descanso: +1 punto.
  - Lesionados: cada jugador del parte oficial de lesionados resta puntos según su posición y cuánto juega normalmente.
  - Playoffs: el margen se amplía ×1.3.
- **Predicción.** Combina Elo (40 %) y ratings (60 %). La probabilidad de victoria sale de una distribución normal de 12.25 puntos de desviación.

**NBA**

- **Elo** al estilo FiveThirtyEight: K=15, ventaja de campo de 70 puntos Elo y regresión de una cuarta parte hacia la media entre temporadas. 28 puntos Elo equivalen a 1 punto de margen.
- **Ratings de ataque y defensa** ajustados por la calidad de los rivales. Un partido de hace 90 días pesa la mitad, y los de la temporada anterior, la mitad más. La ventaja de campo se estima con los datos.
- **Descanso:** el equipo que juega el segundo de dos días seguidos pierde 1.5 puntos.
- **Jugadores disponibles:** cada jugador tiene un valor (la "valoración" Game Score de Hollinger por minuto: puntos, tiros, rebotes, asistencias, robos, tapones, faltas y pérdidas), calculado solo con sus partidos anteriores. Si un equipo juega sin jugadores importantes que suele tener, pierde puntos; si recupera a alguno, los gana. Como no hay parte de lesionados, se supone que juega con los mismos que en su partido anterior (salvo después del verano). Los pronósticos y el informe de equipo muestran esas bajas.
- **Predicción.** Combina Elo (60 %) y ratings (40 %). La probabilidad de victoria sale de una distribución normal de 10 puntos de desviación.
- **Simulación.** Juega muchas veces lo que queda de temporada, el play-in y los playoffs (series al mejor de 7). Como la fuerza real de cada equipo no se conoce con exactitud, en cada simulación varía al azar unos 3 puntos al empezar la temporada y menos a medida que avanza.

**Validación.** El comando `evaluar` predice cada jornada o semana usando solo los partidos anteriores, como si fuera en tiempo real. Después compara el resultado con una referencia ingenua y con las casas de apuestas.

**Mejoras hechas con agentes de IA.** Cuatro agentes probaron mejoras por separado. Ajustaron los parámetros solo con las temporadas de entrenamiento y midieron el resultado en temporadas que no habían visto. Después, otros agentes intentaron refutar cada mejora repitiendo las mediciones y buscando fugas de información:

- **Fútbol** (validación 2023-24 a 2025-26, Premier, LaLiga, Serie A, Bundesliga y Ligue 1; 5.255 partidos): el RPS baja de 0.2012 a 0.1987 y mejora en las cinco ligas. El RPS es la medida habitual para predicciones de 1X2; menos es mejor. Las casas de apuestas están en 0.1934.
- **NFL** (validación 2020–2025, 1.688 partidos): el Brier baja de 0.2228 a 0.2187. Es la medida de error de las probabilidades; menos es mejor, y 0.25 equivale a tirar una moneda. Mejora en 5 de 6 temporadas, y casi toda la ganancia viene del ajuste por quarterback titular.
- **NFL, lesionados:** con el parte oficial de lesionados de cada semana el Brier baja otra vez, de 0.2187 a 0.2175, y los aciertos pasan del 64,4 % al 64,9 %. Cada baja resta puntos según su posición y cuánto juega normalmente (su % de jugadas en sus últimos 4 partidos): un receptor o corredor titular, unos 0,8-0,9 puntos; un linebacker, 0,7; un defensa de la secundaria, 0,4; un liniero ofensivo, 0,3. La línea defensiva y los tight ends no mejoraban la predicción y no cuentan.
- **Descartado:** un modelo NFL basado en EPA por jugada. No mejoraba al actual.
- **NBA** (parámetros ajustados con 2012-13 a 2018-19; validación 2021-22 a 2025-26, 6.605 partidos): el Brier baja de 0.2211, el del Elo de FiveThirtyEight con sus parámetros publicados, a 0.2153, y el acierto del ganador sube del 64.7 % al 66.0 %. El ajuste por jugadores disponibles lo baja a 0.2131 (acierto 66.4 %). Ambos mejoran en las cinco temporadas. Si se supiera exactamente quién juega (con un parte de lesionados), bajaría a 0.2102. La base no tiene líneas de apuestas de la NBA, así que no se compara con el mercado.

Los scripts para reproducir las mediciones están en `experimentos/`: `evaluar_poisson.py`, `futbol_tiros_elo.py`, `nfl_ajuste.py`, `nfl_lesiones.py`, `nba_ajuste.py`, `nba_incertidumbre.py` y `nba_jugadores.py`.

Batir al mercado de apuestas es muy difícil. Úsalo como herramienta de análisis, no como garantía.

## Fuentes de datos

La base de datos combina:

- **[Football-Data.co.uk](https://www.football-data.co.uk/)**: completa la temporada en curso (resultados, estadísticas y cuotas, actualizados dos veces por semana) y rellena las temporadas que faltaban. Las temporadas terminadas se guardan en `datos/football_data/`, así no se descargan cada día y funcionan sin conexión.
- **Football-Data.co.uk y ClubElo**, recopilados por [xgabora/Club-Football-Match-Data-2000-2025](https://github.com/xgabora/Club-Football-Match-Data-2000-2025): partidos de clubes.
- **[openfootball](https://github.com/openfootball/football.json)** (dominio público): temporada en curso.
- **[martj42/international_results](https://github.com/martj42/international_results)** (CC0): selecciones y goleadores.
- **[nflverse](https://github.com/nflverse)**: partidos de la NFL ([nfldata](https://github.com/nflverse/nfldata)) estadísticas de equipo por partido, parte de lesionados y snaps por jugador ([nflverse-data](https://github.com/nflverse/nflverse-data), CC-BY 4.0).
- **[sportsdataverse/hoopR-nba-data](https://github.com/sportsdataverse/hoopR-nba-data)** (datos de ESPN): partidos de la NBA desde 2001-02, calendario de la temporada en curso y estadísticas de equipo por partido. Los traslados y cambios de nombre (New Jersey → Brooklyn, Seattle → Oklahoma City, Hornets → Pelicans) se unifican con el identificador de franquicia de ESPN.

Para analizar un archivo suelto se puede usar `descargar` y `--datos`:

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
  cli.py, comun.py, descargas.py, base.py (base de datos SQLite)
  web/     api.py (datos en JSON) · servidor.py · static/ (index.html, app.js, estilos.css)
  futbol/  datos.py · analisis.py · modelos.py · cli.py
  nfl/     datos.py · equipos.py · analisis.py · estadisticas.py · jugadores.py · modelos.py · cli.py
  nba/     datos.py · equipos.py · analisis.py · estadisticas.py · jugadores.py · modelos.py · cli.py
datos/base_deportiva.sqlite.gz   base de datos completa (comprimida)
datos/                  ejemplos simulados (regenerables con scripts/generar_ejemplos.py)
datos/descargas/        datos reales descargados (ignorados por git)
tests/
```

## Pruebas

```bash
python3 -m unittest discover -s tests -v
```
