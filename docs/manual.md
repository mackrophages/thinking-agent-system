# Manual de TAS (Thinking Agent System)

Este manual es para quien instala TAS por primera vez y quiere usarlo en su trabajo de todos los días. No hace falta haber leído nada antes. Va de lo simple a lo completo: qué es, cómo se instala, un caso entero de principio a fin, cada pieza por separado y qué hacer cuando algo falla.

Los bloques de comandos marcados como ejecutables se probaron de verdad contra la versión 2.2.0. Corren tal cual, en una carpeta vacía, si defines antes la variable `TAS_REPO`.

## 1. Qué es TAS y qué cambia al instalarlo
TAS (*Thinking Agent System*) es un plugin libre en español para agentes de código (Claude Code, Antigravity y OpenCode). Le enseña al agente a trabajar con el método Lean AgentOps: parar cuando algo falla, ir a mirar el lugar real antes de afirmar, pensar en una página antes de construir y dejar por escrito lo que se aprendió.

Al instalarlo cambian tres cosas:
1. **El agente arranca con reglas siempre activas.** Son un archivo corto (`rules/AGENTS.md`) que se carga entero en cada sesión. Las que más notarás:
   - **Gemba antes de afirmar:** no dice "está listo" sin haberlo visto en el lugar real (la salida de un comando, el archivo abierto, la página renderizada); lo que no pudo comprobar lo marca `[SIN CONFIRMAR]`.
   - **Andon al tercer fallo:** si una herramienta falla tres veces seguidas, se detiene y te llega con hechos y opciones.
   - **Nada oculto:** no comenta pruebas que fallan ni debilita aserciones, y nombra lo que falló y lo que quedó fuera.
   - **Se culpa al proceso, no a la persona ni al agente**, y la entrega empieza por si se cumplió el criterio de aceptación.
2. **El agente gana siete skills.** Un skill es un procedimiento que el agente carga cuando la tarea lo pide (sección 4).
3. **El agente gana cuatro revisores y un observador.** Los revisores leen en frío lo que escribió el agente (sección 5). El observador mide el flujo de trabajo sin interrumpirlo (sección 6).

### Qué hace cada pieza
- **Reglas siempre activas:** fijan la conducta básica; se cargan solas en cada sesión.
- **`gemba`:** ir al lugar real antes de afirmar. **`5-porques`:** llegar a la causa raíz de un fallo. **`a3`:** pensar un problema no trivial en una página. **`ojos-frescos`:** hacer revisar lo escrito a alguien sin sesgo. **`kaizen`:** llevar compromisos de mejora y cerrarlos con reflexión. **`agent-ops`:** estándar de trabajo del agente y formato de encargo. **`goldfish-observer`:** tablero de corridas y jugadas.
- **Cuatro revisores:** leen en frío un A3, una cifra o un diagnóstico cuando se los invoca.
- **Observador:** sensor silencioso que registra el trabajo, solo en proyectos donde lo activas (tiene `.tas/`).

Dos nombres que verás seguido: el **Elefante** es el agente que trabaja (memoria larga) y el **Goldfish** es el observador (no recuerda nada, por eso mira sin prejuicio). Las métricas del observador auditan el proceso y el entorno; nunca castigan al agente.

## 2. Instalación y comprobación
En los ejemplos, `<ruta-a-tas>` es la carpeta donde clonaste o copiaste el plugin. Los comandos ejecutables usan la variable `TAS_REPO`; defínela una vez en tu terminal:
```bash
export TAS_REPO=<ruta-a-tas>
```

### 2.1 En Claude Code
Con el catálogo local (queda instalado para siempre):
```bash
claude plugin marketplace add <ruta-a-tas>
claude plugin install tas@tas
```
Solo para una sesión, sin instalar nada: `claude --plugin-dir <ruta-a-tas>`. Antes de instalar puedes pedirle a Claude Code que revise que la carpeta es un plugin válido:
<!-- ejecutable -->
```bash
claude plugin validate "$TAS_REPO"
```
Salida esperada: `Validation passed`. Los skills se invocan con el prefijo del plugin (`/tas:a3`, o `tas:a3`) y los revisores también (`tas:critico-causa-raiz`).

### 2.2 En Antigravity
Antigravity expone cada skill con el campo `name` de su `SKILL.md`, sin anteponer el nombre del plugin. Por eso se instala una copia generada en `~/.gemini/config/plugins/tas` (o en `.agents/plugins/tas` si es solo para un proyecto) con carpetas `tas-*` y rutas internas reescritas:
```bash
mkdir -p ~/.gemini/config/plugins
DEST_PLUGIN="$HOME/.gemini/config/plugins/tas"  # o .agents/plugins/tas por proyecto
rm -rf "$DEST_PLUGIN" && mkdir -p "$DEST_PLUGIN/skills"
cp -r "$TAS_REPO/plugin.json" "$TAS_REPO/hooks.json" "$TAS_REPO/LICENSE" "$TAS_REPO/README.md" \
      "$TAS_REPO/rules" "$TAS_REPO/agents" "$TAS_REPO/scripts" "$DEST_PLUGIN/"
for s in a3 5-porques agent-ops gemba goldfish-observer kaizen ojos-frescos; do
  cp -r "$TAS_REPO/skills/$s" "$DEST_PLUGIN/skills/tas-$s"
  sed -i "s/^name: $s\$/name: tas-$s/" "$DEST_PLUGIN/skills/tas-$s/SKILL.md"
done
python3 - "$DEST_PLUGIN" <<'PY'
import pathlib, sys
root, skills = pathlib.Path(sys.argv[1]), ("a3", "5-porques", "agent-ops", "gemba", "goldfish-observer", "kaizen", "ojos-frescos")
for p in [root / "rules/AGENTS.md", *root.glob("agents/*.md"), *root.glob("skills/tas-*/**/*.md")]:
    txt = p.read_text(encoding="utf-8")
    for s in skills: txt = txt.replace(f"skills/{s}/", f"skills/tas-{s}/").replace(f"`{s}`", f"`tas-{s}`")
    p.write_text(txt, encoding="utf-8")
PY
agy plugin validate "$DEST_PLUGIN"
```

### 2.3 En OpenCode
No hay instalador de plugins; se generan copias `tas-*` junto con `scripts/` (que importa `observer_cli.py`). Para todos los proyectos, instala en `~/.config/opencode/skills` y `~/.config/opencode/AGENTS.md`:
```bash
DEST_OC="$HOME/.config/opencode"
mkdir -p "$DEST_OC/skills" "$DEST_OC/scripts" && rm -rf "$DEST_OC"/skills/tas-*
cp -r "$TAS_REPO/scripts/." "$DEST_OC/scripts/"
for s in a3 5-porques agent-ops gemba goldfish-observer kaizen ojos-frescos; do
  cp -r "$TAS_REPO/skills/$s" "$DEST_OC/skills/tas-$s"
  sed -i "s/^name: $s\$/name: tas-$s/" "$DEST_OC/skills/tas-$s/SKILL.md"
done
{ printf '<!-- TAS v2.2.0: reglas siempre activas, copia de rules/AGENTS.md del plugin -->\n\n'
  cat "$TAS_REPO/rules/AGENTS.md"; } > "$DEST_OC/AGENTS.md"
python3 - "$DEST_OC" <<'PY'
import pathlib, sys
root, skills = pathlib.Path(sys.argv[1]), ("a3", "5-porques", "agent-ops", "gemba", "goldfish-observer", "kaizen", "ojos-frescos")
for p in [root / "AGENTS.md", *root.glob("skills/tas-*/**/*.md")]:
    txt = p.read_text(encoding="utf-8")
    for s in skills: txt = txt.replace(f"skills/{s}/", f"skills/tas-{s}/").replace(f"`{s}`", f"`tas-{s}`")
    p.write_text(txt, encoding="utf-8")
PY
```
Para un solo proyecto, copia en `.opencode/skills`, `.opencode/agents` y `.opencode/scripts`, y apunta `instructions` a `reglas-tas.md` en `opencode.json`:
```bash
mkdir -p .opencode/skills .opencode/agents .opencode/scripts && rm -rf .opencode/skills/tas-*
cp -r "$TAS_REPO/scripts/." .opencode/scripts/ && cp "$TAS_REPO"/agents/*.md .opencode/agents/
for s in a3 5-porques agent-ops gemba goldfish-observer kaizen ojos-frescos; do
  cp -r "$TAS_REPO/skills/$s" ".opencode/skills/tas-$s"
  sed -i "s/^name: $s\$/name: tas-$s/" ".opencode/skills/tas-$s/SKILL.md"
done
cp "$TAS_REPO/rules/AGENTS.md" reglas-tas.md
python3 - <<'PY'
import pathlib
skills = ("a3", "5-porques", "agent-ops", "gemba", "goldfish-observer", "kaizen", "ojos-frescos")
for p in [pathlib.Path("reglas-tas.md"), *pathlib.Path(".opencode/agents").glob("*.md"), *pathlib.Path(".opencode/skills").glob("tas-*/**/*.md")]:
    txt = p.read_text(encoding="utf-8")
    for s in skills: txt = txt.replace(f"skills/{s}/", f".opencode/skills/tas-{s}/").replace(f"`{s}`", f"`tas-{s}`")
    p.write_text(txt, encoding="utf-8")
PY
```
```json
{ "$schema": "https://opencode.ai/config.json", "instructions": ["reglas-tas.md"] }
```
Lo comprobado: `opencode debug skill` lista los siete skills `tas-*`, `opencode debug agent lector-primera-visita` reconoce al revisor y `opencode debug config` muestra las reglas cargadas. Lo que no hay: hooks para OpenCode (el sensor del observador no corre solo; el tablero se alimenta a mano, sección 6) y solo lectura para el revisor copiado (pídele en el encargo que no edite nada).

