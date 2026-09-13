import hashlib
import json
import datetime
from reportlab.pdfgen import canvas

class DecaSecurityEngine:
    @staticmethod
    def generar_hash_datos(datos_dict: dict) -> str:
        """
        Calcula un hash SHA-256 canónico a partir del JSON de datos del DeCA.
        Garantiza que el orden de los campos no altere el resultado.
        """
        cadena_canonica = json.dumps(datos_dict, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(cadena_canonica.encode('utf-8')).hexdigest()

    @staticmethod
    def calcular_hash_archivo(ruta_pdf: str) -> str:
        """
        Calcula la huella digital SHA-256 del archivo PDF final.
        """
        sha256_hash = hashlib.sha256()
        with open(ruta_pdf, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def preparar_registro_auditoria(deca_id: str, usuario_id: str, empresa_id: str, hash_pdf: str, ip_origen: str):
        """
        Estructura el evento inmutable de auditoría para guardar en la BD.
        """
        return {
            "deca_id": deca_id,
            "empresa_id": empresa_id,
            "usuario_id": usuario_id,
            "accion": "EMISION_DECA",
            "hash_sha256": hash_pdf,
            "ip_origen": ip_origen,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }