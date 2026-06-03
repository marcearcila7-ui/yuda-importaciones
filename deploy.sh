#!/bin/bash
set -e

echo "=== YUDA Importaciones — Deploy ==="

# 1. Verificar que existe .env.prod
if [ ! -f .env.prod ]; then
  echo "ERROR: No existe .env.prod. Copia .env.prod.example y completa los valores."
  exit 1
fi

# 2. Pull del código más reciente
git pull origin main

# 3. Build y levantar servicios
docker compose -f docker-compose.prod.yml up -d --build

# 4. Esperar que el backend esté healthy
echo "Esperando que el backend esté listo..."
sleep 10

# 5. Correr migraciones
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# 6. Verificar health check
RESPONSE=$(curl -s http://localhost/ 2>/dev/null || curl -s http://localhost:8000/ 2>/dev/null)
echo "Health check: $RESPONSE"

echo "=== Deploy completado ==="
