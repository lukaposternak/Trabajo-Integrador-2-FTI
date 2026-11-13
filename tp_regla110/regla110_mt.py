"""
Máquina de Turing que simula K generaciones del autómata celular
elemental Regla 110 con frontera cíclica.

Formato de la cinta
-------------------
    entrada:  K#c0 c1 ... c(N-1)#            (K en binario, N >= 8)
    salida:   0..0#GK#                       (K decrementado a cero y la
                                              generación final entre los
                                              dos '#' iniciales; durante la
                                              ejecución la cinta registra
                                              G0#G1#...#GK# y al final se
                                              borra lo que sigue al 2.º '#')

Alfabeto de cinta  Γ = {0, 1, X, Y, #, _}
    0, 1 : valores de celda (y bits del contador K)
    X, Y : celda de la generación actual YA procesada que valía 0 / 1
           (las marcas conservan el valor, por lo que siguen sirviendo
           como vecinas de las celdas que todavía falta procesar).
           Al terminar, marcan el inicio de la generación final.
    #    : separador de generaciones / contador
    _    : blanco

Algoritmo (un ciclo por generación)
-----------------------------------
1. Control de K: si K = 0 pasa a la etapa final (punto 5); si no, K := K - 1
   (decremento binario: los 0 finales pasan a 1 y el primer 1 a 0).
2. Se abre la generación t+1 escribiendo su '#' de cierre al final de la
   cinta y se localiza la generación actual (la última ya cerrada).
3. Para cada celda i, de izquierda a derecha:
     a) se toma la vecina izquierda L. Para i>0 es la celda ya marcada que
        se acaba de recorrer (se recuerda en el estado). Para i=0 (frontera
        cíclica) se viaja hasta la última celda de la generación y se lee.
     b) se lee la celda C (0/1 sin marcar) y se marca (X/Y).
     c) se lee la vecina derecha R. Si en su lugar hay '#' (i = N-1,
        frontera cíclica) se vuelve al comienzo y se lee la celda 0.
     d) el estado ya contiene el par (L, C) y el símbolo leído aporta R:
        se calcula f(L, C, R) con la tabla de la Regla 110, se viaja al
        '#' de cierre de t+1, se lo corre una celda (Sr) y se escribe el
        nuevo bit (X) en el hueco.
4. Al no quedar celdas sin marcar se restauran X/Y -> 0/1 (preservación de
   la generación t) y se vuelve al inicio de la cinta para repetir el ciclo.
5. Con K = 0 se marca el inicio de GK y se pasa, símbolo por símbolo, lo que
   está antes de la marca al final de la cinta: se copia el símbolo y se
   cierra su hueco con Sl. Al llegar la marca a los dos primeros '#', se la
   quita.
6. Limpieza: se avanza hasta el segundo '#' y se borra (con blancos) todo lo
   que le sigue: las generaciones G0..G(K-1). El cabezal vuelve a la primera
   celda de GK y la máquina se detiene.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple

from maquina_turing import BLANCO, DER, IZQ, Delta, L, Lx, MaquinaTuring, R, Rx, Sl, Sr, X

# ---------------------------------------------------------------- Regla 110
REGLA_110: Dict[Tuple[int, int, int], int] = {
    (1, 1, 1): 0,
    (1, 1, 0): 1,
    (1, 0, 1): 1,
    (1, 0, 0): 0,
    (0, 1, 1): 1,
    (0, 1, 0): 1,
    (0, 0, 1): 1,
    (0, 0, 0): 0,
}

SEP = "#"
MARCA = {"0": "X", "1": "Y"}                      # valor -> símbolo marcado
VALOR = {"0": 0, "1": 1, "X": 0, "Y": 1}          # símbolo -> valor de celda
BITS = ("0", "1")
MARCADAS = ("X", "Y")                             # celdas ya procesadas
CELDAS = BITS + MARCADAS                          # cualquier celda de la generación
ALFABETO_ENTRADA = ("0", "1", "#")
ALFABETO_CINTA = ("0", "1", "X", "Y", "#", BLANCO)

Q0 = "q_verificarK"
Q_FIN = "q_fin"

# ------------------------------------------------------------ construcción δ
DELTA: Delta = {}
ESTADOS: List[str] = []                 # en orden de presentación
DESCRIPCION: Dict[str, str] = {}        # estado -> qué hace


def _estado(nombre: str, descripcion: str) -> str:
    ESTADOS.append(nombre)
    DESCRIPCION[nombre] = descripcion
    return nombre


def _construir() -> None:
    # ---------------------------------------------------- 1. control de K
    _estado(Q0, "Inicio de ciclo: recorre K buscando algún 1. Si llega a '#', K = 0 → terminar.")
    R(DELTA, Q0, "0", Q0)
    R(DELTA, Q0, "1", "q_finK")
    R(DELTA, Q0, SEP, "q_mostrar1")

    _estado("q_finK", "K ≠ 0: avanza hasta el '#' que cierra el contador.")
    Rx(DELTA, "q_finK", SEP, BITS, IZQ, "q_decK")

    _estado("q_decK", "Decremento binario de K: 0→1 con préstamo hacia la izquierda; el primer 1 pasa a 0.")
    X(DELTA, "q_decK", "0", "1", IZQ, "q_decK")
    X(DELTA, "q_decK", "1", "0", DER, "q_irFinCinta")

    # ------------------------------------ 2. ubicar la generación actual
    _estado("q_irFinCinta", "Viaja al primer blanco y escribe el '#' de cierre de la generación t+1.")
    Rx(DELTA, "q_irFinCinta", BLANCO, BITS + (SEP,), IZQ, "q_saltarTerm", escribe=SEP)

    _estado("q_saltarTerm", "Salta el '#' que cierra la última generación.")
    L(DELTA, "q_saltarTerm", SEP, "q_iniGen")

    _estado("q_iniGen", "Retrocede hasta el '#' que abre la generación actual.")
    Lx(DELTA, "q_iniGen", SEP, BITS, DER, "q_celda0")

    # ------------------------------- 3. procesamiento celda por celda
    _estado("q_celda0", "Sobre la celda 0. Sin marcar → falta la vecina izquierda cíclica (última celda). "
                        "Marcada → recorre buscando la próxima celda sin procesar.")
    R(DELTA, "q_celda0", BITS, "q_buscarUlt")
    R(DELTA, "q_celda0", "X", "q_C_L0")
    R(DELTA, "q_celda0", "Y", "q_C_L1")

    _estado("q_buscarUlt", "Frontera cíclica izquierda: avanza hasta el '#' final de la generación.")
    Rx(DELTA, "q_buscarUlt", SEP, BITS, IZQ, "q_leerUlt")

    _estado("q_leerUlt", "Lee la última celda c(N-1): será la vecina izquierda de c0.")
    L(DELTA, "q_leerUlt", "0", "q_volverIni_L0")
    L(DELTA, "q_leerUlt", "1", "q_volverIni_L1")

    for l in (0, 1):
        q = f"q_volverIni_L{l}"
        _estado(q, f"Recuerda L={l}; vuelve al inicio de la generación.")
        Lx(DELTA, q, SEP, BITS, DER, f"q_C_L{l}")

    for l in (0, 1):
        q = f"q_C_L{l}"
        _estado(q, f"Vecina izquierda L={l}. Pasa celdas ya marcadas (actualizando L); "
                   f"la primera sin marcar es la celda central C: la marca. '#' → generación completa.")
        R(DELTA, q, "X", "q_C_L0")
        R(DELTA, q, "Y", "q_C_L1")
        X(DELTA, q, "0", "X", DER, f"q_R_{l}0")
        X(DELTA, q, "1", "Y", DER, f"q_R_{l}1")
        L(DELTA, q, SEP, "q_restaurar")

    for l in (0, 1):
        for c in (0, 1):
            q = f"q_R_{l}{c}"
            _estado(q, f"Ventana (L,C)=({l},{c}). Lee la vecina derecha R y aplica la Regla 110. "
                       f"Si encuentra '#', R es la celda 0 (frontera cíclica).")
            for s in BITS:      # a la derecha de C todavía no hay celdas marcadas
                v = REGLA_110[(l, c, VALOR[s])]
                R(DELTA, q, s, f"q_escribir_{v}")
            L(DELTA, q, SEP, f"q_wrap_{l}{c}")

    for l in (0, 1):
        for c in (0, 1):
            q = f"q_wrap_{l}{c}"
            _estado(q, f"Frontera cíclica derecha con (L,C)=({l},{c}): retrocede al inicio de la generación.")
            Lx(DELTA, q, SEP, MARCADAS, DER, f"q_leerC0_{l}{c}")    # todas las celdas ya están marcadas

    for l in (0, 1):
        for c in (0, 1):
            q = f"q_leerC0_{l}{c}"
            _estado(q, f"Lee c0 como vecina derecha R de la última celda y aplica la Regla 110 a ({l},{c},R).")
            for s in MARCADAS:  # c0 fue la primera celda en marcarse
                v = REGLA_110[(l, c, VALOR[s])]
                R(DELTA, q, s, f"q_escribir_{v}")

    for v in (0, 1):
        q = f"q_escribir_{v}"
        _estado(q, f"Lleva el resultado {v}: avanza hasta el final de la generación actual.")
        Rx(DELTA, q, SEP, CELDAS, DER, f"q_escribirNueva_{v}")

        q2 = f"q_escribirNueva_{v}"
        _estado(q2, f"Recorre la generación t+1 y corre su '#' de cierre una celda (Sr) para abrir lugar a {v}.")
        R(DELTA, q2, BITS, q2)
        for aux in Sr(DELTA, q2, (SEP,), f"q_trasSr_{v}"):
            _estado(aux, f"Sr: lleva el '#' de cierre una celda a la derecha (resultado {v}).")

        q3 = f"q_trasSr_{v}"
        _estado(q3, f"Terminó Sr: vuelve hacia el '#' corrido (resultado {v}).")
        L(DELTA, q3, BLANCO, f"q_cruzarCierre_{v}")

        q4 = f"q_cruzarCierre_{v}"
        _estado(q4, f"Cruza el '#' corrido hacia el hueco (resultado {v}).")
        L(DELTA, q4, SEP, f"q_ponerBit_{v}")

        q5 = f"q_ponerBit_{v}"
        _estado(q5, f"Escribe {v} en el hueco que dejó Sr.")
        X(DELTA, q5, BLANCO, str(v), IZQ, "q_volverNueva")

    _estado("q_volverNueva", "Retrocede por la generación t+1 hasta su '#' de apertura.")
    Lx(DELTA, "q_volverNueva", SEP, BITS, IZQ, "q_volverActual")

    _estado("q_volverActual", "Retrocede por la generación t hasta su '#' de apertura.")
    Lx(DELTA, "q_volverActual", SEP, CELDAS, DER, "q_celda0")

    # -------------------------------------- 4. cierre de la generación
    _estado("q_restaurar", "Preserva la generación t: desmarca X→0, Y→1.")
    X(DELTA, "q_restaurar", "X", "0", IZQ, "q_restaurar")
    X(DELTA, "q_restaurar", "Y", "1", IZQ, "q_restaurar")
    L(DELTA, "q_restaurar", SEP, "q_irInicio")

    _estado("q_irInicio", "Vuelve al extremo izquierdo de la cinta (inicio de K) para un nuevo ciclo.")
    Lx(DELTA, "q_irInicio", BLANCO, BITS + (SEP,), DER, Q0)

    # ---------- 5. etapa final (K = 0): GK pasa a los dos primeros '#'
    _estado("q_mostrar1", "K = 0: viaja al final de la cinta.")
    Rx(DELTA, "q_mostrar1", BLANCO, BITS + (SEP,), IZQ, "q_mostrar2")

    _estado("q_mostrar2", "Salta el '#' final.")
    L(DELTA, "q_mostrar2", SEP, "q_mostrar3")

    _estado("q_mostrar3", "Retrocede al comienzo de la generación final GK.")
    Lx(DELTA, "q_mostrar3", SEP, BITS, DER, "q_marcarGK")

    _estado("q_marcarGK", "Marca la primera celda de GK (0→X, 1→Y) para reconocerla al llegar al frente.")
    X(DELTA, "q_marcarGK", "0", "X", IZQ, "q_irIzq")
    X(DELTA, "q_marcarGK", "1", "Y", IZQ, "q_irIzq")

    _estado("q_irIzq", "Viaja al extremo izquierdo de la cinta.")
    Lx(DELTA, "q_irIzq", BLANCO, CELDAS + (SEP,), DER, "q_saltarK")

    _estado("q_saltarK", "Cruza K (ya en cero) hasta el primer '#'.")
    Rx(DELTA, "q_saltarK", SEP, "0", DER, "q_frente")

    _estado("q_frente", "Primer símbolo tras el primer '#'. Marca → GK ya llegó: la desmarca. "
                        "Otro símbolo → lo saca para llevarlo al final de la cinta.")
    X(DELTA, "q_frente", "X", "0", DER, "q_ajustar")
    X(DELTA, "q_frente", "Y", "1", DER, "q_ajustar")
    for s in BITS + (SEP,):
        q = f"q_llevar_{s}"
        X(DELTA, "q_frente", s, BLANCO, DER, q)
        _estado(q, f"Lleva '{s}' al final de la cinta y lo escribe en el primer blanco.")
        Rx(DELTA, q, BLANCO, CELDAS + (SEP,), IZQ, "q_volverHueco", escribe=s)

    _estado("q_volverHueco", "Retrocede hasta el hueco que dejó el símbolo sacado.")
    Lx(DELTA, "q_volverHueco", BLANCO, CELDAS + (SEP,), DER, "q_correr")

    _estado("q_correr", "Sl: cierra el hueco corriendo una celda a la izquierda todo lo que le sigue.")
    for aux in Sl(DELTA, "q_correr", CELDAS + (SEP,), "q_trasSl"):
        _estado(aux, "Sl: lleva un símbolo una celda a la izquierda.")

    _estado("q_trasSl", "Terminó Sl: vuelve a la última celda escrita de la cinta.")
    L(DELTA, "q_trasSl", BLANCO, "q_irIzq")

    # ---- 6. limpieza: se borra todo lo que queda después del segundo '#'
    _estado("q_ajustar", "GK ya está entre los dos primeros '#': avanza hasta el segundo '#'.")
    Rx(DELTA, "q_ajustar", SEP, BITS, DER, "q_borrar")

    _estado("q_borrar", "Borra (escribe blanco) todo lo que sigue al segundo '#' hasta el final de la cinta.")
    for s in BITS + (SEP,):
        X(DELTA, "q_borrar", s, BLANCO, DER, "q_borrar")
    L(DELTA, "q_borrar", BLANCO, "q_volverSep")

    _estado("q_volverSep", "Cinta limpia: retrocede por los blancos hasta el segundo '#'.")
    Lx(DELTA, "q_volverSep", SEP, (BLANCO,), IZQ, "q_volverGK")

    _estado("q_volverGK", "Retrocede por GK hasta el primer '#' y se para en su primera celda.")
    Lx(DELTA, "q_volverGK", SEP, BITS, DER, Q_FIN)

    _estado(Q_FIN, "Estado final (aceptación): el cabezal queda sobre la primera celda de la generación K.")


_construir()


def _verificar_tabla() -> None:
    """Chequeos estructurales: todo estado destino existe y todo símbolo pertenece a Γ."""
    for (q, s), tr in DELTA.items():
        assert q in DESCRIPCION, q
        assert tr.siguiente in DESCRIPCION, tr.siguiente
        assert s in ALFABETO_CINTA and tr.escribe in ALFABETO_CINTA
        assert tr.mueve in (IZQ, DER)


_verificar_tabla()


def crear_maquina() -> MaquinaTuring:
    return MaquinaTuring(DELTA, Q0, {Q_FIN}, BLANCO)


def tabla_transiciones() -> List[Tuple[str, str, str, str, str]]:
    """Filas (estado, lee, escribe, mueve, siguiente) en orden de presentación."""
    orden_simbolos = {s: i for i, s in enumerate(ALFABETO_CINTA)}
    filas = []
    for q in ESTADOS:
        trans = [(s, tr) for (e, s), tr in DELTA.items() if e == q]
        trans.sort(key=lambda x: orden_simbolos[x[0]])
        for s, tr in trans:
            filas.append((q, s, tr.escribe, tr.mueve, tr.siguiente))
    return filas


# ------------------------------------------------- entrada / salida y referencia
PATRON_ENTRADA = re.compile(r"^([01]+)#([01]+)#$")
N_MINIMO = 8


def validar_entrada(cinta: str) -> Tuple[int, str]:
    """Valida 'K#config#' y devuelve (K, config). Lanza ValueError si es inválida."""
    cinta = cinta.strip().replace(" ", "")
    m = PATRON_ENTRADA.match(cinta)
    if not m:
        raise ValueError(
            "Formato inválido. Se espera K en binario, '#', la configuración "
            "binaria y '#'. Ejemplo: 100#000000010000000#"
        )
    k_bin, config = m.groups()
    if len(config) < N_MINIMO:
        raise ValueError(f"La configuración debe tener N ≥ {N_MINIMO} celdas (tiene {len(config)}).")
    return int(k_bin, 2), config


def codificar_entrada(k: int, config: str) -> str:
    if k < 0:
        raise ValueError("K debe ser ≥ 0")
    if not config or set(config) - {"0", "1"}:
        raise ValueError("La configuración debe ser una hilera binaria no vacía")
    return f"{k:b}#{config}#"


def decodificar_cinta(contenido: str) -> Tuple[int, str, str]:
    """
    A partir del contenido de la cinta durante los ciclos devuelve
    (K restante, última generación completa, generación en construcción).
    Las marcas X/Y se leen como 0/1 y se ignoran los blancos que aparecen
    durante Sr.
    """
    partes = contenido.split(SEP)
    k_bin = partes[0]
    k = int(k_bin, 2) if k_bin and set(k_bin) <= {"0", "1"} else 0
    gens = [p.replace("X", "0").replace("Y", "1").replace(BLANCO, "") for p in partes[1:]]
    while gens and not gens[-1]:
        gens.pop()
    if not gens:
        return k, "", ""
    if len(gens) > 1 and len(gens[-1]) < len(gens[0]):
        return k, gens[-2], gens[-1]
    return k, gens[-1], ""


def fin_de_ciclo(mt: MaquinaTuring) -> bool:
    """True justo al volver a q0 con una nueva generación cerrada en la cinta."""
    return mt.estado == Q0 and mt.ultima_clave is not None and mt.ultima_clave[0] == "q_irInicio"


def regla110_paso(config: str) -> str:
    """Una generación de la Regla 110 con frontera cíclica (implementación de referencia)."""
    n = len(config)
    c = [int(ch) for ch in config]
    return "".join(str(REGLA_110[(c[i - 1], c[i], c[(i + 1) % n])]) for i in range(n))


def regla110_referencia(config: str, k: int) -> List[str]:
    """Lista [G0, G1, ..., GK] calculada directamente en Python."""
    gens = [config]
    for _ in range(k):
        gens.append(regla110_paso(gens[-1]))
    return gens


def simular(cinta: str, max_pasos: int = 50_000_000):
    """Ejecuta la MT sobre `cinta` hasta detenerse. Devuelve (máquina, [G0, ..., GK]).

    Como al final la cinta sólo conserva GK, cada generación se registra al
    cerrarse su ciclo, mientras todavía está escrita en la cinta.
    Lanza ValueError si la entrada es inválida y RuntimeError si supera max_pasos.
    """
    _, config = validar_entrada(cinta)
    mt = crear_maquina()
    mt.reiniciar(cinta.strip())
    gens = [config]
    while mt.paso():
        if mt.pasos >= max_pasos:
            raise RuntimeError(f"Se superó el límite de {max_pasos} pasos")
        if fin_de_ciclo(mt):
            gens.append(decodificar_cinta(mt.cinta.contenido())[1])
    return mt, gens
