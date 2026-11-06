"""
Máquina de Turing determinista genérica de una cinta.

    M = (Q, Σ, Γ, δ, q0, B, F)

- La cinta es bi-infinita y se implementa con un diccionario disperso
  (posición -> símbolo); toda celda no escrita contiene el blanco B.
- δ es una función parcial  Q x Γ -> Γ x {L, R} x Q
  representada como dict[(estado, símbolo)] -> Transicion.
- La máquina se detiene al entrar en un estado de F, o cuando δ no está
  definida para el par (estado, símbolo) actual (detención por rechazo).
- δ se construye con las operaciones básicas L, R, X, Lx, Rx, Sl y Sr.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

BLANCO = "_"
IZQ = "L"
DER = "R"


@dataclass(frozen=True)
class Transicion:
    """Resultado de δ(q, s): símbolo a escribir, movimiento y próximo estado."""
    escribe: str
    mueve: str        # 'L' o 'R'
    siguiente: str


Delta = Dict[Tuple[str, str], Transicion]


# ------------------------------------------------------- operaciones básicas
# Cada operación agrega a δ las transiciones que la implementan, a partir del
# estado `q`. Como δ exige mover el cabezal en toda transición, X, Lx y Rx
# reciben el movimiento con el que terminan.
def _agregar(delta: Delta, q: str, lee: str, escribe: str, mueve: str, siguiente: str) -> None:
    clave = (q, lee)
    if clave in delta:  # garantiza determinismo
        raise ValueError(f"Transición duplicada para {clave}")
    delta[clave] = Transicion(escribe, mueve, siguiente)


def L(delta: Delta, q: str, simbolos: Iterable[str], siguiente: str) -> None:
    """L: mueve una celda a la izquierda sin modificar la cinta."""
    for s in simbolos:
        _agregar(delta, q, s, s, IZQ, siguiente)


def R(delta: Delta, q: str, simbolos: Iterable[str], siguiente: str) -> None:
    """R: mueve una celda a la derecha sin modificar la cinta."""
    for s in simbolos:
        _agregar(delta, q, s, s, DER, siguiente)


def X(delta: Delta, q: str, lee: str, x: str, mueve: str, siguiente: str) -> None:
    """X: leyendo `lee`, escribe el símbolo `x` y mueve según `mueve`."""
    _agregar(delta, q, lee, x, mueve, siguiente)


def Lx(delta: Delta, q: str, x: str, atraviesa: Iterable[str], mueve: str, siguiente: str,
       escribe: Optional[str] = None) -> None:
    """Lx: avanza a la izquierda por `atraviesa` hasta hallar `x`; ahí escribe
    `escribe` (por omisión, deja `x`) y sale con `mueve`."""
    L(delta, q, atraviesa, q)
    _agregar(delta, q, x, x if escribe is None else escribe, mueve, siguiente)


def Rx(delta: Delta, q: str, x: str, atraviesa: Iterable[str], mueve: str, siguiente: str,
       escribe: Optional[str] = None) -> None:
    """Rx: avanza a la derecha por `atraviesa` hasta hallar `x`; ahí escribe
    `escribe` (por omisión, deja `x`) y sale con `mueve`."""
    R(delta, q, atraviesa, q)
    _agregar(delta, q, x, x if escribe is None else escribe, mueve, siguiente)


def Sl(delta: Delta, q: str, alfabeto: Iterable[str], siguiente: str, blanco: str = BLANCO) -> List[str]:
    """Sl: corrimiento a la izquierda,  _w_ -> w__.

    Con el cabezal sobre el primer símbolo de w (sin blancos y con un blanco a
    su izquierda), corre w una celda y termina en la celda siguiente a w.
    Devuelve los estados auxiliares que creó.
    """
    avanzar = f"{q}__avanzar"
    auxiliares = []
    for s in alfabeto:
        poner = f"{q}__poner_{s}"
        X(delta, q, s, blanco, IZQ, poner)
        X(delta, poner, blanco, s, DER, avanzar)
        auxiliares.append(poner)
    R(delta, avanzar, blanco, q)
    L(delta, q, blanco, siguiente)
    return auxiliares + [avanzar]


def Sr(delta: Delta, q: str, alfabeto: Iterable[str], siguiente: str, blanco: str = BLANCO) -> List[str]:
    """Sr: corrimiento a la derecha,  w_ -> _w.

    Con el cabezal sobre el primer símbolo de w (sin blancos y con un blanco a
    su derecha), corre w una celda y termina en la celda siguiente a w.
    Devuelve los estados auxiliares que creó.
    """
    alfabeto = tuple(alfabeto)
    auxiliares = []
    for s in alfabeto:
        llevar = f"{q}__llevar_{s}"
        X(delta, q, s, blanco, DER, llevar)
        for t in alfabeto:
            X(delta, llevar, t, s, DER, f"{q}__llevar_{t}")
        X(delta, llevar, blanco, s, DER, siguiente)
        auxiliares.append(llevar)
    R(delta, q, blanco, siguiente)
    return auxiliares


class Cinta:
    """Cinta bi-infinita dispersa."""

    def __init__(self, contenido: str = "", blanco: str = BLANCO) -> None:
        self.blanco = blanco
        self._celdas: Dict[int, str] = {}
        for i, s in enumerate(contenido):
            if s != blanco:
                self._celdas[i] = s
        # Rango de posiciones visitadas o escritas (para visualización).
        self.min_pos = 0
        self.max_pos = max(len(contenido) - 1, 0)

    def leer(self, pos: int) -> str:
        return self._celdas.get(pos, self.blanco)

    def escribir(self, pos: int, simbolo: str) -> None:
        if simbolo == self.blanco:
            self._celdas.pop(pos, None)
        else:
            self._celdas[pos] = simbolo
        self.tocar(pos)

    def tocar(self, pos: int) -> None:
        """Registra que el cabezal pasó por `pos` (amplía el rango visible)."""
        if pos < self.min_pos:
            self.min_pos = pos
        if pos > self.max_pos:
            self.max_pos = pos

    def contenido(self) -> str:
        """Contenido entre el primer y el último símbolo no blanco."""
        if not self._celdas:
            return ""
        a, b = min(self._celdas), max(self._celdas)
        return "".join(self.leer(i) for i in range(a, b + 1))

    def __str__(self) -> str:
        return self.contenido()


class MaquinaTuring:
    def __init__(
        self,
        delta: Dict[Tuple[str, str], Transicion],
        estado_inicial: str,
        estados_finales: Iterable[str],
        blanco: str = BLANCO,
    ) -> None:
        self.delta = delta
        self.estado_inicial = estado_inicial
        self.estados_finales = frozenset(estados_finales)
        self.blanco = blanco
        self.reiniciar("")

    # ------------------------------------------------------------------ estado
    def reiniciar(self, entrada: str, pos_cabezal: int = 0) -> None:
        self.cinta = Cinta(entrada, self.blanco)
        self.cabezal = pos_cabezal
        self.estado = self.estado_inicial
        self.pasos = 0
        self.detenida = self.estado in self.estados_finales
        self.motivo = "estado final" if self.detenida else ""
        # (estado, símbolo leído) de la última transición aplicada
        self.ultima_clave: Optional[Tuple[str, str]] = None
        self.ultima_posicion: Optional[int] = None

    @property
    def aceptada(self) -> bool:
        return self.estado in self.estados_finales

    @property
    def simbolo_actual(self) -> str:
        return self.cinta.leer(self.cabezal)

    # --------------------------------------------------------------- ejecución
    def paso(self) -> bool:
        """Aplica una transición. Devuelve False si la máquina ya está detenida."""
        if self.detenida:
            return False
        simbolo = self.cinta.leer(self.cabezal)
        clave = (self.estado, simbolo)
        tr = self.delta.get(clave)
        if tr is None:
            self.detenida = True
            self.motivo = f"δ({self.estado}, {simbolo}) no definida"
            return False

        self.cinta.escribir(self.cabezal, tr.escribe)
        self.ultima_posicion = self.cabezal
        self.cabezal += -1 if tr.mueve == IZQ else 1
        self.cinta.tocar(self.cabezal)
        self.estado = tr.siguiente
        self.pasos += 1
        self.ultima_clave = clave

        if self.estado in self.estados_finales:
            self.detenida = True
            self.motivo = "estado final"
        return True

    def ejecutar(self, max_pasos: int = 10_000_000) -> int:
        """Ejecuta hasta detenerse. Lanza RuntimeError si supera max_pasos."""
        inicio = self.pasos
        while self.paso():
            if self.pasos - inicio >= max_pasos:
                raise RuntimeError(f"Se superó el límite de {max_pasos} pasos")
        return self.pasos - inicio
