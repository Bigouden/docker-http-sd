FROM alpine:3.18
LABEL maintainer="Thomas GUIRRIEC <thomas@guirriec.fr>"
ENV DOCKER_HOST="unix:///var/run/docker.sock"
ENV HTTP_PORT="9999"
ENV LOG_LEVEL="INFO"
ENV LABEL_PREFIX="docker-http-sd"
ENV SCRIPT="docker_http_sd.py"
ENV TARGETS_DELIMITER=","
ENV USERNAME="docker-http-sd"
ENV UID="1000"
ENV GID="1000"
COPY apk_packages /
COPY pip_packages /
ENV VIRTUAL_ENV="/docker-http-sd"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN xargs -a /apk_packages apk add --no-cache --update \
    && python3 -m venv ${VIRTUAL_ENV} \
    && pip install --no-cache-dir --no-dependencies --no-binary :all: -r pip_packages \
    && pip uninstall -y setuptools pip \
    && useradd -l -u "${UID}" -U -s /bin/sh "${USERNAME}" \
    && rm -rf \
        /root/.cache \
        /tmp/* \
        /var/cache/*
COPY --chown=${USERNAME}:${USERNAME} --chmod=500 ${SCRIPT} ${VIRTUAL_ENV}
COPY --chown=${USERNAME}:${USERNAME} --chmod=500 entrypoint.sh /
USER ${USERNAME}
WORKDIR ${VIRTUAL_ENV}
HEALTHCHECK CMD nc -vz localhost ${HTTP_PORT} || exit 1 # nosemgrep
EXPOSE ${HTTP_PORT}
ENTRYPOINT ["/entrypoint.sh"]
