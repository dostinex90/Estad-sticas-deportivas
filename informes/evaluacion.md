# Precisión de los modelos

_Actualizado automáticamente: 2026-10-28 10:05 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     99    53.5%   0.564    0.953   0.186
  Referencia (frecuencias)           99    44.4%   0.652    1.077   0.226
  Modelo (partidos c/cuotas)         99    53.5%   0.564    0.953   0.186
  Mercado de apuestas                99    55.6%   0.550    0.931   0.182

  Acierto en más/menos de 2.5 goles: 63.6% (99 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.3%  →  real   0.0%  (7)
  Predicho 10-20 %  media  16.2%  →  real   3.1%  (32)
  Predicho 20-30 %  media  26.1%  →  real  27.4%  (135)
  Predicho 30-40 %  media  35.0%  →  real  36.6%  (41)
  Predicho 40-50 %  media  45.3%  →  real  41.0%  (39)
  Predicho 50-60 %  media  54.3%  →  real  65.4%  (26)
  Predicho 60-70 %  media  63.2%  →  real  42.9%  (7)
  Predicho 70-80 %  media  73.2%  →  real 100.0%  (8)
  Predicho 80-90 %  media  83.7%  →  real 100.0%  (2)
```

## Premier League (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     80    45.0%   0.618    1.029   0.208
  Referencia (frecuencias)           80    38.8%   0.666    1.097   0.230
  Modelo (partidos c/cuotas)         80    45.0%   0.618    1.029   0.208
  Mercado de apuestas                80    47.5%   0.611    1.019   0.204

  Acierto en más/menos de 2.5 goles: 50.0% (80 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   8.3%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.4%  →  real  16.7%  (18)
  Predicho 20-30 %  media  25.9%  →  real  28.7%  (108)
  Predicho 30-40 %  media  34.8%  →  real  31.2%  (48)
  Predicho 40-50 %  media  44.4%  →  real  40.0%  (35)
  Predicho 50-60 %  media  54.3%  →  real  47.1%  (17)
  Predicho 60-70 %  media  63.8%  →  real  75.0%  (8)
  Predicho 70-80 %  media  75.1%  →  real 100.0%  (3)
```

## Serie A (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     80    60.0%   0.545    0.930   0.197
  Referencia (frecuencias)           80    47.5%   0.635    1.049   0.242
  Modelo (partidos c/cuotas)         80    60.0%   0.545    0.930   0.197
  Mercado de apuestas                80    61.2%   0.523    0.900   0.188

  Acierto en más/menos de 2.5 goles: 46.2% (80 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.4%  →  real   0.0%  (2)
  Predicho 10-20 %  media  15.9%  →  real  12.0%  (25)
  Predicho 20-30 %  media  26.5%  →  real  17.0%  (100)
  Predicho 30-40 %  media  33.6%  →  real  35.3%  (51)
  Predicho 40-50 %  media  44.7%  →  real  56.7%  (30)
  Predicho 50-60 %  media  55.2%  →  real  72.7%  (22)
  Predicho 60-70 %  media  64.1%  →  real  87.5%  (8)
  Predicho 70-80 %  media  75.4%  →  real 100.0%  (2)
```

## Bundesliga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     63    52.4%   0.586    0.980   0.210
  Referencia (frecuencias)           63    50.8%   0.625    1.038   0.230
  Modelo (partidos c/cuotas)         63    52.4%   0.586    0.980   0.210
  Mercado de apuestas                63    55.6%   0.592    0.989   0.213

  Acierto en más/menos de 2.5 goles: 71.4% (63 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.7%  →  real   0.0%  (4)
  Predicho 10-20 %  media  15.6%  →  real  18.8%  (32)
  Predicho 20-30 %  media  23.9%  →  real  25.0%  (72)
  Predicho 30-40 %  media  35.5%  →  real  33.3%  (27)
  Predicho 40-50 %  media  45.3%  →  real  47.1%  (17)
  Predicho 50-60 %  media  55.2%  →  real  44.4%  (18)
  Predicho 60-70 %  media  64.8%  →  real  70.0%  (10)
  Predicho 70-80 %  media  73.3%  →  real  85.7%  (7)
  Predicho 80-90 %  media  83.5%  →  real  50.0%  (2)
```

## Ligue 1 (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     72    52.8%   0.590    0.990   0.199
  Referencia (frecuencias)           72    44.4%   0.651    1.077   0.228
  Modelo (partidos c/cuotas)         72    52.8%   0.590    0.990   0.199
  Mercado de apuestas                72    54.2%   0.587    0.986   0.198

  Acierto en más/menos de 2.5 goles: 59.7% (72 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.0%  →  real   0.0%  (1)
  Predicho 10-20 %  media  17.4%  →  real  15.0%  (20)
  Predicho 20-30 %  media  25.8%  →  real  24.7%  (97)
  Predicho 30-40 %  media  34.5%  →  real  23.7%  (38)
  Predicho 40-50 %  media  44.1%  →  real  59.4%  (32)
  Predicho 50-60 %  media  55.7%  →  real  56.5%  (23)
  Predicho 60-70 %  media  64.9%  →  real  75.0%  (4)
  Predicho 80-90 %  media  81.1%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 106
  Acierto ganador (combinado)        █████████████░░░░░░░  64.2%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  58.5%
  Acierto ganador (solo ratings)     ███████████░░░░░░░░░  53.8%
  Acierto del favorito del mercado   █████████████░░░░░░░  64.2%
  Brier score: 0.224 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.639
  Error medio del margen: 9.47 pts · del total: 11.48 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.47 pts vs mercado 9.46 pts
  Acierto contra el spread           ███████████░░░░░░░░░  56.0%  (100)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  53.8%  (26)
  Error medio del total: modelo 11.48 vs mercado 10.56
  Acierto over/under                 █████████░░░░░░░░░░░  43.4%  (106)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```

## NBA (temporada en curso o, si no ha empezado, la anterior)

```
Validación del modelo en 2026-27 (día a día, sin datos futuros)
═══════════════════════════════════════════════════════════════
  Partidos evaluados: 52
  Acierto ganador (combinado)        ████████████░░░░░░░░  61.5%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  57.7%
  Acierto ganador (solo ratings)     ████████████░░░░░░░░  59.6%
  Gana siempre el local              ██████████░░░░░░░░░░  50.0%
  Brier score: 0.221 (0.25 = lanzar una moneda; menor es mejor) · solo Elo 0.230 · log-loss 0.630
  Error medio del margen: 11.79 pts · del total: 14.37 pts
  La base no tiene líneas de apuestas de la NBA, así que no hay comparación con el mercado.
```
