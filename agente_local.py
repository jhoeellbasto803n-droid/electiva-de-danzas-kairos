"""Agente académico local de KAIROS.

Reglas deterministas: no usa modelos generativos, webhooks ni servicios
externos. Solo lee el mensaje y devuelve {"texto": str, "acciones": list}.
Las acciones son propuestas; la interfaz nunca las ejecuta directamente.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

CATALOG = {
    "INF": ("Información o aviso", 1, "Aviso"),
    "ACT": ("Actividad de clase", 2, "Actividad"),
    "TAR": ("Tarea", 3, "Tarea"),
    "TAL": ("Taller", 3, "Taller"),
    "QUI": ("Quiz o evaluación corta", 4, "Quiz"),
    "EXP": ("Exposición", 4, "Exposición"),
    "PRO": ("Proyecto", 4, "Proyecto"),
    "PAR": ("Parcial o examen", 5, "Parcial"),
    "FIN": ("Entrega final", 5, "Entrega final"),
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
# "Entrega" suele ser un verbo ("entrega el lunes"), no un tipo de actividad.
TAR_STRONG = re.compile(r"\b(tarea|trabajo escrito)\b", re.IGNORECASE)
TAR_WEAK = re.compile(r"\bentrega\b", re.IGNORECASE)

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

DATE_RE = re.compile(
    r"\b(\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"
    rf"|\d{{1,2}}\s+de\s+(?:{MONTH_ALT})(?:\s+de\s+\d{{4}})?)\b",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"(\d{1,3}(?:[.,]\d+)?)\s*(%|por\s+ciento)", re.IGNORECASE)
HOURS_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(h|horas?|hrs?)\b", re.IGNORECASE)

GRADE_CUE = re.compile(
    r"\b(nota|corte|calificaci[oó]n|ponderaci[oó]n|pondera|pesa|vale|representa|porcentaje|peso)\b",
    re.IGNORECASE,
)
EXTRA_POINT = re.compile(r"\bpuntos?\s+extra\b", re.IGNORECASE)
OPTIONAL = re.compile(r"\b(opcional|voluntari[oa]|no obligatorio)\b", re.IGNORECASE)
CRITICAL = re.compile(r"\b(vital|indispensable|obligatori[oa]|cr[ií]tic[oa]|imprescindible)\b", re.IGNORECASE)
REQUIRED = re.compile(r"\b(obligatori[oa]|requerid[oa])\b", re.IGNORECASE)
APPROXIMATE = re.compile(r"\b(aproximad\w*|posible|quizas|quizá|tal vez|suele|normalmente)\b", re.IGNORECASE)

STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "para", "con",
    "que", "y", "este", "esta", "estos", "estas", "antes", "despues", "hasta",
    "vence", "entrega", "materia", "curso", "clase",
}

QUESTION_START = re.compile(
    r"^(que|qué|cual|cuál|cuales|cuáles|como|cómo|cuando|cuándo|donde|dónde|"
    r"quien|quién|por que|por qué|puedo|debo|tengo que|sirve|funciona|"
    r"explicame|explícame|dime)\b",
    re.IGNORECASE,
)
TOPIC_PRIVACY = re.compile(
    r"\b(privacidad|datos personales|guardas|almacenas|envias|modelo de ia|"
    r"modelo externo|inteligencia artificial|servidor externo|n8n)\b",
    re.IGNORECASE,
)
TOPIC_PRIORITY = re.compile(
    r"\b(indice p|prioridad|prioridades|prioriza\w*|pondera\w*|peso|"
    r"como se calcula|formula|equilibrado|fecha mas proxima|impacto|"
    r"esfuerzo|recuperacion)\b",
    re.IGNORECASE,
)
TOPIC_FEATURES = re.compile(
    r"\b(calendario|csv|google|cuaderno|experimento|contrasena|cuenta|"
    r"instalar|instalable|offline|sin conexion|notificacion|recordatorio)\b",
    re.IGNORECASE,
)
# Preguntas sobre la propia app o sus funciones: se responden con el texto
# documentado del proyecto, nunca con Wikipedia.
TOPIC_APP = re.compile(
    r"\b(kairos|app|aplicacion|aplicativo|funciones|funcionalidades|"
    r"revisor|cronometro|priorizacion|exportar|exportacion|preferencias|"
    r"interfaz|vista|modo|modos)\b",
    re.IGNORECASE,
)
TOPIC_PLANNING = re.compile(
    r"\b(ordenar|ordeno|primero|antes|compara\w*|plan semanal|semana|"
    r"entregas|que hago)\b",
    re.IGNORECASE,
)
TOPIC_MISSING = re.compile(
    r"\b(que datos|que me falta|datos.*faltan|campos|para registrar)\b",
    re.IGNORECASE,
)
# Preguntas sobre datos guardados en la cuenta. El modelo no debe responderlas
# con internet porque no tiene acceso a la base de datos de KAIROS.
_DATOS_APP = (
    r"materia|materias|actividad|actividades|tarea|tareas|examen|examenes|"
    r"nota|notas|calificacion|calificaciones|horario|plan|indice\s+p|"
    r"prioridad|cuaderno|registro|registros|datos"
)
_POSEEDOR = r"mi|mis|me|tengo|tienes|cuenta"
TOPIC_ACCOUNT = re.compile(
    r"\b(?:(?:" + _POSEEDOR + r")\b[^.?!]*\b(?:" + _DATOS_APP + r")\b"
    r"|(?:" + _DATOS_APP + r")\b[^.?!]*\b(?:" + _POSEEDOR + r")\b)",
    re.IGNORECASE,
)


def normalizar(valor: str) -> str:
    texto = unicodedata.normalize("NFD", str(valor or "").lower())
    return "".join(char for char in texto if unicodedata.category(char) != "Mn")


def _iso(year: int, month: int, day: int) -> str | None:
    try:
        date(year, month, day)
    except ValueError:
        return None
    return f"{year:04d}-{month:02d}-{day:02d}T18:00"


def fecha_valor(raw: str) -> str | None:
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", raw)
    if match:
        return _iso(int(match[1]), int(match[2]), int(match[3]))

    match = re.match(r"^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$", raw)
    if match:
        year = int(match[3])
        if year < 100:
            year += 2000
        return _iso(year, int(match[2]), int(match[1]))

    match = re.match(
        rf"^(\d{{1,2}})\s+de\s+({MONTH_ALT})(?:\s+de\s+(\d{{4}}))?$",
        raw,
        re.IGNORECASE,
    )
    if match and match[3]:
        return _iso(int(match[3]), MONTHS[normalizar(match[2])], int(match[1]))
    return None


def extraer_fechas(texto: str) -> list[dict]:
    fechas: list[dict] = []
    vistas: set[str] = set()
    for match in DATE_RE.finditer(texto):
        raw = match[1]
        clave = normalizar(raw)
        if clave in vistas:
            continue
        vistas.add(clave)
        inicio, fin = match.span()
        contexto = texto[max(0, inicio - 48): min(len(texto), fin + 48)].strip()
        vecindario = normalizar(contexto)
        if re.search(
            r"\b(borrador|avance|preentrega|realimentacion|feedback|punto extra|opcional)\b",
            vecindario,
        ):
            papel = "Posible avance u opción"
        elif re.search(
            r"\b(entrega final|fecha limite|vence|fecha de entrega|obligatorio)\b",
            vecindario,
        ):
            papel = "Posible fecha principal"
        else:
            papel = "Fecha sin clasificar"
        fechas.append({"raw": raw, "value": fecha_valor(raw), "role": papel})
    return fechas


def extraer_porcentajes(texto: str) -> list[dict]:
    porcentajes: list[dict] = []
    vistos: set[tuple[float, str]] = set()
    for match in PERCENT_RE.finditer(texto):
        inicio, fin = match.span()
        contexto = texto[max(0, inicio - 48): min(len(texto), fin + 48)].strip()
        valor = float(match[1].replace(",", "."))
        clave = (valor, contexto)
        if clave in vistos:
            continue
        vistos.add(clave)
        valido = bool(GRADE_CUE.search(contexto)) and not EXTRA_POINT.search(contexto) and 0 <= valor <= 100
        porcentajes.append({"raw": match[0], "value": valor, "valid": valido})
    return porcentajes


def extraer_horas(texto: str) -> list[dict]:
    horas: list[dict] = []
    vistos: set[float] = set()
    for match in HOURS_RE.finditer(texto):
        valor = float(match[1].replace(",", "."))
        if valor <= 0 or valor > 168 or valor in vistos:
            continue
        vistos.add(valor)
        horas.append({"raw": match[0], "value": valor})
    return horas


def detectar_tipos(texto: str) -> list[str]:
    tipos: list[str] = []
    for codigo, patron in TYPE_RULES:
        if (
            codigo == "TAR"
            and tipos
            and TAR_WEAK.search(texto)
            and not TAR_STRONG.search(texto)
        ):
            continue
        if re.search(patron, texto, re.IGNORECASE) and codigo not in tipos:
            tipos.append(codigo)
    return tipos


def detectar_materia(texto: str, tipo: str) -> str | None:
    match = re.search(dict(TYPE_RULES)[tipo], texto, re.IGNORECASE)
    if not match:
        return None
    resto = texto[match.end():]
    frase = re.match(r"\s*(?:de|del|en)\s+([^\d,.;:\n]{2,60})", resto, re.IGNORECASE)
    if not frase:
        return None
    palabras: list[str] = []
    for palabra in frase[1].strip().split():
        limpia = re.sub(r"[^\wÁÉÍÓÚÜÑáéíóúüñ]", "", palabra)
        if not limpia or normalizar(limpia) in STOPWORDS:
            break
        palabras.append(limpia)
        if len(palabras) >= 5:
            break
    while palabras and normalizar(palabras[-1]) in {"de", "del"}:
        palabras.pop()
    if not palabras:
        return None
    resultado = " ".join(palabras)
    return resultado[0].upper() + resultado[1:]


def es_pregunta(texto: str) -> bool:
    limpio = texto.strip()
    return limpio.startswith("¿") or bool(QUESTION_START.match(limpio))


def _titulo(texto: str, tipo: str, materia: str | None) -> str | None:
    if "?" in texto or "¿" in texto or es_pregunta(texto):
        return None
    if materia:
        return f"{CATALOG[tipo][2]} de {materia}"[:100]
    primera = next((linea.strip() for linea in texto.splitlines() if linea.strip()), "")
    primera = re.sub(r"^\s*(?:[-*•>]+|\d+[.)])\s*", "", primera)
    primera = " ".join(primera.split()).strip(" \"'“”")
    primera = primera.rstrip(".,;:")
    if len(primera) < 3:
        return None
    if DATE_RE.fullmatch(primera) or PERCENT_RE.fullmatch(primera) or HOURS_RE.fullmatch(primera):
        return None
    if len(primera) > 100:
        primera = primera[:100].rsplit(" ", 1)[0].rstrip(".,;:")
    return primera or None


def _numero(valor: float) -> str:
    return str(int(valor)) if float(valor).is_integer() else str(valor).replace(".", ",")


def _hechos(tipos, fechas, porcentajes, horas, materia) -> list[str]:
    hechos: list[str] = []
    if len(tipos) == 1:
        etiqueta, nivel, _ = CATALOG[tipos[0]]
        hechos.append(f"Tipo sugerido: {tipos[0]} · {etiqueta} ({nivel}/5). Confírmalo.")
    elif tipos:
        lista = ", ".join(f"{c} ({CATALOG[c][1]}/5)" for c in tipos)
        hechos.append(f"Tipos detectados: {lista}. El texto mezcla categorías; elige una antes de guardar.")
    for fecha in fechas:
        if fecha["value"]:
            bonita = fecha["value"].replace("T18:00", " 18:00").replace("-", "/")
            hechos.append(f"Fecha candidata: {fecha['raw']} → {bonita} ({fecha['role']}).")
        else:
            hechos.append(f"Fecha candidata: {fecha['raw']}, sin año reconocible. No la usaré hasta que la confirmes.")
    for porcentaje in porcentajes:
        if porcentaje["valid"]:
            hechos.append(f"Ponderación candidata: {_numero(porcentaje['value'])} % (asociada a la nota).")
        else:
            hechos.append(
                f"Porcentaje {porcentaje['raw']}: no lo tomo como ponderación porque no está claro que corresponda a la nota."
            )
    for hora in horas:
        hechos.append(f"Horas candidatas: {_numero(hora['value'])} h.")
    if materia:
        hechos.append(f"Materia detectada: {materia}. Verifica que coincida con una de tus materias.")
    return hechos


def _advertencias(tipos, fechas, porcentajes, horas, texto) -> list[str]:
    avisos: list[str] = []
    if len(fechas) > 1:
        avisos.append("Aparecen varias fechas. Identifica cuál es el plazo final y cuáles son avances u opciones.")
    if any(f["role"] == "Posible avance u opción" for f in fechas) and any(
        f["role"] == "Posible fecha principal" for f in fechas
    ):
        avisos.append("El texto mezcla fechas de avance y una posible fecha principal; no elijo ninguna automáticamente.")
    if any(not f["value"] for f in fechas):
        avisos.append("Hay fechas sin año. Las dejaré vacías hasta que confirmes el año.")
    if len(porcentajes) > 1:
        avisos.append("Aparecen varios porcentajes; confirma cuál corresponde a esta actividad.")
    if any(not p["valid"] for p in porcentajes):
        avisos.append("Algún porcentaje no está claro o parece un punto extra; no lo tomo como ponderación.")
    if len(tipos) > 1:
        avisos.append("Aparecen varios tipos de actividad. No elijo uno por ti.")
    if OPTIONAL.search(texto) and CRITICAL.search(texto):
        avisos.append("El texto combina opcionalidad con importancia crítica. «Opcional» no reduce la prioridad por sí solo.")
    if OPTIONAL.search(texto) and REQUIRED.search(texto):
        avisos.append("El texto contiene instrucciones contradictorias sobre si la actividad es opcional.")
    if not fechas:
        avisos.append("No encontré una fecha límite; el campo quedará vacío.")
    if not porcentajes:
        avisos.append("No encontré una ponderación; no la inventaré.")
    if not horas:
        avisos.append("No encontré horas estimadas; el formulario usará su sugerencia por tipo.")
    if APPROXIMATE.search(texto):
        avisos.append("El texto usa expresiones aproximadas. Confirma la fuente antes de guardar.")
    if not avisos:
        avisos.append("No encontré datos en conflicto. Verifica igualmente la fuente original antes de guardar.")
    return avisos


def _analizar(texto, tipos, fechas, porcentajes, horas) -> dict:
    materia = detectar_materia(texto, tipos[0]) if len(tipos) == 1 else None
    hechos = _hechos(tipos, fechas, porcentajes, horas, materia)
    avisos = _advertencias(tipos, fechas, porcentajes, horas, texto)

    lineas = ["Revisé tu mensaje con el agente local de KAIROS.", "", "Esto es lo que encontré:"]
    lineas.extend(f"• {h}" for h in hechos)
    lineas.extend(["", "Antes de guardar, confirma:"])
    lineas.extend(f"• {a}" for a in avisos)
    lineas.extend(["", "La decisión final es tuya."])

    accion = None
    titulo = _titulo(texto, tipos[0], materia) if len(tipos) == 1 else None
    if len(tipos) == 1 and titulo:
        accion = {
            "tipo": "crear_actividad",
            "titulo": titulo,
            "categoria": tipos[0],
            "nota": "Tomado de tu mensaje. Verifica cada dato contra la fuente original antes de guardar.",
        }
        if materia:
            accion["materia"] = materia
        validas = [f for f in fechas if f["value"]]
        if len(fechas) == 1 and len(validas) == 1:
            accion["fecha"] = validas[0]["value"]
        if len(porcentajes) == 1 and porcentajes[0]["valid"]:
            accion["ponderacion"] = porcentajes[0]["value"]
        if len(horas) == 1:
            accion["horas"] = horas[0]["value"]
        lineas.insert(-1, "Preparé una propuesta para el formulario. No se guarda hasta que confirmes cada dato.")
    elif "?" in texto or "¿" in texto or es_pregunta(texto):
        extra = ""
        if TOPIC_PLANNING.search(normalizar(texto)):
            extra = (
                " Si tu pregunta era cómo ordenarlas, necesito la fecha y la ponderación de cada actividad: "
                "con esos datos el Plan semanal las compara sin inventar prioridades."
            )
        lineas.insert(
            -1,
            "No generé una tarjeta porque el texto es una pregunta. Escribe la instrucción como enunciado "
            "si quieres registrar una actividad." + extra,
        )
    else:
        lineas.insert(
            -1,
            "No generé una tarjeta porque falta un nombre claro o hay datos en conflicto. Puedes registrar la actividad manualmente.",
        )
    return {"texto": "\n".join(lineas), "acciones": [accion] if accion else []}


def _privacidad(info_modelo: dict | None = None) -> dict:
    info = info_modelo or {}
    if info.get("activo"):
        cuerpo = (
            "Esta copia usa reglas locales en el servidor de KAIROS y, para preguntas generales, un modelo "
            "que corre en tu propia máquina. "
        )
        if info.get("web"):
            cuerpo += (
                "Si la búsqueda web está activa, solo sale a Wikipedia el texto de la búsqueda, nunca tus "
                "contraseñas ni datos de terceros. "
            )
        else:
            cuerpo += "No se consulta la web. "
    else:
        cuerpo = (
            "Este agente funciona solo con reglas deterministas en el servidor de KAIROS: no usa un modelo "
            "generativo ni consulta internet. "
        )
    cuerpo += (
        "No usa n8n ni servicios externos de IA. La conversación vive en memoria y no se guarda en "
        "PostgreSQL ni en `localStorage`. La única copia persistente es la actividad que tú guardas después "
        "de revisarla y confirmarla. El aviso de privacidad se muestra antes de habilitar el campo. No "
        "escribas contraseñas ni datos de terceros."
    )
    return {"texto": cuerpo, "acciones": []}


def _indice_p() -> dict:
    return {"texto": (
        "El índice P combina tres componentes: P = 0,45 × I + 0,35 × U + 0,20 × W.\n\n"
        "• I: importancia del tipo estandarizado, de INF 1/5 a PAR o FIN 5/5.\n"
        "• U: urgencia según la fecha límite; vale 1 si vence en 24 h o menos y baja por tramos hasta 0,10.\n"
        "• W: ponderación confirmada; W = min(porcentaje / 30 %, 1).\n\n"
        "Si falta un componente no se inventa: se excluye y se renormalizan los demás. Los niveles son "
        "Crítica ≥80, Alta ≥60, Media ≥40 y Baja <40. Los cinco modos solo reordenan el plan; no cambian "
        "el puntaje ni prometen una nota."
    ), "acciones": []}


def _funciones(texto: str) -> dict:
    n = normalizar(texto)
    if re.search(r"calendario|csv|google", n):
        cuerpo = (
            "En Plan semanal puedes descargar las sesiones como CSV compatible con Google Calendar. "
            "Eliges la hora inicial y los bloques se ordenan con pausas breves. Revisa los horarios antes "
            "de importarlos: KAIROS propone, no sincroniza cambios en vivo."
        )
    elif re.search(r"cuaderno|experimento", n):
        cuerpo = (
            "El Cuaderno de datos guarda pregunta, fuente, método, métrica, resultado, límites y siguiente "
            "paso. Puedes editar, eliminar y exportar los registros como CSV. Es privado de tu cuenta."
        )
    elif re.search(r"contrasena|cuenta", n):
        cuerpo = (
            "En Preferencias puedes cambiar la contraseña verificando la actual; al hacerlo se cierran las "
            "demás sesiones. La eliminación exige la contraseña y la frase ELIMINAR."
        )
    elif re.search(r"instalar|offline|sin conexion", n):
        cuerpo = (
            "KAIROS es instalable como aplicación web. El service worker guarda recursos estáticos, pero "
            "el inicio de sesión, la sincronización y el cuaderno privado requieren conexión."
        )
    elif re.search(r"notificacion|recordatorio", n):
        cuerpo = (
            "Los avisos de plazos y sobrecarga aparecen dentro de KAIROS al abrir la página. No se envían "
            "correos ni notificaciones push."
        )
    else:
        cuerpo = (
            "KAIROS organiza materias y actividades, calcula una prioridad explicable, propone un plan "
            "semanal, guarda un cuaderno privado de experimentos y permite exportar el horario como CSV. "
            "También incluye el revisor local de instrucciones y este agente de reglas."
        )
    return {"texto": cuerpo, "acciones": []}


def _faltan_datos() -> dict:
    return {"texto": (
        "Para registrar una actividad necesitas: nombre, materia, tipo estandarizado y horas estimadas. "
        "La fecha límite y la ponderación son opcionales: si no aparecen en la fuente, déjalas vacías; no "
        "se inventan. Antes de guardar marca «Confirmo que revisé los datos disponibles». Si pegas la "
        "instrucción, puedo señalarte candidatos de tipo, fecha, ponderación y horas."
    ), "acciones": []}


def _planificacion() -> dict:
    return {"texto": (
        "No puedo ordenar tus entregas sin ver fechas, ponderaciones y horas: inventarlas rompería la regla "
        "del proyecto. Pega las instrucciones o escribe cada actividad con su fecha y su peso, y te señalo "
        "los datos que faltan o se contradicen.\n\n"
        "Mientras tanto, revisa el Plan semanal con el modo que prefieras. El plan compara lo que cabe en tu "
        "tiempo disponible y muestra lo pendiente; no suma porcentajes de materias distintas ni promete "
        "una nota. La prioridad P combina importancia, urgencia y ponderación confirmada."
    ), "acciones": []}


def _datos_cuenta() -> dict:
    return {"texto": (
        "En esta ejecución no pude leer la planificación guardada en tu cuenta, así que no voy a inventar "
        "materias, actividades, notas ni prioridades. Revisa la vista Plan semanal, Actividades, Materias o "
        "Cuaderno de datos y vuelve a intentarlo. Si pegas aquí el texto, también puedo ayudarte a leerlo y "
        "señalar lo que falta."
    ), "acciones": []}


def _ayuda() -> dict:
    return {"texto": (
        "Soy el agente de KAIROS. Funciono con reglas locales y, si está configurado, con un modelo en tu "
        "máquina para temas generales. Puedo:\n\n"
        "• Leer una instrucción y señalar tipo, fechas, ponderación y horas candidatas.\n"
        "• Decirte qué datos faltan o son ambiguos antes de registrar una actividad.\n"
        "• Explicarte el índice P, los modos de priorización y las funciones de KAIROS.\n"
        "• Preparar una actividad sugerida para que la revises en el formulario.\n\n"
        "Pega la instrucción de tu docente o pregúntame por una función. No guardo nada ni decido por ti."
    ), "acciones": []}


def _fallback() -> dict:
    return {"texto": (
        "No encontré una instrucción académica ni una pregunta que pueda responder con mis reglas. Puedo "
        "analizar un texto con tipo de actividad, fechas, porcentajes u horas, o explicarte el índice P, "
        "el plan semanal, el cuaderno de datos o la privacidad.\n\n"
        "Soy una versión local y determinista: si no reconozco la intención, lo digo en lugar de inventar "
        "una respuesta."
    ), "acciones": []}


def es_general(mensaje: str) -> bool:
    """Indica si el mensaje cae fuera de los temas propios de KAIROS.

    Se usa para decidir si vale la pena consultar al modelo local. Las
    instrucciones académicas y las preguntas sobre la app se responden con
    reglas, porque esas respuestas son verificables y no dependen de un modelo.
    """
    texto = str(mensaje or "").strip()
    if not texto:
        return False
    n = normalizar(texto)
    con_datos = bool(
        extraer_fechas(texto)
        or extraer_porcentajes(texto)
        or extraer_horas(texto)
        or detectar_tipos(texto)
    )
    pregunta = es_pregunta(texto) or "?" in texto or "¿" in texto
    conocido = bool(
        TOPIC_PRIVACY.search(n)
        or TOPIC_PRIORITY.search(n)
        or TOPIC_FEATURES.search(n)
        or TOPIC_APP.search(n)
        or TOPIC_PLANNING.search(n)
        or TOPIC_MISSING.search(n)
        or TOPIC_ACCOUNT.search(n)
        or re.search(r"^(hola|buenas|hey|saludos)\b", n)
        or re.search(r"ayuda|que puedes|que haces|para que sirves", n)
    )
    # Las preguntas generales pueden ir al modelo; los enunciados sin datos
    # reconocibles siguen cayendo en la respuesta de fallback determinista.
    return pregunta and not con_datos and not conocido


def responder(mensaje: str, info_modelo: dict | None = None) -> dict:
    """Devuelve {"texto", "acciones"} usando reglas locales.

    ``info_modelo`` solo ajusta el texto de privacidad; no cambia extracciones
    ni acciones. Las reglas siguen siendo la fuente de verdad.
    """
    texto = str(mensaje or "").strip()
    if not texto:
        return _ayuda()

    n = normalizar(texto)
    fechas = extraer_fechas(texto)
    porcentajes = extraer_porcentajes(texto)
    horas = extraer_horas(texto)
    tipos = detectar_tipos(texto)
    con_datos = bool(fechas or porcentajes or horas or tipos)
    pregunta = es_pregunta(texto) or "?" in texto or "¿" in texto

    if TOPIC_PRIVACY.search(n) and not con_datos:
        return _privacidad(info_modelo)
    if pregunta and TOPIC_MISSING.search(n) and not con_datos:
        return _faltan_datos()
    if pregunta and TOPIC_ACCOUNT.search(n) and not con_datos:
        return _datos_cuenta()
    if pregunta and TOPIC_FEATURES.search(n) and not con_datos:
        return _funciones(texto)
    if pregunta and TOPIC_APP.search(n) and not con_datos:
        return _funciones(texto)
    if pregunta and TOPIC_PLANNING.search(n) and not con_datos:
        return _planificacion()
    if pregunta and TOPIC_PRIORITY.search(n) and not con_datos:
        return _indice_p()
    if con_datos:
        return _analizar(texto, tipos, fechas, porcentajes, horas)

    if TOPIC_PRIVACY.search(n):
        return _privacidad(info_modelo)
    if TOPIC_PRIORITY.search(n):
        return _indice_p()
    if TOPIC_PLANNING.search(n):
        return _planificacion()
    if TOPIC_ACCOUNT.search(n):
        return _datos_cuenta()
    if re.search(r"^(hola|buenas|hey|saludos)\b", n) or re.search(
        r"ayuda|que puedes|que haces|para que sirves", n
    ):
        return _ayuda()
    return _fallback()
