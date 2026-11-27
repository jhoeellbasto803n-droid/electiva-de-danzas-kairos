"""Modelo local opcional con reglas de KAIROS y búsqueda pública.

No entrena ni descarga un modelo por su cuenta: se conecta a un servidor
Ollama que corre en la misma máquina. Si no está disponible, ``app.py`` usa el
agente determinista de ``agente_local.py`` como respaldo.

El modelo recibe siempre las reglas no negociables de la app y, cuando hay un
análisis determinista previo, lo trata como fuente de verdad. Las acciones
devueltas por el modelo se filtran contra ese análisis: no puede inventar
fechas, ponderaciones, materias ni tareas nuevas.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode, urlsplit

logger = logging.getLogger("kairos.modelo")


def _numero_env(nombre: str, valor: str) -> float:
    try:
        return float(os.getenv(nombre, valor))
    except ValueError:
        return float(valor)


MODELO_LOCAL_URL = os.getenv("MODELO_LOCAL_URL", "http://127.0.0.1:11434").strip().rstrip("/")
MODELO_LOCAL_NOMBRE = os.getenv("MODELO_LOCAL_NOMBRE", "").strip()
MODELO_LOCAL_TIMEOUT = _numero_env("MODELO_LOCAL_TIMEOUT", "60")
WEB_ACTIVO = os.getenv("WEB_PUBLICA", "0").strip().lower() in {"1", "true", "si", "yes"}
WEB_TIMEOUT = _numero_env("WEB_TIMEOUT", "10")
WEB_RESULTADOS = 3
RESPUESTA_MAX = 128 * 1024
WEB_MAX = 256 * 1024

_partes = urlsplit(MODELO_LOCAL_URL)
if (
    _partes.scheme != "http"
    or _partes.hostname not in {"localhost", "127.0.0.1", "::1"}
    or _partes.path not in ("", "/")
):
    if MODELO_LOCAL_NOMBRE:
        logger.warning("MODELO_LOCAL_URL debe ser HTTP en localhost; modelo local desactivado.")
    MODELO_LOCAL_NOMBRE = ""

SISTEMA = """Eres el asistente de KAIROS para estudiantes de Ciencias de Datos.
Trabajas en la copia local del proyecto: no usas n8n ni servicios de modelos remotos.