### 2.4 Cómo saber que quedó cargado
Ver el plugin en la lista no alcanza: puede estar instalado y no haber inyectado sus reglas. La prueba es preguntarle al agente algo que solo sabe si las reglas están cargadas. Abre una sesión nueva y pregunta:
> ¿Cuál es el tope de bytes del archivo de reglas siempre activas?

Si está cargado, contesta **6.374 bytes** (es la última línea del archivo de reglas). Si dice que no lo sabe o inventa una cifra, las reglas no se cargaron: ve a "Problemas frecuentes". Puedes comprobar lo mismo sin agente:
<!-- ejecutable -->
```bash
peso=$(wc -c < "$TAS_REPO/rules/AGENTS.md")
echo "reglas: $peso bytes (tope 6374)"
test "$peso" -le 6374
echo '{}' | python3 "$TAS_REPO/scripts/session_start_rules.py" | grep -c "6.374"
```
Ese script (`scripts/session_start_rules.py`) es el hook `SessionStart` de Claude Code (`hooks/hooks.json`), que corre al iniciar, reanudar, limpiar o compactar la conversación. Antigravity carga `rules/AGENTS.md` de forma nativa al abrir sesión (su `hooks.json` solo registra `PostToolUse` y `Stop`) y OpenCode lee `~/.config/opencode/AGENTS.md` o `instructions` de `opencode.json`. En las tres plataformas, si instalas con la sesión abierta, hay que abrir otra.

## 3. Un caso completo, de principio a fin
Un problema inventado pero realista, que recorre las piezas en el orden en que se usan. Trabaja en una carpeta vacía; todos los comandos asumen que estás dentro de ella.
**La situación.** Una tienda en línea exporta sus pedidos del día a `pedidos.csv`. Un script, `resumen.py`, suma los totales y contabilidad cierra el día con esa cifra. Hoy el resumen dice 4 pedidos y el archivo tiene 6.

### 3.1 El fallo
Creamos el archivo y el script tal como están hoy, guardando la salida real en `salida-resumen.txt`:
<!-- ejecutable -->
```bash
cat > pedidos.csv <<'EOF'
id,cliente,total
101,Ferretería Norte,45.00
102,Café del Valle,"12,50"
103,Librería Sur,30.00
104,Taller Central,"1.250,00"
105,Panadería Luz,25.00
106,Vivero Sol,30.50
EOF
cat > resumen.py <<'EOF'
import csv, sys
pedidos, suma = 0, 0.0
with open(sys.argv[1], newline="", encoding="utf-8") as f:
    for fila in csv.DictReader(f):
        try:
            suma += float(fila["total"])
            pedidos += 1
        except (ValueError, TypeError):
            continue
print(f"Pedidos: {pedidos}\nTotal: {suma:.2f}")
EOF
{ time -p python3 resumen.py pedidos.csv; } > salida-resumen.txt 2> tiempo-resumen.txt
{ time -p tail -n +2 pedidos.csv | wc -l; } > filas.tmp 2> tiempo-conteo.txt
echo "Filas de datos en el archivo: $(cat filas.tmp)" >> salida-resumen.txt
rm -f filas.tmp && cat salida-resumen.txt tiempo-resumen.txt
```
Imprime `Pedidos: 4` y `Total: 130.50`, con 6 filas de datos. El script terminó sin error y dio una cifra, pero está corta. Esa es la peor clase de fallo: no avisa.

### 3.2 Parar y preguntar por qué (`5-porques`)
Aquí entra la regla "parar para arreglar". No se corrige todavía; primero se entiende. Se le pide al agente: "usa `5-porques` con este fallo" (`/tas:5-porques` en Claude Code, `tas-5-porques` en Antigravity u OpenCode). Lo primero que hace es separar lo **verificado** de lo **supuesto** mirando el lugar real:
<!-- ejecutable -->
```bash
grep -n "try:" -A4 resumen.py
grep -n '"' pedidos.csv
```
Hechos verificados: en `resumen.py` (líneas 6 a 10) el `except` salta la fila sin decir nada, y en `pedidos.csv` (líneas 3 y 5) los pedidos con `id` `102` y `104` traen la coma como separador decimal (`12,50`) o punto de miles (`1.250,00`). Con eso, la cadena de porqués queda así:
```markdown
- Síntoma verificado: el resumen cuenta 4 de 6 pedidos y sale con código 0.
  - 1. ¿Por qué cuenta 4? -> los pedidos 102 y 104 (líneas 3 y 5 de `pedidos.csv`) caen en el `except` y se saltan.
  - 2. ¿Por qué nadie se entera? -> el `except` hace `continue` sin contar ni imprimir.
  - 3. ¿Por qué ese diseño pasó? -> el estándar del resumen termina al imprimir y no lleva conteo de control.
  - Por lo tanto: sin conteo de control -> el `except` silencioso -> el resumen sale corto sin aviso.
```
La **curita** tentadora sería cambiar la coma por punto dentro del script: tapa el síntoma de hoy y deja vivo el mecanismo que calla los errores. La contramedida de raíz es que el resumen deje de callar, y el **poka-yoke** es una prueba que falle si las cuentas no cuadran. Como hay más de una causa posible y el arreglo no es trivial, esto merece un A3.

### 3.3 El A3, etapa por etapa (`a3`)
El A3 no se llena de golpe: se avanza por etapas y cada una se revisa con el coach (quien pregunta, no escribe). Para un A3 propio se parte de `skills/a3/resources/plantilla-a3-interno.md`, que ya trae los títulos exactos que exige `validar-a3.py` (con tope de 160 líneas no vacías para que quepa en una página) y la línea `- **Contrato:** 3` en la cabecera (los A3 con contrato `2` o sin línea `Contrato`, que usa el `1`, siguen validando igual). Con el contrato `3`, cada hecho de la sección 2 y cada fila `**Verificado**` de la sección 4 debe citar fuentes que se puedan abrir en una de **cuatro formas** (o varias separadas por `;` fuera de comillas invertidas): `ruta:N` o rango `ruta:N-M`, `` `comando` -> ruta ``, `https://...` o `evidencia: ruta` (relativas a la carpeta del A3 o a la raíz del proyecto con `.git` o `--raiz`); además, la Brecha exige su indicador delante (`- **Brecha:** <indicador>: de <actual> (medido) a <meta> (meta) para <cuándo>`) y apenas la Brecha tiene contenido real el título la nombra con su indicador y su meta (`# A3: <indicador>: de <actual> a <meta>`; antes de eso el título es libre), van los mapas de estado presente (sec. 2, desde `comprender`) y futuro (sec. 5, desde `proponer`) con columna `Fuente` y estallidos kaizen `[A]` enlazados con las causas de `4b`, cada predicción de la sección 5 declara su `base:`, y el validador avisa sin parar si se pasan los topes de `30` palabras por celda, `40` por viñeta o `1500` en total. Etapa 1, **comprender**: solo contexto y hechos medidos.

