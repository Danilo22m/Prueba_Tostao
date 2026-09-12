# Conclusiones del optimizador del pedido

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/09_pedidos.txt`, de la figura 22 y del fichero
`salidas/parametros/pedidos.csv`.

Este paso convierte el abanico de cuantiles, ya calibrado, en la cantidad que la
tienda ejecuta. Es la capa de decisión, y su lógica es deliberadamente corta para que
pueda revisarla alguien de operaciones sin leer el resto del proyecto.

---

## 1. La regla, entera

```
nivel de servicio  =  el que marcan los costes del producto
objetivo           =  la predicción del modelo a ese nivel, redondeada
pedido             =  máximo(0, objetivo − stock en estantería)
```

Tres líneas. Todo lo demás del proyecto existe para que esas tres sean
defendibles.

## 2. Se verifica, no se supone

El módulo comprueba seis propiedades en cada ejecución y el informe las publica:

- Ningún pedido negativo.
- Todas las cantidades enteras.
- El pedido más el stock alcanza siempre el objetivo.
- Donde el stock ya cubre el objetivo, el pedido es cero.
- Cada producto usa el nivel de servicio que marcan sus costes, no otro.
- Ningún objetivo queda por debajo del pronóstico central.

Además hay ocho pruebas con casos construidos a mano en `tests/test_optimizador.py`,
donde la respuesta correcta se conoce de antemano. Incluyen dos que exigen que el
proceso **falle**: si el abanico no trae el nivel que un producto necesita, o si
alguna serie no tiene stock registrado. Un cero silencioso en el inventario sería
peor que un error.

## 3. El colchón sigue al margen, y ahora se ve en unidades

| Producto | Nivel | Pronóstico | Objetivo | Colchón | Colchón % |
|---|---|---|---|---|---|
| Tinto | 0,68 | 58,7 | 63,5 | 4,9 | 8,3 % |
| Buñuelo | 0,67 | 125,7 | 133,4 | 7,7 | 6,1 % |
| Cappuccino | 0,66 | 83,1 | 89,2 | 6,1 | 7,3 % |
| Café con Leche | 0,65 | 80,2 | 85,5 | 5,2 | 6,5 % |
| Croissant | 0,65 | 115,2 | 122,0 | 6,8 | 5,9 % |
| Pan de Bono | 0,64 | 49,4 | 52,8 | 3,4 | 6,8 % |
| Jugo de Naranja | 0,59 | 112,9 | 116,6 | 3,7 | 3,3 % |
| Pastel de Pollo | 0,57 | 120,1 | 123,4 | 3,3 | 2,8 % |

**Es la respuesta visible a la pregunta del enunciado.** Piden proponer cómo usar
la incertidumbre junto con los márgenes para decidir si el pedido es agresivo o
conservador. Esta tabla es esa respuesta, y el orden del colchón porcentual
coincide exactamente con el del margen.

El Tinto se protege un 8,3 % por encima de lo esperado porque perder una venta
cuesta el doble que tirarlo. El Pastel de Pollo solo un 2,8 % porque sus dos
costes se parecen mucho más.

## 4. La operación resultante

| Indicador | Valor |
|---|---|
| Series con pedido | 160 |
| Unidades totales a pedir | 12.362 |
| Series cubiertas por el stock | 5 |
| Pedido medio por serie | 77,3 |
| Pedido máximo | 220 |
| Stock medio en estantería | 21,0 |

Cinco series no piden nada porque el inventario ya cubre su objetivo. Es el
comportamiento correcto y conviene señalarlo: la política no pide por pedir.

## 5. El escenario de coste mueve el pedido un 38 %

| Escenario | Merma supuesta | Nivel medio | Unidades a pedir |
|---|---|---|---|
| Sin merma | 0 % | 0,989 | 17.180 |
| Merma parcial | 50 % | 0,779 | 13.127 |
| Con merma | 100 % | 0,639 | 12.362 |

Mismo modelo, mismas predicciones, mismo inventario. Solo cambia el supuesto
sobre qué pasa con el sobrante, y el pedido total va de 12.362 a 17.180 unidades.

**Es la cifra que mejor comunica por qué ese supuesto no es un detalle técnico.**
Son 4.818 unidades semanales de diferencia en la red, y la decisión sobre cuál
aplicar es de negocio.

## 6. Restricciones operativas previstas pero desactivadas

El módulo admite tres límites que hoy no se aplican porque el enunciado no da
información para fijarlos:

- **Múltiplo de lote**, si el proveedor sirve en cajas de tamaño fijo.
- **Redondeo al alza**, defendible cuando el coste de faltante domina.
- **Techo físico por serie**, que la superficie de tienda impondría.

Están implementados y probados. Se activan cambiando un parámetro, sin tocar la
lógica. Conviene preguntar por los tres antes del piloto, sobre todo por el
techo: un nivel de servicio alto en una tienda de 15 metros cuadrados puede pedir
más de lo que cabe.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Redondeo al entero más cercano, sin sesgo hacia arriba | Operación |
| 2 | Publicar las seis verificaciones en cada ejecución del informe | Calidad |
| 3 | Llevar la tabla de colchón por producto a la presentación | Presentación |
| 4 | Usar la diferencia de 4.818 unidades para explicar el supuesto de merma | Presentación |
| 5 | Preguntar por lote, techo físico y política de redondeo antes del piloto | Plan de implantación |
