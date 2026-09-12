"""Punto de entrada unico del Caso A: ejecuta el pipeline completo, en orden.

Los once scripts del proyecto son autonomos y se pueden lanzar sueltos, pero el
orden importa y las dependencias entre ellos no estan escritas en ninguna parte
salvo en la memoria de quien los ejecuta. Este modulo las hace explicitas.

Que aporta frente a lanzarlos a mano:

- El orden correcto esta declarado una sola vez, en :data:`PASOS`.
- Cada paso declara que ficheros de parametros necesita de los anteriores. Si
  faltan, el fallo es un mensaje claro y no un rastro de excepcion a media
  ejecucion.
- La ejecucion se detiene en el primer paso que falla, en lugar de seguir
  produciendo informes a partir de un artefacto roto.
- Se pueden ejecutar tramos, que es lo que hace falta al iterar sobre un paso
  concreto sin repetir los diez anteriores.

Uso:

    ./.venv/bin/python main.py                  # todo el pipeline y las pruebas
    ./.venv/bin/python main.py --listar         # ver los pasos y no ejecutar nada
    ./.venv/bin/python main.py --desde rejilla  # desde ese paso hasta el final
    ./.venv/bin/python main.py --solo entrega   # un unico paso
    ./.venv/bin/python main.py --sin-pruebas    # omitir la bateria de tests
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "src"))

ANCHO = 78


@dataclass(frozen=True)
class Paso:
    """Un paso del pipeline, con lo que produce y lo que necesita.

    Attributes:
        numero: Posicion en la metodologia, tal como la numera la memoria.
        clave: Nombre corto con el que se selecciona desde la linea de ordenes.
        modulo: Modulo ejecutable, sin extension.
        titulo: Descripcion de una linea.
        informe: Informe que deja en ``salidas/informes``, si deja alguno.
        requiere: Ficheros de ``salidas/parametros`` que deben existir antes.
    """

    numero: str
    clave: str
    modulo: str
    titulo: str
    informe: str
    requiere: tuple[str, ...] = field(default_factory=tuple)


#: Los hiperparametros los escribe la seleccion de familia y los consumen los
#: cinco pasos que la siguen. Es la unica dependencia real entre scripts.
HIPERPARAMETROS = ("hiperparametros.json",)

PASOS: tuple[Paso, ...] = (
    Paso("1-2", "auditoria", "run_audit", "Auditoria e integridad del panel", "01_auditoria.txt"),
    Paso("3-4", "eda", "run_eda", "Analisis univariado y agregacion a semana", "02_univariado.txt"),
    Paso("5-8", "variables", "run_features", "Variables, particiones y lineas base",
         "03_variables_y_lineas_base.txt"),
    Paso("9", "costes", "run_costes", "Costes y niveles de servicio", "04_costes_y_niveles.txt"),
    Paso("10", "modelos", "run_modelos", "Seleccion de familia", "05_seleccion_familia.txt"),
    Paso("11", "rejilla", "run_rejilla", "Rejilla de niveles", "06_rejilla_niveles.txt",
         HIPERPARAMETROS),
    Paso("12", "diagnostico", "run_diagnostico", "Diagnostico e interpretabilidad",
         "07_diagnostico.txt", HIPERPARAMETROS),
    Paso("13", "calibracion", "run_calibracion", "Calibracion conformal", "08_calibracion.txt",
         HIPERPARAMETROS),
    Paso("14", "pedidos", "run_pedidos", "Optimizador del pedido", "09_pedidos.txt",
         HIPERPARAMETROS),
    Paso("15", "politicas", "run_politicas", "Simulacion de politicas y ahorro",
         "10_politicas.txt", HIPERPARAMETROS),
    Paso("16", "entrega", "run_entrega", "Entrega: pedido de la semana siguiente",
         "11_entrega.txt", HIPERPARAMETROS),
)

#: Baterias de verificacion. No producen informe: fallan o no fallan.
PRUEBAS: tuple[tuple[str, str], ...] = (
    ("tests.test_fuga", "aislamiento temporal entre particiones"),
    ("tests.test_optimizador", "optimizador con casos de respuesta conocida"),
)


def _claves() -> list[str]:
    return [paso.clave for paso in PASOS]


def seleccionar(desde: str | None, hasta: str | None, solo: str | None) -> tuple[Paso, ...]:
    """Devuelve el tramo de pasos a ejecutar, conservando el orden declarado.

    Raises:
        SystemExit: Si alguna clave no existe o el tramo queda vacio.
    """
    claves = _claves()
    for etiqueta, valor in (("--desde", desde), ("--hasta", hasta), ("--solo", solo)):
        if valor is not None and valor not in claves:
            raise SystemExit(
                f"Paso desconocido en {etiqueta}: {valor!r}. Opciones: {', '.join(claves)}"
            )

    if solo is not None:
        return tuple(paso for paso in PASOS if paso.clave == solo)

    inicio = claves.index(desde) if desde else 0
    fin = claves.index(hasta) + 1 if hasta else len(PASOS)
    if inicio >= fin:
        raise SystemExit(f"El tramo esta vacio: --desde {desde} va despues de --hasta {hasta}.")
    return PASOS[inicio:fin]


def dependencias_ausentes(paso: Paso) -> list[str]:
    """Ficheros que el paso necesita y todavia no existen."""
    from caso_a import paths

    return [nombre for nombre in paso.requiere if not (paths.PARAMETROS / nombre).exists()]


def ejecutar(paso: Paso) -> tuple[int, float]:
    """Lanza un paso y devuelve su codigo de salida y el tiempo empleado.

    El script se importa y se llama a su ``main``, en lugar de abrir un proceso
    nuevo: asi el codigo de salida llega sin interpretar texto y no se paga la
    importacion de las librerias once veces.
    """
    modulo = importlib.import_module(paso.modulo)
    arranque = time.perf_counter()
    try:
        codigo = int(modulo.main())
    except Exception as error:  # noqa: BLE001
        print(f"  EXCEPCION  {type(error).__name__}: {error}")
        codigo = 1
    return codigo, time.perf_counter() - arranque


def ejecutar_pruebas() -> int:
    """Lanza las baterias de verificacion. Devuelve el numero de fallos."""
    fallos = 0
    for nombre, descripcion in PRUEBAS:
        print(f"\n{'-' * ANCHO}\nPRUEBAS  {descripcion}\n{'-' * ANCHO}")
        modulo = importlib.import_module(nombre)
        if int(modulo.main()) != 0:
            fallos += 1
    return fallos


def listar() -> None:
    """Imprime los pasos declarados, sin ejecutar nada."""
    print(f"Pipeline del Caso A: {len(PASOS)} pasos\n")
    print(f"  {'paso':>5}  {'clave':<12} {'informe':<32} descripcion")
    print(f"  {'-' * 5}  {'-' * 12} {'-' * 32} {'-' * 20}")
    for paso in PASOS:
        print(f"  {paso.numero:>5}  {paso.clave:<12} {paso.informe:<32} {paso.titulo}")
    print(f"\n  Pendiente: paso 17, presentacion ejecutiva.")


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Ejecuta el pipeline del Caso A en el orden correcto.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    analizador.add_argument("--listar", action="store_true",
                            help="mostrar los pasos y salir sin ejecutar")
    analizador.add_argument("--desde", metavar="CLAVE", help="primer paso a ejecutar")
    analizador.add_argument("--hasta", metavar="CLAVE", help="ultimo paso a ejecutar")
    analizador.add_argument("--solo", metavar="CLAVE", help="ejecutar un unico paso")
    analizador.add_argument("--sin-pruebas", action="store_true",
                            help="omitir las baterias de verificacion del final")
    argumentos = analizador.parse_args()

    if argumentos.listar:
        listar()
        return 0

    if argumentos.solo and (argumentos.desde or argumentos.hasta):
        raise SystemExit("--solo no se combina con --desde ni --hasta.")

    seleccion = seleccionar(argumentos.desde, argumentos.hasta, argumentos.solo)

    from caso_a import paths

    paths.asegurar_salidas()
    print("=" * ANCHO)
    print(f"PIPELINE CASO A - {len(seleccion)} de {len(PASOS)} pasos")
    print("=" * ANCHO)

    resultados: list[tuple[Paso, int, float]] = []
    for indice, paso in enumerate(seleccion, start=1):
        print(f"\n[{indice}/{len(seleccion)}]  paso {paso.numero}  {paso.titulo}")

        ausentes = dependencias_ausentes(paso)
        if ausentes:
            print(f"  BLOQUEADO  faltan {', '.join(ausentes)} en salidas/parametros.")
            print(f"             los produce el paso 'modelos'; ejecutalo antes o lanza "
                  f"el pipeline entero.")
            resultados.append((paso, 1, 0.0))
            break

        codigo, segundos = ejecutar(paso)
        resultados.append((paso, codigo, segundos))
        print(f"  {'OK' if codigo == 0 else 'FALLO'}  {segundos:.1f} s")
        if codigo != 0:
            print(f"\n  Se detiene aqui. Los pasos siguientes leerian artefactos incompletos.")
            break

    print(f"\n{'=' * ANCHO}\nRESUMEN\n{'=' * ANCHO}\n")
    print(f"  {'paso':>5}  {'clave':<12} {'estado':<8} {'segundos':>9}")
    print(f"  {'-' * 5}  {'-' * 12} {'-' * 8} {'-' * 9}")
    for paso, codigo, segundos in resultados:
        estado = "OK" if codigo == 0 else "FALLO"
        print(f"  {paso.numero:>5}  {paso.clave:<12} {estado:<8} {segundos:>9.1f}")
    total = sum(segundos for _, _, segundos in resultados)
    fallidos = [paso.clave for paso, codigo, _ in resultados if codigo != 0]
    print(f"\n  tiempo total: {total:.1f} s")

    if fallidos:
        print(f"  pasos con fallo: {', '.join(fallidos)}")
        return 1
    if len(resultados) < len(seleccion):
        print(f"  pasos no ejecutados: {len(seleccion) - len(resultados)}")
        return 1

    if argumentos.sin_pruebas:
        print("  pruebas: omitidas por --sin-pruebas")
        return 0

    fallos = ejecutar_pruebas()
    print(f"\n{'=' * ANCHO}")
    print("  pipeline completo y verificaciones superadas" if fallos == 0
          else f"  {fallos} bateria(s) de verificacion con fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