<!-- ejecutable -->
```bash
cat > a3-resumen.md <<'EOF'
# A3: pedidos descartados en silencio: de 2 de 6 a 0 de 6
- **Propietario:** agente de la tienda en línea
- **Coach / Revisor:** responsable de contabilidad
- **Versión:** 1 (2026-11-12)
- **Etapa:** comprender
- **Contrato:** 3

## 1. Contexto y Desperdicio (Muda) Observado
- **Por qué importa ahora:** contabilidad cierra el día con el total de `resumen.py`; un total corto se descubre al conciliar con el banco, días después.
- **Desperdicio observado:** defecto oculto; el resumen sale con código 0 aunque descarte pedidos.
- **Pregunta cero:** el resumen no se puede eliminar, porque contabilidad cierra con él; "no construir" queda descartado.

## 2. Estado Actual en el Gemba
| Hecho medido | Fuente |
| :--- | :--- |
| `pedidos.csv` tiene 6 pedidos y el resumen cuenta 4 | `python3 resumen.py pedidos.csv` -> salida-resumen.txt; `tail -n +2 pedidos.csv \| wc -l` -> salida-resumen.txt |
| Los pedidos 102 y 104 no se suman: sus totales son `12,50` y `1.250,00` | pedidos.csv:3; pedidos.csv:5 |
| El total informado es 130.50 y la suma real es 1393.00 | salida-resumen.txt:2; pedidos.csv:2-7 |
- **Brecha:** pedidos descartados en silencio: de 2 de 6 (medido) a 0 de 6 (meta) para el 2026-11-20

### Mapa del estado presente
| Paso | Quién | Tiempo | Problema | Fuente |
| :--- | :--- | :--- | :--- | :--- |
| Exportar `pedidos.csv` | tienda en línea | diario | entran totales con coma decimal | pedidos.csv:3; pedidos.csv:5 |
| Leer y sumar `pedidos.csv` | `resumen.py` | real en archivo | salta totales con coma sin avisar | tiempo-resumen.txt:1; resumen.py:6-10 |
| Contar filas contra resumen | cierre diario | real en archivo | solo miraba código 0 sin cotejar | tiempo-conteo.txt:1; salida-resumen.txt:1-3 |

## Siguientes pasos
- Pasar a la etapa analizar: meta, Ishikawa y porqués con el coach.
EOF
python3 "$TAS_REPO/skills/a3/scripts/validar-a3.py" a3-resumen.md
```
El validador `validar-a3.py` lee la etapa y el contrato de la cabecera. Sus salidas: `0` aprobado, `1` rechazado (un `[PARAR LÍNEA]` es un error de pensamiento, incluido un dato sin fuente válida o un contrato inexistente) y `2` error de uso. Un `[AVISO]` es de forma y no rechaza. Si intentas saltarte una etapa, lo dice. Aquí le pedimos que exija la etapa siguiente y esperamos que rechace:
<!-- ejecutable -->
```bash
rc=0
python3 "$TAS_REPO/skills/a3/scripts/validar-a3.py" --etapa analizar a3-resumen.md || rc=$?
test "$rc" -eq 1
```
```text
Errores de pensamiento (2), rechazan el A3:
[PARAR LÍNEA] sección 3: falta '## 3. Meta y Criterio de Aceptación'; la etapa analizar la exige
[PARAR LÍNEA] sección 4: falta '## 4. Análisis de Causa Raíz'; la etapa analizar la exige
Avisos de forma (1), no rechazan:
[AVISO] la opción --etapa (analizar) manda sobre la Etapa de la cabecera (comprender)
Resultado: RECHAZADO (2 errores de pensamiento, 1 avisos de forma).
```
Etapa 2, **analizar**: la meta y la causa raíz. Aquí van el **Ishikawa** (seis ramas: Método, Máquina, Material, Medición, Medio y Relevo; cada una queda en FOCO o DESCARTADA con su evidencia), los porqués de cada causa en foco y los estallidos kaizen `[A]`, `[B]` y `[C]` marcados al inicio de `Problema` en el paso del mapa presente donde ocurre cada causa. Quitamos el cierre anterior, subimos la etapa, marcamos los estallidos y agregamos las secciones 3 y 4:
<!-- ejecutable -->
```bash
sed -i '/^## Siguientes pasos/,$d' a3-resumen.md
sed -i 's/^- \*\*Etapa:\*\* .*/- **Etapa:** analizar/; s/^- \*\*Versión:\*\* .*/- **Versión:** 2 (2026-11-12)/' a3-resumen.md
sed -i 's/| entran totales con coma decimal |/| [B] entran totales con coma decimal |/; s/| salta totales con coma sin avisar |/| [A] salta totales con coma sin avisar |/; s/| solo miraba código 0 sin cotejar |/| [C] solo miraba código 0 sin cotejar |/' a3-resumen.md
cat >> a3-resumen.md <<'EOF'
## 3. Meta y Criterio de Aceptación
- **Meta:** el resumen cuenta los 6 pedidos del archivo, o se detiene diciendo cuáles no pudo leer.
- **Criterio de aceptación:** `verificar.py pedidos.csv` sale con 0 y el total del resumen es 1393.00 con el archivo de hoy.

## 4. Análisis de Causa Raíz
| Estado | Observación | Evidencia en Gemba o prueba pendiente |
| :--- | :--- | :--- |
| **Verificado** | El resumen descarta un pedido cuyo total no es un número y sigue sin avisar | resumen.py:6-10 |
| **Verificado** | Dos totales vienen con coma decimal o con punto de miles | pedidos.csv:3; pedidos.csv:5 |
| **Supuesto** | El formulario de la tienda deja escribir el total a mano | pendiente: abrir el formulario y probar con `12,50` |

### 4a. Ishikawa
| Rama | Hipótesis u observación | Evidencia en Gemba | Estado |
| :--- | :--- | :--- | :--- |
| Método | El resumen no se corre igual todos los días | el programador lanza el mismo comando cada noche | DESCARTADA |
| Máquina | El script traga el error y deja la cuenta corta | `resumen.py`, líneas 6 a 10 | FOCO |
| Material | Entran totales con formato distinto al esperado | líneas 3 y 5 de `pedidos.csv` (pedidos 102 y 104) | FOCO |
| Medición | Nada compara pedidos leídos contra filas del archivo | no existe prueba ni conteo de control | FOCO |
| Medio | La codificación o el idioma del sistema alteran la lectura | el archivo es UTF-8 y `float()` no usa el idioma del sistema | DESCARTADA |
| Relevo | El encargo del resumen no decía qué hacer con un total ilegible | el encargo original dice solo "sumar los totales" | DESCARTADA |

### 4b. Porqués por causa
- **Causa A (Máquina):** el script descarta pedidos sin decirlo.
  - 1. ¿Por qué el resumen cuenta 4 de 6? -> los pedidos 102 y 104 (líneas 3 y 5 de `pedidos.csv`) caen en el `except` y se saltan.
  - 2. ¿Por qué el salto no se ve? -> el `except` hace `continue` sin contar ni imprimir nada y el programa sale con 0.
  - Por lo tanto: el `except` silencioso salta los pedidos -> el programa sale con 0 -> el resumen sale corto sin aviso.
- **Causa B (Material):** el total llega en formatos distintos.
  - 1. ¿Por qué `12,50` y `1.250,00` no son números para `float()`? -> usan coma decimal y punto de miles.
  - 2. ¿Por qué entran así? -> nada fija ni valida el formato del total al entrar el pedido.
  - Por lo tanto: nada valida el formato -> entran totales con coma -> `float()` los rechaza.
- **Causa C (Medición):** ninguna prueba cuenta los pedidos.
  - 1. ¿Por qué la pérdida pasó sin verse? -> la única señal era el código de salida, siempre 0.
  - 2. ¿Por qué solo se miraba el código de salida? -> el estándar del resumen termina al imprimir y no incluye conteo de control.
  - Por lo tanto: el estándar no incluye conteo -> solo se mira el código de salida -> el resumen corto pasa sin verse.

## Siguientes pasos
- Revisar con el coach las ramas descartadas y pasar a la etapa proponer: el agente de la tienda, 2026-11-13.
EOF
python3 "$TAS_REPO/skills/a3/scripts/validar-a3.py" a3-resumen.md
```
Fíjate en dos detalles: la rama Relevo (el encargo) se revisó antes de culpar a nada más, y ninguna causa nombra a una persona ni a un agente: nombran el script, el dato y el estándar.

Etapa 3, **proponer**: las opciones. Se exigen al menos dos opciones reales y cubrir todas las causas. En la tabla de la sección 5, `validar-a3.py` comprueba el vocabulario cerrado de `skills/a3/references/contrato-a3.json`: `Nivel` (`curita`, `raíz` o `poka-yoke`), `Impacto` (`alto` o `bajo`), `Esfuerzo` (`bajo` o `alto` seguido entre paréntesis de su ventana exacta: `5 h`, `20 h`, `1 semana` o `más de 1 semana`; en `kaizen-cli.py`, en cambio, `--esfuerzo` lleva solo `bajo` o `alto`), `Cuadrante` (`Implementar`, `Desafío`, `Posible` o `Eliminar`, según impacto y esfuerzo; lo que cae en `Eliminar` no se elige) y `Decisión` (`elegida`, `después` o `descartada`).

