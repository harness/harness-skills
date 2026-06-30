FROM node:20-alpine

WORKDIR /app

COPY package.json ./
COPY src ./src

ENV NODE_ENV=production
ENV PORT=3000
ENV HELLO_MESSAGE="Hello, World from PM_Signoff!"

EXPOSE 3000

USER node

CMD ["node", "src/index.js"]
