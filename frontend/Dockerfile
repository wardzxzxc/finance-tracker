FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first for cache reuse
COPY package.json ./
RUN npm install

COPY . .
ARG VITE_API_KEY
ARG VITE_API_BASE_URL=/api
ENV VITE_API_KEY=$VITE_API_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
