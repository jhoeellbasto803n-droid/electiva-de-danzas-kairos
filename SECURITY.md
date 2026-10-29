# Seguridad de KAIROS

## Protección incluida

- Cada usuario puede cambiar la contraseña verificando la actual; al hacerlo se cierran las demás sesiones. La eliminación de cuenta exige contraseña y la frase `ELIMINAR`, y quita el perfil, el plan y las sesiones.
- El modo instalable almacena recursos estáticos. El service worker excluye `/api/` y no cachea actividades, bitácoras ni respuestas privadas.

- Las contraseñas se guardan como derivaciones `scrypt`; nunca se devuelven en la API.
- Las consultas SQL usan parámetros y las operaciones del plan requieren una sesión autenticada. Cada lectura y escritura filtra por el identificador de la cuenta de esa sesión.
- Las sesiones se guardan en PostgreSQL y usan cookies `HttpOnly`, `SameSite=Lax` y `Secure` en producción.
- Las solicitudes que modifican datos validan el origen; la autenticación limita intentos y el servidor limita el cuerpo recibido.
- La API evita almacenar respuestas privadas en la caché del navegador. Se aplican CSP, protección contra marcos, `nosniff` y otras cabeceras.
- Por defecto el asistente de la versión Python responde con reglas locales deterministas: no envía el mensaje a internet ni a un modelo externo. Si se configura n8n (`AGENT_MODE=auto` con `N8N_WEBHOOK_URL` y `N8N_SHARED_SECRET`, o `AGENT_MODE=n8n`), solo entonces reenvía el texto al webhook; la URL y la clave compartida no llegan al navegador. En ambos modos exige sesión y origen correcto, limita a 12 consultas por minuto por cuenta y, en modo n8n, espera como máximo 55 segundos y acota el tamaño de la solicitud y la respuesta. `AGENT_ALLOWED_EMAILS` permite cerrar el piloto a correos concretos. Sus propuestas nunca se guardan sin confirmación humana.
- GitHub Actions ejecuta auditorías de dependencias y Dependabot propone actualizaciones.

## Al publicar

1. Configura únicamente secretos en el panel del proveedor: `DATABASE_URL` y `SESSION_SECRET`. No los guardes en GitHub, capturas, mensajes ni archivos compartidos.
2. Usa la URL interna de PostgreSQL del proveedor y mantén la base fuera del acceso público cuando sea posible.
3. Mantén `APP_ORIGIN` igual al dominio HTTPS desde el que se usa la aplicación. Si cambia el dominio, actualiza la variable y vuelve a desplegar.
4. Configura una base de datos persistente con copias de seguridad antes de guardar información real. Los planes gratuitos pueden caducar, suspenderse o carecer de copias.
5. El prototipo aún no tiene verificación de correo, recuperación de contraseña por email ni revisión de seguridad independiente. No hay servicio de correo transaccional conectado.

## Reportar un problema

No publiques contraseñas, datos personales ni detalles que permitan explotar una vulnerabilidad en un issue público. Contacta de forma privada al propietario del repositorio y comparte los pasos para reproducir el problema sin incluir datos reales.
