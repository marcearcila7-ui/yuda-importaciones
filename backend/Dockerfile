FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema para weasyprint (Pango/Cairo), psycopg2 y fuentes.
# fonts-noto-cjk: necesaria para que el chino del PDF no salga como rectángulos.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    fonts-noto-cjk \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Instala las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de la aplicación
COPY . .

# Arranca el servidor con recarga en caliente
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
