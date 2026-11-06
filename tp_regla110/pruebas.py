"""
Carga y ejecución de casos de prueba desde un archivo .txt.

Formato: un caso por línea
    ENTRADA[;GENERACION_FINAL_ESPERADA[;DESCRIPCION]]
Las líneas vacías y las que comienzan con '//' se ignoran.

Cada caso se ejecuta en la Máquina de Turing y se verifica que:
  1. la máquina se detenga en el estado final,
  2. el contador K quede en cero,
  3. TODAS las generaciones registradas en la cinta coincidan con la
     implementación de referencia de la Regla 110,
  4. la generación final quede entre los dos primeros '#' de la cinta,
  5. la generación final coincida con la esperada (si se indicó).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from regla110_mt import (
    decodificar_cinta, regla110_referencia, simular, validar_entrada,
)


@dataclass
class Caso:
    linea: int
    entrada: str
    esperado: Optional[str] = None
    descripcion: str = ""


@dataclass
class Resultado:
    caso: Caso
    ok: bool
    k: int = 0
    n: int = 0
    pasos: int = 0
    final: str = ""
    cinta_final: str = ""
    errores: List[str] = field(default_factory=list)

    @property
    def mensaje(self) -> str:
        return "OK" if self.ok else "; ".join(self.errores)


def parsear_casos(texto: str) -> List[Caso]:
    casos = []
    for nro, linea in enumerate(texto.splitlines(), start=1):
        linea = linea.strip()
        if not linea or linea.startswith("//"):
            continue
        partes = [p.strip() for p in linea.split(";")]
        entrada = partes[0]
        esperado = partes[1] if len(partes) > 1 and partes[1] else None
        descripcion = partes[2] if len(partes) > 2 else ""
        casos.append(Caso(nro, entrada, esperado, descripcion))
    return casos


def cargar_casos(ruta: str) -> List[Caso]:
    with open(ruta, encoding="utf-8") as f:
        return parsear_casos(f.read())


def ejecutar_caso(caso: Caso) -> Resultado:
    try:
        k, config = validar_entrada(caso.entrada)
    except ValueError as e:
        return Resultado(caso, False, errores=[f"Entrada inválida: {e}"])

    res = Resultado(caso, True, k=k, n=len(config))
    try:
        mt, gens = simular(caso.entrada)
    except RuntimeError as e:
        res.ok = False
        res.errores.append(str(e))
        return res

    res.pasos = mt.pasos
    res.cinta_final = mt.cinta.contenido()
    res.final = gens[-1] if gens else ""
    k_restante, _, parcial = decodificar_cinta(res.cinta_final)
    if res.cinta_final.split("#")[1] != res.final:
        res.errores.append(f"La generación final no quedó entre los dos primeros '#': {res.cinta_final}")

    if not mt.aceptada:
        res.errores.append(f"No se detuvo en estado final ({mt.motivo})")
    if k_restante != 0:
        res.errores.append(f"K restante = {k_restante}")
    if parcial:
        res.errores.append("Quedó una generación sin cerrar")

    ref = regla110_referencia(config, k)
    if len(gens) != len(ref):
        res.errores.append(f"Se registraron {len(gens)} generaciones; se esperaban {len(ref)}")
    else:
        for i, (a, b) in enumerate(zip(gens, ref)):
            if a != b:
                res.errores.append(f"Generación {i}: MT={a} referencia={b}")
                break
    if caso.esperado is not None and res.final != caso.esperado:
        res.errores.append(f"Final {res.final} ≠ esperado {caso.esperado}")
    # La MT debe terminar con el cabezal sobre la configuración final
    if mt.aceptada and gens:
        inicio_final = res.cinta_final.index("#") + 1
        if mt.cabezal != inicio_final:
            res.errores.append("El cabezal no quedó sobre la configuración final")

    res.ok = not res.errores
    return res


def ejecutar_archivo(ruta: str) -> List[Resultado]:
    return [ejecutar_caso(c) for c in cargar_casos(ruta)]
