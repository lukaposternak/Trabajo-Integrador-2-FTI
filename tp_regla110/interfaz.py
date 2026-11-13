"""
Interfaz gráfica (tkinter) del simulador de la Máquina de Turing - Regla 110.
"""
from __future__ import annotations

import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from maquina_turing import BLANCO
from pruebas import cargar_casos
from regla110_mt import (
    DELTA, DESCRIPCION, ESTADOS, N_MINIMO, Q0, codificar_entrada,
    crear_maquina, decodificar_cinta, fin_de_ciclo, regla110_referencia,
    tabla_transiciones, validar_entrada,
)

# ------------------------------------------------------------------ estilo
FUENTE_MONO = ("Consolas", 11)
FUENTE_CELDA = ("Consolas", 13, "bold")
CELDA = 34                       # ancho en px de una celda de la cinta
ORIGEN = -3                      # primera posición dibujada de la cinta

COLOR_FONDO = {"0": "#ffffff", "1": "#1e293b", "X": "#fde68a", "Y": "#b45309",
               "#": "#cbd5e1", BLANCO: "#f1f5f9"}
COLOR_TEXTO = {"0": "#0f172a", "1": "#ffffff", "X": "#0f172a", "Y": "#ffffff",
               "#": "#0f172a", BLANCO: "#94a3b8"}
COLOR_CABEZAL = "#dc2626"
COLOR_VIVA = "#1e293b"
COLOR_MUERTA = "#ffffff"

EJEMPLOS_POR_DEFECTO = {
    "Enunciado 1: K=4, N=15": "100#000000010000000#",
    "Enunciado 2: K=14, N=8": "1110#01101001#",
    "Ejemplo consigna (N=8, K=3)": "11#00010000#",
    "Frontera cíclica (K=1)": "1#10000001#",
    "Celda única, N=32, K=20": "10100#00000000000000000000000000000001#",
    "K = 0": "0#10110010#",
}
RUTA_CASOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "casos_prueba.txt")


def cargar_ejemplos(ruta: str = RUTA_CASOS) -> dict[str, str]:
    """Ejemplos del menú = los casos de casos_prueba.txt (nombre → cinta).
    Las entradas inválidas (esperada ERROR) se marcan para mostrar el rechazo."""
    try:
        casos = cargar_casos(ruta)
    except OSError:
        return dict(EJEMPLOS_POR_DEFECTO)
    ejemplos = {}
    for i, caso in enumerate(casos, start=1):
        nombre = caso.descripcion or caso.entrada
        if caso.espera_error:
            nombre = f"[inválida] {nombre}"
        ejemplos[f"{i:02d}. {nombre}"] = caso.entrada
    return ejemplos or dict(EJEMPLOS_POR_DEFECTO)


EJEMPLOS = cargar_ejemplos()


