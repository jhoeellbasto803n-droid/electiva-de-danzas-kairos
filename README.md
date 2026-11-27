# ELECTIVA DE DANZAS — Organizador académico

Prototipo local de la aplicación académica descrita en los documentos del proyecto. Centraliza actividades, ponderaciones, tiempos estimados y fechas; compara planes explicables y conserva la decisión final en manos del estudiante. El agente de IA y las conexiones de cuenta quedan para una etapa posterior.

## Cómo abrirlo

1. Mantén juntos los archivos de esta carpeta.
2. Abre `index.html` en un navegador moderno.
3. No requiere instalación ni cuenta. Las actividades y sesiones se guardan en el almacenamiento local de ese navegador.

Al abrir por primera vez aparecen datos de demostración inspirados en el ejemplo del proyecto. El aviso permite retirar las tareas de muestra y conservar lo que agregues o importes.

## Funciones

- Crear, editar y eliminar materias, incluida la nota actual usada como contexto.
- Crear, editar, completar y eliminar tareas, talleres, exámenes y sesiones de estudio.
- Guardar fechas, ponderaciones, horas, opcionalidad y texto de origen.
- Confirmar manualmente fechas y ponderaciones antes de usar una actividad en la priorización.
- Ver agenda, pendientes, búsqueda, filtros y carga de las próximas jornadas.
- Comparar planes por prioridad combinada, ponderación o cercanía de la fecha. Cada escenario muestra qué actividades caben completas, cuánto tiempo ocuparían y cuáles quedarían fuera.
- Temporizador de concentración de 25 o 50 minutos. Puedes asociar la sesión a una actividad; se registran minutos realizados y aparecen en la ficha de esa actividad.
- Importar calendarios `.ics` y archivos `.csv` desde la vista **Conectar plataformas**.
- Exportar o restaurar una copia JSON de actividades, materias, preferencias y sesiones.
- Módulo `ai-agent.js` reservado para integrar un agente después.

## Importación de calendario

La importación se procesa en el navegador. En archivos `.ics` admite eventos y tareas VTODO; usa la propiedad `DUE` si existe y, si no, `DTSTART`. La fecha debe revisarse porque puede representar otra cosa, y los calendarios recurrentes no se expanden. Para CSV, se espera una columna de actividad/título y otra de fecha/fecha límite.

Las actividades importadas quedan en **Por confirmar**. Si el archivo no contiene ponderación u horas, se asignan valores temporales (0% y 1 hora) para que se completen manualmente antes de priorizar. Esta función importa un archivo exportado; no inicia sesión ni sincroniza cambios en vivo con Moodle, Canvas, Teams u otro portal.

## Lógica y límites

El índice combina urgencia (45%), ponderación (40%) y contexto de la nota actual (15%), con un ajuste leve para actividades opcionales. Es una heurística inicial, no una fórmula validada ni una predicción de calificaciones. El plan selecciona actividades completas dentro de las horas declaradas; aún no divide una tarea en bloques diarios. Los escenarios muestran actividades y horas sin sumar porcentajes de materias distintas como si fueran una sola nota.

## Agente de IA futuro

`ai-agent.js` es el punto de extensión. La arquitectura prevista separa: (1) extracción probabilística de texto; (2) reglas deterministas para validar fechas, ponderaciones y ambigüedad; y (3) optimización y escenarios. Las extracciones inciertas deben requerir confirmación del estudiante. El prototipo no se conecta a plataformas en vivo, no hace trabajos y no los entrega.
