FROM node:18 AS build
WORKDIR /frontend
COPY package*.json .
COPY . .
CMD npm run build
FROM nginx:latest
RUN rm -rf /usr/share/nginx/html
COPY --from=build /frontend/build /usr/share/nginx/html
COPY mime.types /etc/nginx/mime.types
COPY nginx.conf /etc/nginx/nginx.conf