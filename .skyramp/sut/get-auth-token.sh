#!/usr/bin/env bash
# Obtains a Bearer token from the running Langflow SUT.
# Outputs ONLY the token to stdout. All diagnostic output goes to stderr.
set -euo pipefail

BASE_URL="http://localhost:7860"
TIMEOUT=300
INTERVAL=5
elapsed=0

echo "Waiting for Langflow at ${BASE_URL}/health ..." >&2
until curl -sf "${BASE_URL}/health" > /dev/null 2>&1; do
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "ERROR: Langflow did not become healthy within ${TIMEOUT}s" >&2
    exit 1
  fi
  sleep "$INTERVAL"
  elapsed=$((elapsed + INTERVAL))
done
echo "Langflow is healthy after ${elapsed}s" >&2

# Default superuser created when LANGFLOW_AUTO_LOGIN=true
RESPONSE=$(curl -sf -X POST "${BASE_URL}/api/v1/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=langflow&password=langflow" 2>&1) || {
  echo "ERROR: Login request failed: ${RESPONSE}" >&2
  exit 1
}

TOKEN=$(echo "$RESPONSE" | jq -r '.access_token // empty')
if [ -z "$TOKEN" ]; then
  echo "ERROR: No access_token in response: ${RESPONSE}" >&2
  exit 1
fi

echo "Token obtained successfully" >&2
printf '%s' "$TOKEN"
