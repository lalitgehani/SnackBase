#!/bin/sh
set -eu

SNACKBASE_URL="${SNACKBASE_URL:-${VITE_SNACKBASE_URL:-http://localhost:8002}}"
SNACKBASE_URL="${SNACKBASE_URL%/}"

PROVISION_URL="${PROVISION_API_URL:-${VITE_PROVISION_API_URL:-http://localhost:8091}}"
PROVISION_URL="${PROVISION_URL%/}"

PLATFORM_PREFIX="${PLATFORM_PATH_PREFIX:-/platform/v1}"
PLATFORM_PREFIX="${PLATFORM_PREFIX%/}"

GATEWAY="${PLATFORM_GATEWAY_URL:-http://platform-gateway:8080}"
GATEWAY="${GATEWAY%/}${PLATFORM_PREFIX}/"

escaped_snackbase=$(printf '%s' "$SNACKBASE_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')
escaped_provision=$(printf '%s' "$PROVISION_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')
escaped_prefix=$(printf '%s' "$PLATFORM_PREFIX" | sed 's/\\/\\\\/g; s/"/\\"/g')

cat > /usr/share/nginx/html/config.js <<EOF
window.__SNACKBASE_ENV__ = {
  snackbaseUrl: "${escaped_snackbase}",
  provisionApiUrl: "${escaped_provision}",
  platformPathPrefix: "${escaped_prefix}"
};
EOF

sed "s|\${PLATFORM_GATEWAY_UPSTREAM}|${GATEWAY}|g" \
  /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
