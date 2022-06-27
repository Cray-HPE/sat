#!/bin/bash -xe
#
# MIT License
#
# (C) Copyright 2020-2022 Hewlett Packard Enterprise Development LP
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

NODE_IMAGE_KUBERNETES_REPO="https://github.com/Cray-HPE/node-image-build.git"
NODE_IMAGE_KUBERNETES_DIR="node-image-kubernetes"
NODE_IMAGE_KUBERNETES_PATH="boxes/ncn-node-images/kubernetes"
NODE_IMAGE_KUBERNETES_BRANCH="main"

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
cd /sat
git clone $NODE_IMAGE_KUBERNETES_REPO $NODE_IMAGE_KUBERNETES_DIR
cd  $NODE_IMAGE_KUBERNETES_DIR
git checkout $NODE_IMAGE_KUBERNETES_BRANCH

source "${NODE_IMAGE_KUBERNETES_PATH}/files/resources/common/vars.sh"
if [ -z "$KUBERNETES_PULL_VERSION" ]; then
    KUBERNETES_PULL_VERSION=$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)
fi

curl -LO "https://storage.googleapis.com/kubernetes-release/release/v${KUBERNETES_PULL_VERSION#v}/bin/linux/amd64/kubectl"
chmod +x ./kubectl
mv ./kubectl /usr/bin
