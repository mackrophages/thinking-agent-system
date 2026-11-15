# Historial de cambios (`CHANGELOG`)

Todos los cambios relevantes de **TAS (Thinking Agent System)** se registran en este archivo.

El repositorio público `thinking-agent-system` nace en la versión **2.0.0** con un historial limpio de un solo commit inicial. Las versiones **1.0.0 a 1.3.0** se desarrollaron bajo el nombre anterior del plugin, **`lean-kit`**.

---

## [2.2.0] - 2026-11-15

### El A3 se lee como una historia en una hoja

A partir de "Dirigir para aprender" (Shook): el título y la brecha a la vista, el flujo donde sucede el problema con su estallido kaizen, y poco texto.

- **Título con la brecha:** en el contrato 3, apenas la Brecha está escrita, el título tiene que traer su indicador y su meta: `# A3: <indicador>: de <actual> a <meta>`. Si no, el A3 no aprueba y el mensaje muestra la forma con los valores de la Brecha. Si el título trae `de <X> a <Y>` con cifras, tienen que ser el actual y la meta de la Brecha, aunque lleven un signo delante (`$1,250`, `<200 ms`); un texto de muestra `<...>` sin completar también para la línea.
- **Brecha con indicador:** `- **Brecha:** <indicador>: de <actual> (medido) a <meta> (meta) para <cuándo>`. En el contrato 3 el indicador es obligatorio. El dibujante la pinta: cuadros si es "N de M", barras si es una sola cifra con su unidad, y texto destacado si no puede leer los números (unidades compuestas como `1 h 30 min`, rangos o dos cifras). Las cifras se leen con la convención de El Salvador: punto decimal y coma de miles (`1,250.5`, `4.125 mA`); los rótulos de las barras son el texto del autor.
- **Estallidos kaizen:** en el mapa presente, el paso cuyo Problema empieza con `[A]` (una mayúscula entre corchetes) lleva un estallido de la causa A. La letra tiene que existir en la sección 4b; una marca corta mal escrita (`[a]`, `**[B]**`, `[OK]`) para la línea; una causa sin estallido, o un estallido en el mapa futuro, dan aviso. Un corchete con espacios (`[SIN CONFIRMAR]`) no es estallido. El validador y el dibujante leen la brecha, el estallido y las cifras con el mismo módulo, `skills/a3/scripts/lectura-a3.py`.
- **Menos texto:** avisos, que no paran la línea, cuando una celda pasa de 30 palabras, una viñeta de 40 o el A3 de 1500. El dibujante pone las fuentes al pie, pliega las tablas que ya están dibujadas (mapas e Ishikawa), muestra los porqués en cadena y arma dos columnas en pantallas anchas, sobre hoja blanca.

### Compatibilidad y adopción

- Los contratos 1 y 2 validan igual y se dibujan con el diseño nuevo.
- Un A3 de contrato 3 escrito con la 2.1.0 necesita, para aprobar en la 2.2.0, el indicador en la Brecha y la brecha en el título. La plantilla y el ejemplo ya vienen así.

### Medida

- El A3 que cerró el contrato 3 medía 13,759 px de alto a 412 px de ancho, unas 15 pantallas de teléfono; con el dibujante nuevo, y reescrito con menos texto, mide 4,573 px.
- Tres rondas de revisión en frío, una con otra familia de modelo, encontraron 11 errores honestos en el código nuevo: 7, después 4 y al final 1. Todos están corregidos y cubiertos por pruebas.

### Límites conocidos

- Quien escribe las cifras como en España (`1.250,5`) verá su brecha como texto, y una cifra como `4.125`, que en España son miles, se lee como decimal.
- El validador sigue siendo un poka-yoke contra errores honestos: renombrar o esconder a propósito lo atrapa la revisión en frío.

---

## [2.1.0] - 2026-11-14

### Qué agrega el Contrato 3 en el A3

El contrato 3 exige exactamente la forma de la plantilla. Lo que se le parezca sin coincidir para la línea (`[PARAR LÍNEA]`), y el mensaje muestra la forma correcta.

- **Línea Contrato:** la etiqueta va exactamente así: `- **Contrato:** 3`, y es la puerta del contrato, así que estas reglas paran la línea en cualquier A3:
  - una etiqueta de la cabecera que contiene "contrato" o se le parece por una errata (`- Contrato: 3`, `- **Contato:** 3`, `- **Versión del contrato:** 3`), también si la línea está comentada o dentro de un bloque de código de la cabecera;
  - dos líneas Contrato;
  - un A3 sin línea Contrato que trae rasgos del contrato 3 (un encabezado de tabla con `Paso` y `Fuente`, o una `(base:` en una predicción): "falta - **Contrato:** 3". El título del mapa solo no es rasgo, porque los A3 de contrato 1 y 2 también lo usan.
  El valor lo sigue juzgando la comprobación de contratos existentes (`- **Contrato:** tres` dice que ese contrato no existe). La salida dice siempre qué contrato usó y de dónde lo sacó.
