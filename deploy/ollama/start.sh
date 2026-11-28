#!/bin/sh
set -e

ollama serve &
SERVIDOR=$!

# La imagen no trae wget/curl; esperamos unos segundos a que arranque.
sleep 10

# Descarga en segundo plano: no bloquea el healthcheck del despliegue.
(ollama pull llama3.2:1b || true) &

wait "$SERVIDOR"
