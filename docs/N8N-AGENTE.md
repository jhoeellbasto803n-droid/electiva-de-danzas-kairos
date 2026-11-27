# Asistente académico: reglas locales y n8n opcional

La versión Python de KAIROS incluye un asistente que funciona de inmediato con
reglas locales deterministas. No necesita claves, internet ni un modelo
generativo. n8n es una opción secundaria: si el equipo configura un webhook, el
mismo chat puede reenviar los mensajes a ese flujo.

```
Modo local (por defecto)
Navegador ──POST /api/agent──▶ Flask (sesión, origen, límites)
                                   │
                                   └── local_agent.py ──▶ {texto, acciones}

Modo n8n (opcional)
Navegador ──POST /api/agent──▶ Flask (sesión, origen, límites)
                                   │
                                   ├── x-kairos-key ──▶ Webhook n8n
                                   │                        │
                                   │                        └── Modelo / herramientas
                                   ◀── {texto, acciones} ───┘
```

## Modos

| `AGENT_MODE` | Comportamiento |
| --- | --- |
| `auto` (inicial) | Usa n8n si `N8N_WEBHOOK_URL` y `N8N_SHARED_SECRET` están definidos; en caso contrario, usa reglas locales. |
| `local` | Fuerza las reglas locales aunque existan credenciales de n8n. Es la forma de dejar de enviar mensajes fuera del servidor sin borrar la configuración. |
| `n8n` | Exige webhook y clave. Si faltan, el servidor no arranca y muestra un error claro. |

En modo local los mensajes no salen del servidor de KAIROS. El archivo
[`local_agent.py`](../local_agent.py) contiene las reglas: tipos de actividad,
fechas, porcentajes, horas, privacidad, índice P, plan semanal y funciones de
la app. No es un modelo generativo: si no reconoce la intención, lo dice.

## Principios

1. **Extraer no es decidir.** La revisión local de instrucciones extrae
   candidatos con reglas deterministas. El asistente puede conversar y
   proponer, pero no fija prioridades, ponderaciones ni fechas que no estén en
   la fuente.
2. **Nada se registra solo.** Las acciones del asistente son sugerencias. La
   interfaz las muestra como tarjetas y, como máximo, abre el formulario de
   actividades con los datos propuestos. Guardar exige revisar y confirmar.
3. **La persona decide.** Si falta un dato, el asistente debe decirlo y pedirlo;
   no debe completar huecos con valores inventados.
4. **Privacidad antes del primer mensaje.** La vista muestra un aviso y no
   permite escribir hasta que la persona lo acepta. Si se cambia entre modo
   local y n8n, el aviso vuelve a aparecer porque cambia el destino del texto.
   La conversación vive solo en memoria: no se guarda en PostgreSQL ni en
   `localStorage`.

## Variables de entorno

| Variable | Obligatoria | Uso |
| --- | --- | --- |
| `AGENT_MODE` | No | `auto`, `local` o `n8n`. Por defecto `auto`. |
| `N8N_WEBHOOK_URL` | Solo para n8n | URL completa del webhook de producción. Debe usar HTTPS; solo se admite HTTP en `localhost`/`127.0.0.1` con `APP_ENV=development`. Sin ruta extra, parámetros ni fragmento. |
| `N8N_SHARED_SECRET` | Solo para n8n | Valor aleatorio largo. Flask lo envía en la cabecera `x-kairos-key`; n8n debe rechazar cualquier otra clave. |
| `AGENT_ALLOWED_EMAILS` | No | Correos separados por coma. Si está vacío, cualquier cuenta con sesión puede usar el asistente. Úsalo para un piloto cerrado. |

Ejemplo de modo local (no requiere nada más):

```dotenv
AGENT_MODE=local
```

Ejemplo con n8n:

```dotenv
AGENT_MODE=auto
N8N_WEBHOOK_URL=https://n8n.example.edu/webhook/asistente-academico
N8N_SHARED_SECRET=cambia-esto-por-un-secreto-largo-y-aleatorio
AGENT_ALLOWED_EMAILS=estudiante1@unicafam.edu.co,estudiante2@unicafam.edu.co
```

