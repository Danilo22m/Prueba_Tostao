# ¿Qué pasa si el producto sobrante se guarda?

**Caso A · Optimización de abastecimiento · Tostao**

Es la única decisión de negocio abierta del proyecto, y la que más mueve el
resultado. Este documento la resuelve con números.

---

## 1. La pregunta

Al cierre de la semana sobra producto. ¿Qué se hace con él?

| Respuesta | Qué cuesta que sobre una unidad de Tinto |
|---|---|
| **Se guarda** y se vende la semana siguiente | 10 pesos de almacenaje |
| **Se tira** | 800 del coste unitario más 10 de almacenaje = 810 |

Ochenta y un veces de diferencia. Y de ahí sale todo lo demás.

## 2. Qué cambia en el nivel de servicio

El nivel sale de dividir el margen perdido entre la suma de los dos costes.

**Si se guarda:**

```
1.700 ÷ (1.700 + 10) = 0,994
```

**Si se tira:**

```
1.700 ÷ (1.700 + 810) = 0,68
```

Aplicado a los ocho productos:

| Producto | Nivel si se guarda | Nivel si se tira |
|---|---|---|
| Tinto | 0,994 | 0,68 |
| Buñuelo | 0,988 | 0,67 |
| Cappuccino | 0,995 | 0,66 |
| Café con Leche | 0,994 | 0,65 |
| Croissant | 0,989 | 0,65 |
| Pan de Bono | 0,989 | 0,64 |
| Jugo de Naranja | 0,984 | 0,59 |
| Pastel de Pollo | 0,985 | 0,57 |

**Fíjate en la columna de la izquierda.** Si se guarda, los ocho quedan entre
0,984 y 0,995. Son indistinguibles.

El enunciado pide explícitamente proponer cómo usar la incertidumbre junto con
los márgenes para decidir si el pedido debe ser agresivo o conservador. Con el
supuesto de que se guarda, **esa pregunta se queda sin respuesta**, porque todos
los productos salen igual de agresivos.

Con merma los niveles se separan de 0,57 a 0,68 y quedan ordenados exactamente
por margen. Ahí sí hay algo que mostrar.

## 3. Qué cambia en el pedido

| Supuesto | Nivel medio | Unidades a pedir en la red |
|---|---|---|
| Se guarda | 0,989 | 17.180 |
| Se recupera la mitad | 0,779 | 13.127 |
| Se tira | 0,639 | 12.362 |

Mismo modelo, mismas predicciones, mismo inventario. **Son 4.818 unidades
semanales de diferencia** por una sola decisión de negocio.

## 4. Qué cambia en el ahorro

| Supuesto | Coste al pedir el centro | Coste con la propuesta | Ahorro |
|---|---|---|---|
| Se guarda | 6.025.518 | 448.551 | **92,6 %** |
| Se recupera la mitad | 7.793.518 | 6.051.554 | 22,4 % |
| Se tira | 9.561.518 | 9.062.061 | 5,2 % |

**Aquí está lo incómodo.** El mismo trabajo produce un ahorro del 92 % o del 5 %
según una suposición que no hemos verificado.

**Por qué pasa.** Cuando sobrar cuesta 10 pesos, pedir de más es casi gratis. La
política de nivel pide mucho, casi nunca falta producto, y el coste se desploma.
Cuando sobrar cuesta 810, protegerse sale caro y el margen de mejora se estrecha.

## 5. La sensibilidad no es lineal, y eso cambia la conversación

No hace falta elegir entre los dos extremos. El nivel de servicio se mueve así
según qué porcentaje del sobrante se pierda:

| Se descarta | Nivel del Tinto | Amplitud entre el SKU más y menos agresivo |
|---|---|---|
| 0 % | 0,994 | 0,011 |
| 20 % | 0,909 | — |
| 40 % | 0,837 | — |
| 50 % | 0,806 | 0,086 |
| 100 % | 0,677 | 0,111 |

**La caída más fuerte está al principio.** Basta suponer que se pierde un 20 %
del sobrante para que el nivel baje de 0,99 a 0,91.

Eso convierte la pregunta a negocio de binaria en cuantitativa. En vez de
preguntar «¿se tira el producto?», que invita a discutir principios, se pregunta
«¿qué porcentaje se pierde al cierre?», que es un dato que en tienda tienen.

## 6. Qué recomendamos y por qué

**El escenario con merma**, el más conservador.

Tres razones:

**Por el producto.** El catálogo son ocho referencias de cafetería y bollería:
Tinto, Café con Leche, Cappuccino, Jugo de Naranja, Pan de Bono, Buñuelo,
Croissant y Pastel de Pollo. Ninguna es envasado de larga duración. Un tinto
servido no se guarda y un pan de bono del día anterior no se vende.

**Por la pregunta del enunciado.** Es el único escenario donde los niveles se
diferencian por margen, que es justo lo que piden demostrar.

**Por prudencia.** Da la cifra de ahorro más baja de las tres. Si el piloto
confirma que se pierde menos producto del supuesto, el resultado mejorará. Al
revés sería peor: prometer un 92 % y entregar un 5 % destruye la credibilidad
del proyecto entero.

## 7. Cómo llevarlo a la presentación

No como un detalle técnico escondido, sino como una lámina propia.

El mensaje: el ahorro de este proyecto depende de una decisión que no nos
corresponde. Si el sobrante se vende al día siguiente, ahorra un 93 %. Si se
tira, un 5 %. Recomendamos planificar con el segundo y medir el porcentaje real
de merma en el piloto.

---

## Decisiones que salen de este documento

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Planificar con el escenario de merma total | Operación |
| 2 | Llevar los tres escenarios a la presentación, en lámina propia | Presentación |
| 3 | Preguntar a negocio el porcentaje real de merma, no si se tira o no | Piloto |
| 4 | Medir merma real en el piloto como primera métrica | Piloto |
