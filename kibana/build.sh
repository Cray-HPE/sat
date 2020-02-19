#!/bin/bash

# Build sat-kibana Newline Delimited JSON (NDJSON) file for import into
# Kibana. Kibana objects are searhes, visualizations, and dashboards.
# Visualizations use searches. Dashboards use visualizations and searches.

cd "$(dirname $0)"
cat searches/*.ndjson >sat-kibana.ndjson
cat visualizations/*.ndjson >>sat-kibana.ndjson
cat dashboards/*.ndjson >>sat-kibana.ndjson
