# Conclusiones del análisis univariado

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de los hechos recogidos en `salidas/informes/02_univariado.txt` y en las
ocho figuras de `salidas/figuras/`. El informe describe; este documento
interpreta. Cada conclusión cita el dato que la sostiene.

---

## 1. El objetivo se modela en niveles, sin transformar

Al pasar de granularidad diaria a semanal, la variable cambia de carácter:

| Estadístico | Diario | Semanal |
|---|---|---|
| Media | 13,2 | 92,2 |
| Coeficiente de variación | 0,591 | 0,449 |
| Asimetría | 1,020 | 0,673 |
| Curtosis | 1,219 | 0,334 |
| Mínimo | 0 | 14 |
| Ceros | 26 | 0 |
| Atípicos robustos | 127 | 3 de 2.080 |

**Decisión.** Se regresa en niveles. No hace falta transformación logarítmica, ni
modelos de conteo tipo Poisson o binomial negativa, ni tratamiento de atípicos.
La figura `01_distribucion_semanal.png` lo muestra: una campana con cola derecha
corta y sin masa pegada al cero.

Conviene dejar constancia de que la decisión se tomó sobre el objetivo semanal y
no sobre el diario. En diario, con asimetría 1,02 y ceros presentes, un modelo de
conteo habría sido defendible.

## 2. La demanda registrada no está censurada

Los 26 días sin venta representan el 0,18 % de los 14.560 registros y se
concentran en 14 series, con un máximo de 7 días en una sola.

**Lectura.** Es baja rotación de productos concretos en tiendas concretas, no
quiebres de stock. Si fueran quiebres, las ventas registradas subestimarían la
demanda real y toda la simulación de costes quedaría sesgada.

**Consecuencia.** La simulación de la política puede tratar las ventas históricas
como demanda real. Es un argumento que hay que declarar explícitamente en la
presentación, porque es el supuesto que sostiene la cifra de ahorro.

## 3. Agregar a semana es correcto y además elimina ruido

El ciclo dentro de la semana es fuerte y regular:

| Días | Índice sobre la media |
|---|---|
| Viernes, sábado, domingo | 1,25 · 1,23 · 1,24 |
| Lunes a jueves | 0,83 · 0,83 · 0,81 · 0,82 |

Amplitud de 1,54 veces entre el día más alto y el más bajo. Es la señal dominante
del dato diario.

**Lectura.** El periodo va del lunes 1 de enero al domingo 31 de marzo de 2024,
trece semanas completas. Cada semana contiene exactamente un día de cada tipo, así
que al sumar el ciclo se anula por construcción.

**Consecuencia.** La agregación semanal no pierde señal útil y retira una fuente
de variación grande. Además no hay semanas parciales que descartar.

## 4. No queda memoria de una semana a la siguiente

Es el hallazgo más importante del análisis. La figura `03_autocorrelacion.png` lo
resume en dos paneles.

| Nivel | Rezagos significativos | Rezago 1 | Banda |
|---|---|---|---|
| Diario | 7, 14, 21 | 0,153 | ±0,205 |
| Semanal | ninguno | 0,101 | ±0,544 |

Los rezagos diarios significativos son múltiplos de siete: no reflejan memoria de
la serie, son el mismo ciclo de fin de semana visto de otra forma. Una vez
agregado a semana, no queda estructura temporal.

**Consecuencia 1 — cambia la línea base.** Pedir lo mismo que la semana pasada
descarta doce semanas de historia para quedarse con un dato cuya correlación con
el objetivo es 0,101. Es un rival débil, y escalar las métricas contra él haría
que el modelo pareciese mejor de lo que es. La referencia honesta es la media de
cada serie.

**Consecuencia 2 — cambia el conjunto de variables.** El rezago de una semana
será flojo. Lo que hay que construir son medias móviles de tres o cuatro semanas,
que promedian el ruido, y la pendiente reciente, que mide la dirección.

## 5. El techo de lo predecible, y por qué el R² no sirve

Descomposición de la varianza del objetivo semanal:

| Fuente | Peso | Naturaleza |
|---|---|---|
| Diferencias entre series | 90,0 % | Fija: unas combinaciones venden más que otras |
| Tendencia de cada serie | 3,6 % | Predecible: es el trabajo del modelo |
| Ruido | 6,5 % | Irrecuperable |

Traducido a capacidad de ajuste, dentro de muestra:

| Qué se predice | R² | Qué hace falta |
|---|---|---|
| El mismo número para todo | 0,000 | Nada |
| La media de cada serie | 0,900 | Una tabla de 160 medias |
| La media más la recta | 0,935 | Una recta por serie |

**Consecuencia 1.** El R² queda descartado como métrica principal. Un modelo que
reporte 0,88 estaría por debajo de una tabla de medias construida en una hoja de
cálculo. Si se enseña, va con la advertencia al lado. Las métricas que informan
son el error porcentual ponderado y el error escalado contra la media de la serie.

**Consecuencia 2.** El objetivo del modelo es capturar la tendencia de cada serie.
Todo lo demás ya está resuelto por la identidad de la serie.

**Consecuencia 3.** Sirve de control de sanidad. Si en pasos posteriores aparece
una mejora muy grande sobre la línea base, lo primero que hay que buscar es una
fuga de información.

La figura `04_descomposicion_varianza.png` comunica esto sin necesidad de
explicación verbal.

## 6. Donde hay poca varianza hay mucho dinero

| Grupo | Series | Rango de cambio en 13 semanas |
|---|---|---|
| Crecen más de 20 % | 36 | hasta +61 % |
| Planas, entre −5 y +5 % | 33 | — |
| Caen más de 20 % | 33 | hasta −55 % |