<!-- ejecutable -->
```bash
sed -i '/^## Siguientes pasos/,$d' a3-resumen.md
sed -i 's/^- \*\*Etapa:\*\* .*/- **Etapa:** proponer/; s/^- \*\*Versión:\*\* .*/- **Versión:** 3 (2026-11-12)/' a3-resumen.md
cat >> a3-resumen.md <<'EOF'
## 5. Contramedidas y Poka-Yoke
| Opción | Causa | Nivel | Impacto | Esfuerzo | Cuadrante | Decisión | Predicción |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| O-1 El resumen cuenta lo descartado y sale con 1 si hay alguno | A | raíz | alto | bajo (5 h) | Implementar | elegida | pedidos descartados sin aviso: de 2 de 6 a 0 de 6 (base: pedidos.csv:3,5 tienen coma y resumen.py:6-10 los salta) |
| O-2 El formulario rechaza un total que no sea número con punto decimal | B | poka-yoke | alto | bajo (20 h) | Implementar | elegida | totales con coma que entran: de 2 de 6 a 0 de 6 (base: supuesto en sección 4 de validar la entrada al capturar) |
| O-3 `verificar.py` compara filas del archivo contra pedidos leídos | C | poka-yoke | alto | bajo (5 h) | Implementar | elegida | días con un resumen corto sin aviso: de 1 a 0 (base: salida-resumen.txt:1-3 muestra salida 0 con filas faltantes) |
| O-4 Cambiar la coma por punto dentro de `resumen.py` | síntoma | curita | bajo | bajo (5 h) | Posible | descartada | `1.250,00` pasa a `1.250.00` y sigue sin leerse (base: pedidos.csv:5 trae punto de miles y coma decimal) |
| O-5 Mover los pedidos a una base de datos con tipos | A | raíz | alto | alto (1 semana) | Desafío | después | totales ilegibles: de 2 de 6 a 0 de 6 (base: supuesto de esquema con columnas numéricas en base de datos) |

### Mapa del estado futuro
| Paso | Quién | Tiempo | Problema | Fuente |
| :--- | :--- | :--- | :--- | :--- |
| Sumar y fallar si descarta | `resumen.py` | similar al presente | formulario aún acepta coma | (base: tiempo-resumen.txt:1 y diseño O-1) |
| Cotejar filas al cierre | `verificar.py` | similar al conteo base | ninguno | (base: tiempo-conteo.txt:1 y diseño O-3) |

## Siguientes pasos
- Revisar las opciones con el coach y decidir cuáles pasan al plan: el agente de la tienda, 2026-11-14.
EOF
python3 "$TAS_REPO/skills/a3/scripts/validar-a3.py" a3-resumen.md
```
El A3 completo sigue con las etapas **planear** (sección 6: pasos, responsables, ventana de despliegue) y **cerrar** (sección 7: predicho contra real). En este caso paramos en proponer y pasamos a arreglar, porque el cambio es pequeño y reversible. El archivo `skills/a3/resources/ejemplo-a3.md` del plugin (junto con `skills/a3/resources/ejemplo-respaldo.log`) es un A3 cerrado en contrato 3, para ver cómo termina.

### 3.4 Ver el A3 dibujado (`dibujar-a3.py`)
El Markdown es la fuente. Para verlo con el Ishikawa y la matriz PICK dibujados según el contrato de su cabecera, se genera una página HTML de un solo archivo, sin red, que abres con el navegador. Si cambias el A3, vuelve a generarla:
<!-- ejecutable -->
```bash
python3 "$TAS_REPO/skills/a3/scripts/dibujar-a3.py" a3-resumen.md -o a3-resumen.html
head -c 80 a3-resumen.html; echo
grep -c "svg-ishikawa" a3-resumen.html
```

### 3.5 Ojos frescos
Un diagnóstico importante no se aprueba solo. El skill `ojos-frescos` pide que lo lea un revisor que no estuvo en tu razonamiento. Para este A3 corresponde `critico-causa-raiz`. La regla es no contaminarlo: el encargo lleva solo la ruta del A3, las rutas de las fuentes crudas y las rutas completas a su guía y a las preguntas del coach dentro del plugin. Por ejemplo: "Revisa /ruta/absoluta/a3-resumen.md como critico-causa-raiz. Fuentes crudas: /ruta/absoluta/resumen.py y /ruta/absoluta/pedidos.csv. Sigue `<ruta-a-tas>/agents/critico-causa-raiz.md` y `<ruta-a-tas>/skills/a3/references/preguntas-del-coach.md`."

El revisor responde con `[PARAR LÍNEA]` cuando falta evidencia y con preguntas por etapa cuando falta juicio. Al leer `a3-resumen.md`, `critico-causa-raiz` señala: *"`[PARAR LÍNEA]` En la sección 4 el formulario de la tienda figura como `Supuesto` pendiente de probar, pero la Causa B (sección 4b) y la opción `O-2` (sección 5) lo dan por hecho cierto."* Con ese freno decidimos ejecutar ahora `O-1` y `O-3` (verificadas en `resumen.py` y `pedidos.csv`) y dejar `O-2` pendiente hasta inspeccionar el formulario (lo que retoma el hansei de 3.7). Detalle de cómo invocar a cada revisor en la sección 5.

### 3.6 El arreglo: primero la prueba
La prueba de control (`verificar.py`, opción O-3) se escribe antes del cambio. Comprueba que `resumen.py` salga con código 0 y que los pedidos leídos coincidan con las filas del archivo:
<!-- ejecutable -->
```bash
cat > verificar.py <<'EOF'
import csv, subprocess, sys
ruta = sys.argv[1]
with open(ruta, newline="", encoding="utf-8") as f:
    filas = sum(1 for _ in csv.DictReader(f))
res = subprocess.run([sys.executable, "resumen.py", ruta], capture_output=True, text=True)
leidos = int(res.stdout.split("Pedidos:")[1].split()[0])
print(f"Filas en el archivo: {filas}, pedidos leídos: {leidos} (rc={res.returncode})")
sys.exit(0 if res.returncode == 0 and filas == leidos else 1)
EOF
rc=0
python3 verificar.py pedidos.csv || rc=$?
test "$rc" -eq 1
```
La prueba falla (`Filas en el archivo: 6, pedidos leídos: 4 (rc=0)`): el poka-yoke ya detecta el problema. Ahora la opción O-1: el resumen deja de callar y sale con código 1 si descartó algo.

<!-- ejecutable -->
```bash
cat > resumen.py <<'EOF'
import csv, sys
pedidos, suma, ilegibles = 0, 0.0, []
with open(sys.argv[1], newline="", encoding="utf-8") as f:
    for fila in csv.DictReader(f):
        try:
            suma += float(fila["total"])
            pedidos += 1
        except (ValueError, TypeError):
            ilegibles.append(fila["id"])
print(f"Pedidos: {pedidos}\nTotal: {suma:.2f}")
if ilegibles:
    print("No se pudo leer el total de: " + ", ".join(ilegibles), file=sys.stderr)
    sys.exit(1)
EOF
rc=0
python3 resumen.py pedidos.csv || rc=$?
test "$rc" -eq 1
```
Ahora el fallo es visible: imprime `No se pudo leer el total de: 102, 104` y sale con 1. Guardamos una copia de `pedidos.csv` con comas (`pedidos-con-error.csv`) para seguir probando el bloqueo O-1, corregimos el archivo de hoy, verificamos el criterio del A3 (`Pedidos: 6`, `Total: 1393.00`, salida 0) y cerramos corriendo la compuerta `chequeo-gemba.sh` (que inspecciona Git, JSON, UTF-8, etiquetas `[SIN CONFIRMAR]` y valores duplicados en tablas):
<!-- ejecutable -->
```bash
cp pedidos.csv pedidos-con-error.csv
sed -i 's/"12,50"/12.50/; s/"1.250,00"/1250.00/' pedidos.csv
rc=0
python3 verificar.py pedidos-con-error.csv || rc=$?
test "$rc" -eq 1
python3 resumen.py pedidos.csv | grep -F "Total: 1393.00"
python3 verificar.py pedidos.csv
bash "$TAS_REPO/skills/gemba/scripts/chequeo-gemba.sh" .
```

### 3.7 El compromiso Kaizen y el hansei
Una mejora que nadie vuelve a mirar se pierde. `kaizen` la anota como compromiso y fija tres cortes: a las 5 horas, a las 20 horas y a la semana. Primero se crea el tablero `KAIZEN.md` y se registra el compromiso de la opción O-1 con `--estado` para reflejar que ya quedó instalado. Como viene de un A3, hereda su cuadrante PICK (no se puntúa dos veces). El segundo compromiso no viene de un A3: se puntúa con `--impacto` y `--esfuerzo`, y al omitir `--estado` arranca con `0% ejecutado en el Gemba (pendiente primera ventana)` hasta que se actualice o se cierre:
<!-- ejecutable -->
```bash
KZ="$TAS_REPO/skills/kaizen/scripts/kaizen-cli.py"
python3 "$KZ" init --file KAIZEN.md --project "Tienda en línea" --meta "Cero pedidos perdidos en el resumen" --limite 5
python3 "$KZ" add-compromiso --file KAIZEN.md --id C-01 --inicio 2026-11-12T09:00 \
  --compromiso "El resumen cuenta lo descartado y sale con 1 si hay alguno" \
  --dueno "resumen.py" --a3 a3-resumen.md --opcion O-1 --estado "Instalado en resumen.py; en observación"
python3 "$KZ" add-compromiso --file KAIZEN.md --id C-02 --inicio 2026-11-12T09:00 \
  --compromiso "Correr verificar.py en cada cierre diario" --dueno "verificar.py" --impacto alto --esfuerzo bajo
```

