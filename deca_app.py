import os
import io
import datetime
import qrcode
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURACIÓN DE RUTAS Y SERVIDOR ---

BASE_URL = "https://boutiquelegaltransporte.es/deca/index.php?id="
REPOSITORY_DIR = os.path.expanduser("~/Desktop/deca_repository")
os.makedirs(REPOSITORY_DIR, exist_ok=True)


# --- GENERADOR DE PDF DeCA ---

class DecaGenerator:
    @staticmethod
    def generate_deca_pdf(deca_id, data, output_path, is_modification=False, old_data=None):
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        creation_time = data.get("creation_time", now_iso)
        modification_time = now_iso if is_modification else creation_time

        # 1. Código QR con URL fija
        download_url = f"{BASE_URL}{deca_id}"
        qr_img = qrcode.make(download_url)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        # 2. Metadatos PDF
        def add_pdf_metadata(canvas, doc):
            canvas.setTitle(f"DeCA_{deca_id}")
            canvas.setAuthor("Sistema DeCA - Orden FOM/2861/2012")
            canvas.setSubject("Documento Electrónico de Control Administrativo")
            canvas.setCreator("DeCA Generator v1.0")
            canvas._doc.info.CreationDate = creation_time
            canvas._doc.info.ModDate = modification_time

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=14, leading=18, textColor=colors.HexColor('#1A365D'), alignment=1)
        body_style = styles['BodyText']
        label_style = ParagraphStyle('LabelStyle', parent=body_style, fontName='Helvetica-Bold', fontSize=9)
        val_style = ParagraphStyle('ValStyle', parent=body_style, fontSize=9)
        small_style = ParagraphStyle('SmallStyle', parent=body_style, fontSize=8, textColor=colors.gray)

        story = []

        # Encabezado
        story.append(Paragraph("DOCUMENTO ELECTRÓNICO DE CONTROL ADMINISTRATIVO (DeCA)", title_style))
        story.append(Paragraph("Transporte Público de Mercancías por Carretera (Orden FOM/2861/2012)", ParagraphStyle('Sub', alignment=1, fontSize=9, textColor=colors.HexColor('#4A5568'))))
        story.append(Spacer(1, 10))

        # Bloque superior
        qr_image_obj = Image(qr_buffer, width=80, height=80)
        info_text = f"""
        <b>ID DeCA:</b> {deca_id}<br/>
        <b>Fecha/Hora Creación:</b> {creation_time}<br/>
        <b>Fecha/Hora Modificación:</b> {modification_time}<br/>
        <b>URL Inspección:</b> {download_url}
        """
        top_table = Table([[Paragraph(info_text, body_style), qr_image_obj]], colWidths=[400, 120])
        top_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        story.append(top_table)
        story.append(Spacer(1, 12))

        # Bloque 1: Sujetos
        sujetos_data = [
            [Paragraph("1. CARGADOR CONTRACTUAL", label_style), Paragraph("2. TRANSPORTISTA EFECTIVO", label_style)],
            [
                Paragraph(f"<b>Nombre/Razón:</b> {data['cargador_nombre']}<br/><b>NIF/CIF:</b> {data['cargador_nif']}<br/><b>Domicilio:</b> {data['cargador_domicilio']}", val_style),
                Paragraph(f"<b>Nombre/Razón:</b> {data['transportista_nombre']}<br/><b>NIF/CIF:</b> {data['transportista_nif']}<br/><b>Domicilio:</b> {data['transportista_domicilio']}", val_style)
            ]
        ]
        t_sujetos = Table(sujetos_data, colWidths=[260, 260])
        t_sujetos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#EDF2F7')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(t_sujetos)
        story.append(Spacer(1, 10))

        # Bloque 2: Ruta
        ruta_data = [
            [Paragraph("3. ORIGEN Y LUGAR DE CARGA", label_style), Paragraph("4. DESTINO Y LUGAR DE DESCARGA", label_style)],
            [
                Paragraph(f"<b>Lugar:</b> {data['origen_lugar']}<br/><b>Fecha/Hora Carga:</b> {data.get('fecha_carga', '-')}", val_style),
                Paragraph(f"<b>Lugar:</b> {data['destino_lugar']}<br/><b>Fecha/Hora Descarga:</b> {data.get('fecha_descarga', '-')}", val_style)
            ]
        ]
        t_ruta = Table(ruta_data, colWidths=[260, 260])
        t_ruta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#EDF2F7')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(t_ruta)
        story.append(Spacer(1, 10))

        # Bloque 3: Mercancía y Vehículo
        merc_data = [
            [Paragraph("5. MERCANCÍA TRANSPORTADA", label_style), Paragraph("6. VEHÍCULO / OBSERVACIONES", label_style)],
            [
                Paragraph(f"<b>Naturaleza:</b> {data['mercancia_descripcion']}<br/><b>Peso Bruto:</b> {data['peso_kg']} kg<br/><b>Bultos:</b> {data.get('bultos', '-')}", val_style),
                Paragraph(f"<b>Matrícula Tractora:</b> {data['matricula']}<br/><b>Matrícula Remolque:</b> {data.get('remolque', '-')}<br/><b>Observaciones / Subcontratación:</b> {data.get('observaciones', 'Ninguna')}", val_style)
            ]
        ]
        t_merc = Table(merc_data, colWidths=[260, 260])
        t_merc.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#EDF2F7')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(t_merc)

        story.append(Spacer(1, 15))
        story.append(Paragraph("Documento generado mediante aplicación informática conforme a la Resolución de 5 de junio de 2026 de la DG de Transporte por Carretera y Ferrocarril.", small_style))

        doc.build(story, onFirstPage=add_pdf_metadata)


