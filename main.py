import os
import json
import sqlite3
import qrcode
import smtplib
import jwt
from datetime import datetime, timedelta
from typing import List, Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel
from fpdf import FPDF
from passlib.context import CryptContext

app = FastAPI(title="DeCA API - Documento de Control de Transporte")

DB_PATH = "deca.db"
SECRET_KEY = os.environ.get("JWT_SECRET", "clave_secreta_deca_2026")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decas (
            codigo TEXT PRIMARY KEY,
            cargador TEXT,
            cargador_nif TEXT,
            cargador_dir TEXT,
            cargador_pob TEXT,
            transportista TEXT,
            transportista_nif TEXT,
            transportista_email TEXT,
            matricula_tractor TEXT,
            matricula_remolque TEXT,
            fecha_servicio TEXT,
            envios_json TEXT,
            adr TEXT,
            observaciones TEXT,
            modificaciones_json TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT DEFAULT 'transportista'
        )
    """)
    
    # Crear usuario administrador por defecto si no existe ninguno
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", ("admin@deca.com",))
    if not cursor.fetchone():
        hashed = hash_password("admin1234")
        cursor.execute(
            "INSERT INTO usuarios (email, password_hash, nombre, rol) VALUES (?, ?, ?, ?)",
            ("admin@deca.com", hashed, "Administrador", "admin")
        )
    
    conn.commit()
    conn.close()

init_db()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def crear_token_acceso(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def obtener_usuario_actual(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de acceso no proporcionado")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

class UsuarioRegistro(BaseModel):
    email: str
    password: str
    nombre: str
    rol: Optional[str] = "transportista"

class UsuarioLogin(BaseModel):
    email: str
    password: str

class Envio(BaseModel):
    origen: str
    destino: str
    mercancia: str
    bultos: Optional[str] = "-"
    peso: Optional[str] = "-"

class DECARequest(BaseModel):
    codigo: str
    cargador: str
    cargador_nif: str
    cargador_dir: str = "-"
    cargador_pob: str = "-"
    transportista: str
    transportista_nif: str
    transportista_email: str = ""
    matricula_tractor: str
    matricula_remolque: str = "-"
    fecha_servicio: str
    envios: List[Envio]
    adr: str = "No aplica"
    observaciones: str = "-"
    motivo_modificacion: Optional[str] = None

@app.post("/api/v1/auth/registro")
def registrar_usuario(usuario: UsuarioRegistro):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (usuario.email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    hashed = hash_password(usuario.password)
    cursor.execute("INSERT INTO usuarios (email, password_hash, nombre, rol) VALUES (?, ?, ?, ?)",
                   (usuario.email, hashed, usuario.nombre, usuario.rol))
    conn.commit()
    conn.close()
    return {"status": "ok", "mensaje": "Usuario registrado correctamente"}

@app.post("/api/v1/auth/login")
def login(datos: UsuarioLogin):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash, nombre, rol FROM usuarios WHERE email = ?", (datos.email,))
    user = cursor.fetchone()
    conn.close()
    if not user or not verify_password(datos.password, user[1]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = crear_token_acceso({"sub": datos.email, "nombre": user[2], "rol": user[3]})
    return {"access_token": token, "token_type": "bearer", "nombre": user[2], "rol": user[3]}

def enviar_email_pdf(destinatario: str, codigo: str, pdf_bytes: bytes):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    if not smtp_user or not smtp_password:
        return
    mensaje = MIMEMultipart()
    mensaje["From"] = smtp_user
    mensaje["To"] = destinatario
    mensaje["Subject"] = f"Documento de Control de Transporte (DeCA) - {codigo}"
    cuerpo = f"Estimado/a,\n\nAdjunto se remite el Documento de Control Administrativo en el Transporte (DeCA) correspondiente al código {codigo}.\n\nUn saludo."
    mensaje.attach(MIMEText(cuerpo, "plain"))
    adjunto = MIMEApplication(pdf_bytes, _subtype="pdf")
    adjunto.add_header("Content-Disposition", "attachment", filename=f"{codigo}.pdf")
    mensaje.attach(adjunto)
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(mensaje)
        server.quit()
    except Exception as e:
        print(f"Error enviando correo: {e}")

def guardar_deca_db(data: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT envios_json, modificaciones_json FROM decas WHERE codigo = ?", (data.get("codigo"),))
    existente = cursor.fetchone()
    modificaciones = json.loads(existente[1]) if existente and existente[1] else []
    if existente and data.get("motivo_modificacion"):
        modificaciones.append({
            "fecha_mod": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "motivo": data.get("motivo_modificacion"),
            "envios_previos": existente[0]
        })
    cursor.execute("""
        INSERT OR REPLACE INTO decas 
        (codigo, cargador, cargador_nif, cargador_dir, cargador_pob, transportista, transportista_nif, transportista_email,
         matricula_tractor, matricula_remolque, fecha_servicio, envios_json, adr, observaciones, modificaciones_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("codigo"), data.get("cargador"), data.get("cargador_nif"), data.get("cargador_dir"),
        data.get("cargador_pob"), data.get("transportista"), data.get("transportista_nif"), data.get("transportista_email"),
        data.get("matricula_tractor"), data.get("matricula_remolque"), data.get("fecha_servicio"),
        json.dumps(data.get("envios")), data.get("adr"), data.get("observaciones"), json.dumps(modificaciones)
    ))
    conn.commit()
    conn.close()

