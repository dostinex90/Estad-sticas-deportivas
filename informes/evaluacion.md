# Precisión de los modelos

_Actualizado automáticamente: 2026-11-02 19:35 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                    108    55.6%   0.556    0.943   0.188
  Referencia (frecuencias)          108    45.4%   0.647    1.070   0.229
  Modelo (partidos c/cuotas)        108    55.6%   0.556    0.943   0.188
  Mercado de apuestas               108    56.5%   0.543    0.921   0.184

  Acierto en más/menos de 2.5 goles: 63.0% (108 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.3%  →  real   0.0%  (8)
  Predicho 10-20 %  media  16.1%  →  real   5.4%  (37)
  Predicho 20-30 %  media  26.1%  →  real  25.9%  (147)
  Predicho 30-40 %  media  35.0%  →  real  36.6%  (41)
  Predicho 40-50 %  media  45.3%  →  real  45.5%  (44)
  Predicho 50-60 %  media  54.3%  →  real  65.4%  (26)
  Predicho 60-70 %  media  62.9%  →  real  44.4%  (9)
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
  Modelo Poisson                     89    46.1%   0.619    1.031   0.210
  Referencia (frecuencias)           89    40.4%   0.661    1.090   0.229
  Modelo (partidos c/cuotas)         89    46.1%   0.619    1.031   0.210
  Mercado de apuestas                89    48.3%   0.610    1.017   0.205

  Acierto en más/menos de 2.5 goles: 48.3% (89 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   8.3%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.4%  →  real  16.7%  (18)
  Predicho 20-30 %  media  25.9%  →  real  27.9%  (122)
  Predicho 30-40 %  media  35.0%  →  real  32.1%  (56)
  Predicho 40-50 %  media  44.6%  →  real  43.6%  (39)
  Predicho 50-60 %  media  54.4%  →  real  44.4%  (18)
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
  Modelo Poisson                     98    61.2%   0.542    0.926   0.198
  Referencia (frecuencias)           98    48.0%   0.631    1.043   0.243
  Modelo (partidos c/cuotas)         98    61.2%   0.542    0.926   0.198
  Mercado de apuestas                98    63.3%   0.514    0.888   0.187

  Acierto en más/menos de 2.5 goles: 43.9% (98 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.6%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.0%  →  real  12.9%  (31)
  Predicho 20-30 %  media  26.4%  →  real  16.5%  (121)
  Predicho 30-40 %  media  33.7%  →  real  35.9%  (64)
  Predicho 40-50 %  media  44.9%  →  real  57.1%  (35)
  Predicho 50-60 %  media  55.0%  →  real  70.4%  (27)
  Predicho 60-70 %  media  63.8%  →  real  90.0%  (10)
  Predicho 70-80 %  media  75.2%  →  real 100.0%  (3)
```

## Bundesliga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                     72    48.6%   0.601    1.000   0.213
  Referencia (frecuencias)           72    48.6%   0.633    1.050   0.230
  Modelo (partidos c/cuotas)         72    48.6%   0.601    1.000   0.213
  Mercado de apuestas                72    52.8%   0.606    1.008   0.215

  Acierto en más/menos de 2.5 goles: 69.4% (72 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.7%  →  real   0.0%  (4)
  Predicho 10-20 %  media  15.6%  →  real  18.2%  (33)
  Predicho 20-30 %  media  23.9%  →  real  25.6%  (86)
  Predicho 30-40 %  media  35.4%  →  real  38.7%  (31)
  Predicho 40-50 %  media  45.2%  →  real  40.0%  (20)
  Predicho 50-60 %  media  55.1%  →  real  45.5%  (22)
  Predicho 60-70 %  media  64.6%  →  real  63.6%  (11)
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
  Modelo Poisson                     80    55.0%   0.574    0.968   0.197
  Referencia (frecuencias)           80    48.8%   0.634    1.053   0.226
  Modelo (partidos c/cuotas)         80    55.0%   0.574    0.968   0.197
  Mercado de apuestas                80    56.2%   0.570    0.961   0.196

  Acierto en más/menos de 2.5 goles: 58.8% (80 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.0%  →  real   0.0%  (1)
  Predicho 10-20 %  media  17.2%  →  real  13.6%  (22)
  Predicho 20-30 %  media  25.8%  →  real  22.0%  (109)
  Predicho 30-40 %  media  34.5%  →  real  26.8%  (41)
  Predicho 40-50 %  media  44.0%  →  real  60.0%  (35)
  Predicho 50-60 %  media  55.4%  →  real  60.0%  (25)
  Predicho 60-70 %  media  64.0%  →  real  83.3%  (6)
  Predicho 80-90 %  media  81.1%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 119
  Acierto ganador (combinado)        █████████████░░░░░░░  65.5%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  61.3%
  Acierto ganador (solo ratings)     ███████████░░░░░░░░░  54.6%
  Acierto del favorito del mercado   █████████████░░░░░░░  66.4%
  Brier score: 0.216 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.623
  Error medio del margen: 9.48 pts · del total: 11.53 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.48 pts vs mercado 9.53 pts
  Acierto contra el spread           ████████████░░░░░░░░  57.5%  (113)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  53.6%  (28)
  Error medio del total: modelo 11.53 vs mercado 10.69
  Acierto over/under                 █████████░░░░░░░░░░░  44.5%  (119)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```

## NBA (temporada en curso o, si no ha empezado, la anterior)

```
Validación del modelo en 2026-27 (día a día, sin datos futuros)
═══════════════════════════════════════════════════════════════
  Partidos evaluados: 92
  Acierto ganador (combinado)        █████████████░░░░░░░  67.4%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  58.7%
  Acierto ganador (solo ratings)     ████████████░░░░░░░░  62.0%
  Gana siempre el local              ██████████░░░░░░░░░░  52.2%
  Brier score: 0.207 (0.25 = lanzar una moneda; menor es mejor) · solo Elo 0.228 · log-loss 0.598
  Error medio del margen: 11.66 pts · del total: 15.51 pts
  La base no tiene líneas de apuestas de la NBA, así que no hay comparación con el mercado.
```