`status` muestra los abiertos ordenados por cuadrante, su estado en el Gemba y en qué ventana va cada uno (`--now` fija la fecha de corte; sin ella usa la hora actual):
<!-- ejecutable -->
```bash
python3 "$TAS_REPO/skills/kaizen/scripts/kaizen-cli.py" status --file KAIZEN.md --now 2026-11-12T15:00
```

```text
  1. [Implementar] C-01: El resumen cuenta lo descartado y sale con 1 si hay alguno (Dueño: resumen.py)
     Estado en el Gemba: [Implementar] Instalado en resumen.py; en observación
     Progreso temporal:  [1/3] 5h cumplida -> TOCA REVISIÓN 5 HORAS
  2. [Implementar] C-02: Correr verificar.py en cada cierre diario (Dueño: verificar.py)
     Estado en el Gemba: [Implementar] 0% ejecutado en el Gemba (pendiente primera ventana)
```

Pasadas las ventanas, se mira en el lugar real si la mejora se sostuvo y se cierra con el **hansei** (la reflexión): qué funcionó y por qué, qué no funcionó y por qué. Un cierre sin reflexión no sirve:
<!-- ejecutable -->
```bash
KZ="$TAS_REPO/skills/kaizen/scripts/kaizen-cli.py"
python3 "$KZ" cerrar --file KAIZEN.md --id C-01 --date 2026-11-19T09:00 --sostenido si \
  --hansei "Funcionó: el aviso mostró los pedidos 102 y 104 al primer intento, porque ahora el resumen falla en voz alta. No funcionó: el formulario sigue aceptando comas, así que el problema se desplazó a la entrada; queda la opción O-2."
python3 "$KZ" status --file KAIZEN.md --now 2026-11-19T10:00
```

Con esto el caso queda cerrado: fallo, causa raíz, A3 validado, revisión en frío, arreglo con prueba, y una mejora anotada y reflexionada. Lo que el hansei dejó pendiente (O-2) sigue abierto como siguiente trabajo.

## 4. Cada skill
Un skill se usa de dos maneras: por su nombre ("usa `/tas:a3` para este cambio" en Claude Code, o `tas-a3` en Antigravity y OpenCode) o porque la tarea lo pide y la descripción del skill coincide (el agente lo elige solo). Todos los comandos asumen `TAS_REPO`.

### 4.1 `gemba`
- **Cuándo:** antes de diagnosticar un fallo, antes de confiar en la bitácora o el resumen de otro agente, y antes de dar algo por terminado.
- **Qué entrega:** una verificación hecha en el lugar real: procesos, datos y estado del repositorio; entregables HTML abiertos en un navegador sin red; páginas de manuales PDF renderizadas como imagen; listas de chequeo con criterio de aceptación y no solo "revisar X".
- **Comando:** `chequeo-gemba.sh [directorio-o-archivo]`. Revisa Git, JSON válidos, codificación UTF-8, marcadores `[SIN CONFIRMAR]` y valores repetidos sospechosos en tablas. Úsalo antes de entregar. Sale con 2 si la ruta no existe:
<!-- ejecutable -->
```bash
bash "$TAS_REPO/skills/gemba/scripts/chequeo-gemba.sh" .
rc=0
bash "$TAS_REPO/skills/gemba/scripts/chequeo-gemba.sh" ruta-que-no-existe 2>/dev/null || rc=$?
test "$rc" -eq 2
```

### 4.2 `5-porques`
- **Cuándo:** antes de arreglar cualquier fallo (error en producción, prueba rota, incidente).
- **Qué entrega:** tabla Verificado contra Supuesto, cadena de porqués con su "por lo tanto", contraste entre curita y raíz, y un poka-yoke. No tiene script: el agente lo escribe en su respuesta o dentro del A3. Apoyo: `references/casos-reales.md` y `references/poka-yoke-niveles.md`.

### 4.3 `a3`
- **Cuándo:** un problema no trivial (brecha medida con más de una hipótesis, o decisión difícil de revertir). Si la causa es evidente y el cambio es barato y reversible, se hace y se registra.
- **Qué entrega:** un documento de una página por etapas (`comprender`, `analizar`, `proponer`, `planear`, `cerrar`), con su vocabulario cerrado en `skills/a3/references/contrato-a3.json`.
- **Comandos y fuentes:** `validar-a3.py [--etapa ETAPA] [--raiz CARPETA] <a3.md>` y `dibujar-a3.py`. La plantilla (`resources/plantilla-a3-interno.md`, máx. 160 líneas no vacías) declara `- **Contrato:** 3`: toda fuente de la sección 2 y toda fila `**Verificado**` de la sección 4 debe usar `ruta:N` (o `ruta:N-M`), `` `comando` -> ruta ``, `https://...` o `evidencia: ruta` (separables con `;`), resueltas contra la carpeta del A3 y la raíz del proyecto (`.git` o `--raiz`). Los A3 con contrato `2` o sin línea `Contrato` (contrato `1`) siguen validando igual. Las preguntas del coach están en `references/preguntas-del-coach.md`.

En el contrato `3`, la Brecha exige su indicador delante (`- **Brecha:** <indicador>: de <actual> (medido) a <meta> (meta) para <cuándo>`), el título tiene que contener ese indicador y su meta apenas la Brecha está escrita (`# A3: <indicador>: de <actual> a <meta>`), y los dos mapas son obligatorios desde la etapa de su sección (`### Mapa del estado presente` en la sección 2 desde `comprender` y `### Mapa del estado futuro` en la sección 5 desde `proponer`), uno por sección, una sola tabla por título y nunca fuera de las secciones 2 y 5. Cada mapa lleva exactamente el encabezado `| Paso | Quién | Tiempo | Problema | Fuente |`: el mapa presente admite las cuatro formas o `[SIN MEDIR]` solo hasta `analizar` y enlaza cada **estallido kaizen** empezando `Problema` con `[X]` (letra de su causa en `4b`; desde `analizar`, un `[X]` sin causa en `4b` para la línea y una causa sin estallido avisa), el mapa futuro admite las cuatro formas o una `(base: de dónde sale)` sola en la celda (sin `[X]`, porque ya están resueltos), y toda predicción escrita en la sección 5 (sea `elegida`, `después` o `descartada`) declara al menos una `(base: texto)` en texto plano. Además, `contrato-a3.json` define `topes` de palabras para el contrato 3 (`30` por celda, `40` por viñeta y `1500` en total, sin contar bloques de código cercados), que dan aviso sin parar la línea. El contrato 3 exige la forma exacta de la plantilla: un título, un encabezado, una fila o una base que se le parezca sin coincidir para la línea, y el mensaje dice la forma correcta.
Al dibujar la Brecha, las cifras se leen con punto decimal y coma de miles en grupos de tres dígitos (`1,250.5`, `4.125`); otro formato cae a texto destacado.

### 4.4 `ojos-frescos`
- **Cuándo:** después de redactar un A3, diagnóstico, jugada, plan o tabla técnica, y antes de aprobarlo.
- **Qué entrega:** el dictamen de revisores independientes. Cuántos: ninguno o uno si el cambio es cotidiano; uno con la lente del caso si es importante; dos o más con lentes distintas si es crítico (producción, datos, algo irreversible). Sin script: se invoca a los revisores (sección 5).

### 4.5 `kaizen`
- **Cuándo:** al decidir una mejora (se anota) y en cada ventana de 5 horas, 20 horas y 1 semana (se revisa y se cierra).
- **Qué entrega:** un `KAIZEN.md` con compromisos, mejoras registradas y jugadas.
- **Comandos de `kaizen-cli.py`:** `init`, `add-compromiso` (también `add-ciclo`), `cerrar`, `status`, `add-kaizen` y `add-jugada`. Los cuatro primeros ya los usaste. Los dos que faltan:
<!-- ejecutable -->
```bash
KZ="$TAS_REPO/skills/kaizen/scripts/kaizen-cli.py"
python3 "$KZ" add-kaizen --file KAIZEN.md --proceso "resumen.py" --muda "Pedidos descartados sin aviso" \
  --poka-yoke "El resumen sale con 1 y nombra los pedidos ilegibles" --impacto "0 de 6 pedidos perdidos con el archivo corregido"
python3 "$KZ" add-jugada --file KAIZEN.md --id J-01 --flujo "Cierre diario de pedidos" \
  --presente "Resumen sin conteo de control" --futuro "Resumen que falla en voz alta y prueba de control en cada cierre"
rc=0
python3 "$KZ" add-kaizen --file KAIZEN.md --proceso "el agente" --muda "x" --poka-yoke "y" --impacto "z" 2>/dev/null || rc=$?
test "$rc" -eq 2
rc=0
python3 "$KZ" add-compromiso --file KAIZEN.md --id C-09 --compromiso "x" --dueno "el programador" --impacto alto --esfuerzo bajo 2>/dev/null || rc=$?
test "$rc" -eq 2
```