def obtener_deca_db(codigo: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decas WHERE codigo = ?", (codigo,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "codigo": row[0], "cargador": row[1], "cargador_nif": row[2], "cargador_dir": row[3],
        "cargador_pob": row[4], "transportista": row[5], "transportista_nif": row[6], "transportista_email": row[7],
        "matricula_tractor": row[8], "matricula_remolque": row[9], "fecha_servicio": row[10],
        "envios": json.loads(row[11]) if row[11] else [], "adr": row[12], "observaciones": row[13],
        "modificaciones": json.loads(row[14]) if row[14] else []
    }

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
    pdf.set_font("Helvetica", style="B", size=13)
    pdf.cell(0, 6, "DOCUMENTO DE CONTROL ADMINISTRATIVO EN EL TRANSPORTE (DeCA)", ln=True, align="C")
    pdf.set_font("Helvetica", size=8)
    pdf.cell(0, 4, "Orden FOM/2861/2012 y Ley 16/1987 (LOTT)", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", style="B", size=9)
    pdf.cell(140, 28, f" CÓDIGO DOCUMENTO: {deca_data.get('codigo')}  |  FECHA SERVICIO: {deca_data.get('fecha_servicio')}", border=1, ln=False)
    x_qr, y_qr = pdf.get_x(), pdf.get_y()
    pdf.cell(50, 28, "", border=1, ln=True)
    if os.path.exists(qr_path):
        pdf.image(qr_path, x=x_qr + 11, y=y_qr + 1, w=26, h=26)
    pdf.ln(4)

    def seccion_titulo(texto):
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.cell(0, 5, f" {texto}", border=1, ln=True, fill=True)

    def campo_doble(lbl1, val1, lbl2, val2):
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.cell(32, 5, f" {lbl1}:", border="LBT", ln=False)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(63, 5, f"{val1}", border="RBT", ln=False)
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.cell(32, 5, f" {lbl2}:", border="LBT", ln=False)
        pdf.set_font("Helvetica", size=8)
        pdf.cell(63, 5, f"{val2}", border="RBT", ln=True)

    seccion_titulo("1. CARGADOR CONTRACTUAL / REMITENTE")
    campo_doble("Nombre / Razón", deca_data.get("cargador", "-"), "NIF / CIF", deca_data.get("cargador_nif", "-"))
    campo_doble("Domicilio", deca_data.get("cargador_dir", "-"), "Localidad / CP", deca_data.get("cargador_pob", "-"))
    pdf.ln(2)

    seccion_titulo("2. TRANSPORTISTA EFECTIVO")
    campo_doble("Nombre / Razón", deca_data.get("transportista", "-"), "NIF / CIF", deca_data.get("transportista_nif", "-"))
    campo_doble("Matrícula Tractor", deca_data.get("matricula_tractor", "-"), "Matrícula Remolque", deca_data.get("matricula_remolque", "-"))
    pdf.ln(2)

    envios = deca_data.get("envios", [])
    seccion_titulo(f"3. DETALLE DE ENVÍOS AGRUPADOS (TOTAL: {len(envios)})")
    for idx, env in enumerate(envios, 1):
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.cell(0, 4, f" Envío #{idx}", border="LTR", ln=True)
        campo_doble("Origen", env.get("origen", "-"), "Destino", env.get("destino", "-"))
        campo_doble("Mercancía", env.get("mercancia", "-"), "Bultos / Peso", f"{env.get('bultos', '-')} / {env.get('peso', '-')}")
    pdf.ln(2)

    seccion_titulo("4. OBSERVACIONES, CLASE ADR Y ESTIBA")
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell(0, 6, f" Clase ADR: {deca_data.get('adr', 'No aplica')} | Observaciones: {deca_data.get('observaciones', '-')}", border=1)
    pdf.ln(2)

    modifs = deca_data.get("modificaciones", [])
    if modifs:
        seccion_titulo("5. HISTORIAL DE MODIFICACIONES EN CURSO (TRAZABILIDAD)")
        for m in modifs:
            pdf.set_font("Helvetica", style="7")
            pdf.multi_cell(0, 4, f" Modificado el {m.get('fecha_mod')} - Motivo: {m.get('motivo')}", border=1)
        pdf.ln(2)

    pdf.set_font("Helvetica", style="I", size=7)
    pdf.cell(0, 4, "Documento de Control de Transporte emitido de conformidad con la Orden FOM/2861/2012.", ln=True, align="C")
    return bytes(pdf.output())

@app.post("/api/v1/deca")
def crear_deca(req: DECARequest, usuario: dict = Depends(obtener_usuario_actual)):
    data = req.dict()
    guardar_deca_db(data)
    url_descarga = f"https://deca-api.onrender.com/api/v1/deca/{req.codigo}/pdf"
    pdf_bytes = generar_pdf_deca(data, url_descarga)
    if req.transportista_email:
        enviar_email_pdf(req.transportista_email, req.codigo, pdf_bytes)
    return {"status": "ok", "codigo": req.codigo, "pdf_url": f"/api/v1/deca/{req.codigo}/pdf"}

@app.get("/api/v1/deca/listado")
def listar_decas(usuario: dict = Depends(obtener_usuario_actual)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, cargador, transportista, matricula_tractor, matricula_remolque, fecha_servicio, envios_json FROM decas ORDER BY rowid DESC")
    rows = cursor.fetchall()
    conn.close()
    resultados = []
    for r in rows:
        envios = json.loads(r[6]) if r[6] else []
        origen_dest = f"{envios[0].get('origen')} -> {envios[0].get('destino')}" if envios else "-"
        if len(envios) > 1:
            origen_dest += f" (+{len(envios)-1} más)"
        resultados.append({
            "codigo": r[0], "cargador": r[1], "transportista": r[2], "matricula_tractor": r[3],
            "matricula_remolque": r[4], "fecha_servicio": r[5], "ruta": origen_dest
        })
    return resultados

@app.get("/api/v1/deca/{codigo}/pdf")
def obtener_pdf(codigo: str):
    deca_data = obtener_deca_db(codigo)
    if not deca_data:
        raise HTTPException(status_code=404, detail="DeCA no encontrado")
    url_descarga = f"https://deca-api.onrender.com/api/v1/deca/{codigo}/pdf"
    pdf_bytes = generar_pdf_deca(deca_data, url_descarga)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename={codigo}.pdf"
    })

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_usuario():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Gestión DeCA - Panel de Control</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 text-gray-800 font-sans">
        
        <!-- Modal de Autenticación -->
        <div id="modal-auth" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white p-6 rounded-lg shadow-lg w-full max-w-md">
                <h2 id="modal-titulo" class="text-xl font-bold mb-4 text-gray-800">Iniciar Sesión</h2>
                <form id="form-auth" onsubmit="procesarAuth(event)" class="space-y-4">
                    <div id="campo-nombre" class="hidden">
                        <label class="block text-xs font-medium text-gray-700">Nombre</label>
                        <input type="text" id="auth-nombre" class="w-full p-2 border rounded text-xs mt-1">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-700">Correo Electrónico</label>
                        <input type="email" id="auth-email" class="w-full p-2 border rounded text-xs mt-1" required>
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-700">Contraseña</label>
                        <input type="password" id="auth-password" class="w-full p-2 border rounded text-xs mt-1" required>
                    </div>
                    <button type="submit" id="btn-auth-submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded text-xs transition">
                        Entrar
                    </button>
                </form>
                <div class="mt-4 text-center">
                    <button type="button" onclick="alternarModoAuth()" id="btn-auth-toggle" class="text-xs text-blue-600 hover:underline">
                        ¿No tienes cuenta? Regístrate aquí
                    </button>
                </div>
            </div>
        </div>

        <div class="max-w-7xl mx-auto p-6">
            <header class="flex justify-between items-center mb-6 bg-white p-6 rounded-lg shadow-sm">
                <div>
                    <h1 class="text-2xl font-bold text-gray-900">Panel de Control DeCA</h1>
                    <p class="text-sm text-gray-500">Gestión de documentos de control de transporte con agrupación y modificaciones en curso</p>
                </div>
                <div id="usuario-info" class="text-right">
                    <span id="user-display" class="text-xs font-semibold text-gray-700 block"></span>
                    <button onclick="cerrarSesion()" class="text-xs text-red-600 hover:underline">Cerrar Sesión</button>
                </div>
            </header>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Formulario DeCA -->
                <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                    <h2 class="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b" id="titulo-form">Emitir Nuevo DeCA</h2>
                    <form id="form-deca" class="space-y-4">
                        <div class="grid grid-cols-2 gap-2">
                            <div>
                                <label class="block text-xs font-medium text-gray-700">Código DeCA</label>
                                <input type="text" id="codigo" class="w-full mt-1 p-2 border rounded bg-gray-50 text-xs font-bold text-blue-600" readonly>
                            </div>
                            <div>
                                <label class="block text-xs font-medium text-gray-700">Fecha Servicio</label>
                                <input type="date" id="fecha_servicio" class="w-full mt-1 p-2 border rounded text-xs" required>
                            </div>
                        </div>

                        <!-- Cargador -->
                        <div class="space-y-2 pt-1">
                            <span class="text-xs font-bold text-gray-500 uppercase">1. Cargador Contractual</span>
                            <input type="text" id="cargador" placeholder="Razón Social Cargador" class="w-full p-2 border rounded text-xs" required>
                            <input type="text" id="cargador_nif" placeholder="NIF/CIF Cargador" class="w-full p-2 border rounded text-xs" required>
                            <input type="text" id="cargador_dir" placeholder="Domicilio" class="w-full p-2 border rounded text-xs">
                            <input type="text" id="cargador_pob" placeholder="Localidad / CP" class="w-full p-2 border rounded text-xs">
                        </div>

                        <!-- Transportista -->
                        <div class="space-y-2 pt-1">
                            <span class="text-xs font-bold text-gray-500 uppercase">2. Transportista Efectivo</span>
                            <input type="text" id="transportista" placeholder="Razón Social Transportista" class="w-full p-2 border rounded text-xs" required>
                            <input type="text" id="transportista_nif" placeholder="NIF/CIF Transportista" class="w-full p-2 border rounded text-xs" required>
                            <input type="email" id="transportista_email" placeholder="Email del Transportista" class="w-full p-2 border rounded text-xs">
                            <div class="grid grid-cols-2 gap-2">
                                <input type="text" id="matricula_tractor" placeholder="Matrícula Tractor" class="p-2 border rounded text-xs" required>
                                <input type="text" id="matricula_remolque" placeholder="Matrícula Remolque" class="p-2 border rounded text-xs">
                            </div>
                        </div>

                        <!-- Contenedor Envíos -->
                        <div class="pt-1">
                            <div class="flex justify-between items-center mb-2">
                                <span class="text-xs font-bold text-gray-500 uppercase">3. Envíos Agrupados</span>
                                <button type="button" onclick="agregarEnvio()" class="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200">+ Añadir Envío</button>
                            </div>
                            <div id="lista-envios" class="space-y-3"></div>
                        </div>

                        <!-- Observaciones -->
                        <div class="pt-1 space-y-2">
                            <span class="text-xs font-bold text-gray-500 uppercase">4. ADR y Observaciones</span>
                            <input type="text" id="adr" placeholder="Clase ADR" value="No aplica" class="w-full p-2 border rounded text-xs">
                            <textarea id="observaciones" rows="2" class="w-full p-2 border rounded text-xs" placeholder="Observaciones / Reservas"></textarea>
                        </div>

                        <!-- Modificación -->
                        <div id="bloque-modificacion" class="hidden pt-1 space-y-1 bg-yellow-50 p-2 border border-yellow-200 rounded">
                            <span class="text-xs font-bold text-yellow-800 uppercase">Motivo de Modificación (Orden en curso)</span>
                            <input type="text" id="motivo_modificacion" placeholder="Ej: Cambio de lugar de entrega en tránsito" class="w-full p-2 border rounded text-xs">
                        </div>

                        <button type="button" onclick="emitirDECA()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded text-xs transition">
                            Guardar y Generar PDF
                        </button>
                    </form>
                </div>

                <!-- Histórico -->
                <div class="lg:col-span-2 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                    <div class="flex flex-col sm:flex-row justify-between items-center mb-6 gap-4">
                        <h2 class="text-lg font-semibold text-gray-800">Histórico de Documentos</h2>
                        <input type="text" id="buscador" onkeyup="filtrarTabla()" placeholder="Buscar código, cargador, tractor, remolque..." class="w-full sm:w-64 p-2 border rounded text-xs">
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs border-collapse">
                            <thead>
                                <tr class="bg-gray-50 border-b text-gray-600 uppercase font-semibold">
                                    <th class="p-2">Fecha</th>
                                    <th class="p-2">Código</th>
                                    <th class="p-2">Cargador / Transportista</th>
                                    <th class="p-2">Vehículos</th>
                                    <th class="p-2">Ruta(s)</th>
                                    <th class="p-2 text-center">Acciones</th>
                                </tr>
                            </thead>
                            <tbody id="tabla-historico" class="divide-y"></tbody>
                        </table>
                    </div>
                </div>

            </div>
        </div>

        <script>
            let esModificacion = false;
            let esModoRegistro = false;
            let token = localStorage.getItem('deca_token');

            function fHoy() { return new Date().toISOString().split('T')[0]; }

            function alternarModoAuth() {
                esModoRegistro = !esModoRegistro;
                document.getElementById('modal-titulo').innerText = esModoRegistro ? "Registro de Usuario" : "Iniciar Sesión";
                document.getElementById('btn-auth-submit').innerText = esModoRegistro ? "Registrarse" : "Entrar";
                document.getElementById('btn-auth-toggle').innerText = esModoRegistro ? "¿Ya tienes cuenta? Inicia sesión" : "¿No tienes cuenta? Regístrate aquí";
                document.getElementById('campo-nombre').classList.toggle('hidden', !esModoRegistro);
            }

            async function procesarAuth(e) {
                e.preventDefault();
                const email = document.getElementById('auth-email').value;
                const password = document.getElementById('auth-password').value;
                const url = esModoRegistro ? '/api/v1/auth/registro' : '/api/v1/auth/login';
                
                const body = { email, password };
                if (esModoRegistro) body.nombre = document.getElementById('auth-nombre').value;

                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });

                if (res.ok) {
                    if (esModoRegistro) {
                        alert('Usuario creado correctamente. Ya puedes iniciar sesión.');
                        alternarModoAuth();
                    } else {
                        const data = await res.json();
                        token = data.access_token;
                        localStorage.setItem('deca_token', token);
                        localStorage.setItem('deca_user', data.nombre);
                        iniciarVista();
                    }
                } else {
                    const err = await res.json();
                    alert(err.detail || 'Error al autenticar');
                }
            }

            function cerrarSesion() {
                localStorage.removeItem('deca_token');
                localStorage.removeItem('deca_user');
                location.reload();
            }

            function comprobarSesion() {
                if (!token) {
                    document.getElementById('modal-auth').classList.remove('hidden');
                } else {
                    document.getElementById('modal-auth').classList.add('hidden');
                    document.getElementById('user-display').innerText = "Sesión: " + (localStorage.getItem('deca_user') || 'Usuario');
                    cargarHistorico();
                }
            }

            function nuevoCodigo() {
                esModificacion = false;
                document.getElementById('bloque-modificacion').classList.add('hidden');
                document.getElementById('titulo-form').innerText = "Emitir Nuevo DeCA";
                const fecha = new Date();
                const codigo = "DECA-" + fecha.getFullYear() + (fecha.getMonth()+1).toString().padStart(2, '0') + fecha.getDate().toString().padStart(2, '0') + "-" + Math.floor(1000 + Math.random() * 9000);
                document.getElementById('codigo').value = codigo;
                document.getElementById('fecha_servicio').value = fHoy();
                document.getElementById('lista-envios').innerHTML = '';
                agregarEnvio();
            }

            function agregarEnvio(origen="", destino="", mercancia="", bultos="-", peso="-") {
                const id = Date.now() + Math.random();
                const html = `
                    <div class="p-2 border rounded bg-gray-50 space-y-1 relative" id="envio-${id}">
                        <div class="grid grid-cols-2 gap-1">
                            <input type="text" class="env-origen p-1 border rounded text-xs" placeholder="Origen" value="${origen}" required>
                            <input type="text" class="env-destino p-1 border rounded text-xs" placeholder="Destino" value="${destino}" required>
                        </div>
                        <input type="text" class="env-mercancia p-1 border rounded text-xs w-full" placeholder="Mercancía" value="${mercancia}" required>
                        <div class="grid grid-cols-2 gap-1">
                            <input type="text" class="env-bultos p-1 border rounded text-xs" placeholder="Bultos" value="${bultos}">
                            <input type="text" class="env-peso p-1 border rounded text-xs" placeholder="Peso" value="${peso}">
                        </div>
                    </div>
                `;
                document.getElementById('lista-envios').insertAdjacentHTML('beforeend', html);
            }

            async function cargarHistorico() {
                if (!token) return;
                const res = await fetch('/api/v1/deca/listado', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (res.status === 401) { cerrarSesion(); return; }
                const datos = await res.json();
                const tbody = document.getElementById('tabla-historico');
                tbody.innerHTML = '';
                datos.forEach(d => {
                    const fila = `
                        <tr class="hover:bg-gray-50">
                            <td class="p-2 font-medium">${d.fecha_servicio || '-'}</td>
                            <td class="p-2 font-bold text-blue-600">${d.codigo}</td>
                            <td class="p-2">
                                <div class="font-semibold">${d.cargador}</div>
                                <div class="text-gray-400">${d.transportista}</div>
                            </td>
                            <td class="p-2">
                                <div>T: ${d.matricula_tractor}</div>
                                <div class="text-gray-500">R: ${d.matricula_remolque || '-'}</div>
                            </td>
                            <td class="p-2">${d.ruta}</td>
                            <td class="p-2 text-center space-x-1">
                                <a href="/api/v1/deca/${d.codigo}/pdf" target="_blank" class="inline-block bg-gray-800 text-white px-2 py-1 rounded hover:bg-black">PDF</a>
                                <button onclick='modificarOrden("${d.codigo}")' class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded hover:bg-yellow-200">Modificar</button>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += fila;
                });
            }

            async function emitirDECA() {
                if (!token) { alert('Debes iniciar sesión.'); return; }
                const enviosBlocks = document.querySelectorAll('#lista-envios > div');
                const envios = [];
                enviosBlocks.forEach(b => {
                    envios.push({
                        origen: b.querySelector('.env-origen').value,
                        destino: b.querySelector('.env-destino').value,
                        mercancia: b.querySelector('.env-mercancia').value,
                        bultos: b.querySelector('.env-bultos').value,
                        peso: b.querySelector('.env-peso').value
                    });
                });

                const payload = {
                    codigo: document.getElementById('codigo').value,
                    fecha_servicio: document.getElementById('fecha_servicio').value,
                    cargador: document.getElementById('cargador').value,
                    cargador_nif: document.getElementById('cargador_nif').value,
                    cargador_dir: document.getElementById('cargador_dir').value,
                    cargador_pob: document.getElementById('cargador_pob').value,
                    transportista: document.getElementById('transportista').value,
                    transportista_nif: document.getElementById('transportista_nif').value,
                    transportista_email: document.getElementById('transportista_email').value,
                    matricula_tractor: document.getElementById('matricula_tractor').value,
                    matricula_remolque: document.getElementById('matricula_remolque').value,
                    adr: document.getElementById('adr').value,
                    observaciones: document.getElementById('observaciones').value,
                    envios: envios,
                    motivo_modificacion: esModificacion ? document.getElementById('motivo_modificacion').value : null
                };

                const res = await fetch('/api/v1/deca', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    window.open(`/api/v1/deca/${payload.codigo}/pdf`, '_blank');
                    nuevoCodigo();
                    cargarHistorico();
                } else {
                    alert('Error al guardar el DeCA.');
                }
            }

            function modificarOrden(codigo) {
                esModificacion = true;
                document.getElementById('codigo').value = codigo;
                document.getElementById('bloque-modificacion').classList.remove('hidden');
                document.getElementById('titulo-form').innerText = "Modificar DeCA en Curso (" + codigo + ")";
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function filtrarTabla() {
                const query = document.getElementById('buscador').value.toLowerCase();
                const filas = document.querySelectorAll('#tabla-historico tr');
                filas.forEach(f => {
                    f.style.display = f.innerText.toLowerCase().includes(query) ? '' : 'none';
                });
            }

            function iniciarVista() {
                nuevoCodigo();
                comprobarSesion();
            }

            iniciarVista();
        </script>
    </body>
    </html>
    """