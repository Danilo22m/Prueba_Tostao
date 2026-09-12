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

| Producto | Margen | Nivel | Pronóstico | Objetivo | Colchón | Colchón % |
|---|---|---|---|---|---|---|
| Tinto | 68,0 % | 0,68 | 58,4 | 63,3 | 4,9 | 8,4 % |
| Buñuelo | 68,0 % | 0,67 | 125,4 | 132,7 | 7,2 | 5,7 % |
| Cappuccino | 66,7 % | 0,66 | 82,8 | 88,7 | 5,9 | 7,1 % |
| Café con Leche | 65,7 % | 0,65 | 80,0 | 85,0 | 5,0 | 6,3 % |
| Croissant | 65,7 % | 0,65 | 114,9 | 121,5 | 6,6 | 5,7 % |
| Pan de Bono | 64,3 % | 0,64 | 49,1 | 52,1 | 2,9 | 6,0 % |
| Jugo de Naranja | 60,0 % | 0,59 | 112,6 | 116,0 | 3,4 | 3,0 % |
| Pastel de Pollo | 57,1 % | 0,57 | 119,8 | 123,0 | 3,1 | 2,6 % |

**Es la respuesta visible a la pregunta del enunciado.** Piden proponer cómo usar
la incertidumbre junto con los márgenes para decidir si el pedido es agresivo o
conservador. Esta tabla es esa respuesta. El producto con más margen se protege
más del triple que el de menos margen, y nadie lo decidió a mano.

El orden del colchón porcentual no es exactamente el del margen, porque el
colchón en unidades depende también de la volatilidad de cada producto: el
Cappuccino, con menos margen que el Buñuelo, tiene un colchón mayor en
proporción porque sus series oscilan más. Lo que sí es exacto es el orden de
los niveles, que solo dependen de los costes.

El Tinto se protege un 8,4 % por encima de lo esperado porque perder una venta
cuesta el doble que tirarlo. El Pastel de Pollo solo un 2,6 % porque sus dos
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
