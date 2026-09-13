import os
import io
import qrcode
from fpdf import FPDF
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ------------------------------------------------------------------------------
# 1. BASE DE DATOS Y CONFIGURACIÓN
# ------------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/deca_saas.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DecaModel(Base):
    __tablename__ = "decas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)
    cargador = Column(String)
    cargador_nif = Column(String, default="B12345678")
    cargador_dir = Column(String, default="Pol. Ind. Sabón, Av. Principal 12")
    cargador_pob = Column(String, default="15172 Arteixo (A Coruña)")
    
    transportista = Column(String)
    transportista_nif = Column(String, default="B87654321")
    matricula_tractor = Column(String, default="1234-BBB")
    matricula_remolque = Column(String, default="R-5678-BBB")
    
    origen = Column(String)
    destino = Column(String)
    fecha_salida = Column(String, default="13/09/2026 18:30")
    fecha_entrega = Column(String, default="14/09/2026 08:00")
    
    mercancia = Column(String)
    bultos = Column(String, default="12 Palets")
    peso = Column(String, default="4.250 kg")
    adr = Column(String, default="No aplica")
    observaciones = Column(String, default="Carga estibada y sujeta correctamente según normativa vigente.")
    
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SaaS DeCA API",
    description="Emisión y gestión de Documentos de Control Electrónico de Transporte (DeCA)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------------------------------------------------------
# 2. ESQUEMAS PYDANTIC
# ------------------------------------------------------------------------------
class DecaCreate(BaseModel):
    codigo: str
    cargador: str
    cargador_nif: Optional[str] = "B12345678"
    cargador_dir: Optional[str] = "Pol. Ind. Sabón, Av. Principal 12"
    cargador_pob: Optional[str] = "15172 Arteixo (A Coruña)"
    
    transportista: str
    transportista_nif: Optional[str] = "B87654321"
    matricula_tractor: Optional[str] = "1234-BBB"
    matricula_remolque: Optional[str] = "R-5678-BBB"
    
    origen: str
    destino: str
    fecha_salida: Optional[str] = "13/09/2026 18:30"
    fecha_entrega: Optional[str] = "14/09/2026 08:00"
    
    mercancia: str
    bultos: Optional[str] = "12 Palets"
    peso: Optional[str] = "4.250 kg"
    adr: Optional[str] = "No aplica"
    observaciones: Optional[str] = "Carga estibada y sujeta correctamente según normativa vigente."

class DecaResponse(DecaCreate):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True

# ------------------------------------------------------------------------------
# 3. MOTOR DE GENERACIÓN DEL PDF FORMAL
# ------------------------------------------------------------------------------
def generar_pdf_deca(deca_data: dict, url_descarga: str) -> bytes:
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(url_descarga)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    qr_path = f"/tmp/qr_{deca_data.get('codigo', 'temp')}.png"
    img_qr.save(qr_path)

    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Encabezado principal
    pdf.set_font("Helvetica", style="B", size=13)
    pdf.cell(0, 6, "DOCUMENTO DE CONTROL ADMINISTRATIVO EN EL TRANSPORTE (DeCA)", ln=True, align="C")
    pdf.set_font("Helvetica", size=8)
    pdf.cell(0, 4, "Orden FOM/2861/2012 y Ley 16/1987 de Ordenación de los Transportes Terrestres (LOTT)", ln=True, align="C")
    pdf.ln(4)

    # Guardar posición Y inicial del bloque superior
    y_inicial = pdf.get_y()

    # Recuadro del Código (Izquierda)
    pdf.set_font("Helvetica", style="B", size=10)
    pdf.cell(145, 30, f" CÓDIGO DE DOCUMENTO: {deca_data.get('codigo', 'DECA-001')}", border=1)

    # Recuadro y estampado del QR (Derecha)
    pdf.set_xy(158, y_inicial)
    pdf.cell(32, 30, "", border=1) # Marco exterior del QR
    if os.path.exists(qr_path):
        pdf.image(qr_path, x=159, y=y_inicial + 1, w=28)

    # Forzar el salto de posición Y por debajo de los bloques superiores (30mm + margen)
    pdf.set_xy(10, y_inicial + 34)

    def seccion_titulo(texto):
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Helvetica", style="B", size=9)
        pdf.cell(0, 6, f" {texto}", border=1, ln=True, fill=True)

    def campo_doble(lbl1, val1, lbl2, val2):
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.cell(32, 5, f" {lbl1}:", border="LBT", ln=False)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(63, 5, f"{val1}", border="RBT", ln=False)
        
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.cell(32, 5, f" {lbl2}:", border="LBT", ln=False)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(63, 5, f"{val2}", border="RBT", ln=True)

    # 1. Cargador
    seccion_titulo("1. CARGADOR CONTRACTUAL / REMITENTE")
    campo_doble("Nombre / Razón", deca_data.get("cargador", "-"), "NIF / CIF", deca_data.get("cargador_nif", "-"))
    campo_doble("Domicilio", deca_data.get("cargador_dir", "-"), "Localidad / CP", deca_data.get("cargador_pob", "-"))
    pdf.ln(3)

    # 2. Transportista
    seccion_titulo("2. TRANSPORTISTA EFECTIVO")
    campo_doble("Nombre / Razón", deca_data.get("transportista", "-"), "NIF / CIF", deca_data.get("transportista_nif", "-"))
    campo_doble("Matrícula Tractor", deca_data.get("matricula_tractor", "-"), "Matrícula Remolque", deca_data.get("matricula_remolque", "-"))
    pdf.ln(3)

    # 3. Ruta
    seccion_titulo("3. LUGARES DE ORIGEN Y DESTINO")
    campo_doble("Lugar de Origen", deca_data.get("origen", "-"), "Fecha / Hora Salida", deca_data.get("fecha_salida", "-"))
    campo_doble("Lugar de Destino", deca_data.get("destino", "-"), "Fecha Prevista", deca_data.get("fecha_entrega", "-"))
    pdf.ln(3)

    # 4. Mercancía
    seccion_titulo("4. DESCRIPCIÓN Y NATURALEZA DE LA MERCANCÍA")
    campo_doble("Descripción", deca_data.get("mercancia", "-"), "Nº de Bultos", deca_data.get("bultos", "-"))
    campo_doble("Peso Bruto", deca_data.get("peso", "-"), "Clase ADR", deca_data.get("adr", "-"))
    pdf.ln(3)

    # 5. Observaciones
    seccion_titulo("5. OBSERVACIONES Y RESERVAS EN LA CARGA / ESTIBA")
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell(0, 10, f" {deca_data.get('observaciones', '-')}", border=1)
    pdf.ln(4)

    # Pie
    pdf.set_font("Helvetica", style="I", size=7)
    pdf.cell(0, 4, "Documento de Control de Transporte emitido de conformidad con la normativa de transportes.", ln=True, align="C")

    return bytes(pdf.output())
