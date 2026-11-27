# Asistente académico local (modelo con reglas de la app)

Esta copia de KAIROS usa `agente_local.py` y, si se configura, `modelo_local.py`.
No usa n8n ni servicios de modelos remotos. La integración con n8n sigue en la
carpeta hermana `electiva-de-danzas-python-n8n-espera`.

El modelo corre en la misma máquina y recibe **las reglas no negociables de la
app** en el prompt. Solo se usa para **preguntas generales**. Los temas de
KAIROS, las instrucciones y cualquier pregunta sobre datos de la cuenta se
responden con reglas deterministas, sin consultar al modelo: así no se inventan
materias, notas, fechas ni referencias internas. Las consultas de cuenta leen
`planner_data` en modo solo lectura; no lo modifican ni envían esos datos a
Ollama o Wikipedia. El servidor impone además las
acciones y elimina cualquier URL que no venga de una búsqueda real. Si se activa
`WEB_PUBLICA`, las preguntas generales consultan Wikipedia: **sale el texto de
la búsqueda**, no el mensaje completo a un proveedor de IA. El aviso de
privacidad lo indica antes de habilitar el campo.

## Flujo

```text
Navegador ──POST /api/agent──▶ Flask (sesión, origen, 12 consultas/min)
                                   │
                                   ├─ consulta de cuenta
                                   │     └── planner_data (solo lectura)
                                   │           └── datos_cuenta.responder_cuenta()
                                   │                 └── acciones = [] · sin modelo ni web
                                   │
                                   ├─ agente_local.responder()  ← siempre, fuente de verdad
                                   │     datos, advertencias y acciones propuestas
                                   │
                                   ├─ tema de KAIROS o datos de la cuenta
                                   │     └── respuesta determinista directa (sin modelo)
                                   │
                                   └─ pregunta general con modelo activo
                                         ├── prompt con las reglas de la app
                                         ├── WEB_PUBLICA=1 → búsqueda en Wikipedia
                                         ├── solo se conservan fuentes recuperadas
                                         └── acciones = las del análisis local
                                                  │
                                        si falla ─┴──▶ respuesta determinista directa
```

## Consultas de solo lectura sobre la cuenta

`datos_cuenta.py` detecta preguntas sobre datos guardados y las responde con
`planner_data` de la sesión autenticada. No escribe, no propone acciones y no
pasa por Ollama ni por Wikipedia. Los ejemplos con `demo: true` se excluyen;
si solo hay ejemplos, la respuesta lo indica.

| Consulta | Respuesta |
| --- | --- |
| `¿Qué actividades tengo pendientes?` | Pendientes reales con materia, tipo, fecha, peso, horas y P por actividad. |
| `¿Qué actividades tengo completadas?` | Solo las marcadas como `done`. |
| `¿Qué tengo esta semana?` / `hoy` / `mañana` / `sin fecha` | Filtro por fecha de vencimiento. |
| `¿Qué materias tengo?` / `¿Qué notas tengo?` | Materias y notas registradas; el promedio es simple y no oficial. |
| `¿Cuál es mi índice P?` | Aclara que el P es por actividad y lista las pendientes ordenadas. |
| `¿Qué hay en mi cuaderno?` | Registros reales de `labEntries` con materia y pregunta. |
| `¿Cuántas actividades pendientes tengo?` | Conteo, sin listar todo. |

La detección descarta instrucciones («Tengo un parcial el 15/03») y preguntas
sobre funciones de la app («¿Qué actividades hay en la app?»). Un fallo de
lectura devuelve una explicación sin inventar datos.

`GET /api/agent/status` devuelve siempre `mode: "local"` y además
`modeloActivo`, `modeloNombre` y `webActiva`.

## Reglas que el modelo debe respetar

Están escritas en `SISTEMA` dentro de `modelo_local.py`:

1. La persona decide: solo se sugiere; nada se guarda, edita, elimina ni envía.
2. No se inventan prioridades, fechas, ponderaciones, horas ni materias.
3. No se suman porcentajes de materias distintas ni se promete una nota.
4. El índice P es `0,45 × I + 0,35 × U + 0,20 × W`; si falta un componente se
   excluye y se renormaliza. Niveles: Crítica ≥80, Alta ≥60, Media ≥40, Baja <40.
   Los cinco modos solo reordenan el plan.
5. Funciones reales: Plan semanal con CSV, Cuaderno de datos privado,
   preferencias y exportación. Avisos internos, sin correos ni push.
6. El aviso de privacidad ya se mostró antes de escribir; no se piden
   contraseñas, tokens ni datos de terceros.
7. Español claro y breve. Si no se sabe algo, se dice.
8. El contexto local prevalece en temas de KAIROS: no se omiten cifras ni avisos.
9. En preguntas generales se usa solo el contexto web; no se mencionan manuales
   ni enlaces que no estén en él. El servidor añade las fuentes de Wikipedia
   aunque el modelo omita la cita.
10. El modelo no tiene acceso a la base de datos ni a las materias, actividades,
    notas o planes de la cuenta. Esas preguntas las responde el servidor en modo
    solo lectura con `datos_cuenta.py`; el modelo nunca las recibe. Si faltan
    datos, se dice y se sugiere verlo en la app; nunca se inventa.
11. Salida exclusivamente JSON con `texto` y `acciones`.

Además de este prompt hay verificaciones en servidor: `app.py` conserva siempre
las acciones del análisis determinista, elimina URLs que no vengan de una
búsqueda real y no envía al modelo los temas de KAIROS ni los datos de cuenta.

## Variables de entorno

