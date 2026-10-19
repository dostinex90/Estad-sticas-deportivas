# CLAUDE.md

Guía para Claude (y personas) que trabajen en este repositorio. El README.md es el manual de uso; esto resume cómo está hecho y qué cuidar.

## El proyecto

Programa en Python de análisis y predicción de **fútbol** (clubes y selecciones), **NFL** y **NBA**:
- clasificaciones, informes de equipo, resúmenes de liga y cara a cara;
- rankings y predicciones;
- simulación de playoffs NFL y NBA;
- web publicada en https://dostinex90.github.io/Estad-sticas-deportivas/

Escribe todo en **español**: código, comentarios, mensajes, documentación y commits. El dueño no es programador: explícale las cosas en lenguaje sencillo.

- **Rama principal:** `ccr-672140af-qwksr9`. Es la rama por defecto del repositorio, que es público.
- **Dependencias:** solo biblioteca estándar de Python 3.9+. No añadas dependencias.
- **Pruebas:** `python3 -m unittest discover -s tests`. Algunas usan la base de datos real y tardan unos segundos.

## Estructura

```
analisis_deportivo/
  cli.py          punto de entrada: python3 -m analisis_deportivo {futbol|nfl|nba|web|recopilar|base|descargar}
  base.py         construye la base SQLite desde todas las fuentes (comando recopilar) y la abre
  comun.py        utilidades compartidas
  descargas.py    descarga de archivos sueltos
  futbol/         datos.py · analisis.py · modelos.py (Poisson + Dixon-Coles, tiros a puerta, Elo) · cli.py
  nfl/            datos.py · equipos.py · analisis.py · estadisticas.py · modelos.py (Elo + ratings + ajuste por QB) · cli.py
  nba/            datos.py · equipos.py · analisis.py · estadisticas.py · jugadores.py · modelos.py (Elo + ratings + descanso + jugadores) · cli.py (solo con la base)
  web/            api.py (JSON) · servidor.py (http.server) · static/ (index.html, app.js, estilos.css; JS sin dependencias)
scripts/          generar_informes.py · generar_sitio.py (web estática) · verificar_datos.py · generar_ejemplos.py
experimentos/     scripts para medir modelos: evaluar_poisson.py, futbol_tiros_elo.py, nfl_ajuste.py, nba_ajuste.py…
datos/            base_deportiva.sqlite.gz (copia de la base), football_data/ (caché de football-data.co.uk), ejemplos simulados
informes/         informes Markdown regenerados a diario por GitHub Actions (no editar a mano)
```

La carga de una competición de fútbol está en un solo sitio, `futbol/datos.py::cargar_para_analisis`, y la comparten el CLI y la web. Si añades una vista nueva:
1. Añade la función de datos en `web/api.py` y regístrala en `RUTAS`.
2. Añade su ruta estática en `rutaEstatica()` de `app.js`.
3. Genérala en `scripts/generar_sitio.py`.

## Datos

La base SQLite se construye con `python3 -m analisis_deportivo recopilar`.

**Tablas:**
- `futbol_partidos`
- `futbol_selecciones`
- `futbol_goleadores_selecciones`
- `nfl_partidos`
- `nfl_estadisticas_equipo`
- `nba_partidos` (temporada = año en que termina: 2026 es la 2025-26; tipo REG, COPA, PLAYIN o PO)
- `nba_estadisticas_equipo`
- `nba_jugadores_partido` (desde 2011-12; id y jugador como enteros para ocupar menos) y `nba_jugadores` (nombres)
- `fuentes`

**Fuentes de fútbol, en orden de carga:**
1. **xgabora/Club-Football-Match-Data** (Football-Data.co.uk + ClubElo): 38 ligas desde 2000.
2. **football-data.co.uk:** temporada en curso, temporadas que faltaban y ligas "new".
   - Las temporadas terminadas se guardan en `datos/football_data/`.
   - Desde el entorno de Claude en la nube este dominio está **bloqueado**; desde GitHub Actions funciona.
