#!/usr/bin/env python3
"""
kaizen-cli.py: Herramienta determinista para gestionar el tablero KAIZEN.md:
- Inicializa el tablero desde plantilla (con límite de compromisos abiertos configurable, 5 por defecto)
- Registra compromisos con cortes automáticos (+5 horas, +20 horas y +1 semana) y cuadrante PICK
  heredado de un A3 (--a3 y --opcion) o calculado por --impacto y --esfuerzo cuando no viene de un A3
- Cierra compromisos (cerrar) registrando la reflexión (Hansei) y si la mejora se sostuvo (si|no)
- Agrega mejoras Kaizen (Muda eliminada + Poka-Yoke en el Gemba) y Jugadas VSM
- Emite el reporte de estado ordenando compromisos abiertos por cuadrante PICK y avisando si superan el límite
"""

from __future__ import annotations

import datetime as dt
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "resources" / "plantilla-kaizen.md"
DEFAULT_MAX_OPEN = 5

PICK_ORDER: dict[str, int] = {
    "Implementar": 0,
    "Desafío": 1,
    "Posible": 2,
    "Eliminar": 3,
    "Sin puntuar": 4,
}

CANONICAL_QUADRANTS: dict[str, str] = {
    "implementar": "Implementar",
    "desafío": "Desafío",
    "desafio": "Desafío",
    "posible": "Posible",
    "eliminar": "Eliminar",
    "sin puntuar": "Sin puntuar",
}

RESERVED_HEADER_IDS: set[str] = {"id", "fecha", "id jugada"}

FORBIDDEN_WHO_PATTERNS = re.compile(
    # (?!\.\w): un nombre de archivo como CLAUDE.md es un componente, no el agente Claude.
    r"^(?:el\s+)?(?:agente|usuario|humano|persona|desarrollador|programador|operador|autor|claude|agy|elefante|goldfish)\b(?!\.\w)",
    re.IGNORECASE,
)


def read_board(path: Path) -> tuple[str, str]:
    if not path.exists():
        raise ValueError(f"No existe el archivo: {path}")
    if not path.is_file():
        raise ValueError(f"La ruta no es un archivo regular: {path}")
    try:
        raw = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"No se pudo decodificar el archivo en UTF-8: {path}") from exc
    eol = "\r\n" if "\r\n" in raw else "\n"
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    return normalized, eol


def write_board(path: Path, text: str, eol: str = "\n") -> None:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    out = normalized.replace("\n", eol) if eol != "\n" else normalized
    path.write_bytes(out.encode("utf-8"))



def parse_datetime(dt_str: str | None) -> dt.datetime:
    if not dt_str:
        return dt.datetime.now().replace(second=0, microsecond=0)
    raw = dt_str.strip()
    try:
        if len(raw) == 10 and re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
            d = dt.date.fromisoformat(raw)
            return dt.datetime(d.year, d.month, d.day, 0, 0)
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Fecha inválida '{dt_str}': usa AAAA-MM-DD o AAAA-MM-DDTHH:MM") from exc
    if parsed.tzinfo is not None:
        raise ValueError(
            f"Fecha inválida '{dt_str}': usa AAAA-MM-DD o AAAA-MM-DDTHH:MM sin zona horaria"
        )
    return parsed


def format_dt(value: dt.datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def sanitize_cell(text: str) -> str:
    cleaned = text.replace("\r", " ").replace("\n", " ").strip()
    return re.sub(r"(?<!\\)\|", r"\\|", cleaned)


CELL_SEPARATOR = re.compile(r"(?<!\\)\|")


def split_row(line: str, *, unescape: bool = False) -> list[str]:
    """Parte una fila de tabla Markdown en celdas respetando la barra escapada (`\\|`).

    Con `unescape` la celda se entrega con la barra sin su contrabarra (para leer un valor);
    sin él queda tal cual, para poder volver a escribir la fila sin perder nada.
    """
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    cells = [cell.strip() for cell in CELL_SEPARATOR.split(inner)]
    return [cell.replace("\\|", "|") for cell in cells] if unescape else cells


def normalize_level(raw: str, label: str) -> str:
    token = raw.strip().lower().split()[0] if raw and raw.strip() else ""
    if token not in {"alto", "bajo"}:
        raise ValueError(f"Valor inválido para {label}: '{raw}'. Usa 'alto' o 'bajo'.")
    return token


def calculate_pick_quadrant(impacto_raw: str, esfuerzo_raw: str) -> str:
    impacto = normalize_level(impacto_raw, "--impacto")
    esfuerzo = normalize_level(esfuerzo_raw, "--esfuerzo")
    if impacto == "alto" and esfuerzo == "bajo":
        return "Implementar"
    if impacto == "alto" and esfuerzo == "alto":
        return "Desafío"
    if impacto == "bajo" and esfuerzo == "bajo":
        return "Posible"
    return "Eliminar"


def read_pick_from_a3(a3_path: Path, opcion_code: str) -> str:
    if not a3_path.exists():
        raise ValueError(f"No existe el archivo A3: {a3_path}")
    if not a3_path.is_file():
        raise ValueError(f"La ruta del A3 no es un archivo regular: {a3_path}")
    code_norm = re.sub(r"[*_`]", "", opcion_code).strip()
    if not code_norm:
        raise ValueError("El código de --opcion no puede estar vacío.")
    target_low = code_norm.lower()

    try:
        lines = a3_path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError(f"No se pudo decodificar el archivo A3 en UTF-8: {a3_path}") from exc
    in_sec5 = False
    opt_idx = 0
    quad_idx = 5
    matches: list[str] = []

    for line in lines:
        if line.startswith("## "):
            in_sec5 = "5." in line or "contramedida" in line.lower()
            continue
        if not line.strip().startswith("|") or re.search(r"\|\s*:?---", line):
            continue
        cols = split_row(line, unescape=True)
        if not cols:
            continue
        low_cols = [re.sub(r"[*_`]", "", c).strip().lower() for c in cols]
        if any(h in low_cols[0] for h in ("opción", "opcion")) and any("cuadrante" in c for c in low_cols):
            opt_idx = 0
            for idx, cname in enumerate(low_cols):
                if "cuadrante" in cname:
                    quad_idx = idx
                    break
            in_sec5 = True
            continue
        if not in_sec5 or len(cols) <= max(opt_idx, quad_idx):
            continue

        cell_opt = re.sub(r"[*_`]", "", cols[opt_idx]).strip()
        cell_code = re.split(r"[\s:]+", cell_opt, maxsplit=1)[0] if cell_opt else ""
        if cell_code and cell_code.lower() == target_low:
            matches.append(cols[quad_idx])

    if not matches:
        raise ValueError(f"No se encontró la opción '{opcion_code}' en la tabla de opciones del A3: {a3_path}")
    if len(matches) > 1:
        raise ValueError(f"La opción '{code_norm}' está repetida en la tabla de opciones del A3: {a3_path}")

    raw_quad = re.sub(r"[*_`]", "", matches[0]).strip().lower()
    if raw_quad in CANONICAL_QUADRANTS and CANONICAL_QUADRANTS[raw_quad] != "Sin puntuar":
        return CANONICAL_QUADRANTS[raw_quad]
    raise ValueError(f"Cuadrante inválido '{matches[0]}' para la opción '{opcion_code}' en {a3_path}")


def validate_id(raw_id: str) -> tuple[bool, str]:
    cid = sanitize_cell(raw_id)
    cid_unescaped = cid.replace("\\|", "|").strip()
    if not cid_unescaped or re.match(r"^:?-{3,}:?$", cid_unescaped):
        return False, "[PARAR LÍNEA] El identificador (--id) no puede estar vacío."
    if cid_unescaped.lower() in RESERVED_HEADER_IDS:
        return False, f"[PARAR LÍNEA] El identificador '{raw_id}' no es válido (coincide con un encabezado de tabla)."
    return True, cid


def validate_component(raw: str, flag: str) -> tuple[bool, str]:
    cleaned = sanitize_cell(raw)
    cleaned_unescaped = cleaned.replace("\\|", "|").strip()
    if not cleaned_unescaped:
        return (
            False,
            f"[PARAR LÍNEA] El campo {flag} no puede estar vacío; debe indicar un componente técnico.",
        )
    if FORBIDDEN_WHO_PATTERNS.search(cleaned_unescaped):
        return (
            False,
            f"[PARAR LÍNEA] Violación Lean AgentOps: {flag} ('{cleaned_unescaped}') señala a un agente o persona. "
            "Usa siempre un componente técnico (ej. CLAUDE.md, KI System, MCP Config, Linter Hook, Skill Rule).",
        )
    return True, cleaned


def section_has_id(text: str, section_header_prefix: str, target_id_unescaped: str, id_col_idx: int) -> bool:
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            if in_section:
                break
            if section_header_prefix.lower() in line.lower():
                in_section = True
            continue
        if in_section and line.strip().startswith("|") and not re.search(r"\|\s*:?---", line):
            cols = split_row(line, unescape=True)
            if not cols or cols[0].lower() in {"id", "fecha"}:
                continue
            if len(cols) > id_col_idx and cols[id_col_idx] == target_id_unescaped:
                return True
    return False


def section_has_cuadrante_column(text: str) -> bool:
    in_sec1 = False
    for line in text.splitlines():
        if line.startswith("## "):
            if in_sec1:
                break
            if "## 1." in line:
                in_sec1 = True
        elif in_sec1 and line.strip().startswith("|"):
            cols = [c.lower() for c in split_row(line)]
            if cols and cols[0] == "id":
                return "cuadrante" in cols
    return False


def insert_row_in_section(text: str, section_header_prefix: str, new_row: str) -> str:
    lines = text.splitlines()
    in_section = False
    last_table_line_idx = -1

    for idx, line in enumerate(lines):
        if line.startswith("## "):
            if in_section:
                break
            if section_header_prefix.lower() in line.lower():
                in_section = True
        elif in_section and line.strip().startswith("|"):
            last_table_line_idx = idx

    if last_table_line_idx == -1:
        raise ValueError(f"No se encontró la tabla en la sección '{section_header_prefix}'")

    lines.insert(last_table_line_idx + 1, new_row)
    return "\n".join(lines) + "\n"


def update_timestamp(text: str, now_str: str) -> str:
    return re.sub(
        r"^- \*\*Última actualización:\*\* .*$",
        f"- **Última actualización:** {now_str}",
        text,
        flags=re.MULTILINE,
    )


def extract_board_limit(text: str, cli_limit: int | None) -> int:
    if cli_limit is not None:
        if cli_limit < 1:
            raise ValueError(
                f"El límite de compromisos abiertos (--limite) debe ser un entero de 1 o más (recibido: {cli_limit})."
            )
        return cli_limit
    m = re.search(r"^- \*\*Límite de compromisos abiertos:\*\*\s*(-?\d+)", text, flags=re.MULTILINE)
    if m and int(m.group(1)) >= 1:
        return int(m.group(1))
    return DEFAULT_MAX_OPEN


def parse_compromiso_row(cols: list[str], has_quad_col: bool) -> dict[str, str]:
    if has_quad_col and len(cols) >= 9:
        cid, comp, dueno, cuad, ini, c5h, c20h, c1sem, est = cols[:9]
        cuad_norm = CANONICAL_QUADRANTS.get(cuad.strip().lower(), cuad.strip() or "Sin puntuar")
        return {
            "id": cid,
            "compromiso": comp,
            "dueno": dueno,
            "cuadrante": cuad_norm,
            "inicio": ini,
            "c5h": c5h,
            "c20h": c20h,
            "c1sem": c1sem,
            "estado": est,
        }
    cid, comp, dueno, ini, c5h, c20h, c1sem, est = cols[:8]
    cuad_norm = "Sin puntuar"
    m_quad = re.match(
        r"^\[(Implementar|Desafío|Desafio|Posible|Eliminar|Sin puntuar)\]\s*(.*)$",
        est,
        flags=re.IGNORECASE,
    )
    if m_quad:
        cuad_norm = CANONICAL_QUADRANTS.get(m_quad.group(1).lower(), "Sin puntuar")
    return {
        "id": cid,
        "compromiso": comp,
        "dueno": dueno,
        "cuadrante": cuad_norm,
        "inicio": ini,
        "c5h": c5h,
        "c20h": c20h,
        "c1sem": c1sem,
        "estado": est,
    }


def is_closed_state(estado: str) -> bool:
    cleaned = re.sub(
        r"^\[(?:Implementar|Desafío|Desafio|Posible|Eliminar|Sin puntuar)\]\s*",
        "",
        estado.strip(),
        flags=re.IGNORECASE,
    )
    return bool(re.match(r"^CERRADO\b", cleaned))


@dataclass
class CliArgs:
    cmd: str
    func: Callable[[CliArgs], int]
    file: str = "KAIZEN.md"
    project: str = ""
    meta: str = "Calidad a la primera (FTY = 100%, 0 defectos) y CT <= Standard"
    limite: int | None = None
    date: str | None = None
    force: bool = False
    proceso: str = ""
    muda: str = ""
    poka_yoke: str = ""
    impacto: str | None = None
    id: str = ""
    flujo: str = ""
    presente: str = ""
    futuro: str = ""
    estado: str = ""
    compromiso: str = ""
    dueno: str = ""
    inicio: str | None = None
    a3: str | None = None
    opcion: str | None = None
    esfuerzo: str | None = None
    hansei: str = ""
    sostenido: str = ""
    now: str | None = None
    today: str | None = None


def cmd_init(args: CliArgs) -> int:
    target = Path(args.file)
    if target.exists() and target.is_dir():
        print(f"[PARAR LÍNEA] La ruta es un directorio, no un archivo: {target}", file=sys.stderr)
        return 1
    if not target.parent.exists() or not target.parent.is_dir():
        print(f"[PARAR LÍNEA] No existe la carpeta de destino: {target.parent}", file=sys.stderr)
        return 1
    if target.exists() and not args.force:
        print(f"[PARAR LÍNEA] El archivo ya existe: {target} (usa --force para sobrescribir)", file=sys.stderr)
        return 1

    limite_val = DEFAULT_MAX_OPEN if args.limite is None else args.limite
    if limite_val < 1:
        raise ValueError(
            f"El límite de compromisos abiertos (--limite) debe ser un entero de 1 o más (recibido: {limite_val})."
        )

    project = sanitize_cell(args.project)
    meta = sanitize_cell(args.meta)
    if not project:
        raise ValueError("El nombre del proyecto (--project) no puede estar vacío.")
    if not meta:
        raise ValueError("La meta (--meta) no puede estar vacía.")

    now_str = format_dt(parse_datetime(args.date))
    tpl = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{PROYECTO}}": project,
        "{{META}}": meta,
        "{{LIMITE_ABIERTOS}}": str(limite_val),
        "{{FECHA}}": now_str,
    }
    pattern = re.compile("|".join(re.escape(k) for k in replacements))
    content = pattern.sub(lambda m: replacements[m.group(0)], tpl)
    target.write_text(content, encoding="utf-8")
    print(f"[OK] Tablero Kaizen inicializado en: {target}")
    return 0


def cmd_add_kaizen(args: CliArgs) -> int:
    ok_proc, proc_or_err = validate_component(args.proceso, "--proceso")
    if not ok_proc:
        print(proc_or_err, file=sys.stderr)
        return 2
    target = Path(args.file)
    if not target.exists():
        print(f"[PARAR LÍNEA] No existe el archivo: {target}", file=sys.stderr)
        return 1
    text, eol = read_board(target)
    now_str = format_dt(parse_datetime(args.date))
    proceso = proc_or_err
    muda = sanitize_cell(args.muda)
    poka_yoke = sanitize_cell(args.poka_yoke)
    impacto = sanitize_cell(args.impacto or "")
    row = f"| {now_str} | {proceso} | {muda} | {poka_yoke} | {impacto} |"
    text = insert_row_in_section(text, "## 2.", row)
    text = update_timestamp(text, now_str)
    write_board(target, text, eol)
    print(f"[OK] Mejora Kaizen registrada en {target.name} (Proceso/Componente: {proceso})")
    return 0


def cmd_add_jugada(args: CliArgs) -> int:
    target = Path(args.file)
    if not target.exists():
        print(f"[PARAR LÍNEA] No existe el archivo: {target}", file=sys.stderr)
        return 1
    ok_id, jid_or_err = validate_id(args.id)
    if not ok_id:
        print(jid_or_err, file=sys.stderr)
        return 2
    jid = jid_or_err
    text, eol = read_board(target)
    if section_has_id(text, "## 3.", jid.replace("\\|", "|"), 1):
        print(f"[PARAR LÍNEA] Ya existe una jugada con el ID '{args.id}' en {target}", file=sys.stderr)
        return 2
    now_str = format_dt(parse_datetime(args.date))
    flujo = sanitize_cell(args.flujo)
    presente = sanitize_cell(args.presente)
    futuro = sanitize_cell(args.futuro)
    estado = sanitize_cell(args.estado)
    row = f"| {now_str} | {jid} | {flujo} | {presente} | {futuro} | {estado} |"
    text = insert_row_in_section(text, "## 3.", row)
    text = update_timestamp(text, now_str)
    write_board(target, text, eol)
    print(f"[OK] Jugada {jid} registrada en {target.name} para el flujo '{flujo}'")
    return 0


