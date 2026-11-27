"""Consultas de solo lectura sobre la planificación de una cuenta KAIROS.

Este módulo no escribe en PostgreSQL ni propone acciones. Recibe el objeto
``planner_data`` de la cuenta autenticada y responde preguntas como «qué
actividades tengo pendientes», «qué materias tengo» o «cuál es mi índice P».
Las respuestas se calculan con reglas y con los datos guardados; nunca se
inventan materias, fechas, notas ni referencias.

La integración con el modelo local es deliberadamente nula: los datos de la
cuenta no salen del servidor. ``app.py`` decide cuándo leer ``planner_data`` y
pasa el resultado a ``responder_cuenta``.
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta

from agente_local import CATALOG, normalizar

LIMITE_LISTA = 20
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
TYPE_HINTS = [
    (5, re.compile(r"\b(parcial|examen|prueba final|entrega final|proyecto final)\b")),
    (4, re.compile(r"\b(quiz|exposicion|presentacion|proyecto|sustentacion)\b")),
    (3, re.compile(r"\b(taller|tarea|trabajo|entrega)\b")),
    (2, re.compile(r"\b(actividad|ejercicio|lectura|practica)\b")),
    (1, re.compile(r"\b(aviso|informacion|comunicado)\b")),
]

ACTIVIDADES = (
    r"actividades?|tareas?|trabajos?|entregas?|examenes?|parciales?|"
    r"quizzes?|quices?|talleres?|proyectos?"
)
_DATOS = (
    ACTIVIDADES
    + r"|materias?|asignaturas?|cursos?|notas?|calificaciones?|"
    r"prioridades?|indice\s+p|puntaje\s+p|\bp\b|cuaderno|plan\s+semanal|horario|"
    r"registros?|semana|hoy|ma[nñ]ana|vencid[oa]s?|atrasad[oa]s?"
)
_POSEEDOR = r"mi|mis|me|tengo|tienes|cuenta|hay"
CONSULTA_CUENTA = re.compile(
    r"\b(?:(?:" + _POSEEDOR + r")\b[^.?!]*\b(?:" + _DATOS + r")\b"
    r"|(?:" + _DATOS + r")\b[^.?!]*\b(?:"
    + _POSEEDOR
    + r"|hay|pendientes?|registrad[oa]s?|guardad[oa]s?|completad[oa]s?)\b)",
    re.IGNORECASE,
)
PETICION = re.compile(
    r"^(que|cual|cuales|cuanto|cuanta|cuantos|cuantas|dime|muestra|muestrame|"
    r"lista|listar|resume|resumen|cuentame|ensename|tengo|tienes|hay|mis|mi|"
    r"actividades|tareas|materias|notas|prioridades|cuaderno|plan)\b",
    re.IGNORECASE,
)
INSTRUCCION = re.compile(
    r"\b(entrega|entregar|vence|vale|equivale|ponderacion|porcentaje|horas?)\b",
    re.IGNORECASE,
)
PENDIENTES = re.compile(r"\b(pendientes?|por hacer|sin terminar|no completad[oa]s?|abiertas?)\b", re.IGNORECASE)
COMPLETADAS = re.compile(r"\b(completad[oa]s?|terminad[oa]s?|hech[oa]s?|finalizad[oa]s?|done)\b", re.IGNORECASE)
MATERIAS = re.compile(r"\b(materias?|asignaturas?|cursos?)\b", re.IGNORECASE)
NOTAS = re.compile(r"\b(notas?|calificaciones?|promedio|promedios?)\b", re.IGNORECASE)
PRIORIDAD = re.compile(r"\b(indice\s+p|puntaje\s+p|\bp\b|prioridad(?:es)?|priorizacion)\b", re.IGNORECASE)
CUADERNO = re.compile(r"\b(cuaderno|experimentos?|bitacora|registros? de datos)\b", re.IGNORECASE)
SEMANA = re.compile(r"\b(esta semana|pr[oó]ximos?\s+7\s+d[ií]as|siete\s+d[ií]as|semana)\b", re.IGNORECASE)
HOY = re.compile(r"\bhoy\b", re.IGNORECASE)
MANANA = re.compile(r"\bma[nñ]ana\b", re.IGNORECASE)
VENCIDAS = re.compile(r"\b(vencid[oa]s?|atrasad[oa]s?)\b", re.IGNORECASE)
SIN_FECHA = re.compile(r"\bsin fecha\b", re.IGNORECASE)
CONTAR = re.compile(r"\b(cuantas?|cuantos?|numero de|total de)\b", re.IGNORECASE)
HORAS = re.compile(r"\b(horas disponibles|disponibilidad|plan semanal|horario)\b", re.IGNORECASE)
RESUMEN = re.compile(r"\b(resumen|que datos|mi cuenta|mi informacion|cómo va|como va)\b", re.IGNORECASE)
QUE_TENGO = re.compile(r"\b(que tengo|que hay|que viene|tengo algo|hay algo|pendientes?|vencid[oa]s?)\b", re.IGNORECASE)


def es_consulta_cuenta(mensaje: str) -> bool:
    """Indica si el mensaje pide datos guardados de la cuenta.

    Evita confundir una instrucción académica («Tengo un parcial el 15/03»)
    con una consulta («¿Qué parciales tengo?»).
    """
    texto = str(mensaje or "").strip()
    if not texto:
        return False
    n = normalizar(texto)
    if not CONSULTA_CUENTA.search(n):
        return False
    # «¿Qué actividades hay en la app?» pregunta por una función, no por la
    # cuenta. Si hay un poseedor explícito («mis», «tengo»), sí es de cuenta.
    if re.search(r"\b(en la app|de la app|en kairos|de kairos)\b", n) and not re.search(
        r"\b(mi|mis|me|tengo|tienes|cuenta)\b", n
    ):
        return False
    pregunta = bool(
        "?" in texto
        or "¿" in texto
        or PETICION.search(n)
        or re.match(r"^(actividades|tareas|materias|notas|prioridades|cuaderno|plan)\b", n)
    )
    if not pregunta:
        return False
    # «Tengo un parcial y un taller» describe una instrucción, no consulta.
    if re.match(r"^(tengo|tienes|hay)\b", n) and "?" not in texto and "¿" not in texto:
        if not re.search(r"\b(pendientes?|registrad[oa]s?|guardad[oa]s?|completad[oa]s?|cuantas?|cuantos?|resumen)\b", n):
            return False
    # Una instrucción con fechas o porcentajes se analiza con el agente normal.
    if INSTRUCCION.search(n) and not ("?" in texto or "¿" in texto or PETICION.search(n)):
        return False
    return True


def _texto(valor, maximo: int = 160) -> str:
    if not isinstance(valor, str):
        return ""
    limpio = re.sub(r"\s+", " ", valor).strip()
    return limpio[:maximo]


def _numero(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    return numero if math.isfinite(numero) else None


def _fecha(valor):
    if not isinstance(valor, str) or not valor.strip():
        return None
    texto = valor.strip()
    for formato in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _fmt_fecha(valor) -> str:
    fecha = _fecha(valor)
    if not fecha:
        return "sin fecha"
    return fecha.strftime("%d/%m/%Y %H:%M")


def _plural(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _etiqueta_tipo(tarea: dict) -> str:
    codigo = str(tarea.get("category") or "TAR").upper()
    return CATALOG.get(codigo, ("Actividad", 3, "Actividad"))[2]


def _peso_confirmado(tarea: dict) -> bool:
    return bool(tarea.get("confirmed") is True or tarea.get("weightDeclared") is True or tarea.get("weightConfirmed") is True)


def prioridad(tarea: dict, ahora: datetime | None = None) -> dict:
    """Calcula el P de una actividad con la misma fórmula de la interfaz."""
    ahora = ahora or datetime.now()
    codigo = str(tarea.get("category") or "TAR").upper()
    nivel = CATALOG.get(codigo, ("Actividad", 3, "Actividad"))[1]
    if tarea.get("confirmed") is not True:
        texto = normalizar(f"{tarea.get('title') or ''} {tarea.get('source') or ''}")
        candidatos = [nivel]
        plausibles = []
        for nivel_posible, patron in TYPE_HINTS:
            if patron.search(texto):
                candidatos.append(nivel_posible)
                plausibles.append(nivel_posible)
        if plausibles:
            nivel = max(candidatos)
    importancia = max(0.0, min(1.0, nivel / 5))
    vencimiento = _fecha(tarea.get("due"))
    urgencia = None
    if vencimiento:
        horas = (vencimiento - ahora).total_seconds() / 3600
        if horas <= 24:
            urgencia = 1.0
        elif horas <= 48:
            urgencia = 0.85
        elif horas <= 72:
            urgencia = 0.70
        elif horas <= 168:
            urgencia = 0.50
        elif horas <= 336:
            urgencia = 0.25
        else:
            urgencia = 0.10
    peso = _numero(tarea.get("weight"))
    ponderacion = None
    if _peso_confirmado(tarea) and peso is not None and 0 <= peso <= 100:
        ponderacion = min(1.0, peso / 30)
    componentes = [(importancia, 0.45)]
    if urgencia is not None:
        componentes.append((urgencia, 0.35))
    if ponderacion is not None:
        componentes.append((ponderacion, 0.20))
    denominador = sum(peso_componente for _valor, peso_componente in componentes)
    puntaje = sum(valor * peso_componente for valor, peso_componente in componentes) / denominador
    etiqueta = "Crítica" if puntaje >= 0.8 else "Alta" if puntaje >= 0.6 else "Media" if puntaje >= 0.4 else "Baja"
    return {
        "percent": round(puntaje * 100),
        "level": etiqueta,
        "urgency": urgencia is not None,
        "gradeWeight": ponderacion is not None,
    }


def _materias(data: dict) -> list[dict]:
    return [s for s in data.get("subjects", []) if isinstance(s, dict)]


def _tareas(data: dict) -> list[dict]:
    return [t for t in data.get("tasks", []) if isinstance(t, dict)]


def _laboratorio(data: dict) -> list[dict]:
    return [e for e in data.get("labEntries", []) if isinstance(e, dict)]


def _reales(items: list[dict]) -> list[dict]:
    return [item for item in items if not item.get("demo")]


def _mapa_materias(subjects: list[dict]) -> dict:
    return {
        str(s.get("id")): _texto(s.get("name"), 100) or "Materia sin nombre"
        for s in subjects
        if s.get("id") is not None
    }


def _materia_mencionada(texto: str, subjects: list[dict]) -> dict | None:
    n = normalizar(texto)
    candidatos = []
    for subject in subjects:
        nombre = _texto(subject.get("name"), 120)
        clave = normalizar(nombre)
        if not clave:
            continue
        if clave in n:
            candidatos.append((len(clave), subject))
            continue
        palabras = [
            palabra
            for palabra in clave.split()
            if len(palabra) >= 4 and palabra not in {"datos", "para", "ciencia", "ciencias", "automatico", "automatica"}
        ]
        if any(palabra in n for palabra in palabras):
            candidatos.append((sum(len(palabra) for palabra in palabras), subject))
    if not candidatos:
        return None
    return max(candidatos, key=lambda item: item[0])[1]


def _nota_demo(cantidad: int, singular: str, plural: str) -> str:
    if not cantidad:
        return ""
    return f"\n\nNo incluí {_plural(cantidad, singular, plural)} de ejemplo marcados como demostración."


def _linea_tarea(tarea: dict, subjects: dict, ahora: datetime, con_prioridad: bool = True) -> str:
    materia = subjects.get(str(tarea.get("subjectId"))) or "Materia no registrada"
    partes = [materia, _etiqueta_tipo(tarea)]
    if tarea.get("due"):
        partes.append(_fmt_fecha(tarea.get("due")))
    peso = _numero(tarea.get("weight"))
    if peso is not None:
        partes.append(f"{peso:g} %" + ("" if _peso_confirmado(tarea) else " por confirmar"))
    horas = _numero(tarea.get("hours"))
    if horas is not None:
        partes.append(f"{horas:g} h")
    if tarea.get("optional"):
        partes.append("opcional")
    if tarea.get("done"):
        partes.append("completada")
    if tarea.get("confirmed") is not True:
        partes.append("datos por confirmar")
    detalle = " · ".join(parte for parte in partes if parte)
    linea = f"• {_texto(tarea.get('title'), 140) or 'Actividad sin título'} — {detalle}"
    if con_prioridad:
        calculo = prioridad(tarea, ahora)
        linea += f" · P {calculo['percent']}/100 ({calculo['level']})"
    return linea


def _ordenar_por_fecha(tareas: list[dict]) -> list[dict]:
    return sorted(
        tareas,
        key=lambda t: (
            _fecha(t.get("due")) is None,
            _fecha(t.get("due")) or datetime.max,
            normalizar(t.get("title")),
        ),
    )


def _lista_tareas(tareas: list[dict], subjects: dict, ahora: datetime, titulo: str) -> str:
    if not tareas:
        return titulo + "\n\nNo hay actividades que coincidan con esa consulta."
    visibles = tareas[:LIMITE_LISTA]
    lineas = [_linea_tarea(t, subjects, ahora) for t in visibles]
    extra = ""
    if len(tareas) > LIMITE_LISTA:
        extra = f"\n\nHay {len(tareas) - LIMITE_LISTA} actividades más; puedes pedir una materia o una fecha concreta."
    return f"{titulo}\n\n" + "\n".join(lineas) + extra


def _resumen(data: dict, ahora: datetime) -> str:
    subjects = _materias(data)
    tasks = _tareas(data)
    lab = _laboratorio(data)
    reales = _reales(tasks)
    pendientes = [t for t in reales if not t.get("done")]
    completadas = [t for t in reales if t.get("done")]
    mapa = _mapa_materias(subjects)
    partes = [
        f"En tu cuenta hay {_plural(len(_reales(subjects)), 'materia', 'materias')}, "
        f"{_plural(len(pendientes), 'actividad pendiente', 'actividades pendientes')}, "
        f"{_plural(len(completadas), 'actividad completada', 'actividades completadas')} y "
        f"{_plural(len(_reales(lab)), 'registro en el cuaderno', 'registros en el cuaderno')}."
    ]
    if pendientes:
        proximas = _ordenar_por_fecha(pendientes)[:5]
        partes.append("\n\nPróximas pendientes:\n" + "\n".join(_linea_tarea(t, mapa, ahora) for t in proximas))
    elif not reales:
        partes.append("\n\nNo hay actividades reales registradas; solo ejemplos de demostración.")
    return "\n".join(partes) + _nota_demo(len(tasks) - len(reales), "actividad", "actividades")


def _materias_respuesta(data: dict, texto: str, ahora: datetime) -> str:
    subjects = _materias(data)
    reales = _reales(subjects)
    tasks = _reales(_tareas(data))
    if not reales:
        return (
            "No hay materias reales registradas en tu cuenta."
            + (" Solo hay materias de ejemplo marcadas como demostración." if subjects else "")
            + "\n\nPuedes agregarlas en la vista Materias."
        )
    pendientes_por_materia = {}
    for tarea in tasks:
        if not tarea.get("done"):
            clave = str(tarea.get("subjectId"))
            pendientes_por_materia[clave] = pendientes_por_materia.get(clave, 0) + 1
    lineas = []
    notas = []
    for subject in reales:
        nombre = _texto(subject.get("name"), 120) or "Materia sin nombre"
        nota = _numero(subject.get("grade"))
        detalle = []
        if nota is not None:
            detalle.append(f"nota registrada: {nota:g}")
            notas.append(nota)
        else:
            detalle.append("sin nota registrada")
        pendientes = pendientes_por_materia.get(str(subject.get("id")), 0)
        detalle.append(_plural(pendientes, "actividad pendiente", "actividades pendientes"))
        lineas.append(f"• {nombre} — " + " · ".join(detalle))
    respuesta = "Estas son las materias guardadas en tu cuenta:\n\n" + "\n".join(lineas)
    if NOTAS.search(normalizar(texto)) and notas:
        promedio = sum(notas) / len(notas)
        respuesta += (
            f"\n\nPromedio simple de las {len(notas)} notas registradas: {promedio:.2f}. "
            "No es un promedio ponderado ni una nota oficial."
        )
    return respuesta + _nota_demo(len(subjects) - len(reales), "materia", "materias")


def _notas_respuesta(data: dict, texto: str) -> str:
    reales = _reales(_materias(data))
    con_nota = [s for s in reales if _numero(s.get("grade")) is not None]
    if not con_nota:
        return "No hay notas registradas en las materias reales de tu cuenta."
    lineas = [
        f"• {_texto(s.get('name'), 120) or 'Materia sin nombre'}: {_numero(s.get('grade')):g}"
        for s in con_nota
    ]
    respuesta = "Notas registradas por materia:\n\n" + "\n".join(lineas)
    if re.search(r"\bpromedio", normalizar(texto)):
        promedio = sum(_numero(s.get("grade")) for s in con_nota) / len(con_nota)
        respuesta += (
            f"\n\nPromedio simple: {promedio:.2f} sobre {len(con_nota)} materias. "
            "No es un promedio ponderado ni una nota oficial."
        )
    return respuesta


def _actividades_respuesta(data: dict, texto: str, ahora: datetime) -> str:
    tasks = _tareas(data)
    reales = _reales(tasks)
    subjects = _mapa_materias(_materias(data))
    if not reales:
        if tasks:
            return (
                "No hay actividades reales registradas en tu cuenta; solo hay "
                f"{_plural(len(tasks), 'actividad de ejemplo', 'actividades de ejemplo')} marcadas como demostración."
            )
        return "No hay actividades registradas en tu cuenta. Puedes crear una en la vista Actividades."

    n = normalizar(texto)
    if COMPLETADAS.search(n):
        seleccion = [t for t in reales if t.get("done")]
        titulo = "Estas son tus actividades completadas guardadas en KAIROS:"
    elif re.search(r"\btodas?\b", n):
        seleccion = list(reales)
        titulo = "Estas son todas tus actividades guardadas en KAIROS:"
    else:
        seleccion = [t for t in reales if not t.get("done")]
        titulo = "Estas son tus actividades pendientes guardadas en KAIROS:"

    materia = _materia_mencionada(texto, _materias(data))
    if materia:
        seleccion = [t for t in seleccion if str(t.get("subjectId")) == str(materia.get("id"))]
        titulo = f"Actividades de {_texto(materia.get('name'), 100)}:"
    if VENCIDAS.search(n):
        seleccion = [t for t in seleccion if _fecha(t.get("due")) and _fecha(t.get("due")) < ahora]
        titulo = "Actividades vencidas que siguen pendientes:"
    elif HOY.search(n):
        seleccion = [t for t in seleccion if _fecha(t.get("due")) and _fecha(t.get("due")).date() == ahora.date()]
        titulo = "Actividades que vencen hoy:"
    elif MANANA.search(n):
        manana = ahora.date() + timedelta(days=1)
        seleccion = [t for t in seleccion if _fecha(t.get("due")) and _fecha(t.get("due")).date() == manana]
        titulo = "Actividades que vencen mañana:"
    elif SEMANA.search(n):
        limite = ahora.date() + timedelta(days=7)
        seleccion = [
            t
            for t in seleccion
            if _fecha(t.get("due")) and ahora.date() <= _fecha(t.get("due")).date() < limite
        ]
        titulo = "Actividades pendientes para los próximos 7 días:"
    elif SIN_FECHA.search(n):
        seleccion = [t for t in seleccion if not _fecha(t.get("due"))]
        titulo = "Actividades pendientes sin fecha:"

    seleccion = _ordenar_por_fecha(seleccion)
    if CONTAR.search(n):
        if not seleccion:
            return "No hay actividades que coincidan con esa consulta."
        return (
            f"Tienes {_plural(len(seleccion), 'actividad', 'actividades')} que coinciden con la consulta. "
            "Puedes pedir la lista completa si quieres verlas."
        )
    respuesta = _lista_tareas(seleccion, subjects, ahora, titulo)
    if VENCIDAS.search(n) and seleccion:
        respuesta += "\n\nRevisa si siguen vigentes y actualiza su estado en Actividades."
    return respuesta + _nota_demo(len(tasks) - len(reales), "actividad", "actividades")


def _prioridades_respuesta(data: dict, ahora: datetime) -> str:
    reales = _reales(_tareas(data))
    pendientes = [t for t in reales if not t.get("done")]
    if not pendientes:
        return (
            "No tienes actividades pendientes reales para calcular prioridades. "
            "KAIROS calcula un P por actividad; no hay un índice P único de la cuenta."
        )
    subjects = _mapa_materias(_materias(data))
    ordenadas = sorted(
        pendientes,
        key=lambda t: (-prioridad(t, ahora)["percent"], _fecha(t.get("due")) or datetime.max),
    )
    lineas = [_linea_tarea(t, subjects, ahora) for t in ordenadas[:LIMITE_LISTA]]
    return (
        "KAIROS calcula un P por actividad; no hay un índice P único de la cuenta. "
        "Estas son tus pendientes ordenadas por P:\n\n"
        + "\n".join(lineas)
        + "\n\nEl cálculo usa importancia, urgencia y ponderación confirmada. "
        "Los modos de priorización solo reordenan; no cambian el P."
    )


def _cuaderno_respuesta(data: dict, texto: str) -> str:
    entradas = _laboratorio(data)
    reales = _reales(entradas)
    if not reales:
        if entradas:
            return (
                "No hay registros reales en tu cuaderno; solo hay "
                f"{_plural(len(entradas), 'registro de ejemplo', 'registros de ejemplo')} de demostración."
            )
        return "Tu cuaderno de datos no tiene registros reales todavía."
    if CONTAR.search(normalizar(texto)):
        return f"Tu cuaderno tiene {_plural(len(reales), 'registro real', 'registros reales')}."
    subjects = _mapa_materias(_materias(data))
    lineas = []
    for entrada in reales[:LIMITE_LISTA]:
        materia = subjects.get(str(entrada.get("subjectId"))) or "Proyecto personal"
        titulo = _texto(entrada.get("title"), 140) or "Registro sin título"
        pregunta = _texto(entrada.get("question"), 160)
        fecha = _texto(entrada.get("updatedAt") or entrada.get("createdAt"), 10)
        detalle = f"• {titulo} — {materia}"
        if fecha:
            detalle += f" · actualizado: {fecha}"
        if pregunta:
            detalle += f"\n  Pregunta: {pregunta}"
        lineas.append(detalle)
    extra = ""
    if len(reales) > LIMITE_LISTA:
        extra = f"\n\nHay {len(reales) - LIMITE_LISTA} registros más en el cuaderno."
    return "Registros reales de tu cuaderno:\n\n" + "\n".join(lineas) + extra


def _horas_respuesta(data: dict, ahora: datetime) -> str:
    settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
    disponibles = _numero(settings.get("availableHours"))
    reales = _reales(_tareas(data))
    pendientes = [t for t in reales if not t.get("done")]
    semana = [
        t
        for t in pendientes
        if _fecha(t.get("due")) and ahora.date() <= _fecha(t.get("due")).date() < ahora.date() + timedelta(days=7)
    ]
    horas = sum(_numero(t.get("hours")) or 0 for t in semana)
    partes = []
    if disponibles is not None:
        partes.append(f"Tu disponibilidad semanal registrada es {disponibles:g} h.")
    else:
        partes.append("No hay horas disponibles registradas en Preferencias.")
    partes.append(
        f"En los próximos 7 días tienes {_plural(len(semana), 'actividad pendiente', 'actividades pendientes')} "
        f"con unas {horas:g} h estimadas."
    )
    if disponibles is not None and horas > disponibles:
        partes.append("Las horas estimadas superan tu disponibilidad; revisa el plan y decide qué priorizar.")
    elif disponibles is not None:
        partes.append("Las horas estimadas caben en tu disponibilidad, sin contar imprevistos.")
    return " ".join(partes)


def responder_cuenta(mensaje: str, data: dict | None, ahora: datetime | None = None) -> dict | None:
    """Responde una consulta de cuenta en modo solo lectura.

    Devuelve ``None`` si el mensaje no es una consulta de cuenta. Si lo es pero
    no hay datos legibles, devuelve una explicación sin inventar información.
    """
    if not es_consulta_cuenta(mensaje):
        return None
    if not isinstance(data, dict):
        return {
            "texto": (
                "No pude leer la planificación de tu cuenta en este momento. "
                "No voy a inventar materias, actividades ni notas. Revisa la vista Plan semanal o Actividades "
                "y vuelve a intentarlo."
            ),
            "acciones": [],
        }
    ahora = ahora or datetime.now()
    texto = str(mensaje or "")
    n = normalizar(texto)

    try:
        if CUADERNO.search(n):
            cuerpo = _cuaderno_respuesta(data, texto)
        elif HORAS.search(n):
            cuerpo = _horas_respuesta(data, ahora)
        elif PRIORIDAD.search(n):
            cuerpo = _prioridades_respuesta(data, ahora)
        elif NOTAS.search(n):
            cuerpo = _notas_respuesta(data, texto)
        elif MATERIAS.search(n):
            cuerpo = _materias_respuesta(data, texto, ahora)
        elif RESUMEN.search(n) and not re.search(r"\b(actividades?|tareas?|entregas?|examenes?|parciales?)\b", n):
            cuerpo = _resumen(data, ahora)
        elif (
            re.search(r"\b" + ACTIVIDADES + r"\b", n)
            or PENDIENTES.search(n)
            or COMPLETADAS.search(n)
            or QUE_TENGO.search(n)
        ):
            cuerpo = _actividades_respuesta(data, texto, ahora)
        elif RESUMEN.search(n):
            cuerpo = _resumen(data, ahora)
        else:
            cuerpo = _resumen(data, ahora)
    except (TypeError, ValueError, KeyError):
        return {
            "texto": (
                "Leí la planificación de tu cuenta, pero no pude interpretar una parte de los datos. "
                "No voy a inventar la respuesta. Revisa la vista correspondiente en KAIROS."
            ),
            "acciones": [],
        }
    return {
        "texto": "Según los datos guardados en tu cuenta:\n\n" + cuerpo + "\n\nNo modifiqué nada.",
        "acciones": [],
    }
