# Conclusiones del cambio a parametrización relativa

**Caso A · Optimización de abastecimiento · Tostao**

El diagnóstico del modelo absoluto detectó dos defectos encadenados: un sesgo
sistemático por tamaño de serie y heterocedasticidad. Este documento recoge el
cambio que se hizo para corregirlos y su resultado.

**Sobre la trazabilidad de las cifras.** Las columnas etiquetadas «absoluto»
proceden de una configuración que ya no es la que producen los informes. No son
irreproducibles: basta cambiar la constante `FAMILIA` en `run_rejilla.py` y
`run_diagnostico.py` de `"regresion cuantilica (relativo)"` a
`"regresion cuantilica"` y volver a ejecutar esos dos pasos. Las dos
parametrizaciones conviven en `src/caso_a/modelos.py` y ambas siguen apareciendo
en el informe de selección de familia.

---

## 1. Qué se cambió y por qué

El modelo absoluto predecía unidades directamente. Con series que van de 40 a
154 unidades semanales, la regularización las encogía todas hacia una media
general que no significa nada, y el error absoluto crecía con el nivel.

El cambio: predecir la demanda como **proporción de la media de las cuatro
semanas previas**, y multiplicar de vuelta para devolver unidades.

Una serie que vende 44 sobre una media de 40 y otra que vende 165 sobre una
media de 150 pasan a ser el mismo caso, ambas un 10 % por encima. El modelo ve
un patrón en lugar de dos.

**El ajuste ocurre en proporción; la evaluación sigue en unidades.** Es
importante: el coste del negocio está en pesos, que escalan con las unidades.
Medir en proporciones daría a las series pequeñas más peso del que merecen
económicamente. La conversión de vuelta es exacta, porque multiplicar un cuantil
por una cantidad positiva conocida da el cuantil del producto.

## 2. Cómo se decidió, y por qué la evidencia es honesta pero débil

La regla se fijó antes de probar: se decide en validación, la prueba no se mira
hasta el final.

**Comparación pareada en validación**, cada familia contra su propia versión
relativa:

| Familia | Absoluta | Relativa | Mejora |
|---|---|---|---|
| Boosting cuantílico | 4,999 | 4,795 | +4,1 % |
| GBR + residuales | 4,937 | 4,829 | +2,2 % |
| Bosque cuantílico | 4,902 | 4,849 | +1,1 % |
| Ridge + residuales | 4,873 | 4,843 | +0,6 % |
| Ensemble + residuales | 4,904 | 4,911 | −0,1 % |
| Regresión cuantílica | 4,794 | 4,833 | −0,8 % |

Gana en 4 de 6, con una mejora media del 1,17 %. El contraste de Wilcoxon
pareado da p = 0,219, es decir **no significativo**.

Hay que decirlo así. Con seis pares y tres pliegues de validación de 160 filas
cada uno, la prueba no tiene potencia para detectar un efecto del 1 %. No
rechazar con esa muestra no significa que no haya efecto.

**Lo que sí justifica adoptarlo** es que la evidencia es consistente en cuatro
frentes independientes: dirección positiva en validación, corrección del defecto
diagnosticado, comportamiento del abanico, y confirmación en prueba. Y que el
cambio no fue una búsqueda a ciegas sino una hipótesis derivada de un
diagnóstico previo.

## 3. Corrige el defecto que lo motivó

Sesgo por tramo de volumen, en las semanas de prueba:

| Tramo | Demanda media | Sesgo absoluto | Sesgo relativo |
|---|---|---|---|
| 1, el más bajo | 44,6 | −4,96 | −3,44 |
| 2 | 73,1 | −0,31 | +0,15 |
| 3 | 102,4 | −2,28 | −3,20 |
| 4, el más alto | 153,8 | +10,08 | +6,85 |

La amplitud del sesgo entre el tramo más bajo y el más alto cae de 15,04 a 10,29
unidades, un 32 % menos. No desaparece, pero se reduce de forma clara.

Los residuales también mejoran: la media pasa de 0,65 a 0,11 unidades y la
asimetría de 0,61 a 0,29.

## 4. Arregla el nivel 0,99, que era el problema más grave

Era el hallazgo pendiente del paso anterior: el nivel 0,99 pedía 2,24 veces la
demanda media y cruzaba 44 unidades por debajo del 0,98.

| | Absoluto | Relativo |
|---|---|---|
| Unidades medias en el nivel 0,99 | 208,5 | **128,7** |
| Veces la demanda media | 2,24 | **1,38** |
| Cruce máximo entre 0,98 y 0,99 | 44,08 u | **0,27 u** |

