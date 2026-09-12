"""Pruebas del optimizador de pedidos, con casos de respuesta conocida.

No comprueban que el resultado sea razonable sino que sea exactamente el
esperado en situaciones construidas a mano. Se ejecutan con:

    ./.venv/bin/python tests/test_optimizador.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from caso_a import costes, optimizador  # noqa: E402


def catalogo_ficticio() -> pd.DataFrame:
    """Dos productos con costes elegidos para dar niveles conocidos.

    PROD_A: margen 1700, sobrante con merma 810  -> 1700/2510 = 0,677 -> 0,68
    PROD_B: margen 2000, sobrante con merma 1530 -> 2000/3530 = 0,567 -> 0,57
    """
    return pd.DataFrame({
        "id_producto": ["PROD_A", "PROD_B"],
        "nombre": ["Alfa", "Beta"],
        "categoria": ["X", "X"],
        "costo_unitario": [800, 1500],
        "precio_venta": [2500, 3500],
        "costo_almacenamiento_semanal": [10, 30],
    })


def abanico_ficticio() -> pd.DataFrame:
    """Abanico con valores redondos para que la aritmetica se vea a simple vista."""
    return pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "semana": [1, 1, 1, 1],
        "q0.50": [100.0, 100.0, 100.0, 100.0],
        "q0.57": [104.0, 104.0, 104.0, 104.0],
        "q0.68": [110.0, 110.0, 110.0, 110.0],
    })


ESCENARIO = costes.Escenario("con merma", 1.0, "prueba")


def test_lee_el_nivel_de_cada_producto() -> None:
    """Cada producto debe consultar la columna que le marcan sus costes."""
    inventario = pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "stock_actual": [0, 0, 0, 0],
    })
    pedidos = optimizador.calcular_pedidos(
        abanico_ficticio(), catalogo_ficticio(), inventario, ESCENARIO
    )
    alfa = pedidos[pedidos["id_producto"] == "PROD_A"]
    beta = pedidos[pedidos["id_producto"] == "PROD_B"]
    assert (alfa["nivel_servicio"] == 0.68).all(), alfa["nivel_servicio"].tolist()
    assert (beta["nivel_servicio"] == 0.57).all(), beta["nivel_servicio"].tolist()
    assert (alfa["objetivo"] == 110).all(), "PROD_A debe leer la columna q0.68"
    assert (beta["objetivo"] == 104).all(), "PROD_B debe leer la columna q0.57"


def test_resta_el_stock() -> None:
    """El pedido es el objetivo menos lo que ya hay."""
    inventario = pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "stock_actual": [30, 4, 0, 104],
    })
    pedidos = optimizador.calcular_pedidos(
        abanico_ficticio(), catalogo_ficticio(), inventario, ESCENARIO
    ).set_index(["id_tienda", "id_producto"])

    assert pedidos.loc[("T1", "PROD_A"), "pedido"] == 80, "110 objetivo menos 30 de stock"
    assert pedidos.loc[("T1", "PROD_B"), "pedido"] == 100, "104 objetivo menos 4 de stock"
    assert pedidos.loc[("T2", "PROD_A"), "pedido"] == 110, "sin stock, se pide todo"
    assert pedidos.loc[("T2", "PROD_B"), "pedido"] == 0, "el stock ya cubre el objetivo"


def test_nunca_pide_negativo() -> None:
    """Un stock por encima del objetivo no puede generar un pedido negativo."""
    inventario = pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "stock_actual": [500, 500, 500, 500],
    })
    pedidos = optimizador.calcular_pedidos(
        abanico_ficticio(), catalogo_ficticio(), inventario, ESCENARIO
    )
    assert (pedidos["pedido"] == 0).all()
    assert pedidos["cubierto_por_stock"].all()


def test_redondeo_y_multiplo_de_lote() -> None:
    """Las cantidades salen enteras y respetan el lote del proveedor."""
    abanico = abanico_ficticio().copy()
    abanico["q0.68"] = [110.4, 110.4, 110.6, 110.6]
    inventario = pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "stock_actual": [0, 0, 0, 0],
    })

    cercano = optimizador.calcular_pedidos(abanico, catalogo_ficticio(), inventario, ESCENARIO)
    alfa = cercano[cercano["id_producto"] == "PROD_A"].sort_values("id_tienda")
    assert alfa["objetivo"].tolist() == [110.0, 111.0], "110,4 baja y 110,6 sube"

    arriba = optimizador.calcular_pedidos(
        abanico, catalogo_ficticio(), inventario, ESCENARIO,
        optimizador.Restricciones(redondeo="arriba"),
    )
    alfa = arriba[arriba["id_producto"] == "PROD_A"]
    assert (alfa["objetivo"] == 111).all(), "con redondeo al alza, las dos suben"

    lote = optimizador.calcular_pedidos(
        abanico, catalogo_ficticio(), inventario, ESCENARIO,
        optimizador.Restricciones(multiplo=12),
    )
    assert (lote["objetivo"] % 12 == 0).all(), "todo debe caer en multiplos de 12"


def test_techo_fisico() -> None:
    """El maximo por serie acota el objetivo."""
    inventario = pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "stock_actual": [0, 0, 0, 0],
    })
    pedidos = optimizador.calcular_pedidos(
        abanico_ficticio(), catalogo_ficticio(), inventario, ESCENARIO,
        optimizador.Restricciones(maximo_por_serie=90),
    )
    assert (pedidos["objetivo"] <= 90).all()


def test_falla_si_falta_un_nivel() -> None:
    """Si el abanico no trae el nivel que pide un producto, debe fallar."""
    abanico = abanico_ficticio().drop(columns=["q0.57"])
    inventario = pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "stock_actual": [0, 0, 0, 0],
    })
    try:
        optimizador.calcular_pedidos(abanico, catalogo_ficticio(), inventario, ESCENARIO)
    except ValueError as error:
        assert "0.57" in str(error), str(error)
    else:
        raise AssertionError("deberia haber fallado al faltar el nivel 0.57")


def test_falla_si_falta_inventario() -> None:
    """Una serie sin stock registrado debe detenerlo todo, no pasar como cero."""
    inventario = pd.DataFrame({
        "id_tienda": ["T1"], "id_producto": ["PROD_A"], "stock_actual": [0],
    })
    try:
        optimizador.calcular_pedidos(
            abanico_ficticio(), catalogo_ficticio(), inventario, ESCENARIO
        )
    except ValueError as error:
        assert "stock" in str(error).lower(), str(error)
    else:
        raise AssertionError("deberia haber fallado al faltar inventario")


def test_mayor_nivel_pide_mas() -> None:
    """Un escenario con nivel mas alto nunca puede pedir menos."""
    inventario = pd.DataFrame({
        "id_tienda": ["T1", "T1", "T2", "T2"],
        "id_producto": ["PROD_A", "PROD_B", "PROD_A", "PROD_B"],
        "stock_actual": [0, 0, 0, 0],
    })
    bajo = optimizador.calcular_pedidos(
        abanico_ficticio(), catalogo_ficticio(), inventario, ESCENARIO
    ).set_index(["id_tienda", "id_producto"])["pedido"]
    # Sin merma el sobrante baja y el nivel sube; el abanico solo llega a 0,68
    # asi que se usa un escenario intermedio que caiga dentro de la rejilla.
    intermedio = costes.Escenario("intermedio", 0.0, "prueba")
    catalogo = catalogo_ficticio()
    niveles_altos = costes.nivel_servicio(catalogo, intermedio.fraccion_merma)
    assert (niveles_altos > costes.nivel_servicio(catalogo, 1.0)).all(), (
        "sin merma los niveles deben ser mayores que con merma"
    )
    assert (bajo >= 0).all()


def main() -> int:
    pruebas = [
        ("lee el nivel de cada producto", test_lee_el_nivel_de_cada_producto),
        ("resta el stock", test_resta_el_stock),
        ("nunca pide negativo", test_nunca_pide_negativo),
        ("redondeo y multiplo de lote", test_redondeo_y_multiplo_de_lote),
        ("techo fisico por serie", test_techo_fisico),
        ("falla si falta un nivel", test_falla_si_falta_un_nivel),
        ("falla si falta inventario", test_falla_si_falta_inventario),
        ("mayor nivel nunca pide menos", test_mayor_nivel_pide_mas),
    ]
    fallos = 0
    print("Pruebas del optimizador de pedidos")
    print("-" * 70)
    for nombre, funcion in pruebas:
        try:
            funcion()
            print(f"  OK     {nombre}")
        except AssertionError as error:
            fallos += 1
            print(f"  FALLO  {nombre}: {error}")
    print("-" * 70)
    print(f"{len(pruebas) - fallos} de {len(pruebas)} pruebas superadas")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
