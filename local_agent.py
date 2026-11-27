"""Asistente local de reglas para KAIROS.

No usa un modelo generativo ni servicios externos. Lee el mensaje con reglas
deterministas, señala candidatos y devuelve una respuesta breve con acciones
que la interfaz solo puede abrir en el formulario para revisión humana.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

CATALOG = {
    "INF": ("Información o aviso", 1),
    "ACT": ("Actividad de clase", 2),
    "TAR": ("Tarea", 3),
    "TAL": ("Taller", 3),
    "QUI": ("Quiz o evaluación corta", 4),
    "EXP": ("Exposición", 4),
    "PRO": ("Proyecto", 4),
    "PAR": ("Parcial o examen", 5),
    "FIN": ("Entrega final", 5),
}

# Etiquetas cortas para sugerir un título sin inventar datos de la fuente.
SHORT_LABEL = {
    "INF": "Aviso",
    "ACT": "Actividad",
    "TAR": "Tarea",
    "TAL": "Taller",
    "QUI": "Quiz",
    "EXP": "Exposición",
    "PRO": "Proyecto",
    "PAR": "Parcial",
    "FIN": "Entrega final",
}

TYPE_RULES = [
    ("FIN", r"\b(entrega final|proyecto final|trabajo final|examen final)\b"),
    ("PAR", r"\b(parcial|examen|sustentaci[oó]n)\b"),
    ("QUI", r"\b(quiz|prueba corta|evaluaci[oó]n corta)\b"),
    ("EXP", r"\b(exposici[oó]n|presentaci[oó]n oral)\b"),
    ("PRO", r"\b(proyecto)\b"),
    ("TAL", r"\b(taller)\b"),
    ("ACT", r"\b(actividad|ejercicio|lectura)\b"),
    ("INF", r"\b(aviso|informaci[oó]n|comunicado)\b"),
    ("TAR", r"\b(tarea|trabajo escrito)\b"),
]
# «Entrega» por sí sola suele ser un verbo («entrega el lunes»), no el tipo.
TAR_STRONG = re.compile(r"\b(tarea|trabajo escrito)\b", re.IGNORECASE)
TAR_WEAK = re.compile(r"\bentrega\b", re.IGNORECASE)

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

DATE_RE = re.compile(
    r"\b(\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?"
    r"|\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de\s+\d{4})?)\b",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*(%|por\s+ciento)", re.IGNORECASE)
HOURS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(h|horas?|hrs?)\b", re.IGNORECASE)

STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "para", "con",
    "que", "y", "este", "esta", "estos", "estas", "antes", "despues",
    "hasta", "vence", "entrega", "materia", "curso", "clase",
}

GRADE_CUES = re.compile(
    r"\b(nota|corte|calificaci[oó]n|ponderaci[oó]n|pondera|pesa|vale|representa|porcentaje|peso)\b",
    re.IGNORECASE,
)
EXTRA_POINT = re.compile(r"\bpuntos?\s+extra\b", re.IGNORECASE)
OPTIONAL = re.compile(r"\b(opcional|voluntari[oa]|no obligatorio)\b", re.IGNORECASE)
CRITICAL = re.compile(r"\b(vital|indispensable|obligatori[oa]|cr[ií]tic[oa]|imprescindible)\b", re.IGNORECASE)
REQUIRED = re.compile(r"\b(obligatori[oa]|requerid[oa])\b", re.IGNORECASE)
QUESTION_START = re.compile(
    r"^(que|qué|cual|cuál|cuales|cuáles|como|cómo|cuando|cuándo|donde|dónde|"
    r"quien|quién|por que|por qué|puedo|debo|tengo que|sirve|funciona)\b",
    re.IGNORECASE,
)
META_PHRASE = re.compile(
    r"\b(que datos|qué datos|que me falta|qué me falta|datos.*faltan|campos|"
    r"para que sirve|para qué sirve|como funciona|cómo funciona|"
    r"explicame|explícame|que puedes|qué puedes|que haces|qué haces)\b",
    re.IGNORECASE,
)

TOPIC_PRIVACY = re.compile(
    r"\b(privacidad|datos personales|guardas|almacenas|env[ií]as|"
    r"modelo (?:de ia|de inteligencia artificial|externo|generativo)|"
    r"qu[eé] modelo|usas un modelo|inteligencia artificial|n8n|servidor externo)\b",
    re.IGNORECASE,
)
TOPIC_PRIORITY = re.compile(
    r"\b(indice p|índice p|prioridad|prioridades|prioriz\w*|pondera\w*|peso|"
    r"como se calcula|cómo se calcula|formula|fórmula|equilibrado|"
    r"fecha mas proxima|fecha más próxima|impacto|esfuerzo|recuperacion|recuperación)\b",
    re.IGNORECASE,
)
TOPIC_FEATURES = re.compile(
    r"\b(calendario|csv|google|cuaderno|experimento|contrasena|contraseña|"
    r"cuenta|instalar|instalable|offline|sin conexion|sin conexión|"
    r"notificacion|notificación|recordatorio)\b",
    re.IGNORECASE,
)
TOPIC_PLANNING = re.compile(
    r"\b(ordenar|ordeno|primero|antes|compara\w*|plan semanal|semana|"
    r"entregas|sobrecarga|que hago|qué hago)\b",
    re.IGNORECASE,
)


def fold(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").lower())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")


def _iso_datetime(year: int, month: int, day: int) -> str | None:
    try:
        date(year, month, day)
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}T18:00"


def date_value(raw: str) -> str | None:
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", raw)
    if match:
        return _iso_datetime(int(match[1]), int(match[2]), int(match[3]))
    match = re.match(r"^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?$", raw)
    if match:
        if not match[3]:
            return None
        year = int(match[3])
        if year < 100:
            year += 2000
        return _iso_datetime(year, int(match[2]), int(match[1]))
    match = re.match(
        r"^(\d{1,2})\s+de\s+([a-záéíóúüñ]+)(?:\s+de\s+(\d{4}))?$",
        raw,
        re.IGNORECASE,
    )
    if match and match[3] and fold(match[2]) in MONTHS:
        return _iso_datetime(int(match[3]), MONTHS[fold(match[2])], int(match[1]))
    return None


def extract_dates(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    for match in DATE_RE.finditer(text):
        raw = match[1]
        if raw.lower() in seen:
            continue
        seen.add(raw.lower())
        start = match.start()
        context = text[max(0, start - 48): min(len(text), start + len(raw) + 48)].strip()
        nearby = fold(context)
        if re.search(r"\b(borrador|avance|preentrega|realimentacion|feedback|punto extra|opcional)\b", nearby):
            role = "Posible avance u opción"
        elif re.search(r"\b(entrega final|fecha limite|vence|fecha de entrega|obligatorio)\b", nearby):
            role = "Posible fecha principal"
        else:
            role = "Fecha sin clasificar"
        results.append({"raw": raw, "value": date_value(raw), "role": role, "context": context})
    return results


def extract_percentages(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[tuple[float, str]] = set()
    for match in PERCENT_RE.finditer(text):
        start = match.start()
        context = text[max(0, start - 48): min(len(text), start + len(match[0]) + 48)].strip()
        value = float(match[1].replace(",", "."))
        key = (value, context)
        if key in seen:
            continue
        seen.add(key)
        valid = bool(GRADE_CUES.search(context)) and not EXTRA_POINT.search(context) and 0 <= value <= 100
        results.append({"raw": match[0], "value": value, "valid": valid, "context": context})
    return results


def extract_hours(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[float] = set()
    for match in HOURS_RE.finditer(text):
        value = float(match[1].replace(",", "."))
        if value <= 0 or value > 168 or value in seen:
            continue
        seen.add(value)
        start = match.start()
        context = text[max(0, start - 38): min(len(text), start + len(match[0]) + 38)].strip()
        results.append({"raw": match[0], "value": value, "context": context})
    return results


def find_types(text: str) -> list[str]:
    found: list[str] = []
    for code, pattern in TYPE_RULES:
        # Si ya hay un tipo claro, «entrega» sola no convierte el texto en tarea.
        if code == "TAR" and found and TAR_WEAK.search(text) and not TAR_STRONG.search(text):
            continue
        if re.search(pattern, text, re.IGNORECASE) and code not in found:
            found.append(code)
    return found


def _type_match(text: str, code: str):
    pattern = dict(TYPE_RULES)[code]
    return re.search(pattern, text, re.IGNORECASE)


def _subject_phrase(text: str, code: str) -> str | None:
    match = _type_match(text, code)
    if not match:
        return None
    rest = text[match.end():]
    phrase = re.match(r"\s*(?:de|del|en)\s+([^\d,.;\n]{2,60})", rest, re.IGNORECASE)
    if not phrase:
        return None
    words = []
    for word in phrase[1].strip().split():
        clean = re.sub(r"[^\wÁÉÍÓÚÜÑáéíóúüñ]", "", word)
        if not clean or fold(clean) in STOPWORDS:
            break
        words.append(clean)
        if len(words) >= 5:
            break
    while words and fold(words[-1]) in {"de", "del"}:
        words.pop()
    if not words:
        return None
    result = " ".join(words)
    return result[0].upper() + result[1:]


def _looks_like_question(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("¿") or bool(QUESTION_START.match(stripped))


def _title(text: str, code: str, subject: str | None) -> str | None:
    if "?" in text or "¿" in text or _looks_like_question(text):
        return None
    if subject:
        return f"{SHORT_LABEL[code]} de {subject}"[:100]
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    first = re.sub(r"^\s*(?:[-*•>]+|\d+[.)])\s*", "", first)
    first = " ".join(first.split()).strip(" \"'“”")
    first = first.rstrip(".,;:")
    if len(first) < 3:
        return None
    if DATE_RE.fullmatch(first) or PERCENT_RE.fullmatch(first) or HOURS_RE.fullmatch(first):
        return None
    if len(first) > 100:
        first = first[:100].rsplit(" ", 1)[0].rstrip(".,;:")
    return first or None


def _number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value).replace(".", ",")


def _type_facts(types: list[str]) -> list[str]:
    if not types:
        return []
    if len(types) == 1:
        label, level = CATALOG[types[0]]
        return [f"Tipo sugerido: {types[0]} · {label} ({level}/5). Confírmalo."]
    listed = ", ".join(f"{code} ({CATALOG[code][1]}/5)" for code in types)
    return [f"Tipos detectados: {listed}. El texto mezcla categorías; elige una antes de guardar."]


def _date_facts(dates: list[dict]) -> list[str]:
    facts = []
    for item in dates:
        if item["value"]:
            pretty = item["value"].replace("T18:00", " 18:00").replace("-", "/")
            facts.append(f"Fecha candidata: {item['raw']} → {pretty} ({item['role']}).")
        else:
            facts.append(f"Fecha candidata: {item['raw']}, sin año reconocible. No la usaré hasta que la confirmes.")
    return facts


def _weight_facts(percentages: list[dict]) -> list[str]:
    facts = []
    for item in percentages:
        if item["valid"]:
            facts.append(f"Ponderación candidata: {_number(item['value'])} % (asociada a la nota).")
        else:
            facts.append(f"Porcentaje {item['raw']}: no lo tomo como ponderación porque no está claro que corresponda a la nota.")
    return facts


def _hours_facts(hours: list[dict]) -> list[str]:
    return [f"Horas candidatas: {_number(item['value'])} h." for item in hours]


def _warnings(dates, percentages, hours, types, text) -> list[str]:
    warnings = []
    folded = fold(text)
    if len(dates) > 1:
        warnings.append("Aparecen varias fechas. Identifica en la fuente cuál es el plazo final y cuáles son avances u opciones.")
    if any(item["role"] == "Posible avance u opción" for item in dates) and any(
        item["role"] == "Posible fecha principal" for item in dates
    ):
        warnings.append("El texto mezcla fechas de avance y una posible fecha principal; no elijo ninguna automáticamente.")
    if any(not item["value"] for item in dates):
        warnings.append("Hay fechas sin año. Las dejaré vacías hasta que confirmes el año.")
    if len(percentages) > 1:
        warnings.append("Aparecen varios porcentajes; confirma cuál corresponde a esta actividad y a qué corte pertenece.")
    if any(not item["valid"] for item in percentages):
        warnings.append("Algún porcentaje no está claramente asociado a la nota o parece un punto extra; no lo tomo como ponderación.")
    if len(types) > 1:
        warnings.append("Aparecen varios tipos de actividad. No elijo uno por ti.")
    if OPTIONAL.search(text) and CRITICAL.search(text):
        warnings.append("El texto combina opcionalidad con importancia crítica. La palabra «opcional» no reduce automáticamente la prioridad.")
    if OPTIONAL.search(text) and REQUIRED.search(text):
        warnings.append("El texto contiene instrucciones contradictorias sobre si la actividad es opcional.")
    if not dates:
        warnings.append("No encontré una fecha límite; el campo quedará vacío.")
    if not percentages:
        warnings.append("No encontré una ponderación; no la inventaré.")
    if not hours:
        warnings.append("No encontré horas estimadas; el formulario usará su sugerencia por tipo.")
    if re.search(r"\b(aproximad|posible|quizas|quizá|tal vez|suele|normalmente)\b", folded):
        warnings.append("El texto usa expresiones aproximadas. Confirma la fuente antes de guardar.")
    return warnings


def _analysis_reply(text: str) -> dict | None:
    dates = extract_dates(text)
    percentages = extract_percentages(text)
    hours = extract_hours(text)
    types = find_types(text)
    if not (dates or percentages or hours or types):
        return None

    facts = _type_facts(types)
    facts.extend(_date_facts(dates))
    facts.extend(_weight_facts(percentages))
    facts.extend(_hours_facts(hours))
    subject = _subject_phrase(text, types[0]) if len(types) == 1 else None
    if subject:
        facts.append(f"Materia detectada: {subject}. Verifica que coincida con una de tus materias.")

    warnings = _warnings(dates, percentages, hours, types, text)
    if not warnings:
        warnings.append("No encontré datos en conflicto. Verifica igualmente la fuente original antes de guardar.")
    lines = ["Revisé tu mensaje con las reglas locales de KAIROS.", "", "Esto es lo que encontré:"]
    lines.extend(f"• {fact}" for fact in facts)
    lines.extend(["", "Antes de guardar, confirma:"])
    lines.extend(f"• {warning}" for warning in warnings)

    action = None
    title = _title(text, types[0], subject) if len(types) == 1 else None
    if len(types) == 1 and title:
        action = {
            "tipo": "crear_actividad",
            "titulo": title,
            "categoria": types[0],
            "nota": "Tomado de tu mensaje. Verifica cada dato contra la fuente original antes de guardar.",
        }
        if subject:
            action["materia"] = subject
        valid_dates = [item for item in dates if item["value"]]
        if len(dates) == 1 and len(valid_dates) == 1:
            action["fecha"] = valid_dates[0]["value"]
        if len(percentages) == 1 and percentages[0]["valid"]:
            action["ponderacion"] = percentages[0]["value"]
        if len(hours) == 1:
            action["horas"] = hours[0]["value"]

    lines.extend(["", "La decisión final es tuya."])
    if action:
        lines.insert(-1, "Preparé una propuesta para el formulario. No se guarda hasta que confirmes cada dato y escribas la materia.")
    elif _looks_like_question(text) or "?" in text or "¿" in text:
        extra = (
            " Si tu pregunta era cómo ordenarlas, necesito la fecha límite y la ponderación de cada actividad: "
            "con esos datos el Plan semanal las compara sin inventar prioridades."
            if TOPIC_PLANNING.search(fold(text))
            else ""
        )
        lines.insert(
            -1,
            "No generé una tarjeta porque el texto es una pregunta. Si quieres registrar una actividad, escribe la instrucción como un enunciado con nombre, materia y fecha." + extra,
        )
    else:
        lines.insert(
            -1,
            "No generé una tarjeta porque falta un nombre claro o hay datos en conflicto. Puedes registrar la actividad manualmente.",
        )
    return {"texto": "\n".join(lines), "acciones": [action] if action else []}


def _privacy_reply() -> dict:
    return {
        "texto": (
            "Esta versión funciona con reglas locales en el servidor de KAIROS: tus mensajes no se "
            "envían a un modelo de IA externo ni a n8n. La conversación no se guarda en PostgreSQL y "
            "se pierde al recargar. La única copia persistente es la actividad que tú guardas después "
            "de revisarla y confirmarla. Si el equipo activa n8n más adelante, la vista lo indicará "
            "antes de escribir."
        ),
        "acciones": [],
    }


def _priority_reply() -> dict:
    return {
        "texto": (
            "El índice P combina tres componentes: P = 0,45 × I + 0,35 × U + 0,20 × W.\n\n"
            "• I: importancia del tipo estandarizado, de INF 1/5 a PAR o FIN 5/5.\n"
            "• U: urgencia según la fecha límite; vale 1 si vence en 24 h o menos y baja por tramos hasta 0,10.\n"
            "• W: ponderación confirmada; W = min(porcentaje / 30 %, 1).\n\n"
            "Si falta un componente no se inventa: se excluye y se renormalizan los demás. "
            "Los niveles son Crítica ≥80, Alta ≥60, Media ≥40 y Baja <40. Los cinco modos "
            "(equilibrado, fecha más próxima, impacto, esfuerzo y recuperación) solo reordenan el plan; "
            "no cambian el puntaje ni prometen una nota."
        ),
        "acciones": [],
    }


def _features_reply(text: str) -> dict:
    folded = fold(text)
    if re.search(r"calendario|csv|google", folded):
        body = (
            "En Plan semanal puedes descargar las sesiones propuestas como CSV compatible con la "
            "importación de Google Calendar. Eliges la hora inicial y las sesiones se ordenan en "
            "secuencia con pausas breves. Revisa los horarios antes de importarlos: KAIROS propone "
            "bloques y no sincroniza cambios en vivo."
        )
    elif re.search(r"cuaderno|experimento", folded):
        body = (
            "El Cuaderno de datos guarda pregunta, fuente, método, métrica, resultado, límites y "
            "siguiente paso de cada experimento. Puedes editar, eliminar y exportar los registros "
            "como CSV. Es privado de tu cuenta."
        )
    elif re.search(r"contrasena|contraseña|cuenta", folded):
        body = (
            "En Preferencias puedes cambiar la contraseña verificando la actual; al hacerlo se cierran "
            "las demás sesiones. La eliminación de cuenta exige la contraseña y la frase ELIMINAR, y "
            "borra el perfil, el plan y las sesiones."
        )
    elif re.search(r"instalar|instalable|offline|sin conexion|sin conexión", folded):
        body = (
            "KAIROS es instalable como aplicación web. El service worker guarda los recursos estáticos, "
            "pero el inicio de sesión, la sincronización y el cuaderno privado requieren conexión."
        )
    elif re.search(r"notificacion|notificación|recordatorio", folded):
        body = (
            "Los avisos de plazos y sobrecarga aparecen dentro de KAIROS al abrir la página. No se "
            "envían correos ni notificaciones push."
        )
    else:
        body = (
            "KAIROS organiza materias y actividades, calcula una prioridad explicable, propone un plan "
            "semanal, guarda un cuaderno privado de experimentos y permite exportar el horario como CSV. "
            "También incluye un revisor local de instrucciones y este asistente de reglas."
        )
    return {"texto": body, "acciones": []}


def _missing_data_reply() -> dict:
    return {
        "texto": (
            "Para registrar una actividad necesitas: nombre, materia, tipo estandarizado y horas "
            "estimadas. La fecha límite y la ponderación son opcionales: si no aparecen en la fuente, "
            "déjalas vacías; no se inventan. Antes de guardar marca «Confirmo que revisé los datos "
            "disponibles». Si pegas la instrucción, puedo señalarte candidatos de tipo, fecha, "
            "ponderación y horas."
        ),
        "acciones": [],
    }


def _planning_reply() -> dict:
    return {
        "texto": (
            "No puedo ordenar tus entregas sin ver fechas, ponderaciones y horas: inventarlas rompería "
            "la regla del proyecto. Pega las instrucciones o escribe cada actividad con su fecha y su "
            "peso, y te señalo los datos que faltan o que se contradicen.\n\n"
            "Mientras tanto, revisa el Plan semanal con el modo que prefieras. El plan compara lo que "
            "cabe en tu tiempo disponible y muestra lo que queda pendiente; no suma porcentajes de "
            "materias distintas ni promete una nota. La prioridad P combina importancia, urgencia y "
            "ponderación confirmada, y los criterios solo reordenan el plan."
        ),
        "acciones": [],
    }


def _help_reply() -> dict:
    return {
        "texto": (
            "Soy el asistente local de KAIROS y funciono con reglas, sin un modelo externo. Puedo:\n\n"
            "• Leer una instrucción y señalar tipo, fechas, ponderación y horas candidatas.\n"
            "• Decirte qué datos faltan o son ambiguos antes de registrar una actividad.\n"
            "• Explicarte el índice P, los modos de priorización y las funciones de KAIROS.\n"
            "• Preparar una actividad sugerida para que la revises en el formulario.\n\n"
            "Pega la instrucción de tu docente o pregúntame por una función. No guardo nada ni decido por ti."
        ),
        "acciones": [],
    }


def _fallback_reply() -> dict:
    return {
        "texto": (
            "No encontré una instrucción académica ni una pregunta que pueda responder con mis reglas. "
            "Puedo analizar un texto que incluya tipo de actividad, fechas, porcentajes u horas, o "
            "explicarte el índice P, el plan semanal, el cuaderno de datos o la privacidad.\n\n"
            "Si esperabas una respuesta de un modelo generativo, esta versión funciona en modo local. "
            "El equipo puede activar n8n más adelante sin cambiar esta vista."
        ),
        "acciones": [],
    }


def local_reply(message: str) -> dict:
    """Devuelve {texto, acciones} usando solo reglas locales."""
    text = str(message or "").strip()
    if not text:
        return _help_reply()

    folded = fold(text)
    has_facts = bool(extract_dates(text) or extract_percentages(text) or extract_hours(text) or find_types(text))
    is_question = _looks_like_question(text) or "?" in text or "¿" in text

    if TOPIC_PRIVACY.search(folded) and not has_facts:
        return _privacy_reply()
    if is_question and META_PHRASE.search(folded) and re.search(r"datos|falta|campos", folded) and not has_facts:
        return _missing_data_reply()
    if is_question and TOPIC_FEATURES.search(folded) and not has_facts:
        return _features_reply(text)
    if is_question and TOPIC_PLANNING.search(folded) and not has_facts:
        return _planning_reply()
    if is_question and TOPIC_PRIORITY.search(folded) and not has_facts:
        return _priority_reply()
    if has_facts:
        analysis = _analysis_reply(text)
        if analysis:
            return analysis
    if TOPIC_PRIVACY.search(folded):
        return _privacy_reply()
    if TOPIC_PRIORITY.search(folded):
        return _priority_reply()
    if TOPIC_PLANNING.search(folded):
        return _planning_reply()
    if re.search(r"^(hola|buenas|hey|saludos)\b", folded) or re.search(
        r"ayuda|que puedes|qué puedes|que haces|qué haces|para que sirves|para qué sirves", folded
    ):
        return _help_reply()
    return _fallback_reply()