- **Reglas:** en `--proceso` (`add-kaizen`) y `--dueno` (`add-compromiso` y `add-ciclo`) va siempre un componente técnico (un script, un archivo de reglas, una prueba), nunca una persona ni un agente: `kaizen-cli.py` lo valida con la misma regla que `observer_cli.py` y, si nombras a una persona, un agente o lo dejas vacío, sale con código `2` e imprime `[PARAR LÍNEA] Violación Lean AgentOps: --proceso ('...') señala a un agente o persona. Usa siempre un componente técnico (ej. CLAUDE.md, KI System, MCP Config, Linter Hook, Skill Rule).` Hay un límite de compromisos abiertos (5 por defecto, cambia con `--limite`): `status` avisa cuando se pasa.

### 4.6 `agent-ops`
- **Cuándo:** al empezar una sesión de trabajo y al delegar a otro agente o a una persona.
- **Qué entrega:** el estándar de trabajo del agente (revisar el contexto al iniciar, explorar con índices y lecturas acotadas, Andon al tercer fallo, probar después de cada cambio), las fórmulas honestas de las métricas y el formato de **encargo y devolución** para delegar: contexto, meta, brecha, criterio de aceptación, salida esperada, qué no tocar y qué hacer si falta algo; y quien recibe responde antes de ejecutar qué entendió, cómo lo hará, cuánto cuesta y qué no es viable. Está en `references/encargo-de-delegacion.md`. Si algo delegado sale mal, se revisa primero el encargo.
- **Comandos:** ninguno propio; mide con el observador (sección 6).

### 4.7 `goldfish-observer`
Tiene su propia sección: la 6.

## 5. Los revisores
Son cuatro, cada uno con una lente. Leen en frío (sin tu historial) y en solo lectura (en Claude Code tienen únicamente `Read`, `Grep` y `Glob`). Antes de opinar abren al menos una fuente cruda.

| Revisor | Qué mira | Cuándo |
| :--- | :--- | :--- |
| `auditor-gemba` | Cifras, códigos, consultas, rutas y logs contra la fuente cruda | Tablas técnicas y reportes con métricas |
| `critico-causa-raiz` | Brecha, meta, porqués leídos con "por lo tanto", opciones reales y nivel de poka-yoke | Incidentes, A3 y arreglos importantes |
| `lector-primera-visita` | Si un A3, jugada o guía se entiende sin contexto oral | Entregas que otro va a recibir |
| `observador-goldfish` | La traza del observador, con `Who` siempre un componente | Al cerrar corridas con el observador activo |

### Cómo se invocan
- **En Claude Code:** son subagentes del plugin, con el prefijo `tas:`. Pídeselo al agente por su nombre ("revisa este A3 con `tas:critico-causa-raiz`") o invócalo como subagente con ese tipo. El encargo lleva solo tres cosas: la ruta absoluta del entregable, las rutas absolutas de las fuentes crudas y la instrucción de seguir `<ruta-a-tas>/agents/<revisor>.md` (y `<ruta-a-tas>/skills/a3/references/preguntas-del-coach.md` si revisa un A3). Tu razonamiento no va.
- **En Antigravity:** con `invoke_subagent`, con el mismo encargo de tres elementos.
- **En OpenCode:** los archivos copiados a `.opencode/agents/` quedan como agentes con el nombre del revisor (sección 2.3).

Qué hacer con la respuesta (`[PARAR LÍNEA]` o preguntas por etapa): ver 3.5. El revisor no escribe el arreglo; el autor sigue siendo dueño del problema.

## 6. El observador
El observador (Goldfish) mide el flujo del trabajo fuera de banda: no cuesta tokens ni interrumpe al agente. Registra corridas, anota problemas y dibuja un tablero. Todo vive en una carpeta `.tas/` dentro del proyecto.

### 6.1 Activarlo en un proyecto
Solo observa los proyectos donde lo activas. Sin `.tas/`, sus hooks no hacen nada:
<!-- ejecutable -->
```bash
mkdir -p sin-observador
echo '{"tool_name":"Bash"}' | python3 "$TAS_REPO/scripts/goldfish_sensor.py" --platform claude --event PostToolUse --project-dir sin-observador
test ! -d sin-observador/.tas
```
Para activarlo se corre `init` en la carpeta del proyecto:
<!-- ejecutable -->
```bash
python3 "$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py" init --project-dir . --project-name "Tienda en línea"
ls .tas
grep -qxF ".tas/active_build.json" .gitignore
```
Crea `READINESS_BOARD.md` (el tablero en Markdown), `dashboard/index.html` (el tablero en HTML), `board_state.json`, una carpeta para jugadas y asegura la línea `.tas/active_build.json` en `.gitignore`. `init` se niega a trabajar directamente en un directorio personal con salida `2` y `[PARAR LÍNEA] Poka-Yoke activado`; si de verdad lo quieres ahí, agrega `--allow-home`. Sin opciones, la referencia de tiempo por corrida es de 5 minutos y el techo acordado de 7: son valores de arranque sin respaldo. Cuando tengas unas 12 corridas medidas, recalibra con `--standard-min` y `--takt-min`.

Con el observador activo, los hooks de Claude Code (después de cada herramienta, después de un fallo de herramienta y al terminar un turno) y los de Antigravity (después de cada herramienta y al terminar un turno) alimentan el sensor solos. El sensor ignora los comandos que invocan `observer_cli.py`: así correr `add-quality-issue`, `prepare-goldfish`, `import-goldfish` o `update-board` después de `close-build` no abre una corrida fantasma (`active_build.json`) ni suma fallos de contabilidad como problemas de la corrida. OpenCode no tiene hooks del plugin.

### 6.2 Corridas
Una **corrida** (en el tablero, *Build*) es una unidad de trabajo completa, de un encargo a su entrega. Se abre y se cierra a mano:
<!-- ejecutable -->
```bash
OBS="$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py"
python3 "$OBS" start-build --project-dir . --task "Corregir el resumen de pedidos"
python3 "$OBS" close-build --project-dir . --note "Resumen corregido y verificado"
```
Al cerrar imprime el tiempo de ciclo (CT), los fallos de herramientas capturados en `gemba_trace.jsonl` durante la corrida (`Issues`) y el rendimiento a la primera (FTY). En el tablero, la cuenta de problemas de cada corrida (`Issues (Q)`) suma los de la traza más los registrados para esa corrida en `qualityLog` (con `add-quality-issue` o `import-goldfish`) sin duplicar el mismo `(build, issue)`, y una corrida con problemas pierde el trofeo de mejor corrida (`Best Score` / `🏆`). Un turno de conversación no es una corrida: el hook de fin de turno solo actualiza la corrida activa (`TAS_AUTO_CLOSE_ON_STOP=1` la cierra al terminar el turno). El tablero muestra hasta 12 corridas. Una corrida por encima de la referencia no es por sí sola un problema: solo se actúa ante una causa especial o un patrón repetido.

### 6.3 Problemas
Hay dos tipos. Los de **calidad** (la meta es cero) tienen cuatro categorías: `Wrong Parts - Supplied` (contexto o datos de entrada obsoletos), `Wrong Parts - Built` (defecto al construir), `Wrong Parts - Designed` (herramienta o esquema ambiguo) y `Missing Parts` (falta un índice, una ruta o un comando). Los de **entrega** (flujo) solo se registran ante causa especial o patrón; sus categorías son `CT > TT` y `CT > Standard`, y llevan el tipo de desperdicio (`--muda`):
<!-- ejecutable -->
```bash
OBS="$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py"
python3 "$OBS" add-quality-issue --project-dir . --build 1 --issue "5 búsquedas para hallar dónde se lee el total" --category "Missing Parts" --cm "Índice de archivos del proyecto en CLAUDE.md" --who "CLAUDE.md" --pdca 2
python3 "$OBS" add-delivery-issue --project-dir . --build 1 --issue "9.4 min (causa especial sobre el techo): lectura íntegra de un log de 4.000 líneas" --category "CT > TT" --muda "Inventario (WIP)" --cm "Acotar la lectura con offset y limit" --who "agent-ops" --pdca 3
rc=0
python3 "$OBS" add-quality-issue --project-dir . --build 1 --issue "x" --category "Missing Parts" --cm "y" --who "el agente" 2>/dev/null || rc=$?
test "$rc" -eq 2
grep -F "Pendiente (Meta: 0 Issues | CT <= Standard)" .tas/READINESS_BOARD.md
```
`--who` es siempre un componente técnico: si pones a una persona, un agente o vacío, sale con código `2` y `[PARAR LÍNEA] Violación Lean AgentOps: 'Who' ('...') señala a un agente o persona. Usa siempre un componente técnico (ej. CLAUDE.md, KI System, MCP Config, Linter Hook, Skill Rule).` Tras registrar el problema de calidad en la corrida 1, el tablero pasa `Issues (Q)` de `0` a `1`, quita el `🏆` y deja `Best Score` en `Pendiente (Meta: 0 Issues | CT <= Standard)`. En `.tas/READINESS_BOARD.md` los signos `<`, `>` y `&` se escriben sin escapes de HTML (`&lt;`, `&gt;`, `&amp;`), y solo se escapa `|` como `\|` dentro de las celdas de tabla. `--pdca` marca la etapa de la contramedida: `1` Plan, `2` Do, `3` Check y `4` Act.

