#!/bin/sh
set -e

ollama serve &
SERVIDOR=$!

# Espera a que el servidor interno esté listo antes de descargar el modelo.
i=0
while [ "$i" -lt 30 ]; do
  if wget -q -O /dev/null http://127.0.0.1:11434/api/tags; then
    break
  fi
  i=$((i + 1))
  sleep 2
done

ollama pull llama3.2:3b || ollama pull llama3.2:1b || true

wait "$SERVIDOR"
