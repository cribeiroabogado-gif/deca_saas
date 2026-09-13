from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Importar tu sesión de BD y el modelo DecaModel
# from main import get_db, DecaModel

router = APIRouter()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validación Oficial DeCA - Inspección de Transporte</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #f7fafc; margin: 0; padding: 20px; color: #2d3748; }
        .container { max-width: 600px; margin: 0 auto; background: #ffffff; padding: 24px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); }
        .badge-valid { background-color: #c6f6d5; color: #22543d; border: 1px solid #9ae6b4; padding: 12px; border-radius: 8px; font-weight: bold; text-align: center; font-size: 1.1em; margin-bottom: 20px; }
        .badge-invalid { background-color: #fed7d7; color: #742a2a; border: 1px solid #feb2b2; padding: 12px; border-radius: 8px; font-weight: bold; text-align: center; font-size: 1.1em; margin-bottom: 20px; }
        .field-group { border-bottom: 1px solid #edf2f7; padding: 10px 0; }
        .label { font-size: 0.85em; color: #718096; text-transform: uppercase; font-weight: 600; }
        .value { font-size: 1em; color: #1a202c; margin-top: 4px; font-weight: 500; }
        .btn-download { display: block; width: 100%; text-align: center; background-color: #3182ce; color: white; padding: 12px 0; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 20px; }
        .footer { font-size: 0.8em; text-align: center; color: #a0aec0; margin-top: 24px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Verificación de Documento Control (DeCA)</h2>
        
        {status_badge}

        <div class="field-group">
            <div class="label">Código Único DeCA</div>
            <div class="value">{codigo_deca}</div>
        </div>
        <div class="field-group">
            <div class="label">Fecha / Hora de Emisión</div>
            <div class="value">{created_at}</div>
        </div>
        <div class="field-group">
            <div class="label">Cargador Contractual</div>
            <div class="value">{cargador_nombre} (NIF: {cargador_nif})</div>
        </div>
        <div class="field-group">
            <div class="label">Transportista Efectivo</div>
            <div class="value">{transportista_nombre} (NIF: {transportista_nif})</div>
        </div>
        <div class="field-group">
            <div class="label">Matrícula Tractora / Remolque</div>
            <div class="value">{matricula} / {remolque}</div>
        </div>
        <div class="field-group">
            <div class="label">Huella Digital Criptográfica (SHA-256)</div>
            <div class="value" style="font-family: monospace; font-size: 0.8em; word-break: break-all;">{hash_sha256}</div>
        </div>

        {download_button}

        <div class="footer">
            Validación efectuada conforme a la Orden FOM/2861/2012 y la Resolución de la DG de Transporte por Carretera.
        </div>
    </div>
</body>
</html>
"""

@router.get("/deca/index.php", response_class=HTMLResponse)
async def validar_deca_publico(
    id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint público de inspección al que redirige el QR.
    Servido en la ruta exigida por la URL grabada en el PDF.
    """
    query = select(DecaModel).where(DecaModel.codigo_deca == id)
    result = await db.execute(query)
    deca = result.scalars().first()

    if not deca:
        badge = '<div class="badge-invalid">❌ DOCUMENTO NO ENCONTRADO O NO VÁLIDO</div>'
        return HTML_TEMPLATE.format(
            status_badge=badge,
            codigo_deca=id,
            created_at="-",
            cargador_nombre="-",
            cargador_nif="-",
            transportista_nombre="-",
            transportista_nif="-",
            matricula="-",
            remolque="-",
            hash_sha256="-",
            download_button=""
        )

    datos = deca.datos_json
    badge = '<div class="badge-valid">✅ DOCUMENTO AUTÉNTICO Y REGISTRADO</div>'
    dl_btn = f'<a href="/api/v1/deca/download/{deca.codigo_deca}" class="btn-download">Descargar PDF Oficial Custodiado</a>'

    return HTML_TEMPLATE.format(
        status_badge=badge,
        codigo_deca=deca.codigo_deca,
        created_at=deca.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        cargador_nombre=datos.get("cargador_nombre", "-"),
        cargador_nif=datos.get("cargador_nif", "-"),
        transportista_nombre=datos.get("transportista_nombre", "-"),
        transportista_nif=datos.get("transportista_nif", "-"),
        matricula=datos.get("matricula", "-"),
        remolque=datos.get("remolque", "-"),
        hash_sha256=deca.hash_sha256,
        download_button=dl_btn
    )