# Asistente académico con n8n

Esta guía describe el asistente opcional de la versión Python de KAIROS. El
navegador habla con Flask; Flask habla con un webhook de n8n; n8n decide qué
modelo usa. La URL del webhook y la clave compartida nunca se envían al
navegador.

```
Navegador  ──POST /api/agent──▶  Flask (sesión, origen, límites)
                                     │
                                     ├── x-kairos-key ──▶  Webhook n8n
                                     │                        │
                                     │                        └── Modelo / herramientas
                                     ◀── {texto, acciones} ───┘
```

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
   permite escribir hasta que la persona lo acepta. La conversación vive solo
   en memoria: no se guarda en PostgreSQL ni en `localStorage`.

## Variables de entorno

Añade estas variables al `.env` del servidor (o al panel del proveedor):

| Variable | Obligatoria | Uso |
| --- | --- | --- |
| `N8N_WEBHOOK_URL` | Sí | URL completa del webhook de producción. Debe usar HTTPS; solo se admite HTTP en `localhost`/`127.0.0.1` con `APP_ENV=development`. Sin ruta extra, parámetros ni fragmento. |
| `N8N_SHARED_SECRET` | Sí | Valor aleatorio largo. Flask lo envía en la cabecera `x-kairos-key`; n8n debe rechazar cualquier otra clave. |
| `AGENT_ALLOWED_EMAILS` | No | Correos separados por coma. Si está vacío, cualquier cuenta con sesión puede usar el asistente. Úsalo para un piloto cerrado. |

Si falta `N8N_WEBHOOK_URL` o `N8N_SHARED_SECRET`, el asistente queda
desactivado. `GET /api/agent/status` responde `configured: false` y la interfaz
muestra «Sin configurar»; la revisión local sigue funcionando.

Ejemplo:

```dotenv
N8N_WEBHOOK_URL=https://n8n.example.edu/webhook/asistente-academico
N8N_SHARED_SECRET=cambia-esto-por-un-secreto-largo-y-aleatorio
AGENT_ALLOWED_EMAILS=estudiante1@unicafam.edu.co,estudiante2@unicafam.edu.co
```

## API del servidor Python

### `GET /api/agent/status`

Requiere sesión. Devuelve el estado sin llamar a n8n:

```json
{
  "configured": true,
  "allowed": true,
  "allowlistConfigured": true,
  "available": true,
  "message": "Asistente conectado mediante n8n."
}
```

`available` es `configured && allowed`. La interfaz usa este valor para
habilitar o deshabilitar el formulario.

### `POST /api/agent`

Requiere sesión y el encabezado `Origin` del mismo sitio. Límites:

- 12 solicitudes por minuto por cuenta (HTTP 429 al superarlo).
- Mensaje de 1 a 4000 caracteres.
- Contexto opcional (`candidatos`, `advertencias`) de hasta 8 KB cada uno.
- Espera máxima de 55 segundos al webhook.
- Respuesta máxima de 96 KB; el texto se recorta a 12 000 caracteres.
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
resultado de la revisión local sin reenviar el texto original. El servidor
**añade** estos campos, que el navegador no puede falsificar:

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
`503` asistente sin configurar, `502` respuesta inválida o rechazo de n8n y
`504` tiempo de espera agotado.

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

## Prompt del sistema sugerido

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

## Probar el webhook

Con el servidor Python en marcha y una sesión iniciada, desde PowerShell:

```powershell
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
Invoke-RestMethod -Method Post -Uri http://localhost:3001/api/login `
  -WebSession $session -ContentType "application/json" `
  -Body '{"email":"tu-correo","password":"tu-contraseña"}'

Invoke-RestMethod -Method Post -Uri http://localhost:3001/api/agent `
  -WebSession $session -ContentType "application/json" `
  -Headers @{ Origin = "http://localhost:3001" } `
  -Body '{"mensaje":"¿Cómo ordeno un parcial y un taller la misma semana?"}'
```

Si la respuesta es `503`, revisa que `N8N_WEBHOOK_URL` y
`N8N_SHARED_SECRET` estén definidos y que el servidor se haya reiniciado. Si es
`502`, revisa la autenticación por cabecera en n8n y que el nodo de respuesta
devuelva JSON con `texto`. Si es `504`, reduce el tiempo del modelo o activa
una respuesta intermedia en n8n.

## Desactivar el asistente

Borra `N8N_WEBHOOK_URL` y `N8N_SHARED_SECRET` y reinicia el servidor. La vista
seguirá existiendo, mostrará «Sin configurar» y no enviará nada. La revisión
local de instrucciones no depende de n8n y sigue disponible en el formulario de
actividades.