Si solo se define una de las dos variables de n8n y `AGENT_MODE=auto`, el
servidor registra una advertencia y usa el modo local. Si `AGENT_MODE=n8n`,
el servidor se detiene al arrancar para no fingir que el asistente está
conectado.

## API del servidor Python

### `GET /api/agent/status`

Requiere sesión. Devuelve el estado sin llamar a n8n:

```json
{
  "mode": "local",
  "configured": true,
  "allowed": true,
  "allowlistConfigured": false,
  "available": true,
  "message": "Asistente local de reglas activo. No envía tus mensajes a servicios externos."
}
```

En modo n8n, `mode` vale `"n8n"` y el mensaje lo indica. `available` es
`allowed`; la interfaz usa este valor para habilitar o deshabilitar el
formulario. `configured` se conserva por compatibilidad y vale `true` en ambos
modos porque el asistente local no necesita configuración.

### `POST /api/agent`

Requiere sesión y el encabezado `Origin` del mismo sitio. Límites:

- 12 solicitudes por minuto por cuenta (HTTP 429 al superarlo), en ambos modos.
- Mensaje de 1 a 4000 caracteres.
- Contexto opcional (`candidatos`, `advertencias`) de hasta 8 KB cada uno.
- En modo n8n: espera máxima de 55 segundos al webhook; respuesta máxima de
  96 KB; el texto se recorta a 12 000 caracteres.
- Máximo 10 acciones, 4 KB por acción y 16 KB en total.

Solicitud:

```json
{
  "mensaje": "Tengo un parcial y un taller la misma semana. ¿Qué debería revisar primero?",
  "candidatos": { "category": [{ "value": "PAR", "label": "Parcial o examen" }] },
  "advertencias": ["Aparecen varias fechas."]
}
```

`candidatos` y `advertencias` son opcionales; sirven para compartir el
resultado de la revisión local sin reenviar el texto original. En modo n8n el
servidor **añade** estos campos, que el navegador no puede falsificar:

```json
{
  "mensaje": "…",
  "estudianteId": "uuid-de-la-sesión",
  "sessionId": "kairos-uuid-de-la-sesión",
  "nombre": "Nombre de la cuenta",
  "correo": "cuenta@dominio",
  "origen": "kairos-python",
  "candidatos": null,
  "advertencias": null
}
```

Respuesta que Flask devuelve al navegador:

```json
{
  "texto": "Puedes empezar por el parcial porque…",
  "acciones": [
    {
      "tipo": "crear_actividad",
      "titulo": "Taller de estadística",
      "materia": "Estadística y Probabilidad",
      "categoria": "TAL",
      "fecha": "2026-11-05T18:00",
      "ponderacion": 15,
      "horas": 3,
      "nota": "La fuente no indica el aula; confírmalo."
    }
  ]
}
```

Errores posibles: `401` sin sesión, `403` origen no permitido o cuenta fuera
de `AGENT_ALLOWED_EMAILS`, `400` mensaje inválido, `429` límite alcanzado,
`502` respuesta inválida o rechazo de n8n y `504` tiempo de espera agotado.
En modo local no se contacta ningún servicio, por lo que `502` y `504` no
aplican.

## Contrato del webhook en n8n

El workflow debe aceptar `POST`, validar la cabecera `x-kairos-key` y responder
JSON en menos de 55 segundos.

1. **Webhook** (`POST`, ruta sugerida `asistente-academico`).
   - Autenticación: *Header Auth* con nombre `x-kairos-key` y el mismo valor de
     `N8N_SHARED_SECRET`.
   - Respuesta: *Respond to Webhook* con JSON (no texto plano).
2. **Nodo de modelo** (AI Agent, Basic LLM Chain o llamada HTTP al proveedor).
   Pásale el mensaje, el nombre, el curso y los candidatos opcionales. No le
   pases la base de datos ni credenciales de Moodle.