def resolve_compromiso_quadrant(args: CliArgs) -> tuple[bool, str]:
    has_a3 = bool(args.a3 or args.opcion)
    has_direct = bool(args.impacto or args.esfuerzo)

    if has_a3 and has_direct:
        return (
            False,
            "[PARAR LÍNEA] El cuadrante PICK se hereda del A3: no pases --impacto ni --esfuerzo cuando uses --a3 y --opcion.",
        )

    if has_a3:
        if not (args.a3 and args.opcion):
            return False, "[PARAR LÍNEA] Debes indicar tanto --a3 <ruta> como --opcion <código> para heredar el cuadrante."
        try:
            return True, read_pick_from_a3(Path(args.a3), args.opcion)
        except ValueError as exc:
            return False, f"[PARAR LÍNEA] {exc}"

    if has_direct:
        if not (args.impacto and args.esfuerzo):
            return False, "[PARAR LÍNEA] Debes indicar tanto --impacto (alto|bajo) como --esfuerzo (bajo|alto)."
        try:
            return True, calculate_pick_quadrant(args.impacto, args.esfuerzo)
        except ValueError as exc:
            return False, f"[PARAR LÍNEA] {exc}"

    return True, "Sin puntuar"


def cmd_add_compromiso(args: CliArgs) -> int:
    ok_dueno, dueno_or_err = validate_component(args.dueno, "--dueno")
    if not ok_dueno:
        print(dueno_or_err, file=sys.stderr)
        return 2
    target = Path(args.file)
    if not target.exists():
        print(f"[PARAR LÍNEA] No existe el archivo: {target}", file=sys.stderr)
        return 1

    ok_id, cid_or_err = validate_id(args.id)
    if not ok_id:
        print(cid_or_err, file=sys.stderr)
        return 2
    cid = cid_or_err

    ok, quad_or_err = resolve_compromiso_quadrant(args)
    if not ok:
        print(quad_or_err, file=sys.stderr)
        return 2
    cuadrante = quad_or_err

    text, eol = read_board(target)
    if section_has_id(text, "## 1.", cid.replace("\\|", "|"), 0):
        print(f"[PARAR LÍNEA] Ya existe un compromiso con el ID '{args.id}' en {target}", file=sys.stderr)
        return 2

    start = parse_datetime(args.inicio or args.date)
    now_str = format_dt(parse_datetime(args.date))
    c5h = format_dt(start + dt.timedelta(hours=5))
    c20h = format_dt(start + dt.timedelta(hours=20))
    c1sem = format_dt(start + dt.timedelta(days=7))
    start_str = format_dt(start)

    compromiso = sanitize_cell(args.compromiso)
    dueno = dueno_or_err
    estado = sanitize_cell(args.estado)

    has_quad_col = section_has_cuadrante_column(text)
    if has_quad_col:
        row = (
            f"| {cid} | {compromiso} | {dueno} | {cuadrante} | {start_str} "
            f"| {c5h} | {c20h} | {c1sem} | {estado} |"
        )
    else:
        estado_val = f"[{cuadrante}] {estado}" if (args.a3 or args.impacto) else estado
        row = (
            f"| {cid} | {compromiso} | {dueno} | {start_str} "
            f"| {c5h} | {c20h} | {c1sem} | {estado_val} |"
        )

    text = insert_row_in_section(text, "## 1.", row)
    text = update_timestamp(text, now_str)
    write_board(target, text, eol)
    print(f"[OK] Compromiso {cid} registrado (Cuadrante: {cuadrante}) -> Cortes: 5h={c5h}, 20h={c20h}, 1sem={c1sem}")
    return 0


def cmd_cerrar(args: CliArgs) -> int:
    target = Path(args.file)
    if not target.exists():
        print(f"[PARAR LÍNEA] No existe el archivo: {target}", file=sys.stderr)
        return 1

    ok_id, cid_or_err = validate_id(args.id)
    if not ok_id:
        print(cid_or_err, file=sys.stderr)
        return 2
    target_id = cid_or_err

    hansei_clean = sanitize_cell(args.hansei)
    if not hansei_clean:
        print("[PARAR LÍNEA] El campo --hansei no puede estar vacío.", file=sys.stderr)
        return 2

    sost_raw = args.sostenido.strip().lower()
    if sost_raw not in {"si", "sí", "no"}:
        print("[PARAR LÍNEA] --sostenido debe ser 'si' o 'no'.", file=sys.stderr)
        return 2
    sost_norm = "si" if sost_raw in {"si", "sí"} else "no"

    text, eol = read_board(target)
    expected_cols = 9 if section_has_cuadrante_column(text) else 8
    lines = text.splitlines()
    in_sec1 = False
    updated = False

    for idx, line in enumerate(lines):
        if line.startswith("## "):
            if in_sec1:
                break
            if "## 1." in line:
                in_sec1 = True
            continue
        if in_sec1 and line.strip().startswith("|") and not re.search(r"\|\s*:?---", line):
            cols = split_row(line)
            if not cols:
                continue
            if cols[0].lower() == "id":
                expected_cols = len(cols)
                continue
            if cols[0].replace("\\|", "|") == target_id.replace("\\|", "|"):
                if len(cols) != expected_cols:
                    print(
                        f"[PARAR LÍNEA] La fila del compromiso '{args.id}' tiene {len(cols)} celdas, "
                        f"se esperaban {expected_cols}; no se modifica {target}",
                        file=sys.stderr,
                    )
                    return 2
                prev_est = cols[-1]
                if is_closed_state(prev_est):
                    print(
                        f"[PARAR LÍNEA] El compromiso '{args.id}' ya está cerrado en {target}",
                        file=sys.stderr,
                    )
                    return 2
                m_quad = re.match(
                    r"^(\[(?:Implementar|Desafío|Desafio|Posible|Eliminar|Sin puntuar)\])\s*",
                    prev_est,
                    flags=re.IGNORECASE,
                )
                prefix = f"{m_quad.group(1)} " if m_quad else ""
                cols[-1] = f"{prefix}CERRADO (Sostenido: {sost_norm}; Hansei: {hansei_clean})"
                lines[idx] = "| " + " | ".join(cols) + " |"
                updated = True
                break

    if not updated:
        print(f"[PARAR LÍNEA] No se encontró el compromiso '{args.id}' en {target}", file=sys.stderr)
        return 1

    now_str = format_dt(parse_datetime(args.date))
    new_text = update_timestamp("\n".join(lines) + "\n", now_str)
    write_board(target, new_text, eol)
    hansei_display = hansei_clean.replace("\\|", "|")
    print(f"[OK] Compromiso {target_id.replace(r'\|', '|')} cerrado (Sostenido: {sost_norm} | Hansei: {hansei_display})")
    return 0


def cmd_status(args: CliArgs) -> int:
    target = Path(args.file)
    if not target.exists():
        print(f"[PARAR LÍNEA] No existe el archivo: {target}", file=sys.stderr)
        return 1

    eval_dt_raw = args.now or args.today
    now = parse_datetime(eval_dt_raw)
    now_str = format_dt(now)
    text, _ = read_board(target)
    has_quad_col = section_has_cuadrante_column(text)
    limite = extract_board_limit(text, args.limite)

    print(f"=== Estado Kaizen y Revisión de Ventanas 5h / 20h / 1 Semana ({target.name}) ===")
    print(f"Corte evaluado en el Gemba: {now_str}\n")

    lines = text.splitlines()
    sec = 0
    expected_sec1_cols = 9 if has_quad_col else 8
    sec1_row_num = 0
    comp_items: list[dict[str, str]] = []
    kaizen_count = 0
    jugada_count = 0

    for line in lines:
        if line.startswith("## 1."):
            sec = 1
            continue
        elif line.startswith("## 2."):
            sec = 2
            continue
        elif line.startswith("## 3."):
            sec = 3
            continue

        if line.strip().startswith("|") and not re.search(r"\|\s*:?---", line):
            cols = split_row(line, unescape=True)
            if not cols:
                continue
            if cols[0] in {"ID", "Fecha"}:
                if sec == 1 and cols[0] == "ID":
                    expected_sec1_cols = len(cols)
                continue
            if sec == 1:
                sec1_row_num += 1
                if len(cols) != expected_sec1_cols:
                    print(
                        f"[AVISO] fila {sec1_row_num} de la tabla 1 con {len(cols)} celdas, "
                        f"se esperaban {expected_sec1_cols}."
                    )
                    continue
                parsed_row = parse_compromiso_row(cols, has_quad_col)
                try:
                    parse_datetime(parsed_row["inicio"])
                except ValueError:
                    print(
                        f"[AVISO] Se omite la fila '{parsed_row['id']}' de la tabla 1 por fecha de inicio inválida '{parsed_row['inicio']}'."
                    )
                    continue
                comp_items.append(parsed_row)
            elif sec == 2:
                kaizen_count += 1
            elif sec == 3:
                jugada_count += 1

    open_items = [item for item in comp_items if not is_closed_state(item["estado"])]
    closed_items = [item for item in comp_items if is_closed_state(item["estado"])]
    open_items.sort(key=lambda item: PICK_ORDER.get(item["cuadrante"], 99))

    print(f"- Mejoras Kaizen / Poka-Yokes registrados: {kaizen_count}")
    print(f"- Jugadas (Estado Presente -> Estado Futuro): {jugada_count}")
    print(f"- Compromisos abiertos: {len(open_items)} (límite: {limite}) | Cerrados: {len(closed_items)}\n")

    if len(open_items) > limite:
        print(
            f"[AVISO] Hay {len(open_items)} compromisos abiertos: supera el límite de {limite}. "
            "Cierra o descarta pendientes antes de abrir más.\n"
        )

    if open_items:
        print("Detalle de Compromisos Abiertos (ordenados por cuadrante PICK, Ventanas 5h / 20h / 1sem):")
        for item in open_items:
            cid = item["id"]
            comp = item["compromiso"]
            dueno = item["dueno"]
            cuad = item["cuadrante"]
            ini = item["inicio"]
            c5h = item["c5h"]
            c20h = item["c20h"]
            c1sem = item["c1sem"]
            est = item["estado"]
            d_ini = parse_datetime(ini)
            elapsed_h = (now - d_ini).total_seconds() / 3600.0
            if elapsed_h < 5.0:
                etapa = f"Rumbo a 5h (faltan {5.0 - elapsed_h:.1f}h, corte {c5h})"
            elif elapsed_h < 20.0:
                etapa = f"VENTANA 5h CUMPLIDA ({elapsed_h:.1f}h) -> Rumbo a 20h ({c20h})"
            elif elapsed_h < 168.0:
                etapa = f"VENTANA 20h CUMPLIDA ({elapsed_h:.1f}h) -> Rumbo a 1sem ({c1sem})"
            else:
                etapa = f"CICLO 1 SEMANA CUMPLIDO ({elapsed_h:.1f}h desde inicio, corte 1sem fue {c1sem})"
            print(f"  * [{cid}] [{cuad}] {comp} ({dueno})")
            print(f"    Cronograma: {etapa}")
            print(f"    Estado en el Gemba: {est}")

    if closed_items:
        print("\nCompromisos Cerrados:")
        for item in closed_items:
            print(f"  * [{item['id']}] [{item['cuadrante']}] {item['compromiso']} -> {item['estado']}")

    return 0