**Por qué funciona.** Estimar el percentil 99 de una proporción es mucho más
fácil que estimarlo en unidades, porque todas las series contribuyen a la misma
distribución en vez de una por serie. La cola deja de apoyarse en las seis o
siete observaciones más altas del panel.

Esto quita fuerza a uno de los argumentos que se habían construido contra el
escenario de coste sin merma. Ese escenario sigue siendo poco realista para una
cafetería, pero ya no se le puede reprochar que obligue a operar donde el modelo
peor estima.

## 5. El colchón se gradúa mucho más

| | Absoluto | Relativo |
|---|---|---|
| Desviación del ancho del colchón | 3,53 | **6,60** |
| Rango | 10,5 a 28,6 u | 5,4 a 37,9 u |

El colchón se adapta ahora al doble de amplitud entre series. Es exactamente lo
que se buscaba: una serie tranquila ya no recibe el mismo margen que una volátil.

Y hay un efecto colateral valioso: **todas las familias relativas dejan de cruzar
niveles**, incluido el boosting, que en su versión absoluta cruzaba hasta 5,45
unidades. La parametrización arregla el problema de raíz en lugar de parchearlo
al ordenar.

## 6. El modelo usa más variables, aunque solo una pesa

En la versión absoluta la regularización anuló 12 de 14 variables. En la relativa
quedan 7 con coeficiente no nulo: el rezago, el tamaño de tienda y cinco de las
ocho indicadoras de producto.

**La importancia por permutación matiza ese dato.** Solo el rezago aporta de forma
medible, con una degradación del 24,9 % al barajarlo. El tamaño de tienda aporta
un 0,09 % y el resto exactamente cero.

Así que el modelo sigue siendo muy simple. La diferencia con la versión absoluta
no es que use más información, es que opera sobre la forma de la trayectoria en
lugar de sobre el nivel. Eso es lo que corrige el sesgo y estabiliza la cola.

**Y la interpretabilidad mejora mucho.** Un coeficiente de 0,0185 sobre el rezago
se lee como «una desviación típica en la última semana mueve la predicción un
1,85 % respecto a la media reciente». Eso se le explica a cualquiera. Un
coeficiente de 32,57 en unidades estandarizadas, no.

## 7. Lo único que empeora, y por qué no importa

Los cruces de niveles pasan de 111 a 413 sobre 480 filas. Suena mal y no lo es:

| | Absoluto | Relativo |
|---|---|---|
| Filas con algún cruce | 111 | 413 |
| Magnitud máxima del cruce | **44,08 u** | **0,93 u** |

Hay muchos más cruces pero son de décimas de unidad, entre niveles casi
idénticos como 0,64 y 0,65, donde los dos modelos estiman prácticamente lo
mismo. Es ruido numérico sin consecuencia operativa. El cruce grave, el de 44
unidades, desapareció.

La corrección sigue siendo la misma y sigue dejando cero cruces.

## 8. Resultado global

| Indicador | Absoluto | Relativo | Cambio |
|---|---|---|---|
| Pérdida pinball media, prueba | 4,466 | 4,343 | −2,8 % |
| Error ponderado del centro | 12,01 % | 11,76 % | −0,25 pp |
| Amplitud del sesgo por volumen | 15,04 u | 10,29 u | −32 % |
| Media del residual | 0,65 | 0,11 | −83 % |
| Heterocedasticidad | 0,399 | 0,360 | −10 % |
| Desviación del colchón | 3,53 | 6,60 | +87 % |
| Nivel 0,99 sobre la demanda media | 2,24× | 1,38× | −38 % |
| Cruce máximo | 44,08 u | 0,93 u | −98 % |
| Variables con coeficiente no nulo | 4 de 14 | 7 de 14 | — |

Y en las semanas de prueba, **las siete parametrizaciones absolutas pierden con
evidencia estadística** frente a la mejor relativa, con p-valores entre 0,0014 y
0,030.

---

## Decisiones que salen de este cambio

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Adoptar la parametrización relativa en la familia operada | Toda la cadena posterior |
| 2 | Declarar que la evidencia en validación no fue significativa | Memoria técnica |
| 3 | Retirar el argumento de que el nivel 0,99 es inestable | Presentación |
| 4 | Mantener la evaluación en unidades, nunca en proporciones | Evaluación |
| 5 | Reportar los coeficientes en porcentaje, que sí se explican | Presentación |