REGLAS NO NEGOCIABLES DE LA APP:
1. La persona decide. Solo sugieres. Nunca digas que guardaste, editaste, eliminaste, enviaste o programaste algo. Las acciones son propuestas que alguien debe revisar y confirmar.
2. No inventes ni completes: no fijes prioridades, fechas, ponderaciones, horas ni materias que no estén en el mensaje o en el contexto local. Si falta un dato, dilo y deja el campo vacío.
3. Nunca sumes porcentajes de materias distintas ni prometas una nota.
4. El índice P es P = 0,45 × I + 0,35 × U + 0,20 × W. Si falta un componente se excluye y se renormalizan los demás. Niveles: Crítica ≥80, Alta ≥60, Media ≥40, Baja <40. Los cinco modos solo reordenan el plan; no cambian el puntaje.
5. KAIROS permite organizar materias y actividades, Plan semanal con CSV para Google Calendar, Cuaderno de datos privado, preferencias y exportación. Los avisos son internos: no hay correos ni notificaciones push. No hay sincronización en vivo.
6. El aviso de privacidad ya se mostró en la interfaz antes de habilitar el campo. No pidas contraseñas, tokens ni datos de terceros. La conversación no se guarda en PostgreSQL; solo se conserva la actividad que la persona guarda tras revisarla.
7. Responde siempre en español claro y breve. Si no sabes algo, dilo; no lo rellenes con suposiciones.
8. Si aparece un contexto local, es la fuente de verdad para temas de KAIROS. Conserva sus datos, advertencias y acciones sin cambiarlos. Puedes redactarlos con más claridad, pero no resumas ni omitas cifras ni avisos.
9. Para preguntas generales usa solo el contexto web proporcionado. No menciones manuales, documentos, enlaces ni fuentes que no aparezcan en ese contexto. Si el contexto no basta, explica la limitación.
10. No tienes acceso a la base de datos de KAIROS ni a las materias, actividades, notas, horarios o planes de la cuenta. Si te preguntan por esos datos, dilo y sugiere verlos en la app; nunca los inventes ni afirmes haberlos consultado.
11. Devuelve únicamente JSON con las claves "texto" (string) y "acciones" (lista). Copia las acciones del contexto local exactamente; si no hay contexto local o es una pregunta general, "acciones" debe ser [].
"""


def estado_modelo() -> dict:
    """Estado de la integración opcional, para ``/api/agent/status``."""
    return {
        "activo": bool(MODELO_LOCAL_NOMBRE),
        "nombre": MODELO_LOCAL_NOMBRE,
        "web": WEB_ACTIVO,
    }


def _consulta_web(pregunta: str) -> str:
    """Busca hasta tres resultados públicos en Wikipedia. Nunca falla en alto."""
    if not WEB_ACTIVO:
        return ""
    consulta = re.sub(r"\s+", " ", pregunta).strip(" ¿?.;:!").lower()
    if len(consulta) > 120:
        consulta = consulta[:120].rsplit(" ", 1)[0]
    if not consulta:
        return ""
    url = "https://es.wikipedia.org/w/api.php?" + urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": consulta,
            "format": "json",
            "srlimit": str(WEB_RESULTADOS),
            "utf8": "1",
        }
    )
    solicitud = urllib.request.Request(
        url,
        headers={"User-Agent": "KAIROS-LocalAgent/1.0", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=WEB_TIMEOUT) as respuesta:
            crudo = respuesta.read(WEB_MAX + 1)
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        logger.warning("No se pudo consultar la web pública: %s", exc)
        return ""
    if len(crudo) > WEB_MAX:
        return ""
    try:
        datos = json.loads(crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    resultados = datos.get("query", {}).get("search", [])
    if not isinstance(resultados, list):
        return ""
    lineas = []
    for item in resultados[:WEB_RESULTADOS]:
        if not isinstance(item, dict):
            continue
        titulo = str(item.get("title") or "").strip()
        if not titulo:
            continue
        resumen = re.sub(r"<[^>]+>", "", str(item.get("snippet") or ""))
        resumen = html.unescape(resumen).strip()
        enlace = "https://es.wikipedia.org/wiki/" + quote(titulo.replace(" ", "_"))
        lineas.append(f"- {titulo}: {resumen} ({enlace})")
    return "\n".join(lineas)


def responder_modelo(
    mensaje: str,
    analisis_local: dict | None = None,
    buscar_web: bool | None = None,
) -> dict | None:
    """Responde con Ollama aplicando las reglas de la app, o ``None`` si falla.

    ``analisis_local`` es la respuesta del agente determinista. Se entrega al
    modelo como contexto y se usa además para filtrar las acciones: el modelo
    no puede proponer nada que las reglas locales no hayan propuesto antes.
    """
    if not MODELO_LOCAL_NOMBRE:
        return None

    if buscar_web is None:
        from agente_local import es_general

        buscar_web = es_general(mensaje) if analisis_local is not None else True

    contexto = _consulta_web(mensaje) if buscar_web else ""
    sistema = SISTEMA
    if isinstance(analisis_local, dict):
        sistema += "\n\nContexto local verificado (reglas de la app, fuente de verdad):\n"
        sistema += json.dumps(analisis_local, ensure_ascii=False, indent=2)
    if contexto:
        sistema += "\n\nContexto web recuperado (Wikipedia):\n" + contexto
        sistema += "\nCita las fuentes usadas. Si el contexto no basta, dilo."

    payload = {
        "model": MODELO_LOCAL_NOMBRE,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": mensaje},
        ],
        "options": {"temperature": 0.1, "num_predict": 600},
    }
    solicitud = urllib.request.Request(
        MODELO_LOCAL_URL + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=MODELO_LOCAL_TIMEOUT) as respuesta:
            crudo = respuesta.read(RESPUESTA_MAX + 1)
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        logger.warning("No se pudo consultar el modelo local: %s", exc)
        return None
    if len(crudo) > RESPUESTA_MAX:
        return None
    try:
        datos = json.loads(crudo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None

    contenido = None
    if isinstance(datos.get("message"), dict):
        contenido = datos["message"].get("content")
    if not isinstance(contenido, str) or not contenido.strip():
        contenido = datos.get("response")
    if not isinstance(contenido, str) or not contenido.strip():
        return None
    try:
        parseado = json.loads(contenido)
    except json.JSONDecodeError:
        return None
    if not isinstance(parseado, dict):
        return None

    texto = parseado.get("texto", parseado.get("respuesta"))
    if not isinstance(texto, str) or not texto.strip():
        return None

    # El modelo no decide acciones: se devuelven exactamente las que ya propuso
    # el análisis determinista. Cualquier acción que haya inventado se ignora.
    permitidas = []
    if isinstance(analisis_local, dict) and isinstance(analisis_local.get("acciones"), list):
        permitidas = [a for a in analisis_local["acciones"] if isinstance(a, dict)]

    # La cita se añade en servidor: el modelo podria omitirla aunque el prompt
    # se la pida, y la trazabilidad de la fuente es obligatoria.
    if contexto and "wikipedia.org" not in texto.lower():
        texto = texto.rstrip() + "\n\nFuentes consultadas (Wikipedia):\n" + contexto

    # Solo pueden quedar URLs que realmente se recuperaron. Si no hay contexto
    # web, se eliminan todas: el modelo no puede inventar referencias.
    urls_reales = set(re.findall(r"https?://[^\s)\]]+", contexto))
    texto = re.sub(
        r"https?://[^\s)\]]+",
        lambda m: m.group(0) if m.group(0) in urls_reales else "",
        texto,
    )

    return {"texto": texto[:12000], "acciones": permitidas}
