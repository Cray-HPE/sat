#!/bin/bash
set -e
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
update-ca-certificates 2>/dev/null
exec "$@"