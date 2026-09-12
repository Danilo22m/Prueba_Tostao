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

## Cómo ejecutarlo

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python main.py
```

Eso corre los once pasos en orden y después las dos baterías de verificación.
Tarda alrededor de tres minutos y medio. Dos ejecuciones seguidas producen
informes idénticos byte a byte.

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
fallar a mitad de una ejecución larga.

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

## Cómo está organizado

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

**Informes y memorias son cosas distintas y no se mezclan.** El informe lo genera
el código y contiene únicamente hechos derivados de los datos, sin una sola cifra
escrita a mano: si se ejecuta con otros datos, el informe cambia entero. La
memoria la escribo yo y contiene las conclusiones, las decisiones y lo que no
funcionó. El índice de todo está en `memoria/00_INDICE.md`.

### Los módulos

| Grupo | Módulos |
|---|---|
| Datos | `paths`, `schemas`, `loaders`, `audit`, `profiling` |
| Exploración | `eda_diario`, `panel`, `tablas`, `bivariado`, `plots` |
| Preparación | `splits`, `features`, `metrics`, `baselines` |
| Negocio | `costes` |
| Modelado | `modelos`, `evaluacion`, `ajuste`, `rejilla`, `diagnostico`, `calibracion` |
| Decisión | `optimizador`, `politicas` |

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

## Qué falta

- La presentación ejecutiva.
- Inventario con fecha. El fichero actual no dice a qué momento corresponde el
  stock, y para pedir la semana 14 hace falta el del cierre de la 13.
- Respuesta a tres restricciones operativas: múltiplo de lote, techo físico por
  tienda y política de redondeo. Están implementadas y probadas, desactivadas
  porque nadie ha dicho qué valores toman.

## Entorno

Python 3.13. Las versiones están fijadas en `requirements.txt`.
