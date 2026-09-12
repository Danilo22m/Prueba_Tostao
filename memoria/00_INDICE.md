# Índice del proyecto

**Caso A · Optimización de abastecimiento · Tostao**

Cada paso metodológico produce un informe con los hechos y un memo con la
interpretación. El informe lo genera el código y se regenera al ejecutar; el memo
está escrito a mano y se actualiza cuando cambian las conclusiones.

---

## Los pasos, en orden de ejecución

| # | Paso | Script | Informe | Memo |
|---|---|---|---|---|
| 1-2 | Auditoría e integridad del panel | `run_audit.py` | `01_auditoria.txt` | — |
| 3-4 | Análisis univariado y agregación a semana | `run_eda.py` | `02_univariado.txt` | `02` |
| 5-8 | Variables, particiones y líneas base | `run_features.py` | `03_variables_y_lineas_base.txt` | `03` |
| 9 | Costes y niveles de servicio | `run_costes.py` | `04_costes_y_niveles.txt` | `04` |
| 10 | Selección de familia | `run_modelos.py` | `05_seleccion_familia.txt` | `05` |
| 11 | Rejilla de niveles | `run_rejilla.py` | `06_rejilla_niveles.txt` | `06` |
| 12 | Diagnóstico e interpretabilidad | `run_diagnostico.py` | `07_diagnostico.txt` | `07` |
| 13 | Calibración conformal | `run_calibracion.py` | `08_calibracion.txt` | `08` |
| 14 | Optimizador del pedido | `run_pedidos.py` | `09_pedidos.txt` | `09` |
| 15 | Simulación de políticas y ahorro | `run_politicas.py` | `10_politicas.txt` | `10` |
| 16 | Tabla de pedidos de la semana siguiente | pendiente | — | — |
| 17 | Presentación ejecutiva | pendiente | — | — |

**Orden de ejecución.** Los scripts son independientes salvo que `run_modelos.py`
escribe los hiperparámetros que consumen los cuatro siguientes. El orden seguro
es el de la tabla.

## Documentos transversales

No corresponden a un paso: recogen decisiones que atraviesan varios.

| Documento | De qué trata |
|---|---|
| `T1_parametrizacion_relativa.md` | Por qué el modelo predice proporciones y no unidades, y qué cambió al hacerlo |
| `T2_escenario_del_sobrante.md` | Qué pasa si el producto sobrante se guarda en vez de tirarse. Es la única decisión de negocio abierta |

## Qué produce el pipeline

| Carpeta | Contenido | ¿Se regenera? |
|---|---|---|
| `salidas/informes/` | Diez informes en texto, solo hechos | Sí, en cada ejecución |
| `salidas/figuras/` | Veinticuatro gráficos | Sí |
| `salidas/parametros/` | Política de costes, rejilla, hiperparámetros, abanico, pedidos, ajustes | Sí |
| `memoria/` | Interpretación escrita a mano | No |

## Verificaciones automáticas

| Fichero | Qué comprueba |
|---|---|
| `tests/test_fuga.py` | Nueve verificaciones de aislamiento entre entrenamiento, validación y prueba |
| `tests/test_optimizador.py` | Ocho pruebas del optimizador con casos de respuesta conocida |

## Cómo reproducirlo entero

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt

for s in run_audit run_eda run_features run_costes run_modelos \
         run_rejilla run_diagnostico run_calibracion run_pedidos run_politicas; do
    ./.venv/bin/python $s.py
done

./.venv/bin/python tests/test_fuga.py
./.venv/bin/python tests/test_optimizador.py
```

Dos ejecuciones seguidas producen informes idénticos byte a byte.
