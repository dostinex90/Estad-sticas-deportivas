# Precisión de los modelos

_Actualizado automáticamente: 2026-11-24 20:14 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                    129    55.8%   0.559    0.948   0.188
  Referencia (frecuencias)          129    44.2%   0.652    1.077   0.231
  Modelo (partidos c/cuotas)        129    55.8%   0.559    0.948   0.188
  Mercado de apuestas               129    55.8%   0.543    0.921   0.183

  Acierto en más/menos de 2.5 goles: 61.2% (129 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.6%  →  real   0.0%  (9)
  Predicho 10-20 %  media  16.1%  →  real   4.9%  (41)
  Predicho 20-30 %  media  26.1%  →  real  26.3%  (179)
  Predicho 30-40 %  media  35.0%  →  real  34.7%  (49)
  Predicho 40-50 %  media  45.2%  →  real  44.4%  (54)
  Predicho 50-60 %  media  54.0%  →  real  64.5%  (31)
  Predicho 60-70 %  media  63.0%  →  real  54.5%  (11)
  Predicho 70-80 %  media  73.2%  →  real 100.0%  (11)
  Predicho 80-90 %  media  83.7%  →  real 100.0%  (2)
```

## Premier League (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                    110    46.4%   0.618    1.028   0.211
  Referencia (frecuencias)          110    43.6%   0.652    1.078   0.227
  Modelo (partidos c/cuotas)        110    46.4%   0.618    1.028   0.211
  Mercado de apuestas               110    48.2%   0.614    1.023   0.209

  Acierto en más/menos de 2.5 goles: 48.2% (110 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.7%  →  real   0.0%  (4)
  Predicho 10-20 %  media  16.4%  →  real  14.3%  (21)
  Predicho 20-30 %  media  25.9%  →  real  27.4%  (157)
  Predicho 30-40 %  media  35.0%  →  real  32.8%  (61)
  Predicho 40-50 %  media  44.9%  →  real  45.1%  (51)
  Predicho 50-60 %  media  54.3%  →  real  47.8%  (23)
  Predicho 60-70 %  media  63.5%  →  real  66.7%  (9)
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
  Modelo Poisson                    120    60.8%   0.539    0.922   0.194
  Referencia (frecuencias)          120    47.5%   0.634    1.047   0.242
  Modelo (partidos c/cuotas)        120    60.8%   0.539    0.922   0.194
  Mercado de apuestas               120    63.3%   0.513    0.886   0.184

  Acierto en más/menos de 2.5 goles: 44.2% (120 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.6%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.3%  →  real  12.2%  (41)
  Predicho 20-30 %  media  26.4%  →  real  17.3%  (150)
  Predicho 30-40 %  media  33.7%  →  real  36.6%  (71)
  Predicho 40-50 %  media  44.9%  →  real  52.3%  (44)
  Predicho 50-60 %  media  55.3%  →  real  72.2%  (36)
  Predicho 60-70 %  media  63.7%  →  real  91.7%  (12)
  Predicho 70-80 %  media  75.2%  →  real 100.0%  (3)
```

## Bundesliga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     90    55.6%   0.570    0.959   0.200
  Referencia (frecuencias)           90    50.0%   0.628    1.042   0.230
  Modelo (partidos c/cuotas)         90    55.6%   0.570    0.959   0.200
  Mercado de apuestas                90    57.8%   0.572    0.964   0.201

  Acierto en más/menos de 2.5 goles: 67.8% (90 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.9%  →  real  12.5%  (8)
  Predicho 10-20 %  media  15.9%  →  real  14.3%  (42)
  Predicho 20-30 %  media  23.9%  →  real  22.9%  (105)
  Predicho 30-40 %  media  35.0%  →  real  34.3%  (35)
  Predicho 40-50 %  media  45.2%  →  real  51.9%  (27)
  Predicho 50-60 %  media  55.0%  →  real  50.0%  (26)
  Predicho 60-70 %  media  64.7%  →  real  73.3%  (15)
  Predicho 70-80 %  media  74.0%  →  real  88.9%  (9)
  Predicho 80-90 %  media  85.2%  →  real  33.3%  (3)
```

## Ligue 1 (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     99    50.5%   0.596    0.999   0.209
  Referencia (frecuencias)           99    44.4%   0.648    1.071   0.234
  Modelo (partidos c/cuotas)         99    50.5%   0.596    0.999   0.209
  Mercado de apuestas                99    53.5%   0.580    0.974   0.202

  Acierto en más/menos de 2.5 goles: 55.6% (99 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.1%  →  real   0.0%  (2)
  Predicho 10-20 %  media  17.0%  →  real  15.4%  (26)
  Predicho 20-30 %  media  25.7%  →  real  23.9%  (134)
  Predicho 30-40 %  media  34.9%  →  real  30.4%  (56)
  Predicho 40-50 %  media  44.2%  →  real  55.0%  (40)
  Predicho 50-60 %  media  55.4%  →  real  56.7%  (30)
  Predicho 60-70 %  media  64.7%  →  real  71.4%  (7)
  Predicho 70-80 %  media  79.9%  →  real 100.0%  (1)
  Predicho 80-90 %  media  81.1%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 162
  Acierto ganador (combinado)        ██████████████░░░░░░  68.5%
  Acierto ganador (solo Elo)         █████████████░░░░░░░  63.0%
  Acierto ganador (solo ratings)     ████████████░░░░░░░░  60.5%
  Acierto del favorito del mercado   ██████████████░░░░░░  68.5%
  Brier score: 0.204 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.596
  Error medio del margen: 9.47 pts · del total: 11.29 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.47 pts vs mercado 9.46 pts
  Acierto contra el spread           ███████████░░░░░░░░░  55.8%  (156)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  52.8%  (36)
  Error medio del total: modelo 11.29 vs mercado 10.41
  Acierto over/under                 █████████░░░░░░░░░░░  43.8%  (162)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```

## NBA (temporada en curso o, si no ha empezado, la anterior)

```
Validación del modelo en 2026-27 (día a día, sin datos futuros)
═══════════════════════════════════════════════════════════════
  Partidos evaluados: 258
  Acierto ganador (combinado)        ██████████████░░░░░░  68.2%
  Acierto ganador (solo Elo)         █████████████░░░░░░░  64.7%
  Acierto ganador (solo ratings)     █████████████░░░░░░░  67.1%
  Gana siempre el local              ██████████░░░░░░░░░░  51.9%
  Brier score: 0.200 (0.25 = lanzar una moneda; menor es mejor) · solo Elo 0.214 · log-loss 0.586
  Error medio del margen: 11.12 pts · del total: 14.97 pts
  La base no tiene líneas de apuestas de la NBA, así que no hay comparación con el mercado.
```
