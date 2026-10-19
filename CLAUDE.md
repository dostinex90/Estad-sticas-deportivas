# CLAUDE.md

Guía para Claude (y personas) que trabajen en este repositorio. El README.md es el manual de uso; esto resume cómo está hecho y qué cuidar.

## El proyecto

Programa en Python de análisis y predicción de **fútbol** (clubes y selecciones) y **NFL**:
- clasificaciones, informes de equipo, resúmenes de liga y cara a cara;
- rankings y predicciones;
- simulación de playoffs NFL;
- web publicada en https://dostinex90.github.io/Estad-sticas-deportivas/

Escribe todo en **español**: código, comentarios, mensajes, documentación y commits. El dueño no es programador: explícale las cosas en lenguaje sencillo.

- **Rama principal:** `ccr-672140af-qwksr9`. Es la rama por defecto del repositorio, que es público.
- **Dependencias:** solo biblioteca estándar de Python 3.9+. No añadas dependencias.
- **Pruebas:** `python3 -m unittest discover -s tests`. Algunas usan la base de datos real y tardan unos segundos.

## Estructura

```
analisis_deportivo/
  cli.py          punto de entrada: python3 -m analisis_deportivo {futbol|nfl|web|recopilar|base|descargar}
  base.py         construye la base SQLite desde todas las fuentes (comando recopilar) y la abre
  comun.py        utilidades compartidas
  descargas.py    descarga de archivos sueltos
  futbol/         datos.py · analisis.py · modelos.py (Poisson + Dixon-Coles, tiros a puerta, Elo) · cli.py
  nfl/            datos.py · equipos.py · analisis.py · estadisticas.py · modelos.py (Elo + ratings + ajuste por QB) · cli.py
  web/            api.py (JSON) · servidor.py (http.server) · static/ (index.html, app.js, estilos.css; JS sin dependencias)
scripts/          generar_informes.py · generar_sitio.py (web estática) · verificar_datos.py · generar_ejemplos.py
experimentos/     scripts para medir modelos: evaluar_poisson.py, futbol_tiros_elo.py, nfl_ajuste.py…
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

**Problemas conocidos y cómo se resuelven** (no los rompas):
- **Nombres de equipo distintos entre fuentes** ("Nott'm Forest" / "Nottm Forest", "Preußen Münster" / "Preussen Munster", "Argentinos Jrs" / "Argentinos Juniors"). Hay tres mecanismos:
  - `_clave_nombre` y `_unificar_nombres` unifican las variantes. Se ejecuta antes y después de mezclar fuentes.
  - `_mapear_nombres` aprende equivalencias de los partidos que coinciden en fecha y marcador.
  - `_solo_posteriores` se usa en las ligas "new".
- **Emparejar partidos entre fuentes:** se hace por (competición, temporada, local, visitante). Excepción: en `CRUCES_REPETIDOS` (Escocia, Bélgica, Grecia y ligas "new" hay más de dos cruces o playoffs) se empareja por fecha.
- **Fechas con día y mes intercambiados:** xgabora trae así las 16 ligas "new" (MLS, Brasil, Suecia...) en los días 1 a 12 de cada mes. `fechas_intercambiadas` lo detecta por liga (con esas fechas los equipos juegan a menudo dos días seguidos) y `_clubes` las gira. `verificar_datos.py` da error si vuelve a aparecer.
- **Clubes con dos nombres muy distintos** (cambio de nombre a mitad de temporada): `ALIAS_CLUBES` en `base.py`.
- **football-data.co.uk:** solo un 404 marca una temporada como inexistente (archivo `.none` en la caché); otros errores son pasajeros y se reintenta al día siguiente.
- **Temporadas:** las europeas van de julio a junio. En 2020 el corte es el 15 de agosto por la pandemia. Las ligas de calendario anual (ARG, BRA, USA…) usan el año.
- **Temporadas incompletas reales:** Ligue 1 y Eredivisie 2019-20 (canceladas) y NFL 2022 (271 partidos).
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

**Reglas al cambiar un modelo** (las siguen también los agentes de la revisión semanal):
1. Ajusta parámetros **solo con temporadas de entrenamiento**:
   - fútbol: 2018-19 a 2022-23;
   - NFL: 2012 a 2019.
2. Mide en temporadas de **validación** no usadas para ajustar:
   - fútbol: 2023-24 a 2025-26 en E0, SP1, I1, D1 y F1;
   - NFL: 2020 a 2025.
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
