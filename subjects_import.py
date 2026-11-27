"""Importación segura de materias desde JSON, CSV y XLSX.

Solo analiza; no escribe en PostgreSQL. El cliente debe pedir confirmación antes
de añadir las materias al estado del usuario. No se inventan notas: si falta o
es inválida, `grade` queda `None`.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

MAX_SUBJECTS = 500
MAX_NAME_LENGTH = 80

NAME_KEYS = (
    "name",
    "nombre",
    "materia",
    "asignatura",
    "subject",
    "title",
    "titulo",
    "course",
    "curso",
    "clase",
    "materia nombre",
    "nombre de la materia",
    "nombre materia",
    "nombre asignatura",
    "asignatura nombre",
)

GRADE_KEYS = (
    "grade",
    "nota",
    "calificacion",
    "promedio",
    "score",
    "nota actual",
    "nota_actual",
    "nota actual escala 0 a 5",
    "nota actual (escala 0 a 5)",
    "nota actual 0-5",
    "nota 0-5",
    "nota actual 0 a 5",
    "grade actual",
    "grade actual (0-5)",
    "nota promedio",
    "promedio final",
)

CONTAINER_KEYS = (
    "subjects",
    "materias",
    "asignaturas",
    "courses",
    "cursos",
    "subject",
    "materia",
    "asignatura",
)


def _fold(value: object) -> str:
    text = str(value or "").strip().lower()
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").replace("_", " ")


def _name_keys() -> tuple[str, ...]:
    return tuple(_fold(k) for k in NAME_KEYS)


def _grade_keys() -> tuple[str, ...]:
    return tuple(_fold(k) for k in GRADE_KEYS)


def _first_value(row: dict, keys: tuple[str, ...]) -> object | None:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _parse_grade(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip()
        if not text:
            return None
        # Soporta "4,5", "4.5 / 5" y "4.5/5.0".
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text)
        if not match:
            return None
        try:
            number = float(match.group(0).replace(",", "."))
        except ValueError:
            return None
    if not math.isfinite(number):
        return None
    if number < 0 or number > 5:
        return None
    return number


def _parse_name(value: object) -> str | None:
    if value is None:
        return None
    name = re.sub(r"\s+", " ", str(value).strip())
    if not name:
        return None
    if len(name) > MAX_NAME_LENGTH:
        name = name[:MAX_NAME_LENGTH].strip()
    return name or None


def _row_from_mapping(raw: dict) -> dict:
    row: dict[str, object] = {}
    for key, value in raw.items():
        row[_fold(key)] = value
    return row


def _row_from_sequence(values: list, header: list[str]) -> dict:
    row: dict[str, object] = {}
    for index, key in enumerate(header):
        value = values[index] if index < len(values) else None
        if key:
            row[key] = value
    return row


def _extract_subject_items(obj: object) -> list[object]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for key in CONTAINER_KEYS:
            folded = _fold(key)
            for actual_key, value in obj.items():
                if _fold(actual_key) == folded and isinstance(value, list):
                    return value
        # Objeto único de materia.
        if _first_value(_row_from_mapping(obj), _name_keys()) is not None:
            return [obj]
    return []


def _json_items(obj: object) -> list[dict]:
    items = _extract_subject_items(obj)
    result: list[dict] = []
    for item in items:
        if isinstance(item, dict):
            result.append(_row_from_mapping(item))
        elif isinstance(item, str):
            result.append({_fold("name"): item})
    return result


def _csv_text(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _csv_rows(text: str) -> list[list[str]]:
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [row for row in reader]
    # Elimina filas completamente vacías.
    return [row for row in rows if any((cell or "").strip() for cell in row)]


def _table_items(rows: list[list[str]]) -> list[dict]:
    if not rows:
        return []
    header = [_fold(cell) for cell in rows[0]]
    # Si la primera fila no parece cabecera, tratarla como dato con nombre en A1.
    if not any(key in header for key in _name_keys()):
        # Sin cabecera clara, asumimos primera columna = nombre, segunda = nota.
        result: list[dict] = []
        for values in rows:
            row = {_fold("name"): values[0] if values else ""}
            if len(values) > 1:
                row[_fold("grade")] = values[1]
            result.append(row)
        return result
    result = []
    for values in rows[1:]:
        result.append(_row_from_sequence(values, header))
    return result


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _xml_text(elem: ET.Element) -> str:
    return "".join(t.text or "" for t in elem.iter() if _local_name(t.tag) == "t")


def _column_index(cell_ref: str | None) -> int:
    match = re.match(r"([A-Za-z]+)", cell_ref or "A1")
    letters = (match.group(1) if match else "A").upper()
    index = 0
    for ch in letters:
        index = index * 26 + (ord(ch) - 64)
    return index - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        data = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(data)
    items: list[str] = []
    for si in root:
        if _local_name(si.tag) != "si":
            continue
        items.append(_xml_text(si))
    return items


def _worksheet_names(zf: zipfile.ZipFile) -> list[str]:
    names = [
        n for n in zf.namelist()
        if n.startswith("xl/worksheets/") and n.endswith(".xml") and not n.endswith(".rels")
    ]
    names.sort()
    # sheet1.xml primero si existe.
    for preferred in ("xl/worksheets/sheet1.xml", "xl/worksheets/sheet.xml"):
        if preferred in names:
            names.remove(preferred)
            names.insert(0, preferred)
            break
    return names


def _xlsx_rows(data: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        shared = _shared_strings(zf)
        sheet_names = _worksheet_names(zf)
        if not sheet_names:
            raise ValueError("El XLSX no contiene hojas.")
        root = ET.fromstring(zf.read(sheet_names[0]))
    rows: list[list[str]] = []
    for row_elem in root.iter():
        if _local_name(row_elem.tag) != "row":
            continue
        cells: dict[int, str] = {}
        for cell in row_elem:
            if _local_name(cell.tag) != "c":
                continue
            ref = cell.attrib.get("r")
            col = _column_index(ref)
            cell_type = cell.attrib.get("t")
            value: object | None = None
            if cell_type == "inlineStr":
                value = _xml_text(cell)
            else:
                v_elem = next((c for c in cell if _local_name(c.tag) == "v"), None)
                raw = v_elem.text if v_elem is not None else None
                if raw is None:
                    value = None
                elif cell_type == "s":
                    try:
                        value = shared[int(raw)]
                    except (ValueError, IndexError):
                        value = ""
                elif cell_type == "b":
                    value = "1" if raw == "1" else "0"
                else:
                    value = raw
            cells[col] = "" if value is None else str(value)
        max_col = max(cells) if cells else -1
        values = [cells.get(i, "") for i in range(max_col + 1)]
        if any((v or "").strip() for v in values):
            rows.append(values)
    return rows


def _normalize_items(items: list[dict], warnings: list[str]) -> list[dict]:
    subjects: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(items, start=1):
        name = _parse_name(_first_value(item, _name_keys()))
        if not name:
            warnings.append(f"Fila {index}: sin nombre de materia; se omite.")
            continue
        key = _fold(name)
        if key in seen:
            warnings.append(f"Fila {index}: «{name}» está duplicada en el archivo; se omite.")
            continue
        raw_grade = _first_value(item, _grade_keys())
        grade = _parse_grade(raw_grade)
        if raw_grade not in (None, "") and grade is None:
            warnings.append(f"Fila {index} («{name}»): nota inválida; se importa sin nota.")
        seen.add(key)
        subjects.append({"name": name, "grade": grade})
        if len(subjects) >= MAX_SUBJECTS:
            warnings.append(f"Se importan como máximo {MAX_SUBJECTS} materias; se omiten las restantes.")
            break
    return subjects


def parse_subjects_file(filename: str, data: bytes) -> dict:
    """Analiza un archivo de materias. Lanza ValueError si no es válido."""
    name = (filename or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    warnings: list[str] = []
    if not data:
        raise ValueError("El archivo está vacío.")

    if ext == "json" or (not ext and data.lstrip()[:1] in (b"{", b"[")):
        try:
            obj = json.loads(_csv_text(data))
        except json.JSONDecodeError as exc:
            raise ValueError("El JSON no es válido.") from exc
        items = _json_items(obj)
        fmt = "json"
    elif ext in ("csv", "txt"):
        items = _table_items(_csv_rows(_csv_text(data)))
        fmt = "csv"
    elif ext in ("xlsx", "xlsm"):
        try:
            rows = _xlsx_rows(data)
        except zipfile.BadZipFile as exc:
            raise ValueError("El XLSX no es un archivo Excel válido.") from exc
        except ET.ParseError as exc:
            raise ValueError("No pude leer el contenido XML del XLSX.") from exc
        items = _table_items(rows)
        fmt = "xlsx"
    else:
        raise ValueError("Formato no soportado. Usa .json, .csv o .xlsx.")

    subjects = _normalize_items(items, warnings)
    if not subjects:
        raise ValueError("No encontré materias válidas. Necesito un nombre por materia.")
    return {"subjects": subjects, "warnings": warnings, "format": fmt, "count": len(subjects)}