| Variable | Obligatoria | Uso |
| --- | --- | --- |
| `AGENT_ALLOWED_EMAILS` | No | Correos separados por coma. Vacío = cualquier cuenta con sesión puede usar el asistente. |
| `MODELO_LOCAL_NOMBRE` | No | Nombre del modelo en Ollama, por ejemplo `llama3.2:3b`. Vacío = solo reglas deterministas. |
| `MODELO_LOCAL_URL` | No | URL de Ollama. Solo se permite HTTP en `localhost`, `127.0.0.1` o `::1`. Por defecto `http://127.0.0.1:11434`. |
| `MODELO_LOCAL_TIMEOUT` | No | Segundos de espera al modelo. Por defecto `60`. |
| `WEB_PUBLICA` | No | `1` activa la búsqueda en Wikipedia; `0` la desactiva. Por defecto `0`. |
| `WEB_TIMEOUT` | No | Segundos de espera a Wikipedia. Por defecto `10`. |

## Instalar Ollama y el modelo

Esto **no entrena** un modelo: usa uno ya entrenado que corre en tu máquina.

1. Instala Ollama (en Windows, con winget):

   ```powershell
   winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
   ```

   También puedes descargar el instalador desde `https://ollama.com/download`.

2. Verifica que el servicio responda:

   ```powershell
   ollama list
   ```

3. Descarga el modelo recomendado para este equipo (CPU, 15 GB de RAM):

   ```powershell
   ollama pull llama3.2:3b
   ```

   Son aproximadamente 2 GB. Modelos más grandes pueden ser lentos sin GPU.

4. Agrega a `.env` (o define las variables en el entorno):

   ```dotenv
   MODELO_LOCAL_NOMBRE=llama3.2:3b
   WEB_PUBLICA=1
   ```

5. Reinicia el servidor Python. En `/api/agent/status` debe aparecer
   `modeloActivo: true` y `webActiva: true`.

Si Ollama no está corriendo, el modelo no tira la app: se usa el agente de
reglas automáticamente. Si `WEB_PUBLICA=1` pero Wikipedia no responde, el
modelo contesta sin contexto y lo dice.

## Probar que el modelo respeta las reglas

Con Ollama corriendo y las variables definidas:

```powershell
.\.venv\Scripts\python.exe -c "from modelo_local import responder_modelo; from agente_local import responder; m='Taller de estadística, entrega el 15/03/2026, vale 30%, 4 horas'; local=responder(m); print(responder_modelo(m, local, buscar_web=False))"
```

Comprueba que:

- El texto conserva la fecha, el porcentaje y las horas del análisis local.
- No aparece una materia, fecha ni ponderación que no estuviera en el mensaje.
- `acciones` contiene como máximo la propuesta del análisis local.

Si quieres cambiar de modelo:

```powershell
ollama pull qwen2.5:3b
```

y actualiza `MODELO_LOCAL_NOMBRE=qwen2.5:3b` en `.env`.

## API

### `GET /api/agent/status`

```json
{
  "mode": "local",
  "configured": true,
  "allowed": true,
  "allowlistConfigured": false,
  "available": true,
  "message": "Asistente local activo. Usa el modelo local llama3.2:3b con las reglas de la app; las acciones siguen siendo propuestas revisadas por el servidor. Las preguntas generales consultan Wikipedia; solo sale el texto de la búsqueda.",
  "modeloActivo": true,
  "modeloNombre": "llama3.2:3b",
  "webActiva": true
}
```

### `POST /api/agent`

Requiere sesión y el encabezado `Origin` del mismo sitio.

- Mensaje de 1 a 4000 caracteres.
- Límite de 12 solicitudes por minuto por cuenta (HTTP 429 al superarlo).
- Siempre se calcula el análisis determinista. Con modelo activo, el modelo
  redacta la respuesta respetando ese análisis y las reglas; sin modelo, se
  devuelve el análisis directamente.
- Solo se consulta Wikipedia para preguntas generales detectadas por
  `es_general()`.
- Máximo 10 acciones normalizadas, siempre validadas contra la cuenta.

Solicitud:

```json
{ "mensaje": "¿Qué es la fotosíntesis?" }
```

Errores posibles: `401` sin sesión, `403` origen no permitido o cuenta fuera
de `AGENT_ALLOWED_EMAILS`, `400` mensaje inválido, `429` límite alcanzado y
`500` error inesperado. Los fallos del modelo o de la web no se devuelven como
`502`/`504`: se convierten en una respuesta local de respaldo.

## Esquema de acciones

| Campo | Uso |
| --- | --- |
| `tipo` | `crear_actividad` habilita «Preparar en el formulario». |
| `titulo` | Nombre de la actividad, máximo 100 caracteres. |
| `materia` | Nombre detectado. El servidor lo confirma contra las materias de la cuenta; si no coincide, lo quita y lo deja como nota. |
| `categoria` | Código del catálogo: `INF`, `ACT`, `TAR`, `TAL`, `QUI`, `EXP`, `PRO`, `PAR` o `FIN`. |
| `fecha` | `AAAA-MM-DDTHH:MM`, solo si hay una fecha principal válida. |
| `ponderacion` | Número de 0 a 100, solo si la fuente la declara. |
| `horas` | Número positivo, solo si aparece en el texto. |
| `nota` | Recordatorio de revisión contra la fuente original. |

La interfaz nunca ejecuta una acción por su cuenta.

## Límites

- El modelo no se entrena aquí y puede equivocarse. El prompt, las reglas y la
  validación de acciones lo mitigan, pero no lo garantizan. Verifica las
  respuestas importantes.
- La web se limita a Wikipedia; no hay navegación arbitraria ni acceso a la
  base de datos de la app.
- No hay n8n, correos ni notificaciones push.
- No se prometen notas ni se suman porcentajes de materias distintas.
