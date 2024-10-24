#
# MIT License
#
# (C) Copyright 2022, 2024 Hewlett Packard Enterprise Development LP
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

NAME ?= cray-sat
VERSION ?= $(shell build_scripts/version.sh)
DOCKER_BUILD = docker build . --pull $(DOCKER_ARGS)
DEFAULT_TAG = '$(NAME):$(VERSION)'
TEST_TAG = '$(NAME)-testing:$(VERSION)'
CODESTYLE_TAG = '$(NAME)-codestyle:$(VERSION)'
ifneq ($(wildcard ${HOME}/.netrc),)
	DOCKER_ARGS ?= --secret id=netrc,src=${HOME}/.netrc
endif

all : unittest codestyle image

# The node-images repo must be cloned to get the Kubernetes version, so we can
# install the matching version of kubectl in the cray-sat image. In the Jenkins
# pipeline, this is handled prior to running make
node-images:
		git clone --branch main git@github.com:Cray-HPE/node-images.git node-images

unittest: node-images
		$(DOCKER_BUILD) --target testing --tag $(TEST_TAG)
		docker run $(TEST_TAG)

codestyle: node-images
		$(DOCKER_BUILD) --target codestyle --tag $(CODESTYLE_TAG)
		docker run $(CODESTYLE_TAG)

image: node-images
		$(DOCKER_BUILD) --tag $(DEFAULT_TAG)
