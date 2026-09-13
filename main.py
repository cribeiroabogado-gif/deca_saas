import os
import json
import sqlite3
import qrcode
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, HTMLResponse
from pydantic import BaseModel
from fpdf import FPDF

app = FastAPI(title="DeCA API - Documento de Control de Transporte")

DB_PATH = "deca.db"

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
            fecha_servicio TEXT,
            envios_json TEXT,
            adr TEXT,
            observaciones TEXT,
            modificaciones_json TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

class Envio(BaseModel):
    origen: str
    destino: str
    mercancia: str
    bultos: Optional[str] = "-"
    peso: Optional[str] = "-"

class Modificacion(BaseModel):
    fecha_mod: str
    motivo: str
    datos_anteriores: str

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
    fecha_servicio: str
    envios: List[Envio]
    adr: str = "No aplica"
    observaciones: str = "-"
    motivo_modificacion: Optional[str] = None

def guardar_deca_db(data: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Comprobar si existe para registrar trazabilidad de modificación (Método 1 de la norma)
    cursor.execute("SELECT envios_json, modificaciones_json FROM decas WHERE codigo = ?", (data.get("codigo"),))
    existente = cursor.fetchone()
    
    modificaciones = []
    if existente and existente[1]:
        modificaciones = json.loads(existente[1])
    
    if existente and data.get("motivo_modificacion"):
        modificaciones.append({
            "fecha_mod": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "motivo": data.get("motivo_modificacion"),
            "envios_previos": existente[0]
        })

    cursor.execute("""
        INSERT OR REPLACE INTO decas 
        (codigo, cargador, cargador_nif, cargador_dir, cargador_pob, transportista, transportista_nif, 
         matricula_tractor, matricula_remolque, fecha_servicio, envios_json, adr, observaciones, modificaciones_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("codigo"), data.get("cargador"), data.get("cargador_nif"), data.get("cargador_dir"),
        data.get("cargador_pob"), data.get("transportista"), data.get("transportista_nif"),
        data.get("matricula_tractor"), data.get("matricula_remolque"), data.get("fecha_servicio"),
        json.dumps(data.get("envios")), data.get("adr"), data.get("observaciones"),
        json.dumps(modificaciones)
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
        "cargador_pob": row[4], "transportista": row[5], "transportista_nif": row[6],
        "matricula_tractor": row[7], "matricula_remolque": row[8], "fecha_servicio": row[9],
        "envios": json.loads(row[10]) if row[10] else [], "adr": row[11], "observaciones": row[12],
        "modificaciones": json.loads(row[13]) if row[13] else []
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

    # Bloque superior
    pdf.set_font("Helvetica", style="B", size=9)
    pdf.cell(140, 28, f" CÓDIGO DOCUMENTO: {deca_data.get('codigo')}  |  FECHA SERVICIO: {deca_data.get('fecha_servicio')}", border=1, ln=False)
    
    x_qr = pdf.get_x()
    y_qr = pdf.get_y()
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

    # 1. Cargador
    seccion_titulo("1. CARGADOR CONTRACTUAL / REMITENTE")
    campo_doble("Nombre / Razón", deca_data.get("cargador", "-"), "NIF / CIF", deca_data.get("cargador_nif", "-"))
    campo_doble("Domicilio", deca_data.get("cargador_dir", "-"), "Localidad / CP", deca_data.get("cargador_pob", "-"))
    pdf.ln(2)

    # 2. Transportista
    seccion_titulo("2. TRANSPORTISTA EFECTIVO")
    campo_doble("Nombre / Razón", deca_data.get("transportista", "-"), "NIF / CIF", deca_data.get("transportista_nif", "-"))
    campo_doble("Matrícula Tractor", deca_data.get("matricula_tractor", "-"), "Matrícula Remolque", deca_data.get("matricula_remolque", "-"))
    pdf.ln(2)

    # 3. Agrupación de Envíos / Servicios (Punto Sexto Norma)
    envios = deca_data.get("envios", [])
    seccion_titulo(f"3. DETALLE DE ENVÍOS AGRUPADOS (TOTAL: {len(envios)})")
    
    for idx, env in enumerate(envios, 1):
        pdf.set_font("Helvetica", style="B", size=8)
        pdf.cell(0, 4, f" Envío #{idx}", border="LTR", ln=True)
        campo_doble("Origen", env.get("origen", "-"), "Destino", env.get("destino", "-"))
        campo_doble("Mercancía", env.get("mercancia", "-"), "Bultos / Peso", f"{env.get('bultos', '-')} / {env.get('peso', '-')}")
    pdf.ln(2)

    # 4. ADR y Observaciones
    seccion_titulo("4. OBSERVACIONES, CLASE ADR Y ESTIBA")
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell(0, 6, f" Clase ADR: {deca_data.get('adr', 'No aplica')} | Observaciones: {deca_data.get('observaciones', '-')}", border=1)
    pdf.ln(2)

    # 5. Control de Modificaciones durante el servicio (Punto Quinto Norma)
    modifs = deca_data.get("modificaciones", [])
    if modifs:
        seccion_titulo("5. HISTORIAL DE MODIFICACIONES EN CURSO (TRAZABILIDAD)")
        for m in modifs:
            pdf.set_font("Helvetica", size=7)
            pdf.multi_cell(0, 4, f" Modificado el {m.get('fecha_mod')} - Motivo: {m.get('motivo')}", border=1)
        pdf.ln(2)

    pdf.set_font("Helvetica", style="I", size=7)
    pdf.cell(0, 4, "Documento de Control de Transporte emitido de conformidad con la Orden FOM/2861/2012.", ln=True, align="C")

    return bytes(pdf.output())

@app.post("/api/v1/deca")
def crear_deca(req: DECARequest):
    data = req.dict()
    guardar_deca_db(data)
    return {"status": "ok", "codigo": req.codigo, "pdf_url": f"/api/v1/deca/{req.codigo}/pdf"}

@app.get("/api/v1/deca/listado")
def listar_decas():
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
            "codigo": r[0],
            "cargador": r[1],
            "transportista": r[2],
            "matricula_tractor": r[3],
            "matricula_remolque": r[4],
            "fecha_servicio": r[5],
            "ruta": origen_dest
        })
    return resultados

@app.get("/api/v1/deca/{codigo}/pdf")
def obtener_pdf(codigo: str):
    deca_data = obtener_deca_db(codigo)
    if not deca_data:
        deca_data = {
            "codigo": codigo,
            "cargador": "Logística Codecar S.L.",
            "cargador_nif": "B12345678",
            "cargador_dir": "Pol. Ind. Sabón, Av. Principal 12",
            "cargador_pob": "15172 Arteixo",
            "transportista": "Transportes Ejemplo S.L.",
            "transportista_nif": "B87654321",
            "matricula_tractor": "1234-BBB",
            "matricula_remolque": "R-5678-BBB",
            "fecha_servicio": datetime.now().strftime("%Y-%m-%d"),
            "envios": [{"origen": "Madrid", "destino": "Vigo", "mercancia": "Paquetería", "bultos": "12 Palets", "peso": "4200 kg"}],
            "adr": "No aplica",
            "observaciones": "Carga conforme.",
            "modificaciones": []
        }

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
        <div class="max-w-7xl mx-auto p-6">
            <header class="flex justify-between items-center mb-6 bg-white p-6 rounded-lg shadow-sm">
                <div>
                    <h1 class="text-2xl font-bold text-gray-900">Panel de Control DeCA</h1>
                    <p class="text-sm text-gray-500">Gestión de documentos de control de transporte con agrupación y modificaciones en curso</p>
                </div>
            </header>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Formulario -->
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
                            <div class="grid grid-cols-2 gap-2">
                                <input type="text" id="matricula_tractor" placeholder="Matrícula Tractor" class="p-2 border rounded text-xs" required>
                                <input type="text" id="matricula_remolque" placeholder="Matrícula Remolque" class="p-2 border rounded text-xs">
                            </div>
                        </div>

                        <!-- Contenedor Dinámico Envíos / Agrupación -->
                        <div class="pt-1">
                            <div class="flex justify-between items-center mb-2">
                                <span class="text-xs font-bold text-gray-500 uppercase">3. Envíos Agrupados</span>
                                <button type="button" onclick="agregarEnvio()" class="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200">+ Añadir Envío</button>
                            </div>
                            <div id="lista-envios" class="space-y-3">
                                <!-- Filas de envíos -->
                            </div>
                        </div>

                        <!-- Observaciones -->
                        <div class="pt-1 space-y-2">
                            <span class="text-xs font-bold text-gray-500 uppercase">4. ADR y Observaciones</span>
                            <input type="text" id="adr" placeholder="Clase ADR" value="No aplica" class="w-full p-2 border rounded text-xs">
                            <textarea id="observaciones" rows="2" class="w-full p-2 border rounded text-xs" placeholder="Observaciones / Reservas"></textarea>
                        </div>

                        <!-- Campo adicional para modificaciones en curso -->
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

            function fHoy() {
                return new Date().toISOString().split('T')[0];
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
                const res = await fetch('/api/v1/deca/listado');
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
                                <div>T: <span class="font-bold">${d.matricula_tractor}</span></div>
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
                    matricula_tractor: document.getElementById('matricula_tractor').value,
                    matricula_remolque: document.getElementById('matricula_remolque').value,
                    adr: document.getElementById('adr').value,
                    observaciones: document.getElementById('observaciones').value,
                    envios: envios,
                    motivo_modificacion: esModificacion ? document.getElementById('motivo_modificacion').value : null
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
                    alert('Error al guardar. Revisa que los campos obligatorios estén completos.');
                }
            }

            async function modificarOrden(codigo) {
                const res = await fetch(`/api/v1/deca/${codigo}/pdf`); // Carga los datos existentes
                // Para rellenar el form, obtenemos el listado completo
                const listRes = await fetch('/api/v1/deca/listado');
                const listado = await listRes.json();
                
                // Pedimos los datos del PDF via API
                esModificacion = true;
                document.getElementById('codigo').value = codigo;
                document.getElementById('bloque-modificacion').classList.remove('hidden');
                document.getElementById('titulo-form').innerText = "Modificar DeCA en Curso (" + codigo + ")";
                
                // Hacer scroll arriba
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }

            function filtrarTabla() {
                const query = document.getElementById('buscador').value.toLowerCase();
                const filas = document.querySelectorAll('#tabla-historico tr');
                filas.forEach(f => {
                    f.style.display = f.innerText.toLowerCase().includes(query) ? '' : 'none';
                });
            }

            nuevoCodigo();
            cargarHistorico();
        </script>
    </body>
    </html>
    """
# --- INTERFAZ WEB / DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_usuario():
    return """
    <!DOCTYPE html>
    <html lang="es">
    ...