### 6.4 Actualizar y abrir el tablero
Cada `close-build`, `add-quality-issue`, `add-delivery-issue` e `import-goldfish` actualiza los dos tableros; `update-board` los sincroniza a mano cuando haga falta. El tablero en Markdown es `.tas/READINESS_BOARD.md`. El visual es `.tas/dashboard/index.html`, un único archivo HTML sin conexión a internet (generado con React 19 y TanStack desde `herramientas/tablero/`, donde `update-board` inyecta `window.BOARD_DATA` dentro de `<script id="board-data-script">`):
<!-- ejecutable -->
```bash
python3 "$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py" update-board --project-dir .
test -s .tas/dashboard/index.html
grep -c 'id="raiz-tablero"' .tas/dashboard/index.html
for s in "#encabezado" "#indicadores" "#corridas" "#calidad-entrega" "#pareto" "#herramientas-lean"; do grep -q "$s" .tas/dashboard/index.html; done
```

Ábrelo con tu navegador como cualquier archivo local. La página está organizada en seis secciones con su barra de anclas:
1. **Encabezado (`#encabezado`):** título del proyecto, modo del observador, mejor corrida (`Best Score`), meta de flujo, estándar en minutos, techo acordado y enlaces a las seis vistas.
2. **Indicadores (`#indicadores`):** cuatro tarjetas con corridas hechas de 12, tiempo de ciclo (CT) mediano, corridas con 0 problemas de calidad y problemas abiertos (`PDCA < 4`).
3. **Corridas (`#corridas`):** dos gráficas SVG con TanStack Charts (CT por corrida con líneas punteadas del estándar y del techo acordado, y problemas de calidad por corrida) y las 12 tarjetas de estado (`Hecha`, `Activa`, `Lista` y `Mejor corrida`).
4. **Calidad y Entrega (`#calidad-entrega`):** dos tablas interactivas con TanStack Table (`Registro de Calidad` y `Registro de Entrega y Flujo`), ordenables por columna, filtrables por categoría y estado PDCA, con el componente responsable (`who`) y una rueda PDCA en SVG de cuatro cuartos por fila; en pantalla muestra `CT > TT` como `"CT sobre el techo acordado"` y `CT > Standard` como `"CT sobre el estándar"` sin cambiar el dato.
5. **Pareto de problemas por categoría (`#pareto`):** gráfica horizontal de barras con TanStack Charts y lista ordenada de mayor a menor frecuencia (con porcentaje e incidencia acumulada) sumando calidad y entrega.
6. **Herramientas Lean (`#herramientas-lean`):** referencia fija leída al construir desde `rules/AGENTS.md` y `skills/a3/references/contrato-a3.json`: los 14 principios en cuatro bloques, los 5 principios Lean (`Valor`, `Cadena de valor`, `Flujo`, `Pull`, `Perfección`), el Ishikawa de seis ramas, la matriz PICK, las cinco etapas del A3 y qué skill usar en cada caso.

**Para quien modifique el tablero (`herramientas/tablero/`):** no lo construyas nunca en la carpeta desde la que se instala el plugin, porque `pnpm install` crea `node_modules` y al instalar el plugin esa carpeta quedaría copiada junto a los skills. Trabaja en un clon aparte, instala las dependencias fijas con `pnpm install --frozen-lockfile`, prueba en otra ruta con `construir.mjs --salida <ruta>`, regenera `skills/goldfish-observer/resources/index.html` sin banderas y comprueba con `--comprobar` (sale con `0` si coincide byte a byte y con `1` si difiere):
<!-- ejecutable -->
```bash
mkdir -p clon-tablero/herramientas clon-tablero/rules clon-tablero/skills/a3/references clon-tablero/skills/goldfish-observer/resources
cp -r "$TAS_REPO/herramientas/tablero" clon-tablero/herramientas/
cp "$TAS_REPO/rules/AGENTS.md" clon-tablero/rules/
cp "$TAS_REPO/skills/a3/references/contrato-a3.json" clon-tablero/skills/a3/references/
cp "$TAS_REPO/skills/goldfish-observer/resources/index.html" clon-tablero/skills/goldfish-observer/resources/
pnpm --dir clon-tablero/herramientas/tablero install --frozen-lockfile >/dev/null
node clon-tablero/herramientas/tablero/construir.mjs --salida clon-tablero/prueba.html
test -s clon-tablero/prueba.html
node clon-tablero/herramientas/tablero/construir.mjs >/dev/null
node clon-tablero/herramientas/tablero/construir.mjs --comprobar
```

### 6.5 Jugadas
Una **jugada** rediseña un flujo: describe el estado presente (con su tiempo, su rendimiento y su desperdicio) y el estado futuro con el poka-yoke que lo sostiene. Mientras `kaizen-cli.py add-jugada` (sección 4.5) anota una fila resumida en `KAIZEN.md`, `observer_cli.py create-jugada` crea el documento VSM completo en `.tas/jugadas/`:
<!-- ejecutable -->
```bash
python3 "$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py" create-jugada --project-dir . --id J-02 \
  --flujo "Cierre diario de pedidos" --ct-presente "9 min" --fty-presente "70%" --muda-presente "Reproceso por pedidos descartados" --problema "Nada cuenta lo descartado" --poka-yoke "verificar.py en cada cierre"
ls .tas/jugadas
```

### 6.6 Analizar una conversación
`observer_cli.py analyze-transcript --transcript <sesion.jsonl>` lee el archivo de una sesión y calcula, fuera de banda, el rendimiento a la primera (FTY), el tiempo, la relación de contexto inflado (CBR) y la eficiencia del proceso (PCE). Cuando los hooks del sensor están activos, la ruta del transcript queda anotada en `.tas/gemba_trace.jsonl` (`transcript_path`). Acepta `--format markdown` (por defecto) o `--format json`. Si el archivo indicado no existe, sale con código `1` e imprime `[PARAR LÍNEA] No existe el archivo: ...` (o `"available": false` en JSON) sin inventar cifras:
<!-- ejecutable -->
```bash
OBS="$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py"
rc=0
python3 "$OBS" analyze-transcript --transcript no-existe.jsonl 2>/dev/null || rc=$?
test "$rc" -eq 1
```

### 6.7 Quién observa: los tres niveles y el despacho remoto
| Nivel | Quién observa | Cuándo |
| :--- | :--- | :--- |
| 0 | El sensor y el CLI, sin costo | Siempre que exista `.tas/` |
| 1 | Un revisor remoto que tú configuras | Si defines la variable `TAS_GOLDFISH_DESPACHO` |
| 2 | El subagente local `observador-goldfish` | Si no defines esa variable |

`prepare-goldfish` arma el encargo para el observador y escribe `.tas/encargo_goldfish.md`. Solo lleva la traza cruda, sin la opinión del agente. Sin configuración, indica usar el subagente local:
<!-- ejecutable -->
```bash
python3 "$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py" prepare-goldfish --project-dir .
test -s .tas/encargo_goldfish.md
```

Para el despacho remoto se usan **dos variables de entorno**:

- `TAS_GOLDFISH_DESPACHO`: la plantilla del comando que envía el encargo a tu revisor remoto, con `{encargo}` y `{artefacto}` como huecos.
- `TAS_GOLDFISH_ARTEFACTO`: la ruta donde el revisor escribirá su JSON. Si falta, se usa `.tas/goldfish-board.json`. La opción `--artefacto` manda sobre la variable.
- **Nota de compatibilidad (una versión):** cuando falta o está vacía una variable `TAS_*`, se lee la anterior (`LEAN_PROJECT_DIR`, `LEAN_STANDARD_MIN`, `LEAN_TAKT_MIN`, `LEAN_AUTO_CLOSE_ON_STOP`, `LEAN_GOLDFISH_DESPACHO` y `LEAN_GOLDFISH_ARTEFACTO`); las carpetas `.lean_observer/` existentes siguen funcionando y `observer_cli.py init` las migra a `.tas/` si no hay corrida abierta (`active_build.json`).

