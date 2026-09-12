"""Entrega final: reentrenar con todas las semanas y pedir la semana siguiente.

Los pasos anteriores miden. Este entrega. La diferencia es que aqui no se
reserva ninguna semana: el modelo se ajusta con todo lo observado y predice la
semana que todavia no ha ocurrido, que es la que la tienda tiene que pedir.

Como esa semana no tiene demanda real, este paso no produce ninguna metrica de
error. Su validez viene de los pasos 10 a 15, que ya se midieron en semanas
retenidas. Lo que si se comprueba aqui son las propiedades de la tabla.

Genera:
    salidas/informes/11_entrega.txt
    salidas/parametros/pedidos_semana_siguiente.csv
    salidas/figuras/25_pedido_por_tienda.png

Uso:
    ./.venv/bin/python run_entrega.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import calibracion, costes, features, loaders, modelos  # noqa: E402
from caso_a import optimizador, panel, paths, plots, rejilla, splits  # noqa: E402

ANCHO = 84
FAMILIA = "regresion cuantilica (relativo)"
CLAVE_SERIE = ["id_tienda", "id_producto"]

#: Escenario recomendado: en cafeteria el sobrante no se vende al dia siguiente.
ESCENARIO_PRINCIPAL = "con merma"

#: Tiendas que se muestran en la muestra del informe. La tabla entera va al CSV.
TIENDAS_MUESTRA = ("STORE_01", "STORE_08")


def _utilizable(marco: pd.DataFrame, columnas_base: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Descarta las filas sin historia suficiente para tener todas las variables."""
    nuevas = [c for c in marco.columns if c not in columnas_base]
    return marco.dropna(subset=nuevas), nuevas


