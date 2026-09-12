# Conclusiones sobre variables y líneas base

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/03_variables_y_lineas_base.txt` y de las figuras 09
y 10. El informe describe; este documento interpreta.

---

## 1. El diseño experimental queda congelado

| Periodo | Semanas | Filas | Uso |
|---|---|---|---|
| Historia consumida por los rezagos | 1 a 4 | — | No genera filas utilizables |
| Entrenamiento | 5 a 10 | 960 | El modelo aprende aquí |
| Prueba | 11 a 13 | 480 | Intacta hasta el final |
| Predicción | 14 | 160 | Se entrega, sin observación real |

Dentro de entrenamiento, tres pliegues de ventana expansiva: ajusta con 5-7 y
valida 8, luego 5-8 y valida 9, luego 5-9 y valida 10.

**Limitación declarada.** El análisis univariado previo se hizo sobre las trece
semanas completas, incluidas las de prueba. Es una forma leve de espiar el
resultado. A partir de aquí toda decisión usa solo entrenamiento, y esta
limitación queda escrita en la memoria técnica en lugar de disimularse.

## 2. Las variables no filtran información del futuro

Trece variables construidas: cuatro rezagos, tres medias móviles, tres
desviaciones móviles, pendiente, razón contra la media y coeficiente de
variación reciente.

La prueba antifuga reconstruye todas las variables ocultando lo posterior al
corte y exige que las filas anteriores salgan idénticas. Pasa. Es una prueba
automática, no una revisión visual, y se ejecuta en cada corrida.

## 3. Las correlaciones marginales engañan, y era previsible

| Variable | Spearman marginal | Spearman intra-serie |
|---|---|---|
| media_3 | 0,947 | −0,094 |
| media_4 | 0,947 | −0,098 |
| rezago_1 | 0,931 | −0,017 |
| pendiente | 0,097 | −0,011 |

Todas las variables de historia correlacionan por encima de 0,90 con el
objetivo. Eso no significa que predigan: significa que reflejan el nivel de cada
serie, que es el 90 % de la varianza ya identificado en el univariado.

Al restar la media de cada serie, todas caen a cero. Ninguna llega a 0,10.

**Cautela metodológica.** Centrar dentro de grupos con solo seis observaciones
introduce un sesgo negativo conocido, del orden de 1/(T−1), que aquí ronda −0,2.
Los valores intra-serie se leen como orientativos. La conclusión firme viene del
apartado siguiente, que es una evaluación fuera de muestra y no tiene ese sesgo.

## 4. Las medias móviles y los rezagos son linealmente dependientes

| Variable | R² contra el resto | VIF |
|---|---|---|
| rezago_1 a rezago_4, media_2 a media_4, pendiente | 1,00 | infinito |
| desv_4 | 0,88 | 8,6 |
| tamano_m2 | 0,38 | 1,6 |

No es un problema de datos, es aritmética: `media_2` es exactamente la semisuma
de `rezago_1` y `rezago_2`, y la pendiente por mínimos cuadrados sobre cuatro
puntos es una combinación lineal fija de esos cuatro rezagos. Las ocho variables
ocupan un espacio de dimensión cuatro.

**Consecuencia.** Un modelo lineal no puede recibir rezagos y medias móviles a
la vez: hay que elegir un conjunto. Los modelos de árboles son indiferentes,
porque parten de una variable cada vez, pero incluir las ocho solo diluye la
importancia sin añadir información.

## 5. La línea base es la media móvil de 4 semanas

Resultado sobre las semanas de prueba, que el diseño no ha tocado:

| Línea base | WAPE | MAE | R² | Sesgo |
|---|---|---|---|---|
| Media móvil 4 | **11,91 %** | 11,11 | 0,899 | +0,48 |
| Persistencia | 13,40 % | 12,50 | 0,876 | +0,45 |
| Media histórica | 13,99 % | 13,05 | 0,856 | +1,23 |
| Deriva | 15,51 % | 14,47 | 0,833 | +0,50 |

**Rectifico lo que te dije tras el univariado.** Propuse la media histórica de la
serie como referencia, y no es la mejor. La media expansiva arrastra las semanas
1 a 4, que a estas alturas están desfasadas, y por eso pierde contra la
persistencia en prueba aunque gane en entrenamiento. La ventana corta rastrea el
nivel sin quedarse anclada al pasado remoto.

El barrido de longitudes, en la figura 10, se evalúa **sobre las semanas de
validación 8 a 10, no sobre las de prueba**. Elegir la ventana mirando la prueba
sería ajustar un parámetro contra el conjunto que debe quedar intacto.

La curva tiene forma de U con mínimo en 4 y 5, empatadas en 11,28 % sobre
validación, y un tramo plano entre 3 y 5. Por debajo entra ruido, por encima
entra historia desfasada.

**El listón queda fijado en WAPE 11,91 % y R² 0,899**, medido sobre prueba con la
ventana elegida en validación. Cualquier modelo se mide contra ese número.

Una nota metodológica que conviene declarar: en una primera versión este barrido
se hizo sobre las semanas de prueba y elegía una ventana de 3, con 11,87 %. Esa
cifra estaba inflada porque el parámetro se había ajustado contra el propio
conjunto de evaluación. Corregido el procedimiento, la ventana pasa a 4 y el
listón sube cuatro centésimas.

## 6. La deriva es la peor línea base, y eso es un hallazgo

Añadir la pendiente estimada empeora el error un 30 % respecto a la media móvil.
Es el resultado más informativo del paso.

En el univariado medí que una recta ajustada a las trece semanas explica el 35 %
de la variación intra-serie. Eso es **ajuste dentro de muestra**: se traza la
recta sabiendo ya toda la serie. Fuera de muestra, estimando la pendiente con
cuatro semanas y proyectándola una hacia adelante, la pendiente es casi todo
ruido y arrastra la predicción en la dirección equivocada.

**Consecuencia.** Hay que rebajar la expectativa que yo mismo había puesto. Dije
que el trabajo del modelo era capturar la tendencia de cada serie. Lo sigue
siendo, pero la evidencia dice que con trece semanas y esta relación
señal-ruido, la tendencia no se puede estimar de forma fiable por serie
aisladamente.

Si un modelo global va a superar el listón, será porque aprende la tendencia
apoyándose en las 160 series a la vez, no porque ajuste mejor cada una por
separado. Y el margen disponible es estrecho.

## 7. Qué esperar del modelo

| Referencia | WAPE en prueba |
|---|---|
| Media móvil 4, la línea base | 11,91 % |
| Mejora del 5 % relativo sobre ella | 11,31 % |
| Mejora del 10 % relativo | 10,72 % |

Una mejora del 5 al 10 % relativo sería un buen resultado y hay que presentarlo
como tal. Una mejora muy superior debe hacer sospechar de fuga de información
antes que celebrarse.

Y conviene repetir el argumento central: el valor del proyecto no depende de
ganar esa carrera. Depende de la política de pedido, que convierte cualquier
pronóstico razonable en la cantidad correcta según los costes.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Partición congelada: 5-10 entrenamiento, 11-13 prueba, 14 predicción | Todo lo posterior |
| 2 | Línea base oficial: media móvil de 4 semanas, WAPE 11,91 % | Evaluación |
| 3 | No pasar rezagos y medias móviles juntos a un modelo lineal | Selección de variables |
| 4 | Mantener la pendiente como variable, pero sin esperar mucho de ella | Ingeniería de variables |
| 5 | Prueba antifuga automática en cada corrida | Calidad de código |
| 6 | Declarar que el univariado se hizo sobre las trece semanas | Memoria técnica |
| 7 | Anunciar una mejora esperada del 5 al 10 % relativo, no más | Presentación |