# ------------------------------------------------------------------------------
# 4. RUTAS Y ENDPOINTS
# ------------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>SaaS DeCA - Panel de Control</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-4xl mx-auto bg-white p-6 rounded-lg shadow">
            <h1 class="text-2xl font-bold mb-2 text-gray-800">Panel de Control DeCA</h1>
            <p class="text-gray-600 mb-6">Emisión y verificación de Documentos de Control de Transporte.</p>
            <div class="space-x-4">
                <a href="/docs" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Documentación API</a>
                <a href="/api/v1/deca/DECA-TEST/pdf" target="_blank" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Ver PDF de Ejemplo</a>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/api/v1/auth/login")
def login():
    return {"access_token": "token_demo_deca", "token_type": "bearer"}

@app.post("/api/v1/deca", response_model=DecaResponse)
def crear_deca(deca: DecaCreate, db: Session = Depends(get_db)):
    db_deca = db.query(DecaModel).filter(DecaModel.codigo == deca.codigo).first()
    if db_deca:
        raise HTTPException(status_code=400, detail="El código DeCA ya existe")
    
    nuevo_registro = DecaModel(**deca.dict())
    db.add(nuevo_registro)
    db.commit()
    db.refresh(nuevo_registro)
    return nuevo_registro

@app.get("/api/v1/deca", response_model=List[DecaResponse])
def listar_decas(db: Session = Depends(get_db)):
    return db.query(DecaModel).all()

@app.get("/api/v1/deca/{codigo_deca}/pdf")
def descargar_deca_pdf(codigo_deca: str, db: Session = Depends(get_db)):
    deca_registro = db.query(DecaModel).filter(DecaModel.codigo == codigo_deca).first()
    
    if deca_registro:
        datos = {
            "codigo": deca_registro.codigo,
            "cargador": deca_registro.cargador,
            "cargador_nif": deca_registro.cargador_nif,
            "cargador_dir": deca_registro.cargador_dir,
            "cargador_pob": deca_registro.cargador_pob,
            "transportista": deca_registro.transportista,
            "transportista_nif": deca_registro.transportista_nif,
            "matricula_tractor": deca_registro.matricula_tractor,
            "matricula_remolque": deca_registro.matricula_remolque,
            "origen": deca_registro.origen,
            "destino": deca_registro.destino,
            "fecha_salida": deca_registro.fecha_salida,
            "fecha_entrega": deca_registro.fecha_entrega,
            "mercancia": deca_registro.mercancia,
            "bultos": deca_registro.bultos,
            "peso": deca_registro.peso,
            "adr": deca_registro.adr,
            "observaciones": deca_registro.observaciones,
        }
    else:
        datos = {
            "codigo": codigo_deca,
            "cargador": "Logística Codecar S.L.",
            "cargador_nif": "B12345678",
            "cargador_dir": "Pol. Ind. Sabón, Av. Principal 12",
            "cargador_pob": "15172 Arteixo (A Coruña)",
            "transportista": "Transportes Ejemplo S.L.",
            "transportista_nif": "B87654321",
            "matricula_tractor": "1234-BBB",
            "matricula_remolque": "R-5678-BBB",
            "origen": "Madrid (Centro Logístico)",
            "destino": "Vigo (Zona Franca)",
            "fecha_salida": "13/09/2026 18:30",
            "fecha_entrega": "14/09/2026 08:00",
            "mercancia": "Paquetería industrial / Piezas recambio",
            "bultos": "12 Palets",
            "peso": "4.250 kg",
            "adr": "No aplica",
            "observaciones": "Carga estibada y sujeta correctamente según normativa vigente."
        }

    url_descarga = f"https://deca-saas.onrender.com/api/v1/deca/{codigo_deca}/pdf"
    
    try:
        pdf_bytes = generar_pdf_deca(datos, url_descarga)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar el PDF: {str(e)}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename=DeCA_{codigo_deca}.pdf"
        }
    )

@app.get("/view/deca/{codigo_deca}", response_class=HTMLResponse)
def ver_deca_web(codigo_deca: str):
    return RedirectResponse(url=f"/api/v1/deca/{codigo_deca}/pdf")