69 de las 160 series se mueven más de un 20 % en trece semanas, y las subidas
compensan a las bajadas, así que no hay deriva global que aprovechar.

**Lectura de negocio.** En esas 69 series, quien pide mirando el histórico se
queda corto en las que suben y acumula merma en las que bajan. Ese 3,6 % de
varianza que el R² apenas registra es exactamente donde está el caso de negocio.

La figura `05_tendencias_por_serie.png` es la que hay que llevar a la
presentación para justificar por qué el proyecto tiene sentido.

## 7. Las variables de contexto

**La superficie de la tienda casi determina su demanda.** Correlación de Pearson
0,976, es decir un R² de 0,953, con Spearman 0,971. Los veinte puntos caen
prácticamente sobre la recta en `07_tamano_vs_demanda.png`.

Entra como variable estática. Tiene además un valor operativo: permite estimar la
demanda de una tienda nueva sin historial propio.

**La ciudad no aporta nada.** Sobre el residuo del tamaño, el contraste de
Kruskal-Wallis da p = 0,643. Bogotá y Medellín se solapan sobre la misma recta. Y
con una sola tienda en Cali, cualquier conclusión por ciudad sería indefendible.
Se excluye.

**Precio y coste unitario se quedan fuera del modelo.** Solo toman cinco valores
distintos para ocho productos, así que ni siquiera identifican al SKU. Toda su
información ya está contenida en la identidad del producto. Su sitio es la capa
de costes, no la matriz de entrada.

**La codificación por frecuencia es inservible en producto y tienda.** El diseño
está balanceado por construcción: 1.820 filas diarias por producto y 728 por
tienda, sin una sola de diferencia. Codificar por frecuencia devolvería una
constante y borraría la señal. Hay que usar variables indicadoras. Solo `ciudad`
está desbalanceada, y es precisamente la variable que se descarta.

## 8. Los niveles de servicio solo se separan con merma

| Producto | Margen | Nivel sin merma | Nivel con merma |
|---|---|---|---|
| Tinto | 68,0 % | 0,994 | 0,677 |
| Buñuelo | 68,0 % | 0,988 | 0,675 |
| Cappuccino | 66,7 % | 0,995 | 0,664 |
| Café con Leche | 65,7 % | 0,994 | 0,654 |
| Croissant | 65,7 % | 0,989 | 0,652 |
| Pan de Bono | 64,3 % | 0,989 | 0,638 |
| Jugo de Naranja | 60,0 % | 0,984 | 0,594 |
| Pastel de Pollo | 57,1 % | 0,985 | 0,567 |

Con el coste de sobrante del enunciado, que solo cuenta almacenamiento, los ocho
productos quedan entre 0,984 y 0,995. Son indistinguibles.

Añadiendo merma, es decir suponiendo que el producto fresco no vendido se
descarta, los niveles se abren de 0,567 a 0,677 y quedan ordenados por margen.

**Consecuencia.** El enunciado pide proponer cómo usar la incertidumbre junto con
los márgenes para decidir si el pedido debe ser agresivo o conservador. Sin el
escenario de merma esa pregunta no tiene respuesta, porque no hay diferenciación
que mostrar. Los dos escenarios van completos en la presentación, con una
recomendación explícita.

## 9. Las etiquetas de tendencia no describen lo que hacen las series

El fichero `ground_truth_trends.csv` clasifica cada serie en cuatro patrones. El
comportamiento observado no se corresponde con esa clasificación:

| Patrón | Series | Cambio mediano | Cambio medio | Desviación |
|---|---|---|---|---|
| down | 44 | −1,0 % | −0,4 % | 29,4 |
| seasonal | 57 | −2,5 % | −1,3 % | 22,6 |
| random | 32 | +2,8 % | +2,8 % | 21,8 |
| up | 27 | +3,5 % | +7,4 % | 25,8 |

Contraste de Kruskal-Wallis: H = 2,63, p = 0,453. La razón de correlación es
0,016, es decir la etiqueta explica el 1,6 % de la variación en la tendencia
observada. El resultado se repite calculando las pendientes sobre datos diarios,
con p = 0,418.

La figura `08_patrones_ejemplo.png` lo ilustra: el panel etiquetado «up» tiene la
recta ajustada descendente.

**Consecuencia.** El fichero sigue excluido del modelo, como estaba previsto,
porque describe el proceso generador durante todo el periodo e incluiría
información de las semanas de prueba. Pero su valor como herramienta de
diagnóstico es mucho menor de lo esperado: desglosar el error por tipo de patrón
no va a discriminar nada. Merece una línea en la memoria técnica indicando que se
comprobó y no separa.

---

## Resumen de decisiones que salen de este análisis

| # | Decisión | Afecta al paso |
|---|---|---|
| 1 | Modelar en niveles, sin transformar ni tratar atípicos | Modelado |
| 2 | Tratar las ventas como demanda real, sin censura | Simulación de costes |
| 3 | Agregar a semana, sin semanas parciales que descartar | Construcción del panel |
| 4 | Línea base: media de la serie, no persistencia | Líneas base |
| 5 | Variables: medias móviles y pendiente, no rezago 1 | Ingeniería de variables |
| 6 | Codificar producto y tienda con indicadoras, no por frecuencia | Ingeniería de variables |
| 7 | Excluir ciudad, precio y coste unitario del modelo | Selección de variables |
| 8 | Incluir superficie de tienda como variable estática | Selección de variables |
| 9 | Reportar error ponderado y escalado; el R² solo con advertencia | Evaluación |
| 10 | Presentar los dos escenarios de coste, con y sin merma | Optimización |
