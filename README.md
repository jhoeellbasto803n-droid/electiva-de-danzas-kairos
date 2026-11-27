# KAIROS — Ciencias de Datos (Python)

Versión Python del organizador KAIROS para estudiantes de Ciencias de Datos. Incluye materias y actividades ficticias de Python/pandas, estadística, bases de datos, aprendizaje automático y visualización; planificador por cuenta, cronómetro con alarma, cinco modos de priorización, cuaderno privado de experimentos, controles de cuenta y aplicación instalable. Incluye el revisor local de instrucciones y un asistente académico con reglas deterministas para KAIROS y, de forma opcional, un modelo que corre en tu máquina y recibe esas mismas reglas. El servidor verifica las acciones para que el modelo no invente datos. El asistente también consulta en modo solo lectura las materias, actividades, notas, prioridad P y cuaderno de la cuenta autenticada, sin modificar nada. Si se activa la búsqueda web, las consultas generales van a Wikipedia; nunca se usa un modelo remoto ni n8n en esta copia.

El servidor Python sustituye a Express y conserva las rutas `/api` que usa la interfaz. Las cuentas y los planes se guardan en PostgreSQL usando las mismas tablas `app_users` y `planner_data`; la sesión del servidor Python usa su propia tabla `kairos_python_sessions`. La versión Node puede seguir en la misma carpeta original y usar la misma base de datos. Esta copia abre por defecto en el puerto **3001**, para que las dos versiones puedan convivir.

## Inicio rápido en Windows

1. Instala PostgreSQL y crea la base de datos `electiva_danzas` si todavía no existe. En pgAdmin: clic derecho en **Databases → Create → Database**, escribe `electiva_danzas` y guarda. No hace falta crear tablas manualmente.
2. Haz doble clic en `INICIAR-PYTHON.bat`.
3. La primera vez el programa genera automáticamente una clave de sesión y abre `.env` en el Bloc de notas. Reemplaza `TU_PASSWORD` por la contraseña de PostgreSQL. Guarda y cierra el archivo.
4. Ejecuta `INICIAR-PYTHON.bat` otra vez. El programa crea `.venv`, descarga las bibliotecas y arranca el servidor.
5. Abre **http://localhost:3001** en el navegador y crea tu cuenta.

Si la contraseña de PostgreSQL contiene caracteres especiales como `@`, `:` o `/`, codifícalos para URL dentro de `DATABASE_URL` (por ejemplo, `@` se escribe `%40`). Si tu usuario, servidor o nombre de base son distintos, actualiza también esa parte de `DATABASE_URL`. El archivo `.env` es privado y está excluido del ZIP.

## Abrir y trabajar en Visual Studio Code

Abre esta carpeta desde VS Code con **Archivo → Abrir carpeta…**. Selecciona `electiva-de-danzas-python`. También puedes abrir una terminal en esta carpeta y ejecutar `code .`.

Después de crear `.venv`, selecciona como intérprete `.venv\Scripts\python.exe` desde **Python: Select Interpreter**. El archivo `.vscode/launch.json` permite iniciar el servidor con **F5** una vez que `.env` esté configurado. El lanzador por lotes ofrece la ruta más sencilla para el uso normal.

## Variables de entorno

| Variable | Uso | Valor inicial |
| --- | --- | --- |
| `DATABASE_URL` | Conexión a PostgreSQL | `postgresql://postgres:TU_PASSWORD@localhost:5432/electiva_danzas` |
| `SESSION_SECRET` | Firma y protección de sesiones | Secreto aleatorio de al menos 32 caracteres |
| `APP_ORIGIN` | Protección contra solicitudes de otro sitio | `http://localhost:3001` |
| `HOST` y `PORT` | Dirección de escucha local | `127.0.0.1` y `3001` |
| `DB_POOL_MAX` | Conexiones PostgreSQL máximas | `30` |
| `WEB_THREADS` | Hilos HTTP de Waitress | `32` |
| `AGENT_ALLOWED_EMAILS` | Correos del piloto separados por coma | Vacío (cualquier cuenta con sesión) |
| `MODELO_LOCAL_NOMBRE` | Modelo de Ollama en la máquina; vacío desactiva el modelo | Vacío |
| `MODELO_LOCAL_URL` | URL local de Ollama | `http://127.0.0.1:11434` |
| `MODELO_LOCAL_TIMEOUT` | Segundos de espera al modelo | `60` |
| `WEB_PUBLICA` | `1` consulta Wikipedia en preguntas generales | `0` |
| `WEB_TIMEOUT` | Segundos de espera a Wikipedia | `10` |

`preparar_configuracion.py` genera automáticamente un secreto aleatorio seguro cuando crea `.env`.

## Instalación manual

Desde esta carpeta, configura `.env` a partir de `.env.example` y ejecuta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

La app crea las tablas necesarias al iniciar; no es necesario usar pgAdmin para crear las tablas a mano. El servidor informa un error claro si no logra conectarse a PostgreSQL.

## Capacidad y despliegue

Waitress ejecuta la aplicación con hilos y el pool de PostgreSQL reutiliza conexiones. Puede guardar más de 100 cuentas con uso normal; no se ha hecho una prueba de carga que garantice 100 conexiones simultáneas. DB_POOL_MAX permite ajustar el pool entre 5 y 100 (30 por defecto); no lo aumentes por encima del límite de conexiones de tu proveedor. Para publicar la aplicación a un grupo institucional se debe desplegar en un servidor con HTTPS, configurar APP_ENV=production, APP_ORIGIN con el dominio real, HOST=0.0.0.0 detrás de un proxy confiable, y dimensionar el pool y el número de hilos según el servidor. El equipo local no debe exponerse directamente a Internet.

