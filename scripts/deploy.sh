#!/usr/bin/env bash
# Manual deploy fallback for Business Local Records → Network Solutions.
# Use when GitHub Actions runners are IP-blocked, or for a quick one-off push.
#
# Setup:
#   1) brew install lftp        (macOS)   |   sudo apt-get install lftp (Linux)
#   2) Export credentials (do NOT hardcode):
#        export FTP_SERVER=ftp.businesslocalrecords.com
#        export FTP_USER=your-ftp-user
#        export FTP_PASS=your-ftp-password
#   3) Run:  bash scripts/deploy.sh
#
# Uploads the static site into public_html/prototype2/ (mirrors .github/workflows/deploy.yml).
# It never touches /api, /thanks.html at root, /uet.js, /gtag.js, or per-city archives.
set -euo pipefail

: "${FTP_SERVER:?Set FTP_SERVER}"
: "${FTP_USER:?Set FTP_USER}"
: "${FTP_PASS:?Set FTP_PASS}"
SERVER_DIR="${FTP_SERVER_DIR:-public_html/prototype2/}"
PROTOCOL="${FTP_PROTOCOL:-ftp}"   # or ftps

# Files that ship with the site. Everything not matched here is excluded.
lftp -u "${FTP_USER}","${FTP_PASS}" "${PROTOCOL}://${FTP_SERVER}" <<MIRROR
set ssl:verify-certificate no
set ftp:passive-mode yes
set net:max-retries 2
set net:timeout 20
mirror --reverse \
  --verbose \
  --exclude-glob .git* \
  --exclude-glob .github/ \
  --exclude-glob .kilo/ \
  --exclude-glob __pycache__/ \
  --exclude-glob scripts/ \
  --exclude-glob screenshots/ \
  --exclude-glob public/data/ \
  --exclude-glob *.py \
  --exclude-glob *.md \
  --exclude-glob *.png \
  ./ "${SERVER_DIR}"
bye
MIRROR

echo "Done — site mirrored to ${SERVER_DIR}"
