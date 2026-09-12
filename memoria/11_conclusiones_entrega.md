# Conclusiones de la entrega

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/11_entrega.txt`, de la figura 25 y del fichero
`salidas/parametros/pedidos_semana_siguiente.csv`.

Los quince pasos anteriores miden. Este entrega. Es el único cuyo resultado no se
puede evaluar, y por eso es el que más depende de que los anteriores estuvieran
bien hechos.

---

## 1. Qué es exactamente lo que se entrega

Un fichero con 160 filas, una por tienda y producto, y siete columnas que
importan: el pronóstico central, el nivel de servicio del producto, el objetivo
de estantería, el stock que ya hay y las unidades a pedir. Es la tabla que la
tienda ejecuta sin tener que interpretar nada.

El total son **12.290 unidades** a pedir para la semana 14. El objetivo de
estantería suma 15.591 unidades y el inventario actual aporta 3.367. Las dos
cifras no restan exacto porque en cinco de las 160 series el stock ya supera el
objetivo, y ese exceso no descuenta nada del resto: esas cinco simplemente no
piden.

## 2. Por qué se reentrena con las trece semanas

Hasta el paso 15 el modelo se ajustaba con las semanas 5 a 10 y se medía en las
11 a 13. Esa separación era obligatoria para que las métricas significaran algo.

Para el pedido real deja de serlo. La semana 14 no está en ningún sitio, así que
no hay nada que proteger de la contaminación, y cada semana retenida sería una
semana de historia tirada. El modelo pasa de 960 a 1.440 filas de ajuste y de
tres a seis pliegues de calibración.

Esto no es un atajo, es la práctica estándar: se elige el modelo con datos
retenidos y se reajusta con todo antes de usarlo. Lo que **no** cambia es la
elección. Los niveles de servicio vienen del paso 9, la familia y los
hiperparámetros del paso 10, y ninguno se ha vuelto a tocar. Si los hubiéramos
reelegido ahora, con trece semanas, habríamos anulado la evaluación entera: el
modelo habría visto las semanas con las que se le midió.

## 3. Este paso no tiene métricas, y eso hay que decirlo

No hay WAPE ni pinball para la semana 14. No existe la demanda con la que
compararlos, y cualquier número calculado sobre las semanas de ajuste estaría
medido en los mismos datos que entrenaron el modelo.

Si en la presentación alguien pide el error de esta tabla, la respuesta correcta
es que el error esperado es el del informe 05, medido en semanas que el modelo no
vio, y que se sabrá el real cuando la semana 14 termine. Enseñar un error
calculado sobre el entrenamiento sería el error clásico del ejercicio.

## 4. Lo que sí se puede comprobar

**Las propiedades de la tabla.** Doce verificaciones automáticas en cada
ejecución, y todas pasan. Seis son las del optimizador, que ya existían. Las
otras seis son nuevas y específicas de la entrega: que ampliar el panel con la
fila de la semana 14 no altera ninguna variable del pasado, que esa semana no
aparece en el entrenamiento, que hay una fila por serie sin duplicados, que
todas las series del panel reciben pedido, que la tabla no contiene demanda
observada, y que el entrenamiento usa todas las semanas disponibles.

La primera es la que más me preocupaba. Para predecir la semana 14 hay que
fabricar su fila, porque no existe en el panel, y al fabricarla es fácil
desplazar una ventana móvil sin darse cuenta. La comprobación reconstruye todas
las variables con y sin la fila nueva y exige que las semanas pasadas salgan
idénticas. Es el argumento de `verificar_sin_fuga` en la dirección contraria.

**El contraste con los patrones declarados.** El fichero de tendencias dice de
cada serie si sube, baja, es estacional o es aleatoria. Ese dato nunca entra al
modelo. Comparar la variación que predice el modelo frente a la media de las
cuatro últimas semanas, agrupada por patrón, da esto:

| Patrón | Series | Variación mediana |
|---|---|---|
| up | 27 | +0,18 % |
| seasonal | 57 | −0,35 % |
| random | 32 | −0,37 % |
| down | 44 | −0,86 % |

El orden es el correcto: las series que suben son las únicas con variación
positiva, las que bajan son las más negativas, y las aleatorias quedan en medio.
Es una validación externa real, porque el modelo llegó a ese orden sin que nadie
le dijera a qué grupo pertenece cada serie.

También es una confirmación de lo que dice el paso 3. Las magnitudes son
diminutas: apenas un punto porcentual separa al grupo que sube del que baja.
El modelo detecta la dirección pero apenas se mueve, que es exactamente lo que
cabe esperar de series con autocorrelación semanal cercana a cero. Sirve como
prueba de que no hay un error de signo, no como prueba de que el modelo tenga
poder predictivo. Eso lo mide el informe 05.

## 5. La calibración se recalcula, y se mueve

Con seis pliegues en lugar de tres, los desplazamientos conformales cambian. Los
niveles centrales se mueven poco. Los extremos se mueven bastante: el 0,99 pasa
de −1,96 a −2,74 unidades y el 0,98 de −0,44 a −1,72.

Tiene sentido y conviene entenderlo. Un cuantil extremo se estima con las pocas
observaciones de la cola, así que duplicar los datos de calibración cambia mucho
la estimación. Es un recordatorio de que los niveles altos son los menos fiables
del abanico, y de que la política recomendada no los usa: con merma, los ocho
productos piden niveles entre 0,57 y 0,68, donde la corrección es estable.

Si algún día el negocio decidiera operar sin merma, los niveles subirían a 0,99 y
esta inestabilidad pasaría a ser un problema de primer orden. Es otro argumento,
además del económico, para no presentar ese escenario como el recomendado.

## 6. El escenario de coste sigue siendo la decisión abierta

La misma tabla de pronósticos produce tres pedidos distintos:

| Escenario | Nivel medio | Unidades a pedir |
|---|---|---|
| Sin merma | 0,99 | 16.671 |
| Merma parcial | 0,78 | 13.248 |
| Con merma | 0,64 | 12.290 |

Son **4.381 unidades de diferencia** entre el extremo y el recomendado, un 36 %
más de pedido, sobre las mismas predicciones y el mismo modelo. Ninguna sale de
un supuesto estadístico: salen de responder si el café que sobra se vende al día
siguiente o se tira.

Entregamos la tabla del escenario con merma, que es el más conservador de los
tres y el que corresponde a cafetería. Las otras dos quedan en el informe para
que la decisión sea explícita. Está desarrollado en
`T2_escenario_del_sobrante.md`.

## 7. Lo que haría falta para que esto corra solo

La tabla de esta semana está hecha. Convertirlo en un proceso semanal necesita
tres cosas que hoy no tenemos:

- **Un inventario con fecha.** El fichero actual no dice a qué momento
  corresponde el stock. Para pedir la semana 14 hace falta el stock del cierre de
  la 13, y hay que poder comprobarlo.
- **Reentrenamiento programado.** Cada semana nueva añade 160 filas. No hace
  falta reentrenar cada semana, pero sí decidir cada cuánto y vigilar que el
  error real no se separe del medido.
- **Respuesta a las tres restricciones operativas.** Múltiplo de lote, techo
  físico por tienda y política de redondeo. Están implementadas y probadas, pero
  desactivadas porque nadie ha dicho qué valores toman. Está en
  `09_conclusiones_pedidos.md`.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Reentrenar con las trece semanas y entregar la 14, conservando la familia y los hiperparámetros del paso 10 | Entrega |
| 2 | No publicar ninguna métrica de error para la semana entregada | Presentación |
| 3 | Llevar el contraste por patrón declarado como validación externa, aclarando que mide dirección y no potencia | Presentación |
| 4 | Entregar el escenario con merma y adjuntar los otros dos | Negocio |
| 5 | Pedir inventario con fecha antes del piloto | Plan de implantación |
| 6 | No operar a nivel 0,99 mientras la corrección conformal de la cola siga siendo inestable | Modelo |