- **Mapas obligatorios:** el mapa presente es obligatorio desde la etapa `comprender` y el futuro desde `proponer`, uno por sección, con una sola tabla bajo su título y nunca fuera de las secciones 2 y 5 (ni en la cabecera ni en una sección extra). Los únicos títulos son `### Mapa del estado presente`, en la sección 2, y `### Mapa del estado futuro`, en la sección 5. Debajo va una tabla con exactamente el encabezado `| Paso | Quién | Tiempo | Problema | Fuente |`; puede haber prosa entre el título y la tabla. Un título que se les parezca (otro nivel, numeración, otra redacción, negrita o cita), un título en la sección que no le toca, o una tabla con columnas `Paso` y `Fuente` fuera de esos títulos para la línea.
- **Columna Fuente de los mapas:** en el mapa presente, una de las cuatro formas verificables (`ruta:N` o `ruta:N-M`, `` `comando` -> ruta ``, `https://...` o `evidencia: ruta`) o `[SIN MEDIR]`, que solo vale hasta la etapa `analizar`; desde `proponer` para la línea. En el mapa futuro, una de las cuatro formas o exactamente una `(base: de dónde sale)` sola en la celda.
- **Base en cada predicción (`base_prediccion: "toda"`):** toda opción con `Predicción` escrita, sea su decisión `elegida`, `después` o `descartada`, declara al menos una base con la forma única `(base: texto)`: el paréntesis, `base:` en minúsculas pegado a él, el texto en texto plano (sin cursivas, negritas, tachado, comillas invertidas, HTML, imágenes, enlaces ni barras de escape) y el paréntesis que cierra; se admiten paréntesis anidados si están balanceados. Cualquier otra forma de escribir `base:` para la línea con "escribe la base así: (base: de dónde sale)". `línea base` es prosa y no cuenta como base.
- **Qué texto de base no vale:** el vacío, el relleno (`-`, `--`, `pendiente`, `por definir`, `por medir`, `por confirmar`, `sin fuente`, `ninguna`, `n/a`, `no aplica`, `a definir`, `por determinar`, `por estimar`, `sin dato`, `sin base`, `xx`, `idem` y los demás de la lista, con sus plurales y femeninos) y el que empieza con una marca de dato no medido (`[SIN MEDIR]`, `sin medir`, `sin medida`, `sin medición`, `no medido`, `aún sin medir`, `todavía sin medir` o `se medirá`). Tampoco valen los textos de ejemplo de la plantilla y de los mensajes (`de dónde sale`, `texto`, `medición o supuesto`): quien los deja sin cambiar no dijo de dónde sale la cifra. Se compara en minúsculas, sin tildes y sin puntuación.
- **Filas de tabla:** toda fila va con `|` al principio y al final, dentro de una tabla con encabezado y separador. Una fila fuera de tabla (tras una línea en blanco, tras una línea sin barras o dentro de una cita), o una línea con barras pegada a una tabla sin las barras de los extremos, para la línea. Los bloques de código se reconocen como en GFM: una cerca empieza la línea y no lleva otra comilla invertida detrás. En la sección 5, toda tabla que empiece con `Opción` lleva exactamente las columnas de opciones del contrato.
- **Fuentes en un A3 de contrato 3:** `https://` exige un servidor con al menos un punto y una terminación de letras (`https://x` se rechaza), y una fuente que apunta al mismo A3 que se valida se rechaza por autocita. En el contrato 2 estas dos reglas no se aplican, para que valide igual que en la 2.0.0.

### Compatibilidad y adopción

- **Contratos anteriores:** los A3 con `- **Contrato:** 1` (o sin línea `Contrato`) y con `- **Contrato:** 2` siguen validando y dibujándose igual que en la versión 2.0.0.
- **Plantilla y ejemplo:** `skills/a3/references/contrato-a3.json` fija `"vigente": 3`; `skills/a3/resources/plantilla-a3-interno.md` y `skills/a3/resources/ejemplo-a3.md` nacen con `- **Contrato:** 3`, mapas de cinco columnas con `Fuente` y predicciones con `base:`. `skills/a3/SKILL.md` y `docs/manual.md` documentan estas reglas.

### Medida verificada

- Al validar con `- **Contrato:** 3` el A3 de prueba de la fase 1, `validar-a3.py` bloquea sus **3 hallazgos sin respaldo** (incluidos los tiempos de los dos mapas y la predicción sin `base:` que escapaban en contrato 2), frente a **2 de 3** bloqueados con el contrato 2.
- Antes de publicar, revisiones en frío del lector, una con otra familia de modelo, encontraron formas de escribir lo mismo que se escapaban. Tolerar cada variante no convergía (8 casos corregidos dieron paso a 11 nuevos), y el contrato 3 pasó a exigir una sola forma. Con la forma única, lo que quedaba abierto era la puerta: un mapa o una línea Contrato tan distintos que el validador no los reconocía. Por eso los mapas pasaron a ser obligatorios y la línea Contrato se vigila. Todos esos casos paran ahora la línea y están cubiertos por pruebas.

### Límites conocidos

- La lista de relleno es finita: un sinónimo que no esté en ella pasa, y un texto de base real pero vago también. Lo atrapa la revisión en frío del A3 (skill `ojos-frescos`), no el validador.
- El validador no abre la red: una dirección `https://` bien formada pero inventada pasa.
- Con `--etapa`, manda la etapa pedida aunque sea anterior a la de la cabecera: un `[SIN MEDIR]` pasa con aviso y salida 0.
- El validador es un poka-yoke contra errores honestos de quien copia la plantilla, no una barrera contra quien quiere esquivarlo a propósito (renombrar, esconder o reescribir una sección para que no se reconozca). Eso lo atrapa la revisión en frío.

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
