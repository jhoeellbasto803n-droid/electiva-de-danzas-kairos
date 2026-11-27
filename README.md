# KAIROS — Electiva de Danzas (Python)

Version Python de la aplicación académica. Conserva la interfaz web, el planificador por cuenta, las materias y actividades, el cronómetro con alarma, los modos de priorización y el tema oscuro. El espacio del agente de IA queda preparado, sin activarlo todavía.

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

Waitress ejecuta la aplicación con hilos y el pool de PostgreSQL reutiliza conexiones. La configuración inicial contempla decenas de solicitudes simultáneas y cuentas de más de 100 usuarios. Para publicar la aplicación a un grupo institucional se debe desplegar en un servidor con HTTPS, configurar `APP_ENV=production`, `APP_ORIGIN` con el dominio real, `HOST=0.0.0.0` detrás de un proxy confiable, y dimensionar el pool y el número de hilos según el servidor. El equipo local no debe exponerse directamente a Internet.

## Estructura

- `app.py`: autenticación, sesiones PostgreSQL, almacenamiento del plan, API y servidor Waitress.
- `static/`: interfaz y lógica de navegador reutilizadas de la versión 2.1.0.
- `static/fonts/`: fuentes Inter y Poppins locales con sus licencias OFL.
- `requirements.txt`: dependencias Python.
- `.env.example`: plantilla de configuración; duplica como `.env` para uso local.
- `.vscode/launch.json`: configuración para depurar con VS Code.
- `INICIAR-PYTHON.bat`: prepara las dependencias la primera vez y ejecuta la app.

## Exportar el horario semanal

Desde **Plan semanal** puedes descargar las sesiones propuestas como CSV compatible con la importación de Google Calendar. Elige una hora inicial; las sesiones se ordenan en secuencia con pausas breves. Revisa los horarios antes de importarlos: la app propone bloques y no sincroniza cambios en vivo.
