FROM node:20-slim

WORKDIR /app

# Instala dependencias a partir del package.json
COPY package.json ./
RUN npm install

# Copia el resto del código del frontend
COPY . .

EXPOSE 3000

# Arranca Vite accesible desde fuera del contenedor
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
