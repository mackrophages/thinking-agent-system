#!/usr/bin/env python3
"""
observer_cli.py: Herramienta determinista del Observador Silencioso Goldfish (Lean AgentOps).
Gestiona `.tas/` en un proyecto (durante una versión lee `.lean_observer/` si falta `.tas/`):
- `init`: Inicializa `.tas/`, tablero Markdown y HTML interactivo (bloquea directorios personales por Poka-Yoke) y migra `.lean_observer/` si no hay corrida abierta.
- `start-build`: Inicia una corrida (Build) explícita sin detener el reloj entre turnos.
- `close-build`: Cierra la corrida activa, analiza el transcript fuera de banda (si existe) y actualiza ambos tableros.
- `update-board`: Sincroniza `READINESS_BOARD.md` y `dashboard/index.html` escapando JSON/HTML contra XSS.
- `add-quality-issue` / `add-delivery-issue`: Registra contramedidas validando que `Who` sea un componente técnico, nunca una persona o agente.
- `analyze-transcript`: Calcula FTY, CT, CBR y PCE leyendo transcripts reales de Claude Code o Antigravity fuera de banda.
- `create-jugada`: Crea una Jugada VSM (Estado Presente -> Estado Futuro) vinculada al Readiness Board.
- `prepare-goldfish`: Prepara el paquete sin sesgo ("deriva primero, compara después") para despachar a un revisor remoto (`TAS_GOLDFISH_DESPACHO`) o indica el modo local.
"""

import datetime as dt
import json
import math
import os
import re
import shlex
import shutil
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SKILL_ROOT.parent.parent
RESOURCES_DIR = SKILL_ROOT / "resources"
SENSOR_SCRIPT = PLUGIN_ROOT / "scripts" / "goldfish_sensor.py"

sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
import goldfish_sensor as sensor  # noqa: E402

FORBIDDEN_WHO_PATTERNS = re.compile(
    # (?!\.\w): un nombre de archivo como CLAUDE.md es un componente, no el agente Claude.
    r"^(?:el\s+)?(?:agente|usuario|humano|persona|desarrollador|programador|operador|autor|claude|agy|elefante|goldfish)\b(?!\.\w)",
    re.IGNORECASE,
)

PDCA_SYMBOLS = {
    1: "◔ (`Plan`)",
    2: "◑ (`Do`)",
    3: "◕ (`Check`)",
    4: "● (`Act`)",
}

DEFAULT_COMPONENT_BY_CATEGORY = {
    "Missing Parts": ("Documentar índice de rutas y arquitectura en CLAUDE.md / KI", "CLAUDE.md / KI"),
    "Wrong Parts - Designed": ("Aplicar Poka-Yoke en el esquema JSON de la herramienta o MCP", "MCP / Tool Schema"),
    "Wrong Parts - Supplied": ("Purgar contexto obsoleto (5S Seiri) y enlazar especificación vigente", "KI System"),
    "Wrong Parts - Built": ("Añadir chequeo focalizado en la fuente antes de entregar", "Linter / Test Hook"),
}

DEFAULT_DELIVERY_BY_CATEGORY = {
    "CT > TT": ("Inventario (WIP)", "Acotar lecturas con offset/limit y cortar retrabajo al 3er fallo (Andon)", "agent-ops"),
    "CT > Standard": ("Movimiento", "Agrupar búsquedas independientes en lote paralelo y podar MCPs inactivos (5S)", "Skill Rule"),
}


def safe_json_for_html_script(data: dict[str, Any]) -> str:
    """
    Serializa un diccionario como JSON seguro para incrustar dentro de `<script>window.BOARD_DATA = ...;</script>`.
    Escapa `<`, `>`, `&` y comillas simples como secuencias Unicode (`\\u003c`, `\\u003e`, `\\u0026`, `\\u0027`)
    para impedir que un payload con `</script>` o etiquetas HTML rompa el bloque `<script>` (Poka-Yoke XSS).
    """
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    return (
        raw.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("'", "\\u0027")
    )


def escape_md_cell(val: Any) -> str:
    if val is None:
        return "-"
    return str(val).replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def escape_md_text(val: Any) -> str:
    """Como escape_md_cell, para una línea que no es celda de tabla: ahí la barra no lleva contrabarra."""
    return escape_md_cell(val).replace("\\|", "|")


def validate_who_component(who: str) -> tuple[bool, str]:
    cleaned = who.strip()
    if not cleaned:
        return False, "El campo 'Who' no puede estar vacío; debe indicar un componente técnico."
    if FORBIDDEN_WHO_PATTERNS.search(cleaned):
        return (
            False,
            f"Violación Lean AgentOps: 'Who' ('{cleaned}') señala a un agente o persona. "
            "Usa siempre un componente técnico (ej. CLAUDE.md, KI System, MCP Config, Linter Hook, Skill Rule).",
        )
    return True, cleaned


