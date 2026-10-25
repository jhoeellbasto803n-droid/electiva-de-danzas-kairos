# Historial y pasos realizados

Este documento resume las etapas que construyeron el proyecto y lo que queda conectado en esta entrega.

1. **Base académica:** se partió de los materiales de tutoría académica y del proyecto sustentado de la electiva de danzas. Se diseñó la app alrededor de materias, actividades, notas de contexto, fechas de entrega y horas estimadas.
2. **Organización académica:** se añadieron tareas con confirmación manual, filtros, búsqueda, agenda, recomendación de prioridades y cinco sistemas seleccionables de priorización.
3. **Plan semanal:** se creó la disponibilidad por día, las acciones para repartir o limpiar horas y la propuesta de sesiones de hasta 90 minutos según fechas y carga.
4. **Cuenta y almacenamiento:** se añadió registro e inicio de sesión con contraseñas protegidas, sesiones persistidas y almacenamiento de datos por cuenta en PostgreSQL.
5. **Interfaz:** se incorporaron tema oscuro de alto contraste, tipografías locales Inter y Poppins, navegación entre vistas, controles interactivos y diseño adaptable.
6. **Concentración:** se añadió un temporizador con duración personalizada, pausa, continuación, reinicio, registro de sesiones y alarma sonora configurable.
7. **Datos y plataformas:** se incorporaron importación manual de archivos `.ics` y `.csv`, revisión de los datos antes de priorizar y copia/restauración JSON.
8. **Exportación del horario:** el plan semanal puede descargarse como CSV para abrir en Excel o importar a Google Calendar. Se elige la hora inicial; las sesiones se secuencian con pausas breves. No es una sincronización en vivo.
9. **Dos servidores:** se conservó la implementación Node.js/Express y se creó una implementación Python/Waitress, ambas compatibles con PostgreSQL y ejecutables en Windows con sus archivos `.bat`.
10. **Preparación para IA:** se dejó `ai-agent.js` como punto de extensión. No hay un modelo probabilístico ni proveedor de IA conectado; el análisis actual usa reglas locales y no transmite información académica.
11. **Preparación de publicación:** se documentaron requisitos, configuración y pasos de inicio; se añadieron CSV de prueba y reglas de Git para excluir secretos, dependencias, cachés y bases locales.
12. **Revisión de los cuatro documentos del proyecto:** se normalizaron nueve tipos de actividad, se añadió un revisor local de texto para extraer candidatos y señalar ambigüedad, y se reforzó la confirmación humana antes de usar datos.
13. **Optimización explicable:** los escenarios ahora seleccionan la combinación de actividades que mejor cabe según el criterio activo y la capacidad disponible; muestran por actividad qué queda fuera, sin calcular una nota perdida ficticia. La mejora se comparte entre Node.js y Python.

## Pendiente para integraciones institucionales

La conexión directa a Moodle, Canvas, Teams u otros sistemas requiere identificar la plataforma y versión, confirmar que la institución permite acceso por API y configurar OAuth o credenciales oficiales. Hasta que eso exista, la transferencia es manual mediante archivos de calendario.