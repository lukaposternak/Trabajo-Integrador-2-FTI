"""Pruebas unitarias:  python -m unittest -v test_regla110"""
import os
import random
import unittest

from maquina_turing import BLANCO, DER, IZQ, L, Lx, MaquinaTuring, R, Rx, Sl, Sr, X
from pruebas import Caso, ejecutar_archivo, ejecutar_caso
from regla110_mt import (
    ALFABETO_CINTA, DELTA, ESTADOS, Q0, Q_FIN, REGLA_110, codificar_entrada,
    crear_maquina, decodificar_cinta, regla110_paso, regla110_referencia,
    simular, validar_entrada,
)


class TestOperaciones(unittest.TestCase):
    GAMMA = ("0", "1", "#")

    def correr(self, delta, entrada, pos=0):
        mt = MaquinaTuring(delta, "q", {"f"})
        mt.reiniciar(entrada, pos)
        mt.ejecutar(10_000)
        self.assertTrue(mt.aceptada, mt.motivo)
        return mt

    def test_L_R(self):
        for op, esperado in ((L, 0), (R, 2)):
            delta = {}
            op(delta, "q", self.GAMMA, "f")
            mt = self.correr(delta, "101", 1)
            self.assertEqual((mt.cabezal, mt.cinta.contenido()), (esperado, "101"))

    def test_X(self):
        delta = {}
        X(delta, "q", "1", "#", DER, "f")
        mt = self.correr(delta, "101")
        self.assertEqual((mt.cabezal, mt.cinta.contenido()), (1, "#01"))

    def test_Lx_Rx(self):
        delta = {}
        Rx(delta, "q", "#", ("0", "1"), IZQ, "f")
        mt = self.correr(delta, "01#1")
        self.assertEqual((mt.cabezal, mt.cinta.contenido()), (1, "01#1"))

        delta = {}
        Lx(delta, "q", "#", ("0", "1"), DER, "f")
        mt = self.correr(delta, "1#01", 3)
        self.assertEqual((mt.cabezal, mt.cinta.contenido()), (2, "1#01"))

    def test_Rx_escribe_al_hallar(self):
        delta = {}
        Rx(delta, "q", BLANCO, ("0", "1"), IZQ, "f", escribe="#")
        self.assertEqual(self.correr(delta, "01").cinta.contenido(), "01#")

    def test_Sr(self):
        for w in ("0", "1", "01#10", "111"):
            delta = {}
            Sr(delta, "q", self.GAMMA, "f")
            mt = self.correr(delta, w)
            self.assertEqual(mt.cabezal, len(w) + 1)
            self.assertEqual("".join(mt.cinta.leer(i) for i in range(len(w) + 2)), BLANCO + w + BLANCO)

    def test_Sl(self):
        for w in ("0", "1", "01#10", "111"):
            delta = {}
            Sl(delta, "q", self.GAMMA, "f")
            mt = self.correr(delta, BLANCO + w, 1)
            self.assertEqual(mt.cabezal, len(w))
            self.assertEqual("".join(mt.cinta.leer(i) for i in range(len(w) + 2)), w + BLANCO * 2)

    def test_Sl_no_pasa_del_simbolo_a_su_izquierda(self):
        delta = {}
        Sl(delta, "q", self.GAMMA, "f")
        mt = self.correr(delta, "1#" + BLANCO + "01", 3)
        self.assertEqual(mt.cinta.contenido(), "1#01")
        self.assertEqual(mt.cabezal, 4)

    def test_corrimiento_de_cadena_vacia(self):
        delta = {}
        Sr(delta, "q", self.GAMMA, "f")
        self.assertEqual(self.correr(delta, "").cabezal, 1)
        delta = {}
        Sl(delta, "q", self.GAMMA, "f")
        self.assertEqual(self.correr(delta, "", 1).cabezal, 0)

    def test_transicion_duplicada(self):
        delta = {}
        R(delta, "q", "0", "f")
        with self.assertRaises(ValueError):
            L(delta, "q", "0", "f")


class TestReferencia(unittest.TestCase):
    def test_tabla_regla_110(self):
        # 110 = 0b01101110: el bit i es la salida para la vecindad de valor i
        for i in range(8):
            vec = ((i >> 2) & 1, (i >> 1) & 1, i & 1)
            self.assertEqual(REGLA_110[vec], (110 >> i) & 1)

    def test_ejemplo_enunciado(self):
        self.assertEqual(regla110_referencia("000100", 3),
                         ["000100", "001100", "011100", "110100"])


class TestTablaTransiciones(unittest.TestCase):
    def test_determinista_y_bien_formada(self):
        for (q, s), tr in DELTA.items():
            self.assertIn(q, ESTADOS)
            self.assertIn(tr.siguiente, ESTADOS)
            self.assertIn(s, ALFABETO_CINTA)
            self.assertIn(tr.escribe, ALFABETO_CINTA)

    def test_estado_final_sin_salidas(self):
        self.assertFalse([k for k in DELTA if k[0] == Q_FIN])

    def test_cada_transicion_de_regla_usa_la_tabla(self):
        for l in (0, 1):
            for c in (0, 1):
                for r, s, marca in ((0, "0", "X"), (1, "1", "Y")):
                    v = REGLA_110[(l, c, r)]
                    self.assertEqual(DELTA[(f"q_R_{l}{c}", s)].siguiente, f"q_escribir_{v}")
                    self.assertEqual(DELTA[(f"q_leerC0_{l}{c}", marca)].siguiente, f"q_escribir_{v}")


