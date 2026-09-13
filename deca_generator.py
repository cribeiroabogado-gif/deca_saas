import os
import io
import datetime
import qrcode
import requests
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

        # 1. Código QR
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


# --- PUBLICACIÓN NAS ---

def publicar_en_nas(ruta_pdf_local):
    upload_url = "https://boutiquelegaltransporte.es/deca/upload.php"
    datos = {'token': 'MiClaveSegura2026'}
    
    with open(ruta_pdf_local, 'rb') as f:
        ficheros = {'pdf': (os.path.basename(ruta_pdf_local), f, 'application/pdf')}
        respuesta = requests.post(upload_url, data=datos, files=ficheros)
        
    if respuesta.status_code == 200:
        print("Éxito: Publicado en el NAS.")
    else:
        print(f"Error [{respuesta.status_code}]: {respuesta.text}")
        raise Exception(respuesta.text)