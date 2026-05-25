FROM node:20-alpine

# Додаємо підтримку сумісності бібліотек C (часто вирішує проблеми з Turbopack та Tailwind)
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Копіюємо лише package.json, щоб npm згенерував залежності з нуля під Alpine
COPY package.json ./

# Встановлюємо залежності з примусовим включенням опціональних пакетів
RUN npm install --include=optional

COPY . .

CMD ["npm", "run", "dev"]