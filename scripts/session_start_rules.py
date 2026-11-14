#!/usr/bin/env python3
"""
Inyecta las reglas operativas de `rules/AGENTS.md` al inicio de la sesión en Claude Code
(donde los plugins no tienen un directorio `rules/` nativo auto-cargado como Antigravity).
"""

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = PLUGIN_ROOT / "rules" / "AGENTS.md"


def main() -> int:
    if not RULES_FILE.exists():
        print("{}")
        return 0

    content = RULES_FILE.read_text(encoding="utf-8").strip()
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