def analyze_transcript_file(transcript_path: Path) -> dict[str, Any]:
    """
    Lee un archivo transcript JSONL real (Claude Code o Antigravity) fuera de banda
    y calcula de forma honesta los indicadores FTY, CT, CBR y PCE.
    Distingue explícitamente conteos exactos de API (`exact_metrics`) y atribuciones derivadas (`derived_kpis`).
    """
    if not transcript_path.exists():
        return {"available": False, "reason": f"No existe el archivo: {transcript_path}"}

    platform = "unknown"
    api_input_tokens = 0
    api_cache_read_tokens = 0
    api_cache_creation_tokens = 0
    api_output_tokens = 0
    api_thinking_tokens = 0

    total_tool_calls = 0
    failed_tool_calls = 0
    retried_tool_calls = 0
    exploratory_calls = 0
    last_failed_tool: str | None = None

    tool_output_chars = 0
    va_chars = 0
    nnva_chars = 0
    muda_chars = 0

    timestamps: list[float] = []
    tool_id_to_name: dict[str, str] = {}

    va_tools = {"edit", "write", "multiedit", "notebookedit", "write_file", "edit_file", "replace_file_content"}
    exploratory_tools = {"grep", "glob", "find_by_name", "grep_search", "list_dir"}

    with transcript_path.open(encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue

            ts_str = obj.get("timestamp") or obj.get("created_at")
            if isinstance(ts_str, str):
                try:
                    ts_norm = ts_str.replace("Z", "+00:00")
                    timestamps.append(dt.datetime.fromisoformat(ts_norm).timestamp())
                except Exception:
                    pass

            rec_type = obj.get("type")

            # Formato 1: Claude Code transcript.jsonl
            if rec_type == "assistant" and isinstance(obj.get("message"), dict):
                platform = "claude-code"
                msg = obj["message"]
                usage = msg.get("usage") or {}
                if isinstance(usage, dict):
                    api_input_tokens += int(usage.get("input_tokens") or 0)
                    api_cache_read_tokens += int(usage.get("cache_read_input_tokens") or 0)
                    api_cache_creation_tokens += int(usage.get("cache_creation_input_tokens") or 0)
                    api_output_tokens += int(usage.get("output_tokens") or 0)
                    details = usage.get("output_tokens_details") or {}
                    if isinstance(details, dict):
                        api_thinking_tokens += int(details.get("thinking_tokens") or 0)

                content_list = msg.get("content") or []
                if isinstance(content_list, list):
                    for block in content_list:
                        if not isinstance(block, dict):
                            continue
                        b_type = block.get("type")
                        if b_type == "tool_use":
                            t_name = str(block.get("name") or "unknown")
                            t_id = str(block.get("id") or "")
                            if t_id:
                                tool_id_to_name[t_id] = t_name
                            total_tool_calls += 1
                            inp_str = json.dumps(block.get("input") or {}, ensure_ascii=False)
                            if t_name.lower() in va_tools:
                                va_chars += len(inp_str)
                            elif t_name.lower() in exploratory_tools:
                                exploratory_calls += 1
                                if exploratory_calls > 4:
                                    muda_chars += len(inp_str)
                                else:
                                    nnva_chars += len(inp_str)
                            else:
                                nnva_chars += len(inp_str)
                        elif b_type == "text":
                            va_chars += len(str(block.get("text") or ""))
                        elif b_type == "thinking":
                            nnva_chars += len(str(block.get("thinking") or ""))

            elif rec_type == "user" and isinstance(obj.get("message"), dict):
                content_list = obj["message"].get("content") or []
                if isinstance(content_list, list):
                    for block in content_list:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            t_id = str(block.get("tool_use_id") or "")
                            t_name = tool_id_to_name.get(t_id, "unknown")
                            c_str = json.dumps(block.get("content") or "", ensure_ascii=False)
                            tool_output_chars += len(c_str)
                            is_err = bool(block.get("is_error"))
                            if is_err:
                                failed_tool_calls += 1
                                last_failed_tool = t_name
                                muda_chars += len(c_str)
                            else:
                                if last_failed_tool == t_name:
                                    retried_tool_calls += 1
                                last_failed_tool = None
                                if len(c_str) > 20000:
                                    muda_chars += len(c_str) - 20000
                                    nnva_chars += 20000
                                else:
                                    nnva_chars += len(c_str)

            # Formato 2: Antigravity transcript.jsonl
            elif rec_type == "PLANNER_RESPONSE":
                platform = "antigravity"
                api_input_tokens += int(obj.get("input_tokens") or 0)
                api_cache_read_tokens += int(obj.get("cache_read_tokens") or 0)
                api_output_tokens += int(obj.get("output_tokens") or 0)
                thinking_str = str(obj.get("thinking") or "")
                content_str = str(obj.get("content") or "")
                nnva_chars += len(thinking_str)
                va_chars += len(content_str)

                t_calls = obj.get("tool_calls") or []
                if isinstance(t_calls, list):
                    for tc in t_calls:
                        if not isinstance(tc, dict):
                            continue
                        t_name = str(tc.get("name") or "unknown")
                        total_tool_calls += 1
                        args_str = json.dumps(tc.get("args") or {}, ensure_ascii=False)
                        if t_name.lower() in va_tools:
                            va_chars += len(args_str)
                        elif t_name.lower() in exploratory_tools:
                            exploratory_calls += 1
                            if exploratory_calls > 4:
                                muda_chars += len(args_str)
                            else:
                                nnva_chars += len(args_str)
                        else:
                            nnva_chars += len(args_str)

            elif rec_type in ("GENERIC", "ERROR_MESSAGE"):
                c_str = str(obj.get("content") or "")
                tool_output_chars += len(c_str)
                if obj.get("status") == "ERROR" or rec_type == "ERROR_MESSAGE":
                    failed_tool_calls += 1
                    muda_chars += len(c_str)
                else:
                    if len(c_str) > 20000:
                        muda_chars += len(c_str) - 20000
                        nnva_chars += 20000
                    else:
                        nnva_chars += len(c_str)

    fty_pct = (
        round(max(0.0, (1.0 - ((failed_tool_calls + retried_tool_calls) / total_tool_calls)) * 100.0), 1)
        if total_tool_calls > 0
        else 100.0
    )

    total_classified_chars = va_chars + nnva_chars + muda_chars
    if total_classified_chars > 0:
        tokens_va_est = max(1, round(va_chars / 4))
        tokens_nnva_est = round(nnva_chars / 4)
        tokens_muda_est = round(muda_chars / 4)
        pce_pct = round((tokens_va_est / (tokens_va_est + tokens_nnva_est + tokens_muda_est)) * 100.0, 1)
        tool_out_tokens_est = round(tool_output_chars / 4)
        cbr_ratio = round(tool_out_tokens_est / tokens_va_est, 2)
    else:
        tokens_va_est = 0
        tokens_nnva_est = 0
        tokens_muda_est = 0
        pce_pct = None
        cbr_ratio = None

    ct_from_transcript_min = None
    if len(timestamps) >= 2:
        ct_from_transcript_min = round(max(0.0, (max(timestamps) - min(timestamps)) / 60.0), 2)

    return {
        "available": True,
        "platform": platform,
        "transcript_path": str(transcript_path),
        "exact_metrics": {
            "source": "transcript_api_usage_and_tool_records",
            "tool_calls": total_tool_calls,
            "failed_tool_calls": failed_tool_calls,
            "retried_tool_calls": retried_tool_calls,
            "exploratory_calls": exploratory_calls,
            "fty_pct": fty_pct,
            "api_input_tokens": api_input_tokens,
            "api_cache_read_tokens": api_cache_read_tokens,
            "api_cache_creation_tokens": api_cache_creation_tokens,
            "api_output_tokens": api_output_tokens,
            "api_thinking_tokens": api_thinking_tokens,
            "tool_output_chars": tool_output_chars,
            "va_chars": va_chars,
            "ct_transcript_min": ct_from_transcript_min,
        },
        "derived_kpis": {
            "source": "heuristic_step_attribution_4chars_per_token",
            "note": "Los LLMs reportan usage por turno completo; el desglose VA/NNVA/Muda y CBR se estima sobre el volumen real de cada paso en el transcript (sin inventar datos).",
            "tokens_va_est": tokens_va_est,
            "tokens_nnva_est": tokens_nnva_est,
            "tokens_muda_est": tokens_muda_est,
            "pce_pct": pce_pct,
            "cbr_ratio": cbr_ratio,
        },
    }


def load_board_state(obs_dir: Path) -> dict[str, Any]:
    state_file = obs_dir / "board_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "projectTitle": f"Pre-Production Board: Readiness ({obs_dir.parent.name})",
        "observerMode": "Observador Silencioso (Elephant-Goldfish Pattern)",
        "standardMinutes": 5.0,
        "taktTimeMinutes": 7.0,
        "maxChartMinutes": 9.0,
        "maxQualityScale": 5,
        "qualityLog": [],
        "deliveryLog": [],
        "jugadas": [],
    }


def save_board_state(obs_dir: Path, board_state: dict[str, Any]) -> None:
    state_file = obs_dir / "board_state.json"
    state_file.write_text(json.dumps(board_state, ensure_ascii=False, indent=2), encoding="utf-8")