def main() -> int:  # noqa: PLR0915
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    catalogo, inventario = tablas["catalogo"], tablas["inventario"]
    pnl = panel.enriquecer(panel.a_semanal(tablas["ventas"]), catalogo, tablas["tiendas"])

    particion_evaluacion = splits.desde_panel(pnl)
    particion = splits.para_entrega(pnl)
    semana_entregada = particion.prediccion

    # El panel se amplia con una fila por serie para la semana que se pide. Las
    # variables de esa fila salen de las semanas reales que la preceden.
    ampliado = features.construir(features.extender_al_futuro(pnl, semana_entregada))
    utilizable, nuevas = _utilizable(ampliado, list(pnl.columns))
    futuro = splits.separar(utilizable, semana_entregada)

    parametros = json.loads((paths.PARAMETROS / "hiperparametros.json").read_text(encoding="utf-8"))
    parametros = parametros["por_familia"].get(FAMILIA, {})
    niveles = costes.rejilla_niveles(catalogo)
    clase = modelos.FAMILIAS_AMBAS[FAMILIA]

    ajustados, correcciones = rejilla.entrenar_calibrado(
        clase, utilizable, particion, niveles, parametros
    )
    abanico = rejilla.predecir_calibrado(ajustados, correcciones, futuro)

    escenario = next(e for e in costes.ESCENARIOS if e.nombre == ESCENARIO_PRINCIPAL)
    restricciones = optimizador.Restricciones()
    pedidos = optimizador.calcular_pedidos(
        abanico, catalogo, inventario, escenario, restricciones
    )
    # La demanda de la semana entregada no existe todavia; la columna solo
    # contendria ausentes y confundiria a quien lea el fichero.
    pedidos = pedidos.drop(columns=["unidades_vendidas"], errors="ignore")

    partes = ["ENTREGA: PEDIDO DE LA SEMANA SIGUIENTE - CASO A", "=" * ANCHO]
    partes += ["",
               f"  semana entregada: {semana_entregada} (sin demanda observada)",
               f"  entrenamiento: semanas {particion.entrenamiento[0]}-"
               f"{particion.entrenamiento[-1]} ({len(particion.entrenamiento)} semanas)",
               f"  familia: {FAMILIA}",
               f"  escenario de coste: {escenario.nombre} "
               f"(se descarta el {escenario.fraccion_merma:.0%} del sobrante)",
               f"  redondeo: al entero {restricciones.redondeo}, multiplo de lote "
               f"{restricciones.multiplo}",
               "",
               "  Este paso no calcula error de prediccion. La semana entregada no tiene",
               "  demanda con la que compararse; las metricas estan en los informes 05 a 10."]

    partes += ["", "", "1. VERIFICACIONES DE LA ENTREGA", "=" * ANCHO, ""]
    comprobaciones: list[tuple[str, bool]] = []

    try:
        features.verificar_extension(pnl)
        extension_limpia = True
    except AssertionError:
        extension_limpia = False
    comprobaciones.append(
        ("ampliar el panel no altera ninguna variable de las semanas pasadas", extension_limpia)
    )

    series_panel = pnl[CLAVE_SERIE].drop_duplicates()
    comprobaciones += [
        ("la semana entregada no aparece en el entrenamiento",
         semana_entregada not in particion.entrenamiento),
        ("hay una fila por serie del panel, sin duplicados",
         len(pedidos) == len(series_panel) and not pedidos.duplicated(CLAVE_SERIE).any()),
        ("todas las series del panel reciben pedido",
         len(pedidos.merge(series_panel, on=CLAVE_SERIE)) == len(series_panel)),
        ("la tabla entregada no contiene demanda observada",
         "unidades_vendidas" not in pedidos.columns),
        ("el entrenamiento usa todas las semanas con variables completas",
         len(particion.entrenamiento) == utilizable.loc[
             utilizable["semana"] < semana_entregada, "semana"].nunique()),
    ]

    for texto, ok in comprobaciones:
        partes.append(f"  {'OK  ' if ok else 'FALLO'}  {texto}")

    problemas = optimizador.verificar(pedidos, catalogo, escenario)
    if problemas:
        for problema in problemas:
            partes.append(f"  FALLO  {problema}")
    else:
        partes += ["  OK    ningun pedido negativo",
                   "  OK    todas las cantidades son enteras",
                   "  OK    el pedido mas el stock alcanza siempre el objetivo",
                   "  OK    donde el stock cubre el objetivo, el pedido es cero",
                   "  OK    cada producto usa el nivel de servicio que marcan sus costes",
                   "  OK    ningun objetivo queda por debajo del pronostico central"]
    problemas += [texto for texto, ok in comprobaciones if not ok]

    partes += ["", "", "2. QUE CAMBIA AL ENTRENAR CON TODAS LAS SEMANAS", "=" * ANCHO, ""]
    filas_particion = []
    for nombre, cual in (("evaluacion", particion_evaluacion), ("entrega", particion)):
        entrena = splits.separar(utilizable, cual.entrenamiento)
        filas_particion.append({
            "particion": nombre,
            "semanas_entrenamiento": len(cual.entrenamiento),
            "primera": cual.entrenamiento[0],
            "ultima": cual.entrenamiento[-1],
            "filas_ajuste": len(entrena),
            "pliegues_calibracion": len(splits.pliegues_expansivos(cual.entrenamiento)),
            "semanas_retenidas": len(cual.prueba),
        })
    partes.append(pd.DataFrame(filas_particion).to_string(index=False))
    partes += ["",
               "  La particion de evaluacion reserva semanas para medir. La de entrega no",
               "  reserva ninguna, porque ya no queda nada que medir con ellas."]

    fuera_evaluacion = calibracion.predicciones_fuera_de_pliegue(
        clase, utilizable, particion_evaluacion, niveles, parametros
    )
    ajustes_evaluacion = calibracion.calcular_ajustes(fuera_evaluacion)
    comparacion = (
        calibracion.tabla_ajustes(ajustes_evaluacion)[["nivel", "desplazamiento"]]
        .rename(columns={"desplazamiento": "desplaz_evaluacion"})
        .merge(
            calibracion.tabla_ajustes(correcciones)[
                ["nivel", "cobertura_fuera_pliegue", "desplazamiento"]
            ].rename(columns={"desplazamiento": "desplaz_entrega"}),
            on="nivel",
        )
    )
    comparacion["diferencia"] = comparacion["desplaz_entrega"] - comparacion["desplaz_evaluacion"]
    partes += ["", "  Correccion conformal recalculada con la historia completa:", ""]
    partes.append(comparacion.round(3).to_string(index=False))
    partes += ["",
               f"  observaciones fuera de pliegue: {len(fuera_evaluacion)} en evaluacion, "
               f"{next(iter(correcciones.values())).n_calibracion} en entrega"]

    partes += ["", "", "3. PEDIDO POR PRODUCTO", "=" * ANCHO, ""]
    por_producto = (
        pedidos.merge(catalogo[["id_producto", "nombre"]], on="id_producto")
        .groupby(["id_producto", "nombre"], observed=True)
        .agg(nivel=("nivel_servicio", "first"),
             pronostico=("pronostico", "mean"),
             objetivo=("objetivo", "mean"),
             colchon=("colchon", "mean"),
             stock=("stock_actual", "mean"),
             pedido_medio=("pedido", "mean"),
             pedido_total=("pedido", "sum"),
             tiendas_sin_pedido=("cubierto_por_stock", "sum"))
        .reset_index()
        .sort_values("nivel", ascending=False)
    )
    partes.append(por_producto.round(2).to_string(index=False))
    partes += ["",
               "  El colchon es la diferencia entre lo que se pide tener y lo que se espera",
               "  vender. Crece con el nivel de servicio, que a su vez crece con el margen."]

    partes += ["", "", "4. PEDIDO POR TIENDA", "=" * ANCHO, ""]
    por_tienda = (
        pedidos.groupby("id_tienda", observed=True)
        .agg(objetivo=("objetivo", "sum"),
             stock=("stock_actual", "sum"),
             pedido=("pedido", "sum"),
             series_sin_pedido=("cubierto_por_stock", "sum"))
        .reset_index()
        .sort_values("pedido", ascending=False)
    )
    partes.append(por_tienda.round(1).to_string(index=False))

    partes += ["", "", "5. RESUMEN DE LA OPERACION", "=" * ANCHO, ""]
    partes.append(f"  series en la tabla              {len(pedidos)}")
    partes.append(f"  unidades totales a pedir        {int(pedidos['pedido'].sum()):,}")
    partes.append(f"  objetivo total en estanteria    {int(pedidos['objetivo'].sum()):,}")
    partes.append(f"  stock que ya esta               {int(pedidos['stock_actual'].sum()):,}")
    partes.append(f"  series cubiertas por el stock   {int(pedidos['cubierto_por_stock'].sum())}")
    partes.append(f"  pedido medio por serie          {pedidos['pedido'].mean():.1f}")
    partes.append(f"  pedido maximo                   {int(pedidos['pedido'].max())}")

    partes += ["", "", "6. COHERENCIA CON EL PATRON DECLARADO DE CADA SERIE", "=" * ANCHO, ""]
    variacion = futuro[CLAVE_SERIE + ["media_4"]].merge(
        pedidos[CLAVE_SERIE + ["pronostico"]], on=CLAVE_SERIE
    )
    variacion["variacion_pct"] = 100 * (variacion["pronostico"] / variacion["media_4"] - 1)
    variacion = variacion.merge(tablas["tendencias"], on=CLAVE_SERIE, how="left")
    resumen_patron = (
        variacion.groupby("trend_type", observed=True)["variacion_pct"]
        .agg(series="size", mediana="median", media="mean")
        .reset_index()
        .sort_values("mediana", ascending=False)
    )
    partes.append(resumen_patron.round(2).to_string(index=False))
    partes += ["",
               "  Variacion del pronostico de la semana entregada frente a la media de las",
               "  cuatro ultimas semanas observadas, por patron declarado en el fichero de",
               "  tendencias. El patron no entra al modelo: sirve solo como contraste externo."]

    partes += ["", "", "7. MUESTRA DE LA TABLA ENTREGADA", "=" * ANCHO, ""]
    muestra = pedidos.merge(catalogo[["id_producto", "nombre"]], on="id_producto")
    vista = muestra[muestra["id_tienda"].isin(TIENDAS_MUESTRA)]
    vista = vista[["id_tienda", "nombre", "pronostico", "nivel_servicio",
                   "objetivo", "stock_actual", "pedido"]]
    vista.columns = ["tienda", "producto", "pronostico", "nivel", "objetivo", "stock", "pedido"]
    partes.append(vista.to_string(
        index=False,
        formatters={"pronostico": "{:.1f}".format, "nivel": "{:.2f}".format,
                    "objetivo": "{:.0f}".format, "stock": "{:.0f}".format,
                    "pedido": "{:.0f}".format},
    ))
    partes += ["", f"  Se muestran {len(TIENDAS_MUESTRA)} tiendas. La tabla completa esta en el CSV."]

    partes += ["", "", "8. SENSIBILIDAD AL ESCENARIO DE COSTE", "=" * ANCHO, ""]
    filas_esc = []
    for alternativo in costes.ESCENARIOS:
        otros = optimizador.calcular_pedidos(
            abanico, catalogo, inventario, alternativo, restricciones
        )
        filas_esc.append({
            "escenario": alternativo.nombre,
            "merma_supuesta": f"{alternativo.fraccion_merma:.0%}",
            "nivel_medio": otros["nivel_servicio"].mean(),
            "objetivo_total": int(otros["objetivo"].sum()),
            "unidades_a_pedir": int(otros["pedido"].sum()),
            "series_sin_pedido": int(otros["cubierto_por_stock"].sum()),
        })
    partes.append(pd.DataFrame(filas_esc).round(3).to_string(index=False))
    partes += ["",
               "  La eleccion del escenario es una decision de negocio, no del modelo. Las",
               "  tres columnas de pedido salen del mismo abanico de cuantiles."]

    ruta_csv = paths.PARAMETROS / "pedidos_semana_siguiente.csv"
    pedidos.to_csv(ruta_csv, index=False, encoding="utf-8")
    figura = plots.pedido_por_tienda(pedidos, paths.FIGURAS)

    partes += ["", "", "9. FICHEROS GENERADOS", "=" * ANCHO, ""]
    partes.append(f"  {ruta_csv.relative_to(paths.RAIZ)}")
    partes.append(f"  {figura.relative_to(paths.RAIZ)}")

    destino = paths.INFORMES / "11_entrega.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Verificaciones: {'todas OK' if not problemas else f'{len(problemas)} FALLOS'}")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
