import os
import hashlib
from datetime import datetime, timedelta, date
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from jose import JWTError, jwt
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "LLAVE_SECRETA_POR_DEFECTO")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////tmp/deca_saas.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# MODELOS BASE DE DATOS
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class DecaDocument(Base):
    __tablename__ = "deca_documents"
    id = Column(Integer, primary_key=True, index=True)
    codigo_deca = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    cargador_nombre = Column(String, nullable=False)
    cargador_nif = Column(String, nullable=False)
    cargador_domicilio = Column(String, nullable=False)
    transportista_nombre = Column(String, nullable=False)
    transportista_nif = Column(String, nullable=False)
    transportista_email = Column(String, nullable=True)
    origen_lugar = Column(String, nullable=False)
    destino_lugar = Column(String, nullable=False)
    mercancia_descripcion = Column(String, nullable=False)
    peso_kg = Column(String, nullable=False)
    fecha_transporte = Column(String, nullable=False)
    matricula = Column(String, nullable=False)
    remolque = Column(String, nullable=True)
    autorizacion_especial = Column(String, nullable=True)
    observaciones = Column(String, nullable=True)
    hash_sha256 = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def get_optional_current_user(token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)), db: Session = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email:
            return db.query(User).filter(User.email == email).first()
    except JWTError:
        pass
    return None

def send_deca_email(email_destino: str, codigo_deca: str, hash_sha256: str):
    if email_destino:
        print(f"[EMAIL] Enviando DeCA {codigo_deca} a {email_destino} (Hash: {hash_sha256})")

# ESQUEMAS PYDANTIC
class DecaCreate(BaseModel):
    cargador_nombre: str
    cargador_nif: str
    cargador_domicilio: str
    transportista_nombre: str
    transportista_nif: str
    transportista_email: Optional[str] = None
    origen_lugar: str
    destino_lugar: str
    mercancia_descripcion: str
    peso_kg: str
    fecha_transporte: str
    matricula: str
    remolque: Optional[str] = None
    autorizacion_especial: Optional[str] = None
    observaciones: Optional[str] = None

class DecaResponse(DecaCreate):
    codigo_deca: str
    hash_sha256: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

app = FastAPI(title="SaaS DeCA API")

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "contacto@unamunolegal.es")
    admin_pass = os.getenv("INITIAL_ADMIN_PASSWORD", "mi_password_seguro_123")
    if not db.query(User).filter(User.email == admin_email).first():
        db.add(User(
            email=admin_email,
            hashed_password=hash_password(admin_pass)
        ))
        db.commit()
    db.close()

