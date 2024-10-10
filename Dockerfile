#
# MIT License
#
# (C) Copyright 2020-2024 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# Dockerfile for SAT
#
# The multi-stage Dockerfile is somewhat more complex than the original
# Dockerfile, but it provides significant reductions in image size and build time
# when cached builds are present.


# The venv_base sets up the environment variables for the virtualenv which are
# used by every other stage. Anything that uses the SAT venv should derive from
# this stage.
FROM artifactory.algol60.net/csm-docker/stable/docker.io/library/alpine:3.15 AS venv_base
ENV VIRTUAL_ENV="/sat/venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# The base stage only installs Python and sets up the workdir.
FROM venv_base AS base

RUN apk update && \
    apk add --no-cache python3-dev py3-pip

WORKDIR /sat

# The build stage installs all build dependencies (e.g. to compile the
# cryptography wheel etc.), installs all Python dependencies in the
# virtualenv, installs SAT itself in the virtualenv, and then runs the config
# script to install kubectl and build docs.
FROM base as build

RUN apk update && \
    apk add bash bash-completion openssl-dev libffi-dev openssh curl musl-dev \
            git make gcc mandoc ipmitool ceph-common && \
    python3 -m venv $VIRTUAL_ENV

COPY requirements.lock.txt requirements.txt
ARG PIP_EXTRA_INDEX_URL="https://artifactory.algol60.net/artifactory/csm-python-modules/simple"
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    pip3 install --no-cache-dir -U pip && \
    pip3 install -r requirements.txt

COPY CHANGELOG.md README.md setup.py ./
# This file is used to get the version of docutils needed
COPY requirements-dev.lock.txt requirements-dev.lock.txt
COPY docker_scripts/config-docker-sat.sh ./
COPY sat sat
COPY docs/man docs/man
COPY tools tools

RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    --mount=type=bind,source=node-images,target=/tmp/node-images \
    pip3 install --no-cache-dir pip && \
    pip3 install --no-cache-dir --timeout=300 . && \
    ./config-docker-sat.sh

FROM base as ci_base
COPY --from=build $VIRTUAL_ENV $VIRTUAL_ENV
COPY requirements-dev.lock.txt requirements-dev.lock.txt
RUN --mount=type=secret,id=netrc,target=/root/.netrc \
    pip3 install -r requirements-dev.lock.txt

# The testing stage runs tests in the container in the CI pipeline. This allows
# us to use the same Python version in CI as we use in our production Docker
# containers.
FROM ci_base as testing
# The container overhead reduces performance such that performance tests fail
# when they succeed natively, so disable those in CI.
ENV SAT_SKIP_PERF_TESTS=1
COPY tests tests
COPY unittest.cfg ./
# Omit test coverage in CI, coverage reports are discarded anyway.
CMD nose2 --exclude-plugin='nose2.plugins.coverage'

# This stage runs pycodestyle in the container so we are again using the same
# production environment to check our code style.
FROM ci_base as codestyle
WORKDIR /codestyle
COPY sat sat
COPY tests tests
COPY pycodestyle.conf pycodestyle.conf
CMD ["pycodestyle", "--config", "pycodestyle.conf", "sat", "tests"]

# The production stage is our actual SAT image. We simply install runtime
# dependencies, copy the whole virtualenv from the build stage, as well as the
# scaffolding scripts to launch SAT within the container, and set up CMD and
# ENTRYPOINT.
FROM venv_base AS production
# certs should be mounted from host
# --mount type=bind,src=/etc/pki/trust/anchors,target=/usr/local/share/ca-certificates,ro=true

RUN apk update && \
    apk add --no-cache python3 bash bash-completion openssh curl git ipmitool \
        ceph-common mandoc && \
    rm -r /var/cache/apk

COPY --from=build $VIRTUAL_ENV $VIRTUAL_ENV
COPY --from=build /usr/share/man/man8/sat*.8 /usr/share/man/man8/
COPY --from=build /usr/bin/kubectl /usr/bin/kubectl
COPY --from=build /usr/share/bash-completion/completions/sat /usr/share/bash-completion/completions/sat
COPY --from=build /etc/profile.d/sat_path.sh /etc/profile.d/sat_path.sh

COPY docker_scripts/sat_container_prompt.sh /etc/profile.d/sat_container_prompt.sh
COPY docker_scripts/docker_entrypoint.sh /docker_entrypoint.sh
RUN chmod +x docker_entrypoint.sh

ENTRYPOINT ["/docker_entrypoint.sh"]
CMD ["/bin/bash", "-l"]
