# Despliegue de KAIROS en Railway

Este proyecto **no se puede publicar con GitHub Pages**: necesita un servidor
Python/Flask y PostgreSQL. Railway permite desplegar la app, la base de datos y
Ollama en el mismo proyecto.

## 1. Cuenta y login

1. Crea cuenta en https://railway.com (se recomienda usar tu GitHub).
2. Instala la CLI:

   ```powershell
   npm.cmd install -g @railway/cli
   railway.cmd login
   ```

   Se abre el navegador; inicia sesión. La CLI guarda la sesión, así que no hace
   falta pegar tokens en el chat.

## 2. Proyecto y PostgreSQL

Desde la carpeta del proyecto activo:

```powershell
cd "C:\Users\jhoeell1\Documents\Codex\2026-09-27\ayudama-a-crear-un-programa-en\outputs\electiva-de-danzas-python-agente-local"
railway.cmd init
railway.cmd add postgres
railway.cmd variables
```

En el panel de Railway, abre el servicio Postgres → **Variables** y copia
`DATABASE_URL`. Si usas la CLI, `railway variables` muestra los valores.

## 3. Servicio KAIROS

El repo ya incluye `Dockerfile` y `railway.json` en la rama
`agente-local-sin-n8n`.

1. En Railway: **New Service → Deploy from GitHub repo** y elige
   `jhoeellbasto803n-droid/electiva-de-danzas-kairos`.
2. Selecciona la rama `agente-local-sin-n8n`.
3. Railway detecta el `Dockerfile`. Variables de la app:

   | Variable | Valor |
   | --- | --- |
   | `APP_ENV` | `production` |
   | `DATABASE_URL` | La del Postgres de Railway |
   | `SESSION_SECRET` | Cadena aleatoria larga (ver abajo) |
   | `APP_ORIGIN` | `https://<tu-dominio-de-railway>` (sin barra final) |
   | `PORT` | `3000` (o el que asigne Railway) |
   | `HOST` | `0.0.0.0` |
   | `MODELO_LOCAL_URL` | `http://ollama.railway.internal:11434` |
   | `MODELO_LOCAL_NOMBRE` | `llama3.2:3b` |
   | `MODELO_LOCAL_HOSTS` | `railway.internal` |
   | `MODELO_LOCAL_TIMEOUT` | `120` |
   | `WEB_PUBLICA` | `1` |
   | `WEB_TIMEOUT` | `15` |
   | `WEB_THREADS` | `16` |

   Genera `SESSION_SECRET` con:

   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

   **No subas `.env` al repositorio.** El repo solo contiene `.env.example`.

4. Añade un dominio público en **Settings → Domains → Generate Domain**.
   Copia esa URL exacta en `APP_ORIGIN`.

## 4. Servicio Ollama

1. En el mismo proyecto: **New Service → Deploy from GitHub repo**, misma rama,
   pero configura el **Root Directory** como `deploy/ollama`.
2. Railway detecta `deploy/ollama/Dockerfile` y `railway.json`.
3. Nombre del servicio: `ollama` (importante: así se forma
   `http://ollama.railway.internal:11434`).
4. Añade un volumen persistente en **Settings → Volumes**:
   ruta `/root/.ollama`, tamaño según plan (al menos 4 GB recomendados).
5. Variables: `OLLAMA_HOST=0.0.0.0:11434`. El contenedor descarga
   `llama3.2:3b` al arrancar; si no hay memoria suficiente, prueba
   `llama3.2:1b` cambiando `MODELO_LOCAL_NOMBRE`.

`modelo_local.py` solo acepta `localhost` o hosts listados en
`MODELO_LOCAL_HOSTS`; por eso `railway.internal` debe estar autorizado.

## 5. Verificación

- `https://<dominio>/api/health` debe responder 200.
- Inicia sesión y abre **Asistente**: debe decir que hay modelo local activo.
- Prueba `¿Qué actividades tengo pendientes?`: debe responder con reglas de
  cuenta, sin enviar esos datos a Ollama ni a Wikipedia.
- Prueba **Materias → Importar materias** con
  `docs/Materias-prueba-importacion.xlsx`.
- Si Ollama falla, la app sigue funcionando con reglas deterministas: es un
  respaldo, no un error fatal.

## 6. Costes y límites

- `llama3.2:3b` necesita varios GB de RAM; en planes pequeños usa `1b`.
- La búsqueda web consulta Wikipedia en HTTPS y no envía datos de la cuenta.
- Las sesiones y los datos se guardan solo en tu PostgreSQL de Railway.
- Nunca subas `.env`, credenciales ni logs.