def build_board_data(obs_dir: Path) -> dict[str, Any]:
    board_state = load_board_state(obs_dir)
    standard_min = float(board_state.get("standardMinutes", 5.0))
    takt_min = float(board_state.get("taktTimeMinutes", 7.0))

    trace_file = obs_dir / "gemba_trace.jsonl"
    raw_records: list[dict[str, Any]] = []
    if trace_file.exists():
        for line in trace_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    raw_records.append(json.loads(line))
                except Exception:
                    pass

    # Tomar el bloque más reciente de hasta 12 corridas
    recent_records = raw_records[-12:]
    by_slot: dict[int, dict[str, Any]] = {}
    for idx, rec in enumerate(recent_records, 1):
        slot = int(rec.get("build") or idx)
        if not (1 <= slot <= 12):
            slot = idx
        by_slot[slot] = rec

    # Si hay una corrida activa en curso que aún no está reflejada en gemba_trace.jsonl, colocarla en el siguiente slot
    active_file = obs_dir / "active_build.json"
    active_slot: int | None = None
    if active_file.exists():
        try:
            act = json.loads(active_file.read_text(encoding="utf-8"))
            already_traced = (
                bool(recent_records)
                and act.get("start_time") is not None
                and recent_records[-1].get("start_time") == act.get("start_time")
            )
            if not already_traced:
                now_wall = time.time()
                now_mono = time.monotonic()
                el_sec, _, _ = sensor.compute_elapsed_seconds(act, now_wall, now_mono)
                next_slot = (len(recent_records) % 12) + 1
                active_slot = next_slot
                by_slot[next_slot] = {
                    "build": next_slot,
                    "status": "active",
                    "quality_issues": int(act.get("quality_issues", 0)),
                    "ct_min": round(el_sec / 60.0, 2),
                    "note": str(act.get("task") or "Corrida en observación"),
                    "issues_log": act.get("issues_log", []),
                }
        except Exception:
            pass

    # El número de problemas de una corrida cuenta los de la traza y los registrados a mano para ella,
    # sin contar dos veces el mismo (misma corrida y mismo texto).
    registrados: dict[int, set[str]] = {}
    for q in board_state.get("qualityLog", []):
        try:
            registrados.setdefault(int(q.get("build", 0)), set()).add(str(q.get("issue", "")))
        except (TypeError, ValueError):
            continue
    q_count: dict[int, int] = {}
    for slot_id, rec in by_slot.items():
        en_traza = {str(i.get("detail", "")) for i in rec.get("issues_log", [])}
        q_count[slot_id] = int(rec.get("quality_issues", 0)) + len(registrados.get(slot_id, set()) - en_traza)

    # Determinar Best Score entre las corridas ejecutadas con 0 defectos de calidad
    best_slot: int | None = None
    best_ct: float | None = None
    for slot_id, rec in by_slot.items():
        if rec.get("status") == "performed" and q_count[slot_id] == 0:
            ct_val = float(rec.get("ct_min", 0.0))
            if best_ct is None or ct_val < best_ct:
                best_ct = ct_val
                best_slot = slot_id

    builds_array: list[dict[str, Any]] = []
    for slot_id in range(1, 13):
        if slot_id in by_slot:
            rec = by_slot[slot_id]
            is_best = (slot_id == best_slot)
            builds_array.append(
                {
                    "id": slot_id,
                    "status": rec.get("status", "performed"),
                    "qualityIssues": q_count[slot_id],
                    "ctMinutes": float(rec.get("ct_min", 0.0)),
                    "note": "Best Score Achieved" if is_best else str(rec.get("note", "Single build performed")),
                    **({"isBest": True} if is_best else {}),
                }
            )
        else:
            builds_array.append(
                {
                    "id": slot_id,
                    "status": "ready",
                    "qualityIssues": None,
                    "ctMinutes": None,
                    "note": "Ready for single build",
                }
            )

    if best_slot is not None and best_ct is not None:
        best_score_obj = {
            "build": best_slot,
            "label": f"Build #{best_slot} (0 Issues | {best_ct} min)",
        }
    else:
        best_score_obj = {
            "build": 0,
            "label": "Pendiente (Meta: 0 Issues | CT <= Standard)",
        }

    # Construir qualityLog y deliveryLog combinando lo curado en board_state con lo detectado en gemba_trace
    quality_log: list[dict[str, Any]] = list(board_state.get("qualityLog", []))
    existing_q_keys = {(int(q.get("build", 0)), str(q.get("issue", ""))) for q in quality_log}

    delivery_log: list[dict[str, Any]] = list(board_state.get("deliveryLog", []))
    existing_d_builds = {int(d.get("build", 0)) for d in delivery_log}

    for slot_id in sorted(by_slot.keys()):
        rec = by_slot[slot_id]
        for issue_item in rec.get("issues_log", []):
            cat = str(issue_item.get("category", "Wrong Parts - Built"))
            detail = str(issue_item.get("detail", "Anomalía de herramienta"))
            key = (slot_id, detail)
            if key not in existing_q_keys:
                default_cm, default_who = DEFAULT_COMPONENT_BY_CATEGORY.get(
                    cat, ("Estandarizar validación y Poka-Yoke en el proceso", "Skill Rule")
                )
                quality_log.append(
                    {
                        "build": slot_id,
                        "issue": detail,
                        "category": cat,
                        "cm": default_cm,
                        "who": default_who,
                        "pdca": 1,
                    }
                )
                existing_q_keys.add(key)

        ct_val = float(rec.get("ct_min", 0.0))
        if ct_val > takt_min and slot_id not in existing_d_builds:
            d_cat = "CT > TT"
            default_muda, default_cm, default_who = DEFAULT_DELIVERY_BY_CATEGORY[d_cat]
            muda_val = str(rec.get("muda_Detected") or default_muda)
            delivery_log.append(
                {
                    "build": slot_id,
                    "issue": f"{ct_val} min ({d_cat}): Exceso de tiempo en corrida #{slot_id}",
                    "category": d_cat,
                    "muda": muda_val,
                    "cm": default_cm,
                    "who": default_who,
                    "pdca": 1,
                }
            )
            existing_d_builds.add(slot_id)

    max_observed_ct = max([float(b["ctMinutes"]) for b in builds_array if b["ctMinutes"] is not None] + [takt_min + 2.0])
    max_observed_q = max([int(b["qualityIssues"]) for b in builds_array if b["qualityIssues"] is not None] + [5])

    return {
        "projectTitle": str(board_state.get("projectTitle", "Pre-Production Board: Readiness (AgentOps)")),
        "observerMode": str(board_state.get("observerMode", "Observador Silencioso (Elephant-Goldfish Pattern)")),
        "bestScore": best_score_obj,
        "bestScoreGoal": f"0 Issues | CT <= {standard_min} min (techo acordado: {takt_min} min)",
        "standardMinutes": standard_min,
        "taktTimeMinutes": takt_min,
        "maxChartMinutes": round(max(float(board_state.get("maxChartMinutes", 9.0)), max_observed_ct), 1),
        "maxQualityScale": max(int(board_state.get("maxQualityScale", 5)), max_observed_q),
        "builds": builds_array,
        "qualityLog": quality_log,
        "deliveryLog": delivery_log,
    }


