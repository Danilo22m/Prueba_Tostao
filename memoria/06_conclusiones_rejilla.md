# Conclusiones del entrenamiento de la rejilla

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/06_rejilla_niveles.txt` y de las figuras 16 y 17.

Se entrenan 17 regresiones cuantílicas en parametrización relativa, una por cada
nivel de servicio que pidieron los costes, reutilizando el alfa optimizado en el
nivel de operación.

Las cifras comparativas de la parametrización absoluta se reproducen cambiando
la constante `FAMILIA` del script correspondiente. Ver `T1_parametrizacion_relativa.md`.

---

## 1. La calibración es buena en todo el rango

Cobertura empírica frente al nivel prometido, sobre las 480 decisiones de prueba:

| Nivel | Cobertura | Desvío | Unidades medias |
|---|---|---|---|
| 0,50 | 0,502 | +0,002 | 92,9 |
| 0,59 | 0,610 | +0,020 | 96,2 |
| 0,65 | 0,660 | +0,010 | 98,0 |
| 0,68 | 0,685 | +0,005 | 99,2 |
| 0,74 | 0,719 | −0,021 | 101,0 |
| 0,81 | 0,785 | −0,025 | 104,5 |
| 0,90 | 0,862 | −0,037 | 109,1 |
| 0,98 | 0,992 | +0,012 | 124,4 |
| 0,99 | 0,994 | +0,004 | 126,9 |

El desvío medio es de −0,005 y el peor caso de 0,037, en el nivel 0,90. En la
figura 17 los puntos abrazan la diagonal. Ocho de los diecisiete se quedan
ligeramente cortos, todos entre el 0,72 y el 0,90, que son niveles que la
política recomendada no opera.

**Qué significa.** Cuando la política promete cubrir el 68 % de las semanas, se
cubre el 68,5 %. El nivel de servicio que se le ofrece a negocio es real y no una
etiqueta.

## 2. El nivel 0,99 ya es utilizable

Era el hallazgo pendiente cuando el modelo trabajaba en unidades absolutas: el
nivel extremo pedía más del doble de la demanda media y era el peor estimado de
toda la rejilla.

| | Parametrización absoluta | Relativa |
|---|---|---|
| Unidades medias en el nivel 0,99 | 208,5 | **126,9** |
| Veces la demanda media | 2,24 | **1,38** |
| Cobertura | 0,988 | 0,994 |

**Por qué se arregló.** Estimar el percentil 99 de una proporción es mucho más
fácil que estimarlo en unidades, porque todas las series contribuyen a la misma
distribución en vez de una por serie. La cola deja de apoyarse en las seis o
siete observaciones más altas del panel.

**Consecuencia.** Se retira el argumento que se había construido contra el
escenario de coste sin merma por inestabilidad del nivel extremo. Ese escenario
sigue siendo poco realista para una cafetería, pero ya no se le puede reprochar
que obligue a operar donde el modelo peor estima.

## 3. Los cruces son muchos pero inofensivos

Se detectaron 413 cruces sobre 480 filas y 16 pares consecutivos de niveles. Cada
nivel se ajusta por separado, así que nada garantiza que salgan ordenados.

| Par | Cruces | Cruce máximo |
|---|---|---|
| 0,79 → 0,80 | 84 | 0,93 unidades |
| 0,64 → 0,65 | 83 | 0,65 unidades |
| 0,66 → 0,67 | 82 | 0,74 unidades |
| 0,65 → 0,66 | 58 | 0,08 unidades |
| 0,98 → 0,99 | 6 | 0,27 unidades |

**La magnitud es lo que importa, no el recuento.** El cruce máximo de toda la
rejilla es de 0,93 unidades, frente a 44,08 en la versión absoluta. Ocurren entre
niveles casi idénticos, como 0,64 y 0,65, donde los dos modelos estiman
prácticamente lo mismo y la diferencia es ruido numérico sin consecuencia
operativa.

La corrección es ordenar los valores de cada fila. No cambia el conjunto de
cantidades estimadas, solo su asignación a niveles, y garantiza que pedir con más
protección nunca devuelva menos unidades. Tras ordenar no queda ningún cruce.

## 4. El pedido frente a la venta real, serie a serie

La figura 16 dibuja, para cuatro series, el pronóstico central, el pedido al
nivel de servicio del producto en el escenario con merma, y la venta real de
las tres semanas de prueba. La franja entre las dos líneas es el colchón.

Las cuatro series no se eligen a mano. Se ordenan las 160 por la pérdida
pinball en su nivel de operación, relativa a la demanda media de cada una, y se
muestran tres de las mejor cubiertas y la peor. El título de la figura lo
declara, para que nadie lea las tres buenas como si fueran representativas.

**Lo que se ve en las tres buenas.** La venta real se mueve alrededor del
pronóstico central y el pedido la cubre casi siempre, con un sobrante pequeño.
El colchón es distinto en cada una: unas 10 unidades en una serie de 180 y unas
4 en una de 60. El nivel es el mismo, la cantidad que representa la decide la
historia de cada serie.

**Lo que se ve en la peor.** Es STORE_09 con Café con Leche, la misma que el
diagnóstico señala como la de mayor error de las 160. El modelo pronostica
unas 45 unidades y se venden unas 30: pide de más las tres semanas. No es un
fallo del abanico, es una serie donde el nivel reciente no describe lo que
está pasando, y va a la lista de las once que hay que revisar antes del piloto.

**Por qué esta figura y no una de intervalos.** Una versión anterior dibujaba
la franja del nivel 0,50 al 0,99, y se leía como intervalo de confianza sin
serlo: por construcción la venta real cae bajo el centro la mitad de las
semanas, y la figura parecía fallar cuando no fallaba. La franja actual va del
centro al pedido, que es la lectura de negocio: si la venta queda bajo la línea
discontinua, la tienda cubrió la demanda; si la supera, hubo faltante.

## 5. Sobre reutilizar el alfa en toda la rejilla

El alfa se optimizó en el nivel 0,65 y se reutiliza en los 17. La alternativa
sería reoptimizar en cada nivel, y no se hizo por dos motivos.

Con 960 filas de entrenamiento y tres pliegues de validación, 17 búsquedas
independientes se ajustarían al ruido de la validación más de lo que mejorarían
el resultado.

Y la calibración obtenida es buena en todo el rango, incluidos los extremos, así
que no hay evidencia de que el alfa elegido se quede corto donde más difícil es
estimar. A diferencia de la versión absoluta, el nivel 0,99 ya no es una
excepción.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Ordenar los valores de cada fila para forzar niveles monótonos | Optimizador |
| 2 | El nivel 0,99 pasa a ser utilizable, con 1,38 veces la demanda media | Presentación |
| 3 | Reutilizar el alfa en toda la rejilla, con la calibración como justificación | Memoria técnica |
| 4 | Declarar que los cruces son de menos de una unidad | Memoria técnica |
| 5 | El abanico de prueba queda guardado como artefacto auditable | Optimizador |