class TestMaquina(unittest.TestCase):
    def comprobar(self, cinta):
        k, config = validar_entrada(cinta)
        mt, gens = simular(cinta)
        self.assertTrue(mt.aceptada, mt.motivo)
        self.assertEqual(gens, regla110_referencia(config, k))
        k_rest, _, parcial = decodificar_cinta(mt.cinta.contenido())
        self.assertEqual(k_rest, 0)
        self.assertEqual(parcial, "")
        self.assertEqual(mt.simbolo_actual, gens[-1][0])   # cabezal sobre la config. final
        return mt, gens

    def test_ejemplos_enunciado(self):
        self.comprobar("100#000000010000000#")
        self.comprobar("1110#01101001#")
        _, gens = self.comprobar("11#00010000#")
        self.assertEqual(gens, ["00010000", "00110000", "01110000", "11010000"])

    def test_k_cero(self):
        mt, gens = self.comprobar("0#10110010#")
        self.assertEqual(gens, ["10110010"])
        self.assertEqual(mt.cinta.contenido(), "0#10110010#")

    def test_fronteras_ciclicas(self):
        self.assertEqual(self.comprobar("1#00000001#")[1][1], "00000011")
        self.assertEqual(self.comprobar("1#10000000#")[1][1], "10000001")

    def test_aleatorios(self):
        rnd = random.Random(110)
        for _ in range(150):
            n, k = rnd.randint(8, 24), rnd.randint(0, 20)
            self.comprobar(codificar_entrada(k, "".join(rnd.choice("01") for _ in range(n))))

    def test_generacion_final_entre_los_primeros_separadores(self):
        mt, gens = self.comprobar("101#0001001101110110#")
        self.assertEqual(mt.cinta.contenido(), "000#" + gens[-1] + "#")
        self.assertEqual(self.comprobar("11#00010000#")[0].cinta.contenido(), "00#11010000#")
        self.assertNotIn("X", mt.cinta.contenido())
        self.assertNotIn("Y", mt.cinta.contenido())

    def test_no_borra_generaciones_al_cerrar_cada_ciclo(self):
        mt = crear_maquina()
        mt.reiniciar("11#00010000#")
        cintas = []
        while mt.paso():
            if mt.estado == Q0 and mt.ultima_clave[0] == "q_irInicio":
                cintas.append(mt.cinta.contenido())
        self.assertEqual(cintas, ["10#00010000#00110000#",
                                  "01#00010000#00110000#01110000#",
                                  "00#00010000#00110000#01110000#11010000#"])

    def test_la_regla_usa_todas_las_operaciones(self):
        # Sl y Sr crean estados auxiliares propios; la máquina debe pasar por ellos.
        mt = crear_maquina()
        mt.reiniciar("1#00010000#")
        visitados = set()
        while mt.paso():
            visitados.add(mt.estado)
        self.assertTrue(any(q.startswith("q_correr__poner_") for q in visitados))
        self.assertTrue(any("__llevar_" in q for q in visitados))

    def test_un_ciclo_por_generacion(self):
        mt = crear_maquina()
        mt.reiniciar("11#00010000#")
        ciclos = 0
        while mt.paso():
            if mt.estado == Q0 and mt.ultima_clave[0] == "q_irInicio":
                ciclos += 1
        self.assertEqual(ciclos, 3)


class TestEntrada(unittest.TestCase):
    def test_invalidas(self):
        for mala in ["", "#0101#", "10#0101", "10#01a1#", "1#0101#", "2#00000000#"]:
            with self.assertRaises(ValueError):
                validar_entrada(mala)

    def test_longitud_minima(self):
        self.assertEqual(validar_entrada("1#00000000#"), (1, "00000000"))
        for corta in ("1#0000000#", "11#000100#"):
            with self.assertRaises(ValueError):
                validar_entrada(corta)
            with self.assertRaises(ValueError):
                simular(corta)

    def test_caso_corto_falla_en_pruebas(self):
        r = ejecutar_caso(Caso(1, "1#0000000#"))
        self.assertFalse(r.ok)
        self.assertIn("N ≥ 8", r.mensaje)

    def test_caso_invalido_esperado(self):
        self.assertTrue(ejecutar_caso(Caso(1, "1#0000000#", "ERROR")).ok)
        r = ejecutar_caso(Caso(1, "1#00000000#", "ERROR"))   # válida: no debía aceptarse
        self.assertFalse(r.ok)

    def test_codificar(self):
        self.assertEqual(codificar_entrada(14, "01101001"), "1110#01101001#")


class TestArchivoCasos(unittest.TestCase):
    def test_casos_prueba_txt(self):
        ruta = os.path.join(os.path.dirname(__file__), "casos_prueba.txt")
        resultados = ejecutar_archivo(ruta)
        self.assertTrue(resultados)
        for r in resultados:
            self.assertTrue(r.ok, f"línea {r.caso.linea}: {r.mensaje}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
