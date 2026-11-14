# Historial de cambios (`CHANGELOG`)

Todos los cambios relevantes de **TAS (Thinking Agent System)** se registran en este archivo.

El repositorio público `thinking-agent-system` nace en la versión **2.0.0** con un historial limpio de un solo commit inicial. Las versiones **1.0.0 a 1.3.0** se desarrollaron bajo el nombre anterior del plugin, **`lean-kit`**.

---

## [2.0.0] - 2026-11-13

### Por qué cambia a 2.0.0

**TAS (Thinking Agent System)** es la versión 2.0.0 de `lean-kit` (1.x). El cambio de versión mayor responde a tres motivos:
1. **Renombrado del plugin y sus skills:** evita la repetición de `"lean"` al invocar (`/lean-kit:lean-a3` pasa a `/tas:a3` en Claude Code y a `tas-a3` en Antigravity y OpenCode) y elimina la colisión de nombre con productos comerciales llamados LeanKit.
2. **Publicación en un repositorio nuevo sin historial previo:** `thinking-agent-system` se publica desde una exportación limpia de la etiqueta `v2.0.0`.
3. **Poka-yoke de fuentes verificables en el A3 (Contrato 2):** `validar-a3.py` exige fuentes que se puedan abrir o comprobar en disco, manteniendo compatibilidad con los A3 existentes mediante la línea `- **Contrato:**`.

### Qué cambia de nombre

| Elemento | En `lean-kit` 1.x | En `TAS` 2.0.0 | Notas de compatibilidad |
| :--- | :--- | :--- | :--- |
| **Nombre del plugin y catálogo** | `lean-kit` (`lean-kit@lean-kit`) | `tas` (`tas@tas`) | En `plugin.json`, `.claude-plugin/plugin.json` y `.claude-plugin/marketplace.json`. |
| **Nombre visible (`displayName`)** | `Lean Kit: Mejora Continua, Gemba y Lean AgentOps` | `TAS: Thinking Agent System` | `"Lean AgentOps"` se conserva donde nombra el método operativo. |
| **Paquete del tablero** | `lean-kit-tablero` | `tas-tablero` | En `herramientas/tablero/package.json`. |
| **Carpetas y nombres de skills en el repositorio** | `skills/lean-a3/`, `skills/lean-5-porques/`, `skills/lean-agent-ops/`, `skills/lean-gemba/`, `skills/lean-goldfish-observer/`, `skills/lean-kaizen/`, `skills/lean-ojos-frescos/` | `skills/a3/`, `skills/5-porques/`, `skills/agent-ops/`, `skills/gemba/`, `skills/goldfish-observer/`, `skills/kaizen/`, `skills/ojos-frescos/` | En Claude Code se invocan como `/tas:<skill>`. En Antigravity y OpenCode se instalan copias generadas `tas-<skill>` (`skills/tas-<skill>/`). |
| **Clave del hook en Antigravity** | `lean-goldfish-sensor` | `tas-goldfish-sensor` | En `hooks.json`. |
| **Carpeta del observador por proyecto** | `.lean_observer/` | `.tas/` | Durante una versión, `scripts/goldfish_sensor.py`, `skills/goldfish-observer/scripts/observer_cli.py`, `hooks.json` y `hooks/hooks.json` siguen leyendo `.lean_observer/` si `.tas/` no existe. |
| **Variables de entorno del sensor y observador** | `LEAN_PROJECT_DIR`, `LEAN_STANDARD_MIN`, `LEAN_TAKT_MIN`, `LEAN_AUTO_CLOSE_ON_STOP`, `LEAN_GOLDFISH_ARTEFACTO`, `LEAN_GOLDFISH_DESPACHO` | `TAS_PROJECT_DIR`, `TAS_STANDARD_MIN`, `TAS_TAKT_MIN`, `TAS_AUTO_CLOSE_ON_STOP`, `TAS_GOLDFISH_ARTEFACTO`, `TAS_GOLDFISH_DESPACHO` | Durante una versión se lee la variable `LEAN_*` si la variable `TAS_*` correspondiente no está definida o está vacía. |
| **Variable de ruta al repositorio en el manual y pruebas** | `LEAN_KIT_REPO` | `TAS_REPO` | Con respaldo en `LEAN_KIT_REPO` durante una versión. |

