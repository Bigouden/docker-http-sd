FROM alpine:3.16
LABEL maintainer="Thomas GUIRRIEC <thomas@guirriec.fr>"
ENV HTTP_PORT="9999"
ENV LOG_LEVEL="INFO"
ENV LABEL_PREFIX="docker-multi-targets-service-discovery"
ENV SCRIPT="docker_multi_targets_service_discovery.py"
ENV TARGETS_DELIMITER=","
COPY requirements.txt /
COPY entrypoint.sh /
ENV VIRTUAL_ENV="/docker-multi-targets-service-discovery"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN apk add --no-cache --update \
         python3 \
    && python3 -m venv ${VIRTUAL_ENV} \
    && pip install --no-cache-dir --no-dependencies --no-binary :all: -r requirements.txt \
    && pip uninstall -y setuptools pip \
    && rm -rf \
        /root/.cache \
        /tmp/* \
        /var/cache/* \
    && chmod +x /entrypoint.sh
COPY ${SCRIPT} ${VIRTUAL_ENV}
WORKDIR ${VIRTUAL_ENV}
HEALTHCHECK CMD nc -vz localhost ${HTTP_PORT} || exit 1
ENTRYPOINT ["/entrypoint.sh"]
