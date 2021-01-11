#!/bin/bash
set -e
#
# update-ca-certficates reads from /usr/local/share/ca-certificates
# and updates /etc/ssl/certs/ca-certificates.crt
# REQUESTS_CA_BUNDLE is used by python
#
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
update-ca-certificates 2>/dev/null
exec "$@"
