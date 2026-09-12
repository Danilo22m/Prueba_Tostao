"""Optimizador del pedido: del abanico de cuantiles a la cantidad a pedir.

Genera:
    salidas/informes/09_pedidos.txt
    salidas/parametros/pedidos.csv
    salidas/figuras/22_composicion_pedido.png

Uso:
    ./.venv/bin/python run_pedidos.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import costes, features, loaders, modelos, optimizador  # noqa: E402
from caso_a import panel, paths, plots, rejilla, splits  # noqa: E402

ANCHO = 84
FAMILIA = "regresion cuantilica (relativo)"

#: Escenario recomendado: en cafeteria el sobrante no se vende al dia siguiente.
ESCENARIO_PRINCIPAL = "con merma"


def main() -> int:  # noqa: PLR0915
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    catalogo, inventario = tablas["catalogo"], tablas["inventario"]
    pnl = panel.enriquecer(panel.a_semanal(tablas["ventas"]), catalogo, tablas["tiendas"])
    completo = features.construir(pnl)
    particion = splits.desde_panel(pnl)
    nuevas = [c for c in completo.columns if c not in pnl.columns]
    utilizable = completo.dropna(subset=nuevas)

    entrenamiento = splits.separar(utilizable, particion.entrenamiento)
    prueba = splits.separar(utilizable, particion.prueba)

    parametros = json.loads((paths.PARAMETROS / "hiperparametros.json").read_text(encoding="utf-8"))
    parametros = parametros["por_familia"].get(FAMILIA, {})
    niveles = costes.rejilla_niveles(catalogo)
    ajustados, correcciones = rejilla.entrenar_calibrado(
        modelos.FAMILIAS_AMBAS[FAMILIA], utilizable, particion, niveles, parametros
    )
    abanico = rejilla.predecir_calibrado(ajustados, correcciones, prueba)

    escenario = next(e for e in costes.ESCENARIOS if e.nombre == ESCENARIO_PRINCIPAL)
    restricciones = optimizador.Restricciones()
    pedidos = optimizador.calcular_pedidos(abanico, catalogo, inventario, escenario, restricciones)

    partes = ["PEDIDOS RECOMENDADOS - CASO A", "=" * ANCHO]
    partes += ["", f"  escenario de coste: {escenario.nombre} "
                   f"(se descarta el {escenario.fraccion_merma:.0%} del sobrante)",
               f"  familia: {FAMILIA}",
               f"  semanas simuladas: {list(particion.prueba)}",
               f"  redondeo: al entero {restricciones.redondeo}, multiplo de lote "
               f"{restricciones.multiplo}"]

    partes += ["", "", "1. VERIFICACIONES DE LA TABLA", "=" * ANCHO, ""]
    problemas = optimizador.verificar(pedidos, catalogo, escenario)
    if problemas:
        for problema in problemas:
            partes.append(f"  FALLO  {problema}")
    else:
        partes += ["  OK  ningun pedido negativo",
                   "  OK  todas las cantidades son enteras",
                   "  OK  el pedido mas el stock alcanza siempre el objetivo",
                   "  OK  donde el stock cubre el objetivo, el pedido es cero",
                   "  OK  cada producto usa el nivel de servicio que marcan sus costes",
                   "  OK  ningun objetivo queda por debajo del pronostico central"]

    partes += ["", "", "2. NIVEL DE SERVICIO Y COLCHON POR PRODUCTO", "=" * ANCHO, ""]
    por_producto = (
        pedidos.merge(catalogo[["id_producto", "nombre"]], on="id_producto")
        .groupby(["id_producto", "nombre"], observed=True)
        .agg(nivel=("nivel_servicio", "first"),
             pronostico=("pronostico", "mean"),
             objetivo=("objetivo", "mean"),
             colchon=("colchon", "mean"),
             pedido=("pedido", "mean"))
        .reset_index()
        .sort_values("nivel", ascending=False)
    )
    por_producto["colchon_pct"] = 100 * por_producto["colchon"] / por_producto["pronostico"]
    partes.append(por_producto.round(2).to_string(index=False))
    partes += ["", "  El colchon es la diferencia entre lo que se pide tener y lo que se espera",
               "  vender. Crece con el nivel de servicio, que a su vez crece con el margen."]

    partes += ["", "", "3. RESUMEN DE LA OPERACION", "=" * ANCHO, ""]
    ultima = pedidos[pedidos["semana"] == pedidos["semana"].max()]
    partes.append(f"  series con pedido               {len(ultima)}")
    partes.append(f"  unidades totales a pedir        {int(ultima['pedido'].sum()):,}")
    partes.append(f"  series cubiertas por el stock   {int(ultima['cubierto_por_stock'].sum())}")
    partes.append(f"  pedido medio por serie          {ultima['pedido'].mean():.1f}")
    partes.append(f"  pedido maximo                   {int(ultima['pedido'].max())}")
    partes.append(f"  stock medio en estanteria       {ultima['stock_actual'].mean():.1f}")

    partes += ["", "", "4. MUESTRA DE LA TABLA", "=" * ANCHO, ""]
    muestra = ultima.merge(catalogo[["id_producto", "nombre"]], on="id_producto")
    vista = muestra[muestra["id_tienda"].isin(["STORE_01", "STORE_08"])]
    vista = vista[["id_tienda", "nombre", "pronostico", "nivel_servicio",
                   "objetivo", "stock_actual", "pedido"]]
    vista.columns = ["tienda", "producto", "pronostico", "nivel", "objetivo", "stock", "pedido"]
    partes.append(vista.to_string(
        index=False,
        formatters={"pronostico": "{:.1f}".format, "nivel": "{:.2f}".format,
                    "objetivo": "{:.0f}".format, "pedido": "{:.0f}".format},
    ))

    partes += ["", "", "5. SENSIBILIDAD AL ESCENARIO DE COSTE", "=" * ANCHO, ""]
    filas_esc = []
    for alternativo in costes.ESCENARIOS:
        otros = optimizador.calcular_pedidos(abanico, catalogo, inventario, alternativo, restricciones)
        ult = otros[otros["semana"] == otros["semana"].max()]
        filas_esc.append({
            "escenario": alternativo.nombre,
            "merma_supuesta": f"{alternativo.fraccion_merma:.0%}",
            "nivel_medio": ult["nivel_servicio"].mean(),
            "objetivo_medio": ult["objetivo"].mean(),
            "unidades_a_pedir": int(ult["pedido"].sum()),
        })
    partes.append(pd.DataFrame(filas_esc).round(3).to_string(index=False))

    ruta_csv = paths.PARAMETROS / "pedidos.csv"
    pedidos.to_csv(ruta_csv, index=False, encoding="utf-8")
    figura = plots.composicion_pedido(por_producto, paths.FIGURAS)

    partes += ["", "", "6. FICHEROS GENERADOS", "=" * ANCHO, ""]
    partes.append(f"  {ruta_csv.relative_to(paths.RAIZ)}")
    partes.append(f"  {figura.relative_to(paths.RAIZ)}")

    destino = paths.INFORMES / "09_pedidos.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Verificaciones: {'todas OK' if not problemas else f'{len(problemas)} FALLOS'}")
    return 1 if problemas else 0


if __name__ == "__main__":
    raise SystemExit(main())
