FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN rm -f package-lock.json && npm cache clean --force && npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