USAGE = "Uso: kaizen-cli.py [-h] {init,add-kaizen,add-jugada,add-compromiso,add-ciclo,cerrar,status} ..."
HELP = f"""{USAGE}

Gestor determinista de tableros KAIZEN.md (TAS).

Subcomandos:
  init                      Inicializar un archivo KAIZEN.md.
  add-kaizen                Registrar mejora Kaizen y Poka-Yoke.
  add-jugada                Registrar jugada (Estado Presente -> Estado Futuro).
  add-compromiso (add-ciclo)
                            Registrar compromiso con cortes a 5h, 20h y 1 semana y cuadrante PICK.
  cerrar                    Cerrar un compromiso registrando reflexión Hansei y si se sostuvo.
  status                    Auditar estado, orden PICK, límite de abiertos y cortes de 5h/20h/1sem.

Argumentos:
  -h, --help                Muestra esta ayuda y termina.
"""

USAGE_INIT = (
    "Uso: kaizen-cli.py init --project <nombre> [--file <ruta>] [--meta <texto>] "
    "[--limite <n>] [--date <fecha>] [--force]"
)
HELP_INIT = f"""{USAGE_INIT}

Inicializa un archivo KAIZEN.md desde la plantilla.

Argumentos:
  --project <nombre>             Nombre del proyecto (obligatorio).
  --file <ruta>                  Ruta del tablero (por defecto: KAIZEN.md).
  --meta <texto>                 Meta Norte del tablero.
  --limite, --max-abiertos <n>   Límite de compromisos abiertos (por defecto: {DEFAULT_MAX_OPEN}).
  --date <fecha>                 Fecha/hora ISO (AAAA-MM-DD o AAAA-MM-DDTHH:MM).
  --force                        Sobrescribir el archivo si ya existe.
  -h, --help                     Muestra esta ayuda y termina.
"""

USAGE_ADD_KAIZEN = (
    "Uso: kaizen-cli.py add-kaizen --proceso <texto> --muda <texto> "
    "--poka-yoke <texto> --impacto <texto> [--file <ruta>] [--date <fecha>]"
)
HELP_ADD_KAIZEN = f"""{USAGE_ADD_KAIZEN}

Registra una mejora Kaizen y su Poka-Yoke en el tablero.

Argumentos:
  --proceso <texto>    Proceso o componente intervenido (obligatorio).
  --muda <texto>       Desperdicio (Muda) o defecto eliminado (obligatorio).
  --poka-yoke <texto>  Contramedida o Poka-Yoke instalado (obligatorio).
  --impacto <texto>    Impacto verificado en el Gemba (obligatorio).
  --file <ruta>        Ruta del tablero (por defecto: KAIZEN.md).
  --date <fecha>       Fecha/hora ISO (AAAA-MM-DD o AAAA-MM-DDTHH:MM).
  -h, --help           Muestra esta ayuda y termina.
"""

USAGE_ADD_JUGADA = (
    "Uso: kaizen-cli.py add-jugada --id <id> --flujo <texto> --presente <texto> "
    "--futuro <texto> [--file <ruta>] [--estado <texto>] [--date <fecha>]"
)
HELP_ADD_JUGADA = f"""{USAGE_ADD_JUGADA}

Registra una jugada de flujo de valor (Estado Presente -> Estado Futuro).

Argumentos:
  --id <id>          Identificador único de la jugada (obligatorio).
  --flujo <texto>    Flujo de valor (obligatorio).
  --presente <texto> Estado presente medido (obligatorio).
  --futuro <texto>   Estado futuro objetivo (obligatorio).
  --file <ruta>      Ruta del tablero (por defecto: KAIZEN.md).
  --estado <texto>   Estado de la jugada en el tablero.
  --date <fecha>     Fecha/hora ISO (AAAA-MM-DD o AAAA-MM-DDTHH:MM).
  -h, --help         Muestra esta ayuda y termina.
"""

