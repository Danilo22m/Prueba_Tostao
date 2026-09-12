"""Seleccion de familia de algoritmo del Caso A.

Compara cada familia en dos parametrizaciones, absoluta y relativa. La
relativa aprende la demanda como proporcion de la media reciente y devuelve la
prediccion en unidades, de modo que las metricas siguen siendo comparables.

Las familias que solo estiman la media se convierten a distribucion con los
cuantiles empiricos de sus residuales, para que compitan en la misma metrica.

La familia se elige por la perdida pinball en el nivel que se va a operar, no
por el error del pronostico central.

Genera:
    salidas/informes/05_seleccion_familia.txt
    salidas/figuras/13_comparacion_familias.png
    salidas/figuras/14_significacion.png
    salidas/figuras/15_colchon_por_serie.png
    salidas/parametros/hiperparametros.json

Uso:
    ./.venv/bin/python run_modelos.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import ajuste, evaluacion, features, loaders, metrics  # noqa: E402
from caso_a import modelos, panel, paths, plots, splits  # noqa: E402

ANCHO = 84

#: Niveles en los que se compara. Uno central, uno de operacion y uno alto.
NIVELES_COMPARACION = (0.5, 0.65, 0.9)

#: Nivel que decide la seleccion: el que se va a operar de verdad.
NIVEL_DECISION = 0.65

#: Familias que solo estiman la media condicional. Se marcan en el informe
#: porque su colchon es constante por construccion.
PUNTUALES = set(modelos.FAMILIAS_PUNTUALES) | {
    f"{n} (relativo)" for n in modelos.FAMILIAS_PUNTUALES
}

#: Parametrizacion que se opera: la relativa de cada familia mas la media
#: movil, que no tiene version relativa porque seria una constante. Las
#: figuras y el resumen por familia se construyen sobre este conjunto; la
#: comparacion completa con las parametrizaciones absolutas queda en el informe.
OPERADAS = set(modelos.FAMILIAS_RELATIVAS) | {"media movil + residuales"}


def _limpio(nombre: str) -> str:
    """Nombre de familia sin la marca de parametrizacion."""
    return nombre.replace(" (relativo)", "")


def main() -> int:  # noqa: PLR0915
    paths.asegurar_salidas()
    tablas = loaders.cargar_todo(validar=True)
    pnl = panel.enriquecer(panel.a_semanal(tablas["ventas"]), tablas["catalogo"], tablas["tiendas"])
    completo = features.construir(pnl)
    particion = splits.desde_panel(pnl)
    nuevas = [c for c in completo.columns if c not in pnl.columns]
    utilizable = completo.dropna(subset=nuevas)

    entrenamiento = splits.separar(utilizable, particion.entrenamiento)
    prueba = splits.separar(utilizable, particion.prueba)
    real = prueba[modelos.OBJETIVO].to_numpy(float)
    familias = modelos.FAMILIAS_AMBAS

    partes = ["SELECCION DE FAMILIA - CASO A", "=" * ANCHO]
    partes += ["", f"  {particion}",
               f"  filas: {len(entrenamiento)} de entrenamiento, {len(prueba)} de prueba",
               f"  niveles evaluados: {list(NIVELES_COMPARACION)}",
               f"  nivel que decide la seleccion: {NIVEL_DECISION}",
               "",
               "  Las familias marcadas [puntual] solo estiman la media condicional. Se",
               "  convierten en distribucion con los cuantiles empiricos de sus residuales,",
               "  igual que la linea base, para que compitan en la misma metrica.",
               "",
               "  Las marcadas (relativo) aprenden la demanda como proporcion de la media",
               "  de las cuatro semanas previas y devuelven la prediccion en unidades. Todas",
               "  las metricas se calculan en unidades, no en proporciones."]

    partes += ["", "", "1. AJUSTE DE HIPERPARAMETROS", "=" * ANCHO, ""]
    partes += [f"  Busqueda bayesiana, {ajuste.ENSAYOS} ensayos por familia, optimizando la",
               f"  perdida pinball en el nivel {NIVEL_DECISION} sobre los pliegues de validacion.", ""]
    mejores: dict[str, dict] = {}
    filas_ajuste = []
    for nombre, clase in familias.items():
        parametros, perdida = ajuste.optimizar(
            nombre, clase, utilizable, particion, NIVEL_DECISION
        )
        mejores[nombre] = parametros
        filas_ajuste.append({
            "familia": f"{nombre} [puntual]" if nombre in PUNTUALES else nombre,
            "perdida_validacion": perdida,
            "hiperparametros": json.dumps(parametros, sort_keys=True) if parametros else "por defecto",
        })
    partes.append(pd.DataFrame(filas_ajuste).sort_values("perdida_validacion").round(4).to_string(index=False))

    partes += ["", "", "2. RESULTADO EN LAS SEMANAS DE PRUEBA", "=" * ANCHO, ""]
    tabla, predicciones = evaluacion.comparar(
        familias, entrenamiento, prueba, NIVELES_COMPARACION, mejores
    )
    pivote = tabla.pivot(index="familia", columns="nivel", values="pinball")
    pivote.columns = [f"pinball {c}" for c in pivote.columns]
    pivote["media"] = pivote.mean(axis=1)
    vista = pivote.sort_values("media").copy()
    vista.index = [f"{i} [puntual]" if i in PUNTUALES else i for i in vista.index]
    partes.append(vista.round(4).to_string())

    partes += ["", "  metricas del pronostico central, nivel 0.5:", ""]
    central = tabla[tabla["nivel"] == 0.5].set_index("familia")[["WAPE", "MAE", "sesgo"]]
    central = central.sort_values("WAPE")
    central.index = [f"{i} [puntual]" if i in PUNTUALES else i for i in central.index]
    partes.append(central.round(4).to_string())

    partes += ["", "  resumen por familia, parametrizacion operada:", ""]
    metricas_centro = tabla[tabla["nivel"] == 0.5].set_index("familia")[["WAPE", "MAE", "sesgo"]]
    resumen = pivote.join(metricas_centro)
    resumen = resumen[resumen.index.isin(OPERADAS)].sort_values("media")
    resumen.index = [_limpio(i) for i in resumen.index]
    partes.append(resumen.round(4).to_string())
    partes += ["", f"  gana «{resumen.index[0]}» por perdida pinball media; "
                   f"«{resumen['WAPE'].idxmin()}» tiene el menor WAPE del centro."]

    partes += ["", "", "3. EL CLASICO POR SERIE", "=" * ANCHO, ""]
    historico = splits.separar(pnl, tuple(range(1, particion.prueba[0])))
    filas_clasico = []
    for nivel in NIVELES_COMPARACION:
        prediccion = modelos.SuavizadoPorSerie(nivel).ajustar_predecir(historico, prueba)
        fila = {"nivel": nivel, "pinball": metrics.pinball(real, prediccion, nivel)}
        if nivel == 0.5:
            fila["WAPE"] = metrics.wape(real, prediccion)
        filas_clasico.append(fila)
    partes.append(pd.DataFrame(filas_clasico).round(4).to_string(index=False))
    partes += ["", "  Ajusta cada serie con su propia historia, sin variables construidas."]

    partes += ["", "", "4. SON REALES LAS DIFERENCIAS", "=" * ANCHO]
    orden = pivote.sort_values("media").index.tolist()
    mejor = orden[0]
    partes += ["", f"4.1 Diebold-Mariano contra «{mejor}», nivel {NIVEL_DECISION}", "-" * ANCHO, ""]
    filas_dm = []
    for rival in orden[1:]:
        estadistico, p_valor = evaluacion.diebold_mariano(
            real, predicciones[rival][NIVEL_DECISION], predicciones[mejor][NIVEL_DECISION], NIVEL_DECISION
        )
        filas_dm.append({
            "rival": f"{rival} [puntual]" if rival in PUNTUALES else rival,
            "estadistico": estadistico, "p_valor": p_valor,
            "conclusion": "pierde con evidencia" if p_valor < 0.05 else "empate tecnico",
        })
    partes.append(pd.DataFrame(filas_dm).round(4).to_string(index=False))

    partes += ["", "4.2 Banda de confianza al 95 % por remuestreo de series", "-" * ANCHO, ""]
    filas_banda = []
    for familia in orden:
        inferior, superior = evaluacion.banda_remuestreo(
            real, predicciones[familia][NIVEL_DECISION], NIVEL_DECISION, prueba
        )
        filas_banda.append({
            "familia": familia,
            "pinball": metrics.pinball(real, predicciones[familia][NIVEL_DECISION], NIVEL_DECISION),
            "inferior": inferior, "superior": superior,
        })
    banda = pd.DataFrame(filas_banda)
    vista_banda = banda.copy()
    vista_banda["familia"] = [f"{f} [puntual]" if f in PUNTUALES else f for f in banda["familia"]]
    partes.append(vista_banda.round(4).to_string(index=False))
    solape = banda["inferior"].max() <= banda["superior"].min()
    partes += ["", f"  Las bandas {'se solapan' if solape else 'no se solapan'} entre todas las familias."]

    partes += ["", "", "5. ANCHO DEL COLCHON POR SERIE", "=" * ANCHO, ""]
    partes += ["  Diferencia entre el nivel 0.9 y el 0.5 de cada fila. Desviacion cero significa",
               "  que el modelo aplica el mismo colchon a las 160 series. Minimo negativo",
               "  significa que los niveles se cruzan, lo que es imposible en la realidad.", ""]
    filas_colchon = []
    for nombre in orden:
        colchon = predicciones[nombre][0.9] - predicciones[nombre][0.5]
        filas_colchon.append({
            "familia": f"{nombre} [puntual]" if nombre in PUNTUALES else nombre,
            "media": colchon.mean(), "desviacion": colchon.std(),
            "minimo": colchon.min(), "maximo": colchon.max(),
            "se_cruza": bool((colchon < 0).any()),
        })
    partes.append(pd.DataFrame(filas_colchon).round(2).to_string(index=False))

    ruta_parametros = paths.PARAMETROS / "hiperparametros.json"
    ruta_parametros.write_text(
        json.dumps({"nivel_optimizado": NIVEL_DECISION, "ensayos": ajuste.ENSAYOS,
                    "por_familia": mejores}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Las figuras muestran la parametrizacion operada, con el nombre de cada
    # familia limpio. La comparacion completa esta en las tablas de arriba.
    pivote_operado = pivote[pivote.index.isin(OPERADAS)].copy()
    pivote_operado.index = [_limpio(i) for i in pivote_operado.index]
    banda_operada = banda[banda["familia"].isin(OPERADAS)].copy()
    banda_operada["familia"] = banda_operada["familia"].map(_limpio)
    predicciones_operadas = {
        _limpio(n): predicciones[n] for n in orden if n in OPERADAS
    }
    figuras = [
        plots.comparacion_familias(pivote_operado, paths.FIGURAS),
        plots.significacion(banda_operada, paths.FIGURAS),
        plots.colchon_por_serie(predicciones_operadas, paths.FIGURAS),
    ]
    partes += ["", "", "6. FICHEROS GENERADOS", "=" * ANCHO, ""]
    partes += [f"  {ruta_parametros.relative_to(paths.RAIZ)}"]
    partes += [f"  {f.relative_to(paths.RAIZ)}" for f in figuras]

    destino = paths.INFORMES / "05_seleccion_familia.txt"
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Informe: {destino.relative_to(paths.RAIZ)}")
    print(f"Figuras: {len(figuras)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