# --- PUBLICACIÓN AL NAS ---

def publicar_en_nas(ruta_pdf_local):
    upload_url = "https://boutiquelegaltransporte.es/deca/upload.php"
    datos = {'token': 'MiClaveSegura2026'}
    
    with open(ruta_pdf_local, 'rb') as f:
        ficheros = {'pdf': (os.path.basename(ruta_pdf_local), f, 'application/pdf')}
        respuesta = requests.post(upload_url, data=datos, files=ficheros)
        
    if respuesta.status_code == 200:
        print("Éxito: Publicado en el NAS.")
    else:
        raise Exception(f"Error [{respuesta.status_code}]: {respuesta.text}")


# --- INTERFAZ GRÁFICA INTERACTIVA (TKINTER) ---

class DecaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor DeCA - Boutique Legal Transporte")
        self.root.geometry("750x720")

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

        ttk.Label(self.scrollable_frame, text="DOCUMENTO ELECTRÓNICO DE CONTROL (DeCA)", font=('Helvetica', 13, 'bold')).pack(**pad)

        # 1. ID
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
        self.ent_carg_nom = ttk.Entry(f_carg, width=45)
        self.ent_carg_nom.insert(0, "LOGÍSTICA ALIMENTARIA S.A.")
        self.ent_carg_nom.grid(row=0, column=1, **pad)

        ttk.Label(f_carg, text="NIF / CIF:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_carg_nif = ttk.Entry(f_carg, width=45)
        self.ent_carg_nif.insert(0, "A12345678")
        self.ent_carg_nif.grid(row=1, column=1, **pad)

        ttk.Label(f_carg, text="Domicilio:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_carg_dom = ttk.Entry(f_carg, width=45)
        self.ent_carg_dom.insert(0, "Av. de la Industria 45, Madrid")
        self.ent_carg_dom.grid(row=2, column=1, **pad)

        # 3. Transportista
        f_trans = ttk.LabelFrame(self.scrollable_frame, text="3. Transportista Efectivo")
        f_trans.pack(fill="x", expand=True, **pad)
        ttk.Label(f_trans, text="Nombre / Razón:").grid(row=0, column=0, sticky="w", **pad)
        self.ent_trans_nom = ttk.Entry(f_trans, width=45)
        self.ent_trans_nom.insert(0, "TRANSPORTES RÁPIDOS S.L.")
        self.ent_trans_nom.grid(row=0, column=1, **pad)

        ttk.Label(f_trans, text="NIF / CIF:").grid(row=1, column=0, sticky="w", **pad)
        self.ent_trans_nif = ttk.Entry(f_trans, width=45)
        self.ent_trans_nif.insert(0, "B98765432")
        self.ent_trans_nif.grid(row=1, column=1, **pad)

        ttk.Label(f_trans, text="Domicilio:").grid(row=2, column=0, sticky="w", **pad)
        self.ent_trans_dom = ttk.Entry(f_trans, width=45)
        self.ent_trans_dom.insert(0, "Calle Transporte 12, Valencia")
        self.ent_trans_dom.grid(row=2, column=1, **pad)

        # 4. Cadena de Subcontratación
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
        e_nom = ttk.Entry(frame_item, width=22)
        e_nom.grid(row=0, column=1, padx=2)

        ttk.Label(frame_item, text="NIF:").grid(row=0, column=2, sticky="w")
        e_nif = ttk.Entry(frame_item, width=12)
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