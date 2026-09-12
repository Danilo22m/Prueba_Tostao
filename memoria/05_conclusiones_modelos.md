# Conclusiones de la selección de familia

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/05_seleccion_familia.txt` y de las figuras 13 a 15.

Se comparan siete familias. Las marcadas `[puntual]` solo estiman la media
condicional; las demás estiman directamente un nivel de servicio.

---

## 1. Cómo se hizo justa la comparación

Cuatro decisiones de método, tomadas antes de mirar resultados.

**Los modelos puntuales compiten en la misma métrica.** Ridge, el boosting
ordinario, su combinación y la media móvil minimizan el error al cuadrado o
promedian, así que solo estiman el centro. Para que entren en una métrica
distribucional se les suma el cuantil empírico de sus propios residuales de
entrenamiento. Sin eso, cualquier modelo probabilístico habría ganado por
defecto y no por mérito.

**Se compara en el nivel que se va a operar**, el 0,65, no en la mediana. La
decisión de pedido no usa la mediana.

**Todas las familias se ajustan con la misma búsqueda.** Optimización bayesiana,
30 ensayos por familia, minimizando la pérdida pinball sobre los pliegues de
validación. El espacio de búsqueda se mantuvo estrecho a propósito: con 960 filas
y tres pliegues, el riesgo no es quedarse corto de búsqueda sino ajustarse al
ruido de la validación.

**Se contrasta si las diferencias son reales**, con Diebold-Mariano sobre la
pérdida observación a observación y bandas de confianza remuestreando series
completas.

## 2. Resultado: tres familias empatan y cuatro pierden

Pérdida pinball media sobre las semanas de prueba:

| Familia | 0,50 | 0,65 | 0,90 | Media |
|---|---|---|---|---|
| Regresión cuantílica | 5,599 | 5,251 | 2,547 | **4,466** |
| Ridge + residuales `[puntual]` | 5,494 | 5,279 | 2,719 | 4,497 |
| Media móvil + residuales | 5,563 | 5,319 | 2,741 | 4,541 |
| Ensemble + residuales `[puntual]` | 5,584 | 5,334 | 2,849 | 4,589 |
| Bosque cuantílico | 5,764 | 5,413 | 2,674 | 4,617 |
| GBR + residuales `[puntual]` | 5,750 | 5,474 | 2,926 | 4,716 |
| Boosting cuantílico | 5,752 | 5,463 | 3,042 | 4,752 |

Contraste de Diebold-Mariano contra la mejor:

| Rival | p-valor | Veredicto |
|---|---|---|
| Media móvil + residuales | 0,807 | Empate técnico |
| Ridge + residuales `[puntual]` | 0,178 | Empate técnico |
| Ensemble + residuales `[puntual]` | 0,057 | Empate técnico, al límite |
| Bosque cuantílico | 0,021 | Pierde con evidencia |
| GBR + residuales `[puntual]` | 0,005 | Pierde con evidencia |
| Boosting cuantílico | 0,001 | Pierde con evidencia |

**Ninguna familia supera a la media móvil de 4 semanas.** Las bandas de
confianza de las siete se solapan por completo. Es lo que la exploración
anticipó: sin autocorrelación semanal, con el 90 % de la varianza entre series y
sin tendencia estimable fuera de muestra, no hay señal que un modelo extraiga y
una media móvil no.

## 3. Ridge da el mejor pronóstico central, y aun así no es la elección

| Familia | Error ponderado | Sesgo |
|---|---|---|
| Ridge + residuales `[puntual]` | **11,74 %** | +0,48 |
| Media móvil + residuales | 11,93 % | −0,02 |
| Ensemble + residuales `[puntual]` | 11,97 % | +0,37 |
| Regresión cuantílica | 12,01 % | +0,51 |
| GBR + residuales `[puntual]` | 12,33 % | +0,10 |
| Boosting cuantílico | 12,33 % | +0,16 |
| Bosque cuantílico | 12,34 % | +0,36 |

Ridge da el error puntual más bajo de las siete familias. El dato es sólido y
hay que reconocerlo: es el mejor pronóstico central del conjunto.

Y sin embargo pierde en pérdida pinball en el nivel de operación. **Es la
demostración más limpia de la tesis del proyecto:** el modelo que mejor acierta
el centro no es el que mejor sirve la decisión, porque la decisión no se toma en
el centro.

Si la selección se hubiera hecho con el error del pronóstico, se habría elegido
Ridge. Y se habría operado un modelo incapaz de dar lo que el newsvendor
necesita.

## 4. Lo que decide: el colchón

Ancho entre el nivel 0,90 y el 0,50, fila a fila:

| Familia | Media | Desviación | Mínimo | Máximo | ¿Cruza? |
|---|---|---|---|---|---|
| Regresión cuantílica | 16,67 | **3,78** | 9,30 | 30,22 | No |
| Ridge + residuales `[puntual]` | 16,27 | 0,00 | 16,27 | 16,27 | No |
| Media móvil + residuales | 16,53 | 0,00 | 16,53 | 16,53 | No |
| Ensemble + residuales `[puntual]` | 14,39 | 0,00 | 14,39 | 14,39 | No |
| GBR + residuales `[puntual]` | 14,99 | 0,00 | 14,99 | 14,99 | No |
| Bosque cuantílico | 17,02 | 6,11 | 4,00 | 45,00 | No |
| Boosting cuantílico | 13,23 | 6,53 | **−7,23** | 38,21 | **Sí** |

**Las cuatro familias puntuales dan un colchón plano.** No es un defecto de
implementación, es una consecuencia matemática: son modelos puntuales, y sumarles
un cuantil de residuales añade una constante. Asignan las mismas 16 unidades de
margen a las 160 series, a la más estable y a la más volátil.

El nivel de servicio dice qué proporción de semanas cubrir. El colchón dice
cuántas unidades hacen falta para cubrirla, y eso depende de lo volátil que sea
cada serie. Con un colchón plano se sobre-sirven las series tranquilas, que
acumulan merma, y se infra-sirven las movidas, que es donde se pierden ventas.

Esa diferencia no aparece en el error de pronóstico, que es prácticamente el
mismo. Aparece en el coste de la política.

**Y el boosting cuantílico tiene un defecto que lo descarta por sí solo:** sus
niveles se cruzan, con el cuantil 0,90 cayendo hasta 7,23 unidades por debajo del
0,50. Es imposible en la realidad y viene de entrenar cada nivel por separado sin
restricción de orden, y es un motivo suficiente para descartarlo por sí solo.

## 5. El enfoque clásico por serie es el peor

El suavizado exponencial con tendencia amortiguada, ajustado serie a serie,
obtiene 5,465 de pérdida en el nivel de operación y 12,32 % de error ponderado.
Queda por detrás de todas las familias globales.

Con trece semanas por serie y sin estructura temporal, ajustar parámetros por
serie solo añade varianza. Tenerlo medido permite descartarlo en la presentación
con evidencia propia en lugar de con un argumento teórico.

## 6. Familia elegida: regresión cuantílica lineal

Cuatro razones, en orden de peso:

1. **Es la única que gradúa el colchón sin cruzar niveles.** El bosque también lo
   gradúa, pero pierde con evidencia estadística.
2. **Gana en la métrica de la decisión**, aunque sea por empate técnico con las
   dos siguientes.
3. **Bate con evidencia a tres familias**, con contraste estadístico.
4. **Es interpretable**: cada coeficiente se puede enseñar, lo que importa cuando
   hay que explicar a una tienda por qué se le mandan 106 tintos.

Que empate con la línea base en precisión no es un argumento en contra. El valor
del proyecto nunca estuvo en predecir mejor, y ahora está medido en lugar de
supuesto.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Familia operativa: regresión cuantílica lineal, con alfa ajustada | Entrenamiento de la rejilla |
| 2 | Descartar los tres modelos de árboles, con contraste estadístico | Memoria técnica |
| 3 | Descartar el enfoque clásico por serie, con medición propia | Memoria técnica |
| 4 | Declarar que ninguna familia bate a la media móvil de 4 semanas | Presentación |
| 5 | Justificar la elección por el colchón variable, no por la precisión | Presentación |
| 6 | Verificar el orden de los niveles en cada predicción | Entrenamiento |
| 7 | Reconocer que Ridge da el mejor pronóstico central | Presentación |


---

## Anexo: profundidad de historia

Se probó si acortar el rezago más largo compensaba, porque cada semana de
historia consumida cuesta 160 filas de entrenamiento. Comparación sobre las
mismas semanas de validación y de prueba en las tres configuraciones:

| Rezago máximo | Filas de entrenamiento | Pérdida en validación | Pérdida en prueba |
|---|---|---|---|
| 2 | 1.280 | 5,196 | 5,678 |
| 3 | 1.120 | 5,054 | 5,391 |
| 4 | 960 | 5,071 | 5,377 |

Con rezago 2 se ganan 320 filas y se pierde bastante más de lo que se gana: es la
peor de las tres en las siete familias, en validación y en prueba. Entre 3 y 4
hay empate, con diferencias de milésimas.

**Se mantiene el rezago máximo en 4.** Gana en prueba, gana en cuatro de las
siete familias en validación, y es el único que permite construir la media móvil
de 4 semanas que el barrido eligió como línea base.

La lectura de fondo encaja con todo lo demás: lo que predice no es el dato de una
semana suelta sino el nivel suavizado de la serie, así que más filas de
entrenamiento no compensan tener variables peores. El cuello de botella no es el
número de filas.
