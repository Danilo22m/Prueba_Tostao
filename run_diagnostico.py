"""Diagnostico del modelo elegido: donde falla y por que predice lo que predice.

Genera:
    salidas/informes/07_diagnostico.txt
    salidas/figuras/18_error_por_grupo.png
    salidas/figuras/19_residuales.png
    salidas/figuras/20_importancia.png

Uso:
    ./.venv/bin/python run_diagnostico.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import costes, diagnostico, features, loaders, modelos  # noqa: E402
from caso_a import panel, paths, plots, rejilla, splits  # noqa: E402

ANCHO = 84
FAMILIA = "regresion cuantilica (relativo)"
NIVEL_CENTRAL = "q0.50"
NIVEL_OPERACION = 0.65


def main() -> int:  # noqa: PLR0915
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    catalogo = tablas["catalogo"]
    pnl = panel.enriquecer(panel.a_semanal(tablas["ventas"]), catalogo, tablas["tiendas"])
    completo = features.construir(pnl)
    particion = splits.desde_panel(pnl)
    nuevas = [c for c in completo.columns if c not in pnl.columns]
    utilizable = completo.dropna(subset=nuevas)

    entrenamiento = splits.separar(utilizable, particion.entrenamiento)
    prueba = splits.separar(utilizable, particion.prueba)

    ruta_hiper = paths.PARAMETROS / "hiperparametros.json"
    parametros = json.loads(ruta_hiper.read_text(encoding="utf-8"))["por_familia"].get(FAMILIA, {})
    clase = modelos.FAMILIAS_AMBAS[FAMILIA]

    niveles = costes.rejilla_niveles(catalogo)
    ajustados, correcciones = rejilla.entrenar_calibrado(
        clase, utilizable, particion, niveles, parametros
    )
    abanico = rejilla.predecir_calibrado(ajustados, correcciones, prueba)

    # Pegar los atributos que hacen falta para desglosar.
    contexto = prueba[["id_tienda", "id_producto", "semana", "nombre", "ciudad", "tamano_m2"]]
    marco = abanico.merge(contexto, on=["id_tienda", "id_producto", "semana"], how="left")
    marco = marco.merge(tablas["tendencias"], on=["id_tienda", "id_producto"], how="left")

    partes = ["DIAGNOSTICO DEL MODELO - CASO A", "=" * ANCHO]
    partes += ["", f"  familia: {FAMILIA}",
               f"  pronostico central: {NIVEL_CENTRAL}",
               f"  filas evaluadas: {len(marco)} (semanas {list(particion.prueba)})"]

    partes += ["", "", "1. ERROR POR PRODUCTO", "=" * ANCHO, ""]
    por_producto = diagnostico.error_por_grupo(marco, NIVEL_CENTRAL, "nombre")
    partes.append(por_producto.round(3).to_string(index=False))

    partes += ["", "", "2. ERROR POR TIENDA", "=" * ANCHO, ""]
    por_tienda = diagnostico.error_por_grupo(marco, NIVEL_CENTRAL, "id_tienda")
    partes.append(por_tienda.round(3).to_string(index=False))

    partes += ["", "", "3. ERROR SEGUN EL VOLUMEN DE LA SERIE", "=" * ANCHO, ""]
    partes += ["  Las series se reparten en cuatro tramos de igual tamano segun su demanda",
               "  media. El error en unidades favorece a las series pequenas y el porcentual",
               "  a las grandes: se leen juntos.", ""]
    por_volumen = diagnostico.error_por_volumen(marco, NIVEL_CENTRAL)
    partes.append(por_volumen.round(3).to_string(index=False))

    partes += ["", "", "4. ERROR POR TIPO DE PATRON", "=" * ANCHO, ""]
    por_patron = diagnostico.error_por_grupo(marco, NIVEL_CENTRAL, "trend_type")
    partes.append(por_patron.round(3).to_string(index=False))

    partes += ["", "", "5. DISTRIBUCION DEL ERROR ENTRE LAS SERIES", "=" * ANCHO, ""]
    por_serie = diagnostico.resumen_por_serie(marco, NIVEL_CENTRAL)
    descripcion = por_serie["WAPE"].describe(percentiles=[0.1, 0.5, 0.9])
    partes.append(descripcion.round(4).to_string())
    partes += ["", "  las cinco series con mas error:"]
    partes.append(por_serie.head(5).round(3).to_string(index=False))
    umbral = 2 * por_serie["WAPE"].median()
    partes += ["", f"  series con error superior al doble de la mediana: "
                   f"{int((por_serie['WAPE'] > umbral).sum())} de {len(por_serie)}"]

    partes += ["", "", "6. DIAGNOSTICO DE RESIDUALES", "=" * ANCHO, ""]
    residuales = diagnostico.diagnostico_residuales(marco, NIVEL_CENTRAL)
    for clave, valor in residuales.items():
        partes.append(f"  {clave:30s} {valor:10.4f}" if isinstance(valor, float)
                      else f"  {clave:30s} {valor:>10}")
    partes += ["", "  corr_pred_error mide heterocedasticidad: si el error absoluto crece con",
               "  el valor predicho, el modelo no es igual de fiable en series grandes y",
               "  pequenas. series_con_autocorrelacion cuenta cuantas conservan estructura",
               "  temporal sin capturar, segun el contraste de Ljung-Box al 5 %."]

    partes += ["", "", "7. IMPORTANCIA POR PERMUTACION", "=" * ANCHO, ""]
    partes += [f"  Degradacion de la perdida pinball en el nivel {NIVEL_OPERACION} al barajar",
               "  cada variable en las semanas de prueba, promediada sobre 20 repeticiones.", ""]
    modelo_operacion = ajustados[min(niveles, key=lambda n: abs(n - NIVEL_OPERACION))]
    importancia = diagnostico.importancia_permutacion(modelo_operacion, prueba, NIVEL_OPERACION)
    partes.append(importancia.round(4).to_string(index=False))

    partes += ["", "", "8. COEFICIENTES DEL MODELO", "=" * ANCHO, ""]
    partes += ["  Sobre variables estandarizadas: indican cuantas unidades cambia la",
               "  prediccion por cada desviacion tipica de esa variable.", ""]
    coefs = diagnostico.coeficientes(modelo_operacion)
    partes.append(coefs.round(4).to_string(index=False))

    figuras = [
        plots.error_por_grupo(por_producto, por_tienda, paths.FIGURAS),
        plots.residuales(marco, NIVEL_CENTRAL, paths.FIGURAS),
        plots.importancia(importancia, paths.FIGURAS),
    ]
    partes += ["", "", "9. GRAFICOS GENERADOS", "=" * ANCHO, ""]
    partes += [f"  {f.relative_to(paths.RAIZ)}" for f in figuras]

    destino = paths.INFORMES / "07_diagnostico.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Figuras: {len(figuras)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
