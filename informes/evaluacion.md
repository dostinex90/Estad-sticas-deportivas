# Precisión de los modelos

_Actualizado automáticamente: 2026-11-11 17:16 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                    119    55.5%   0.561    0.950   0.188
  Referencia (frecuencias)          119    43.7%   0.654    1.080   0.231
  Modelo (partidos c/cuotas)        119    55.5%   0.561    0.950   0.188
  Mercado de apuestas               119    56.3%   0.541    0.918   0.181

  Acierto en más/menos de 2.5 goles: 62.2% (119 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.3%  →  real   0.0%  (8)
  Predicho 10-20 %  media  16.0%  →  real   5.3%  (38)
  Predicho 20-30 %  media  26.2%  →  real  26.1%  (165)
  Predicho 30-40 %  media  34.8%  →  real  35.6%  (45)
  Predicho 40-50 %  media  45.2%  →  real  45.1%  (51)
  Predicho 50-60 %  media  54.0%  →  real  64.3%  (28)
  Predicho 60-70 %  media  62.7%  →  real  50.0%  (10)
  Predicho 70-80 %  media  73.3%  →  real 100.0%  (10)
  Predicho 80-90 %  media  83.7%  →  real 100.0%  (2)
```

## Premier League (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                    100    47.0%   0.612    1.020   0.209
  Referencia (frecuencias)          100    42.0%   0.657    1.084   0.229
  Modelo (partidos c/cuotas)        100    47.0%   0.612    1.020   0.209
  Mercado de apuestas               100    48.0%   0.605    1.011   0.205

  Acierto en más/menos de 2.5 goles: 49.0% (100 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.7%  →  real   0.0%  (4)
  Predicho 10-20 %  media  16.4%  →  real  15.0%  (20)
  Predicho 20-30 %  media  26.0%  →  real  27.3%  (139)
  Predicho 30-40 %  media  35.0%  →  real  32.2%  (59)
  Predicho 40-50 %  media  44.8%  →  real  44.7%  (47)
  Predicho 50-60 %  media  54.5%  →  real  47.4%  (19)
  Predicho 60-70 %  media  63.8%  →  real  75.0%  (8)
  Predicho 70-80 %  media  75.1%  →  real 100.0%  (3)
  Predicho 80-90 %  media  80.0%  →  real 100.0%  (1)
```

## Serie A (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                    110    60.9%   0.546    0.931   0.198
  Referencia (frecuencias)          110    46.4%   0.635    1.049   0.243
  Modelo (partidos c/cuotas)        110    60.9%   0.546    0.931   0.198
  Mercado de apuestas               110    62.7%   0.521    0.898   0.189

  Acierto en más/menos de 2.5 goles: 43.6% (110 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.6%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.2%  →  real  14.3%  (35)
  Predicho 20-30 %  media  26.5%  →  real  16.8%  (137)
  Predicho 30-40 %  media  33.6%  →  real  36.2%  (69)
  Predicho 40-50 %  media  44.9%  →  real  54.8%  (42)
  Predicho 50-60 %  media  55.1%  →  real  70.0%  (30)
  Predicho 60-70 %  media  63.6%  →  real  90.9%  (11)
  Predicho 70-80 %  media  75.2%  →  real 100.0%  (3)
```

## Bundesliga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     81    53.1%   0.569    0.956   0.201
  Referencia (frecuencias)           81    50.6%   0.626    1.039   0.229
  Modelo (partidos c/cuotas)         81    53.1%   0.569    0.956   0.201
  Mercado de apuestas                81    56.8%   0.574    0.965   0.204

  Acierto en más/menos de 2.5 goles: 70.4% (81 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.9%  →  real   0.0%  (5)
  Predicho 10-20 %  media  15.9%  →  real  14.6%  (41)
  Predicho 20-30 %  media  23.9%  →  real  24.5%  (94)
  Predicho 30-40 %  media  35.3%  →  real  37.5%  (32)
  Predicho 40-50 %  media  45.2%  →  real  40.9%  (22)
  Predicho 50-60 %  media  55.0%  →  real  50.0%  (24)
  Predicho 60-70 %  media  64.7%  →  real  73.3%  (15)
  Predicho 70-80 %  media  73.9%  →  real  87.5%  (8)
  Predicho 80-90 %  media  83.5%  →  real  50.0%  (2)
```

## Ligue 1 (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     90    52.2%   0.580    0.976   0.204
  Referencia (frecuencias)           90    46.7%   0.640    1.059   0.233
  Modelo (partidos c/cuotas)         90    52.2%   0.580    0.976   0.204
  Mercado de apuestas                90    55.6%   0.568    0.958   0.199

  Acierto en más/menos de 2.5 goles: 56.7% (90 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.1%  →  real   0.0%  (2)
  Predicho 10-20 %  media  17.1%  →  real  13.0%  (23)
  Predicho 20-30 %  media  25.9%  →  real  22.3%  (121)
  Predicho 30-40 %  media  34.8%  →  real  30.8%  (52)
  Predicho 40-50 %  media  44.0%  →  real  57.9%  (38)
  Predicho 50-60 %  media  55.3%  →  real  57.7%  (26)
  Predicho 60-70 %  media  64.0%  →  real  83.3%  (6)
  Predicho 70-80 %  media  79.9%  →  real 100.0%  (1)
  Predicho 80-90 %  media  81.1%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 135
  Acierto ganador (combinado)        ██████████████░░░░░░  68.1%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  62.2%
  Acierto ganador (solo ratings)     ████████████░░░░░░░░  58.5%
  Acierto del favorito del mercado   ██████████████░░░░░░  68.9%
  Brier score: 0.208 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.605
  Error medio del margen: 9.49 pts · del total: 11.50 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.49 pts vs mercado 9.53 pts
  Acierto contra el spread           ███████████░░░░░░░░░  57.4%  (129)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  56.7%  (30)
  Error medio del total: modelo 11.50 vs mercado 10.58
  Acierto over/under                 █████████░░░░░░░░░░░  43.7%  (135)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```

## NBA (temporada en curso o, si no ha empezado, la anterior)

```
Validación del modelo en 2026-27 (día a día, sin datos futuros)
═══════════════════════════════════════════════════════════════
  Partidos evaluados: 160
  Acierto ganador (combinado)        ██████████████░░░░░░  69.4%
  Acierto ganador (solo Elo)         █████████████░░░░░░░  65.6%
  Acierto ganador (solo ratings)     ██████████████░░░░░░  68.8%
  Gana siempre el local              ██████████░░░░░░░░░░  51.9%
  Brier score: 0.195 (0.25 = lanzar una moneda; menor es mejor) · solo Elo 0.208 · log-loss 0.572
  Error medio del margen: 11.65 pts · del total: 14.68 pts
  La base no tiene líneas de apuestas de la NBA, así que no hay comparación con el mercado.
```