USAGE_ADD_COMPROMISO = (
    "Uso: kaizen-cli.py add-compromiso --id <id> --compromiso <texto> --dueno <texto> "
    "[--file <ruta>] [--inicio <fecha>] [--date <fecha>] [--estado <texto>] "
    "[--a3 <ruta> --opcion <codigo> | --impacto <nivel> --esfuerzo <nivel>]"
)
HELP_ADD_COMPROMISO = f"""{USAGE_ADD_COMPROMISO}

Registra un compromiso con cortes a 5 horas, 20 horas y 1 semana y cuadrante PICK.

Argumentos:
  --id <id>                      Identificador único del compromiso (obligatorio).
  --compromiso <texto>           Acción concreta comprometida (obligatorio).
  --dueno <texto>                Dueño: proceso o componente (obligatorio).
  --file <ruta>                  Ruta del tablero (por defecto: KAIZEN.md).
  --inicio, --fecha-inicio <f>   Fecha/hora ISO de inicio de las ventanas.
  --date <fecha>                 Fecha/hora ISO de actualización del tablero.
  --estado <texto>               Estado inicial en el Gemba.
  --a3 <ruta>                    Ruta del A3 de origen para heredar el cuadrante PICK.
  --opcion <codigo>              Código de la opción en la tabla de sección 5 del A3 (ej. O-1).
  --impacto <nivel>              alto|bajo (solo cuando el compromiso no viene de un A3).
  --esfuerzo <nivel>             bajo|alto (solo cuando el compromiso no viene de un A3).
  -h, --help                     Muestra esta ayuda y termina.
"""

USAGE_CERRAR = (
    "Uso: kaizen-cli.py cerrar --id <id> --hansei <texto> --sostenido <si|no> "
    "[--file <ruta>] [--date <fecha>]"
)
HELP_CERRAR = f"""{USAGE_CERRAR}

Cierra un compromiso registrando la reflexión Hansei y si la mejora se sostuvo.

Argumentos:
  --id <id>            ID del compromiso a cerrar (obligatorio).
  --hansei <texto>     Reflexión: qué funcionó y por qué, qué no y por qué (obligatorio).
  --sostenido <si|no>  si|no: si la mejora se sostuvo en la siguiente ventana (obligatorio).
  --file <ruta>        Ruta del tablero (por defecto: KAIZEN.md).
  --date <fecha>       Fecha/hora ISO de cierre (AAAA-MM-DD o AAAA-MM-DDTHH:MM).
  -h, --help           Muestra esta ayuda y termina.
"""

USAGE_STATUS = (
    "Uso: kaizen-cli.py status [--file <ruta>] [--now <fecha>] [--today <fecha>] [--limite <n>]"
)
HELP_STATUS = f"""{USAGE_STATUS}

Audita el estado del tablero, el orden PICK, el límite de abiertos y las ventanas 5h/20h/1sem.

Argumentos:
  --file <ruta>                  Ruta del tablero (por defecto: KAIZEN.md).
  --now <fecha>                  Fecha/hora ISO de corte (ej. 2026-11-09T15:30).
  --today <fecha>                Alias de --now.
  --limite, --max-abiertos <n>   Límite de compromisos abiertos ({DEFAULT_MAX_OPEN} por defecto).
  -h, --help                     Muestra esta ayuda y termina.
"""


class UsageError(Exception):
    """Uso inválido de la línea de comandos: código de salida 2."""

    def __init__(self: UsageError, mensaje: str, usage: str = USAGE) -> None:
        super().__init__(mensaje)
        self.usage = usage


@dataclass(frozen=True)
class OptionSpec:
    flags: tuple[str, ...]
    dest: str
    required: bool = False
    default: str | int | bool | None = None
    is_flag: bool = False
    is_int: bool = False


@dataclass(frozen=True)
class SubcommandSpec:
    name: str
    usage: str
    help_text: str
    func: Callable[[CliArgs], int]
    options: tuple[OptionSpec, ...]


SUBCOMMANDS: dict[str, SubcommandSpec] = {}
for _spec in (
    SubcommandSpec(
        name="init",
        usage=USAGE_INIT,
        help_text=HELP_INIT,
        func=cmd_init,
        options=(
            OptionSpec(("--file",), "file", default="KAIZEN.md"),
            OptionSpec(("--project",), "project", required=True),
            OptionSpec(
                ("--meta",),
                "meta",
                default="Calidad a la primera (FTY = 100%, 0 defectos) y CT <= Standard",
            ),
            OptionSpec(("--limite", "--max-abiertos"), "limite", default=DEFAULT_MAX_OPEN, is_int=True),
            OptionSpec(("--date",), "date", default=None),
            OptionSpec(("--force",), "force", default=False, is_flag=True),
        ),
    ),
    SubcommandSpec(
        name="add-kaizen",
        usage=USAGE_ADD_KAIZEN,
        help_text=HELP_ADD_KAIZEN,
        func=cmd_add_kaizen,
        options=(
            OptionSpec(("--file",), "file", default="KAIZEN.md"),
            OptionSpec(("--proceso",), "proceso", required=True),
            OptionSpec(("--muda",), "muda", required=True),
            OptionSpec(("--poka-yoke",), "poka_yoke", required=True),
            OptionSpec(("--impacto",), "impacto", required=True),
            OptionSpec(("--date",), "date", default=None),
        ),
    ),
    SubcommandSpec(
        name="add-jugada",
        usage=USAGE_ADD_JUGADA,
        help_text=HELP_ADD_JUGADA,
        func=cmd_add_jugada,
        options=(
            OptionSpec(("--file",), "file", default="KAIZEN.md"),
            OptionSpec(("--id",), "id", required=True),
            OptionSpec(("--flujo",), "flujo", required=True),
            OptionSpec(("--presente",), "presente", required=True),
            OptionSpec(("--futuro",), "futuro", required=True),
            OptionSpec(("--estado",), "estado", default="En observación (Readiness Board)"),
            OptionSpec(("--date",), "date", default=None),
        ),
    ),
    SubcommandSpec(
        name="add-compromiso",
        usage=USAGE_ADD_COMPROMISO,
        help_text=HELP_ADD_COMPROMISO,
        func=cmd_add_compromiso,
        options=(
            OptionSpec(("--file",), "file", default="KAIZEN.md"),
            OptionSpec(("--id",), "id", required=True),
            OptionSpec(("--compromiso",), "compromiso", required=True),
            OptionSpec(("--dueno",), "dueno", required=True),
            OptionSpec(("--inicio", "--fecha-inicio"), "inicio", default=None),
            OptionSpec(("--date",), "date", default=None),
            OptionSpec(
                ("--estado",),
                "estado",
                default="0% ejecutado en el Gemba (pendiente primera ventana)",
            ),
            OptionSpec(("--a3",), "a3", default=None),
            OptionSpec(("--opcion",), "opcion", default=None),
            OptionSpec(("--impacto",), "impacto", default=None),
            OptionSpec(("--esfuerzo",), "esfuerzo", default=None),
        ),
    ),
    SubcommandSpec(
        name="cerrar",
        usage=USAGE_CERRAR,
        help_text=HELP_CERRAR,
        func=cmd_cerrar,
        options=(
            OptionSpec(("--file",), "file", default="KAIZEN.md"),
            OptionSpec(("--id",), "id", required=True),
            OptionSpec(("--hansei",), "hansei", required=True),
            OptionSpec(("--sostenido",), "sostenido", required=True),
            OptionSpec(("--date",), "date", default=None),
        ),
    ),
    SubcommandSpec(
        name="status",
        usage=USAGE_STATUS,
        help_text=HELP_STATUS,
        func=cmd_status,
        options=(
            OptionSpec(("--file",), "file", default="KAIZEN.md"),
            OptionSpec(("--now",), "now", default=None),
            OptionSpec(("--today",), "today", default=None),
            OptionSpec(("--limite", "--max-abiertos"), "limite", default=None, is_int=True),
        ),
    ),
):
    SUBCOMMANDS[_spec.name] = _spec
