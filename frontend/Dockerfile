# ---- build do Angular ----
FROM node:22 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- nginx servindo o build ----
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
# output real do Angular 21 (angular.json): dist/frontend/browser
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
EXPOSE 80
