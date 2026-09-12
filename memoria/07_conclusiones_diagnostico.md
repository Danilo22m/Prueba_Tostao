# Conclusiones del diagnóstico del modelo

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/07_diagnostico.txt` y de las figuras 18 a 20.
Modelo diagnosticado: regresión cuantílica en parametrización relativa.

Las cifras comparativas de la parametrización absoluta se reproducen cambiando
la constante `FAMILIA` del script correspondiente. Ver `T1_parametrizacion_relativa.md`.

---

## 1. El error se concentra en las tiendas pequeñas

| Tramo por volumen | Demanda media | MAE | Error porcentual | Sesgo |
|---|---|---|---|---|
| 1, el más bajo | 44,6 | 7,93 | **17,8 %** | −3,44 |
| 2 | 73,1 | 9,05 | 12,4 % | +0,15 |
| 3 | 102,4 | 11,10 | 10,8 % | −3,20 |
| 4, el más alto | 153,8 | 15,84 | 10,3 % | +6,85 |

**Por qué ocurre.** En una serie que vende 45 unidades, un error de 8 es un 18 %.
En una que vende 154, un error de 16 es un 10 %. La demanda baja es
proporcionalmente más ruidosa, y con trece semanas no hay forma de separar señal
de ruido en esas series.

**Consecuencia operativa.** Las tiendas pequeñas necesitan más colchón relativo y
conviene vigilarlas de cerca en el piloto.

## 2. Queda un sesgo residual por tamaño, reducido pero no eliminado

Mira la columna de sesgo. El modelo sobrepredice las series pequeñas en 3,4
unidades y subpredice las grandes en 6,9.

Es el efecto de la regularización, que encoge las predicciones hacia el centro.
La parametrización relativa lo redujo un 32 % respecto a la versión absoluta, que
iba de −4,96 a +10,08, pero no lo hizo desaparecer.

**Por qué importa para el pedido.** Ese sesgo se traduce en merma en las tiendas
pequeñas y ventas perdidas en las grandes, justo al revés de lo que conviene.
Queda como línea de mejora: bajar el alfa de regularización o modelar por
segmentos de volumen son los siguientes candidatos, y merecen probarse antes del
piloto.

## 3. Lo que está bien

**No queda estructura temporal sin capturar.** El contraste de Ljung-Box no
detecta autocorrelación en ninguna de las 160 series. El modelo ha extraído toda
la señal temporal que había, que era poca.

**Los residuales están casi centrados y son más simétricos.** La media es de 0,11
unidades sobre una demanda media de 93, y la asimetría de 0,29. En la versión
absoluta eran 0,65 y 0,61.

**No hay error sistemático por tipo de patrón.** Los cuatro tipos quedan entre
11,2 y 12,2 % de error. Coherente con lo ya medido: esas etiquetas no separan el
comportamiento real de las series.

**El modelo usa algo más que antes, pero sigue siendo muy simple.** En la
parametrización absoluta la regularización anulaba 12 de 14 variables. En la
relativa quedan 7 con coeficiente no nulo: el rezago, el tamaño de tienda y cinco
de las ocho indicadoras de producto.

Pero la importancia por permutación matiza ese dato. Solo el rezago aporta de
forma medible, con una degradación del 24,9 % al barajarlo. El tamaño de tienda
aporta un 0,09 % y el resto exactamente cero. Los coeficientes de producto no son
nulos pero su efecto sobre la métrica es indistinguible del ruido.

**La descripción honesta del modelo** es: predice la razón entre la demanda de la
semana y la media de las cuatro previas, apoyándose casi solo en la razón de la
semana anterior, y multiplica de vuelta. Sigue siendo una regla sencilla, pero
opera sobre la forma de la trayectoria y no sobre el nivel.

## 4. Hay heterocedasticidad, y es esperable

La correlación entre el valor predicho y el error absoluto es de +0,36, algo
menor que el +0,40 de la versión absoluta. El error sigue creciendo con el nivel
de la serie.

No invalida nada, pero tiene una consecuencia concreta: el intervalo no puede
tener el mismo ancho absoluto en una serie que vende 45 y en una que vende 154.
El modelo elegido ya lo gradúa, y es otro motivo por el que un colchón plano
sería incorrecto.

## 5. Once series necesitan revisión antes del piloto

De las 160, once superan el doble del error mediano, frente a trece en la versión
absoluta. Las cinco peores:

| Serie | Demanda media | Error | Sesgo |
|---|---|---|---|
| STORE_09 / Café con Leche | 30,7 | 43,0 % | −13,2 |
| STORE_09 / Croissant | 71,0 | 30,1 % | −3,4 |
| STORE_07 / Buñuelo | 34,7 | 29,8 % | −10,3 |
| STORE_14 / Café con Leche | 70,3 | 29,1 % | −2,4 |
| STORE_09 / Cappuccino | 53,0 | 28,9 % | −14,6 |

Tres de las cinco son de STORE_09. Todas tienen sesgo negativo, es decir el
modelo pide de más en todas.

**Acción concreta.** Revisar esas once series antes de implantar, y excluirlas
del piloto o vigilarlas aparte. Que STORE_09 aparezca tres veces sugiere algo
propio de esa tienda y no del modelo.

## 6. La interpretabilidad mejoró de forma sustancial

Los coeficientes están sobre variables estandarizadas y, al trabajar en
proporción, se leen en porcentaje. Un coeficiente de 0,0185 en el rezago
significa que una desviación típica en la última semana mueve la predicción un
1,85 % respecto a la media reciente de esa serie.

Eso se le explica a un jefe de tienda. Un coeficiente de 32,57 en unidades
estandarizadas, que era lo que daba la versión absoluta, no.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Probar un alfa menor para reducir el sesgo residual por volumen | Mejora previa al piloto |
| 2 | Reportar el error por tramo de volumen, no solo el agregado | Presentación |
| 3 | Vigilar las once series con error alto en el piloto | Plan de implantación |
| 4 | Revisar STORE_09 aparte, por concentrar tres de las cinco peores | Plan de implantación |
| 5 | Usar la ausencia de autocorrelación residual como validación del diseño | Memoria técnica |
| 6 | Presentar los coeficientes en porcentaje | Presentación |
| 7 | Declarar que solo el rezago aporta de forma medible | Presentación |
