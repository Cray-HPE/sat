# Copyright 2020-2021 Hewlett Packard Enterprise Development LP
#
# Dockerfile for SAT

FROM arti.dev.cray.com/baseos-docker-master-local/alpine:3.13.2 as base

WORKDIR /sat
COPY CHANGELOG.md README.md /sat/
COPY setup.cfg setup.py /sat/
COPY requirements.lock.txt /sat/requirements.txt
# This file is used to get the version of docutils needed
COPY requirements-dev.lock.txt /sat/requirements-dev.lock.txt
COPY docker_scripts/config-docker-sat.sh /sat/
COPY sat /sat/sat
COPY docs/man /sat/docs/man
COPY tools /sat/tools
COPY docker_scripts/docker_entrypoint.sh /docker_entrypoint.sh
COPY docker_scripts/sat_container_prompt.sh /etc/profile.d/sat_container_prompt.sh

RUN apk update && \
    apk add --no-cache python3-dev py3-pip bash openssl-dev libffi-dev \
        openssh curl musl-dev git make gcc mandoc ipmitool ceph-common rust cargo && \
    PIP_INDEX_URL=http://dst.us.cray.com/dstpiprepo/simple \
    PIP_TRUSTED_HOST=dst.us.cray.com \
    pip3 install --no-cache-dir -U pip && \
    pip3 install --no-cache-dir . && \
    apk del cargo rust

RUN /sat/config-docker-sat.sh

# All files have been installed so remove from WORKDIR
RUN rm -rf /sat/*

# certs should be mounted from host
# --mount type=bind,src=/etc/pki/trust/anchors,target=/usr/local/share/ca-certificates,ro=true
RUN chmod +x /docker_entrypoint.sh
ENTRYPOINT ["/docker_entrypoint.sh"]
CMD ["/bin/bash", "-l"]
