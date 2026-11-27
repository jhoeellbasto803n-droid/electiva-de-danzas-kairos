/* Integración de IA reservada.
 * El agente todavía no está conectado y nunca cambia ni entrega actividades.
 * Mantener extracción probabilística separada de reglas y optimización.
 * Una futura conexión debe devolver campos candidatos, fuente, confianza y
 * datos por confirmar. El estudiante valida fechas y ponderaciones antes de guardar.
 */
window.KairosAgent = Object.freeze({
  status: "reserved",
  async extractActivityCandidates(sourceText) {
    return {
      available: false,
      message: "El agente aún no está conectado. Registra y verifica los datos manualmente.",
      candidates: [],
      sourceText
    };
  }
});