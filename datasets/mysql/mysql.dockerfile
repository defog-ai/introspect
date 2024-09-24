FROM alpine:3.20

WORKDIR /app
# VOLUME /app

RUN apk add --update mysql mysql-client \
    && apk add tzdata && cp /usr/share/zoneinfo/PRC /etc/localtime && echo "PRC" > /etc/timezone && apk del tzdata \
    && rm -f /var/cache/apk/*
    
COPY my.cnf /etc/mysql/my.cnf
COPY startup.sh .

EXPOSE 3306
CMD ["/bin/sh", "/app/startup.sh"]