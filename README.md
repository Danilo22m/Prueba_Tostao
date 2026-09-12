# Caso A · Optimización de Abastecimiento

Prueba técnica de Data Scientist Senior · Tostao

Pronóstico semanal de demanda por SKU y tienda, y política de pedido derivada de
los costes de cada producto. El entregable no es un pronóstico: es la cantidad
que cada tienda tiene que pedir.

---

## El problema, en una frase

Pedir de menos cuesta el margen que se deja de ganar. Pedir de más cuesta el
producto que sobra. La cantidad óptima no es la demanda esperada, es el cuantil
de la demanda que iguala esos dos costes:

```
nivel de servicio  =  margen / (margen + coste del sobrante)
objetivo           =  predicción del modelo a ese nivel, redondeada
pedido             =  máximo(0, objetivo − stock en estantería)
```

En esa fórmula no aparece la demanda. El nivel depende solo de dos precios, y
cada producto tiene el suyo. Todo el proyecto existe para que esas tres líneas
sean defendibles.

## Los datos

`Caso A/01_supply_optimization`, cinco tablas que nunca se modifican:

| Fichero | Contenido |
|---|---|
| `ventas_historicas.csv` | Ventas diarias por tienda y producto |
| `catalogo_productos.csv` | Precio, coste unitario y coste de almacenamiento |
| `inventario_actual.csv` | Stock disponible por serie |
| `maestro_tiendas.csv` | Ciudad y superficie |
| `ground_truth_trends.csv` | Patrón real de cada serie, usado solo para contrastar |

Agregadas a semana dan un panel de **2.080 filas**: 20 tiendas × 8 productos ×
13 semanas. Las cuatro primeras semanas se consumen en construir los rezagos.

## Instalación y ejecución

Requiere **Python 3.13**. Las ocho dependencias están fijadas a versión exacta en
`requirements.txt`.

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python main.py
```

`main.py` corre los once pasos en orden y después las dos baterías de
verificación. Tarda alrededor de tres minutos y medio. Dos ejecuciones seguidas
producen informes idénticos byte a byte.

Para iterar sobre un paso sin repetir los anteriores:

```bash
./.venv/bin/python main.py --listar          # los pasos y sus claves
./.venv/bin/python main.py --solo entrega    # un único paso
./.venv/bin/python main.py --desde rejilla   # desde ese paso hasta el final
./.venv/bin/python main.py --hasta costes    # hasta ese paso
./.venv/bin/python main.py --sin-pruebas     # omitir las verificaciones
```

Cada paso declara qué artefactos necesita de los anteriores. Si faltan, el
proceso se detiene con un mensaje que dice cuál y quién lo produce, en lugar de
fallar a mitad de una ejecución larga. La única dependencia real entre scripts es
que la selección de familia escribe los hiperparámetros que consumen los cinco
pasos siguientes.

---

# Arquitectura de la solución

## Tres capas, y una regla

La solución está partida en tres capas. La regla es que cada una habla solo con
la de abajo.

| Capa | Qué hace | Módulos |
|---|---|---|
| **Datos** | Lee los CSV, los valida contra un esquema y construye el panel semanal | `paths`, `schemas`, `loaders`, `audit`, `profiling`, `panel` |
| **Modelado** | Convierte el panel en predicciones por nivel de servicio | `features`, `splits`, `metrics`, `baselines`, `modelos`, `evaluacion`, `ajuste`, `rejilla`, `diagnostico`, `calibracion` |
| **Decisión** | Convierte las predicciones en unidades a pedir | `costes`, `optimizador`, `politicas` |

La capa de datos no sabe que existen los modelos. La de modelado no sabe qué
precio tiene un producto. La de decisión no sabe qué modelo hay debajo: le da
igual que sea una regresión cuantílica o una media móvil.

Esa separación es lo que permite que el paso 10 compare siete familias distintas
sin tocar una línea de la lógica de pedido.

Aparte quedan `eda_diario`, `tablas`, `bivariado` y `plots`, que solo producen
material de lectura y no participan en la decisión.

## El recorrido de un dato

```
5 CSV originales
   │  loaders + schemas          se validan tipos, rangos y claves
   │  audit                      integridad: series completas, sin duplicados
   ↓
ventas diarias
   │  panel.a_semanal            se suman por semana, se comprueba que el total cuadre
   │  panel.enriquecer           se unen catálogo y maestro de tiendas
   ↓
