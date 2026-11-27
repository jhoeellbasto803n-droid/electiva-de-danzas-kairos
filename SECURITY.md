# Seguridad de KAIROS

## Protección incluida

- Cada usuario puede cambiar la contraseña verificando la actual; al hacerlo se cierran las demás sesiones. La eliminación de cuenta exige contraseña y la frase `ELIMINAR`, y quita el perfil, el plan y las sesiones.
- El modo instalable almacena recursos estáticos. El service worker excluye `/api/` y no cachea actividades, bitácoras ni respuestas privadas.

- Las contraseñas se guardan como derivaciones `scrypt`; nunca se devuelven en la API.
- Las consultas SQL usan parámetros y las operaciones del plan requieren una sesión autenticada. Cada lectura y escritura filtra por el identificador de la cuenta de esa sesión.
- Las sesiones se guardan en PostgreSQL y usan cookies `HttpOnly`, `SameSite=Lax` y `Secure` en producción.
- Las solicitudes que modifican datos validan el origen; la autenticación limita intentos y el servidor limita el cuerpo recibido.
- La API evita almacenar respuestas privadas en la caché del navegador. Se aplican CSP, protección contra marcos, `nosniff` y otras cabeceras.
- El asistente calcula siempre un análisis determinista para KAIROS. Si se configura un modelo en `localhost` (Ollama), este se usa solo para preguntas generales, con las reglas de la app en el prompt; los temas de KAIROS y los datos de la cuenta nunca se envían al modelo. El servidor conserva las acciones del análisis local, descarta acciones inventadas y elimina URLs que no vengan de una búsqueda real. No envía mensajes a un modelo externo ni a n8n. Si `WEB_PUBLICA=1`, el texto de la búsqueda va a Wikipedia por HTTPS y se limita a tres resultados. El servidor toma el identificador de la cuenta de la sesión, exige el origen correcto y limita a 12 consultas por minuto por cuenta. `AGENT_ALLOWED_EMAILS` permite limitar el piloto a correos concretos.
- Las preguntas sobre materias, actividades, notas, prioridad P o cuaderno se responden con `datos_cuenta.py`, que lee el `planner_data` de la cuenta autenticada en modo solo lectura. Esa rama no llama al modelo, no consulta Wikipedia, no escribe en PostgreSQL y devuelve `acciones: []`. Los ejemplos con `demo: true` se excluyen de las respuestas reales.
- El asistente no guarda conversaciones ni escribe en `planner_data`; sus propuestas solo abren el formulario de actividades para revisión y confirmación manual.
- GitHub Actions ejecuta auditorías de dependencias y Dependabot propone actualizaciones.

## Al publicar

1. Configura únicamente secretos en el panel del proveedor: `DATABASE_URL` y `SESSION_SECRET`. No los guardes en GitHub, capturas, mensajes ni archivos compartidos.
2. Usa la URL interna de PostgreSQL del proveedor y mantén la base fuera del acceso público cuando sea posible.
3. Mantén `APP_ORIGIN` igual al dominio HTTPS desde el que se usa la aplicación. Si cambia el dominio, actualiza la variable y vuelve a desplegar.
4. Configura una base de datos persistente con copias de seguridad antes de guardar información real. Los planes gratuitos pueden caducar, suspenderse o carecer de copias.
5. Si activas `MODELO_LOCAL_NOMBRE` o `WEB_PUBLICA`, comprueba que `/api/agent/status` refleje `modeloActivo` y `webActiva`; el aviso de privacidad debe coincidir antes de pedir datos reales.
6. El prototipo aún no tiene verificación de correo, recuperación de contraseña por email ni revisión de seguridad independiente. No hay servicio de correo transaccional conectado.

## Reportar un problema

No publiques contraseñas, datos personales ni detalles que permitan explotar una vulnerabilidad en un issue público. Contacta de forma privada al propietario del repositorio y comparte los pasos para reproducir el problema sin incluir datos reales.
