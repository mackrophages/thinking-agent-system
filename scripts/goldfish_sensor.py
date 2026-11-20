#!/usr/bin/env python3
"""
Observador Silencioso Gemba - Sensor Out-of-Band (0 Tokens).
Mide Cycle Time (CT) sin detener el reloj y registra fallos reales de herramientas
para alimentar el Pre-Production Readiness Board (Builds 1-12).

Principios y Poka-Yokes implementados:
1. Opcional por proyecto (Poka-Yoke): si el directorio del proyecto no contiene
   `.tas/` (creado con `observer_cli.py init`), el sensor no hace nada
   y sale con `{}` (código 0). Nunca ensucia `/root` ni directorios no instrumentados.
2. Señales de error documentadas:
   - En Claude Code: evento `PostToolUseFailure` (campo `error`), o `tool_response`
     objeto con `is_error: true` / `interrupted: true` / `exit_code != 0`.
   - En Antigravity (agy): evento `PostToolUse` con campo `error` no vacío.
   - Jamás busca palabras como "failed" o "error:" en el texto libre de lecturas exitosas.
3. Reloj resistente a proot/Android: guarda tanto `time.time()` como `time.monotonic()`
   y suma `duration_ms` de herramientas. Calcula CT con el delta monotónico cuando
   proviene del mismo arranque y detecta saltos de reloj (`clock_jump_detected`).
4. Unidad de trabajo real (Corrida / Build): `Stop` se dispara al final de cada turno,
   por lo que actualiza el checkpoint activo sin fragmentar la corrida en múltiples builds,
   salvo que se indique `TAS_AUTO_CLOSE_ON_STOP=1` o `--close-build`.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

EXPLORATORY_TOOLS = {
    "grep",
    "glob",
    "find_by_name",
    "grep_search",
    "list_dir",
}

READ_TOOLS = {
    "read",
    "read_file",
    "view_file",
}

CARPETA_OBSERVADOR = ".tas"


def leer_env(nombre: str, defecto: str = "") -> str:
    """Devuelve la variable si está definida y no vacía; si no, el defecto."""
    valor = os.environ.get(nombre, "").strip()
    return valor or defecto


def resolver_carpeta_observador(project_dir: Path) -> Path:
    """Carpeta del observador del proyecto."""
    return project_dir / CARPETA_OBSERVADOR


def resolve_project_dir(cli_project_dir: str | None, payload: dict[str, Any]) -> Path:
    if cli_project_dir:
        return Path(cli_project_dir).resolve()
    cwd = payload.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        return Path(cwd.strip()).resolve()
    ws_paths = payload.get("workspacePaths") or payload.get("workspace_paths")
    if isinstance(ws_paths, list) and ws_paths and isinstance(ws_paths[0], str) and ws_paths[0].strip():
        return Path(ws_paths[0].strip()).resolve()
    env_dir = leer_env("TAS_PROJECT_DIR", os.environ.get("CLAUDE_PROJECT_DIR", "").strip())
    if env_dir:
        return Path(env_dir).resolve()
    return Path.cwd().resolve()


def resolve_event(cli_event: str | None, payload: dict[str, Any]) -> str:
    if cli_event:
        return cli_event
    env_ev = os.environ.get("CLAUDE_HOOK_EVENT")
    if env_ev:
        return env_ev
    hook_ev = payload.get("hook_event_name") or payload.get("event")
    if isinstance(hook_ev, str) and hook_ev.strip():
        return hook_ev.strip()
    if "terminationReason" in payload or "stop_hook_active" in payload:
        return "Stop"
    return "PostToolUse"


def extract_tool_name(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("tool_name"), str) and payload["tool_name"].strip():
        return payload["tool_name"].strip()
    if isinstance(payload.get("toolName"), str) and payload["toolName"].strip():
        return payload["toolName"].strip()
    tool_call = payload.get("toolCall")
    if isinstance(tool_call, dict) and isinstance(tool_call.get("name"), str):
        return tool_call["name"].strip()
    return "unknown_tool"


def is_observer_own_command(payload: dict[str, Any]) -> bool:
    """El observador no se mide a sí mismo: sus comandos (observer_cli.py) no son trabajo de la corrida."""
    tool_input = payload.get("tool_input") or payload.get("toolInput")
    if not isinstance(tool_input, dict):
        tool_call = payload.get("toolCall")
        tool_input = tool_call.get("args") if isinstance(tool_call, dict) else None
    if not isinstance(tool_input, dict):
        return False
    command = tool_input.get("command") or tool_input.get("CommandLine")
    return isinstance(command, str) and "observer_cli.py" in command


def extract_transcript_path(payload: dict[str, Any]) -> str | None:
    tp = payload.get("transcript_path") or payload.get("transcriptPath")
    if isinstance(tp, str) and tp.strip():
        return tp.strip()
    return None


def detect_documented_tool_error(event: str, payload: dict[str, Any]) -> tuple[bool, str]:
    """
    Detecta fallos de herramientas usando únicamente señales estructurales documentadas
    de Claude Code y Antigravity, evitando falsos positivos por contenido leído.
    """
    if event == "PostToolUseFailure":
        err = payload.get("error")
        detail = str(err).strip() if err is not None else "PostToolUseFailure"
        return True, detail or "PostToolUseFailure"

    # Antigravity PostToolUse documenta `error` (string) en el nivel superior si la herramienta falló
    top_err = payload.get("error")
    if isinstance(top_err, str) and top_err.strip():
        return True, top_err.strip()
    if top_err is True:
        return True, "Tool error flag set"

    if payload.get("is_error") is True:
        return True, str(payload.get("error") or "is_error=true")

    # Claude Code PostToolUse pasa `tool_response` como objeto
    tool_resp = payload.get("tool_response")
    if isinstance(tool_resp, dict):
        if tool_resp.get("is_error") is True:
            return True, str(tool_resp.get("stderr") or tool_resp.get("error") or "tool_response.is_error=true")
        if tool_resp.get("interrupted") is True:
            return True, "Tool execution interrupted"
        for code_key in ("exit_code", "exitCode", "return_code", "returnCode"):
            code_val = tool_resp.get(code_key)
            if isinstance(code_val, int) and code_val != 0:
                stderr_txt = str(tool_resp.get("stderr") or "").strip()
                return True, f"{code_key}={code_val}: {stderr_txt}"[:200]

    return False, ""


def classify_error_category(tool_name: str, error_detail: str) -> str:
    low = error_detail.lower()
    t_low = tool_name.lower()

    if any(
        tok in low
        for tok in (
            "schema",
            "invalid parameter",
            "missing required",
            "validation",
            "unexpected property",
            "invalid_type",
            "unknown argument",
        )
    ):
        return "Wrong Parts - Designed"

    if any(
        tok in low
        for tok in (
            "no such file",
            "file does not exist",
            "not found",
            "enoent",
            "cannot find",
            "does not exist",
        )
    ):
        return "Missing Parts"

    if t_low in READ_TOOLS and any(tok in low for tok in ("corrupt", "obsolete", "contradict", "invalid config")):
        return "Wrong Parts - Supplied"

    return "Wrong Parts - Built"


def default_active_state(now_wall: float, now_mono: float, task: str = "") -> dict[str, Any]:
    return {
        "task": task or "Corrida en observación",
        "start_time": now_wall,
        "start_monotonic": now_mono,
        "last_update_time": now_wall,
        "last_update_monotonic": now_mono,
        "turns": 0,
        "tool_calls": 0,
        "failed_tool_calls": 0,
        "retried_tool_calls": 0,
        "consecutive_failures": 0,
        "andon_triggered": False,
        "last_failed_tool": None,
        "exploratory_calls": 0,
        "consecutive_exploratory": 0,
        "bloated_reads": 0,
        "tool_duration_ms_sum": 0,
        "quality_issues": 0,
        "issues_log": [],
        "transcript_path": None,
        "transcript_paths": [],
    }


def load_active_state(active_path: Path, now_wall: float, now_mono: float) -> dict[str, Any]:
    if active_path.exists():
        try:
            data = json.loads(active_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "start_time" in data:
                return data
        except Exception:
            pass
    state = default_active_state(now_wall, now_mono)
    active_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def compute_elapsed_seconds(state: dict[str, Any], now_wall: float, now_mono: float) -> tuple[float, bool, str]:
    """
    Calcula el tiempo transcurrido prefiriendo CLOCK_MONOTONIC cuando es consistente,
    detectando saltos del reloj de pared bajo proot/Android.
    """
    start_wall = float(state.get("start_time", now_wall))
    start_mono = state.get("start_monotonic")
    wall_delta = now_wall - start_wall
    tool_dur_sec = float(state.get("tool_duration_ms_sum", 0)) / 1000.0

    if isinstance(start_mono, (int, float)):
        mono_delta = now_mono - float(start_mono)
        if mono_delta >= 0:
            jump = (wall_delta < 0) or (abs(wall_delta - mono_delta) > 5.0)
            elapsed = max(0.01, mono_delta, tool_dur_sec)
            return elapsed, jump, "monotonic_clock"

    jump = wall_delta < 0
    elapsed = max(0.01, wall_delta if wall_delta >= 0 else tool_dur_sec, tool_dur_sec)
    return elapsed, jump, "wall_clock"


def get_next_build_number(trace_file: Path, start_time: float | None = None) -> int:
    if not trace_file.exists():
        return 1
    lines = [line for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return 1
    if start_time is not None:
        try:
            last_rec = json.loads(lines[-1])
            if isinstance(last_rec, dict) and last_rec.get("start_time") == start_time:
                return int(last_rec.get("build") or ((len(lines) - 1) % 12) + 1)
        except Exception:
            pass
    return (len(lines) % 12) + 1


def write_or_update_trace_record(
    obs_dir: Path,
    state: dict[str, Any],
    now_wall: float,
    now_mono: float,
    standard_min: float,
    takt_min: float,
    note: str = "",
) -> dict[str, Any]:
    trace_file = obs_dir / "gemba_trace.jsonl"
    elapsed_sec, clock_jump, clock_source = compute_elapsed_seconds(state, now_wall, now_mono)
    ct_min = round(elapsed_sec / 60.0, 2)
    start_time = state.get("start_time")
    build_num = get_next_build_number(trace_file, start_time=start_time)

    # Si hubo exceso de búsqueda exploratoria a ciegas (>4 llamadas), registrar Missing Parts
    if state.get("exploratory_calls", 0) > 4 and not any(
        i.get("tool") == "search_loop" for i in state.get("issues_log", [])
    ):
        state["quality_issues"] = state.get("quality_issues", 0) + 1
        state.setdefault("issues_log", []).append(
            {
                "tool": "search_loop",
                "category": "Missing Parts",
                "detail": f"{state['exploratory_calls']} búsquedas exploratorias; falta índice en CLAUDE.md/KI.",
            }
        )

    total_calls = int(state.get("tool_calls", 0))
    failed_or_retried = int(state.get("failed_tool_calls", 0)) + int(state.get("retried_tool_calls", 0))
    fty_pct = round(max(0.0, (1.0 - (failed_or_retried / total_calls)) * 100.0), 1) if total_calls > 0 else 100.0

    delivery_status = "Under Standard"
    muda_type = None
    if ct_min > takt_min:
        delivery_status = "CT > TT"
        muda_type = "Inventario (WIP)" if state.get("bloated_reads", 0) > 0 else "Retrabajo / Espera"
    elif ct_min > standard_min:
        delivery_status = "CT > Standard"
        muda_type = "Movimiento" if state.get("exploratory_calls", 0) > 2 else "Sobreprocesamiento"

    t_paths = state.get("transcript_paths", [])
    last_tp = state.get("transcript_path") or (t_paths[-1] if t_paths else None)

    build_record = {
        "build": build_num,
        "start_time": start_time,
        "task": state.get("task", "Corrida ejecutada"),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now_wall)),
        "status": "performed",
        "turns": max(1, int(state.get("turns", 1))),
        "ct_min": ct_min,
        "elapsed_sec": round(elapsed_sec, 2),
        "clock_source": clock_source,
        "clock_jump_detected": clock_jump,
        "standard_min": standard_min,
        "tt_min": takt_min,
        "delivery_flag": delivery_status,
        "muda_Detected": muda_type,
        "tool_calls": total_calls,
        "failed_tool_calls": int(state.get("failed_tool_calls", 0)),
        "retried_tool_calls": int(state.get("retried_tool_calls", 0)),
        "fty_pct": fty_pct,
        "exploratory_calls": int(state.get("exploratory_calls", 0)),
        "bloated_reads": int(state.get("bloated_reads", 0)),
        "andon_triggered": bool(state.get("andon_triggered", False)),
        "quality_issues": int(state.get("quality_issues", 0)),
        "issues_log": state.get("issues_log", []),
        "transcript_path": last_tp,
        "transcript_paths": t_paths,
        "note": note or ("CT > TT" if delivery_status == "CT > TT" else ("CT > Standard" if delivery_status == "CT > Standard" else "Single build performed")),
    }

    lines: list[str] = []
    if trace_file.exists():
        lines = [line for line in trace_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    updated_existing = False
    if lines and start_time is not None:
        try:
            last_rec = json.loads(lines[-1])
            if isinstance(last_rec, dict) and last_rec.get("start_time") == start_time:
                lines[-1] = json.dumps(build_record, ensure_ascii=False)
                updated_existing = True
        except Exception:
            pass

    if not updated_existing:
        lines.append(json.dumps(build_record, ensure_ascii=False))

    trace_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return build_record


def close_active_build(
    obs_dir: Path,
    now_wall: float,
    now_mono: float,
    standard_min: float,
    takt_min: float,
    note: str = "",
) -> dict[str, Any] | None:
    active_path = obs_dir / "active_build.json"
    if not active_path.exists():
        return None

    try:
        state = json.loads(active_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    build_record = write_or_update_trace_record(
        obs_dir, state, now_wall, now_mono, standard_min, takt_min, note=note
    )
    active_path.unlink(missing_ok=True)
    return build_record


def main() -> int:
    parser = argparse.ArgumentParser(description="Sensor silencioso Goldfish (Lean AgentOps)")
    parser.add_argument("--platform", default="auto", choices=["auto", "claude", "agy"])
    parser.add_argument("--event", default=None)
    parser.add_argument("--project-dir", dest="project_dir", default=None)
    parser.add_argument("--close-build", action="store_true", help="Cerrar explícitamente la corrida activa")
    parser.add_argument("--close-on-stop", action="store_true", help="Cerrar la corrida al recibir Stop")
    parser.add_argument("--note", default="", help="Nota opcional al cerrar la corrida")
    args, _ = parser.parse_known_args()

    raw_input = ""
    if not sys.stdin.isatty():
        try:
            raw_input = sys.stdin.read().strip()
        except Exception:
            raw_input = ""

    payload: dict[str, Any] = {}
    if raw_input:
        try:
            parsed = json.loads(raw_input)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {}

    project_dir = resolve_project_dir(args.project_dir, payload)
    obs_dir = resolver_carpeta_observador(project_dir)

    # Poka-Yoke: si el proyecto no tiene .tas/ inicializado, no hacer nada
    if not obs_dir.is_dir():
        print("{}")
        return 0

    standard_min = float(leer_env("TAS_STANDARD_MIN", "5.0"))
    takt_min = float(leer_env("TAS_TAKT_MIN", "7.0"))
    now_wall = time.time()
    now_mono = time.monotonic()

    if args.close_build:
        close_active_build(obs_dir, now_wall, now_mono, standard_min, takt_min, note=args.note)
        print("{}")
        return 0

    event = resolve_event(args.event, payload)
    active_path = obs_dir / "active_build.json"

    if event in ("PostToolUse", "PostToolUseFailure"):
        if is_observer_own_command(payload):
            print("{}")
            return 0
        state = load_active_state(active_path, now_wall, now_mono)
        tool_name = extract_tool_name(payload)
        is_error, error_detail = detect_documented_tool_error(event, payload)

        state["tool_calls"] = int(state.get("tool_calls", 0)) + 1
        state["last_update_time"] = now_wall
        state["last_update_monotonic"] = now_mono

        dur = payload.get("duration_ms")
        if isinstance(dur, (int, float)) and dur > 0:
            state["tool_duration_ms_sum"] = int(state.get("tool_duration_ms_sum", 0)) + int(dur)

        tp = extract_transcript_path(payload)
        if tp:
            state["transcript_path"] = tp
            t_list = state.setdefault("transcript_paths", [])
            if tp not in t_list:
                t_list.append(tp)

        if tool_name.lower() in EXPLORATORY_TOOLS:
            state["exploratory_calls"] = int(state.get("exploratory_calls", 0)) + 1
            state["consecutive_exploratory"] = int(state.get("consecutive_exploratory", 0)) + 1
        else:
            state["consecutive_exploratory"] = 0

        # Detectar lecturas masivas sin acotar (>20 KB devueltos de una vez)
        if tool_name.lower() in READ_TOOLS and not is_error:
            resp_obj = payload.get("tool_response")
            resp_len = len(json.dumps(resp_obj, ensure_ascii=False)) if resp_obj is not None else 0
            if resp_len > 20000:
                state["bloated_reads"] = int(state.get("bloated_reads", 0)) + 1

        if is_error:
            state["failed_tool_calls"] = int(state.get("failed_tool_calls", 0)) + 1
            state["consecutive_failures"] = int(state.get("consecutive_failures", 0)) + 1
            state["last_failed_tool"] = tool_name
            state["quality_issues"] = int(state.get("quality_issues", 0)) + 1
            category = classify_error_category(tool_name, error_detail)
            state.setdefault("issues_log", []).append(
                {
                    "tool": tool_name,
                    "category": category,
                    "detail": error_detail[:160].replace("\n", " "),
                }
            )
            if state["consecutive_failures"] >= 3 and not state.get("andon_triggered"):
                state["andon_triggered"] = True
                state["issues_log"].append(
                    {
                        "tool": tool_name,
                        "category": "Missing Parts" if category == "Missing Parts" else "Wrong Parts - Designed",
                        "detail": f"Andon activado: 3 fallos consecutivos ({tool_name}). La tercera es la vencida.",
                    }
                )
        else:
            if state.get("last_failed_tool") == tool_name:
                state["retried_tool_calls"] = int(state.get("retried_tool_calls", 0)) + 1
            state["consecutive_failures"] = 0
            state["last_failed_tool"] = None

        active_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    elif event == "Stop":
        if not active_path.exists():
            print("{}")
            return 0

        state = load_active_state(active_path, now_wall, now_mono)
        state["turns"] = int(state.get("turns", 0)) + 1
        state["last_update_time"] = now_wall
        state["last_update_monotonic"] = now_mono

        tp = extract_transcript_path(payload)
        if tp:
            state["transcript_path"] = tp
            t_list = state.setdefault("transcript_paths", [])
            if tp not in t_list:
                t_list.append(tp)

        elapsed_sec, clock_jump, _ = compute_elapsed_seconds(state, now_wall, now_mono)
        state["current_ct_min"] = round(elapsed_sec / 60.0, 2)
        state["clock_jump_detected"] = clock_jump
        active_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        write_or_update_trace_record(obs_dir, state, now_wall, now_mono, standard_min, takt_min, note=args.note)

        auto_close = args.close_on_stop or (leer_env("TAS_AUTO_CLOSE_ON_STOP") == "1")
        if auto_close:
            active_path.unlink(missing_ok=True)

    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