@app.post("/api/v1/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Correo o contraseña incorrectos"
        )
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/deca", response_model=DecaResponse)
def create_deca(
    deca_data: DecaCreate, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    codigo_deca = f"DECA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    raw_payload = f"{codigo_deca}|{deca_data.cargador_nif}|{deca_data.transportista_nif}|{deca_data.fecha_transporte}"
    hash_sha256 = hashlib.sha256(raw_payload.encode()).hexdigest()

    db_deca = DecaDocument(
        codigo_deca=codigo_deca,
        user_id=current_user.id,
        hash_sha256=hash_sha256,
        **deca_data.model_dump()
    )
    db.add(db_deca)
    db.commit()
    db.refresh(db_deca)

    if deca_data.transportista_email:
        background_tasks.add_task(send_deca_email, deca_data.transportista_email, codigo_deca, hash_sha256)

    return db_deca

@app.get("/api/v1/deca", response_model=List[DecaResponse])
def list_decas(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(DecaDocument).filter(DecaDocument.user_id == current_user.id).order_by(DecaDocument.created_at.desc()).all()

@app.get("/view/deca/{codigo_deca}", response_class=HTMLResponse)
def view_deca_document(codigo_deca: str, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_optional_current_user)):
    doc = db.query(DecaDocument).filter(DecaDocument.codigo_deca == codigo_deca).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento DeCA no encontrado")

    is_authenticated = current_user is not None and current_user.id == doc.user_id
    if not is_authenticated:
        try:
            fecha_transporte_dt = datetime.strptime(doc.fecha_transporte, "%Y-%m-%d").date()
        except ValueError:
            fecha_transporte_dt = doc.created_at.date()

        dias_transcurridos = (date.today() - fecha_transporte_dt).days
        if dias_transcurridos > 7:
            expired_html = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>Verificación Expirada - {doc.codigo_deca}</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-slate-100 flex items-center justify-center min-h-screen p-4">
                <div class="bg-white p-8 rounded-xl shadow-md max-w-md w-full text-center border border-amber-200">
                    <div class="text-amber-500 mb-3 text-4xl">⏳</div>
                    <h1 class="text-lg font-bold text-slate-800 mb-2">Acceso Público Expirado</h1>
                    <p class="text-xs text-slate-600 mb-4">
                        Han transcurrido más de <strong>7 días naturales</strong> desde la fecha del transporte (<strong>{doc.fecha_transporte}</strong>).
                    </p>
                    <div class="bg-amber-50 text-amber-800 text-[11px] p-3 rounded text-left border border-amber-200 mb-4">
                        Conforme a la normativa vigente, la consulta mediante URL/QR finaliza a los 7 días. El documento oficial sigue estando disponible en el archivo privado del cargador/transportista para su conservación durante 1 año.
                    </div>
                    <p class="text-[10px] font-mono text-slate-400">Código DeCA: {doc.codigo_deca}</p>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=expired_html, status_code=410)

    qr_url = f"{BASE_URL}/view/deca/{doc.codigo_deca}"

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Documento DeCA - {doc.codigo_deca}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    </head>
    <body class="bg-slate-100 p-8">
        <div class="max-w-3xl mx-auto mb-4 text-center no-print flex gap-4 justify-center">
            <button onclick="downloadPDF()" class="bg-blue-600 text-white px-4 py-2 rounded text-xs font-bold hover:bg-blue-700 shadow">
                Descargar PDF Directo
            </button>
            <button onclick="window.close()" class="bg-slate-500 text-white px-4 py-2 rounded text-xs font-bold hover:bg-slate-600 shadow">
                Cerrar
            </button>
        </div>

        <div id="deca-document" class="max-w-3xl mx-auto bg-white p-8 rounded-lg shadow-md border border-slate-300">
            <div class="flex justify-between items-center border-b-2 border-slate-800 pb-4 mb-6">
                <div>
                    <h1 class="text-xl font-bold text-slate-900">DOCUMENTO DE CONTROL DE TRANSPORTE (DeCA)</h1>
                    <p class="text-xs text-slate-500">Orden FOM/2861/2012, de 13 de diciembre</p>
                </div>
                <div class="text-right">
                    <span class="block text-sm font-bold text-blue-700">{doc.codigo_deca}</span>
                    <span class="block text-xs text-slate-500">Fecha transporte: <strong>{doc.fecha_transporte}</strong></span>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-6 mb-6">
                <div class="border p-4 rounded bg-slate-50">
                    <h2 class="text-xs font-bold text-slate-700 uppercase mb-2 border-b pb-1">a) Cargador Contractual</h2>
                    <p class="text-sm font-semibold text-slate-800">{doc.cargador_nombre}</p>
                    <p class="text-xs text-slate-600">NIF: {doc.cargador_nif}</p>
                    <p class="text-xs text-slate-600">Domicilio: {doc.cargador_domicilio}</p>
                </div>
                <div class="border p-4 rounded bg-slate-50">
                    <h2 class="text-xs font-bold text-slate-700 uppercase mb-2 border-b pb-1">b) Transportista Efectivo</h2>
                    <p class="text-sm font-semibold text-slate-800">{doc.transportista_nombre}</p>
                    <p class="text-xs text-slate-600">NIF: {doc.transportista_nif}</p>
                    <p class="text-xs text-slate-600">Email: {doc.transportista_email or 'N/A'}</p>
                </div>
            </div>

            <div class="grid grid-cols-2 gap-6 mb-6">
                <div class="border p-4 rounded">
                    <h2 class="text-xs font-bold text-slate-700 uppercase mb-2 border-b pb-1">c) Ruta de Transporte</h2>
                    <p class="text-xs text-slate-700"><strong>Origen:</strong> {doc.origen_lugar}</p>
                    <p class="text-xs text-slate-700"><strong>Destino:</strong> {doc.destino_lugar}</p>
                    <p class="text-xs text-slate-700 mt-2"><strong>f) Fecha del Transporte:</strong> {doc.fecha_transporte}</p>
                </div>
                <div class="border p-4 rounded">
                    <h2 class="text-xs font-bold text-slate-700 uppercase mb-2 border-b pb-1">d) & g) Mercancía y Vehículo</h2>
                    <p class="text-xs text-slate-700"><strong>Mercancía:</strong> {doc.mercancia_descripcion}</p>
                    <p class="text-xs text-slate-700"><strong>Peso / Magnitud:</strong> {doc.peso_kg} kg</p>
                    <p class="text-xs text-slate-700 mt-2"><strong>Tractor:</strong> {doc.matricula}</p>
                    <p class="text-xs text-slate-700"><strong>Semirremolque/Remolque:</strong> {doc.remolque or 'N/A'}</p>
                </div>
            </div>

            {f'<div class="border p-4 rounded mb-6 bg-amber-50/50"><h2 class="text-xs font-bold text-slate-700 uppercase mb-1">e) Autorización Especial de Circulación</h2><p class="text-xs text-slate-800">{doc.autorizacion_especial}</p></div>' if doc.autorizacion_especial else ''}

            <div class="border p-4 rounded mb-6">
                <h2 class="text-xs font-bold text-slate-700 uppercase mb-1 border-b pb-1">h) Observaciones y Reservas</h2>
                <p class="text-xs text-slate-700 italic">{doc.observaciones or 'Sin observaciones ni reservas registradas.'}</p>
            </div>

            <div class="border-t pt-4 mt-6 flex items-center justify-between">
                <div class="pr-4">
                    <p class="text-[10px] text-slate-500 font-mono break-all mb-1"><strong>Firma Digital / SHA-256:</strong></p>
                    <p class="text-[10px] text-slate-500 font-mono break-all">{doc.hash_sha256}</p>
                </div>
                <div id="qrcode" class="p-1 bg-white border rounded shrink-0"></div>
            </div>
        </div>

        <script>
            new QRCode(document.getElementById("qrcode"), {{
                text: "{qr_url}",
                width: 70,
                height: 70,
                colorDark : "#000000",
                colorLight : "#ffffff",
                correctLevel : QRCode.CorrectLevel.H
            }});

            function downloadPDF() {{
                const element = document.getElementById('deca-document');
                const opt = {{
                    margin:       10,
                    filename:     '{doc.codigo_deca}.pdf',
                    image:        {{ type: 'jpeg', quality: 0.98 }},
                    html2canvas:  {{ scale: 2, useCORS: true }},
                    jsPDF:        {{ unit: 'mm', format: 'a4', orientation: 'portrait' }}
                }};
                html2pdf().set(opt).from(element).save();
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    today_str = date.today().isoformat()
    html_content = f'''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard SaaS DeCA</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen">
        <div id="login-screen" class="flex items-center justify-center min-h-screen p-4">
            <div class="bg-white p-8 rounded-xl shadow-md w-full max-w-md border border-slate-200">
                <h1 class="text-2xl font-bold text-slate-800 text-center mb-2">SaaS DeCA</h1>
                <p class="text-sm text-slate-500 text-center mb-6">Iniciar sesión en la plataforma</p>
                <div id="login-error" class="hidden bg-red-50 text-red-600 text-sm p-3 rounded-md mb-4 border border-red-200"></div>
                <form id="login-form" onsubmit="handleLogin(event)" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Usuario / Email</label>
                        <input type="email" id="username" required value="contacto@unamunolegal.es" class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-slate-600 uppercase mb-1">Contraseña</label>
                        <input type="password" id="password" required value="mi_password_seguro_123" class="w-full px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800">
                    </div>
                    <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-md transition duration-200">
                        Entrar al Panel
                    </button>
                </form>
            </div>
        </div>

        <div id="app-screen" class="hidden min-h-screen flex flex-col">
            <header class="bg-slate-900 text-white py-4 px-6 flex justify-between items-center shadow-md">
                <div>
                    <h1 class="text-lg font-bold tracking-wide">Gestión de Documentos DeCA</h1>
                    <p class="text-xs text-slate-400">Orden FOM/2861/2012</p>
                </div>
                <button onclick="handleLogout()" class="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded border border-slate-700 transition">
                    Cerrar Sesión
                </button>
            </header>

            <main class="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 lg:col-span-1">
                    <h2 class="text-base font-bold text-slate-800 mb-4 border-b pb-2">Nuevo Documento DeCA</h2>
                    <form id="deca-form" onsubmit="handleCreateDeca(event)" class="space-y-3 text-sm">
                        <div class="bg-slate-50 p-2.5 rounded border border-slate-200 space-y-2">
                            <span class="block text-[11px] font-bold text-slate-700 uppercase">a) Cargador Contractual</span>
                            <div>
                                <label class="block text-[11px] text-slate-600">Nombre / Razón Social</label>
                                <input type="text" id="cargador_nombre" required value="LOGÍSTICA ALIMENTARIA S.A." class="w-full border p-1 rounded text-xs bg-white">
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    <label class="block text-[11px] text-slate-600">NIF</label>
                                    <input type="text" id="cargador_nif" required value="A12345678" class="w-full border p-1 rounded text-xs bg-white">
                                </div>
                                <div>
                                    <label class="block text-[11px] text-slate-600">Domicilio</label>
                                    <input type="text" id="cargador_domicilio" required value="Av. Industria 45, Madrid" class="w-full border p-1 rounded text-xs bg-white">
                                </div>
                            </div>
                        </div>

                        <div class="bg-slate-50 p-2.5 rounded border border-slate-200 space-y-2">
                            <span class="block text-[11px] font-bold text-slate-700 uppercase">b) Transportista Efectivo</span>
                            <div>
                                <label class="block text-[11px] text-slate-600">Nombre / Razón Social</label>
                                <input type="text" id="transportista_nombre" required value="TRANSPORTES RÁPIDOS S.L." class="w-full border p-1 rounded text-xs bg-white">
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <div>
                                    <label class="block text-[11px] text-slate-600">NIF</label>
                                    <input type="text" id="transportista_nif" required value="B98765432" class="w-full border p-1 rounded text-xs bg-white">
                                </div>
                                <div>
                                    <label class="block text-[11px] text-slate-600">Email Envío (opcional)</label>
                                    <input type="email" id="transportista_email" value="efectivo@transportes.com" class="w-full border p-1 rounded text-xs bg-white">
                                </div>
                            </div>
                        </div>

                        <div class="grid grid-cols-3 gap-2">
                            <div>
                                <label class="block text-[11px] text-slate-600">Origen</label>
                                <input type="text" id="origen_lugar" required value="Madrid" class="w-full border p-1 rounded text-xs">
                            </div>
                            <div>
                                <label class="block text-[11px] text-slate-600">Destino</label>
                                <input type="text" id="destino_lugar" required value="Valencia" class="w-full border p-1 rounded text-xs">
                            </div>
                            <div>
                                <label class="block text-[11px] text-slate-600">Fecha porte</label>
                                <input type="date" id="fecha_transporte" required value="{today_str}" class="w-full border p-1 rounded text-xs">
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="block text-[11px] text-slate-600">Mercancía</label>
                                <input type="text" id="mercancia_descripcion" required value="Productos Refrigerados" class="w-full border p-1 rounded text-xs">
                            </div>
                            <div>
                                <label class="block text-[11px] text-slate-600">Peso / Magnitud (kg)</label>
                                <input type="text" id="peso_kg" required value="18500" class="w-full border p-1 rounded text-xs">
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="block text-[11px] text-slate-600">Matrícula Tractor</label>
                                <input type="text" id="matricula" required value="1234-BBB" class="w-full border p-1 rounded text-xs">
                            </div>
                            <div>
                                <label class="block text-[11px] text-slate-600">Semirremolque/Remolque</label>
                                <input type="text" id="remolque" value="R-5678-BBB" class="w-full border p-1 rounded text-xs">
                            </div>
                        </div>

                        <div>
                            <label class="block text-[11px] text-slate-600">e) Aut. Especial (si procede)</label>
                            <input type="text" id="autorizacion_especial" placeholder="Nº de autorización especial de tráfico" class="w-full border p-1 rounded text-xs">
                        </div>

                        <div>
                            <label class="block text-[11px] text-slate-600">h) Observaciones / Reservas</label>
                            <textarea id="observaciones" rows="2" placeholder="Observaciones, reservas o instrucciones particulares..." class="w-full border p-1 rounded text-xs"></textarea>
                        </div>

                        <button type="submit" class="w-full bg-slate-800 hover:bg-slate-900 text-white font-medium py-2 rounded text-xs transition mt-2">
                            Emitir y Enviar DeCA
                        </button>
                    </form>
                </div>

                <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200 lg:col-span-2 flex flex-col">
                    <div class="flex justify-between items-center mb-4 border-b pb-2">
                        <h2 class="text-base font-bold text-slate-800">Documentos Emitidos</h2>
                        <input type="text" id="search-input" onkeyup="filterDecas()" placeholder="Buscar por matrícula, cargador, fecha..." class="border px-3 py-1 text-xs rounded-md w-64 focus:outline-none focus:ring-1 focus:ring-blue-500">
                    </div>
                    <div class="overflow-x-auto flex-1">
                        <table class="w-full text-left border-collapse">
                            <thead>
                                <tr class="text-xs font-semibold text-slate-500 border-b bg-slate-50">
                                    <th class="p-2">Código DeCA</th>
                                    <th class="p-2">Cargador / Efectivo</th>
                                    <th class="p-2">Matrícula</th>
                                    <th class="p-2">Fecha Porte</th>
                                    <th class="p-2 text-right">Acción</th>
                                </tr>
                            </thead>
                            <tbody id="deca-list" class="text-xs divide-y divide-slate-100"></tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>

        <script>
            let allDocuments = [];

            document.addEventListener("DOMContentLoaded", () => {{
                const token = localStorage.getItem("deca_token");
                if (token) {{ showAppScreen(); }}
            }});

            async function handleLogin(event) {{
                event.preventDefault();
                const errorDiv = document.getElementById("login-error");
                errorDiv.classList.add("hidden");

                const formData = new URLSearchParams();
                formData.append("username", document.getElementById("username").value);
                formData.append("password", document.getElementById("password").value);

                try {{
                    const response = await fetch("/api/v1/auth/login", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
                        body: formData
                    }});

                    if (!response.ok) {{
                        const data = await response.json();
                        throw new Error(data.detail || "Error al iniciar sesión");
                    }}

                    const data = await response.json();
                    localStorage.setItem("deca_token", data.access_token);
                    showAppScreen();
                }} catch (err) {{
                    errorDiv.innerText = err.message;
                    errorDiv.classList.remove("hidden");
                }}
            }}

            function handleLogout() {{
                localStorage.removeItem("deca_token");
                document.getElementById("app-screen").classList.add("hidden");
                document.getElementById("login-screen").classList.remove("hidden");
            }}

            function showAppScreen() {{
                document.getElementById("login-screen").classList.add("hidden");
                document.getElementById("app-screen").classList.remove("hidden");
                loadDecas();
            }}

            async function loadDecas() {{
                const token = localStorage.getItem("deca_token");
                try {{
                    const response = await fetch("/api/v1/deca", {{
                        headers: {{ "Authorization": `Bearer ${{token}}` }}
                    }});

                    if (response.status === 401) {{
                        handleLogout();
                        return;
                    }}

                    allDocuments = await response.json();
                    renderDecaTable(allDocuments);
                }} catch (err) {{
                    console.error("Error al cargar listado DeCA:", err);
                }}
            }}

            function renderDecaTable(documents) {{
                const tbody = document.getElementById("deca-list");
                tbody.innerHTML = "";

                if (documents.length === 0) {{
                    tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-400 italic">No se encontraron documentos.</td></tr>`;
                    return;
                }}

                documents.forEach(doc => {{
                    const tr = document.createElement("tr");
                    tr.className = "hover:bg-slate-50";
                    
                    tr.innerHTML = `
                        <td class="p-2 font-semibold">
                            <a href="/view/deca/${{doc.codigo_deca}}" target="_blank" class="text-blue-600 hover:underline">
                                ${{doc.codigo_deca}}
                            </a>
                        </td>
                        <td class="p-2 text-slate-700">
                            <div class="font-medium">${{doc.cargador_nombre}}</div>
                            <div class="text-[10px] text-slate-400">${{doc.transportista_nombre}}</div>
                        </td>
                        <td class="p-2 font-mono text-slate-800">${{doc.matricula}}</td>
                        <td class="p-2 text-slate-700">${{doc.fecha_transporte}}</td>
                        <td class="p-2 text-right">
                            <a href="/view/deca/${{doc.codigo_deca}}" target="_blank" class="bg-blue-50 text-blue-600 hover:bg-blue-100 border border-blue-200 px-2.5 py-1 rounded text-[11px] font-medium transition inline-block">
                                Descargar PDF
                            </a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                }});
            }}

            function filterDecas() {{
                const query = document.getElementById("search-input").value.toLowerCase().trim();
                if (!query) {{
                    renderDecaTable(allDocuments);
                    return;
                }}

                const filtered = allDocuments.filter(doc => {{
                    return (
                        doc.codigo_deca.toLowerCase().includes(query) ||
                        doc.cargador_nombre.toLowerCase().includes(query) ||
                        doc.transportista_nombre.toLowerCase().includes(query) ||
                        doc.matricula.toLowerCase().includes(query) ||
                        doc.fecha_transporte.toLowerCase().includes(query) ||
                        doc.origen_lugar.toLowerCase().includes(query) ||
                        doc.destino_lugar.toLowerCase().includes(query)
                    );
                }});

                renderDecaTable(filtered);
            }}

            async function handleCreateDeca(event) {{
                event.preventDefault();
                const token = localStorage.getItem("deca_token");

                const payload = {{
                    cargador_nombre: document.getElementById("cargador_nombre").value,
                    cargador_nif: document.getElementById("cargador_nif").value,
                    cargador_domicilio: document.getElementById("cargador_domicilio").value,
                    transportista_nombre: document.getElementById("transportista_nombre").value,
                    transportista_nif: document.getElementById("transportista_nif").value,
                    transportista_email: document.getElementById("transportista_email").value || null,
                    origen_lugar: document.getElementById("origen_lugar").value,
                    destino_lugar: document.getElementById("destino_lugar").value,
                    fecha_transporte: document.getElementById("fecha_transporte").value,
                    mercancia_descripcion: document.getElementById("mercancia_descripcion").value,
                    peso_kg: document.getElementById("peso_kg").value,
                    matricula: document.getElementById("matricula").value,
                    remolque: document.getElementById("remolque").value || null,
                    autorizacion_especial: document.getElementById("autorizacion_especial").value || null,
                    observaciones: document.getElementById("observaciones").value || null
                }};

                try {{
                    const response = await fetch("/api/v1/deca", {{
                        method: "POST",
                        headers: {{
                            "Content-Type": "application/json",
                            "Authorization": `Bearer ${{token}}`
                        }},
                        body: JSON.stringify(payload)
                    }});

                    if (response.ok) {{
                        loadDecas();
                    }} else {{
                        const errData = await response.json();
                        alert("Error al guardar: " + JSON.stringify(errData.detail || errData));
                    }}
                }} catch (err) {{
                    console.error("Error al crear documento:", err);
                }}
            }}
        </script>
    </body>
    </html>
    '''
    return HTMLResponse(content=html_content)