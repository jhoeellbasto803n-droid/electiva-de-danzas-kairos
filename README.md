# KAIROS — Electiva de Danzas

Organizador académico para planear actividades, materias y sesiones de estudio de la electiva de danzas. Incluye dos implementaciones del servidor: **Node.js + PostgreSQL** y **Python + PostgreSQL**. La interfaz web es compartida entre las dos versiones.

## Versiones incluidas

- [`nodejs/`](nodejs/): servidor Express, registro e inicio de sesión, PostgreSQL, interfaz y lanzador de Windows.
- [`python/`](python/): servidor Python/Waitress con las mismas rutas de API, PostgreSQL y lanzador de Windows.
- [`ejemplos/`](ejemplos/): CSV de actividades para probar la importación de la aplicación y CSV de ejemplo para importar en Google Calendar.
- [`HISTORIAL-Y-PASOS.md`](HISTORIAL-Y-PASOS.md): resumen del desarrollo y pasos que se realizaron.

## Funciones actuales

- Registro e inicio de sesión por cuenta; cada usuario guarda sus propios datos en PostgreSQL.
- Materias con nota de contexto y actividades con fecha, ponderación, horas estimadas y confirmación manual.
- Cinco sistemas de priorización con categorías normalizadas (INF, ACT, TAR, TAL, QUI, EXP, PRO, PAR y FIN), además de preferencias de tema claro/oscuro.
- Revisión local de instrucciones: propone candidatos de tipo, fechas, porcentajes y horas; señala contradicciones como «opcional» y «vital». Las propuestas requieren confirmación manual y no se envían a servicios externos.
- Comparación de escenarios con una optimización por capacidad y fecha límite; muestra por actividad qué cabe y qué queda pendiente sin inventar una nota perdida.
- Plan semanal editable por día, que distribuye actividades confirmadas en sesiones de hasta 90 minutos.
- Exportación del plan semanal como CSV con encabezados compatibles con la importación de Google Calendar. La persona elige la hora de inicio; el plan se ordena en secuencia con pausas breves.
- Temporizador de concentración configurable con pausa, continuación y alarma sonora.
- Importación local de calendarios `.ics` y actividades `.csv`; copia/restauración de datos.
- Revisor local de instrucciones disponible; el modelo probabilístico futuro y las conexiones institucionales todavía no están conectados.

La integración con Google Calendar es por archivo CSV. El revisor de texto es determinista y local; no es todavía un modelo probabilístico ni una conexión institucional. Moodle, Canvas, Teams u otros portales institucionales no están conectados en vivo: eso requiere APIs oficiales y autorización de cada institución.

## Requisitos

- PostgreSQL instalado y ejecutándose.
- **Node.js** versión 20 o posterior para `nodejs/`.
- **Python** para `python/`; el lanzador crea un entorno virtual e instala las dependencias declaradas.

Crea una base PostgreSQL llamada `electiva_danzas` desde pgAdmin (**Databases → Create → Database**) o con `psql`. Las tablas de la aplicación se crean al iniciar el servidor; no las crees manualmente.

## Ejecutar la versión Node.js

1. Abre `nodejs/`.
2. Ejecuta `INICIAR-ELECTIVA.bat`. La primera vez prepara la configuración; completa en `.env` la conexión a PostgreSQL y guarda el archivo.
3. Vuelve a ejecutar el lanzador y deja abierta la ventana del servidor.
4. Abre <http://localhost:3000> y crea una cuenta.

Alternativa manual desde la carpeta `nodejs/`: duplica `.env.example` como `.env`, actualiza `DATABASE_URL`, `APP_ORIGIN` y `SESSION_SECRET`, ejecuta `npm install` y `npm start`.

## Ejecutar la versión Python

1. Abre `python/`.
2. Ejecuta `INICIAR-PYTHON.bat`. La primera vez genera la configuración y abre `.env` para que completes la contraseña de PostgreSQL.
3. Guarda y cierra `.env`; vuelve a ejecutar el lanzador. Este crea `.venv`, instala requisitos y arranca el servidor.
4. Abre <http://localhost:3001> y crea una cuenta.

La versión Python reutiliza las tablas `app_users` y `planner_data` y usa una tabla separada para sus sesiones. Las dos versiones pueden convivir en puertos distintos.

## Probar importación y exportación

1. En la aplicación, abre **Conectar plataformas**.
2. Carga `ejemplos/plantilla-prueba-electiva.csv`, asigna una materia e importa las cuatro actividades.
3. En **Actividades**, revisa y confirma manualmente la fecha y la ponderación de cada actividad. Solo las confirmadas entran al plan.
4. Abre **Plan semanal**, asigna disponibilidad, elige la hora inicial y descarga el horario CSV.
5. Para probar en Google Calendar, en un computador abre **Configuración → Importar y exportar**, elige el CSV descargado, selecciona un calendario y pulsa **Importar**. También puedes probar la importación con `ejemplos/horario-prueba-google-calendar.csv`.

Los CSV de Google Calendar requieren encabezados en inglés. La importación crea eventos en el calendario elegido y no mantiene sincronización automática.

## Seguridad y datos

Los archivos `.env`, entornos virtuales, dependencias instaladas, cachés y bases de datos locales están excluidos del repositorio. No publiques tu contraseña de PostgreSQL ni copies tu `.env` a GitHub. Usa `.env.example` como plantilla y coloca tus propios datos solo en el `.env` local.

Las materias, calificaciones, tareas y fechas de demostración son ficticias; verifica los datos académicos con tus docentes.