3. **openfootball:** calendario pendiente de la temporada en curso.

**Otras fuentes:**
- Selecciones: martj42/international_results.
- NFL: nflverse (`games.csv` y estadísticas de equipo por partido).
- NBA: sportsdataverse-data (releases `espn_nba_schedules` y `espn_nba_team_boxscores`, datos de ESPN). Los equipos se identifican por el id de franquicia de ESPN (`nba/equipos.py::POR_ID`), así NJ/BKN, SEA/OKC y NOH/NO son el mismo. Se descartan pretemporada, partidos de las estrellas y aplazados. La final de la NBA Cup (COPA) no cuenta en la clasificación. 2019-20 desde el 30 de julio (burbuja) se marca como campo neutral.

**Problemas conocidos y cómo se resuelven** (no los rompas):
- **Nombres de equipo distintos entre fuentes** ("Nott'm Forest" / "Nottm Forest", "Preußen Münster" / "Preussen Munster", "Argentinos Jrs" / "Argentinos Juniors"). Hay tres mecanismos:
  - `_clave_nombre` y `_unificar_nombres` unifican las variantes. Se ejecuta antes y después de mezclar fuentes.
  - `_mapear_nombres` aprende equivalencias de los partidos que coinciden en fecha y marcador.
  - `_solo_posteriores` se usa en las ligas "new".
- **Emparejar partidos entre fuentes:** se hace por (competición, temporada, local, visitante). Excepción: en `CRUCES_REPETIDOS` (Escocia, Bélgica, Grecia y ligas "new" hay más de dos cruces o playoffs) se empareja por fecha.
- **Temporadas:** las europeas van de julio a junio. En 2020 el corte es el 15 de agosto por la pandemia. Las ligas de calendario anual (ARG, BRA, USA…) usan el año.
- **Temporadas incompletas reales:** Ligue 1 y Eredivisie 2019-20 (canceladas), NFL 2022 (271 partidos) y NBA 2011-12 (990), 2012-13 (1229), 2019-20 (1059) y 2020-21 (1080).
- **NBA:** la fuente tiene un PHX-GS de 2019-20 con fecha errónea; `verificar_datos.py` solo da error por dos partidos el mismo día en las dos últimas temporadas.
- **La temporada en curso puede ir días por detrás:** los pronósticos omiten los partidos pasados sin resultado.

`scripts/verificar_datos.py` comprueba:
- duplicados;
- equipos con dos partidos el mismo día;
- resultados con fecha futura;
- temporadas incompletas.

La actualización diaria **no publica** si encuentra errores. Si cambias `base.py`, ejecútalo siempre después de `recopilar`.

## Modelos y cómo mejorarlos

- **Fútbol, `ModeloPoisson`:**
  - Fuerzas de ataque y defensa ajustadas por rival.
  - Decaimiento temporal con vida media de 240 días.
  - Previa de 4 y equipos ascendidos hacia (0.85, 1.2).
  - Dixon-Coles con rho fijo de −0.08.
  - Mezcla del 70 % de tiros a puerta ("xG aproximado") y mezcla del 70 % con el Elo de ClubElo.
  - Se entrena con la temporada actual más la anterior.
  - **Validación 2023-26 en 5 ligas: RPS 0.1987.** Mercado: 0.1934. Línea base original: 0.2012.
- **NFL:**
  - Elo con K=20, ventaja de campo 84, regresión de 1/3 y mov=3.
  - `RatingsNFL`: ofensa y defensa ajustadas por rival.
  - Mezcla: 40 % Elo, 60 % ratings, con desviación de 12.25.
  - Ajustes previos al partido: QB titular, semana de descanso (bye) y playoffs ×1.3.
  - **Validación 2020-2025: Brier 0.2187.** Línea base original: 0.2228.
  - Un modelo basado en EPA por jugada se probó y no mejoraba.