def render_markdown_board(board_data: dict[str, Any]) -> str:
    builds = board_data["builds"]
    state_cells = []
    q_cells = []
    ct_cells = []

    for b in builds:
        st = b["status"]
        if st == "performed":
            state_cells.append("🏆" if b.get("isBest") else "✅")
            q_cells.append(f"`{b['qualityIssues']}`")
            ct_cells.append(f"`{b['ctMinutes']}`")
        elif st == "active":
            state_cells.append("🔄")
            q_cells.append(f"`{b['qualityIssues']}`")
            ct_cells.append(f"`{b['ctMinutes']}`")
        else:
            state_cells.append("⬜")
            q_cells.append("`-`")
            ct_cells.append("`-`")

    q_rows = []
    for row in board_data["qualityLog"]:
        pdca_str = PDCA_SYMBOLS.get(int(row.get("pdca", 1)), "◔ (`Plan`)")
        q_rows.append(
            f"| **#{escape_md_cell(row['build'])}** | {escape_md_cell(row['issue'])} "
            f"| `{escape_md_cell(row['category'])}` | {escape_md_cell(row['cm'])} "
            f"| `{escape_md_cell(row['who'])}` | {pdca_str} |"
        )
    if not q_rows:
        q_rows.append("| `-` | Sin defectos de calidad registrados | `-` | `-` | `-` | `-` |")

    d_rows = []
    for row in board_data["deliveryLog"]:
        pdca_str = PDCA_SYMBOLS.get(int(row.get("pdca", 1)), "◔ (`Plan`)")
        d_rows.append(
            f"| **#{escape_md_cell(row['build'])}** | `{escape_md_cell(row['issue'])}` "
            f"| **{escape_md_cell(row['muda'])}** | {escape_md_cell(row['cm'])} "
            f"| `{escape_md_cell(row['who'])}` | {pdca_str} |"
        )
    if not d_rows:
        d_rows.append("| `-` | Sin causas especiales ni patrones de flujo registrados | `-` | `-` | `-` | `-` |")

    replacements = {
        "PROYECTO": escape_md_text(board_data["projectTitle"]),
        "BEST_SCORE": escape_md_text(board_data["bestScore"]["label"]),
        "STANDARD_MIN": str(board_data["standardMinutes"]),
        "TAKT_MIN": str(board_data["taktTimeMinutes"]),
    }

    template_text = (RESOURCES_DIR / "READINESS_BOARD.md").read_text(encoding="utf-8")
    out_lines: list[str] = []
    section = 0
    matched = {"estado": False, "issues": False, "ct": False, "q_table": False, "d_table": False}

    for line in template_text.splitlines():
        if line.startswith("## 2."):
            section = 2
        elif line.startswith("## 3."):
            section = 3

        if line.startswith("| **Estado** |"):
            out_lines.append(f"| **Estado** | {' | '.join(state_cells)} |")
            matched["estado"] = True
        elif line.startswith("| **Issues (Q)** |"):
            out_lines.append(f"| **Issues (Q)** | {' | '.join(q_cells)} |")
            matched["issues"] = True
        elif line.startswith("| **CT (min)** |"):
            out_lines.append(f"| **CT (min)** | {' | '.join(ct_cells)} |")
            matched["ct"] = True
        elif line.startswith("| :---: |") and section == 2 and not matched["q_table"]:
            out_lines.append(line)
            out_lines.extend(q_rows)
            matched["q_table"] = True
        elif line.startswith("| :---: |") and section == 3 and not matched["d_table"]:
            out_lines.append(line)
            out_lines.extend(d_rows)
            matched["d_table"] = True
        else:
            out_lines.append(
                re.sub(
                    r"\{\{(PROYECTO|BEST_SCORE|STANDARD_MIN|TAKT_MIN)\}\}",
                    lambda m: replacements[m.group(1)],
                    line,
                )
            )

    missing = [key for key, ok in matched.items() if not ok]
    if missing:
        raise ValueError(f"Plantilla READINESS_BOARD.md incompleta; faltan anclas: {', '.join(missing)}")

    return "\n".join(out_lines) + "\n"


def update_board_files(obs_dir: Path) -> tuple[Path, Path]:
    board_data = build_board_data(obs_dir)

    md_path = obs_dir / "READINESS_BOARD.md"
    md_path.write_text(render_markdown_board(board_data), encoding="utf-8")

    dash_dir = obs_dir / "dashboard"
    dash_dir.mkdir(parents=True, exist_ok=True)
    html_path = dash_dir / "index.html"

    base_html = (RESOURCES_DIR / "index.html").read_text(encoding="utf-8")
    safe_json = safe_json_for_html_script(board_data)

    replacement_block = f'<script id="board-data-script">\n      window.BOARD_DATA = {safe_json};\n    </script>'
    updated_html = re.sub(
        r'<script id="board-data-script">.*?</script>',
        lambda _: replacement_block,
        base_html,
        flags=re.DOTALL,
    )
    html_path.write_text(updated_html, encoding="utf-8")
    return md_path, html_path


def ensure_gitignore_entry(project_dir: Path) -> None:
    """Deja una sola línea `.tas/active_build.json`; sustituye en su sitio la de `.lean_observer/` si estaba."""
    gi = project_dir / ".gitignore"
    entry = f"{sensor.CARPETA_OBSERVADOR}/active_build.json"
    old_entry = f"{sensor.CARPETA_OBSERVADOR_VIEJA}/active_build.json"
    if not gi.exists():
        gi.write_text(f"{entry}\n", encoding="utf-8")
        return
    txt = gi.read_text(encoding="utf-8")
    lines = txt.splitlines()
    if old_entry in lines:
        pos = lines.index(old_entry)
        ya_estaba = entry in lines
        lines = [ln for ln in lines if ln != old_entry]
        if not ya_estaba:
            lines.insert(pos, entry)
        txt = "\n".join(lines) + "\n"
    elif entry in lines:
        return
    else:
        if not txt.endswith("\n"):
            txt += "\n"
        txt += f"{entry}\n"
    gi.write_text(txt, encoding="utf-8")


def is_personal_home_dir(raw_dir: Path, resolved_dir: Path) -> bool:
    """Indica si el directorio es el home de quien lo corre, /root o una carpeta directa de /home."""
    homes: set[Path] = {Path.home(), Path("/root")}
    for base in list(homes):
        try:
            homes.add(base.resolve())
        except OSError:
            pass
    abs_dir = Path(os.path.abspath(raw_dir))
    if abs_dir in homes or resolved_dir in homes:
        return True

    home_roots: set[Path] = {Path("/home")}
    try:
        home_roots.add(Path("/home").resolve())
    except OSError:
        pass
    for candidate in (abs_dir, resolved_dir):
        if candidate.parent in home_roots and candidate not in home_roots:
            return True
    return False


def cmd_init(args: SimpleNamespace) -> int:
    raw_dir = Path(args.project_dir).expanduser()
    project_dir = raw_dir.resolve()
    if is_personal_home_dir(raw_dir, project_dir) and not args.allow_home:
        print(
            f"[PARAR LÍNEA] Poka-Yoke activado: se bloqueó inicializar .tas/ directamente en "
            f"un directorio personal ({project_dir}) para no ensuciarlo. Usa un directorio de proyecto "
            f"(o pasa --allow-home si es intencional).",
            file=sys.stderr,
        )
        return 2
    if not project_dir.is_dir():
        print(
            f"[PARAR LÍNEA] No existe la carpeta del proyecto: {project_dir}. init no crea carpetas "
            "(una ruta mal escrita dejaría basura en el disco): créala primero o corrige la ruta.",
            file=sys.stderr,
        )
        return 2

    # Tabla de estados de init: la carpeta nueva manda; la vieja se migra solo sin corrida abierta.
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    old_name = sensor.CARPETA_OBSERVADOR_VIEJA
    new_name = sensor.CARPETA_OBSERVADOR
    old_dir = project_dir / old_name
    migrated = False
    if obs_dir.name == old_name:
        if (obs_dir / "active_build.json").exists():
            print(
                f"[PARAR LÍNEA] Hay una corrida abierta en {old_name}/ (active_build.json). "
                "Ciérrala con close-build y vuelve a correr init.",
                file=sys.stderr,
            )
            return 2
        obs_dir = obs_dir.rename(project_dir / new_name)
        migrated = True
    elif old_dir.is_dir():
        print(f"[AVISO] También existe {old_name}/: no se usa ni se toca. Revísala y bórrala a mano.", file=sys.stderr)
    (obs_dir / "dashboard").mkdir(parents=True, exist_ok=True)
    (obs_dir / "jugadas").mkdir(parents=True, exist_ok=True)

    # Copiar el sensor a la carpeta del observador para compatibilidad local (reemplaza la copia vieja al migrar)
    if SENSOR_SCRIPT.exists():
        dst_sensor = obs_dir / "goldfish_sensor.py"
        shutil.copyfile(SENSOR_SCRIPT, dst_sensor)
        dst_sensor.chmod(0o755)

    board_state = load_board_state(obs_dir)
    if migrated:
        for jugada in board_state.get("jugadas", []):
            ruta = jugada.get("file") if isinstance(jugada, dict) else None
            if isinstance(ruta, str) and ruta.startswith(f"{old_name}/"):
                jugada["file"] = f"{new_name}/" + ruta[len(old_name) + 1:]
    if args.project_name:
        board_state["projectTitle"] = f"Pre-Production Board: Readiness ({args.project_name})"
    board_state["standardMinutes"] = float(args.standard_min)
    board_state["taktTimeMinutes"] = float(args.takt_min)
    save_board_state(obs_dir, board_state)

    ensure_gitignore_entry(project_dir)
    md_path, html_path = update_board_files(obs_dir)
    if migrated:
        print(f"[OK] Carpeta del observador migrada de {old_name}/ a {new_name}/ en: {project_dir}")
    print(f"[OK] Observador Goldfish inicializado en: {obs_dir}")
    print(f"  - Tablero Markdown: {md_path}")
    print(f"  - Tablero HTML:     {html_path}")
    return 0


