# ELECTIVA DE DANZAS — Organizador académico

Aplicación web con registro e inicio de sesión, almacenamiento centralizado en PostgreSQL y datos académicos separados por cuenta. Centraliza actividades, ponderaciones, tiempos estimados y fechas; compara planes explicables y conserva la decisión final en manos del estudiante. El agente de IA y las integraciones institucionales quedan para una etapa posterior.

## Cómo abrirlo

En Windows, inicia `INICIAR-ELECTIVA.bat`. La primera vez completa `.env` cuando el Bloc de notas se abra, comprueba que PostgreSQL esté iniciado y que exista la base `electiva_danzas`; luego vuelve a ejecutar el iniciador. Mantén la ventana del servidor abierta y visita `http://localhost:3000`. El iniciador usa `npm.cmd`, que funciona desde Windows PowerShell sin cambiar su política de ejecución.


1. Instala Node.js 20 o superior y PostgreSQL.
2. Crea una base de datos llamada `electiva_danzas` (por ejemplo: `psql -U postgres -c "CREATE DATABASE electiva_danzas;"`).
3. Copia `.env.example` como `.env`; actualiza `DATABASE_URL` y `APP_ORIGIN`. Genera `SESSION_SECRET` con `node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"`.
4. Ejecuta `npm install` y después `npm start`.
5. Abre `http://localhost:3000` y crea una cuenta. Cada cuenta recibe datos de demostración de danza que puedes retirar desde el resumen.

La aplicación requiere el servidor para iniciar sesión y sincronizar materias y actividades. No abras `index.html` directamente.

## Funciones

- Tipografía local Inter para lectura y Poppins para títulos; las fuentes se sirven desde el proyecto y no requieren que el navegador dependa de Google Fonts.
- Tema oscuro de alto contraste, alternable con el tema claro desde la barra superior o Preferencias.
- Cinco sistemas de priorización seleccionables y persistentes. La selección reorganiza las sugerencias, el puntaje y la distribución semanal.
- Crear, editar y eliminar materias, incluida la nota actual usada como contexto.
- Crear, editar, completar y eliminar tareas, talleres, exámenes y sesiones de estudio.
- Guardar fechas, ponderaciones, horas, opcionalidad y texto de origen.
- Confirmar manualmente fechas y ponderaciones antes de usar una actividad en la priorización.
- Ver agenda, pendientes, búsqueda, filtros y carga de las próximas jornadas.
- Comparar los cinco sistemas de priorización. Cada escenario muestra qué actividades caben completas, cuánto tiempo ocuparían y cuáles quedarían fuera. El resumen de carga semanal solo suma actividades confirmadas.
- Plan semanal por día: configura tus horas disponibles, repártelas por igual o vacía la semana. El plan distribuye actividades confirmadas en bloques de máximo 90 minutos y detecta horas que no caben antes de la fecha límite. Puedes saltar desde un bloque al temporizador asociado.
- Temporizador de concentración con bloques rápidos de 15, 25 y 50 minutos o duración personalizada entre 1 y 240 minutos. Pausa, continúa, reinicia o guarda una sesión; una alarma sonora avisa al terminar y puedes probarla o desactivarla. Puedes asociar la sesión a una actividad; se registran minutos realizados y aparecen en su ficha.
- Importar calendarios `.ics` y archivos `.csv` desde la vista **Conectar plataformas**.
- Exportar o restaurar una copia JSON de actividades, materias, preferencias y sesiones.
- Módulo `ai-agent.js` reservado para integrar un agente después.
- Registro e inicio de sesión con contraseñas protegidas mediante `scrypt`, cookie de sesión HTTP-only y sesiones persistidas en PostgreSQL.
- API que guarda una copia de planificación JSON independiente por cuenta; los cambios se sincronizan automáticamente y el estado de conexión se muestra en la interfaz.
- Perfil visible y cierre de sesión para separar sesiones en dispositivos compartidos.

## Importación de calendario

La lectura de archivos `.ics` y `.csv` ocurre en el navegador; las actividades importadas se sincronizan con la cuenta después de guardarse. En archivos `.ics` admite eventos y tareas VTODO; usa la propiedad `DUE` si existe y, si no, `DTSTART`. La fecha debe revisarse porque puede representar otra cosa, y los calendarios recurrentes no se expanden. Para CSV, se espera una columna de actividad/título y otra de fecha/fecha límite.

Las actividades importadas quedan en **Por confirmar**. Si el archivo no contiene ponderación u horas, se asignan valores temporales (0% y 1 hora) para que se completen manualmente antes de priorizar. Esta función importa un archivo exportado; no inicia sesión ni sincroniza cambios en vivo con Moodle, Canvas, Teams u otro portal.

## Lógica y límites

Elige entre cinco criterios: equilibrado, fecha más próxima, mayor ponderación, tareas breves primero o materia que necesita apoyo. La elección modifica las recomendaciones, el puntaje y el orden del plan; los escenarios comparan qué cabe en tu disponibilidad. Son heurísticas configurables, no fórmulas validadas ni predicciones de calificaciones. El plan reparte tareas confirmadas entre las horas que declaras para cada día, con sesiones de máximo 90 minutos. Puedes editar cada día, repartir las horas o vaciar la semana. Es una propuesta y no reserva horas reales en un calendario. Los escenarios no suman porcentajes de materias distintas como si fueran una sola nota.

## Autenticación y despliegue

El servidor usa Express, sesiones PostgreSQL y una base de datos PostgreSQL compartida. El pool de conexiones y la estructura permiten comenzar con más de 100 cuentas registradas con uso normal, sujeto a los recursos de la base y del servidor. Esto describe la arquitectura inicial; no es una prueba de carga ni garantiza 100 conexiones simultáneas. `planner_data` mantiene un documento JSONB por usuario con límite de 2 MB; para crecer a miles de usuarios o manejar ediciones simultáneas desde varios dispositivos, el siguiente paso es normalizar actividades y materias en tablas y añadir control de conflictos.

Antes de abrir registros al público, configura HTTPS y un `SESSION_SECRET` aleatorio de al menos 32 caracteres; también conviene añadir verificación de correo y recuperación de contraseña. El prototipo no implementa verificación por correo, recuperación ni pagos.

## Agente de IA futuro

`ai-agent.js` es el punto de extensión. La arquitectura prevista separa: (1) extracción probabilística de texto; (2) reglas deterministas para validar fechas, ponderaciones y ambigüedad; y (3) optimización y escenarios. Las extracciones inciertas deben requerir confirmación del estudiante. El prototipo no se conecta a plataformas en vivo, no hace trabajos y no los entrega. Las tres materias, sus notas y las ponderaciones y fechas de ejemplo son inventadas para mostrar la interfaz; confirma todos esos datos con tu docente antes de usarlos.




## Exportar el horario semanal

Desde **Plan semanal** puedes descargar las sesiones propuestas como CSV compatible con la importación de Google Calendar. Elige una hora inicial; las sesiones se ordenan en secuencia con pausas breves. Revisa los horarios antes de importarlos: la app propone bloques y no sincroniza cambios en vivo.
