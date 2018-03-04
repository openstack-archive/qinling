FROM node:8-alpine
MAINTAINER anlin.kong@gmail.com

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY package.json /usr/src/app/
COPY package-lock.json /usr/src/app/
RUN npm install && npm cache clean --force
COPY server.js /usr/src/app/server.js

EXPOSE 9090

CMD [ "npm", "start" ]