def cmd_start_build(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    if not obs_dir.is_dir():
        print(f"[PARAR LÍNEA] El proyecto no tiene .tas/ ({project_dir}). Ejecuta primero `init`.", file=sys.stderr)
        return 1

    active_path = obs_dir / "active_build.json"
    now_wall = time.time()
    now_mono = time.monotonic()

    if active_path.exists():
        try:
            prev = json.loads(active_path.read_text(encoding="utf-8"))
            if int(prev.get("tool_calls", 0)) > 0:
                board_state = load_board_state(obs_dir)
                sensor.close_active_build(
                    obs_dir,
                    now_wall,
                    now_mono,
                    float(board_state.get("standardMinutes", 5.0)),
                    float(board_state.get("taktTimeMinutes", 7.0)),
                )
        except Exception:
            pass

    state = sensor.default_active_state(now_wall, now_mono, task=args.task)
    active_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    update_board_files(obs_dir)
    print(f"[OK] Corrida iniciada en observación: '{args.task}'")
    return 0


def cmd_close_build(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    if not obs_dir.is_dir():
        print(f"[PARAR LÍNEA] No existe {obs_dir}", file=sys.stderr)
        return 1

    board_state = load_board_state(obs_dir)
    now_wall = time.time()
    now_mono = time.monotonic()
    rec = sensor.close_active_build(
        obs_dir,
        now_wall,
        now_mono,
        float(board_state.get("standardMinutes", 5.0)),
        float(board_state.get("taktTimeMinutes", 7.0)),
        note=args.note,
    )
    if rec is None:
        print("[AVISO] No había corrida activa en active_build.json.", file=sys.stderr)
        return 1

    # Si hay transcript_paths registrados, analizar el último fuera de banda y guardar KPIs en el último registro
    t_paths = rec.get("transcript_paths") or []
    if t_paths:
        last_tp = Path(t_paths[-1])
        if last_tp.exists():
            rec["transcript_kpis"] = analyze_transcript_file(last_tp)
            trace_file = obs_dir / "gemba_trace.jsonl"
            lines = trace_file.read_text(encoding="utf-8").splitlines()
            if lines:
                lines[-1] = json.dumps(rec, ensure_ascii=False)
                trace_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    md_path, html_path = update_board_files(obs_dir)
    print(
        f"[OK] Build #{rec['build']} cerrado -> CT={rec['ct_min']} min ({rec['delivery_flag']}), "
        f"Issues={rec['quality_issues']}, FTY={rec['fty_pct']}%"
    )
    print(f"  - Actualizado: {md_path} y {html_path}")
    return 0


def cmd_add_quality_issue(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    ok, who_msg = validate_who_component(args.who)
    if not ok:
        print(f"[PARAR LÍNEA] {who_msg}", file=sys.stderr)
        return 2

    board_state = load_board_state(obs_dir)
    board_state.setdefault("qualityLog", []).append(
        {
            "build": int(args.build),
            "issue": args.issue,
            "category": args.category,
            "cm": args.cm,
            "who": who_msg,
            "pdca": int(args.pdca),
        }
    )
    save_board_state(obs_dir, board_state)
    update_board_files(obs_dir)
    print(f"[OK] Problema de calidad registrado en Build #{args.build} (Who: {who_msg})")
    return 0


def cmd_add_delivery_issue(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    ok, who_msg = validate_who_component(args.who)
    if not ok:
        print(f"[PARAR LÍNEA] {who_msg}", file=sys.stderr)
        return 2

    board_state = load_board_state(obs_dir)
    board_state.setdefault("deliveryLog", []).append(
        {
            "build": int(args.build),
            "issue": args.issue,
            "category": args.category,
            "muda": args.muda,
            "cm": args.cm,
            "who": who_msg,
            "pdca": int(args.pdca),
        }
    )
    save_board_state(obs_dir, board_state)
    update_board_files(obs_dir)
    print(f"[OK] Desviación de entrega registrada en Build #{args.build} (Who: {who_msg})")
    return 0


def cmd_update_board(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    if not obs_dir.is_dir():
        print(f"[PARAR LÍNEA] No existe {obs_dir}", file=sys.stderr)
        return 1
    md_path, html_path = update_board_files(obs_dir)
    print(f"[OK] Tableros sincronizados:\n  - {md_path}\n  - {html_path}")
    return 0


def cmd_analyze_transcript(args: SimpleNamespace) -> int:
    tp = Path(args.transcript).resolve()
    res = analyze_transcript_file(tp)
    if args.format == "json":
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res.get("available") else 1

    if not res.get("available"):
        print(f"[PARAR LÍNEA] {res.get('reason')}", file=sys.stderr)
        return 1

    ex = res["exact_metrics"]
    der = res["derived_kpis"]
    print(f"=== Análisis Out-of-Band de Transcript ({res['platform']}) ===")
    print(f"Archivo: {res['transcript_path']}")
    print("\n1. Métricas Exactas (Fuente: registros de herramientas y API usage):")
    print(f"  - Llamadas a herramientas: {ex['tool_calls']} (Fallidas: {ex['failed_tool_calls']}, Reintentos: {ex['retried_tool_calls']})")
    print(f"  - First-Time Yield (FTY):  {ex['fty_pct']}%")
    print(f"  - Búsquedas exploratorias: {ex['exploratory_calls']}")
    print(f"  - Tokens API Input/Output: in={ex['api_input_tokens']} | cache_read={ex['api_cache_read_tokens']} | cache_create={ex['api_cache_creation_tokens']} | out={ex['api_output_tokens']}")
    if ex["ct_transcript_min"] is not None:
        print(f"  - Duración en transcript:  {ex['ct_transcript_min']} min")
    print("\n2. Indicadores Derivados (Atribución proporcional por tipo de paso):")
    print(f"  - Tokens estimados (VA / NNVA / Muda): {der['tokens_va_est']} / {der['tokens_nnva_est']} / {der['tokens_muda_est']}")
    print(f"  - Process Cycle Efficiency (PCE):      {der['pce_pct']}%")
    print(f"  - Context Bloat Ratio (CBR):           {der['cbr_ratio']}")
    return 0


def cmd_create_jugada(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    if not obs_dir.is_dir():
        print(f"[PARAR LÍNEA] Primero inicializa .tas/ con `init` en {project_dir}", file=sys.stderr)
        return 1

    board_state = load_board_state(obs_dir)
    tpl = (RESOURCES_DIR / "plantilla-jugada-vsm.md").read_text(encoding="utf-8")
    slug = re.sub(r"[^a-z0-9]+", "-", args.flujo.lower()).strip("-") or "flujo"
    jugada_file = obs_dir / "jugadas" / f"{args.id}-{slug}.md"

    now_str = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    content = (
        tpl.replace("{{ID}}", args.id)
        .replace("{{FLUJO}}", args.flujo)
        .replace("{{FECHA}}", now_str)
        .replace("{{PROYECTO}}", project_dir.name)
        .replace("{{STANDARD_MIN}}", str(board_state.get("standardMinutes", 5.0)))
        .replace("{{TAKT_MIN}}", str(board_state.get("taktTimeMinutes", 7.0)))
        .replace("{{PASO_PRESENTE_1}}", args.paso_presente_1)
        .replace("{{PASO_PRESENTE_2}}", args.paso_presente_2)
        .replace("{{CT_PRESENTE}}", args.ct_presente)
        .replace("{{FTY_PRESENTE}}", args.fty_presente)
        .replace("{{MUDA_PRESENTE}}", args.muda_presente)
        .replace("{{PROBLEMA_1}}", args.problema)
        .replace("{{POKA_YOKE_1}}", args.poka_yoke)
        .replace("{{PASO_FUTURO_1}}", args.paso_futuro_1)
        .replace("{{PASO_FUTURO_2}}", args.paso_futuro_2)
    )
    jugada_file.parent.mkdir(parents=True, exist_ok=True)
    jugada_file.write_text(content, encoding="utf-8")

    board_state.setdefault("jugadas", []).append(
        {
            "id": args.id,
            "flujo": args.flujo,
            "file": str(jugada_file.relative_to(project_dir)),
            "created_at": now_str,
        }
    )
    save_board_state(obs_dir, board_state)
    print(f"[OK] Jugada VSM creada en: {jugada_file}")
    return 0


def resolve_goldfish_artefacto(obs_dir: Path, cli_artefacto: str | None) -> str:
    if cli_artefacto is not None and cli_artefacto.strip():
        return cli_artefacto.strip()
    env_artefacto = sensor.leer_env("TAS_GOLDFISH_ARTEFACTO", "LEAN_GOLDFISH_ARTEFACTO")
    if env_artefacto:
        return env_artefacto
    return str(obs_dir / "goldfish-board.json")


def cmd_prepare_goldfish(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    trace_file = obs_dir / "gemba_trace.jsonl"
    if not trace_file.exists():
        print(f"[PARAR LÍNEA] No existe traza para observar en: {trace_file}", file=sys.stderr)
        return 1

    despacho_tpl = sensor.leer_env("TAS_GOLDFISH_DESPACHO", "LEAN_GOLDFISH_DESPACHO")
    encargo_path = (
        Path(args.output_encargo).resolve()
        if args.output_encargo
        else (obs_dir / "encargo_goldfish.md")
    )
    artefacto = resolve_goldfish_artefacto(obs_dir, getattr(args, "artefacto", None))

    comando_remoto: str | None = None
    if despacho_tpl:
        try:
            comando_remoto = despacho_tpl.format(
                encargo=shlex.quote(str(encargo_path)),
                artefacto=shlex.quote(artefacto),
            )
        except (KeyError, ValueError, IndexError) as exc:
            print(
                f"[PARAR LÍNEA] Plantilla inválida en TAS_GOLDFISH_DESPACHO "
                f"(usa {{encargo}} y {{artefacto}}): {exc}",
                file=sys.stderr,
            )
            return 2

    trace_txt = trace_file.read_text(encoding="utf-8").strip()

    encargo_content = f"""# Encargo de Observación (Observador Silencioso Goldfish - Círculo de Ohno)

Actúas como el **Observador Silencioso (Goldfish)** bajo el modelo Lean AgentOps.
Regla crítica de decorrelación: **deriva primero, compara después**. Recibes únicamente la traza cruda de ejecución sin auto-evaluaciones ni conclusiones del agente ejecutor (Elefante).

## Reglas obligatorias de observación
1. **Las métricas nunca castigan al agente:** Tu análisis audita el proceso, las herramientas y la documentación, jamás al individuo o al agente.
2. **`Who` es siempre un componente técnico:** En cada fila de `qualityLog` y `deliveryLog`, el campo `who` debe ser un componente (`CLAUDE.md`, `KI System`, `MCP Config`, `Linter Hook`, `Skill Rule`, `Test Runner`), nunca una persona ni el agente.
3. **Clasificación de Calidad (`Goal = 0`):** `Wrong Parts - Supplied`, `Wrong Parts - Built`, `Wrong Parts - Designed`, `Missing Parts`.
4. **Clasificación de Entrega (`Measured CT w/o stopping clock`):** `CT > TT` o `CT > Standard`, indicando el tipo de Muda (`Inventario (WIP)`, `Movimiento`, `Sobreprocesamiento`, `Espera`, `Retrabajo`).
5. **Proteger el NNVA de calidad y seguridad:** Prohibido recomendar recortar validaciones, tests o controles de seguridad para ahorrar tokens.

## Traza cruda registrada (`{obs_dir.name}/gemba_trace.jsonl`)
```jsonl
{trace_txt}
```

## Salida requerida
Escribe en `{artefacto}` un objeto JSON válido con las listas `qualityLog` y `deliveryLog` propuestas para actualizar el Pre-Production Readiness Board.
Quien te despachó importa ese archivo con `observer_cli.py import-goldfish --project-dir <proyecto> --artefacto {artefacto}`, que valida cada fila con las mismas reglas que `add-quality-issue` y `add-delivery-issue` (build entero, `who` componente, categoría y `pdca` 1 a 4) y rechaza las que no cumplan.
"""
    encargo_path.write_text(encargo_content, encoding="utf-8")

    print(f"[OK] Encargo Goldfish sin sesgo generado en: {encargo_path}")
    if comando_remoto is not None:
        print(
            "\nComando para despachar al revisor remoto:\n"
            f"  {comando_remoto}"
        )
    else:
        print(
            "\n[MODO LOCAL / FALLBACK] TAS_GOLDFISH_DESPACHO no está configurada. "
            "Usa el subagente local sin contexto `observador-goldfish` o `observer_cli.py update-board`."
        )
    return 0


def _opcion_choices(subcomando: str, dest: str) -> tuple[Any, ...]:
    for spec in SUBCOMMANDS_BY_NAME[subcomando].options:
        if spec.dest == dest:
            return spec.choices or ()
    return ()


def validar_fila_goldfish(fila: Any, tipo: str) -> tuple[dict[str, Any] | None, str]:
    """Valida una fila del revisor con las reglas de add-quality-issue / add-delivery-issue."""
    if not isinstance(fila, dict):
        return None, "la fila no es un objeto JSON"
    campos = ("build", "issue", "category", "cm", "who") + (("muda",) if tipo == "delivery" else ())
    faltan = [c for c in campos if c not in fila]
    if faltan:
        return None, "faltan campos: " + ", ".join(faltan)
    build = fila["build"]
    if isinstance(build, bool) or not isinstance(build, int) or build < 1:
        return None, "build debe ser un entero desde 1"
    for c in campos[1:]:
        if not isinstance(fila[c], str) or not fila[c].strip():
            return None, f"{c} debe ser un texto no vacío"
    categorias = _opcion_choices("add-quality-issue" if tipo == "quality" else "add-delivery-issue", "category")
    if fila["category"] not in categorias:
        return None, f"categoría inválida '{fila['category']}' (válidas: {', '.join(categorias)})"
    pdca = fila.get("pdca", 1)
    if isinstance(pdca, bool) or pdca not in (1, 2, 3, 4):
        return None, f"PDCA inválido '{pdca}' (válidos: 1, 2, 3, 4)"
    ok, who_msg = validate_who_component(fila["who"])
    if not ok:
        return None, who_msg
    limpia: dict[str, Any] = {
        "build": build,
        "issue": fila["issue"],
        "category": fila["category"],
    }
    if tipo == "delivery":
        limpia["muda"] = fila["muda"]
    limpia.update({"cm": fila["cm"], "who": who_msg, "pdca": int(pdca)})
    return limpia, ""


def cmd_import_goldfish(args: SimpleNamespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    obs_dir = sensor.resolver_carpeta_observador(project_dir)
    if not obs_dir.is_dir():
        print(f"[PARAR LÍNEA] No existe {obs_dir}. Ejecuta primero `init`.", file=sys.stderr)
        return 1
    artefacto = Path(args.artefacto).expanduser()
    if not artefacto.exists():
        print(f"[AVISO] El revisor aún no escribió {artefacto}: no hay nada que importar.")
        return 0
    try:
        datos = json.loads(artefacto.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[PARAR LÍNEA] No se pudo leer un JSON en {artefacto}: {exc}", file=sys.stderr)
        return 2
    listas = {k: datos.get(k) for k in ("qualityLog", "deliveryLog")} if isinstance(datos, dict) else {}
    presentes = {k: v for k, v in listas.items() if v is not None}
    if not presentes or not all(isinstance(v, list) for v in presentes.values()):
        print(
            f"[PARAR LÍNEA] {artefacto} debe ser un objeto JSON con las listas `qualityLog` y/o `deliveryLog`.",
            file=sys.stderr,
        )
        return 2

    board_state = load_board_state(obs_dir)
    resumen: list[str] = []
    rechazos: list[str] = []
    for clave, tipo, etiqueta in (("qualityLog", "quality", "calidad"), ("deliveryLog", "delivery", "entrega")):
        log = board_state.setdefault(clave, [])
        vistas = {(int(f.get("build", 0)), str(f.get("issue", ""))) for f in log}
        nuevas = repetidas = 0
        for pos, fila in enumerate(presentes.get(clave, []), 1):
            limpia, motivo = validar_fila_goldfish(fila, tipo)
            if limpia is None:
                rechazos.append(f"  - {clave}[{pos}] rechazada: {motivo}")
                continue
            llave = (limpia["build"], limpia["issue"])
            if llave in vistas:
                repetidas += 1
                continue
            vistas.add(llave)
            log.append(limpia)
            nuevas += 1
        resumen.append(f"{nuevas} de {etiqueta} ({repetidas} ya estaban)")

    save_board_state(obs_dir, board_state)
    update_board_files(obs_dir)
    print("[OK] Importado del revisor: " + "; ".join(resumen) + f"; {len(rechazos)} rechazadas.")
    for linea in rechazos:
        print(linea)
    return 0


USAGE = "Uso: observer_cli.py <subcomando> [opciones]"


@dataclass(frozen=True)
class OptionSpec:
    flag: str
    dest: str
    help: str
    metavar: str = "<valor>"
    kind: str = "str"
    default: Any = None
    required: bool = False
    choices: tuple[Any, ...] | None = None


@dataclass(frozen=True)
class SubcommandSpec:
    name: str
    summary: str
    func: Callable[[SimpleNamespace], int]
    options: tuple[OptionSpec, ...]

    @property
    def usage(self) -> str:
        partes: list[str] = [f"Uso: observer_cli.py {self.name}"]
        opcionales: list[str] = []
        for opt in self.options:
            etiqueta = opt.flag if opt.kind == "flag" else f"{opt.flag} {opt.metavar}"
            if opt.required:
                partes.append(etiqueta)
            else:
                opcionales.append(f"[{etiqueta}]")
        if len(opcionales) > 3:
            partes.append("[opciones]")
        else:
            partes.extend(opcionales)
        return " ".join(partes)


SUBCOMMANDS: tuple[SubcommandSpec, ...] = (
    SubcommandSpec(
        name="init",
        summary="Inicializar .tas/ y tableros en un proyecto",
        func=cmd_init,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--project-name", "project_name", "Nombre visible del proyecto en el tablero.", "<nombre>", default=None),
            OptionSpec("--standard-min", "standard_min", "Referencia de tiempo de ciclo en minutos (5.0 por defecto).", "<min>", kind="float", default=5.0),
            OptionSpec("--takt-min", "takt_min", "Techo acordado de tiempo de ciclo en minutos (7.0 por defecto).", "<min>", kind="float", default=7.0),
            OptionSpec("--allow-home", "allow_home", "Permitir inicializar en un directorio personal.", kind="flag", default=False),
        ),
    ),
    SubcommandSpec(
        name="start-build",
        summary="Iniciar una corrida (Build) explícita sin detener el reloj",
        func=cmd_start_build,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--task", "task", "Descripción de la unidad de trabajo o encargo", "<texto>", required=True),
        ),
    ),
    SubcommandSpec(
        name="close-build",
        summary="Cerrar la corrida activa y actualizar tableros",
        func=cmd_close_build,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--note", "note", "Nota opcional de cierre.", "<texto>", default=""),
        ),
    ),
    SubcommandSpec(
        name="add-quality-issue",
        summary="Registrar anomalía de calidad y contramedida",
        func=cmd_add_quality_issue,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--build", "build", "Número entero de corrida (Build)", "<n>", kind="int", required=True),
            OptionSpec("--issue", "issue", "Descripción de la anomalía observada", "<texto>", required=True),
            OptionSpec(
                "--category",
                "category",
                "Categoría de calidad",
                "<cat>",
                required=True,
                choices=("Wrong Parts - Supplied", "Wrong Parts - Built", "Wrong Parts - Designed", "Missing Parts"),
            ),
            OptionSpec("--cm", "cm", "Contramedida técnica propuesta", "<texto>", required=True),
            OptionSpec("--who", "who", "Componente técnico responsable (nunca una persona o agente)", "<componente>", required=True),
            OptionSpec("--pdca", "pdca", "Etapa PDCA de la contramedida (1 por defecto).", "<1..4>", kind="int", default=1, choices=(1, 2, 3, 4)),
        ),
    ),
    SubcommandSpec(
        name="add-delivery-issue",
        summary="Registrar desviación de flujo (CT) y contramedida",
        func=cmd_add_delivery_issue,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--build", "build", "Número entero de corrida (Build)", "<n>", kind="int", required=True),
            OptionSpec("--issue", "issue", "Descripción de la desviación o patrón de flujo", "<texto>", required=True),
            OptionSpec("--category", "category", "Categoría de entrega", "<cat>", required=True, choices=("CT > TT", "CT > Standard")),
            OptionSpec("--muda", "muda", "Tipo de desperdicio (Muda) identificado", "<tipo>", required=True),
            OptionSpec("--cm", "cm", "Contramedida técnica propuesta", "<texto>", required=True),
            OptionSpec("--who", "who", "Componente técnico responsable (nunca una persona o agente)", "<componente>", required=True),
            OptionSpec("--pdca", "pdca", "Etapa PDCA de la contramedida (1 por defecto).", "<1..4>", kind="int", default=1, choices=(1, 2, 3, 4)),
        ),
    ),
    SubcommandSpec(
        name="update-board",
        summary="Sincronizar READINESS_BOARD.md y dashboard/index.html",
        func=cmd_update_board,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
        ),
    ),
    SubcommandSpec(
        name="analyze-transcript",
        summary="Analizar transcript JSONL fuera de banda (FTY, CT, CBR, PCE)",
        func=cmd_analyze_transcript,
        options=(
            OptionSpec("--transcript", "transcript", "Ruta al archivo JSONL de transcript", "<ruta>", required=True),
            OptionSpec("--format", "format", "Formato de salida (markdown por defecto).", "<formato>", default="markdown", choices=("markdown", "json")),
        ),
    ),
    SubcommandSpec(
        name="create-jugada",
        summary="Crear una Jugada VSM (Estado Presente -> Estado Futuro)",
        func=cmd_create_jugada,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--id", "id", "Identificador de la jugada (ej. JUG-01)", "<id>", required=True),
            OptionSpec("--flujo", "flujo", "Nombre del flujo observado", "<texto>", required=True),
            OptionSpec("--paso-presente-1", "paso_presente_1", "Primer paso del estado presente.", "<texto>", default="Exploración secuencial sin índice previo"),
            OptionSpec("--paso-presente-2", "paso_presente_2", "Segundo paso del estado presente.", "<texto>", default="Edición y validación manual al final"),
            OptionSpec("--ct-presente", "ct_presente", "Tiempo de ciclo del estado presente.", "<texto>", default="7.5 min (CT > TT)"),
            OptionSpec("--fty-presente", "fty_presente", "FTY del estado presente.", "<texto>", default="75%"),
            OptionSpec("--muda-presente", "muda_presente", "Muda principal del estado presente.", "<texto>", default="Inventario y Movimiento en exploración"),
            OptionSpec("--problema", "problema", "Problema observado en el proceso.", "<texto>", default="Falta de índice arquitectónico y lecturas sin acotar"),
            OptionSpec("--poka-yoke", "poka_yoke", "Poka-Yoke o contramedida aplicada.", "<texto>", default="Índice en CLAUDE.md + lecturas acotadas en lote paralelo"),
            OptionSpec("--paso-futuro-1", "paso_futuro_1", "Primer paso del estado futuro.", "<texto>", default="Lectura quirúrgica en paralelo guiada por índice"),
            OptionSpec("--paso-futuro-2", "paso_futuro_2", "Segundo paso del estado futuro.", "<texto>", default="Edición con inspección focalizada en la fuente"),
        ),
    ),
    SubcommandSpec(
        name="prepare-goldfish",
        summary="Generar encargo Goldfish sin sesgo para revisor remoto o local",
        func=cmd_prepare_goldfish,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--output-encargo", "output_encargo", "Ruta opcional del archivo Markdown de encargo.", "<ruta>", default=None),
            OptionSpec("--artefacto", "artefacto", "Ruta donde el revisor escribirá su JSON (manda sobre TAS_GOLDFISH_ARTEFACTO).", "<ruta>", default=None),
        ),
    ),
    SubcommandSpec(
        name="import-goldfish",
        summary="Importar al tablero el JSON que escribió el revisor remoto",
        func=cmd_import_goldfish,
        options=(
            OptionSpec("--project-dir", "project_dir", "Directorio del proyecto.", "<ruta>", default="."),
            OptionSpec("--artefacto", "artefacto", "Ruta del JSON con qualityLog y deliveryLog.", "<json>", required=True),
        ),
    ),
)

SUBCOMMANDS_BY_NAME: dict[str, SubcommandSpec] = {spec.name: spec for spec in SUBCOMMANDS}


def format_general_help() -> str:
    lineas_sub = "\n".join(f"  {spec.name:<22}  {spec.summary}." for spec in SUBCOMMANDS)
    return (
        f"{USAGE}\n\n"
        "Herramienta determinista del Observador Silencioso Goldfish (Lean AgentOps).\n\n"
        f"Subcomandos:\n{lineas_sub}\n\n"
        "Opciones:\n"
        "  -h, --help              Muestra esta ayuda y termina.\n"
    )


def format_subcommand_help(spec: SubcommandSpec) -> str:
    entradas: list[tuple[str, str]] = []
    for opt in spec.options:
        izq = opt.flag if opt.kind == "flag" else f"{opt.flag} {opt.metavar}"
        desc = opt.help.rstrip(".")
        if opt.required:
            desc += " (obligatorio)."
        else:
            desc += "."
        if opt.choices is not None:
            permitidos = ", ".join(repr(c) for c in opt.choices)
            desc += f" Valores permitidos: {permitidos}."
        entradas.append((izq, desc))
    entradas.append(("-h, --help", "Muestra esta ayuda y termina."))
    ancho = max(22, *(len(izq) for izq, _ in entradas))
    lineas_opt = "\n".join(f"  {izq:<{ancho}}  {desc}" for izq, desc in entradas)
    return f"{spec.usage}\n\n{spec.summary}.\n\nOpciones:\n{lineas_opt}\n"


HELP = format_general_help()


class UsageError(Exception):
    """Uso inválido de la línea de comandos: código de salida 2."""

    def __init__(self, message: str, usage: str = USAGE) -> None:
        super().__init__(message)
        self.usage = usage


def parse_option_value(opt: OptionSpec, raw: str, usage: str) -> Any:
    if opt.kind == "int":
        try:
            val: Any = int(raw)
        except ValueError:
            raise UsageError(
                f"valor inválido para {opt.flag} (se esperaba un entero): {raw!r}",
                usage,
            ) from None
    elif opt.kind == "float":
        try:
            fval = float(raw)
        except ValueError:
            raise UsageError(
                f"valor inválido para {opt.flag} (se esperaba un número): {raw!r}",
                usage,
            ) from None
        if not math.isfinite(fval):
            raise UsageError(
                f"valor inválido para {opt.flag} (se esperaba un número finito): {raw!r}",
                usage,
            )
        val = fval
    else:
        val = raw

    if opt.choices is not None and val not in opt.choices:
        permitidos = ", ".join(repr(c) for c in opt.choices)
        raise UsageError(
            f"valor inválido para {opt.flag}: {val!r} (valores permitidos: {permitidos})",
            usage,
        )
    return val


def parse_args(argv: list[str]) -> SimpleNamespace | str:
    """Devuelve el espacio de argumentos del subcomando, o el texto de ayuda si se pidió -h/--help.

    Se lee a mano y no con argparse para que el uso, la ayuda y los errores salgan en español.
    """
    if not argv:
        nombres = ", ".join(SUBCOMMANDS_BY_NAME)
        raise UsageError(f"falta indicar un subcomando ({nombres})")

    primero = argv[0]
    if primero in ("-h", "--help"):
        return HELP
    if primero.startswith("-"):
        raise UsageError(f"opción desconocida: {primero}")

    spec = SUBCOMMANDS_BY_NAME.get(primero)
    if spec is None:
        raise UsageError(f"subcomando desconocido: {primero!r}")

    opts_by_flag = {opt.flag: opt for opt in spec.options}
    values: dict[str, Any] = {opt.dest: opt.default for opt in spec.options}
    seen: set[str] = set()
    solo_posicionales = False
    pendientes = iter(argv[1:])

    for arg in pendientes:
        if solo_posicionales:
            raise UsageError(f"argumento posicional inesperado: {arg}", spec.usage)
        if arg == "--":
            solo_posicionales = True
            continue
        if arg in ("-h", "--help"):
            return format_subcommand_help(spec)
        if not arg.startswith("-") or arg == "-":
            raise UsageError(f"argumento posicional inesperado: {arg}", spec.usage)

        if "=" in arg:
            flag, _, inline_val = arg.partition("=")
            has_inline = True
        else:
            flag = arg
            inline_val = ""
            has_inline = False

        opt = opts_by_flag.get(flag)
        if opt is None:
            raise UsageError(f"opción desconocida: {flag}", spec.usage)

        if opt.kind == "flag":
            if has_inline:
                raise UsageError(f"la opción {flag} no admite valor", spec.usage)
            values[opt.dest] = True
            seen.add(opt.dest)
            continue

        if has_inline:
            raw_val = inline_val
        else:
            nxt = next(pendientes, None)
            if nxt is None:
                raise UsageError(f"a {flag} le falta un valor", spec.usage)
            raw_val = nxt

        values[opt.dest] = parse_option_value(opt, raw_val, spec.usage)
        seen.add(opt.dest)

    faltantes = [opt.flag for opt in spec.options if opt.required and opt.dest not in seen]
    if len(faltantes) == 1:
        raise UsageError(f"falta la opción obligatoria: {faltantes[0]}", spec.usage)
    if len(faltantes) > 1:
        raise UsageError(f"faltan las opciones obligatorias: {', '.join(faltantes)}", spec.usage)

    return SimpleNamespace(cmd=spec.name, func=spec.func, **values)


def main(argv: list[str] | None = None) -> int:
    try:
        parsed = parse_args(sys.argv[1:] if argv is None else argv)
    except UsageError as exc:
        print(f"{exc.usage}\nError: {exc}", file=sys.stderr)
        return 2
    if isinstance(parsed, str):
        print(parsed, end="")
        return 0
    return parsed.func(parsed)


if __name__ == "__main__":
    sys.exit(main())