class Aplicacion(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Máquina de Turing · Autómata celular Regla 110")
        self.geometry("1280x860")
        self.minsize(1000, 700)

        self.mt = crear_maquina()
        self.entrada_cargada = ""
        self.config_inicial = ""
        self.k_inicial = 0
        self.historial: list[str] = []      # generaciones cerradas, en orden (la etapa final las reordena en la cinta)
        self.ejecutando = False
        self._after_id = None
        self._cache_celdas: dict[int, tuple[int, int, str]] = {}
        self._items_cabezal: tuple[int, int] | None = None
        self._gens_dibujadas = -1
        self._iid_transicion: dict[tuple[str, str], str] = {}
        self._iid_resaltado: str | None = None

        self._estilos()
        self._construir()
        self.cargar_en_maquina(next(iter(EJEMPLOS.values())))

    # ============================================================== UI
    def _estilos(self) -> None:
        st = ttk.Style(self)
        if "clam" in st.theme_names():
            st.theme_use("clam")
        st.configure("Titulo.TLabel", font=("Segoe UI", 10, "bold"))
        st.configure("Valor.TLabel", font=("Consolas", 11, "bold"), foreground="#1d4ed8")
        st.configure("Ok.TLabel", foreground="#15803d", font=("Segoe UI", 10, "bold"))
        st.configure("Error.TLabel", foreground="#b91c1c", font=("Segoe UI", 10, "bold"))
        st.configure("Treeview", font=("Consolas", 10), rowheight=20)
        st.map("Treeview", background=[("selected", "#dc2626")], foreground=[("selected", "#ffffff")])

    def _construir(self) -> None:
        raiz = ttk.Frame(self, padding=8)
        raiz.pack(fill="both", expand=True)
        self._construir_entrada(raiz)
        self._construir_controles(raiz)
        self._construir_estado(raiz)
        self._construir_cinta(raiz)
        self._construir_pestanias(raiz)
        self.bind("<space>", lambda e: self._atajo(self.paso))
        self.bind("<Return>", lambda e: self._atajo(self.alternar_ejecucion))

    def _atajo(self, accion):
        # No interceptar teclas mientras se escribe en un campo de texto.
        if isinstance(self.focus_get(), (tk.Entry, ttk.Entry, ttk.Spinbox, tk.Text)):
            return
        accion()

    # ------------------------------------------------------------ entrada
    def _construir_entrada(self, padre) -> None:
        caja = ttk.LabelFrame(padre, text="Entrada", padding=6)
        caja.pack(fill="x")

        ttk.Label(caja, text="Cinta (K binario # configuración #):").grid(row=0, column=0, sticky="w")
        self.var_cinta = tk.StringVar()
        e = ttk.Entry(caja, textvariable=self.var_cinta, font=FUENTE_MONO, width=58)
        e.grid(row=0, column=1, columnspan=3, sticky="we", padx=4)
        e.bind("<Return>", lambda ev: self.cargar_en_maquina(self.var_cinta.get()))
        ttk.Button(caja, text="Cargar en la MT",
                   command=lambda: self.cargar_en_maquina(self.var_cinta.get())).grid(row=0, column=4, padx=4)

        ttk.Label(caja, text="Ejemplos:").grid(row=0, column=5, sticky="e", padx=(12, 2))
        self.var_ejemplo = tk.StringVar()
        cb = ttk.Combobox(caja, textvariable=self.var_ejemplo, values=list(EJEMPLOS),
                          state="readonly", width=40, height=20)
        cb.grid(row=0, column=6, sticky="w")
        cb.bind("<<ComboboxSelected>>",
                lambda ev: self.cargar_en_maquina(EJEMPLOS[self.var_ejemplo.get()]))

        ttk.Label(caja, text="Generador →  K (decimal):").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.var_k = tk.StringVar(value="4")
        ttk.Spinbox(caja, from_=0, to=9999, textvariable=self.var_k, width=7).grid(
            row=1, column=1, sticky="w", pady=(6, 0))
        ttk.Label(caja, text="Configuración inicial:").grid(row=1, column=2, sticky="e", pady=(6, 0))
        self.var_config = tk.StringVar(value="000000010000000")
        ttk.Entry(caja, textvariable=self.var_config, font=FUENTE_MONO, width=34).grid(
            row=1, column=3, sticky="we", padx=4, pady=(6, 0))
        ttk.Button(caja, text="Generar cinta", command=self.generar_cinta).grid(
            row=1, column=4, padx=4, pady=(6, 0))

        ttk.Label(caja, text="N aleatoria:").grid(row=1, column=5, sticky="e", padx=(12, 2), pady=(6, 0))
        sub = ttk.Frame(caja)
        sub.grid(row=1, column=6, sticky="w", pady=(6, 0))
        self.var_n_azar = tk.StringVar(value="16")
        ttk.Spinbox(sub, from_=N_MINIMO, to=200, textvariable=self.var_n_azar, width=5).pack(side="left")
        ttk.Button(sub, text="Aleatoria", command=self.configuracion_aleatoria).pack(side="left", padx=4)
        caja.columnconfigure(3, weight=1)

    # ----------------------------------------------------------- controles
    def _construir_controles(self, padre) -> None:
        caja = ttk.Frame(padre, padding=(0, 6))
        caja.pack(fill="x")
        ttk.Button(caja, text="⏭ Paso", command=self.paso).pack(side="left")
        self.btn_ejecutar = ttk.Button(caja, text="▶ Ejecutar", command=self.alternar_ejecucion)
        self.btn_ejecutar.pack(side="left", padx=4)
        ttk.Button(caja, text="⏩ Siguiente generación", command=self.siguiente_generacion).pack(side="left")
        ttk.Button(caja, text="⏹ Ejecutar hasta el final", command=self.hasta_el_final).pack(side="left", padx=4)
        ttk.Button(caja, text="↺ Reiniciar", command=self.reiniciar).pack(side="left")

        ttk.Label(caja, text="Velocidad:").pack(side="left", padx=(20, 4))
        self.var_vel = tk.DoubleVar(value=40)
        ttk.Scale(caja, from_=0, to=100, variable=self.var_vel, length=220,
                  command=lambda v: self._mostrar_velocidad()).pack(side="left")
        self.lbl_vel = ttk.Label(caja, width=16)
        self.lbl_vel.pack(side="left", padx=4)
        self._mostrar_velocidad()

    def _pasos_por_segundo(self) -> float:
        return 10 ** (self.var_vel.get() / 25)        # 1 … 10 000 pasos/s

    def _mostrar_velocidad(self) -> None:
        self.lbl_vel.config(text=f"{self._pasos_por_segundo():,.0f} pasos/s".replace(",", "."))

    # -------------------------------------------------------------- estado
    def _construir_estado(self, padre) -> None:
        caja = ttk.LabelFrame(padre, text="Estado de la máquina", padding=6)
        caja.pack(fill="x")
        self.lbls = {}
        campos = [("estado", "Estado"), ("pasos", "Pasos"), ("cabezal", "Cabezal"),
                  ("lee", "Lee"), ("k", "K restante"), ("gen", "Generaciones")]
        for i, (clave, texto) in enumerate(campos):
            ttk.Label(caja, text=texto + ":", style="Titulo.TLabel").grid(row=0, column=2 * i, sticky="e", padx=(10, 2))
            lbl = ttk.Label(caja, text="-", style="Valor.TLabel")
            lbl.grid(row=0, column=2 * i + 1, sticky="w")
            self.lbls[clave] = lbl
        ttk.Label(caja, text="Última transición:", style="Titulo.TLabel").grid(row=1, column=0, sticky="e", padx=(10, 2), pady=(4, 0))
        self.lbl_trans = ttk.Label(caja, text="-", font=FUENTE_MONO)
        self.lbl_trans.grid(row=1, column=1, columnspan=11, sticky="w", pady=(4, 0))
        ttk.Label(caja, text="Descripción:", style="Titulo.TLabel").grid(row=2, column=0, sticky="ne", padx=(10, 2))
        self.lbl_desc = ttk.Label(caja, text="-", wraplength=1050, justify="left")
        self.lbl_desc.grid(row=2, column=1, columnspan=11, sticky="w")
        self.lbl_resultado = ttk.Label(caja, text="")
        self.lbl_resultado.grid(row=3, column=0, columnspan=12, sticky="w", padx=(10, 0), pady=(4, 0))

    # --------------------------------------------------------------- cinta
    def _construir_cinta(self, padre) -> None:
        caja = ttk.LabelFrame(padre, text="Cinta", padding=4)
        caja.pack(fill="x", pady=(6, 0))
        self.canvas_cinta = tk.Canvas(caja, height=86, bg="#f8fafc", highlightthickness=0)
        sb = ttk.Scrollbar(caja, orient="horizontal", command=self.canvas_cinta.xview)
        self.canvas_cinta.configure(xscrollcommand=sb.set)
        self.canvas_cinta.pack(fill="x")
        sb.pack(fill="x")
        leyenda = ttk.Frame(caja)
        leyenda.pack(fill="x", pady=(2, 0))
        for s, txt in [("0", "0"), ("1", "1"), ("X", "X = 0 procesado"), ("Y", "Y = 1 procesado"),
                       ("#", "# separador"), (BLANCO, "_ blanco")]:
            tk.Label(leyenda, text="  ", bg=COLOR_FONDO[s], relief="solid", bd=1).pack(side="left", padx=(8, 2))
            ttk.Label(leyenda, text=txt).pack(side="left")
        self.var_seguir = tk.BooleanVar(value=True)
        ttk.Checkbutton(leyenda, text="Seguir al cabezal", variable=self.var_seguir).pack(side="right")

    # ----------------------------------------------------------- pestañas
    def _construir_pestanias(self, padre) -> None:
        self.nb = ttk.Notebook(padre)
        self.nb.pack(fill="both", expand=True, pady=(6, 0))
        self._tab_evolucion()
        self._tab_tabla()
        self._tab_generaciones()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.refrescar(completo=True))

    def _tab_evolucion(self) -> None:
        f = ttk.Frame(self.nb, padding=4)
        self.nb.add(f, text="Evolución (espacio-tiempo)")
        self.canvas_evo = tk.Canvas(f, bg="#ffffff", highlightthickness=0)
        sy = ttk.Scrollbar(f, orient="vertical", command=self.canvas_evo.yview)
        sx = ttk.Scrollbar(f, orient="horizontal", command=self.canvas_evo.xview)
        self.canvas_evo.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.canvas_evo.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        f.rowconfigure(0, weight=1)
        f.columnconfigure(0, weight=1)
        self.canvas_evo.bind("<Configure>", lambda e: self._dibujar_evolucion(forzar=True))

    def _tab_tabla(self) -> None:
        f = ttk.Frame(self.nb, padding=4)
        self.nb.add(f, text="Tabla de transiciones δ")
        filas = tabla_transiciones()
        info = (f"|Q| = {len(ESTADOS)} estados   ·   |δ| = {len(DELTA)} transiciones   ·   "
                f"Γ = {{0, 1, X, Y, #, _}}   ·   q0 = {Q0}   ·   F = {{q_fin}}")
        ttk.Label(f, text=info, font=FUENTE_MONO).pack(anchor="w", pady=(0, 4))

        cuerpo = ttk.Frame(f)
        cuerpo.pack(fill="both", expand=True)
        cols = ("estado", "lee", "escribe", "mueve", "siguiente")
        self.tree_delta = ttk.Treeview(cuerpo, columns=cols, show="headings", selectmode="browse")
        for c, t, w in zip(cols, ("Estado actual", "Lee", "Escribe", "Mueve", "Estado siguiente"),
                           (200, 60, 70, 60, 200)):
            self.tree_delta.heading(c, text=t)
            self.tree_delta.column(c, width=w, anchor="center" if w < 100 else "w", stretch=w >= 100)
        self.tree_delta.tag_configure("par", background="#f1f5f9")
        estado_previo, grupo = None, 0
        for fila in filas:
            if fila[0] != estado_previo:
                grupo += 1
                estado_previo = fila[0]
            iid = self.tree_delta.insert("", "end", values=fila, tags=("par",) if grupo % 2 else ())
            self._iid_transicion[(fila[0], fila[1])] = iid
        sb = ttk.Scrollbar(cuerpo, orient="vertical", command=self.tree_delta.yview)
        self.tree_delta.configure(yscrollcommand=sb.set)
        self.tree_delta.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

        # Panel lateral: descripción del estado seleccionado
        lateral = ttk.Frame(cuerpo, padding=(10, 0))
        lateral.pack(side="left", fill="both")
        ttk.Label(lateral, text="Estados", style="Titulo.TLabel").pack(anchor="w")
        self.lista_estados = tk.Listbox(lateral, font=("Consolas", 10), width=22, height=18, exportselection=False)
        for q in ESTADOS:
            self.lista_estados.insert("end", q)
        self.lista_estados.pack(anchor="w", fill="y", expand=True)
        self.lbl_desc_estado = ttk.Label(lateral, text="", wraplength=260, justify="left")
        self.lbl_desc_estado.pack(anchor="w", pady=4)
        self.lista_estados.bind("<<ListboxSelect>>", self._seleccionar_estado)
        self.var_resaltar = tk.BooleanVar(value=True)
        ttk.Checkbutton(lateral, text="Resaltar la transición aplicada",
                        variable=self.var_resaltar).pack(anchor="w")
        ttk.Button(lateral, text="Exportar tabla (.csv)", command=self.exportar_tabla).pack(anchor="w", pady=4)

    def _tab_generaciones(self) -> None:
        f = ttk.Frame(self.nb, padding=4)
        self.nb.add(f, text="Generaciones (texto)")
        self.txt_gens = tk.Text(f, font=FUENTE_MONO, wrap="none", height=10)
        sy = ttk.Scrollbar(f, orient="vertical", command=self.txt_gens.yview)
        self.txt_gens.configure(yscrollcommand=sy.set)
        self.txt_gens.pack(side="left", fill="both", expand=True)
        sy.pack(side="left", fill="y")
        self.txt_gens.tag_configure("ok", foreground="#15803d")
        self.txt_gens.tag_configure("error", foreground="#b91c1c")

    # ========================================================= acciones
    def generar_cinta(self) -> None:
        try:
            k = int(self.var_k.get())
            cinta = codificar_entrada(k, self.var_config.get().strip())
        except ValueError as e:
            messagebox.showerror("Entrada inválida", str(e))
            return
        self.cargar_en_maquina(cinta)

    def configuracion_aleatoria(self) -> None:
        try:
            n = max(N_MINIMO, int(self.var_n_azar.get()))
        except ValueError:
            n = 16
        self.var_config.set("".join(random.choice("01") for _ in range(n)))
        self.generar_cinta()

    def cargar_en_maquina(self, cinta: str) -> None:
        cinta = cinta.strip().replace(" ", "")
        try:
            k, config = validar_entrada(cinta)
        except ValueError as e:
            # Se deja la cinta rechazada a la vista; la máquina conserva la anterior.
            self.var_cinta.set(cinta)
            self.lbl_resultado.config(text=f"✘ Entrada rechazada: {e}", style="Error.TLabel")
            messagebox.showerror("Entrada inválida", str(e))
            return
        self.pausar()
        self.entrada_cargada, self.k_inicial, self.config_inicial = cinta, k, config
        self.var_cinta.set(cinta)
        self.var_k.set(str(k))
        self.var_config.set(config)
        self.reiniciar()

    def reiniciar(self) -> None:
        self.pausar()
        self.mt.reiniciar(self.entrada_cargada)
        self.historial = [self.config_inicial] if self.config_inicial else []
        self.canvas_cinta.delete("all")
        self._cache_celdas.clear()
        self._items_cabezal = None
        self._gens_dibujadas = -1
        self.refrescar(completo=True)

    def _paso_mt(self) -> bool:
        """Aplica una transición y registra la generación si se cerró un ciclo."""
        avanzo = self.mt.paso()
        if avanzo and fin_de_ciclo(self.mt):
            self.historial.append(decodificar_cinta(self.mt.cinta.contenido())[1])
        return avanzo

    def paso(self) -> None:
        self.pausar()
        self._paso_mt()
        self.refrescar()

    def siguiente_generacion(self) -> None:
        """Ejecuta un ciclo completo de la MT: hasta la transición q_irInicio → q_verificarK
        (nueva generación cerrada y vuelta al inicio) o hasta que se detenga."""
        self.pausar()
        while self._paso_mt():
            if fin_de_ciclo(self.mt):
                break
        self.refrescar()

    def alternar_ejecucion(self) -> None:
        if self.ejecutando:
            self.pausar()
        elif not self.mt.detenida:
            self.ejecutando = True
            self.btn_ejecutar.config(text="⏸ Pausar")
            self._tick()

    def pausar(self) -> None:
        self.ejecutando = False
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.btn_ejecutar.config(text="▶ Ejecutar")

    def _tick(self) -> None:
        if not self.ejecutando:
            return
        sps = self._pasos_por_segundo()
        if sps <= 30:
            n, demora = 1, int(1000 / sps)
        else:
            n, demora = int(sps * 0.033), 33
        for _ in range(n):
            if not self._paso_mt():
                break
        self.refrescar()
        if self.mt.detenida:
            self.pausar()
            return
        self._after_id = self.after(demora, self._tick)

    def hasta_el_final(self) -> None:
        """Ejecuta sin animación, en bloques para no congelar la ventana."""
        self.pausar()
        self.ejecutando = True
        self.btn_ejecutar.config(text="⏸ Pausar")

        def bloque():
            if not self.ejecutando:
                return
            for _ in range(200_000):
                if not self._paso_mt():
                    break
            self.refrescar()
            if self.mt.detenida:
                self.pausar()
            else:
                self._after_id = self.after(1, bloque)
        bloque()

    # ===================================================== refresco
    def _generacion_en_curso(self, actual: str, nueva: str) -> str:
        """Generación t+1 todavía no registrada; en la etapa final ya están todas registradas."""
        if not self.historial or len(self.historial) > self.k_inicial:
            return ""
        return nueva or (actual if actual != self.historial[-1] else "")

    def refrescar(self, completo: bool = False) -> None:
        mt = self.mt
        contenido = mt.cinta.contenido()
        k_rest, actual, nueva = decodificar_cinta(contenido)
        gens, parcial = self.historial, self._generacion_en_curso(actual, nueva)

        self.lbls["estado"].config(text=mt.estado)
        self.lbls["pasos"].config(text=f"{mt.pasos:,}".replace(",", "."))
        self.lbls["cabezal"].config(text=str(mt.cabezal))
        self.lbls["lee"].config(text=mt.simbolo_actual)
        self.lbls["k"].config(text=f"{k_rest}  ({contenido.split('#')[0] or '-'})")
        self.lbls["gen"].config(text=f"{max(len(gens) - 1, 0)} / {self.k_inicial}")
        self.lbl_desc.config(text=DESCRIPCION.get(mt.estado, ""))
        if mt.ultima_clave:
            q, s = mt.ultima_clave
            tr = DELTA[mt.ultima_clave]
            self.lbl_trans.config(text=f"δ({q}, {s}) = ({tr.siguiente}, {tr.escribe}, {tr.mueve})")
        else:
            self.lbl_trans.config(text="-")

        self._dibujar_cinta()
        pestania = self.nb.index(self.nb.select())
        if pestania == 0:
            self._dibujar_evolucion(gens=gens, parcial=parcial)
        elif pestania == 1:
            self._resaltar_transicion()
        elif pestania == 2:
            self._escribir_generaciones(gens, parcial)
        self._mostrar_resultado(gens)

    # ---------------------------------------------------------- cinta
    def _dibujar_cinta(self) -> None:
        c = self.canvas_cinta
        cinta = self.mt.cinta
        y0, y1 = 30, 66
        desde = min(ORIGEN, cinta.min_pos - 2)
        hasta = max(cinta.max_pos, self.mt.cabezal) + 4
        for pos in range(desde, hasta):
            s = cinta.leer(pos)
            item = self._cache_celdas.get(pos)
            if item is None:
                x = (pos - ORIGEN) * CELDA
                r = c.create_rectangle(x + 1, y0, x + CELDA - 1, y1, fill=COLOR_FONDO[s], outline="#64748b")
                t = c.create_text(x + CELDA / 2, (y0 + y1) / 2, text=s, font=FUENTE_CELDA, fill=COLOR_TEXTO[s])
                c.create_text(x + CELDA / 2, y1 + 10, text=str(pos), font=("Consolas", 7), fill="#94a3b8")
                self._cache_celdas[pos] = (r, t, s)
            elif item[2] != s:
                r, t, _ = item
                c.itemconfigure(r, fill=COLOR_FONDO[s])
                c.itemconfigure(t, text=s, fill=COLOR_TEXTO[s])
                self._cache_celdas[pos] = (r, t, s)

        # Cabezal: triángulo + recuadro rojo + nombre del estado
        x = (self.mt.cabezal - ORIGEN) * CELDA
        if self._items_cabezal:
            for it in self._items_cabezal:
                c.delete(it)
        tri = c.create_polygon(x + CELDA / 2 - 8, 6, x + CELDA / 2 + 8, 6, x + CELDA / 2, 24,
                               fill=COLOR_CABEZAL, outline="")
        caja = c.create_rectangle(x, y0 - 2, x + CELDA, y1 + 2, outline=COLOR_CABEZAL, width=3)
        etiqueta = c.create_text(x + CELDA / 2 + 14, 13, text=self.mt.estado, anchor="w",
                                 font=("Consolas", 9, "bold"), fill=COLOR_CABEZAL)
        self._items_cabezal = (tri, caja, etiqueta)

        ancho_total = (hasta - ORIGEN + 8) * CELDA
        c.configure(scrollregion=(0, 0, ancho_total, 86))
        if self.var_seguir.get():
            visible = c.winfo_width() or 800
            izq, der = c.canvasx(0), c.canvasx(visible)
            if not (izq + CELDA * 2 <= x <= der - CELDA * 3):
                c.xview_moveto(max(0.0, (x - visible / 2) / ancho_total))

    # ------------------------------------------------------ evolución
    def _dibujar_evolucion(self, gens=None, parcial="", forzar=False) -> None:
        if gens is None:
            _, actual, nueva = decodificar_cinta(self.mt.cinta.contenido())
            gens, parcial = self.historial, self._generacion_en_curso(actual, nueva)
        clave = (len(gens), len(parcial))
        if not forzar and clave == self._gens_dibujadas:
            return
        self._gens_dibujadas = clave
        c = self.canvas_evo
        c.delete("all")
        n = len(self.config_inicial) or 1
        filas = self.k_inicial + 1
        margen_izq, margen_sup = 70, 24
        ancho = max(c.winfo_width() - margen_izq - 20, 200)
        alto = max(c.winfo_height() - margen_sup - 10, 150)
        lado = max(6, min(26, ancho // n, max(alto // filas, 10)))

        for j in range(n):
            if n <= 40 or j % 5 == 0:
                c.create_text(margen_izq + j * lado + lado / 2, 10, text=str(j), font=("Consolas", 7), fill="#64748b")
        refs = regla110_referencia(self.config_inicial, len(gens) - 1) if gens else []
        for i, g in enumerate(gens):
            y = margen_sup + i * lado
            ok = i < len(refs) and refs[i] == g
            c.create_text(margen_izq - 8, y + lado / 2, anchor="e", font=("Consolas", 9),
                          text=f"G{i} {'✔' if ok else '✘'}", fill="#15803d" if ok else "#b91c1c")
            for j, ch in enumerate(g):
                x = margen_izq + j * lado
                c.create_rectangle(x, y, x + lado, y + lado, outline="#cbd5e1",
                                   fill=COLOR_VIVA if ch == "1" else COLOR_MUERTA)
        # Generación en construcción (fila parcial en azul)
        if parcial and not self.mt.detenida:
            y = margen_sup + len(gens) * lado
            c.create_text(margen_izq - 8, y + lado / 2, anchor="e", font=("Consolas", 9),
                          text=f"G{len(gens)} …", fill="#2563eb")
            for j, ch in enumerate(parcial):
                x = margen_izq + j * lado
                c.create_rectangle(x, y, x + lado, y + lado, outline="#93c5fd",
                                   fill="#2563eb" if ch == "1" else "#dbeafe")
        c.configure(scrollregion=(0, 0, margen_izq + n * lado + 20, margen_sup + (filas + 1) * lado))

    # --------------------------------------------------------- tabla δ
    def _resaltar_transicion(self) -> None:
        if not self.var_resaltar.get():
            return
        iid = self._iid_transicion.get(self.mt.ultima_clave) if self.mt.ultima_clave else None
        if iid == self._iid_resaltado:
            return
        if iid:
            self.tree_delta.selection_set(iid)
            self.tree_delta.see(iid)
        else:
            self.tree_delta.selection_remove(self.tree_delta.selection())
        self._iid_resaltado = iid

    def _seleccionar_estado(self, _evento=None) -> None:
        sel = self.lista_estados.curselection()
        if not sel:
            return
        q = ESTADOS[sel[0]]
        self.lbl_desc_estado.config(text=f"{q}:\n{DESCRIPCION[q]}")
        for s in ("0", "1", "X", "Y", "#", BLANCO):
            iid = self._iid_transicion.get((q, s))
            if iid:
                self.tree_delta.see(iid)
                self.tree_delta.selection_set(iid)
                break

    def exportar_tabla(self) -> None:
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="tabla_transiciones.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not ruta:
            return
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("estado;lee;escribe;mueve;siguiente\n")
            for fila in tabla_transiciones():
                f.write(";".join(fila) + "\n")
        messagebox.showinfo("Exportar", f"Tabla exportada a:\n{ruta}")

    # --------------------------------------------------- generaciones
    def _escribir_generaciones(self, gens, parcial) -> None:
        t = self.txt_gens
        t.delete("1.0", "end")
        t.insert("end", f"Entrada: {self.entrada_cargada}   (K = {self.k_inicial}, N = {len(self.config_inicial)})\n\n")
        refs = regla110_referencia(self.config_inicial, max(len(gens) - 1, 0)) if gens else []
        for i, g in enumerate(gens):
            ok = i < len(refs) and refs[i] == g
            t.insert("end", f"Gen {i:>3}: {' '.join(g)}  ")
            t.insert("end", "✔\n" if ok else f"✘ (referencia: {refs[i] if i < len(refs) else '?'})\n",
                     "ok" if ok else "error")
        if parcial and not self.mt.detenida:
            t.insert("end", f"Gen {len(gens):>3}: {' '.join(parcial)}  … (en construcción)\n")
        t.insert("end", f"\nCinta: {self.mt.cinta.contenido()}\n")
        if self.mt.detenida:
            t.insert("end", f"\nMáquina detenida en {self.mt.estado} ({self.mt.motivo}) "
                            f"tras {self.mt.pasos} pasos.\n")

    def _mostrar_resultado(self, gens) -> None:
        if not self.mt.detenida:
            self.lbl_resultado.config(text="")
            return
        ref = regla110_referencia(self.config_inicial, self.k_inicial)
        if self.mt.aceptada and gens == ref:
            self.lbl_resultado.config(text=f"✔ Detenida en q_fin · {len(gens) - 1} generaciones "
                                           f"coinciden con la referencia", style="Ok.TLabel")
        else:
            self.lbl_resultado.config(text=f"✘ {self.mt.motivo} · resultado no coincide", style="Error.TLabel")


def main() -> None:
    Aplicacion().mainloop()


if __name__ == "__main__":
    main()
