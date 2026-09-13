# Imagen base ligera con Python 3.12/3.14
FROM python:3.12-slim

# Evita la creación de archivos .pyc y fuerza el envío directo de logs a la consola
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalación de dependencias del sistema necesarias para ReportLab y bibliotecas C
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e instalación de paquetes de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia del código fuente de la aplicación
COPY . .

# Creación de un usuario sin privilegios por seguridad
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Arranque del servidor de producción Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]