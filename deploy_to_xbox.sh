#!/usr/bin/env bash
# Deploy a built .appx/.msix package to the dev-mode Xbox One S over Device Portal (WDP).
# Portal verified reachable: https://192.168.12.131:11443  auth: M:M (Basic)
# Endpoint contract confirmed: POST /api/app/install (403 on a non-package payload =
#   portal validates the real package; the script dumps full diag on failure so we
#   can adjust field name / headers at deploy time if needed).
set -euo pipefail
HOST="192.168.12.131"
PORT="11443"
USER="M"
PASS="M"
PKG="${1:-}"

if [ -z "$PKG" ] || [ ! -f "$PKG" ]; then
  echo "usage: $0 /path/to/Package.appx"
  exit 2
fi

echo ">> Deploying $(basename "$PKG") to https://$HOST:$PORT ..."
# Install request. Fields per MS Device Portal REST contract:
#   name  -> package family name / display name
#   file  -> the application package (.appx / .msix)
CODE=$(curl -sk -u "$USER:$PASS" \
  -X POST "https://$HOST:$PORT/api/app/install" \
  -F "file=@$PKG" -F "name=MadManagerXbox" \
  -D /tmp/wdp_headers.txt -o /tmp/wdp_body.txt \
  -w "%{http_code}" 2>/dev/null || true)
echo ">> POST /api/app/install -> HTTP $CODE"
echo "   headers:"; sed 's/^/     /' /tmp/wdp_headers.txt 2>/dev/null | head -8
echo "   body:";    sed 's/^/     /' /tmp/wdp_body.txt 2>/dev/null | head -8

# 202 Accepted => Location: /api/app/installstatus?id=<id>  -> poll until done
LOC=$(grep -i '^Location:' /tmp/wdp_headers.txt 2>/dev/null | sed 's/.*id=//; s/\r//; s/ //g' || true)
if [ "$CODE" = "202" ] && [ -n "$LOC" ]; then
  echo ">> Operation queued (id=$LOC), polling installstatus ..."
  for i in $(seq 1 30); do
    POLL=$(curl -sk -u "$USER:$PASS" -X GET "https://$HOST:$PORT/api/app/installstatus?id=$LOC" -w "\n%{http_code}" 2>/dev/null || true)
    PCODE=$(printf '%s' "$POLL" | tail -1)
    PBODY=$(printf '%s' "$POLL" | sed '$d')
    echo "   poll $i: HTTP $PCODE  $PBODY"
    case "$PBODY" in
      *Pending*|*Queued*|*Installing*) sleep 2; continue ;;
      *Success*|*Completed*)          echo ">> INSTALL OK"; exit 0 ;;
      *Failure*|*Error*|*Cancelled*)  echo ">> INSTALL FAILED"; exit 3 ;;
      *) ;;
    esac
  done
  echo ">> Timed out polling installstatus (id=$LOC). Check Device Portal UI."
  exit 4
fi
# Non-202: surface diagnostics; the real .appx should move past 403.
echo ">> No accepted install operation. Full HTTP headers + body above for diagnosis."
exit "$CODE"
