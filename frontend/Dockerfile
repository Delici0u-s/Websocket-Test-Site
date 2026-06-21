FROM node:22-slim AS build
WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
# PUBLIC_WS_URL is baked in at build time (SvelteKit static env vars).
# Leave it unset in production and the client will derive ws(s)://<host>/ws.
ARG PUBLIC_WS_URL=""
ENV PUBLIC_WS_URL=${PUBLIC_WS_URL}
RUN npm run build

FROM node:22-slim AS run
WORKDIR /app
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["node", "build/index.js"]
