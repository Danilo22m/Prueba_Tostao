# Conclusiones sobre costes y niveles de servicio

**Caso A · Optimización de abastecimiento · Tostao**

Lectura de `salidas/informes/04_costes_y_niveles.txt` y de las figuras 11 y 12.
Este paso se ejecuta antes de entrenar porque decide cuántos modelos hacen falta
y cuáles.

---

## 1. El nivel de servicio no depende de la demanda

Sale de igualar lo que se espera ganar al añadir una unidad con lo que se espera
perder:

    nivel = coste de faltante / (coste de faltante + coste de sobrante)

En esa expresión no aparece la demanda por ningún lado. Depende solo de dos
precios. Tiene tres consecuencias prácticas:

- El mismo modelo sirve para los ocho productos con políticas distintas.
- Si mañana cambia el precio del Tinto, no hay que reentrenar nada: se recalcula
  el nivel y el pedido se ajusta solo.
- La conversación con negocio sobre qué nivel usar es independiente de la
  discusión técnica sobre qué modelo usar.

## 2. Con el coste del enunciado, la política es la misma para todos

| Producto | Faltante | Sobrante | Razón | Nivel |
|---|---|---|---|---|
| Cappuccino | 3.000 | 15 | 200 : 1 | 0,995 |
| Tinto | 1.700 | 10 | 170 : 1 | 0,994 |
| Café con Leche | 2.300 | 15 | 153 : 1 | 0,994 |
| Croissant | 2.300 | 25 | 92 : 1 | 0,989 |
| Pan de Bono | 1.800 | 20 | 90 : 1 | 0,989 |
| Buñuelo | 1.700 | 20 | 85 : 1 | 0,988 |
| Pastel de Pollo | 2.000 | 30 | 67 : 1 | 0,985 |
| Jugo de Naranja | 3.000 | 50 | 60 : 1 | 0,984 |

Los ocho caben en una amplitud de 0,011. Son indistinguibles en la práctica.

**Por qué importa.** El enunciado pide explícitamente proponer cómo usar la
incertidumbre junto con los márgenes para decidir si el pedido debe ser agresivo
o conservador. Con estos costes todos salen máximamente agresivos y esa pregunta
se queda sin respuesta, porque no hay nada que diferenciar.

Y hay un problema operativo añadido: un nivel de 0,995 exige estimar un cuantil
que la muestra no sostiene. Con trece semanas por serie, el percentil 99 no es
estimable, hay que extrapolarlo, y es justo donde la extrapolación falla más.

## 3. La sensibilidad es brutal cerca de cero, y eso cambia la conversación

| Se descarta | Amplitud entre el SKU más y menos agresivo |
|---|---|
| 0 % | 0,011 |
| 25 % | 0,058 |
| 50 % | 0,086 |
| 75 % | 0,102 |
| 100 % | 0,111 |

El tramo más pronunciado está al principio. Descartar solo un 20 % del sobrante
ya baja los niveles de 0,99 a alrededor de 0,90.

**Consecuencia para la presentación.** No hace falta plantear un dilema binario
entre «se guarda todo» y «se tira todo». La pregunta a negocio es cuantitativa:
qué porcentaje del sobrante se pierde. Es una pregunta que en tienda saben
responder, mientras que la binaria invita a discutir el supuesto en vez del
método. La figura 12 es la que hay que llevar a esa conversación.

## 4. Con merma, la diferenciación aparece y está ordenada por margen

| Producto | Margen | Nivel con merma total |
|---|---|---|
| Tinto | 68,0 % | 0,677 |
| Buñuelo | 68,0 % | 0,675 |
| Cappuccino | 66,7 % | 0,664 |
| Café con Leche | 65,7 % | 0,654 |
| Croissant | 65,7 % | 0,652 |
| Pan de Bono | 64,3 % | 0,638 |
| Jugo de Naranja | 60,0 % | 0,594 |
| Pastel de Pollo | 57,1 % | 0,567 |

El orden es exactamente el del margen porcentual. Es la demostración numérica de
que la política responde a la economía del producto y no a una preferencia.

El Pastel de Pollo sale el más conservador porque combina el margen más bajo con
el segundo almacenamiento más caro. El Tinto sale el más agresivo porque tiene el
margen más alto y el almacenamiento más barato del catálogo.

**Recomendación.** Llevar el escenario con merma como principal y el del
enunciado como contraste, explicando que este último se descarta porque supone
que el café y la bollería sobrantes se venden al día siguiente.

La decisión final es de negocio, no técnica. Lo que sí es responsabilidad técnica
es presentar las dos y decir cuál se recomienda y por qué.

## 5. La rejilla queda cerrada en 17 niveles

```
0,50  0,57  0,59  0,64  0,65  0,66  0,67  0,68
0,72  0,74  0,78  0,79  0,80  0,81  0,90  0,98  0,99
```

Reúne los niveles que piden los tres escenarios, más el 0,50 para el pronóstico
central que quiere negocio y el 0,90 para auditar la incertidumbre.

Los niveles se acotan en 0,99 por arriba. El redondeo llevaba el Cappuccino a
1,00, y un nivel de 1 significa pedir sin límite: el cuantil 1 no es estimable a
partir de una muestra finita.

**Esto es lo que hacía falta para poder entrenar.** Hasta tener esta lista no se
sabía cuántos modelos de cuantil hay que ajustar. Son 17, y con 960 filas de
entrenamiento cada uno cuesta segundos.

## 6. Qué falta y por qué no se puede hacer todavía

La frontera entre tasa de quiebre y tasa de merma, que es el gráfico que mejor
explica el compromiso a una dirección de operaciones, necesita predicciones. Va
en el paso de simulación de la política.

También queda abierto el coste de capital inmovilizado. El módulo lo admite como
tasa anual y por defecto está en cero, porque el enunciado no lo menciona y
añadirlo sin base sería inventar un parámetro.

---

## Decisiones que salen de este paso

| # | Decisión | Afecta a |
|---|---|---|
| 1 | Rejilla de 17 niveles, acotada en 0,99 | Entrenamiento |
| 2 | Escenario principal: merma total; contraste: el del enunciado | Presentación |
| 3 | Presentar la sensibilidad como curva continua, no como dos casos | Presentación |
| 4 | Cada producto consulta su propio nivel, según tabla de política | Optimizador |
| 5 | Coste de capital disponible pero desactivado, por falta de base | Memoria técnica |
