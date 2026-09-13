import os
import io
import qrcode
from fpdf import FPDF
from fastapi import FastAPI, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# ------------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE BASE DE DATOS Y APLICACIÓN
# ------------------------------------------------------------------------------
# Ruta segura en /tmp para evitar fallos de permisos en el contenedor Docker
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/deca_saas.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de datos para guardar los documentos de control (DeCA)
class DecaModel(Base):
    __tablename__ = "decas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True)
    cargador = Column(String)
    transportista = Column(String)
    origen = Column(String)
    destino = Column(String)
    mercancia = Column(String)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SaaS DeCA API",
    description="Gestión y emisión de Documentos de Control Electrónico de Transporte (DeCA)",
    version="0.1.0"
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
    transportista: str
    origen: str
    destino: str
    mercancia: str

class DecaResponse(DecaCreate):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True

# ------------------------------------------------------------------------------
# 3. GENERADOR DE PDF Y QR (NORMATIVA DECA)
# ------------------------------------------------------------------------------
def generar_pdf_deca(deca_data: dict, url_descarga: str) -> bytes:
    # Generar imagen QR que apunta a la llamada directa de descarga en PDF
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(url_descarga)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    
    qr_path = f"/tmp/qr_{deca_data['codigo']}.png"
    img_qr.save(qr_path)

    # Construcción del documento de control en formato PDF
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # Encabezado oficial
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.cell(0, 10, "DOCUMENTO DE CONTROL ELECTRÓNICO (DeCA)", ln=True, align="C")
    pdf.ln(5)
    
    # Detalle de la carga y las partes del contrato de transporte
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, f"Código DeCA: {deca_data['codigo']}", ln=True)
    pdf.cell(0, 7, f"Cargador: {deca_data['cargador']}", ln=True)
    pdf.cell(0, 7, f"Transportista: {deca_data['transportista']}", ln=True)
    pdf.cell(0, 7, f"Origen: {deca_data['origen']}  -->  Destino: {deca_data['destino']}", ln=True)
    pdf.cell(0, 7, f"Mercancía: {deca_data['mercancia']}", ln=True)
    pdf.ln(5)

    # Estampar código QR de verificación para inspección en carretera
    if os.path.exists(qr_path):
        pdf.image(qr_path, x=140, y=35, w=45)
    
    return bytes(pdf.output())

# ------------------------------------------------------------------------------
# 4. RUTAS Y ENDPOINTS DE LA APLICACIÓN
# ------------------------------------------------------------------------------

# Redirección de la raíz '/' directo al Dashboard para evitar 404
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")

# Vista HTML simple para el panel principal
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
            <h1 class="text-2xl font-bold mb-4 text-gray-800">Panel de Control DeCA</h1>
            <p class="text-gray-600 mb-6">Emisión y verificación de documentos de control de transporte.</p>
            <div class="space-x-4">
                <a href="/docs" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Documentación API</a>
                <a href="/api/v1/deca/DECA-TEST/pdf" class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">Probar PDF de Ejemplo</a>
            </div>
        </div>
    </body>
    </html>
    """

# Login de autenticación (Placeholder para token JWT)
@app.post("/api/v1/auth/login")
def login():
    return {"access_token": "token_demo_deca", "token_type": "bearer"}

# Crear un nuevo registro de DeCA
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

# Listar registros emitidos
@app.get("/api/v1/deca", response_model=List[DecaResponse])
def listar_decas(db: Session = Depends(get_db)):
    return db.query(DecaModel).all()

# Endpoint para cumplimiento de la norma: Descarga/Verificación directa en formato PDF mediante URL/QR
@app.get("/api/v1/deca/{codigo_deca}/pdf")
def descargar_deca_pdf(codigo_deca: str, db: Session = Depends(get_db)):
    # Buscar en BD o usar datos plantilla para pruebas
    deca_registro = db.query(DecaModel).filter(DecaModel.codigo == codigo_deca).first()
    
    if deca_registro:
        datos = {
            "codigo": deca_registro.codigo,
            "cargador": deca_registro.cargador,
            "transportista": deca_registro.transportista,
            "origen": deca_registro.origen,
            "destino": deca_registro.destino,
            "mercancia": deca_registro.mercancia,
        }
    else:
        datos = {
            "codigo": codigo_deca,
            "cargador": "Logística Codecar S.L.",
            "transportista": "Transportes Ejemplo S.L.",
            "origen": "Madrid",
            "destino": "Vigo",
            "mercancia": "Carga General / Paquetería"
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

# Vista pública web individual
@app.get("/view/deca/{codigo_deca}", response_class=HTMLResponse)
def ver_deca_web(codigo_deca: str):
    return RedirectResponse(url=f"/api/v1/deca/{codigo_deca}/pdf")