panel semanal                    2.080 filas: 160 series × 13 semanas
   │  features.construir         rezagos, medias móviles, pendiente
   │                             toda variable se calcula de t-1 hacia atrás
   ↓
variables de historia
   │  splits.desde_panel         entrenamiento 5-10, prueba 11-13, predicción 14
   ↓
particiones congeladas
   │  costes.rejilla_niveles     los precios deciden qué 17 niveles hay que entrenar
   ↓
rejilla de niveles
   │  rejilla.entrenar_calibrado 17 modelos de la familia elegida
   │                             + corrección conformal fuera de pliegue
   ↓
abanico de cuantiles             una columna por nivel de servicio
   │  optimizador.calcular_pedidos  cada producto consulta su nivel
   │                                se resta el stock, se redondea
   ↓
tabla de pedidos
```

## El contrato entre capas

Las capas se comunican por dos tablas, y solo por ellas.

**El panel** conecta datos con modelado. Una fila por serie y semana, con la
demanda observada y los atributos fijos de tienda y producto.

**El abanico** conecta modelado con decisión. Lleva las claves de serie, la
semana y una columna por nivel de servicio. Cualquier familia de modelos que
produzca esa tabla encaja sin cambiar nada más, y de hecho el paso 15 la usa para
simular políticas alternativas con el mismo código.

## Las cuatro decisiones que la definen

**Los costes no entran al modelo, lo configuran.** Es la decisión central y la
menos obvia. El modelo nunca ve un precio. Los precios se usan dos veces y las
dos fuera del modelo: primero para calcular qué niveles de servicio hay que
entrenar, después para decidir cuál consultar ante cada producto. Si mañana
cambia el precio del Tinto, no hay que reentrenar nada mientras su nivel siga en
la rejilla.

**Diecisiete modelos, no uno.** Un estimador de cuantiles solo devuelve el
cuantil para el que fue entrenado. Como cada producto necesita el suyo en cada
escenario de coste, se entrena la misma familia con los mismos hiperparámetros
diecisiete veces, una por nivel. Cuando el proyecto dice "el modelo ganador" se
refiere a esos diecisiete estimadores.

**La lógica no sabe que existen los informes.** Todo lo que piensa vive en
`src/caso_a/`. Los once `run_*.py` llaman a esa lógica y escriben texto. Ninguno
contiene una fórmula. La consecuencia práctica es que las veinte verificaciones
pueden probar la lógica sin ejecutar el pipeline.

**El código escribe en `salidas/`, nunca en `memoria/`.** El informe se regenera
entero en cada ejecución, así que no puede contener una sola cifra escrita a
mano: con otros datos, cambia entero. La memoria la escribe una persona y
sobrevive a las ejecuciones. Esa frontera es lo que hace que los informes sigan
siendo válidos si el ejercicio se repite con otro panel.

## Los ficheros

```
main.py                  punto de entrada: orden, dependencias y tramos
run_*.py                 un script por paso, ejecutable suelto
src/caso_a/              la lógica, sin nada de presentación
tests/                   verificaciones de aislamiento temporal y del optimizador
salidas/informes/        once informes en texto, solo hechos
salidas/figuras/         veinticinco gráficos
salidas/parametros/      política de costes, rejilla, pedidos, ajustes
memoria/                 la interpretación, escrita a mano
```

El índice de la metodología está en `memoria/00_INDICE.md`.

---

## Los pasos

| # | Paso | Script | Informe |
|---|---|---|---|
| 1-2 | Auditoría e integridad del panel | `run_audit.py` | `01_auditoria.txt` |
| 3-4 | Análisis univariado y agregación a semana | `run_eda.py` | `02_univariado.txt` |
| 5-8 | Variables, particiones y líneas base | `run_features.py` | `03_variables_y_lineas_base.txt` |
| 9 | Costes y niveles de servicio | `run_costes.py` | `04_costes_y_niveles.txt` |
| 10 | Selección de familia | `run_modelos.py` | `05_seleccion_familia.txt` |
| 11 | Rejilla de niveles | `run_rejilla.py` | `06_rejilla_niveles.txt` |
| 12 | Diagnóstico e interpretabilidad | `run_diagnostico.py` | `07_diagnostico.txt` |
| 13 | Calibración conformal | `run_calibracion.py` | `08_calibracion.txt` |
| 14 | Optimizador del pedido | `run_pedidos.py` | `09_pedidos.txt` |
| 15 | Simulación de políticas y ahorro | `run_politicas.py` | `10_politicas.txt` |
| 16 | Entrega: pedido de la semana siguiente | `run_entrega.py` | `11_entrega.txt` |

Los pasos 1 a 15 miden, con las semanas 11 a 13 retenidas. El paso 16 reentrena
con las trece semanas completas y produce el pedido de la semana 14, que no
tiene demanda con la que compararse y por tanto no lleva métricas.

## Cómo se evita engañarse

Es la parte del proyecto que más código tiene, porque es donde se pierden estos
ejercicios.

- **Particiones congeladas antes de modelar.** Entrenamiento 5-10, prueba 11-13,
  y la prueba no se toca hasta el final. Las semanas se deducen del panel: no hay
  ninguna constante con el número de semanas.
- **Validación con ventana expansiva** dentro del entrenamiento. Los
  hiperparámetros se eligen ahí, nunca en la prueba.
- **Veinte verificaciones automáticas.** Doce de aislamiento temporal en
  `tests/test_fuga.py`, incluida una instrumentada que registra cada semana que
  toca la búsqueda de hiperparámetros, y un control negativo que exige que más
  datos sí cambien el modelo. Ocho del optimizador en `tests/test_optimizador.py`
  con casos de respuesta conocida, dos de los cuales exigen que el proceso falle.
- **Las variables se reconstruyen ocultando el futuro** y se exige que salgan
  idénticas. Y al revés: añadir la fila de la semana a entregar no puede mover
  ninguna variable del pasado.
- **Calibración conformal aplicada dentro del pipeline**, con predicciones fuera
  de pliegue, antes de que nadie use las predicciones. No es un análisis
  posterior: es una corrección al modelo.

## Qué salió

Está en los informes y desarrollado en las memorias. Dos titulares:

**La regla aporta más que el modelo.** La descomposición factorial del paso 15
atribuye la mayor parte del ahorro a pedir por nivel de servicio en lugar de por
pronóstico central, y una parte menor al modelo frente a una media móvil. Es un
resultado incómodo y se presenta sin maquillar, porque cambia qué hay que
defender ante negocio.

**El supuesto de merma domina el resultado.** La misma tabla de pronósticos da un
ahorro del 92,6 % si se supone que el producto sobrante se vende al día
siguiente, y del 5,2 % si se supone que se tira. Dos órdenes de magnitud a partir
de los mismos datos y el mismo modelo. Recomendamos el segundo, que es lo
habitual en cafetería, y llevamos la tabla completa. Está en
`memoria/T2_escenario_del_sobrante.md`.

La única mejora genuina de modelado fue **predecir proporciones en vez de
unidades**, dividiendo por la media de las cuatro últimas semanas y
multiplicando después. Corrigió el sesgo de volumen, estabilizó la cola y dejó
los coeficientes interpretables como porcentajes. Está en
`memoria/T1_parametrizacion_relativa.md`.

---

# Próximos pasos

Lo que sigue no está implementado. Es la propuesta de cómo llevar esto de una
prueba técnica a un proceso que la operación use cada semana. Son dos frentes
independientes: primero demostrar que el ahorro existe fuera del papel, después
automatizarlo.

## Frente 1 · El piloto

Antes de automatizar nada hay que comprobar que el ahorro simulado se materializa
en tienda. La simulación del paso 15 compara políticas sobre la misma demanda
observada, y eso tiene un límite: supone que pedir distinto no cambia lo que se
vende. En la realidad sí lo cambia, porque una estantería mejor surtida vende más
y una vacía pierde ventas que nunca se registran.

**Diseño.** Seis u ocho tiendas durante seis u ocho semanas. La mitad aplica el
pedido recomendado, la otra mitad sigue con el método actual y hace de control.
Las parejas se forman por volumen y categoría de tienda, para que la comparación
no confunda el efecto de la política con el de tener tiendas distintas. Es
preferible separar por tienda y no por semana: alternar semanas dentro de la
misma tienda contamina el resultado, porque el inventario que sobra de una semana
entra en la siguiente.

**Qué se mide.** Unidades vendidas, unidades sobrantes al cierre y roturas de
stock, todo por tienda y producto. Con esas tres cifras y los costes del catálogo
se calcula el coste real de cada política, que es la única comparación que
importa. Conviene además registrar la cobertura observada por nivel de servicio:
si un producto con nivel 0,68 se queda corto mucho más del 32 % de las semanas,
la calibración no está funcionando en producción.

**Qué hay que cerrar antes de arrancar.** Tres cosas, todas de negocio y ninguna
técnica. El supuesto de merma, que es el que decide si el ahorro es del 5 % o del
92 %. El inventario con fecha, porque hoy no se sabe a qué momento corresponde el
stock. Y las tres restricciones operativas que ya están implementadas pero
desactivadas: múltiplo de lote, techo físico por tienda y política de redondeo.

**El criterio de salida se fija antes de empezar.** Qué diferencia de coste entre
grupo piloto y grupo control justifica desplegar a toda la red, y qué resultado
obliga a parar. Decidirlo después de ver los números es la forma más común de
convencerse de un resultado que no está.

## Frente 2 · Automatización en GCP

La arquitectura por capas está pensada para esto. Solo la capa de datos cambia:
en lugar de leer CSV de disco, lee tablas de BigQuery. Las capas de modelado y
decisión no se tocan, porque no saben de dónde vienen los datos.

```
POS / ERP
   │  exporta ventas e inventario, a diario
   ↓
