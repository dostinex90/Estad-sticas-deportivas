# Precisión de los modelos

_Actualizado automáticamente: 2026-10-19 02:56 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     78    51.3%   0.559    0.947   0.185
  Referencia (frecuencias)           78    44.9%   0.650    1.075   0.226
  Modelo (partidos c/cuotas)         78    51.3%   0.559    0.947   0.185
  Mercado de apuestas                78    55.1%   0.547    0.927   0.182

  Acierto en más/menos de 2.5 goles: 67.9% (78 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.0%  →  real   0.0%  (6)
  Predicho 10-20 %  media  16.3%  →  real   3.7%  (27)
  Predicho 20-30 %  media  26.1%  →  real  27.6%  (105)
  Predicho 30-40 %  media  35.2%  →  real  40.6%  (32)
  Predicho 40-50 %  media  45.6%  →  real  31.0%  (29)
  Predicho 50-60 %  media  54.5%  →  real  68.2%  (22)
  Predicho 60-70 %  media  63.5%  →  real  60.0%  (5)
  Predicho 70-80 %  media  73.7%  →  real 100.0%  (6)
  Predicho 80-90 %  media  83.7%  →  real 100.0%  (2)
```

## Premier League (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     60    45.0%   0.636    1.054   0.209
  Referencia (frecuencias)           60    38.3%   0.668    1.101   0.225
  Modelo (partidos c/cuotas)         60    45.0%   0.636    1.054   0.209
  Mercado de apuestas                60    45.0%   0.630    1.045   0.205

  Acierto en más/menos de 2.5 goles: 51.7% (60 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.9%  →  real   0.0%  (2)
  Predicho 10-20 %  media  16.5%  →  real  20.0%  (15)
  Predicho 20-30 %  media  26.0%  →  real  30.9%  (81)
  Predicho 30-40 %  media  34.7%  →  real  29.4%  (34)
  Predicho 40-50 %  media  44.4%  →  real  40.7%  (27)
  Predicho 50-60 %  media  54.4%  →  real  33.3%  (12)
  Predicho 60-70 %  media  63.8%  →  real  71.4%  (7)
  Predicho 70-80 %  media  75.7%  →  real 100.0%  (2)
```

## Serie A (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     60    58.3%   0.541    0.923   0.190
  Referencia (frecuencias)           60    46.7%   0.642    1.060   0.239
  Modelo (partidos c/cuotas)         60    58.3%   0.541    0.923   0.190
  Mercado de apuestas                60    56.7%   0.531    0.910   0.187

  Acierto en más/menos de 2.5 goles: 46.7% (60 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.4%  →  real   0.0%  (2)
  Predicho 10-20 %  media  16.1%  →  real  11.1%  (18)
  Predicho 20-30 %  media  26.6%  →  real  18.4%  (76)
  Predicho 30-40 %  media  33.6%  →  real  35.1%  (37)
  Predicho 40-50 %  media  44.6%  →  real  52.2%  (23)
  Predicho 50-60 %  media  54.5%  →  real  68.8%  (16)
  Predicho 60-70 %  media  63.7%  →  real 100.0%  (6)
  Predicho 70-80 %  media  75.4%  →  real 100.0%  (2)
```

## Bundesliga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     45    55.6%   0.583    0.975   0.209
  Referencia (frecuencias)           45    51.1%   0.624    1.036   0.231
  Modelo (partidos c/cuotas)         45    55.6%   0.583    0.975   0.209
  Mercado de apuestas                45    55.6%   0.590    0.984   0.212

  Acierto en más/menos de 2.5 goles: 77.8% (45 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.7%  →  real   0.0%  (4)
  Predicho 10-20 %  media  15.4%  →  real  22.7%  (22)
  Predicho 20-30 %  media  24.1%  →  real  23.5%  (51)
  Predicho 30-40 %  media  34.9%  →  real  27.8%  (18)
  Predicho 40-50 %  media  45.2%  →  real  46.7%  (15)
  Predicho 50-60 %  media  55.5%  →  real  54.5%  (11)
  Predicho 60-70 %  media  64.7%  →  real  71.4%  (7)
  Predicho 70-80 %  media  74.0%  →  real  80.0%  (5)
  Predicho 80-90 %  media  83.5%  →  real  50.0%  (2)
```

## Ligue 1 (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     54    53.7%   0.599    1.005   0.205
  Referencia (frecuencias)           54    46.3%   0.645    1.068   0.226
  Modelo (partidos c/cuotas)         54    53.7%   0.599    1.005   0.205
  Mercado de apuestas                54    53.7%   0.595    0.997   0.203

  Acierto en más/menos de 2.5 goles: 59.3% (54 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.0%  →  real   0.0%  (1)
  Predicho 10-20 %  media  17.0%  →  real  21.4%  (14)
  Predicho 20-30 %  media  26.0%  →  real  24.7%  (73)
  Predicho 30-40 %  media  34.5%  →  real  20.7%  (29)
  Predicho 40-50 %  media  44.1%  →  real  61.5%  (26)
  Predicho 50-60 %  media  55.2%  →  real  50.0%  (14)
  Predicho 60-70 %  media  64.9%  →  real  75.0%  (4)
  Predicho 80-90 %  media  81.1%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 90
  Acierto ganador (combinado)        ████████████░░░░░░░░  62.2%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  57.8%
  Acierto ganador (solo ratings)     ███████████░░░░░░░░░  53.3%
  Acierto del favorito del mercado   █████████████░░░░░░░  63.3%
  Brier score: 0.226 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.642
  Error medio del margen: 9.38 pts · del total: 11.57 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.38 pts vs mercado 9.43 pts
  Acierto contra el spread           ███████████░░░░░░░░░  56.0%  (84)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  54.2%  (24)
  Error medio del total: modelo 11.57 vs mercado 10.49
  Acierto over/under                 ████████░░░░░░░░░░░░  40.0%  (90)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```
