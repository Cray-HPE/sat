# Copyright 2020 Hewlett Packard Enterprise Development LP
#
# Dockerfile for SAT

FROM dtr.dev.cray.com/baseos/alpine:3.12.0 as base

WORKDIR /sat
COPY CHANGELOG.md README.md /sat/
COPY setup.cfg setup.py /sat/
COPY requirements.docker.txt /sat/requirements.txt
COPY config-docker-sat.sh /sat/
COPY sat /sat/sat
COPY docs/man /sat/docs/man
COPY tools /sat/tools

RUN apk update && \
    apk add --no-cache python3-dev py3-pip bash openssl-dev libffi-dev \
        curl musl-dev git make gcc mandoc ipmitool && \
    PIP_INDEX_URL=http://dst.us.cray.com/dstpiprepo/simple \
    PIP_TRUSTED_HOST=dst.us.cray.com \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir .

RUN /sat/config-docker-sat.sh

# All files have been installed so remove from WORKDIR
RUN rm -rf /sat/*

# certs should be mounted from host
# --mount type=bind,src=/usr/share/pki/trust/anchors,target=/usr/local/share/ca-certificates,ro=true
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
CMD ["sh", "-c", "update-ca-certificates 2&>/dev/null && /bin/bash -l"]]
