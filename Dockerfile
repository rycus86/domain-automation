FROM alpine

LABEL maintainer "Viktor Adam <rycus86@gmail.com>"

ADD requirements.txt /tmp/requirements.txt

RUN apk add --no-cache python3 openssl \
    && apk add --no-cache --virtual build-dependencies \
        gcc python3-dev musl-dev linux-headers libffi-dev openssl-dev \
    && pip3 install -r /tmp/requirements.txt \
    && apk del build-dependencies

ADD src /app
WORKDIR /app

STOPSIGNAL SIGTERM

CMD [ "python3", "app.py" ]

# add app info as environment variables
ARG GIT_COMMIT
ENV GIT_COMMIT $GIT_COMMIT
ARG BUILD_TIMESTAMP
ENV BUILD_TIMESTAMP $BUILD_TIMESTAMP
