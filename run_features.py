"""Particion temporal, variables y lineas base del Caso A.

Genera:
    salidas/informes/03_variables_y_lineas_base.txt
    salidas/figuras/09_lineas_base.png
    salidas/figuras/10_barrido_ventana.png

Uso:
    ./.venv/bin/python run_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import baselines, bivariado, features, loaders, metrics  # noqa: E402
from caso_a import panel, paths, plots, splits  # noqa: E402

ANCHO = 84

#: Variables construidas que se evaluan como candidatas.
CANDIDATAS = [
    "rezago_1", "rezago_2", "rezago_3", "rezago_4",
    "media_2", "media_3", "media_4",
    "desv_2", "desv_3", "desv_4",
    "pendiente", "razon_ultima", "cv_reciente", "tamano_m2",
]


def barrido_ventanas(pnl: pd.DataFrame, particion: splits.Particion,
                     ventanas: range) -> pd.DataFrame:
    """Error de la media movil segun cuantas semanas promedie.

    Se evalua sobre las semanas de validacion, no sobre las de prueba. Elegir la
    longitud mirando la prueba seria ajustar un parametro contra el conjunto que
    debe quedar intacto, y dejaria la cifra final optimista.

    Las semanas de validacion son las de los pliegues de ventana expansiva, es
    decir las ultimas del tramo de entrenamiento.
    """
    ordenado = pnl.sort_values(baselines.CLAVE_SERIE + ["semana"]).copy()
    grupo = ordenado.groupby(baselines.CLAVE_SERIE, observed=True)[baselines.OBJETIVO]
    for v in ventanas:
        ordenado[f"mm{v}"] = grupo.transform(
            lambda s, v=v: s.shift(1).rolling(v, min_periods=v).mean()
        )
    semanas_validacion = tuple(
        validacion for _, validacion in splits.pliegues_expansivos(particion.entrenamiento)
    )
    validacion = splits.separar(ordenado, semanas_validacion)
    real = validacion[baselines.OBJETIVO].to_numpy(float)

    filas = []
    for v in ventanas:
        pred = validacion[f"mm{v}"].to_numpy(float)
        if np.isnan(pred).any():
            continue
        filas.append({"ventana": v, "WAPE": metrics.wape(real, pred),
                      "MAE": metrics.mae(real, pred), "R2": metrics.r2(real, pred)})
    return pd.DataFrame(filas)


def main() -> int:
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    pnl = panel.enriquecer(panel.a_semanal(tablas["ventas"]), tablas["catalogo"], tablas["tiendas"])
    particion = splits.desde_panel(pnl)

    partes = ["VARIABLES Y LINEAS BASE - CASO A", "=" * ANCHO]

    partes += ["", "", "1. DISENO DEL EXPERIMENTO", "=" * ANCHO, ""]
    partes.append(f"  {particion}")
    partes.append(f"  semanas 1-{particion.entrenamiento[0] - 1}: historia que consumen los rezagos, sin filas utilizables")
    partes.append("")
    partes.append("  pliegues de validacion, ventana expansiva:")
    for numero, (ajuste, validacion) in enumerate(splits.pliegues_expansivos(particion.entrenamiento), 1):
        partes.append(f"    {numero}: ajusta {list(ajuste)} -> valida semana {validacion}")

    partes += ["", "", "2. VARIABLES CONSTRUIDAS", "=" * ANCHO, ""]
    completo = features.construir(pnl)
    nuevas = [c for c in completo.columns if c not in pnl.columns]
    partes.append(f"  {len(nuevas)} variables: {', '.join(nuevas)}")
    features.verificar_sin_fuga(pnl, semana_corte=particion.entrenamiento[-1])
    partes.append("  prueba antifuga: superada, ninguna variable usa informacion posterior al corte")
    entrenamiento = splits.separar(completo, particion.entrenamiento).dropna(subset=nuevas)
    prueba = splits.separar(completo, particion.prueba).dropna(subset=nuevas)
    partes.append(f"  filas utilizables: {len(entrenamiento)} de entrenamiento, {len(prueba)} de prueba")

    partes += ["", "", "3. RELACION DE CADA VARIABLE CON EL OBJETIVO", "=" * ANCHO]
    partes += ["", "3.1 Correlacion marginal, sobre entrenamiento", "-" * ANCHO]
    partes.append(bivariado.relacion_con_objetivo(entrenamiento, CANDIDATAS).round(3).to_string(index=False))

    partes += ["", "3.2 Correlacion dentro de la serie, restada la media de cada una", "-" * ANCHO]
    intra = [c for c in CANDIDATAS if c != "tamano_m2"]
    partes.append(bivariado.relacion_intra_serie(entrenamiento, intra).round(4).to_string(index=False))

    partes += ["", "3.3 Redundancia entre variables", "-" * ANCHO]
    partes.append(bivariado.inflacion_varianza(entrenamiento, CANDIDATAS).round(2).to_string(index=False))

    partes += ["", "", "4. LINEAS BASE", "=" * ANCHO]
    con_base = baselines.calcular_todas(pnl)
    columnas = [c for c in con_base.columns if c.startswith("base: ")]
    tabla_prueba = None
    for etiqueta, semanas in (("4.1 Semanas de entrenamiento", particion.entrenamiento),
                              ("4.2 Semanas de prueba", particion.prueba)):
        sub = splits.separar(con_base, semanas).dropna(subset=columnas)
        real = sub[baselines.OBJETIVO].to_numpy(float)
        escala = metrics.mae(real, sub["base: media historica"].to_numpy(float))
        resultados = {
            c.replace("base: ", ""): metrics.resumen(real, sub[c].to_numpy(float), escala)
            for c in columnas
        }
        tabla = metrics.tabla_resumen(resultados)
        partes += ["", f"{etiqueta}, {len(sub)} filas", "-" * ANCHO]
        partes.append(tabla.round(4).to_string())
        if semanas == particion.prueba:
            tabla_prueba = tabla

    semanas_validacion = tuple(
        v for _, v in splits.pliegues_expansivos(particion.entrenamiento)
    )
    partes += ["", "", "5. LONGITUD OPTIMA DE LA MEDIA MOVIL", "=" * ANCHO, "",
              f"  Evaluado sobre las semanas de validacion {semanas_validacion}, no sobre prueba.", ""]
    barrido = barrido_ventanas(pnl, particion, range(2, 9))
    partes.append(barrido.round(4).to_string(index=False))

    figuras = [
        plots.comparacion_lineas_base(tabla_prueba, paths.FIGURAS),
        plots.barrido_ventana(barrido, paths.FIGURAS),
    ]
    partes += ["", "", "6. GRAFICOS GENERADOS", "=" * ANCHO, ""]
    partes += [f"  {f.relative_to(paths.RAIZ)}" for f in figuras]

    destino = paths.INFORMES / "03_variables_y_lineas_base.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Figuras: {len(figuras)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
