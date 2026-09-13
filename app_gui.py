import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from import_os import DecaGenerator, publicar_en_nas, REPOSITORY_DIR

class DecaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador DeCA - Boutique Legal Transporte")
        self.root.geometry("750x700")

        # Contenedor con scroll para asegurar visibilidad en cualquier resolución
        canvas = tk.Canvas(root)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.agencias_entries = []
        self._build_ui()

    def _build_ui(self):
        pad = {'padx': 10, 'pady': 5}

        # Header
        ttk.Label(self.scrollable_frame, text="DOCUMENTO ELECTRÓNICO DE CONTROL (DeCA)", font=('Helvetica', 14, 'bold')).pack(**pad)

        # 1. Identificación
        f_id = ttk.LabelFrame(self.scrollable_frame, text="1. Identificación del Envío")
        f_id.pack(fill="x", expand=True, **pad)
        
        ttk.Label(f_id, text="Número Correlativo:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_num = ttk.Entry(f_id)
        self.ent_num.insert(0, "1")
        self.ent_num.grid(row=0, column=1, sticky="ew", **pad)
import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from deca_generator import DecaGenerator, publicar_en_nas, REPOSITORY_DIR

class DecaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generador DeCA - Boutique Legal Transporte")
        self.root.geometry("750x700")

        canvas = tk.Canvas(root)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.agencias_entries = []
        self._build_ui()

    def _build_ui(self):
        pad = {'padx': 10, 'pady': 5}

        # Header
        ttk.Label(self.scrollable_frame, text="DOCUMENTO ELECTRÓNICO DE CONTROL (DeCA)", font=('Helvetica', 14, 'bold')).pack(**pad)

        # 1. Identificación
        f_id = ttk.LabelFrame(self.scrollable_frame, text="1. Identificación del Envío")
        f_id.pack(fill="x", expand=True, **pad)
        
        ttk.Label(f_id, text="Número Correlativo:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_num = ttk.Entry(f_id)
        self.ent_num.insert(0, "1")
        self.ent_num.grid(row=0, column=1, sticky="ew", **pad)

        # 2. Cargador
        f_carg = ttk.LabelFrame(self.scrollable_frame, text="2. Cargador Contractual / Remitente")
        f_carg.pack(fill="x", expand=True, **pad)

        ttk.Label(f_carg, text="Nombre / Razón:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_carg_nom = ttk.Entry(f_carg, width=50)
        self.ent_carg_nom.insert(0, "LOGÍSTICA ALIMENTARIA S.A.")
        self.ent_carg_nom.grid(row=0, column=1, **pad)

        ttk.Label(f_carg, text="NIF / CIF:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_carg_nif = ttk.Entry(f_carg, width=50)
        self.ent_carg_nif.insert(0, "A12345678")
        self.ent_carg_nif.grid(row=1, column=1, **pad)

        ttk.Label(f_carg, text="Domicilio:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_carg_dom = ttk.Entry(f_carg, width=50)
        self.ent_carg_dom.insert(0, "Av. de la Industria 45, Madrid")
        self.ent_carg_dom.grid(row=2, column=1, **pad)

        # 3. Transportista
        f_trans = ttk.LabelFrame(self.scrollable_frame, text="3. Transportista Efectivo")
        f_trans.pack(fill="x", expand=True, **pad)

        ttk.Label(f_trans, text="Nombre / Razón:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_trans_nom = ttk.Entry(f_trans, width=50)
        self.ent_trans_nom.insert(0, "TRANSPORTES RÁPIDOS S.L.")
        self.ent_trans_nom.grid(row=0, column=1, **pad)

        ttk.Label(f_trans, text="NIF / CIF:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_trans_nif = ttk.Entry(f_trans, width=50)
        self.ent_trans_nif.insert(0, "B98765432")
        self.ent_trans_nif.grid(row=1, column=1, **pad)

        ttk.Label(f_trans, text="Domicilio:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_trans_dom = ttk.Entry(f_trans, width=50)
        self.ent_trans_dom.insert(0, "Calle Transporte 12, Valencia")
        self.ent_trans_dom.grid(row=2, column=1, **pad)

        # 4. Subcontratación
        self.f_sub = ttk.LabelFrame(self.scrollable_frame, text="4. Cadena de Subcontratación (Agencias Intermediarias)")
        self.f_sub.pack(fill="x", expand=True, **pad)

        btn_add = ttk.Button(self.f_sub, text="+ Añadir Intermediario / Agencia", command=self._add_agencia_field)
        btn_add.pack(anchor="w", **pad)

        # 5. Ruta y Mercancía
        f_ruta = ttk.LabelFrame(self.scrollable_frame, text="5. Datos del Viaje y Mercancía")
        f_ruta.pack(fill="x", expand=True, **pad)

        ttk.Label(f_ruta, text="Origen:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_origen = ttk.Entry(f_ruta, width=40)
        self.ent_origen.insert(0, "Mercamadrid, Nave 4, Madrid")
        self.ent_origen.grid(row=0, column=1, **pad)

        ttk.Label(f_ruta, text="Destino:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_destino = ttk.Entry(f_ruta, width=40)
        self.ent_destino.insert(0, "Puerto de Valencia, Muelle 3")
        self.ent_destino.grid(row=1, column=1, **pad)

        ttk.Label(f_ruta, text="Mercancía:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_merc = ttk.Entry(f_ruta, width=40)
        self.ent_merc.insert(0, "Productos refrigerados")
        self.ent_merc.grid(row=2, column=1, **pad)

        ttk.Label(f_ruta, text="Peso (kg):").grid(row=3, column=0, sticky="w", **pad)
        self.ent_peso = ttk.Entry(f_ruta, width=40)
        self.ent_peso.insert(0, "18500")
        self.ent_peso.grid(row=3, column=1, **pad)

        ttk.Label(f_ruta, text="Matrícula Tractora:").grid(row=4, column=0, sticky="w", **pad)
        self.ent_mat = ttk.Entry(f_ruta, width=40)
        self.ent_mat.insert(0, "1234-BBB")
        self.ent_mat.grid(row=4, column=1, **pad)

        ttk.Label(f_ruta, text="Matrícula Remolque:").grid(row=5, column=0, sticky="w", **pad)
        self.ent_rem = ttk.Entry(f_ruta, width=40)
        self.ent_rem.insert(0, "R-5678-BBB")
        self.ent_rem.grid(row=5, column=1, **pad)

        ttk.Label(f_ruta, text="Observaciones:").grid(row=6, column=0, sticky="w", **pad)
        self.ent_obs = ttk.Entry(f_ruta, width=40)
        self.ent_obs.insert(0, "Mantener temperatura a +4°C")
        self.ent_obs.grid(row=6, column=1, **pad)

        # Botón de Generar y Publicar
        btn_gen = ttk.Button(self.scrollable_frame, text="GENERAR Y PUBLICAR DeCA EN EL NAS", command=self._procesar_deca)
        btn_gen.pack(fill="x", **pad)

    def _add_agencia_field(self):
        idx = len(self.agencias_entries) + 1
        frame_item = ttk.Frame(self.f_sub)
        frame_item.pack(fill="x", expand=True, padx=5, pady=2)

        ttk.Label(frame_item, text=f"Agencia {idx} Nombre:").grid(row=0, column=0, sticky="w")
        e_nom = ttk.Entry(frame_item, width=25)
        e_nom.grid(row=0, column=1, padx=2)

        ttk.Label(frame_item, text="NIF:").grid(row=0, column=2, sticky="w")
        e_nif = ttk.Entry(frame_item, width=15)
        e_nif.grid(row=0, column=3, padx=2)

        self.agencias_entries.append((e_nom, e_nif))

    def _procesar_deca(self):
        try:
            num_val = int(self.ent_num.get().strip())
            deca_id = f"DECA-{datetime.datetime.now().year}-{num_val:05d}"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            agencias = []
            for nom_e, nif_e in self.agencias_entries:
                nom = nom_e.get().strip()
                nif = nif_e.get().strip()
                if nom:
                    agencias.append(f"{nom} (NIF: {nif})")

            cadena_sub = ""
            if agencias:
                cadena_sub = " | Subcontratación: " + " -> ".join(agencias)

            data = {
                "creation_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "cargador_nombre": self.ent_carg_nom.get(),
                "cargador_nif": self.ent_carg_nif.get(),
                "cargador_domicilio": self.ent_carg_dom.get(),
                "transportista_nombre": self.ent_trans_nom.get(),
                "transportista_nif": self.ent_trans_nif.get(),
                "transportista_domicilio": self.ent_trans_dom.get(),
                "origen_lugar": self.ent_origen.get(),
                "fecha_carga": now_str,
                "destino_lugar": self.ent_destino.get(),
                "fecha_descarga": "-",
                "mercancia_descripcion": self.ent_merc.get(),
                "peso_kg": self.ent_peso.get(),
                "bultos": "-",
                "matricula": self.ent_mat.get(),
                "remolque": self.ent_rem.get(),
                "observaciones": f"{self.ent_obs.get()}{cadena_sub}"
            }

            output_pdf = os.path.join(REPOSITORY_DIR, f"{deca_id}.pdf")
            
            DecaGenerator.generate_deca_pdf(deca_id, data, output_pdf)
            publicar_en_nas(output_pdf)

            messagebox.showinfo("Éxito", f"Documento {deca_id} generado localmente y publicado con éxito en el NAS.")

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al procesar el documento: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DecaApp(root)
    root.mainloop()
        # 2. Cargador
        f_carg = ttk.LabelFrame(self.scrollable_frame, text="2. Cargador Contractual / Remitente")
        f_carg.pack(fill="x", expand=True, **pad)

        ttk.Label(f_carg, text="Nombre / Razón:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_carg_nom = ttk.Entry(f_carg, width=50)
        self.ent_carg_nom.insert(0, "LOGÍSTICA ALIMENTARIA S.A.")
        self.ent_carg_nom.grid(row=0, column=1, **pad)

        ttk.Label(f_carg, text="NIF / CIF:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_carg_nif = ttk.Entry(f_carg, width=50)
        self.ent_carg_nif.insert(0, "A12345678")
        self.ent_carg_nif.grid(row=1, column=1, **pad)

        ttk.Label(f_carg, text="Domicilio:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_carg_dom = ttk.Entry(f_carg, width=50)
        self.ent_carg_dom.insert(0, "Av. de la Industria 45, Madrid")
        self.ent_carg_dom.grid(row=2, column=1, **pad)

        # 3. Transportista
        f_trans = ttk.LabelFrame(self.scrollable_frame, text="3. Transportista Efectivo")
        f_trans.pack(fill="x", expand=True, **pad)

        ttk.Label(f_trans, text="Nombre / Razón:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_trans_nom = ttk.Entry(f_trans, width=50)
        self.ent_trans_nom.insert(0, "TRANSPORTES RÁPIDOS S.L.")
        self.ent_trans_nom.grid(row=0, column=1, **pad)

        ttk.Label(f_trans, text="NIF / CIF:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_trans_nif = ttk.Entry(f_trans, width=50)
        self.ent_trans_nif.insert(0, "B98765432")
        self.ent_trans_nif.grid(row=1, column=1, **pad)

        ttk.Label(f_trans, text="Domicilio:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_trans_dom = ttk.Entry(f_trans, width=50)
        self.ent_trans_dom.insert(0, "Calle Transporte 12, Valencia")
        self.ent_trans_dom.grid(row=2, column=1, **pad)

        # 4. Subcontratación dinámica
        self.f_sub = ttk.LabelFrame(self.scrollable_frame, text="4. Cadena de Subcontratación (Agencias Intermediarias)")
        self.f_sub.pack(fill="x", expand=True, **pad)

        btn_add = ttk.Button(self.f_sub, text="+ Añadir Intermediario / Agencia", command=self._add_agencia_field)
        btn_add.pack(anchor="w", **pad)

        # 5. Ruta y Mercancía
        f_ruta = ttk.LabelFrame(self.scrollable_frame, text="5. Datos del Viaje y Mercancía")
        f_ruta.pack(fill="x", expand=True, **pad)

        ttk.Label(f_ruta, text="Origen:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_origen = ttk.Entry(f_ruta, width=40)
        self.ent_origen.insert(0, "Mercamadrid, Nave 4, Madrid")
        self.ent_origen.grid(row=0, column=1, **pad)

        ttk.Label(f_ruta, text="Destino:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_destino = ttk.Entry(f_ruta, width=40)
        self.ent_destino.insert(0, "Puerto de Valencia, Muelle 3")
        self.ent_destino.grid(row=1, column=1, **pad)

        ttk.Label(f_ruta, text="Mercancía:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_merc = ttk.Entry(f_ruta, width=40)
        self.ent_merc.insert(0, "Productos refrigerados")
        self.ent_merc.grid(row=2, column=1, **pad)

        ttk.Label(f_ruta, text="Peso (kg):").grid(row=3, column=0, sticky="w", **pad)
        self.ent_peso = ttk.Entry(f_ruta, width=40)
        self.ent_peso.insert(0, "18500")
        self.ent_peso.grid(row=3, column=1, **pad)

        ttk.Label(f_ruta, text="Matrícula Tractora:").grid(row=4, column=0, sticky="w", **pad)
        self.ent_mat = ttk.Entry(f_ruta, width=40)
        self.ent_mat.insert(0, "1234-BBB")
        self.ent_mat.grid(row=4, column=1, **pad)

        ttk.Label(f_ruta, text="Matrícula Remolque:").grid(row=5, column=0, sticky="w", **pad)
        self.ent_rem = ttk.Entry(f_ruta, width=40)
        self.ent_rem.insert(0, "R-5678-BBB")
        self.ent_rem.grid(row=5, column=1, **pad)

        ttk.Label(f_ruta, text="Observaciones:").grid(row=6, column=0, sticky="w", **pad)
        self.ent_obs = ttk.Entry(f_ruta, width=40)
        self.ent_obs.insert(0, "Mantener temperatura a +4°C")
        self.ent_obs.grid(row=6, column=1, **pad)

        # Botón de Generar y Publicar
        btn_gen = ttk.Button(self.scrollable_frame, text="GENERAR Y PUBLICAR DeCA EN EL NAS", command=self._procesar_deca)
        btn_gen.pack(fill="x", **pad)

    def _add_agencia_field(self):
        idx = len(self.agencias_entries) + 1
        frame_item = ttk.Frame(self.f_sub)
        frame_item.pack(fill="x", expand=True, padx=5, pady=2)

        ttk.Label(frame_item, text=f"Agencia {idx} Nombre:").grid(row=0, column=0, sticky="w")
        e_nom = ttk.Entry(frame_item, width=25)
        e_nom.grid(row=0, column=1, padx=2)

        ttk.Label(frame_item, text="NIF:").grid(row=0, column=2, sticky="w")
        e_nif = ttk.Entry(frame_item, width=15)
        e_nif.grid(row=0, column=3, padx=2)

        self.agencias_entries.append((e_nom, e_nif))

    def _procesar_deca(self):
        try:
            num_val = int(self.ent_num.get().strip())
            deca_id = f"DECA-{datetime.datetime.now().year}-{num_val:05d}"
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

            # Construir cadena de subcontratación
            agencias = []
            for nom_e, nif_e in self.agencias_entries:
                nom = nom_e.get().strip()
                nif = nif_e.get().strip()
                if nom:
                    agencias.append(f"{nom} (NIF: {nif})")

            cadena_sub = ""
            if agencias:
                cadena_sub = " | Subcontratación: " + " -> ".join(agencias)

            data = {
                "creation_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "cargador_nombre": self.ent_carg_nom.get(),
                "cargador_nif": self.ent_carg_nif.get(),
                "cargador_domicilio": self.ent_carg_dom.get(),
                "transportista_nombre": self.ent_trans_nom.get(),
                "transportista_nif": self.ent_trans_nif.get(),
                "transportista_domicilio": self.ent_trans_dom.get(),
                "origen_lugar": self.ent_origen.get(),
                "fecha_carga": now_str,
                "destino_lugar": self.ent_destino.get(),
                "fecha_descarga": "-",
                "mercancia_descripcion": self.ent_merc.get(),
                "peso_kg": self.ent_peso.get(),
                "bultos": "-",
                "matricula": self.ent_mat.get(),
                "remolque": self.ent_rem.get(),
                "observaciones": f"{self.ent_obs.get()}{cadena_sub}"
            }

            output_pdf = os.path.join(REPOSITORY_DIR, f"{deca_id}.pdf")
            
            # Generación local
            DecaGenerator.generate_deca_pdf(deca_id, data, output_pdf)
            
            # Publicación NAS
            publicar_en_nas(output_pdf)

            messagebox.showinfo("Éxito", f"Documento {deca_id} generado localmente y publicado con éxito en el NAS.")

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al procesar el documento: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = DecaApp(root)
    root.mainloop()