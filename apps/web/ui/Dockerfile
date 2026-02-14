FROM node:20-alpine AS build

WORKDIR /ui

COPY apps/web/ui/package.json /ui/package.json
RUN npm install

COPY apps/web/ui/ /ui/
RUN npm run build

FROM nginx:1.27-alpine

COPY apps/web/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /ui/dist/ /usr/share/nginx/html/

EXPOSE 80

