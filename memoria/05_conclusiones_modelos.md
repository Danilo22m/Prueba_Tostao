# Conclusiones de la selección de familia

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/05_seleccion_familia.txt` y de las figuras 13 a 15.

Se comparan trece configuraciones: siete familias en parametrización absoluta y
seis de ellas también en relativa. Las marcadas `[puntual]` solo estiman la media
condicional. El detalle de la parametrización relativa está en
`T1_parametrizacion_relativa.md`.

---

## 1. Cómo se hizo justa la comparación

Cuatro decisiones de método, tomadas antes de mirar resultados.

**Los modelos puntuales compiten en la misma métrica.** Ridge, el boosting
ordinario, su combinación y la media móvil solo estiman el centro. Para que
entren en una métrica distribucional se les suma el cuantil empírico de sus
propios residuales de entrenamiento. Sin eso, cualquier modelo probabilístico
habría ganado por defecto y no por mérito.

**Todas las métricas se calculan en unidades**, incluidas las de las
configuraciones relativas, que se convierten de vuelta antes de medir. El coste
del negocio está en pesos y escala con las unidades.

**Se compara en el nivel que se va a operar**, el 0,65, no en la mediana.

**Todas se ajustan con la misma búsqueda:** optimización bayesiana, 30 ensayos,
minimizando la pérdida pinball sobre los pliegues de validación.

## 2. Resultado: la parametrización relativa barre

Pérdida pinball media sobre las semanas de prueba:

| Configuración | 0,50 | 0,65 | 0,90 | Media |
|---|---|---|---|---|
| Bosque cuantílico (relativo) | 5,490 | 5,103 | 2,341 | **4,311** |
| GBR + residuales (relativo) | 5,514 | 5,117 | 2,328 | 4,320 |
| Boosting cuantílico (relativo) | 5,467 | 5,136 | 2,391 | 4,331 |
| Ridge + residuales (relativo) | 5,508 | 5,172 | 2,335 | 4,338 |
| Regresión cuantílica (relativo) | 5,484 | 5,166 | 2,378 | 4,343 |
| Ensemble + residuales (relativo) | 5,574 | 5,177 | 2,407 | 4,386 |
| Regresión cuantílica | 5,599 | 5,251 | 2,547 | 4,466 |
| Ridge + residuales | 5,494 | 5,279 | 2,719 | 4,497 |
| Media móvil + residuales | 5,563 | 5,319 | 2,741 | 4,541 |
| Ensemble + residuales | 5,584 | 5,334 | 2,849 | 4,589 |
| Bosque cuantílico | 5,764 | 5,413 | 2,674 | 4,617 |
| GBR + residuales | 5,750 | 5,474 | 2,926 | 4,716 |
| Boosting cuantílico | 5,752 | 5,463 | 3,042 | 4,752 |

**Las seis configuraciones relativas ocupan los seis primeros puestos.** No hay
solapamiento con las absolutas.

Y el contraste de Diebold-Mariano contra la mejor confirma la separación: las
seis relativas son empates técnicos entre sí, con p-valores entre 0,12 y 0,58,
mientras que **las siete absolutas pierden con evidencia**, con p entre 0,0014 y
0,030.

## 3. Ahora sí se supera la línea base

| Configuración | Error ponderado del centro |
|---|---|
| Boosting cuantílico (relativo) | **11,72 %** |
| Regresión cuantílica (relativo) | 11,76 % |
| Bosque cuantílico (relativo) | 11,77 % |
| Ridge + residuales | 11,78 % |
| Media móvil de 4 semanas, la línea base | 11,91 % |
| Regresión cuantílica | 12,01 % |

En la versión absoluta ninguna familia batía a la media móvil. Con la
parametrización relativa la superan seis configuraciones, aunque por márgenes
pequeños: entre 0,14 y 0,19 puntos porcentuales.

**Hay que presentarlo con la magnitud correcta.** Es una mejora real y medida,
pero modesta. La conclusión de fondo del proyecto no cambia: el valor está en la
política de pedido, no en la precisión del pronóstico.

## 4. El enfoque clásico por serie sigue siendo el peor

El suavizado exponencial con tendencia amortiguada obtiene 5,465 en el nivel de
operación y 12,32 % de error ponderado, por detrás de las trece configuraciones
globales.

Con trece semanas por serie y sin estructura temporal, ajustar parámetros por
serie solo añade varianza. Queda descartado con medición propia y no con un
argumento teórico.

## 5. El colchón: lo que decide entre las que empatan

Ancho entre el nivel 0,90 y el 0,50, fila a fila:

| Configuración | Media | Desviación | Mínimo | ¿Cruza? |
|---|---|---|---|---|
| Ridge + residuales (relativo) | 17,73 | 7,80 | 3,63 | No |
| Bosque cuantílico (relativo) | 17,66 | 7,64 | 3,89 | No |
| GBR + residuales (relativo) | 17,54 | 7,72 | 3,59 | No |
| Regresión cuantílica (relativo) | 17,44 | 6,60 | 5,39 | No |
| Boosting cuantílico (relativo) | 16,83 | 7,33 | 2,82 | No |
| Regresión cuantílica | 16,76 | 3,53 | 10,52 | No |
| Ridge + residuales | 16,42 | **0,00** | 16,42 | No |
| Media móvil + residuales | 16,53 | **0,00** | 16,53 | No |
| Ensemble + residuales | 14,39 | **0,00** | 14,39 | No |
| GBR + residuales | 14,90 | **0,00** | 14,90 | No |
| Boosting cuantílico | 13,62 | 5,92 | **−5,45** | **Sí** |

Dos observaciones.

**Las cuatro configuraciones puntuales absolutas dan colchón plano.** No es un
defecto de implementación, es matemática: son modelos que estiman la media, y
sumarles un cuantil de residuales añade una constante. Asignan el mismo margen a
las 160 series, a la más estable y a la más volátil.

**La parametrización relativa arregla el cruce del boosting.** En absoluto
cruzaba hasta 5,45 unidades; en relativo no cruza ninguna configuración. Lo
resuelve de raíz en lugar de parchearlo al ordenar.

## 6. Configuración elegida: regresión cuantílica relativa

Las seis relativas son estadísticamente indistinguibles entre sí, así que la
elección se decide por criterios secundarios:

1. **Interpretabilidad.** Es la única con coeficientes que se pueden enseñar, y
   en parametrización relativa se leen en porcentaje: «una desviación típica en
   la última semana mueve la predicción un 1,85 % sobre la media reciente». Eso
   se le explica a un jefe de tienda. Un bosque de 300 árboles, no.
2. **Estabilidad del colchón.** Su desviación de 6,60 es la menor de las seis,
   con un mínimo de 5,39 unidades. Las otras bajan hasta 2,82, lo que en series
   pequeñas deja un margen demasiado ajustado.
3. **Coste de cómputo despreciable** y sin dependencias adicionales.

Que empate con cinco configuraciones más no es un problema. Cuando las
diferencias no son distinguibles del ruido, elegir por interpretabilidad es la
decisión correcta y hay que decirlo así.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Configuración operativa: regresión cuantílica relativa | Entrenamiento de la rejilla |
| 2 | Descartar las siete parametrizaciones absolutas, con contraste | Memoria técnica |
| 3 | Descartar el enfoque clásico por serie, con medición propia | Memoria técnica |
| 4 | Declarar que la mejora sobre la línea base es real pero modesta | Presentación |
| 5 | Justificar la elección final por interpretabilidad ante el empate | Presentación |
| 6 | Verificar el orden de los niveles en cada predicción | Entrenamiento |
