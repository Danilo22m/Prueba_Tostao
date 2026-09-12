"""Verificaciones de que ningun modelo ve datos que no deberia.

Cada prueba falla de forma ruidosa si se rompe el aislamiento entre
entrenamiento, validacion y prueba. Se ejecutan con:

    ./.venv/bin/python tests/test_fuga.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from caso_a import ajuste, features, loaders, modelos, panel, splits  # noqa: E402

NIVELES = (0.5, 0.65, 0.9)


def preparar() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, splits.Particion]:
    """Devuelve panel completo, entrenamiento, prueba y particion."""
    tablas = loaders.cargar_todo(validar=True)
    pnl = panel.enriquecer(
        panel.a_semanal(tablas["ventas"]), tablas["catalogo"], tablas["tiendas"]
    )
    completo = features.construir(pnl)
    particion = splits.desde_panel(pnl)
    nuevas = [c for c in completo.columns if c not in pnl.columns]
    utilizable = completo.dropna(subset=nuevas)
    return (
        utilizable,
        splits.separar(utilizable, particion.entrenamiento),
        splits.separar(utilizable, particion.prueba),
        particion,
    )


def test_particiones_no_se_solapan(entrenamiento, prueba, particion) -> None:
    """Ninguna semana puede estar en entrenamiento y en prueba a la vez."""
    semanas_tr = set(entrenamiento["semana"].unique())
    semanas_te = set(prueba["semana"].unique())
    assert not semanas_tr & semanas_te, f"semanas compartidas: {semanas_tr & semanas_te}"
    assert semanas_tr == set(particion.entrenamiento)
    assert semanas_te == set(particion.prueba)
    assert max(semanas_tr) < min(semanas_te), "el entrenamiento incluye semanas posteriores a la prueba"


def test_prediccion_no_depende_del_objetivo_de_prueba(entrenamiento, prueba) -> None:
    """Si se destruye el objetivo de prueba, las predicciones no deben cambiar.

    Es la prueba decisiva: si el modelo estuviera usando la demanda real de las
    semanas de prueba, aunque fuera de forma indirecta, las predicciones se
    moverian al alterarla.
    """
    corrompida = prueba.copy()
    generador = np.random.default_rng(0)
    corrompida[modelos.OBJETIVO] = generador.integers(0, 10_000, size=len(corrompida))

    for nombre, clase in modelos.FAMILIAS_TODAS.items():
        modelo = clase(0.65).ajustar(entrenamiento)
        original = modelo.predecir(prueba)
        alterada = modelo.predecir(corrompida)
        assert np.allclose(original, alterada), f"{nombre} usa el objetivo de prueba"


def test_ajustar_no_mira_la_prueba(entrenamiento, prueba) -> None:
    """Ajustar con el entrenamiento no puede depender de que exista la prueba."""
    for nombre, clase in modelos.FAMILIAS_TODAS.items():
        solo_train = clase(0.65).ajustar(entrenamiento).predecir(prueba)
        con_ruido = clase(0.65).ajustar(entrenamiento.sample(frac=1, random_state=1)).predecir(prueba)
        assert np.allclose(solo_train, con_ruido, atol=1e-6), (
            f"{nombre} depende del orden de las filas de entrenamiento"
        )


def test_entrenar_con_mas_datos_cambia_el_modelo(entrenamiento, prueba, utilizable, particion) -> None:
    """Control negativo: si entrenar con prueba no cambiara nada, algo falla.

    Una prueba de fuga que siempre pasa no demuestra nada. Esta comprueba que el
    mecanismo es sensible: anadir las semanas de prueba al entrenamiento tiene
    que mover las predicciones.
    """
    todo = splits.separar(utilizable, particion.entrenamiento + particion.prueba)
    movidos = 0
    for clase in modelos.FAMILIAS_TODAS.values():
        solo_train = clase(0.65).ajustar(entrenamiento).predecir(prueba)
        con_prueba = clase(0.65).ajustar(todo).predecir(prueba)
        if not np.allclose(solo_train, con_prueba):
            movidos += 1
    assert movidos == len(modelos.FAMILIAS_TODAS), (
        f"solo {movidos} de {len(modelos.FAMILIAS_TODAS)} familias reaccionan a mas datos"
    )


def test_variables_sin_fuga_temporal(particion) -> None:
    """Ninguna variable construida usa informacion posterior a su semana."""
    tablas = loaders.cargar_todo(validar=True)
    pnl = panel.enriquecer(
        panel.a_semanal(tablas["ventas"]), tablas["catalogo"], tablas["tiendas"]
    )
    for corte in (particion.entrenamiento[-1], particion.prueba[0]):
        features.verificar_sin_fuga(pnl, semana_corte=corte)


def test_hiperparametros_solo_ven_validacion(utilizable, particion) -> None:
    """La busqueda de hiperparametros no puede tocar las semanas de prueba."""
    vistas: set[int] = set()
    for ajuste_semanas, validacion in splits.pliegues_expansivos(particion.entrenamiento):
        vistas |= set(ajuste_semanas) | {validacion}
    assert not vistas & set(particion.prueba), (
        f"la validacion toca semanas de prueba: {vistas & set(particion.prueba)}"
    )
    assert vistas <= set(particion.entrenamiento)


def test_busqueda_no_toca_la_prueba(utilizable, particion) -> None:
    """Registra cada semana que consulta la busqueda de hiperparametros.

    No comprueba la configuracion sino la ejecucion real: intercepta la funcion
    que separa semanas y anota todas las que se piden durante la optimizacion.
    Si alguna fuera de prueba, quedaria registrada.
    """
    vistas: set[int] = set()
    original = splits.separar

    def espia(marco: pd.DataFrame, semanas):
        objetivo = (semanas,) if isinstance(semanas, int) else semanas
        vistas.update(int(s) for s in objetivo)
        return original(marco, semanas)

    splits.separar = espia
    ajuste.splits.separar = espia
    try:
        for nombre, clase in modelos.FAMILIAS_TODAS.items():
            ajuste.optimizar(nombre, clase, utilizable, particion, 0.65, ensayos=2)
    finally:
        splits.separar = original
        ajuste.splits.separar = original

    fuga = vistas & set(particion.prueba)
    assert not fuga, f"la busqueda de hiperparametros consulto semanas de prueba: {sorted(fuga)}"
    assert vistas <= set(particion.entrenamiento), (
        f"la busqueda consulto semanas fuera de entrenamiento: {sorted(vistas - set(particion.entrenamiento))}"
    )


def test_pliegues_avanzan_en_el_tiempo(particion) -> None:
    """En cada pliegue, la semana validada va despues de todas las de ajuste."""
    for ajuste_semanas, validacion in splits.pliegues_expansivos(particion.entrenamiento):
        assert validacion > max(ajuste_semanas), (
            f"el pliegue valida la semana {validacion} con datos de {ajuste_semanas}"
        )


def test_clasico_no_ve_la_prueba(prueba, particion) -> None:
    """El suavizado por serie solo recibe semanas anteriores a la prueba."""
    tablas = loaders.cargar_todo(validar=True)
    pnl = panel.enriquecer(
        panel.a_semanal(tablas["ventas"]), tablas["catalogo"], tablas["tiendas"]
    )
    historico = splits.separar(pnl, tuple(range(1, particion.prueba[0])))
    assert historico["semana"].max() < particion.prueba[0]
    prediccion = modelos.SuavizadoPorSerie(0.65).ajustar_predecir(historico, prueba)
    assert not np.isnan(prediccion).any(), "el suavizado dejo predicciones sin calcular"


def main() -> int:
    utilizable, entrenamiento, prueba, particion = preparar()
    pruebas = [
        ("particiones no se solapan", lambda: test_particiones_no_se_solapan(entrenamiento, prueba, particion)),
        ("pliegues avanzan en el tiempo", lambda: test_pliegues_avanzan_en_el_tiempo(particion)),
        ("hiperparametros solo ven validacion", lambda: test_hiperparametros_solo_ven_validacion(utilizable, particion)),
        ("la busqueda real no toca la prueba", lambda: test_busqueda_no_toca_la_prueba(utilizable, particion)),
        ("variables sin fuga temporal", lambda: test_variables_sin_fuga_temporal(particion)),
        ("prediccion ignora el objetivo de prueba", lambda: test_prediccion_no_depende_del_objetivo_de_prueba(entrenamiento, prueba)),
        ("ajuste no mira la prueba", lambda: test_ajustar_no_mira_la_prueba(entrenamiento, prueba)),
        ("control negativo: mas datos cambian el modelo", lambda: test_entrenar_con_mas_datos_cambia_el_modelo(entrenamiento, prueba, utilizable, particion)),
        ("el clasico no ve la prueba", lambda: test_clasico_no_ve_la_prueba(prueba, particion)),
    ]

    fallos = 0
    print(f"Verificacion de aislamiento entre particiones")
    print(f"  entrenamiento: semanas {list(particion.entrenamiento)}, {len(entrenamiento)} filas")
    print(f"  prueba:        semanas {list(particion.prueba)}, {len(prueba)} filas")
    print(f"  familias:      {len(modelos.FAMILIAS_TODAS)}")
    print("-" * 70)
    for nombre, funcion in pruebas:
        try:
            funcion()
            print(f"  OK     {nombre}")
        except AssertionError as error:
            fallos += 1
            print(f"  FALLO  {nombre}: {error}")
    print("-" * 70)
    print(f"{len(pruebas) - fallos} de {len(pruebas)} verificaciones superadas")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