El comando de ejemplo `revisor-remoto` es inventado: pon el tuyo. `prepare-goldfish` **imprime** el comando ya con los huecos llenos; no lo ejecuta, lo copias y lo corres tú:
<!-- ejecutable -->
```bash
export TAS_GOLDFISH_DESPACHO='revisor-remoto enviar {encargo} {artefacto}'
export TAS_GOLDFISH_ARTEFACTO="$PWD/salida/goldfish.json"
OBS="$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py"
python3 "$OBS" prepare-goldfish --project-dir . | grep "revisor-remoto enviar"
python3 "$OBS" prepare-goldfish --project-dir . --artefacto "$PWD/otro.json" | grep -c "otro.json"
```

El revisor escribe un JSON con las listas `qualityLog` y/o `deliveryLog`, y `import-goldfish --project-dir . --artefacto <ruta.json>` lo importa al tablero. Valida cada fila con las mismas reglas que `add-quality-issue` y `add-delivery-issue` (`build` entero desde 1, categoría válida, `pdca` 1 a 4 y `who` componente técnico), agrega sin duplicar `(build, issue)`, actualiza ambos tableros, sale con `0` e imprime `[OK] Importado del revisor: X de calidad (Y ya estaban); W de entrega (Z ya estaban); R rechazadas.` listando debajo las filas rechazadas y su motivo. Si el archivo aún no existe, sale con `0` y `[AVISO] El revisor aún no escribió <ruta>: no hay nada que importar.`; si el JSON es inválido o no trae un objeto con las listas `qualityLog` y/o `deliveryLog`, sale con `2` y `[PARAR LÍNEA] <ruta> debe ser un objeto JSON con las listas qualityLog y/o deliveryLog.` (y si falta `.tas/`, sale con `1`):
<!-- ejecutable -->
```bash
OBS="$TAS_REPO/skills/goldfish-observer/scripts/observer_cli.py"
python3 "$OBS" import-goldfish --project-dir . --artefacto aun-no-existe.json | grep -F "[AVISO] El revisor aún no escribió"
echo '{}' > malo.json
rc=0
python3 "$OBS" import-goldfish --project-dir . --artefacto malo.json 2>/dev/null || rc=$?
test "$rc" -eq 2
cat > respuesta-revisor.json <<'EOF'
{"qualityLog": [
  {"build": 1, "issue": "5 búsquedas para hallar dónde se lee el total", "category": "Missing Parts", "cm": "Índice en CLAUDE.md", "who": "CLAUDE.md", "pdca": 2},
  {"build": 1, "issue": "Lectura sin fijar codificación", "category": "Wrong Parts - Built", "cm": "Fijar UTF-8 al abrir CSV", "who": "resumen.py", "pdca": 2},
  {"build": 1, "issue": "Fallo atribuido a alguien", "category": "Missing Parts", "cm": "Nada", "who": "el agente", "pdca": 1}
], "deliveryLog": []}
EOF
python3 "$OBS" import-goldfish --project-dir . --artefacto respuesta-revisor.json | grep -F "[OK] Importado del revisor: 1 de calidad (1 ya estaban); 0 de entrega (0 ya estaban); 1 rechazadas."
```

## 7. Las reglas siempre activas y su presupuesto
`rules/AGENTS.md` se carga entero en cada sesión, en todos los proyectos, todas las veces. Lo paga cada agente. Por eso tiene un presupuesto: **6.374 bytes** como máximo. No es un adorno: un archivo de reglas más largo desplaza atención de la tarea.
Cómo cambiarlas sin que engorden:
1. **Mide antes y después.** Se mide con `wc -c`, no con el número de líneas.
2. **Toda adición se compensa con una reducción** igual o mayor. Quien agrega una línea quita otra.
3. **Siempre activo es solo lo que se hace siempre.** Lo que sirve a veces va a un skill o a su carpeta `references/`, que se carga a pedido.
4. **Cada regla es una contramedida:** debe poder decirse qué condición atiende. Si deja de mover algo, se retira.
5. **Las descripciones de los skills también se cargan.** Mantenlas cortas. Si el margen sale negativo, la regla no cabe: quita otra o muévela a un skill.

Simulación de agregar una regla, sobre una copia (nunca sobre el original):
<!-- ejecutable -->
```bash
cp "$TAS_REPO/rules/AGENTS.md" reglas-copia.md
antes=$(wc -c < reglas-copia.md)
printf -- '- **15. Regla de ejemplo:** una línea nueva que ocupa lugar.\n' >> reglas-copia.md
despues=$(wc -c < reglas-copia.md)
echo "antes: $antes bytes, después: $despues bytes, tope: 6374, margen: $((6374 - despues))"
test "$despues" -le 6374
```

## 8. Problemas frecuentes
| Qué pasa | Por qué | Arreglo |
| :--- | :--- | :--- |
| El plugin está en la lista, pero el agente no sabe el tope de bytes | Las reglas se inyectan al iniciar la sesión; la sesión se abrió antes de instalar | Abre una sesión nueva. En Claude Code, `claude plugin validate <ruta-a-tas>` descarta una carpeta dañada |
| `init` sale con 2 y dice "Poka-Yoke activado" | Intentaste activar el observador directamente en un directorio personal | Entra a la carpeta del proyecto, o pasa `--allow-home` si es intencional |
| El observador no registra nada | El proyecto no tiene `.tas/`, y sin ella los hooks no hacen nada; o el plugin no tiene hooks en tu plataforma (OpenCode) | Corre `observer_cli.py init` en el proyecto; en OpenCode, usa los comandos a mano |
| `observer_cli.py` o `kaizen-cli.py` sale con 2 y dice `[PARAR LÍNEA] Violación Lean AgentOps` | `--who`, `--proceso` o `--dueno` nombra a una persona o a un agente | Pon el componente técnico: un archivo de reglas (`CLAUDE.md`), un script (`resumen.py`), una prueba |
| `import-goldfish` sale con 2 o imprime `[AVISO] El revisor aún no escribió...` (salida 0) | Con `2`, el JSON es ilegible o no trae las listas `qualityLog`/`deliveryLog`; con `0` y `[AVISO]`, el archivo aún no existe | Revisa la ruta pasada en `--artefacto` y que el revisor haya escrito un objeto JSON con `qualityLog` y/o `deliveryLog` |
| `validar-a3.py` rechaza con `[PARAR LÍNEA]` (salida 1) | El A3 no cumple lo que exige su etapa o su regla de fuentes | Lee la sección o celda que nombra; o baja la etapa de la cabecera si todavía no toca |
| `prepare-goldfish` dice "MODO LOCAL" | `TAS_GOLDFISH_DESPACHO` no está definida | Es lo esperado sin revisor remoto: usa el subagente local `observador-goldfish` |

Si un comando falla de una forma que no está aquí, no lo repitas a ciegas: es la regla del tercer fallo. Anota los tres intentos y la salida real.

## 9. Glosario corto
- **Gemba:** el lugar real donde ocurre el trabajo (el código, el servidor, el documento, la máquina). "Ir al Gemba" es mirarlo en vez de suponer. "Firmar no es inspeccionar": un visto bueno sin criterio no comprueba nada.
- **Andon:** la señal para parar la línea. Para un agente: al tercer fallo seguido, se detiene y llega con hechos y opciones.
- **Jidoka:** que el proceso se detenga solo ante un defecto, en vez de seguir y esconderlo. Es la idea detrás de parar para arreglar y de los poka-yoke.
- **PDCA:** el ciclo Planear, Hacer, Verificar, Actuar. Cada contramedida pasa por ahí: se analiza, se instala, se verifica y se estandariza.
- **Hansei:** la reflexión honesta al cerrar: qué funcionó y por qué, qué no funcionó y por qué.
- **Muda:** desperdicio; lo que quien recibe el trabajo no necesita ni reconocería (reintentos, esperas, lecturas de más, trabajo no pedido).
- **Mura:** irregularidad; el trabajo que llega en oleadas, o el que se reparte de forma despareja.
- **Muri:** sobrecarga; pedirle a un agente o a una persona más de lo que cabe (quince tareas a la vez, treinta archivos en una revisión).
- **Ishikawa:** el diagrama de espina de pescado. En el A3 son seis ramas (Método, Máquina, Material, Medición, Medio, Relevo) para ordenar las hipótesis de una causa.
- **PICK:** el cuadrante que ordena las ideas por impacto y esfuerzo: `Implementar` (impacto alto, esfuerzo bajo), `Desafío` (alto, alto), `Posible` (bajo, bajo) y `Eliminar` (bajo, alto).
- **Poka-yoke:** mecanismo que impide que el error vuelva: desde un aviso hasta un bloqueo (una prueba que falla, un comando que rechaza un dato).
