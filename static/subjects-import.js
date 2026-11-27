/* KAIROS · importación segura de materias desde JSON, CSV o Excel (.xlsx). */
(() => {
  "use strict";

  const MAX_FILE_BYTES = 2 * 1024 * 1024;
  const app = () => window.Electiva;
  const state = () => app()?.getState?.();

  function toast(message) {
    if (app()?.toast) app().toast(message);
    else console.info(message);
  }

  async function parseOnServer(file) {
    const form = new FormData();
    form.append("file", file, file.name);
    const response = await fetch("/api/subjects/import", {
      method: "POST",
      body: form,
      credentials: "same-origin",
      headers: { "X-Requested-With": "KAIROS" }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "No pude leer ese archivo.");
    return data;
  }

  function existingNames() {
    const subjects = (state() && state().subjects) || [];
    return new Set(subjects.map(s => String(s.name || "").toLocaleLowerCase("es-CO")));
  }

  async function onFile(event) {
    const input = event.target;
    const file = input.files && input.files[0];
    if (!file) return;
    try {
      if (file.size > MAX_FILE_BYTES) throw new Error("El archivo supera el límite de 2 MB.");
      const parsed = await parseOnServer(file);
      const incoming = Array.isArray(parsed.subjects) ? parsed.subjects : [];
      const existing = existingNames();
      const fresh = incoming.filter(s => s && s.name && !existing.has(String(s.name).toLocaleLowerCase("es-CO")));
      const skippedDuplicates = incoming.length - fresh.length;
      const warnings = Array.isArray(parsed.warnings) ? parsed.warnings : [];

      if (!fresh.length) {
        toast(skippedDuplicates ? "Todas esas materias ya están registradas." : "No encontré materias nuevas para importar.");
        return;
      }

      const sample = fresh.slice(0, 5).map(s => `• ${s.name}${s.grade == null ? " (sin nota)" : ` · ${s.grade}/5`}`).join("\n");
      const more = fresh.length > 5 ? `\n… y ${fresh.length - 5} más` : "";
      const message =
        `¿Importar ${fresh.length} materia(s) nueva(s)?` +
        (skippedDuplicates ? `\n(${skippedDuplicates} duplicada(s) se omitirán)` : "") +
        (warnings.length ? `\nAvisos: ${warnings.length}` : "") +
        `\n\n${sample}${more}` +
        `\n\nNo se guarda nada hasta que confirmes. Las notas que falten quedan vacías; no se inventan.`;
      if (!window.confirm(message)) return;

      const st = state();
      if (!st) throw new Error("La app no está lista.");
      st.subjects = st.subjects || [];
      for (const s of fresh) {
        st.subjects.push({
          id: app().uid(),
          name: String(s.name).trim().slice(0, 80),
          grade: s.grade == null ? null : Number(s.grade),
          demo: false
        });
      }
      app().save();
      app().render();
      toast(`${fresh.length} materia(s) importada(s). La priorización sigue usando KAIROS-P-1.0; tú decides.`);
    } catch (err) {
      toast(err.message || "No pude importar materias.");
    } finally {
      input.value = "";
    }
  }

  function bind() {
    const button = document.getElementById("import-subjects");
    const input = document.getElementById("import-subjects-file");
    if (!button || !input || button.dataset.kairosBound === "1") return;
    button.dataset.kairosBound = "1";
    button.addEventListener("click", () => input.click());
    input.addEventListener("change", onFile);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind, { once: true });
  }
  bind();
})();