En producción Python confía un solo proxy frontal para obtener la IP cliente y el protocolo HTTPS. Conserva ese límite: no configures `ProxyFix` para confiar todos los proxies ni expongas Waitress directamente a Internet. El servidor aplica límites de intentos de autenticación por IP, poda las entradas antiguas de ese limitador, rechaza contraseñas de inicio de sesión mayores al límite admitido, protege las respuestas de API contra caché y requiere el origen correcto también al cerrar sesión. Para producción, usa PostgreSQL con almacenamiento persistente y copias de seguridad; la base gratuita de Render caduca a los 30 días. El asistente añade su propio límite de 12 consultas por minuto y por cuenta. El modelo corre en `localhost` con un tiempo de espera configurable; si no responde, se usa el respaldo determinista. La búsqueda web, si está activa, consulta Wikipedia con su propio tiempo de espera.

## Asistente académico

La vista **Asistente** funciona de inmediato con reglas locales para los temas de KAIROS; no necesita claves. Si se configura `MODELO_LOCAL_NOMBRE`, el modelo corre en tu máquina, recibe las reglas de la app y responde **solo preguntas generales**. Los temas de KAIROS y las instrucciones se responden con reglas. Las preguntas sobre la cuenta («¿qué actividades tengo pendientes?», «¿qué materias tengo?», «¿cuál es mi P?», «¿qué hay en mi cuaderno?») se responden con `datos_cuenta.py`, que lee `planner_data` en modo solo lectura y nunca envía esos datos al modelo ni a Wikipedia. El servidor calcula siempre el análisis determinista, conserva las acciones validadas y elimina URLs no recuperadas. Con `WEB_PUBLICA=1`, las preguntas generales consultan Wikipedia antes de contestar. El navegador envía el mensaje a `POST /api/agent`; el servidor añade el identificador de la cuenta desde la sesión y responde. Antes del primer mensaje se muestra un aviso acorde a la configuración activa; la conversación no se guarda en PostgreSQL ni en `localStorage`.

El asistente puede proponer actividades, pero no las guarda: cada propuesta aparece como una tarjeta con el botón **Preparar en el formulario**, que abre la actividad con los datos sugeridos sin confirmar. La persona revisa fechas, ponderaciones y horas, y confirma manualmente.

Esta copia no tiene modos remotos: la integración con n8n quedó en la carpeta hermana `electiva-de-danzas-python-n8n-espera` para retomarla cuando se defina el proveedor, el modelo y el webhook.

## Estructura

- `app.py`: autenticación, sesiones PostgreSQL, almacenamiento del plan, API, asistente local y servidor Waitress.
- `agente_local.py`: reglas deterministas para temas de KAIROS y respaldo sin modelo.
- `datos_cuenta.py`: consultas de solo lectura sobre `planner_data` (materias, actividades, notas, P y cuaderno); no escribe ni propone acciones.
- `modelo_local.py`: integración opcional con Ollama en localhost y búsqueda en Wikipedia.
- Interfaz web compartida con Node, con cuaderno de datos, exportación CSV y modo instalable.
- `static/agent-chat.js`: vista del asistente; aviso de privacidad, conversación y propuestas que solo abren el formulario.
- `docs/AGENTE-LOCAL.md`: principios, API, esquema de acciones y pruebas del asistente local.
- `requirements.txt`: dependencias Python.
- `.env.example`: plantilla de configuración; duplica como `.env` para uso local.
- `.vscode/launch.json`: configuración para depurar con VS Code.
- `INICIAR-PYTHON.bat`: prepara las dependencias la primera vez y ejecuta la app.

## Revisión de instrucciones y prioridad

En el editor de actividades puedes analizar localmente texto copiado desde un aula virtual. Se muestran candidatos de fechas, porcentajes, horas y categorías normalizadas; varias fechas, pesos o expresiones opuestas quedan señaladas para que revises la fuente. Seleccionar un candidato solo lo copia al formulario; todavía debes verificar y confirmar. El planificador compara combinaciones que caben según el criterio seleccionado y el tiempo disponible, sin estimar una nota perdida ni sumar porcentajes de materias distintas. El plan semanal también admite actividades confirmadas sin fecha límite, sin asignarles una fecha artificial.

## Prioridad y estimaciones

La pantalla Actividades explica los componentes I, U y W, el resultado P y la versión de la fórmula. Si falta una fecha o una ponderación confirmada, no asigna un valor ficticio: excluye el componente y renormaliza los pesos restantes. Las horas sugeridas usan el catálogo de tipos y se ajustan con sesiones de enfoque completadas, acercándose gradualmente al historial personal. Las alertas se muestran dentro de la aplicación; no envían correo ni notificaciones push.

## Exportar el horario semanal

Desde **Plan semanal** puedes descargar las sesiones propuestas como CSV compatible con la importación de Google Calendar. Elige una hora inicial; las sesiones se ordenan en secuencia con pausas breves. Revisa los horarios antes de importarlos: la app propone bloques y no sincroniza cambios en vivo.
