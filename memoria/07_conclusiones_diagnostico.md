# Conclusiones del diagnóstico del modelo

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/07_diagnostico.txt` y de las figuras 18 a 20.

---

## 1. El modelo se redujo a una media móvil ponderada

Es el hallazgo del paso y obliga a replantear cómo se presenta el trabajo.

Coeficientes sobre variables estandarizadas:

| Variable | Coeficiente |
|---|---|
| media_4 | 32,57 |
| rezago_1 | 6,38 |
| cv_reciente | −0,29 |
| tamano_m2 | 0,01 |
| desv_4, razon_ultima | 0,00 |
| Las ocho indicadoras de producto | 0,00 |

La regularización L1 anuló todo menos dos variables. La importancia por
permutación lo confirma: barajar `media_4` degrada la pérdida un 283 %, barajar
`rezago_1` un 28 %, y barajar cualquier otra no cambia nada.

**Qué significa.** El modelo elegido es, en la práctica, la media de las últimas
cuatro semanas con una corrección por la última. No usa la identidad del
producto, ni el tamaño de la tienda, ni la volatilidad reciente para el centro.

Eso explica por qué empata con la línea base: **es casi la misma regla**. La
diferencia está en que la regresión cuantílica sí gradúa el ancho del abanico,
mientras que la media móvil lo aplica plano.

**Consecuencia para la presentación.** Hay que decirlo abiertamente. La
conclusión honesta del proyecto no es «entrenamos un modelo que mejora el
pronóstico», es «medimos que nada mejora a una media móvil, y el valor está en
la política de pedido». Presentarlo así es más sólido que disfrazarlo.

## 2. El error se concentra en las tiendas pequeñas

| Tramo por volumen | Demanda media | MAE | Error porcentual | Sesgo |
|---|---|---|---|---|
| 1, el más bajo | 44,6 | 8,38 | **18,8 %** | −4,96 |
| 2 | 73,1 | 8,94 | 12,2 % | −0,31 |
| 3 | 102,4 | 10,76 | 10,5 % | −2,28 |
| 4, el más alto | 153,8 | 17,30 | 11,3 % | +10,08 |

Y por tienda, la correlación entre superficie y error es de −0,54: cuanto más
pequeña la tienda, mayor el error relativo. Las tres peores son las de 15, 19 y
25 metros cuadrados.

**Por qué ocurre.** En una serie que vende 40 unidades, un error de 8 es un 20 %.
En una que vende 154, un error de 17 es un 11 %. La demanda baja es
proporcionalmente más ruidosa, y con trece semanas no hay forma de separar señal
de ruido en esas series.

**Consecuencia operativa.** Las tiendas pequeñas necesitan más colchón relativo, y
conviene vigilarlas de cerca en el piloto.

## 3. Hay un sesgo sistemático por tamaño de serie

Mira la columna de sesgo de la tabla anterior. El modelo **sobrepredice las
series pequeñas en 5 unidades y subpredice las grandes en 10**.

Es el efecto clásico de la regularización: encoge las predicciones hacia el
centro. Con una penalización L1 fuerte, las series extremas se atraen hacia la
media general.

**Por qué importa para el pedido.** Ese sesgo se traduce directamente en merma en
las tiendas pequeñas y en ventas perdidas en las grandes, justo al revés de lo
que conviene. Es corregible bajando el alfa de regularización o modelando por
segmentos de volumen, y merece probarse antes del piloto.

## 4. Lo que está bien

**No queda estructura temporal sin capturar.** El contraste de Ljung-Box no
detecta autocorrelación en ninguna de las 160 series. El modelo ha extraído toda
la señal temporal que había, que era poca.

**No hay error sistemático por tipo de patrón.** Los cuatro tipos quedan entre
12,0 y 12,5 % de error. Coherente con lo ya medido: esas etiquetas no separan el
comportamiento real de las series.

**Los residuales están centrados**, con media de 0,65 unidades sobre una demanda
media de 93.

## 5. Hay heterocedasticidad, y es esperable

La correlación entre el valor predicho y el error absoluto es de +0,40: el error
crece con el nivel de la serie.

No invalida nada, pero tiene una consecuencia concreta: el intervalo no puede
tener el mismo ancho absoluto en una serie que vende 40 y en una que vende 154.
El modelo elegido ya lo hace, y es otro motivo por el que un colchón plano sería
incorrecto.

## 6. Trece series necesitan revisión antes del piloto

De las 160, trece superan el doble del error mediano. Las cinco peores:

| Serie | Demanda media | Error | Sesgo |
|---|---|---|---|
| STORE_09 / Café con Leche | 30,7 | 47,2 % | −14,5 |
| STORE_17 / Pan de Bono | 16,3 | 38,9 % | −6,4 |
| STORE_07 / Buñuelo | 34,7 | 34,6 % | −12,0 |
| STORE_09 / Croissant | 71,0 | 30,2 % | −3,1 |
| STORE_09 / Cappuccino | 53,0 | 28,6 % | −15,0 |

Tres de las cinco son de STORE_09. Todas tienen sesgo negativo, es decir el
modelo pide de más en todas.

**Acción concreta.** Revisar esas trece series antes de implantar, y excluirlas
del piloto o vigilarlas aparte. Que STORE_09 aparezca tres veces sugiere algo
propio de esa tienda y no del modelo.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Declarar que el modelo se redujo a una media móvil ponderada | Presentación |
| 2 | Probar un alfa menor para corregir el encogimiento hacia el centro | Mejora previa al piloto |
| 3 | Reportar el error por tramo de volumen, no solo el agregado | Presentación |
| 4 | Vigilar las trece series con error alto en el piloto | Plan de implantación |
| 5 | Revisar STORE_09 aparte, por concentrar tres de las cinco peores | Plan de implantación |
| 6 | Usar la ausencia de autocorrelación residual como validación del diseño | Memoria técnica |
