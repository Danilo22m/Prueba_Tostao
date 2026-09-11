"""Ejecuta la auditoria de datos del Caso A y escribe el informe.

Uso:
    ./.venv/bin/python run_audit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from caso_a import audit, loaders, paths  # noqa: E402

MARCA_OK = "OK  "
MARCA_FALLO = "FALLO"


def formatear(resultados: dict[str, list[audit.Resultado]]) -> tuple[str, int, int]:
    """Compone el informe en texto y cuenta comprobaciones superadas."""
    lineas: list[str] = []
    superadas = total = 0

    for bloque, items in resultados.items():
        lineas.append("")
        lineas.append(bloque.upper())
        lineas.append("-" * 78)
        for item in items:
            informativo = item.esperado == "informativo"
            if not informativo:
                total += 1
                superadas += int(item.supera)
            marca = "  --" if informativo else (MARCA_OK if item.supera else MARCA_FALLO)
            lineas.append(f"{marca}  {item.nombre:<46} {item.obtenido}")
            if item.detalle:
                lineas.append(f"        {item.detalle}")

    return "\n".join(lineas), superadas, total


def main() -> int:
    paths.asegurar_salidas()

    print("Cargando y validando esquemas...")
    tablas = loaders.cargar_todo(validar=True)
    print(f"Cargadas {len(tablas)} tablas, {sum(len(t) for t in tablas.values())} filas en total.")

    cuerpo, superadas, total = formatear(audit.auditar(tablas))

    cabecera = (
        "AUDITORIA DE DATOS - CASO A - OPTIMIZACION DE ABASTECIMIENTO\n"
        + "=" * 78
        + f"\nComprobaciones superadas: {superadas} de {total}"
    )
    informe = cabecera + cuerpo + "\n"

    destino = paths.INFORMES / "01_auditoria.txt"
    destino.write_text(informe, encoding="utf-8")

    print(informe)
    print(f"Informe escrito en {destino.relative_to(paths.RAIZ)}")
    return 0 if superadas == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