- **NBA:**
  - Elo con K=15, ventaja de campo 70, regresión de 1/4 y multiplicador por margen de FiveThirtyEight.
  - `RatingsNBA`: ataque y defensa ajustados por rival, vida media de 90 días y ×0.5 por temporada anterior.
  - Mezcla: 60 % Elo, 40 % ratings, desviación de 10; −1.5 puntos por jugar dos días seguidos.
  - Jugadores disponibles (`nba/jugadores.py`): Game Score por minuto de cada jugador; ajuste = 0.2 × (valor de la plantilla de hoy − media de sus últimos 40 partidos), con jugadores de rotación (20+ minutos). Sin parte de lesionados: se supone la plantilla del partido anterior, salvo si fue hace más de 60 días. No se aplica en la simulación de la temporada (las bajas son temporales).
  - Simulación con incertidumbre de la fuerza de 3 puntos × √(fracción pendiente), medida en `experimentos/nba_incertidumbre.py`.
  - **Validación 2021-22 a 2025-26: Brier 0.2131** (0.2153 sin jugadores; 0.2102 si se supiera quién juega). Línea base (Elo de FiveThirtyEight): 0.2211. Sin líneas de apuestas en la base. Mediciones en `experimentos/nba_ajuste.py` y `nba_jugadores.py`.
  - Posible mejora: un parte de lesionados (ESPN lo tiene, pero su dominio está bloqueado desde el entorno de Claude en la nube; no se ha probado desde GitHub Actions).

**Reglas al cambiar un modelo** (las siguen también los agentes de la revisión semanal):
1. Ajusta parámetros **solo con temporadas de entrenamiento**:
   - fútbol: 2018-19 a 2022-23;
   - NFL: 2012 a 2019;
   - NBA: 2012-13 a 2018-19.
2. Mide en temporadas de **validación** no usadas para ajustar:
   - fútbol: 2023-24 a 2025-26 en E0, SP1, I1, D1 y F1;
   - NFL: 2020 a 2025;
   - NBA: 2021-22 a 2025-26 (2019-20 y 2020-21 no se usan para ajustar ni para validar).
3. **Sin fugas de información:** cada predicción usa solo datos anteriores al partido.
4. **Nunca uses cuotas ni líneas de apuestas como entrada;** solo para comparar.
5. Mide siempre la línea base con el mismo procedimiento y deja el script de medición en `experimentos/`.
6. Si no mejora en validación, descártalo.

## Automatización

- **`.github/workflows/actualizacion-diaria.yml`**, a las 09:17 UTC:
  1. `recopilar`.
  2. Guarda la caché de football-data.
  3. `verificar_datos.py`.
  4. Pruebas.
  5. Informes, con commit del bot.
  6. Web estática y despliegue en GitHub Pages.

  Usa `git pull --rebase --autostash` porque `datos/base_deportiva.sqlite.gz` se regenera y no se sube a diario.
- **`.github/workflows/pruebas.yml`:** pruebas en cada push.
- **Revisión semanal en la nube:** tarea programada de Claude, los lunes a las 09:47 UTC. Lanza un workflow de agentes que buscan mejoras de los modelos y las proponen en una rama `revision-semanal-AAAA-MM-DD` con un pull request.
  - **Nunca** hace push directo a la rama principal ni fusiona.
  - Puede no tener permisos de GitHub; en ese caso deja los cambios descritos en su resumen.
- **El bot de GitHub añade commits a la rama principal a diario:** haz `git pull` antes de trabajar.

## Convenciones

- **Commits** en español, con título corto y cuerpo que explique el porqué.
- **No subas** `datos/base_deportiva.sqlite` (está en `.gitignore`), `sitio/` ni `datos/descargas/`.
- **Antes de subir cambios:**
  - pasa las pruebas;
  - si tocaste datos, ejecuta `verificar_datos.py`;
  - si tocaste la web, comprueba las vistas, por ejemplo con Chromium sin interfaz sobre `python3 -m analisis_deportivo web --no-abrir`.
- **Cuida el consumo:** el dueño quiere controlar el gasto de uso de Claude. Lo diario va en GitHub Actions, sin IA, y los agentes solo para mejoras de modelos.
