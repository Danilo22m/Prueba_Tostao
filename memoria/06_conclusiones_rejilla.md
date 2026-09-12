# Conclusiones del entrenamiento de la rejilla

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/06_rejilla_niveles.txt` y de las figuras 16 y 17.

Se entrenan 17 regresiones cuantílicas, una por cada nivel de servicio que
pidieron los costes, reutilizando el alfa optimizado en el nivel de operación.

---

## 1. La calibración es buena, y no era evidente que fuera a serlo

Cobertura empírica frente al nivel prometido, sobre las 480 decisiones de prueba:

| Nivel | Cobertura | Desvío |
|---|---|---|
| 0,50 | 0,517 | +0,017 |
| 0,57 | 0,581 | +0,011 |
| 0,65 | 0,679 | +0,029 |
| 0,68 | 0,700 | +0,020 |
| 0,74 | 0,735 | −0,005 |
| 0,81 | 0,777 | −0,033 |
| 0,90 | 0,875 | −0,025 |
| 0,98 | 0,960 | −0,020 |
| 0,99 | 0,988 | −0,002 |

El desvío medio es de −0,000 y el peor caso es de 0,038. En la figura 17 los
puntos abrazan la diagonal.

**Qué significa.** Cuando la política prometa cubrir el 68 % de las semanas, se
cubre el 70 %. El nivel de servicio que se le ofrece a negocio es real y no una
etiqueta.

Se aprecia un patrón leve pero consistente: los niveles bajos cubren algo de más
y los altos algo de menos. Es lo habitual cuando se estima con muestra corta, y
la magnitud es pequeña. El paso de calibración conformal puede corregirlo, pero
partiendo de aquí el margen de mejora es estrecho.

## 2. Los niveles se cruzan en el 23 % de las filas, y hay que corregirlo

Se detectaron 111 cruces sobre 480 filas y 16 pares consecutivos de niveles. Cada
nivel se ajusta por separado, así que nada garantiza que salgan ordenados.

La mayoría son irrelevantes por magnitud:

| Par | Cruces | Cruce máximo |
|---|---|---|
| 0,65 → 0,66 | 37 | 0,25 unidades |
| 0,66 → 0,67 | 26 | 0,25 unidades |
| 0,64 → 0,65 | 12 | 0,15 unidades |
| 0,90 → 0,98 | 6 | 2,64 unidades |
| **0,98 → 0,99** | **11** | **44,08 unidades** |

Entre niveles casi idénticos, como 0,65 y 0,66, el cruce es de décimas de unidad
y es simple ruido numérico: los dos modelos estiman prácticamente lo mismo.

**El cruce de 44 unidades entre 0,98 y 0,99 es otra cosa** y se trata en el
apartado siguiente.

La corrección aplicada es ordenar los valores de cada fila. No cambia el conjunto
de cantidades estimadas, solo su asignación a niveles, y garantiza que pedir con
más protección nunca devuelva menos unidades. Tras ordenar no queda ningún cruce.

## 3. El nivel 0,99 no es fiable, y eso confirma una advertencia previa

| Nivel | Unidades medias | Veces la demanda media |
|---|---|---|
| 0,90 | 109,4 | 1,17 |
| 0,98 | 125,4 | 1,34 |
| 0,99 | 208,5 | **2,24** |

El salto entre 0,98 y 0,99 es de 83 unidades, mientras que entre 0,90 y 0,98 es
de 16. La progresión se rompe.

Su pérdida pinball también lo delata: 1,299 en el nivel 0,99 frente a 0,979 en el
0,98. Una pérdida mayor en un nivel más extremo es anómala.

**La causa es la muestra.** Estimar el percentil 99 con 960 filas significa
apoyarse en las seis o siete observaciones más altas. Cualquier modelo se vuelve
inestable ahí.

**La consecuencia práctica es importante y hay que llevarla a la presentación.**
El nivel 0,99 es el que opera el escenario sin merma, el del enunciado. Aplicarlo
literalmente significaría pedir 2,24 veces la demanda media, con la estimación
menos fiable de toda la rejilla.

Es un argumento adicional, ahora medido, contra ese escenario de coste. No solo
deja los ocho productos indistinguibles: además obliga a operar en la zona donde
el modelo peor estima.

Los niveles del escenario con merma, entre 0,57 y 0,68, caen cerca de la mediana,
que es donde la estimación es más estable y la calibración sale mejor.

## 4. El abanico se adapta a cada serie

La figura 16 muestra cuatro series de volatilidad distinta con su abanico. El
ancho medio va de una serie a otra en un rango amplio, que es exactamente la
propiedad por la que se eligió esta familia frente a Ridge y la media móvil.

## 5. Sobre reutilizar el alfa en toda la rejilla

El alfa se optimizó en el nivel 0,65 y se reutiliza en los 17. La alternativa
sería reoptimizar en cada nivel, y no se hizo por dos motivos.

Con 960 filas de entrenamiento y tres pliegues de validación, 17 búsquedas
independientes se ajustarían al ruido de la validación más de lo que mejorarían
el resultado.

Y la calibración obtenida es buena en todo el rango, incluidos los extremos, así
que no hay evidencia de que el alfa elegido se quede corto donde más difícil es
estimar.

La excepción es el nivel 0,99, pero ahí el problema no es el alfa sino que no hay
datos suficientes en la cola. Reoptimizar no lo arreglaría.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Ordenar los valores de cada fila para forzar niveles monótonos | Optimizador |
| 2 | Declarar que el nivel 0,99 pide 2,24 veces la demanda media | Presentación |
| 3 | Usar el nivel 0,99 como argumento medido contra el escenario sin merma | Presentación |
| 4 | Reutilizar el alfa en toda la rejilla, con la calibración como justificación | Memoria técnica |
| 5 | El abanico de prueba queda guardado como artefacto auditable | Optimizador |
