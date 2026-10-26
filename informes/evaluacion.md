# Precisión de los modelos

_Actualizado automáticamente: 2026-10-26 10:02 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     89    52.8%   0.559    0.947   0.183
  Referencia (frecuencias)           89    43.8%   0.655    1.082   0.226
  Modelo (partidos c/cuotas)         89    52.8%   0.559    0.947   0.183
  Mercado de apuestas                89    55.1%   0.548    0.929   0.179

  Acierto en más/menos de 2.5 goles: 64.0% (89 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.3%  →  real   0.0%  (7)
  Predicho 10-20 %  media  16.3%  →  real   3.4%  (29)
  Predicho 20-30 %  media  26.2%  →  real  27.3%  (121)
  Predicho 30-40 %  media  35.0%  →  real  38.9%  (36)
  Predicho 40-50 %  media  45.2%  →  real  36.1%  (36)
  Predicho 50-60 %  media  54.5%  →  real  69.6%  (23)
  Predicho 60-70 %  media  63.6%  →  real  50.0%  (6)
  Predicho 70-80 %  media  73.7%  →  real 100.0%  (7)
  Predicho 80-90 %  media  83.7%  →  real 100.0%  (2)
```

## Premier League (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     70    47.1%   0.610    1.018   0.204
  Referencia (frecuencias)           70    40.0%   0.663    1.093   0.229
  Modelo (partidos c/cuotas)         70    47.1%   0.610    1.018   0.204
  Mercado de apuestas                70    48.6%   0.599    1.003   0.198

  Acierto en más/menos de 2.5 goles: 51.4% (70 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   8.3%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.5%  →  real  17.6%  (17)
  Predicho 20-30 %  media  25.9%  →  real  27.7%  (94)
  Predicho 30-40 %  media  34.9%  →  real  31.7%  (41)
  Predicho 40-50 %  media  44.4%  →  real  41.4%  (29)
  Predicho 50-60 %  media  54.5%  →  real  50.0%  (16)
  Predicho 60-70 %  media  63.8%  →  real  71.4%  (7)
  Predicho 70-80 %  media  75.1%  →  real 100.0%  (3)
```

## Serie A (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     70    57.1%   0.557    0.948   0.204
  Referencia (frecuencias)           70    47.1%   0.635    1.049   0.243
  Modelo (partidos c/cuotas)         70    57.1%   0.557    0.948   0.204
  Mercado de apuestas                70    58.6%   0.539    0.922   0.197

  Acierto en más/menos de 2.5 goles: 42.9% (70 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.4%  →  real   0.0%  (2)
  Predicho 10-20 %  media  16.0%  →  real  14.3%  (21)
  Predicho 20-30 %  media  26.6%  →  real  18.4%  (87)
  Predicho 30-40 %  media  33.7%  →  real  36.2%  (47)
  Predicho 40-50 %  media  44.8%  →  real  50.0%  (26)
  Predicho 50-60 %  media  55.0%  →  real  72.2%  (18)
  Predicho 60-70 %  media  63.6%  →  real  85.7%  (7)
  Predicho 70-80 %  media  75.4%  →  real 100.0%  (2)
```

## Bundesliga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     54    55.6%   0.579    0.968   0.206
  Referencia (frecuencias)           54    51.9%   0.622    1.034   0.229
  Modelo (partidos c/cuotas)         54    55.6%   0.579    0.968   0.206
  Mercado de apuestas                54    57.4%   0.586    0.978   0.210

  Acierto en más/menos de 2.5 goles: 74.1% (54 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.7%  →  real   0.0%  (4)
  Predicho 10-20 %  media  15.4%  →  real  20.0%  (25)
  Predicho 20-30 %  media  24.0%  →  real  23.8%  (63)
  Predicho 30-40 %  media  35.2%  →  real  30.4%  (23)
  Predicho 40-50 %  media  45.3%  →  real  47.1%  (17)
  Predicho 50-60 %  media  55.9%  →  real  53.3%  (15)
  Predicho 60-70 %  media  64.7%  →  real  71.4%  (7)
  Predicho 70-80 %  media  73.7%  →  real  83.3%  (6)
  Predicho 80-90 %  media  83.5%  →  real  50.0%  (2)
```

## Ligue 1 (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     63    54.0%   0.588    0.988   0.204
  Referencia (frecuencias)           63    44.4%   0.649    1.072   0.233
  Modelo (partidos c/cuotas)         63    54.0%   0.588    0.988   0.204
  Mercado de apuestas                63    55.6%   0.585    0.983   0.203

  Acierto en más/menos de 2.5 goles: 60.3% (63 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.0%  →  real   0.0%  (1)
  Predicho 10-20 %  media  17.3%  →  real  17.6%  (17)
  Predicho 20-30 %  media  25.9%  →  real  22.6%  (84)
  Predicho 30-40 %  media  34.5%  →  real  25.7%  (35)
  Predicho 40-50 %  media  44.1%  →  real  62.1%  (29)
  Predicho 50-60 %  media  55.3%  →  real  55.6%  (18)
  Predicho 60-70 %  media  64.9%  →  real  75.0%  (4)
  Predicho 80-90 %  media  81.1%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 105
  Acierto ganador (combinado)        █████████████░░░░░░░  64.8%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  59.0%
  Acierto ganador (solo ratings)     ███████████░░░░░░░░░  54.3%
  Acierto del favorito del mercado   █████████████░░░░░░░  63.8%
  Brier score: 0.223 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.637
  Error medio del margen: 9.38 pts · del total: 11.48 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.38 pts vs mercado 9.43 pts
  Acierto contra el spread           ███████████░░░░░░░░░  56.6%  (99)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  56.0%  (25)
  Error medio del total: modelo 11.48 vs mercado 10.51
  Acierto over/under                 █████████░░░░░░░░░░░  42.9%  (105)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```

## NBA (temporada en curso o, si no ha empezado, la anterior)

```
Validación del modelo en 2026-27 (día a día, sin datos futuros)
═══════════════════════════════════════════════════════════════
  Partidos evaluados: 36
  Acierto ganador (combinado)        ████████████░░░░░░░░  58.3%
  Acierto ganador (solo Elo)         ███████████░░░░░░░░░  55.6%
  Acierto ganador (solo ratings)     ███████████░░░░░░░░░  55.6%
  Gana siempre el local              ██████████░░░░░░░░░░  50.0%
  Brier score: 0.211 (0.25 = lanzar una moneda; menor es mejor) · solo Elo 0.230 · log-loss 0.604
  Error medio del margen: 11.81 pts · del total: 14.23 pts
  La base no tiene líneas de apuestas de la NBA, así que no hay comparación con el mercado.
```