3. **Normalizador** (Code node): garantiza un objeto con `texto` y `acciones`.
   Si el modelo devuelve un bloque ` ```acciones ` dentro del texto, extráelo
   aquí. El servidor acepta también `respuesta`, pero `texto` es el nombre
   preferido.
4. **Respond to Webhook**: devuelve el objeto normalizado.

Ejemplo de respuesta del webhook:

```json
{
  "texto": "Para decidir necesito dos datos que no aparecen en la instrucción: la fecha del taller y su ponderación. ¿Los tienes?",
  "acciones": []
}
```

### Acciones

`acciones` es una lista. Cada elemento debe ser un objeto. La interfaz reconoce:

| Campo | Uso |
| --- | --- |
| `tipo` | `crear_actividad` para habilitar «Preparar en el formulario»; cualquier otro valor se muestra solo como sugerencia. |
| `titulo` | Nombre de la actividad (máximo 100 caracteres en el formulario). |
| `materia` | Nombre exacto de una materia existente; si no coincide, se usa la primera del formulario. |
| `categoria` | Código del catálogo: `INF`, `ACT`, `TAR`, `TAL`, `QUI`, `EXP`, `PRO`, `PAR` o `FIN`. |
| `fecha` | `YYYY-MM-DDTHH:MM`. Si el formato no es válido, el campo queda vacío. |
| `ponderacion` | Número entre 0 y 100, solo si la fuente lo declara o la persona lo confirma. |
| `horas` | Número positivo; si falta, el formulario usa su sugerencia por tipo. |
| `nota` | Texto que se copia como instrucción de origen para revisión. |

El servidor descarta acciones que no sean objetos, que superen 4 KB o que
excedan el total permitido. La interfaz nunca ejecuta una acción directamente.

## Prompt del sistema sugerido para n8n

```text
Eres el asistente académico de KAIROS para estudiantes de Ciencias de Datos.
Ayudas a leer instrucciones, comparar entregas y preparar registros.

Reglas obligatorias:
1. No inventes fechas, ponderaciones, prioridades ni horas. Si faltan, dilo y
   pide el dato.
2. No afirmes que guardaste, editaste o eliminaste algo. No tienes esa
   capacidad. Tus propuestas solo abren el formulario para revisión humana.
3. Distingue hechos de la fuente, supuestos y preguntas. Señala ambigüedades y
   fechas o porcentajes en conflicto.
4. No sumes porcentajes de materias distintas ni prometas una nota.
5. No pidas contraseñas, tokens ni datos de terceros.
6. Responde en español claro y breve. Cuando propongas una actividad, usa el
   arreglo "acciones" con el esquema acordado y explica qué debe verificar la
   persona.
```

## Probar el asistente

Con el servidor Python en marcha y una sesión iniciada, desde PowerShell:

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Method Post -Uri http://localhost:3001/api/auth/login `
  -WebSession $session -ContentType "application/json" `
  -Body '{"email":"tu-correo","password":"tu-contraseña"}'

Invoke-RestMethod -Method Get -Uri http://localhost:3001/api/agent/status `
  -WebSession $session

Invoke-RestMethod -Method Post -Uri http://localhost:3001/api/agent `
  -WebSession $session -ContentType "application/json" `
  -Headers @{ Origin = "http://localhost:3001" } `
  -Body '{"mensaje":"Taller de estadística, vale 15%, entrega el 5 de noviembre de 2026, 3 horas"}'
```

En modo local la última llamada devuelve un texto con candidatos y una acción
`crear_actividad`; no se guarda nada. En modo n8n, si la respuesta es `502`,
revisa la autenticación por cabecera en n8n y que el nodo de respuesta devuelva
JSON con `texto`. Si es `504`, reduce el tiempo del modelo o activa una
respuesta intermedia.

## Cambiar o desactivar el modo remoto

Configura `AGENT_MODE=local` y reinicia el servidor para usar solo reglas
locales, aunque el webhook siga definido. Para volver a n8n, usa
`AGENT_MODE=auto` o `AGENT_MODE=n8n`. Si borras `N8N_WEBHOOK_URL` y
`N8N_SHARED_SECRET` con `AGENT_MODE=auto`, el asistente local sigue funcionando:
la vista no se desactiva y la revisión local de instrucciones permanece
disponible en el formulario de actividades.
