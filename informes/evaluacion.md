# Precisión de los modelos

_Actualizado automáticamente: 2026-11-04 17:22 UTC_

## LaLiga (temporada en curso)

```
Validación histórica del modelo (sin mirar el futuro)
═════════════════════════════════════════════════════
  Para cada jornada se ajusta el modelo solo con los partidos anteriores y se predice esa jornada.
  Brier, log-loss y RPS: menor es mejor. RPS es la métrica estándar para 1X2.

                               Partidos  Acierto   Brier  LogLoss     RPS
  Modelo Poisson                    109    56.0%   0.556    0.943   0.188
  Referencia (frecuencias)          109    45.9%   0.645    1.067   0.229
  Modelo (partidos c/cuotas)        109    56.0%   0.556    0.943   0.188
  Mercado de apuestas               109    56.9%   0.542    0.920   0.184

  Acierto en más/menos de 2.5 goles: 62.4% (109 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.3%  →  real   0.0%  (8)
  Predicho 10-20 %  media  16.1%  →  real   5.4%  (37)
  Predicho 20-30 %  media  26.2%  →  real  25.7%  (148)
  Predicho 30-40 %  media  34.9%  →  real  35.7%  (42)
  Predicho 40-50 %  media  45.2%  →  real  46.7%  (45)
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
  Modelo Poisson                     90    45.6%   0.621    1.034   0.211
  Referencia (frecuencias)           90    40.0%   0.662    1.092   0.230
  Modelo (partidos c/cuotas)         90    45.6%   0.621    1.034   0.211
  Mercado de apuestas                90    47.8%   0.611    1.019   0.206

  Acierto en más/menos de 2.5 goles: 47.8% (90 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   8.3%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.4%  →  real  16.7%  (18)
  Predicho 20-30 %  media  26.0%  →  real  28.2%  (124)
  Predicho 30-40 %  media  35.0%  →  real  32.1%  (56)
  Predicho 40-50 %  media  44.6%  →  real  42.5%  (40)
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
  Modelo Poisson                    100    61.0%   0.547    0.934   0.201
  Referencia (frecuencias)          100    47.0%   0.632    1.043   0.244
  Modelo (partidos c/cuotas)        100    61.0%   0.547    0.934   0.201
  Mercado de apuestas               100    63.0%   0.520    0.898   0.191

  Acierto en más/menos de 2.5 goles: 43.0% (100 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   7.6%  →  real   0.0%  (3)
  Predicho 10-20 %  media  16.1%  →  real  15.6%  (32)
  Predicho 20-30 %  media  26.5%  →  real  16.3%  (123)
  Predicho 30-40 %  media  33.8%  →  real  36.4%  (66)
  Predicho 40-50 %  media  44.9%  →  real  57.1%  (35)
  Predicho 50-60 %  media  55.1%  →  real  67.9%  (28)
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
  Modelo Poisson                     81    54.3%   0.576    0.971   0.199
  Referencia (frecuencias)           81    48.1%   0.636    1.055   0.228
  Modelo (partidos c/cuotas)         81    54.3%   0.576    0.971   0.199
  Mercado de apuestas                81    55.6%   0.571    0.963   0.198

  Acierto en más/menos de 2.5 goles: 58.0% (81 partidos)

── Calibración (¿lo que el modelo dice 60% ocurre ~60%?) ───────
  Predicho  0-10 %  media   6.0%  →  real   0.0%  (1)
  Predicho 10-20 %  media  17.2%  →  real  13.6%  (22)
  Predicho 20-30 %  media  25.8%  →  real  22.5%  (111)
  Predicho 30-40 %  media  34.5%  →  real  26.8%  (41)
  Predicho 40-50 %  media  44.0%  →  real  58.3%  (36)
  Predicho 50-60 %  media  55.4%  →  real  60.0%  (25)
  Predicho 60-70 %  media  64.0%  →  real  83.3%  (6)
  Predicho 80-90 %  media  81.1%  →  real 100.0%  (1)
```

## NFL (temporada en curso)

```
Validación del modelo en 2026 (semana a semana, sin datos futuros)
══════════════════════════════════════════════════════════════════
  Partidos evaluados: 120
  Acierto ganador (combinado)        █████████████░░░░░░░  65.0%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  60.8%
  Acierto ganador (solo ratings)     ███████████░░░░░░░░░  54.2%
  Acierto del favorito del mercado   █████████████░░░░░░░  65.8%
  Brier score: 0.217 (0.25 = lanzar una moneda; menor es mejor) · log-loss 0.625
  Error medio del margen: 9.56 pts · del total: 11.47 pts

── Frente a las casas de apuestas ──────────────────────────────
  Error medio del margen: modelo 9.56 pts vs mercado 9.62 pts
  Acierto contra el spread           ████████████░░░░░░░░  57.9%  (114)
  ATS con diferencia ≥3 pts          ███████████░░░░░░░░░  53.6%  (28)
  Error medio del total: modelo 11.47 vs mercado 10.64
  Acierto over/under                 █████████░░░░░░░░░░░  44.2%  (120)
  Para ganar apostando a -110 hace falta acertar más del 52.4% contra el spread.
```

## NBA (temporada en curso o, si no ha empezado, la anterior)

```
Validación del modelo en 2026-27 (día a día, sin datos futuros)
═══════════════════════════════════════════════════════════════
  Partidos evaluados: 107
  Acierto ganador (combinado)        █████████████░░░░░░░  67.3%
  Acierto ganador (solo Elo)         ████████████░░░░░░░░  59.8%
  Acierto ganador (solo ratings)     █████████████░░░░░░░  63.6%
  Gana siempre el local              ██████████░░░░░░░░░░  51.4%
  Brier score: 0.207 (0.25 = lanzar una moneda; menor es mejor) · solo Elo 0.228 · log-loss 0.599
  Error medio del margen: 11.44 pts · del total: 15.56 pts
  La base no tiene líneas de apuestas de la NBA, así que no hay comparación con el mercado.
```
