import os
import sqlite3
import qrcode
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel
from fpdf import FPDF

app = FastAPI(title="DeCA API - Documento de Control de Transporte")

DB_PATH = "deca.db"

# --- INICIALIZACIÓN DE BASE DE DATOS ---
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
            matricula_tractor TEXT,
            matricula_remolque TEXT,
            origen TEXT,
            fecha_salida TEXT,
            destino TEXT,
            fecha_entrega TEXT,
            mercancia TEXT,
            bultos TEXT,
            peso TEXT,
            adr TEXT,
            observaciones TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- MODELO DE DATOS ENTRADA ---
class DECARequest(BaseModel):
    codigo: str
    cargador: str
    cargador_nif: str
    cargador_dir: str = "-"
    cargador_pob: str = "-"
    transportista: str
    transportista_nif: str
    matricula_tractor: str
    matricula_remolque: str = "-"
    origen: str
    fecha_salida: str
    destino: str
    fecha_entrega: str
    mercancia: str
    bultos: str = "-"
    peso: str = "-"
    adr: str = "No aplica"
    observaciones: str = "-"

def guardar_deca_db(data: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO decas 
        (codigo, cargador, cargador_nif, cargador_dir, cargador_pob, transportista, transportista_nif, 
         matricula_tractor, matricula_remolque, origen, fecha_salida, destino, fecha_entrega, 
         mercancia, bultos, peso, adr, observaciones)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("codigo"), data.get("cargador"), data.get("cargador_nif"), data.get("cargador_dir"),
        data.get("cargador_pob"), data.get("transportista"), data.get("transportista_nif"),
        data.get("matricula_tractor"), data.get("matricula_remolque"), data.get("origen"),
        data.get("fecha_salida"), data.get("destino"), data.get("fecha_entrega"),
        data.get("mercancia"), data.get("bultos"), data.get("peso"),
        data.get("adr"), data.get("observaciones")
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
    
    columnas = ["codigo", "cargador", "cargador_nif", "cargador_dir", "cargador_pob", "transportista", 
                "transportista_nif", "matricula_tractor", "matricula_remolque", "origen", "fecha_salida", 
                "destino", "fecha_entrega", "mercancia", "bultos", "peso", "adr", "observaciones"]
    return dict(zip(columnas, row))

# --- GENERADOR DE PDF ---
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
    pdf.cell(0, 4, "Orden FOM/2861/2012 y Ley 16/1987 de Ordenación de los Transportes Terrestres (LOTT)", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", style="B", size=10)
    pdf.cell(140, 30, f" CÓDIGO DE DOCUMENTO: {deca_data.get('codigo', 'DECA-001')}", border=1, ln=False)
    
    x_qr = pdf.get_x()
    y_qr = pdf.get_y()
    pdf.cell(50, 30, "", border=1, ln=True) 
    
    if os.path.exists(qr_path):
        pdf.image(qr_path, x=x_qr + 11, y=y_qr + 1, w=28, h=28)
    
    pdf.ln(5)

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

    seccion_titulo("1. CARGADOR CONTRACTUAL / REMITENTE")
    campo_doble("Nombre / Razón", deca_data.get("cargador", "-"), "NIF / CIF", deca_data.get("cargador_nif", "-"))
    campo_doble("Domicilio", deca_data.get("cargador_dir", "-"), "Localidad / CP", deca_data.get("cargador_pob", "-"))
    pdf.ln(3)

    seccion_titulo("2. TRANSPORTISTA EFECTIVO")
    campo_doble("Nombre / Razón", deca_data.get("transportista", "-"), "NIF / CIF", deca_data.get("transportista_nif", "-"))
    campo_doble("Matrícula Tractor", deca_data.get("matricula_tractor", "-"), "Matrícula Remolque", deca_data.get("matricula_remolque", "-"))
    pdf.ln(3)

    seccion_titulo("3. LUGARES DE ORIGEN Y DESTINO")
    campo_doble("Lugar de Origen", deca_data.get("origen", "-"), "Fecha / Hora Salida", deca_data.get("fecha_salida", "-"))
    campo_doble("Lugar de Destino", deca_data.get("destino", "-"), "Fecha Prevista", deca_data.get("fecha_entrega", "-"))
    pdf.ln(3)

    seccion_titulo("4. DESCRIPCIÓN Y NATURALEZA DE LA MERCANCÍA")
    campo_doble("Descripción", deca_data.get("mercancia", "-"), "Nº de Bultos", deca_data.get("bultos", "-"))
    campo_doble("Peso Bruto", deca_data.get("peso", "-"), "Clase ADR", deca_data.get("adr", "-"))
    pdf.ln(3)

    seccion_titulo("5. OBSERVACIONES Y RESERVAS EN LA CARGA / ESTIBA")
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell(0, 10, f" {deca_data.get('observaciones', '-')}", border=1)
    pdf.ln(4)

    pdf.set_font("Helvetica", style="I", size=7)
    pdf.cell(0, 4, "Documento de Control de Transporte emitido de conformidad con la normativa de transportes.", ln=True, align="C")

    return bytes(pdf.output())

# --- ENDPOINTS API ---

@app.post("/api/v1/deca")
def crear_deca(req: DECARequest):
    data = req.dict()
    guardar_deca_db(data)
    return {"status": "ok", "codigo": req.codigo, "pdf_url": f"/api/v1/deca/{req.codigo}/pdf"}

@app.get("/api/v1/deca/listado")
def listar_decas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, cargador, cargador_nif, cargador_dir, cargador_pob, transportista, transportista_nif, matricula_tractor, matricula_remolque, origen, fecha_salida, destino, fecha_entrega, mercancia, bultos, peso, adr, observaciones FROM decas ORDER BY rowid DESC")
    columnas = [column[0] for column in cursor.description]
    resultados = [dict(zip(columnas, row)) for row in cursor.fetchall()]
    conn.close()
    return resultados

@app.get("/api/v1/deca/{codigo}/pdf")
def obtener_pdf(codigo: str):
    deca_data = obtener_deca_db(codigo)
    if not deca_data:
        # Registro por defecto para pruebas
        deca_data = {
            "codigo": codigo,
            "cargador": "Logística Codecar S.L.",
            "cargador_nif": "B12345678",
            "cargador_dir": "Pol. Ind. Sabón, Av. Principal 12",
            "cargador_pob": "15172 Arteixo (A Coruña)",
            "transportista": "Transportes Ejemplo S.L.",
            "transportista_nif": "B87654321",
            "matricula_tractor": "1234-BBB",
            "matricula_remolque": "R-5678-BBB",
            "origen": "Madrid (Centro Logístico)",
            "fecha_salida": "13/09/2026 18:30",
            "destino": "Vigo (Zona Franca)",
            "fecha_entrega": "14/09/2026 08:00",
            "mercancia": "Paquetería industrial / Piezas recambio",
            "bultos": "12 Palets",
            "peso": "4.250 kg",
            "adr": "No aplica",
            "observaciones": "Carga estibada y sujeta correctamente según normativa vigente."
        }

    url_descarga = f"https://deca-api.onrender.com/api/v1/deca/{codigo}/pdf"
    pdf_bytes = generar_pdf_deca(deca_data, url_descarga)
    
    return Response(content=pdf_bytes, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename={codigo}.pdf"
    })

# --- INTERFAZ WEB / DASHBOARD ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_usuario():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gestión DeCA - Panel de Agencia</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 text-gray-800 font-sans">
        <div class="max-w-7xl mx-auto p-6">
            <header class="flex justify-between items-center mb-8 bg-white p-6 rounded-lg shadow-sm">
                <div>
                    <h1 class="text-2xl font-bold text-gray-900">Panel de Control DeCA</h1>
                    <p class="text-sm text-gray-500">Gestión y emisión de documentos de control administrativo de transporte</p>
                </div>
            </header>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Formulario -->
                <div class="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                    <h2 class="text-lg font-semibold text-gray-800 mb-4 pb-2 border-b">Emitir Nuevo DeCA</h2>
                    <form id="form-deca" class="space-y-4">
                        <div>
                            <label class="block text-xs font-medium text-gray-700">Código DeCA</label>
                            <input type="text" id="codigo" class="w-full mt-1 p-2 border rounded bg-gray-50 text-sm font-bold text-blue-600" readonly>
                        </div>
                        <div class="space-y-2 pt-2">
                            <span class="text-xs font-bold text-gray-500 uppercase">1. Cargador Contractual</span>
                            <input type="text" id="cargador" placeholder="Razón Social Cargador" class="w-full p-2 border rounded text-sm" required>
                            <input type="text" id="cargador_nif" placeholder="NIF/CIF Cargador" class="w-full p-2 border rounded text-sm" required>
                            <input type="text" id="cargador_dir" placeholder="Domicilio" class="w-full p-2 border rounded text-sm">
                            <input type="text" id="cargador_pob" placeholder="Localidad / CP" class="w-full p-2 border rounded text-sm">
                        </div>
                        <div class="space-y-2 pt-2">
                            <span class="text-xs font-bold text-gray-500 uppercase">2. Transportista Efectivo</span>
                            <input type="text" id="transportista" placeholder="Razón Social Transportista" class="w-full p-2 border rounded text-sm" required>
                            <input type="text" id="transportista_nif" placeholder="NIF/CIF Transportista" class="w-full p-2 border rounded text-sm" required>
                            <div class="grid grid-cols-2 gap-2">
                                <input type="text" id="matricula_tractor" placeholder="Matrícula Tractor" class="p-2 border rounded text-sm" required>
                                <input type="text" id="matricula_remolque" placeholder="Matrícula Remolque" class="p-2 border rounded text-sm">
                            </div>
                        </div>
                        <div class="space-y-2 pt-2">
                            <span class="text-xs font-bold text-gray-500 uppercase">3. Ruta</span>
                            <div class="grid grid-cols-2 gap-2">
                                <input type="text" id="origen" placeholder="Origen" class="p-2 border rounded text-sm" required>
                                <input type="text" id="destino" placeholder="Destino" class="p-2 border rounded text-sm" required>
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <input type="text" id="fecha_salida" placeholder="Fecha/Hora Salida" class="p-2 border rounded text-sm" required>
                                <input type="text" id="fecha_entrega" placeholder="Fecha Prevista" class="p-2 border rounded text-sm" required>
                            </div>
                        </div>
                        <div class="space-y-2 pt-2">
                            <span class="text-xs font-bold text-gray-500 uppercase">4. Mercancía</span>
                            <input type="text" id="mercancia" placeholder="Descripción mercancía" class="w-full p-2 border rounded text-sm" required>
                            <div class="grid grid-cols-2 gap-2">
                                <input type="text" id="bultos" placeholder="Nº Bultos (ej. 12 Palets)" class="p-2 border rounded text-sm">
                                <input type="text" id="peso" placeholder="Peso (ej. 4250 kg)" class="p-2 border rounded text-sm">
                            </div>
                            <input type="text" id="adr" placeholder="Clase ADR" value="No aplica" class="w-full p-2 border rounded text-sm">
                        </div>
                        <div class="pt-2">
                            <span class="text-xs font-bold text-gray-500 uppercase">5. Observaciones</span>
                            <textarea id="observaciones" rows="2" class="w-full mt-1 p-2 border rounded text-sm" placeholder="Observaciones / Reservas"></textarea>
                        </div>
                        <button type="button" onclick="emitirDECA()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 rounded text-sm transition">
                            Generar y Emitir DeCA
                        </button>
                    </form>
                </div>

                <!-- Histórico -->
                <div class="lg:col-span-2 bg-white p-6 rounded-lg shadow-sm border border-gray-200">
                    <div class="flex flex-col sm:flex-row justify-between items-center mb-6 gap-4">
                        <h2 class="text-lg font-semibold text-gray-800">Histórico de Documentos</h2>
                        <input type="text" id="buscador" onkeyup="filtrarTabla()" placeholder="Buscar código, cargador, matrícula..." class="w-full sm:w-64 p-2 border rounded text-sm">
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs border-collapse">
                            <thead>
                                <tr class="bg-gray-50 border-b text-gray-600 uppercase font-semibold">
                                    <th class="p-3">Código</th>
                                    <th class="p-3">Cargador / Transportista</th>
                                    <th class="p-3">Ruta</th>
                                    <th class="p-3">Matrícula</th>
                                    <th class="p-3 text-center">Acciones</th>
                                </tr>
                            </thead>
                            <tbody id="tabla-historico" class="divide-y"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function nuevoCodigo() {
                const fecha = new Date();
                const codigo = "DECA-" + fecha.getFullYear() + (fecha.getMonth()+1).toString().padStart(2, '0') + fecha.getDate().toString().padStart(2, '0') + "-" + Math.floor(1000 + Math.random() * 9000);
                document.getElementById('codigo').value = codigo;
            }

            async function cargarHistorico() {
                const res = await fetch('/api/v1/deca/listado');
                const datos = await res.json();
                const tbody = document.getElementById('tabla-historico');
                tbody.innerHTML = '';
                datos.forEach(d => {
                    const fila = `
                        <tr class="hover:bg-gray-50">
                            <td class="p-3 font-bold text-blue-600">${d.codigo}</td>
                            <td class="p-3">
                                <div class="font-semibold">${d.cargador}</div>
                                <div class="text-gray-400">${d.transportista}</div>
                            </td>
                            <td class="p-3">${d.origen} &rarr; ${d.destino}</td>
                            <td class="p-3">${d.matricula_tractor}</td>
                            <td class="p-3 text-center space-x-2">
                                <a href="/api/v1/deca/${d.codigo}/pdf" target="_blank" class="inline-block bg-gray-800 text-white px-2 py-1 rounded hover:bg-black">PDF</a>
                                <button onclick='reutilizar("${encodeURIComponent(JSON.stringify(d))}")' class="bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200">Reutilizar</button>
                            </td>
                        </tr>
                    `;
                    tbody.innerHTML += fila;
                });
            }

            async function emitirDECA() {
                const payload = {
                    codigo: document.getElementById('codigo').value,
                    cargador: document.getElementById('cargador').value,
                    cargador_nif: document.getElementById('cargador_nif').value,
                    cargador_dir: document.getElementById('cargador_dir').value,
                    cargador_pob: document.getElementById('cargador_pob').value,
                    transportista: document.getElementById('transportista').value,
                    transportista_nif: document.getElementById('transportista_nif').value,
                    matricula_tractor: document.getElementById('matricula_tractor').value,
                    matricula_remolque: document.getElementById('matricula_remolque').value,
                    origen: document.getElementById('origen').value,
                    fecha_salida: document.getElementById('fecha_salida').value,
                    destino: document.getElementById('destino').value,
                    fecha_entrega: document.getElementById('fecha_entrega').value,
                    mercancia: document.getElementById('mercancia').value,
                    bultos: document.getElementById('bultos').value,
                    peso: document.getElementById('peso').value,
                    adr: document.getElementById('adr').value,
                    observaciones: document.getElementById('observaciones').value
                };

                const res = await fetch('/api/v1/deca', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    window.open(`/api/v1/deca/${payload.codigo}/pdf`, '_blank');
                    nuevoCodigo();
                    cargarHistorico();
                } else {
                    alert('Error al guardar el DeCA. Revisa los campos obligatorios.');
                }
            }

            function reutilizar(jsonStr) {
                const d = JSON.parse(decodeURIComponent(jsonStr));
                document.getElementById('cargador').value = d.cargador || '';
                document.getElementById('cargador_nif').value = d.cargador_nif || '';
                document.getElementById('cargador_dir').value = d.cargador_dir || '';
                document.getElementById('cargador_pob').value = d.cargador_pob || '';
                document.getElementById('transportista').value = d.transportista || '';
                document.getElementById('transportista_nif').value = d.transportista_nif || '';
                document.getElementById('matricula_tractor').value = d.matricula_tractor || '';
                document.getElementById('matricula_remolque').value = d.matricula_remolque || '';
                document.getElementById('origen').value = d.origen || '';
                document.getElementById('destino').value = d.destino || '';
                document.getElementById('mercancia').value = d.mercancia || '';
                document.getElementById('bultos').value = d.bultos || '';
                document.getElementById('peso').value = d.peso || '';
                document.getElementById('adr').value = d.adr || 'No aplica';
                document.getElementById('observaciones').value = d.observaciones || '';
                nuevoCodigo();
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function filtrarTabla() {
                const query = document.getElementById('buscador').value.toLowerCase();
                const filas = document.querySelectorAll('#tabla-historico tr');
                filas.forEach(f => {
                    const texto = f.innerText.toLowerCase();
                    f.style.display = texto.includes(query) ? '' : 'none';
                });
            }

            nuevoCodigo();
            cargarHistorico();
        </script>
    </body>
    </html>
    """