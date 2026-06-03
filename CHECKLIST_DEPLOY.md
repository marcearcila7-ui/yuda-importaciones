## Checklist pre-deploy YUDA Importaciones

### Servidor
- [ ] El servidor tiene Docker y Docker Compose instalados
- [ ] El servidor tiene al menos 1GB de RAM y 10GB de disco
- [ ] El puerto 80 está abierto en el firewall
- [ ] El dominio del backend apunta a la IP del servidor

### Configuración
- [ ] .env.prod existe y tiene todos los valores completados
- [ ] SECRET_KEY tiene al menos 32 caracteres aleatorios
- [ ] ANTHROPIC_API_KEY es válida y tiene créditos
- [ ] CORS_ORIGINS tiene la URL exacta del frontend en Vercel (sin slash final)
- [ ] VITE_API_URL tiene la URL exacta del backend (con https://)

### Deploy
- [ ] docker compose -f docker-compose.prod.yml up -d --build corre sin errores
- [ ] alembic upgrade head aplicó todas las migraciones
- [ ] curl https://tu-backend/  retorna {"status":"ok","sistema":"YUDA Importaciones"}
- [ ] El login funciona desde el navegador
- [ ] Una vendedora puede subir una foto y el OCR responde