SUBCOMMANDS["add-ciclo"] = SUBCOMMANDS["add-compromiso"]


def parse_args(argv: list[str]) -> CliArgs | str:
    """Devuelve los argumentos validados, o el texto de ayuda si se pidió con -h/--help.

    Se lee a mano y no con argparse para que el uso, la ayuda y los errores salgan en español.
    """
    if not argv:
        raise UsageError(
            "falta el subcomando (usa: init, add-kaizen, add-jugada, add-compromiso, cerrar o status)",
            USAGE,
        )
    first = argv[0]
    if first in ("-h", "--help"):
        return HELP
    if first.startswith("-"):
        raise UsageError(f"opción desconocida: {first}", USAGE)
    spec = SUBCOMMANDS.get(first)
    if spec is None:
        raise UsageError(
            f"subcomando desconocido: '{first}' (usa: init, add-kaizen, add-jugada, add-compromiso, cerrar o status)",
            USAGE,
        )

    by_flag: dict[str, OptionSpec] = {}
    values: dict[str, str | int | bool | None] = {}
    for opt in spec.options:
        values[opt.dest] = opt.default
        for flag in opt.flags:
            by_flag[flag] = opt

    provided: set[str] = set()
    solo_posicionales = False
    pendientes = iter(argv[1:])
    for arg in pendientes:
        if solo_posicionales or arg == "-" or not arg.startswith("-"):
            raise UsageError(f"argumento no esperado: {arg}", spec.usage)
        if arg == "--":
            solo_posicionales = True
            continue
        if arg in ("-h", "--help"):
            return spec.help_text

        if "=" in arg:
            opt_flag, inline_val = arg.split("=", 1)
        else:
            opt_flag, inline_val = arg, None

        opt_spec = by_flag.get(opt_flag)
        if opt_spec is None:
            raise UsageError(f"opción desconocida: {opt_flag}", spec.usage)

        if opt_spec.is_flag:
            if inline_val is not None:
                raise UsageError(f"la opción {opt_flag} no lleva valor", spec.usage)
            values[opt_spec.dest] = True
            provided.add(opt_spec.dest)
            continue

        if inline_val is not None:
            raw_val = inline_val
        else:
            nxt = next(pendientes, None)
            if nxt in ("-h", "--help"):
                return spec.help_text
            if nxt is None or nxt in by_flag:
                raise UsageError(f"a la opción {opt_flag} le falta un valor", spec.usage)
            raw_val = nxt

        if opt_spec.is_int:
            try:
                values[opt_spec.dest] = int(raw_val)
            except ValueError:
                raise UsageError(
                    f"el valor de {opt_flag} debe ser un número entero: '{raw_val}'",
                    spec.usage,
                ) from None
        else:
            values[opt_spec.dest] = raw_val
        provided.add(opt_spec.dest)

    faltantes = [opt.flags[0] for opt in spec.options if opt.required and opt.dest not in provided]
    if faltantes:
        if len(faltantes) == 1:
            raise UsageError(f"falta el argumento obligatorio: {faltantes[0]}", spec.usage)
        raise UsageError(f"faltan los argumentos obligatorios: {', '.join(faltantes)}", spec.usage)

    parsed = CliArgs(cmd=first, func=spec.func)
    for k, v in values.items():
        setattr(parsed, k, v)
    return parsed


def main(argv: list[str] | None = None) -> int:
    try:
        parsed = parse_args(sys.argv[1:] if argv is None else argv)
    except UsageError as exc:
        print(f"{exc.usage}\nError: {exc}", file=sys.stderr)
        return 2
    if isinstance(parsed, str):
        print(parsed, end="")
        return 0
    try:
        return parsed.func(parsed)
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        msg = str(exc)
        if not msg.startswith("[PARAR LÍNEA]"):
            msg = f"[PARAR LÍNEA] {msg}"
        print(msg, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