### Nuevas capacidades de la versión 2.0.0

- **Poka-yoke de fuentes verificables en `skills/a3/scripts/validar-a3.py` (Contrato 2):**
  - Revisa todas las celdas de la columna `"Fuente"` (o viñetas `Fuente:`) en la sección 2 y todas las filas cuyo estado es `**Verificado**` en la tabla de observaciones de la sección 4.
  - Admite una o varias fuentes separadas por `;` (fuera de comillas invertidas), exigiendo que cada una cumpla una de cuatro formas:
    1. Archivo y línea o rango: `<ruta>:<N>` o `<ruta>:<N>-<M>` (archivo real dentro de la carpeta del A3 o la raíz del proyecto, con `1 <= N <= M` dentro del total de líneas).
    2. Comando con su salida: `` `<comando>` -> <ruta> `` (archivo real y mayor de 0 bytes).
    3. URL: `https://<sin-espacios>`.
    4. Evidencia: `evidencia: <ruta>` (archivo real y mayor de 0 bytes).
  - Nueva opción `--raiz <carpeta>` en `validar-a3.py`.
  - La plantilla `skills/a3/resources/plantilla-a3-interno.md` y el ejemplo `skills/a3/resources/ejemplo-a3.md` declaran `- **Contrato:** 2`, acompañados de `skills/a3/resources/ejemplo-respaldo.log`. Los A3 sin línea `Contrato` se siguen validando y dibujando con el contrato `1`.
- **Vocabulario unificado en `skills/a3/references/contrato-a3.json`:**
  - Fuente única para etapas, ramas, estados de rama, niveles, cuadrantes PICK, decisiones, ventanas, columnas de opciones y rótulos de la sección 7 en los contratos `1` y `2`, leída por `skills/a3/scripts/validar-a3.py`, `skills/a3/scripts/dibujar-a3.py` y `herramientas/tablero/construir.mjs`.

### Cómo migrar desde `lean-kit` 1.x

En los bloques siguientes, `REPO=<ruta-a-tas>` es la carpeta donde clonaste o copiaste `thinking-agent-system`.

#### 1. Claude Code

Desinstala el plugin y el catálogo anteriores y registra `tas@tas`:

```bash
claude plugin uninstall lean-kit@lean-kit
claude plugin marketplace remove lean-kit
claude plugin marketplace add <ruta-a-tas>
claude plugin install tas@tas
```

Verificación: `claude plugin list` debe mostrar `tas@tas` en la versión `2.0.0` y no mostrar `lean-kit`.

#### 2. Antigravity (`agy`)

Desinstala `lean-kit` y genera la copia `tas` con las siete carpetas `tas-<skill>` y sus rutas internas reescritas:

```bash
agy plugin uninstall lean-kit
REPO=<ruta-a-tas>
DEST_PLUGIN="$HOME/.gemini/config/plugins/tas"  # o .agents/plugins/tas por proyecto
rm -rf "$DEST_PLUGIN" "$HOME/.gemini/config/plugins/lean-kit"
mkdir -p "$DEST_PLUGIN/skills"
cp -r "$REPO/plugin.json" "$REPO/hooks.json" "$REPO/LICENSE" "$REPO/README.md" \
      "$REPO/rules" "$REPO/agents" "$REPO/scripts" "$DEST_PLUGIN/"
for s in a3 5-porques agent-ops gemba goldfish-observer kaizen ojos-frescos; do
  cp -r "$REPO/skills/$s" "$DEST_PLUGIN/skills/tas-$s"
  sed -i "s/^name: $s\$/name: tas-$s/" "$DEST_PLUGIN/skills/tas-$s/SKILL.md"
done
python3 - "$DEST_PLUGIN" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
skills = ("a3", "5-porques", "agent-ops", "gemba", "goldfish-observer", "kaizen", "ojos-frescos")
archivos = [root / "rules/AGENTS.md", *root.glob("agents/*.md"), *root.glob("skills/tas-*/**/*.md")]
for p in archivos:
    txt = p.read_text(encoding="utf-8")
    for s in skills:
        txt = txt.replace(f"skills/{s}/", f"skills/tas-{s}/").replace(f"`{s}`", f"`tas-{s}`")
    p.write_text(txt, encoding="utf-8")
PY
agy plugin validate "$DEST_PLUGIN"
```

