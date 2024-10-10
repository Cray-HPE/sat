#!/bin/bash -xe
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

LOGDIR=/var/log/cray/sat

SATMANDIR=/usr/share/man/man8

NODE_IMAGES_DIR="/tmp/node-images"
NODE_IMAGES_BASE_PACKAGES_PATH="metal-provision/group_vars/all.yml"

# create logging directory
if [ ! -d "$LOGDIR" ]; then
    mkdir -p $LOGDIR
    chmod 755 $LOGDIR
fi

# temporarily install docutils needed for man page builds
pip install "$(grep docutils /sat/requirements-dev.lock.txt)"
# make man pages
cd /sat/docs/man
make
# remove docutils when done since it's not needed in final image
pip uninstall -y docutils

# install man pages
cd /sat
if [ ! -d "$SATMANDIR" ]; then
    mkdir -p $SATMANDIR
    chmod 755 $SATMANDIR
fi
cp docs/man/*.8 $SATMANDIR

# generate auto-completion script
register-python-argcomplete sat > /usr/share/bash-completion/completions/sat

# /etc/profile sets $PATH to a static value on login, therefore $VIRTUAL_ENV/bin must be prepended.
echo "export PATH=$VIRTUAL_ENV/bin:\$PATH" > /etc/profile.d/sat_path.sh

# install kubectl using same version used in ncn image
KUBERNETES_PULL_VERSION=$(python3 <<EOF
import sys

import yaml


with open("${NODE_IMAGES_DIR}/${NODE_IMAGES_BASE_PACKAGES_PATH}") as pkgs:
    pkgs = yaml.safe_load(pkgs)
    version = pkgs.get("kubernetes_release")
    if version:
        print(version.strip())
        sys.exit(0)
print("Could not determine kubectl version")
sys.exit(1)
EOF
)

if [ -z "$KUBERNETES_PULL_VERSION" ]; then
    echo >&2 "Unable to determine version of kubectl to use from node-images repo"
    exit 1
fi

curl -fLO "https://storage.googleapis.com/kubernetes-release/release/v${KUBERNETES_PULL_VERSION#v}/bin/linux/amd64/kubectl"
chmod +x ./kubectl
mv ./kubectl /usr/bin
