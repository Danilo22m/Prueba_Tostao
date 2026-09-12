# Conclusiones de la calibración conformal

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/08_calibracion.txt` y de la figura 22.

---

## 1. Qué se hizo y para qué

Un modelo puede prometer cubrir el 68 % de las semanas y cubrir solo el 60. Si
eso pasa, el nivel de servicio que se le ofrece a negocio es una etiqueta falsa,
y el pedido se queda corto justo en las semanas de demanda alta, que son las que
más margen dejan.

La calibración conformal corrige esa desviación. Mide en datos que el modelo no
vio cuánto se desvía la cobertura, y desplaza la predicción lo justo para cerrar
la brecha. No supone nada sobre la forma de la distribución de la demanda.

Se usó la variante de validación cruzada: cada semana de validación la predice un
modelo que no la vio. Así no hay que reservar un trozo del entrenamiento, que con
960 filas sería caro.

## 2. Dónde se aplica

La calibración es una corrección **al modelo**, así que se aplica dentro del
entrenamiento, antes de que ninguna decisión use las predicciones. Todo lo que
viene después (rejilla, diagnóstico, pedidos y políticas) trabaja ya con los
niveles corregidos.

Se hace a través de `rejilla.entrenar_calibrado`, que es el punto único desde el
que el resto del pipeline obtiene el modelo.

**Una corrección de criterio.** En una primera versión no se aplicó, porque su
efecto medido en prueba era pequeño. Ese razonamiento era malo: decidir con el
conjunto de evaluación es exactamente el error que se corrigió dos veces antes en
este proyecto. La calibración conformal tiene garantía teórica de cobertura, así
que su sitio es el pipeline, y lo que se reporta es la magnitud de su efecto, no
si se adopta o no.

## 3. Resultado: el efecto es pequeño pero positivo

Los desplazamientos calculados van de −0,09 a −1,47 unidades, todos negativos:
el modelo cubría ligeramente **de más**, así que la corrección reduce el pedido.

Efecto sobre el ahorro total de la política:

| | Sin calibrar | Calibrado | Cambio |
|---|---|---|---|
| Ahorro con merma | 477.963 | **499.457** | +21.494 |
| Ahorro sin merma | 92,4 % | **92,6 %** | +0,2 pp |
| Extrapolación anual | 8.284.700 | **8.657.250** | +372.550 |

Es una mejora real pero modesta: un 4,5 % más de ahorro. No cambia ninguna
conclusión del proyecto.

**El efecto sobre la cobertura es ambiguo.** El desvío medio absoluto baja de
0,019 a 0,017 y nueve de los diecisiete niveles mejoran, pero ocho empeoran: la
corrección arregla los niveles bajos y desplaza ligeramente los altos. Eso es
esperable cuando el punto de partida ya estaba bien calibrado.

## 4. Por qué el margen de mejora era pequeño

Porque el modelo ya estaba bien calibrado de origen. El desvío de partida era de
0,019, y un modelo mal calibrado tendría desvíos de 0,05 o 0,10. La corrección
tenía poco que corregir.

Esto se debe en buena parte a la parametrización relativa. Al predecir
proporciones en lugar de unidades, todas las series contribuyen a estimar la
misma distribución, y las colas salen mucho más estables. Ya lo habíamos visto en
el nivel 0,99, que pasó de pedir 2,24 veces la demanda media a pedir 1,38.

## 5. Cómo presentarlo

Como un control que se pasó, no como un paso que se omitió.

La frase para la presentación: los niveles se recalibran con métodos
conformales dentro del entrenamiento, y la corrección aporta un 4,5 % adicional
de ahorro. El margen era pequeño porque la parametrización relativa ya dejaba los
niveles bien calibrados de origen.

Eso es más fuerte que aplicarlo sin medir cuánto aporta, y más fuerte que no
haberlo mirado.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Aplicar la calibración dentro del entrenamiento, no como análisis posterior | Pipeline |
| 2 | Declarar que aporta un 4,5 % adicional, no más | Presentación |
| 3 | Atribuir el margen estrecho a la parametrización relativa | Memoria técnica |
| 4 | No decidir la adopción mirando el conjunto de prueba | Método |
