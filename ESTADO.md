# Estado de esta copia

**ACTIVA — agente local con modelo propio y reglas de la app.**

Propósito: avanzar con el asistente académico sin depender de n8n ni de un
servicio externo, pero con capacidad de responder preguntas generales mediante
un modelo que corre en la misma máquina.

## Decisiones de esta copia

- No hay `AGENT_MODE`, `N8N_WEBHOOK_URL` ni `N8N_SHARED_SECRET`. No hay lógica
  n8n en `app.py`. La integración remota sigue intacta en
  `electiva-de-danzas-python-n8n-espera`.
- `agente_local.py` calcula siempre el análisis determinista: es la fuente de
  verdad para datos, advertencias y acciones.
- El modelo local se usa **solo para preguntas generales**. Los temas de KAIROS,
  las funciones de la app, las instrucciones y cualquier pregunta sobre datos
  de la cuenta se responden con reglas, sin consultar a Ollama ni a Wikipedia.
- `datos_cuenta.py` responde en **modo solo lectura** preguntas sobre materias,
  actividades pendientes o completadas, notas, prioridad P, cuaderno, horas y
  resumen de la cuenta. Lee `planner_data` de la sesión autenticada, excluye los
  ejemplos `demo: true`, devuelve `acciones: []` y no escribe en PostgreSQL.
- Esa rama no llama a Ollama ni a Wikipedia: los datos de la cuenta nunca salen
  del servidor. Si no puede leer el plan, lo dice y no inventa información.
- Preguntas sobre funciones de la app («¿Qué actividades hay en la app?») e
  instrucciones («Tengo un parcial el 15/03») no se confunden con consultas de
  cuenta; siguen el flujo determinista normal.
- `modelo_local.py` conecta con Ollama en `http://127.0.0.1:11434` (solo
  localhost). Si no responde, `app.py` usa el análisis determinista sin error
  para el cliente.
- El prompt del modelo incluye las reglas no negociables de la app: la persona
  decide, no se inventan fechas/ponderaciones/materias, no se suman porcentajes
  de materias distintas, no se promete nota, no se inventan fuentes, español
  claro y aviso de privacidad previo.
- El modelo nunca decide acciones: `app.py` conserva las del análisis local.
  Solo se conservan las URLs que realmente vinieron de una búsqueda; cualquier
  referencia inventada se elimina antes de mostrar la respuesta.
- `WEB_PUBLICA=1` consulta Wikipedia (HTTPS, máximo 3 resultados) solo para
  preguntas generales. Sale el texto de la búsqueda, no el mensaje completo.
- El aviso de privacidad y las etiquetas de la vista se ajustan solo si hay
  modelo o web activos; se conserva la vista «Conectar plataformas» y la
  versión de Node no se modificó.
- No se entrena un modelo desde cero: se integra uno existente con Ollama.

## Variables nuevas

```dotenv
MODELO_LOCAL_NOMBRE=llama3.2:3b
MODELO_LOCAL_URL=http://127.0.0.1:11434
MODELO_LOCAL_TIMEOUT=60
WEB_PUBLICA=1
WEB_TIMEOUT=10
```

Sin `MODELO_LOCAL_NOMBRE`, la copia funciona exactamente como la versión
determinista anterior.

## Verificación

- `py_compile` de `app.py`, `agente_local.py`, `modelo_local.py` y
  `datos_cuenta.py`: OK.
- `node --check` de `agent-chat.js` y `ai-agent.js` con Node v24.21.0: OK.
- Pruebas sintéticas de `datos_cuenta.py`: detección de consultas, pendientes,
  completadas, materias/notas, P por actividad, cuaderno, semana, conteo, filtro
  por materia, sin datos, solo ejemplos y datos malformados: OK.
- Se verificó que «¿Qué actividades hay en la app?» y «¿Qué materias hay en
  KAIROS?» no se tratan como consultas de cuenta: OK.
- Se cubrieron «¿Cuál es mi P?» y «¿Tengo algo para mañana/esta semana?» sin
  confundirlos con preguntas generales: OK.
- Simulación de Ollama y Wikipedia: OK.
- Prompt con reglas, filtro de acciones inventadas, conservación de acciones
  legítimas, aviso de privacidad dinámico y fallback ante fallo del modelo: OK.
- Anti-alucinaciones: preguntas sobre datos de cuenta y sobre la app no van al
  modelo; reglas del índice P intactas; URLs inventadas eliminadas; sin web no
  aparecen URLs. OK.
- Ollama 0.40.16 instalado con winget. Modelo `llama3.2:3b` descargado y
  verificado (≈2 GB). Servidor escuchando en `127.0.0.1:11434`.
- Prueba real con el modelo: conserva fecha 15/03/2026, ponderación 30 % y
  4 horas; devuelve solo la acción propuesta por las reglas; pregunta general
  con Wikipedia devuelve `acciones: []` y el servidor añade las fuentes. OK.
- Reinicio real del localhost con el código corregido: HTTP 200 en
  `http://127.0.0.1:3001`, servidor dejado en marcha. `/api/agent/status` sin
  sesión responde 401. OK.
- La contraseña de PostgreSQL del `.env` activo no coincide con el servicio
  local; para arrancar se usó en memoria la `DATABASE_URL` de la copia hermana
  `electiva-de-danzas-python`, sin modificar ni copiar `.env`.
- No se crearon cuentas ni se escribió en PostgreSQL.
- Queda pendiente la prueba autenticada real de `/api/agent` con una consulta
  como «¿Qué actividades tengo pendientes?»: falta el correo de la cuenta.

## Git

- Clon local: rama `agente-local-sin-n8n` en `67e313b`. Commits de la sesión:
  `770b345` («Asistente: consultar el plan en modo solo lectura») y `67e313b`
  («Asistente: reconocer preguntas por P y por la semana»).
- `main` sigue en `7ca78ac`, igual que el remoto.
- No se hizo push. La copia en espera y el proyecto original están intactos.
- `ESTADO.md` es una nota local de esta copia; no se versionó en el clon.

No incluye `.venv` ni `.env`. Para ejecutarla, toma esos archivos de
`../electiva-de-danzas-python` o define las variables en el entorno.