#### 3. OpenCode (global y por proyecto)

Elimina las copias `lean-*` y genera las copias `tas-*` junto con `scripts/` y el archivo de reglas:

**Global (`~/.config/opencode/`):**
```bash
REPO=<ruta-a-tas>
DEST_OC="$HOME/.config/opencode"
mkdir -p "$DEST_OC/skills"
rm -rf "$DEST_OC"/skills/lean-* "$DEST_OC"/skills/tas-* "$DEST_OC/scripts"
cp -r "$REPO/scripts" "$DEST_OC/scripts"
for s in a3 5-porques agent-ops gemba goldfish-observer kaizen ojos-frescos; do
  cp -r "$REPO/skills/$s" "$DEST_OC/skills/tas-$s"
  sed -i "s/^name: $s\$/name: tas-$s/" "$DEST_OC/skills/tas-$s/SKILL.md"
done
{
  printf '<!-- TAS v2.0.0: reglas siempre activas, copia de rules/AGENTS.md del plugin -->\n\n'
  cat "$REPO/rules/AGENTS.md"
} > "$DEST_OC/AGENTS.md"
python3 - "$DEST_OC" <<'PY'
import pathlib, sys
root = pathlib.Path(sys.argv[1])
skills = ("a3", "5-porques", "agent-ops", "gemba", "goldfish-observer", "kaizen", "ojos-frescos")
archivos = [root / "AGENTS.md", *root.glob("skills/tas-*/**/*.md")]
for p in archivos:
    txt = p.read_text(encoding="utf-8")
    for s in skills:
        txt = txt.replace(f"skills/{s}/", f"skills/tas-{s}/").replace(f"`{s}`", f"`tas-{s}`")
    p.write_text(txt, encoding="utf-8")
PY
```

**Por proyecto (`.opencode/` y `opencode.json`):**
```bash
REPO=<ruta-a-tas>
mkdir -p .opencode/skills .opencode/agents
rm -rf .opencode/skills/lean-* .opencode/skills/tas-* .opencode/scripts reglas-lean.md
cp -r "$REPO/scripts" .opencode/scripts
for s in a3 5-porques agent-ops gemba goldfish-observer kaizen ojos-frescos; do
  cp -r "$REPO/skills/$s" ".opencode/skills/tas-$s"
  sed -i "s/^name: $s\$/name: tas-$s/" ".opencode/skills/tas-$s/SKILL.md"
done
cp "$REPO"/agents/*.md .opencode/agents/
cp "$REPO/rules/AGENTS.md" reglas-tas.md
python3 - <<'PY'
import pathlib
skills = ("a3", "5-porques", "agent-ops", "gemba", "goldfish-observer", "kaizen", "ojos-frescos")
archivos = [pathlib.Path("reglas-tas.md"), *pathlib.Path(".opencode/agents").glob("*.md"), *pathlib.Path(".opencode/skills").glob("tas-*/**/*.md")]
for p in archivos:
    txt = p.read_text(encoding="utf-8")
    for s in skills:
        txt = txt.replace(f"skills/{s}/", f".opencode/skills/tas-{s}/").replace(f"`{s}`", f"`tas-{s}`")
    p.write_text(txt, encoding="utf-8")
PY
```
En `opencode.json`, cambia `"instructions": ["reglas-lean.md"]` por `"instructions": ["reglas-tas.md"]`.

#### 4. Proyectos instrumentados con `.lean_observer/`

- Mientras no ejecutes `init`, el sensor y todos los subcomandos de `observer_cli.py` siguen operando sobre `.lean_observer/` sin migrar nada.
- Para migrar un proyecto a `.tas/`, asegúrate de que no tenga una corrida abierta (`active_build.json`; si existe, ciérrala antes con `close-build`) y ejecuta:
  ```bash
  python3 <ruta-a-tas>/skills/goldfish-observer/scripts/observer_cli.py init --project-dir <ruta-al-proyecto>
  ```
  El comando renombra `.lean_observer/` a `.tas/`, actualiza `.tas/goldfish_sensor.py`, reemplaza `.lean_observer/active_build.json` por `.tas/active_build.json` en `.gitignore`, actualiza las rutas de jugadas en `board_state.json` y regenera `.tas/READINESS_BOARD.md` y `.tas/dashboard/index.html`.
