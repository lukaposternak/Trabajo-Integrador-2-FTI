"""
Punto de entrada.

    python main.py                         # interfaz gráfica
    python main.py --cinta "11#00010000#"  # ejecución por consola
    python main.py --pruebas casos_prueba.txt
    python main.py --tabla                 # imprime la tabla de transiciones
"""
import argparse
import sys

from regla110_mt import DELTA, ESTADOS, simular, tabla_transiciones, validar_entrada


def ejecutar_consola(cinta: str) -> int:
    try:
        validar_entrada(cinta)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    mt, gens = simular(cinta)
    for i, g in enumerate(gens):
        print(f"Gen {i:>3}: {' '.join(g)}")
    print(f"\nCinta final: {mt.cinta.contenido()}")
    print(f"Estado: {mt.estado} ({mt.motivo}) · pasos: {mt.pasos} · cabezal: {mt.cabezal}")
    return 0


def ejecutar_pruebas(ruta: str) -> int:
    from pruebas import ejecutar_archivo
    resultados = ejecutar_archivo(ruta)
    for r in resultados:
        marca = "OK   " if r.ok else "FALLA"
        print(f"[{marca}] línea {r.caso.linea:>3}  {r.caso.entrada:<45} pasos={r.pasos:<7} {r.caso.descripcion}")
        if not r.ok:
            print(f"        {r.mensaje}")
    aprobados = sum(r.ok for r in resultados)
    print(f"\n{aprobados}/{len(resultados)} casos aprobados")
    return 0 if aprobados == len(resultados) else 1


def imprimir_tabla() -> int:
    print(f"|Q| = {len(ESTADOS)}   |δ| = {len(DELTA)}\n")
    print(f"{'Estado':<18}{'Lee':<5}{'Escribe':<9}{'Mueve':<7}Siguiente")
    previo = None
    for q, s, w, m, sig in tabla_transiciones():
        if previo and q != previo:
            print()
        print(f"{q:<18}{s:<5}{w:<9}{m:<7}{sig}")
        previo = q
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Máquina de Turing - Regla 110")
    p.add_argument("--cinta", help="ejecuta la cinta indicada por consola")
    p.add_argument("--pruebas", metavar="ARCHIVO", help="ejecuta los casos de prueba de un .txt")
    p.add_argument("--tabla", action="store_true", help="imprime la tabla de transiciones")
    a = p.parse_args()
    if a.cinta:
        return ejecutar_consola(a.cinta)
    if a.pruebas:
        return ejecutar_pruebas(a.pruebas)
    if a.tabla:
        return imprimir_tabla()
    from interfaz import main as gui
    gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
