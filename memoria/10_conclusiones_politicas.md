# Conclusiones de la simulación de políticas

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/10_politicas.txt` y de las figuras 23 y 24.

Es el paso que produce la cifra de negocio. Las predicciones ya incorporan la
calibración conformal, que se aplica dentro del entrenamiento. Demanda real, decisión hipotética,
sobre las 480 decisiones de las semanas de prueba.

---

## 1. El diseño: cinco políticas, no dos

|  | Pedir el centro | Pedir el nivel de servicio |
|---|---|---|
| **Pronóstico ingenuo** | P1 | P3 |
| **Pronóstico del modelo** | P2 | P4 |

Más P0, repetir lo de la semana anterior, que aproxima la práctica actual.

**Por qué no bastan dos.** Comparar solo P0 contra P4 daría un ahorro grande sin
saber a qué atribuirlo. Con una asimetría de costes como la de este catálogo,
casi cualquier regla que pida más gana esa comparación. El diseño factorial
permite cambiar un factor manteniendo el otro.

## 2. Resultado

| Política | Coste total | Ventas perdidas | Merma | Servicio real |
|---|---|---|---|---|
| P4 modelo, pedir el nivel | **9.062.061** | 3.974.025 | 5.088.036 | 96,1 % |
| P3 media móvil, pedir el nivel | 9.255.833 | 4.042.293 | 5.213.540 | 96,0 % |
| P2 modelo, pedir el centro | 9.512.699 | 6.106.946 | 3.405.752 | 93,9 % |
| P1 media móvil, pedir el centro | 9.561.518 | 5.958.025 | 3.603.493 | 94,0 % |
| P0 repetir la semana anterior | 11.022.905 | 7.085.000 | 3.937.905 | 93,1 % |

La propuesta completa cuesta un 17,8 % menos que la práctica actual y un 5,2 %
menos que pedir el pronóstico central.

**Fíjate en la composición del coste**, no solo en el total. Las políticas de
nivel cambian merma por ventas perdidas: P4 tiene 1,8 millones más de merma que
P1, pero 2,2 millones menos en ventas perdidas. El servicio real sube del 94,0 %
al 96,3 %.

## 3. De dónde viene el ahorro

| Componente | Ahorro | Peso |
|---|---|---|
| Efecto de la regla | 305.685 | **61 %** |
| Interacción | 144.953 | 29 % |
| Efecto del modelo | 48.819 | 10 % |
| **Total** | **499.457** | 100 % |

**Seis de cada diez pesos del ahorro vienen de cambiar la regla de pedido, no de
predecir mejor.** Es exactamente lo que la tesis del proyecto anticipaba desde el
análisis exploratorio, y ahora está medido con un diseño que lo aísla.

Presentar los 499.000 pesos como logro del modelo sería atribuirle un mérito que
no tiene. Por sí solo aporta 49.000, un 10 %.

**La interacción es el segundo componente y merece atención.** Los 145.000 pesos
que no son ni regla ni modelo salen de que el modelo, además de acertar el
centro, gradúa el ancho del abanico por serie. Ese efecto solo aparece cuando se combinan los dos factores, y
es lo que justifica haber elegido una regresión cuantílica en lugar de un modelo
puntual.

## 4. Solo dos de las cuatro comparaciones son significativas

| Comparación | Ahorro | Banda 95 % | ¿Significativo? |
|---|---|---|---|
| P4 frente a P0 | 1.960.844 | 1.325.913 a 2.598.960 | **Sí** |
| P4 frente a P1 | 499.457 | 87.470 a 963.945 | **Sí** |
| P4 frente a P3 | 193.772 | −17.437 a 422.048 | No |
| P3 frente a P1 | 305.685 | −37.446 a 681.407 | No |

**Lo que se puede afirmar.** Que la propuesta completa mejora la práctica actual
y mejora pedir el centro. Las dos bandas excluyen el cero.

**Lo que no se puede afirmar.** Que el modelo aporte por encima de la regla
ingenua, ni que la regla aporte por sí sola. Sus bandas cruzan el cero.

Esto hay que decirlo tal cual en la presentación. Con 160 series y tres semanas
no hay potencia para separar efectos de ese tamaño, y presentar la
descomposición del apartado 3 como si estuviera demostrada sería excederse. La
descomposición indica de dónde parece venir el ahorro; la significación solo
alcanza para el total.

## 5. El supuesto de coste cambia el resultado por completo

| Escenario | Coste P1 | Coste P4 | Ahorro | Ahorro % |
|---|---|---|---|---|
| Sin merma | 6.025.518 | 448.551 | 5.576.966 | **92,6 %** |
| Merma parcial | 7.793.518 | 6.051.554 | 1.741.964 | 22,4 % |
| Con merma | 9.561.518 | 9.062.061 | 499.457 | 5,2 % |

Es el resultado más incómodo del paso y hay que presentarlo sin maquillar.

**Con el supuesto del enunciado, el ahorro sería del 92 %.** Con el que
recomendamos, del 5 %. Son dos órdenes de magnitud distintos a partir de los
mismos datos, el mismo modelo y las mismas predicciones.

**Por qué pasa.** Cuando el sobrante casi no cuesta, pedir de más es casi gratis
y la política de nivel arrasa. Cuando el sobrante cuesta 810 pesos por unidad,
protegerse sale caro y el margen de mejora se estrecha.

**Consecuencia para la presentación.** Una cifra de ahorro sin declarar el
supuesto de merma no significa nada. Lo honesto es llevar la tabla completa y
recomendar el escenario con merma, que da la cifra más baja de las tres. Llevar
solo el 92 % sería vender un número que depende de suponer que el café sobrante
se vende al día siguiente.

## 6. La extrapolación anual, con su advertencia

| | |
|---|---|
| Ahorro medido en 3 semanas | 499.457 |
| Por semana | 166.486 |
| Extrapolado a 52 semanas | **8.657.250** |

Es una extrapolación lineal desde tres semanas de veinte tiendas. Da orden de
magnitud, no un compromiso. Y como el ahorro total del que parte no es
significativo en todas sus componentes, la banda de esa cifra anual sería muy
ancha.

La forma correcta de presentarla es como hipótesis que un piloto convierte en
cifra, midiendo faltante y merma reales en un grupo reducido de tiendas.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Presentar la descomposición: 61 % regla, 29 % interacción, 10 % modelo | Presentación |
| 2 | Declarar que solo el ahorro total es estadísticamente significativo | Presentación |
| 3 | Llevar los tres escenarios de coste, recomendando el más conservador | Presentación |
| 4 | Presentar el ahorro anual como hipótesis, nunca como compromiso | Presentación |
| 5 | Usar la interacción para justificar el modelo cuantílico frente a uno puntual | Presentación |
| 6 | Proponer un piloto que mida faltante y merma reales | Próximos pasos |
