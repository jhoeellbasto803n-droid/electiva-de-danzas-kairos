#!/bin/sh
set -e

ollama serve &
SERVIDOR=$!

# La imagen no trae wget/curl; esperamos unos segundos a que arranque.
sleep 10

ollama pull llama3.2:1b || true

wait "$SERVIDOR"