Cloud Storage                     zona de aterrizaje, un prefijo por fecha
   │  load job                    validación de esquema antes de cargar
   ↓
BigQuery · capa cruda             tablas particionadas por fecha
   │  vistas / scheduled query    agregación a semana y unión con maestros
   ↓
BigQuery · capa curada            el panel semanal, listo para el pipeline
   │
   ├── Cloud Scheduler            dispara una vez por semana, tras el cierre
   │      ↓ Pub/Sub
   │   Cloud Run Job              ejecuta main.py en un contenedor
   │      │                       imagen versionada en Artifact Registry
   │      ↓
   ├── BigQuery · pedidos         una fila por tienda, producto y semana
   │                              con id de ejecución y versión del modelo
   ├── Cloud Storage · artefactos informes, figuras, hiperparámetros, calibración
   ↓
Looker Studio                     el informe que ve la operación
```

**Ingesta y almacenamiento.** El export del punto de venta cae en un bucket de
Cloud Storage, un prefijo por fecha. Un load job lo lleva a BigQuery validando el
esquema, que es el mismo que ya declara `schemas.py`. La capa cruda guarda el
dato tal cual llegó y no se modifica nunca. Una scheduled query construye encima
la capa curada, que es el panel semanal que hoy produce `panel.py`. Las tablas se
particionan por fecha y se agrupan por tienda y producto, que es como se
consultan.

**Ejecución.** Cloud Scheduler dispara el proceso una vez por semana, después del
cierre del domingo. Para un pipeline que tarda minutos y arrastra ocho
dependencias, el sitio correcto es un Cloud Run Job y no una Cloud Function: la
función encaja para el pegamento ligero, no para el lote. El contenedor es este
mismo repositorio con `main.py` como punto de entrada, y la imagen queda
versionada en Artifact Registry, de modo que siempre se sabe qué código produjo
qué pedido.

**Salidas.** Los pedidos se escriben en una tabla de BigQuery con una fila por
tienda, producto y semana, más el identificador de ejecución y la versión del
modelo. Eso permite reconstruir cualquier pedido pasado y comparar lo que se
pidió con lo que después se vendió. Los informes, las figuras y los parámetros
del modelo van a Cloud Storage, versionados por ejecución.

**El informe.** Looker Studio conecta directamente a la tabla de pedidos. Tres
vistas bastan. La primera es operativa: el pedido de la semana, filtrable por
tienda y producto, que es lo que descarga el responsable de tienda. La segunda es
de seguimiento: cobertura observada frente al nivel de servicio prometido, y
error real del pronóstico una vez llega la demanda de esa semana. La tercera es
económica: coste de faltante y de sobrante acumulados, comparados con lo que
habría costado repetir el pedido de la semana anterior.

**Vigilancia.** `main.py` ya devuelve código de salida distinto de cero cuando
una verificación falla. Enganchado a Cloud Logging, eso se convierte en una
alerta de Cloud Monitoring: si el pipeline falla o si alguna de las veinte
comprobaciones no pasa, alguien se entera antes de que las tiendas pidan con una
tabla rota. Merece la pena añadir una alerta más, sobre el propio resultado: si
el error real se separa de forma sostenida del medido en la prueba, el modelo se
ha quedado viejo y toca reentrenar.
