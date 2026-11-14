#!/usr/bin/env bash
# chequeo-gemba.sh: Inspección determinista en el Gemba antes de dar un paso por cerrado.
# Verifica git real, validez de JSON, ausencia de mojibake, placeholders abiertos
# y heurística de valores duplicados sospechosos en tablas.

set -euo pipefail

TARGET="${1:-.}"

if [ ! -e "$TARGET" ]; then
  echo "[PARAR LÍNEA] No existe la ruta objetivo: $TARGET" >&2
  exit 2
fi

echo "============================================================"
echo " INSPECCIÓN EN EL GEMBA: $(realpath "$TARGET")"
echo " Fecha: $(date -Iseconds)"
echo "============================================================"

ISSUES=0
WARNINGS=0

# 1. Estado de Git (si aplica)
if [ -d "$TARGET" ] && git -C "$TARGET" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo ""
  echo "[1/5] Estado Git real en el Gemba:"
  BRANCH=$(git -C "$TARGET" branch --show-current 2>/dev/null || echo "detached")
  DIRTY=$(git -C "$TARGET" status --porcelain | wc -l)
  echo "  - Rama activa: $BRANCH"
  echo "  - Archivos sin commitear: $DIRTY"
  if [ "$DIRTY" -gt 0 ]; then
    git -C "$TARGET" status -s | sed 's/^/    /'
  fi
else
  echo ""
  echo "[1/5] Estado Git: objetivo fuera de un árbol git o es un archivo individual."
fi

# 2. Validación de archivos JSON
echo ""
echo "[2/5] Validación determinista de archivos JSON:"
JSON_COUNT=0
while IFS= read -r -d '' jf; do
  JSON_COUNT=$((JSON_COUNT + 1))
  if ! python3 -m json.tool "$jf" >/dev/null 2>&1; then
    echo "  [PARAR LÍNEA] JSON inválido: $jf"
    ISSUES=$((ISSUES + 1))
  fi
done < <(find "$TARGET" -path '*/.git' -prune -o -name '*.json' -type f -print0)
echo "  - Archivos JSON verificados: $JSON_COUNT (Errores: $ISSUES)"

# 3. Detección de Mojibake (UTF-8 corrupto)
echo ""
echo "[3/5] Chequeo de codificación UTF-8 y ausencia de Mojibake:"
MOJIBAKE_HITS=$(python3 - "$TARGET" <<'PYEOF'
import pathlib, re, sys

target = pathlib.Path(sys.argv[1])
files = [target] if target.is_file() else [
    p for p in target.rglob("*")
    if p.is_file() and ".git" not in p.parts and p.suffix in {".md", ".html", ".py", ".ts", ".js", ".json"}
]
# Patrones típicos de UTF-8 leído como Latin-1
bad_re = re.compile(r"Ã[¡©­³º±‰“š‘]|â€[“”˜™¦¢]|Â¿|Â¡")
hits = 0
for f in files:
    try:
        txt = f.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  [PARAR LÍNEA] No es UTF-8 válido: {f}")
        hits += 1
        continue
    for idx, line in enumerate(txt.splitlines(), 1):
        m = bad_re.search(line)
        if m:
            print(f"  [PARAR LÍNEA] Posible mojibake ('{m.group(0)}') en {f}:{idx}")
            hits += 1
            break
sys.exit(hits)
PYEOF
) || {
  MOJIBAKE_CODE=$?
  echo "$MOJIBAKE_HITS"
  ISSUES=$((ISSUES + MOJIBAKE_CODE))
}
if [ -z "${MOJIBAKE_HITS:-}" ]; then
  echo "  - Cero mojibake y UTF-8 válido en todos los archivos de texto."
fi

# 4. Marcadores de trazabilidad ([SIN CONFIRMAR], [PRÁCTICA ESTÁNDAR], TODO/TBD)
echo ""
echo "[4/5] Marcadores de trazabilidad y pendientes:"
python3 - "$TARGET" <<'PYEOF'
import pathlib, re, sys

target = pathlib.Path(sys.argv[1])
files = [target] if target.is_file() else [
    p for p in target.rglob("*")
    if p.is_file() and ".git" not in p.parts and p.suffix in {".md", ".html"}
]
sin_conf = 0
prac_est = 0
for f in files:
    txt = f.read_text(encoding="utf-8", errors="ignore")
    sin_conf += len(re.findall(r"\[SIN CONFIRMAR\]", txt, re.I))
    prac_est += len(re.findall(r"\[PR[ÁA]CTICA EST[ÁA]NDAR\]", txt, re.I))

print(f"  - Etiquetas [SIN CONFIRMAR] declaradas honestamente: {sin_conf}")
print(f"  - Etiquetas [PRÁCTICA ESTÁNDAR] declaradas: {prac_est}")
PYEOF

# 5. Heurística anti-misatribución en tablas (Caso FSU-5: dos filas con el mismo valor numérico con unidades)
echo ""
echo "[5/5] Heurística anti-misatribución en tablas (valores con unidades duplicados):"
DUP_OUT=$(python3 - "$TARGET" <<'PYEOF'
import collections, pathlib, re, sys

target = pathlib.Path(sys.argv[1])
files = [target] if target.is_file() else [
    p for p in target.rglob("*")
    if p.is_file() and ".git" not in p.parts and p.suffix in {".md", ".html"}
]
unit_re = re.compile(r"\b(\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?\s*(?:N·m|Nm|kPa|MPa|bar|psi))\b")

warnings = 0
for f in files:
    txt = f.read_text(encoding="utf-8", errors="ignore")
    seen = collections.defaultdict(list)
    for idx, line in enumerate(txt.splitlines(), 1):
        if "|" in line or "<td" in line.lower():
            for m in unit_re.finditer(line):
                val = re.sub(r"\s+", " ", m.group(1).strip())
                seen[val].append(idx)
    for val, lines in seen.items():
        if len(lines) > 1:
            print(f"  [AVISO GEMBA] Valor '{val}' aparece en múltiples filas de tabla en {f.name} (líneas {lines}); verificar que no sea misatribución.")
            warnings += 1
sys.exit(0)
PYEOF
)
if [ -n "$DUP_OUT" ]; then
  echo "$DUP_OUT"
  WARNINGS=$((WARNINGS + 1))
else
  echo "  - Sin valores físicos duplicados sospechosos en tablas."
fi

echo ""
echo "============================================================"
if [ "$ISSUES" -gt 0 ]; then
  echo " VEREDICTO GEMBA: PARAR LÍNEA ($ISSUES errores críticos detectados)"
  exit 1
else
  echo " VEREDICTO GEMBA: VERIFICADO ($ISSUES errores críticos, $WARNINGS avisos para revisión)"
  exit 0
fi
