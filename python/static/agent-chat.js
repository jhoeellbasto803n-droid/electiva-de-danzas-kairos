/* Asistente academico opcional.
 * Conversa con el flujo de n8n a traves de POST /api/agent. Nunca guarda ni
 * modifica actividades: las propuestas solo abren el formulario para revisar.
 */
(() => {
  "use strict";
  const $ = selector => document.querySelector(selector);
  const fold = value => String(value || "").toLocaleLowerCase("es-CO").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  const WELCOME = "Hola. Puedo ayudarte a leer una instrucción, comparar entregas o preparar una actividad. No guardo nada por mi cuenta: cuando propongo una actividad, la cargo en el formulario para que revises cada dato y decidas.";
  const state = { info: null, sending: false, messages: [] };
  const userID = () => String(window.KairosAuth?.user?.id || "local");
  const privacyKey = () => "kairos-agent-privacy:" + userID();

  const el = {};
  ["agent-state", "agent-privacy", "agent-privacy-ok", "agent-log", "agent-form", "agent-input", "agent-hint", "agent-clear", "agent-prompts"].forEach(id => {
    el[id] = document.getElementById(id);
  });
  if (!el["agent-log"] || !el["agent-form"]) return;

  function privacyAccepted() {
    try { return localStorage.getItem(privacyKey()) === "1"; } catch (error) { return false; }
  }
  function acceptPrivacy() {
    try { localStorage.setItem(privacyKey(), "1"); } catch (error) { /* almacenamiento no disponible */ }
  }
  function showPrivacyGate() {
    const accepted = privacyAccepted();
    el["agent-privacy"].hidden = accepted;
    el["agent-form"].hidden = !accepted;
    if (!accepted) el["agent-privacy-ok"]?.focus();
  }

  function setStatus(text, tone) {
    el["agent-state"].textContent = text;
    el["agent-state"].className = "agent-state" + (tone ? " " + tone : "");
  }
  function setBusy(busy) {
    state.sending = busy;
    const button = el["agent-form"].querySelector("button[type=submit]");
    if (button) {
      button.disabled = busy || !(state.info && state.info.available);
      button.textContent = busy ? "Enviando…" : "Enviar";
    }
    el["agent-input"].disabled = busy || !(state.info && state.info.available);
  }
  function setAvailability(info) {
    state.info = info || null;
    const available = !!(info && info.available);
    if (!info) {
      setStatus("Sin comprobar", "off");
    } else if (!info.configured) {
      setStatus("Sin configurar", "off");
    } else if (!info.allowed) {
      setStatus("Cuenta no habilitada", "off");
    } else {
      setStatus("Disponible", "on");
    }
    if (!available) {
      el["agent-hint"].textContent = (info && info.message ? info.message + " " : "") + "La revisión local de instrucciones sigue disponible en el formulario de actividades.";
    } else if (state.sending) {
      el["agent-hint"].textContent = "El asistente está respondiendo. Enter envía, Shift+Enter hace un salto de línea.";
    } else {
      el["agent-hint"].textContent = "El asistente propone; tú confirmas. Enter envía, Shift+Enter hace un salto de línea.";
    }
    setBusy(state.sending);
  }

  async function refreshStatus() {
    if (!window.KairosAgent?.agentStatus) return;
    setStatus("Comprobando…");
    try {
      setAvailability(await window.KairosAgent.agentStatus());
    } catch (error) {
      setStatus("No disponible", "off");
      setAvailability(null);
      el["agent-hint"].textContent = (error.message || "No pude comprobar el asistente.") + " La revisión local sigue disponible en Actividades.";
    }
  }

  function messageNode(role, text, actions) {
    const article = document.createElement("article");
    article.className = "agent-msg " + role;
    const meta = document.createElement("small");
    meta.textContent = role === "user" ? "Tú" : role === "error" ? "Aviso" : "Asistente KAIROS";
    const body = document.createElement("p");
    body.textContent = text;
    article.append(meta, body);
    if (Array.isArray(actions) && actions.length) article.append(actionsNode(actions));
    return article;
  }
  function appendMessage(role, text, actions) {
    state.messages.push({ role, text, actions: actions || [] });
    const node = messageNode(role, text, actions);
    el["agent-log"].append(node);
    el["agent-log"].scrollTop = el["agent-log"].scrollHeight;
    return node;
  }
  function renderHistory() {
    el["agent-log"].textContent = "";
    if (!state.messages.length) state.messages.push({ role: "assistant", text: WELCOME, actions: [] });
    state.messages.forEach(item => el["agent-log"].append(messageNode(item.role, item.text, item.actions)));
    el["agent-log"].scrollTop = el["agent-log"].scrollHeight;
  }

  function textValue(action, keys) {
    for (const key of keys) {
      const value = action[key];
      if (typeof value === "string" && value.trim()) return value.trim();
      if (typeof value === "number" && Number.isFinite(value)) return value;
    }
    return "";
  }
  function actionsNode(actions) {
    const wrap = document.createElement("div");
    wrap.className = "agent-actions";
    actions.forEach((action, index) => {
      if (!action || typeof action !== "object") return;
      const title = textValue(action, ["titulo", "title", "nombre"]);
      const note = textValue(action, ["nota", "notas", "detalle", "texto", "descripcion"]);
      const card = document.createElement("div");
      card.className = "agent-action";
      const heading = document.createElement("strong");
      heading.textContent = (title ? "Propuesta " + (index + 1) + ": " + title : "Sugerencia " + (index + 1));
      card.append(heading);

      const rows = [];
      const subject = textValue(action, ["materia", "subject", "asignatura"]);
      const category = textValue(action, ["categoria", "category", "tipoActividad", "tipo"]);
      const due = textValue(action, ["fecha", "due", "fechaLimite"]);
      const weight = textValue(action, ["ponderacion", "weight", "porcentaje"]);
      const hours = textValue(action, ["horas", "hours", "tiempo"]);
      if (subject) rows.push(["Materia", subject]);
      if (category && category !== "crear_actividad") rows.push(["Tipo", category]);
      if (due) rows.push(["Fecha propuesta", due]);
      if (weight !== "") rows.push(["Ponderación", weight + (typeof weight === "number" ? " %" : "")]);
      if (hours !== "") rows.push(["Horas estimadas", hours]);
      if (note && !title) rows.push(["Detalle", note]);
      if (rows.length) {
        const list = document.createElement("dl");
        rows.forEach(([label, value]) => {
          const dt = document.createElement("dt");
          dt.textContent = label;
          const dd = document.createElement("dd");
          dd.textContent = String(value);
          list.append(dt, dd);
        });
        card.append(list);
      }
      if (note && title) {
        const detail = document.createElement("p");
        detail.className = "fine";
        detail.textContent = note;
        card.append(detail);
      }
      if (title && (category === "" || category === "crear_actividad" || textValue(action, ["tipo"]) === "crear_actividad")) {
        const prepare = document.createElement("button");
        prepare.type = "button";
        prepare.className = "outline";
        prepare.textContent = "Preparar en el formulario";
        prepare.addEventListener("click", () => prepareAction(action));
        card.append(prepare);
      }
      wrap.append(card);
    });
    return wrap;
  }

  function prepareAction(action) {
    const app = window.Electiva;
    if (!app?.openTask) {
      alert("El formulario de actividades todavía no está disponible.");
      return;
    }
    const data = app.getState ? app.getState() : null;
    const subjects = Array.isArray(data?.subjects) ? data.subjects : [];
    const subjectName = fold(textValue(action, ["materia", "subject", "asignatura"]));
    const subject = subjectName ? subjects.find(item => fold(item.name) === subjectName) : null;
    const category = String(textValue(action, ["categoria", "category", "tipoActividad", "tipo"]) || "").toUpperCase();
    const title = textValue(action, ["titulo", "title", "nombre"]);
    const due = textValue(action, ["fecha", "due", "fechaLimite"]);
    const weight = textValue(action, ["ponderacion", "weight", "porcentaje"]);
    const hours = textValue(action, ["horas", "hours", "tiempo"]);
    const note = textValue(action, ["nota", "notas", "detalle", "descripcion"]);
    const validCategory = window.KairosAgent?.catalog?.[category] ? category : "TAR";
    const validDue = typeof due === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(due) ? due : "";
    const numericWeight = weight === "" ? null : Number(String(weight).replace(",", "."));
    const numericHours = hours === "" ? undefined : Number(String(hours).replace(",", "."));
    app.switchView("tasks");
    app.openTask({
      id: "",
      title: String(title || "Actividad propuesta").slice(0, 100),
      subjectId: subject?.id,
      category: validCategory,
      due: validDue,
      weight: Number.isFinite(numericWeight) ? numericWeight : null,
      hours: Number.isFinite(numericHours) && numericHours > 0 ? numericHours : undefined,
      source: (note ? note + "\n\n" : "") + "Propuesta del asistente. Verifica cada dato contra la fuente original antes de guardar.",
      confirmed: false
    });
    app.toast?.("Propuesta cargada. Revisa y confirma cada dato.");
  }

  function splitFence(text) {
    const pattern = /```acciones\s*([\s\S]*?)```/i;
    const match = String(text || "").match(pattern);
    if (!match) return { text: String(text || ""), actions: [] };
    let actions = [];
    try {
      const parsed = JSON.parse(match[1].trim());
      actions = Array.isArray(parsed) ? parsed : Array.isArray(parsed?.acciones) ? parsed.acciones : [];
    } catch (error) {
      actions = [];
    }
    return { text: String(text || "").replace(pattern, "").trim(), actions };
  }
  function mergeActions(primary, secondary) {
    const seen = new Set();
    return [...(Array.isArray(primary) ? primary : []), ...(Array.isArray(secondary) ? secondary : [])].filter(action => {
      if (!action || typeof action !== "object") return false;
      let key = "";
      try { key = JSON.stringify(action); } catch (error) { return false; }
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  async function send() {
    const text = el["agent-input"].value.trim();
    if (!text || state.sending) return;
    if (!privacyAccepted()) { showPrivacyGate(); return; }
    if (!state.info?.available) { refreshStatus(); return; }
    appendMessage("user", text, []);
    el["agent-input"].value = "";
    resize();
    const pending = appendMessage("assistant", "Pensando…", []);
    pending.classList.add("pending");
    setBusy(true);
    try {
      const result = await window.KairosAgent.chat(text);
      const split = splitFence(result.texto);
      const actions = mergeActions(result.acciones, split.actions);
      pending.remove();
      state.messages.pop();
      appendMessage("assistant", split.text || result.texto, actions);
    } catch (error) {
      pending.remove();
      state.messages.pop();
      appendMessage("error", error.message || "No pude contactar al asistente. Inténtalo de nuevo.");
    } finally {
      setBusy(false);
      el["agent-input"].focus();
    }
  }

  function resize() {
    const input = el["agent-input"];
    input.style.height = "auto";
    input.style.height = Math.min(160, Math.max(46, input.scrollHeight)) + "px";
  }

  function reset() {
    state.messages = [];
    renderHistory();
    el["agent-input"].value = "";
    resize();
    el["agent-input"].focus();
  }

  el["agent-form"].addEventListener("submit", event => {
    event.preventDefault();
    send();
  });
  el["agent-input"].addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      el["agent-form"].requestSubmit();
    }
  });
  el["agent-input"].addEventListener("input", resize);
  el["agent-privacy-ok"]?.addEventListener("click", () => {
    acceptPrivacy();
    showPrivacyGate();
    el["agent-input"]?.focus();
  });
  el["agent-clear"]?.addEventListener("click", reset);
  el["agent-prompts"]?.addEventListener("click", event => {
    const button = event.target.closest("button");
    if (!button || !privacyAccepted()) {
      if (button && !privacyAccepted()) showPrivacyGate();
      return;
    }
    el["agent-input"].value = button.textContent.trim();
    resize();
    el["agent-input"].focus();
  });
  document.addEventListener("click", event => {
    if (event.target.closest('[data-view="agent"],[data-go="agent"]')) {
      setTimeout(refreshStatus, 60);
    }
  });

  showPrivacyGate();
  renderHistory();
  resize();
  refreshStatus();
  window.__kairosAgentChatReady = true;
})();
