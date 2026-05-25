FROM node:20-alpine

RUN apk add --no-cache libc6-compat

WORKDIR /app

# Копіюємо обидва файли для відтворюваної установки
COPY package.json package-lock.json* ./

# npm ci замість npm install: швидше, суворо за lock-файлом,
# і --include=optional гарантує завантаження нативних бінарників для linux-x64-musl
RUN npm ci --include=optional

# Копіюємо решту файлів (node_modules вже виключено через .dockerignore)
COPY . .

CMD ["npm", "run", "dev"]
