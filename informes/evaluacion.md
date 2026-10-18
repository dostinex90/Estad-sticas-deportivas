# Precisión de los modelos

_Actualizado automáticamente: 2026-10-18 22:55 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     69    50.7%   0.567    0.958   0.194
  Referencia (frecuencias)           69    44.9%   0.649    1.072   0.231
  Modelo (partidos c/cuotas)         31    54.8%   0.546    0.927   0.181
  Mercado de apuestas                31    58.1%   0.534    0.909   0.176

  Acierto en más/menos de 2.5 goles: 68.1% (69 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.1%  →  real   0.0%  (5)
  Predicho 10-20 %  media  16.2%  →  real   4.3%  (23)
  Predicho 20-30 %  media  26.1%  →  real  26.0%  (96)
  Predicho 30-40 %  media  35.1%  →  real  50.0%  (24)
  Predicho 40-50 %  media  45.9%  →  real  30.0%  (30)
  Predicho 50-60 %  media  54.3%  →  real  70.6%  (17)
  Predicho 60-70 %  media  63.3%  →  real  60.0%  (5)
  Predicho 70-80 %  media  72.9%  →  real 100.0%  (5)
  Predicho 80-90 %  media  83.4%  →  real 100.0%  (2)
```

## Premier League (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     50    44.0%   0.637    1.058   0.209
  Referencia (frecuencias)           50    36.0%   0.674    1.110   0.227
  Modelo (partidos c/cuotas)         20    50.0%   0.604    1.011   0.221
  Mercado de apuestas                20    55.0%   0.575    0.976   0.208

  Acierto en más/menos de 2.5 goles: 48.0% (50 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.8%  →  real   0.0%  (2)
  Predicho 10-20 %  media  16.0%  →  real  23.1%  (13)
  Predicho 20-30 %  media  25.8%  →  real  30.9%  (68)
  Predicho 30-40 %  media  34.7%  →  real  26.9%  (26)
  Predicho 40-50 %  media  44.6%  →  real  40.9%  (22)
  Predicho 50-60 %  media  54.1%  →  real  40.0%  (10)
  Predicho 60-70 %  media  63.9%  →  real  57.1%  (7)
  Predicho 70-80 %  media  75.8%  →  real 100.0%  (2)
```

## Serie A (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     50    60.0%   0.551    0.938   0.199
  Referencia (frecuencias)           50    44.0%   0.640    1.057   0.243
  Modelo (partidos c/cuotas)         20    70.0%   0.462    0.812   0.183
  Mercado de apuestas                20    70.0%   0.443    0.787   0.177

  Acierto en más/menos de 2.5 goles: 48.0% (50 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.5%  →  real   0.0%  (1)
  Predicho 10-20 %  media  16.2%  →  real  21.4%  (14)
  Predicho 20-30 %  media  26.8%  →  real  16.7%  (66)
  Predicho 30-40 %  media  33.3%  →  real  35.7%  (28)
  Predicho 40-50 %  media  44.2%  →  real  50.0%  (22)
  Predicho 50-60 %  media  54.5%  →  real  71.4%  (14)
  Predicho 60-70 %  media  64.2%  →  real 100.0%  (4)
  Predicho 70-80 %  media  77.8%  →  real 100.0%  (1)
```

## Bundesliga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     36    50.0%   0.575    0.967   0.209
  Referencia (frecuencias)           36    52.8%   0.619    1.029   0.230
  Modelo (partidos c/cuotas)          9    55.6%   0.524    0.900   0.180
  Mercado de apuestas                 9    55.6%   0.532    0.905   0.185

  Acierto en más/menos de 2.5 goles: 77.8% (36 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.5%  →  real   0.0%  (4)
  Predicho 10-20 %  media  15.2%  →  real  12.5%  (16)
  Predicho 20-30 %  media  24.4%  →  real  29.3%  (41)
  Predicho 30-40 %  media  35.2%  →  real  31.2%  (16)
  Predicho 40-50 %  media  45.6%  →  real  38.5%  (13)
  Predicho 50-60 %  media  55.0%  →  real  42.9%  (7)
  Predicho 60-70 %  media  64.4%  →  real  80.0%  (5)
  Predicho 70-80 %  media  74.7%  →  real 100.0%  (4)
  Predicho 80-90 %  media  83.5%  →  real  50.0%  (2)
```

## Ligue 1 (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     45    48.9%   0.636    1.057   0.216
  Referencia (frecuencias)           45    40.0%   0.668    1.101   0.230
  Modelo (partidos c/cuotas)         19    42.1%   0.639    1.062   0.199
  Mercado de apuestas                19    47.4%   0.649    1.068   0.201

  Acierto en más/menos de 2.5 goles: 55.6% (45 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho 10-20 %  media  17.4%  →  real  25.0%  (12)
  Predicho 20-30 %  media  26.2%  →  real  28.3%  (60)
  Predicho 30-40 %  media  34.7%  →  real  18.5%  (27)
  Predicho 40-50 %  media  44.4%  →  real  60.9%  (23)
  Predicho 50-60 %  media  56.2%  →  real  40.0%  (10)
  Predicho 60-70 %  media  64.4%  →  real  50.0%  (2)
  Predicho 70-80 %  media  70.9%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 87
  Acierto ganador (combinado)        ████████████░░░░░░░░  62.1%
  Acierto ganador (solo Elo)         ███████████░░░░░░░░░  57.5%
  Acierto ganador (solo ratings)     ███████████░░░░░░░░░  52.9%
  Acierto del favorito del mercado   █████████████░░░░░░░  63.2%
  Brier score: 0.224 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.639
  Error medio del margen: 9.45 pts · del total: 11.53 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.45 pts vs mercado 9.47 pts
  Acierto contra el spread           ███████████░░░░░░░░░  55.6%  (81)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  54.2%  (24)
  Error medio del total: modelo 11.53 vs mercado 10.39
  Acierto over/under                 ████████░░░░░░░░░░░░  39.1%  (87)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```
