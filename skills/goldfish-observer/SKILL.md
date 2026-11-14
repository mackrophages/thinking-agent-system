---
name: goldfish-observer
description: >-
  Actúa como el Observador Silencioso en el Círculo de Ohno (Agente Goldfish sin estado).
  Analiza trazas (.tas/gemba_trace.jsonl y transcripts) sin juzgar al ejecutor,
  actualiza el Pre-Production Readiness Board en Markdown y HTML offline, gestiona Jugadas
  VSM y define cuándo despachar la observación a un revisor remoto o al subagente local.
---

# Observador Silencioso en el Círculo de Ohno (Modelo Goldfish)

El **Observador Silencioso (Goldfish)** opera sin estado previo ni juicio punitivo: observa bloques de **12 corridas (`Builds 1 a 12`)** en `.tas/gemba_trace.jsonl` para detectar fricción en herramientas, contexto o estándares.

## 1. Reglas de Clasificación y Calibración en el Gemba

1. **Cero Culpa al Agente (`Who` = Componente Técnico):** En `Quality` y `Delivery`, `Who` jamás señala a personas ni agentes (el CLI lo bloquea, Poka-Yoke); nombra siempre el componente técnico (`CLAUDE.md`, `KI System`, `MCP Config`, `Linter Hook`, `Test Suite`, `Skill Rule` o `Workflow`).
2. **Problemas de Calidad (`Quality`, Meta `Goal = 0`):**
   - `Wrong Parts - Supplied`: Contexto inicial, configuración o *KI* con datos obsoletos o contradictorios.
   - `Wrong Parts - Built`: Defecto introducido al construir (sintaxis, tipo inválido, dato mal transcrito o test roto).
   - `Wrong Parts - Designed`: Esquema JSON de MCP o CLI ambiguo que induce a fallos de invocación.
   - `Missing Parts`: Falta índice, ruta o comando en `CLAUDE.md`/`KIs`, forzando exploración a ciegas (`> 4` búsquedas).
3. **Flujo, Calibración Medida y Regla de Lectura (`Delivery`, `Measured CT w/o stopping clock`):**
   - Los `5` y `7` min que `init` trae sin opciones son **valores de arranque sin respaldo**, nunca un estándar universal. Se fijan midiendo la **distribución** real de las primeras corridas limpias del proyecto (moda baja para la referencia, límite superior según la dispersión) y recalibrando con `init --standard-min <ref> --takt-min <techo>`.
   - **Compás real vs techo acordado:** El compás (*takt*) sale del tiempo disponible dividido entre la demanda regular. Sin demanda regular conocida no se le llama *Takt Time*, sino **techo acordado** (o se documenta de qué tiempo disponible y demanda sale). El CLI conserva `--takt-min` y `CT > TT` por compatibilidad.
   - **Regla de lectura:** **Una corrida por encima de la referencia no es por sí sola un problema.** Todo proceso tiene variación normal; intervenir ante cada desvío aislado es reaccionar al ruido. Solo se abre contramedida ante **causa especial** (salto fuera de la variación normal, como retrabajo o lectura íntegra de archivo gigante, *Muda de Inventario*) o **patrón** repetido (llamadas secuenciales, *Muda de Movimiento*, o MCPs inactivos, *Muda de Sobreprocesamiento*).
   - **Fila automática de `Delivery`:** `observer_cli.py` solo agrega fila automática cuando una corrida pasa el **techo acordado** (causa especial evidente); los patrones los propone el observador (`add-delivery-issue`).
   - **Fuentes:** Respaldo en [compas-y-variacion.md](./references/compas-y-variacion.md).
4. **Esfera PDCA (`⊕`):** `1` = `Plan` (raíz analizada), `2` = `Do` (contramedida instalada), `3` = `Check` (verificado en la distribución siguiente con `0` defectos), `4` = `Act` (estandarizado, *Yokoten*).

## 2. Niveles de Observación (Regla de Despacho)

| Nivel | Quién actúa como Goldfish | Cuándo se usa | Cómo se invoca |
| :--- | :--- | :--- | :--- |
| **Nivel 0 (Base, 0 tokens)** | **Sensor y CLI (`goldfish_sensor.py` + `observer_cli.py`)** | En todo proyecto con `.tas/`. | Automático vía hooks (`PostToolUse`, `PostToolUseFailure`, `Stop`) y `close-build`. |
| **Nivel 1 (Revisor remoto)** | **Revisor remoto configurado** | Con `TAS_GOLDFISH_DESPACHO` definida. | `observer_cli.py prepare-goldfish` imprime el comando listo para copiar (no lo ejecuta). |
| **Nivel 2 (Subagente local)** | **Subagente fresco (`observador-goldfish`)** | Sin `TAS_GOLDFISH_DESPACHO` configurada. | Invocar `observador-goldfish` (`omitClaudeMd: true`) solo con `gemba_trace.jsonl` y `transcript_path`. |

Variables de entorno del despacho remoto:
- `TAS_GOLDFISH_DESPACHO`: plantilla del comando remoto con `{encargo}` y `{artefacto}` citados para la shell.
- `TAS_GOLDFISH_ARTEFACTO`: ruta del JSON del revisor; por defecto `.tas/goldfish-board.json` (`--artefacto` manda).
- Compatibilidad (una versión): si falta o está vacía una `TAS_*`, se lee la anterior (`LEAN_GOLDFISH_DESPACHO`, `LEAN_GOLDFISH_ARTEFACTO`, `LEAN_PROJECT_DIR`, `LEAN_STANDARD_MIN`, `LEAN_TAKT_MIN`, `LEAN_AUTO_CLOSE_ON_STOP`); `.lean_observer/` sigue funcionando e `init` la migra a `.tas/` sin corrida abierta.

> **Regla de Oro ("Deriva primero, compara después"):** Pasa solo la traza cruda (`gemba_trace.jsonl` y extractos de herramientas), sin opinión ni resumen del Elefante.

## 3. Definición de "Corrida" (`Build`) y Poka-Yoke por Proyecto

1. **Poka-Yoke de Activación:** `goldfish_sensor.py` no actúa sin `.tas/`, evitando ensuciar otros directorios. `observer_cli.py init` bloquea directorios personales salvo con `--allow-home`.
2. **Qué es una Corrida (`Build`):** `Stop` ocurre en cada turno y solo actualiza `.tas/active_build.json` (`status: "active"`, sin parar el reloj). Una corrida es una **unidad de trabajo completa**: abre con `observer_cli.py start-build --task "..."` y cierra con `observer_cli.py close-build` al entregar (o en `Stop` con `TAS_AUTO_CLOSE_ON_STOP=1`).

## 4. Comandos de `observer_cli.py`

### 1. Inicializar o recalibrar `.tas/` con datos medidos
```bash
# Sin opciones deja 5 y 7 min de arranque sin respaldo; recalibra tras medir Builds 1-12:
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py init \
  --project-dir /ruta/al/proyecto \
  --project-name "Mantenimiento Equipos" \
  --standard-min 3.2 \
  --takt-min 6.0
```
Crea o actualiza `.tas/READINESS_BOARD.md`, `.tas/dashboard/index.html` (offline, sin CDN ni red), `.tas/jugadas/`, y la línea `.tas/active_build.json` en `.gitignore`.

### 2. Iniciar y cerrar una corrida (`Build`)
```bash
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py start-build \
  --project-dir /ruta/al/proyecto \
  --task "Verificar bitácora de mantenimiento y pruebas"

python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py close-build \
  --project-dir /ruta/al/proyecto \
  --note "Verificación en verde"
```

### 3. Registrar contramedidas de Calidad y Flujo (`Who` = Componente)
```bash
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py add-quality-issue \
  --project-dir /ruta/al/proyecto \
  --build 1 \
  --issue "5 llamadas a grep buscando rutas de esquemas" \
  --category "Missing Parts" \
  --cm "Documentar índice de rutas principales en CLAUDE.md" \
  --who "CLAUDE.md / KI" \
  --pdca 2

# Solo ante causa especial o patrón repetido (compatibilidad CLI: --category "CT > TT" o "CT > Standard")
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py add-delivery-issue \
  --project-dir /ruta/al/proyecto \
  --build 2 \
  --issue "9.4 min (causa especial sobre techo acordado): volcado íntegro de log de 4,000 líneas" \
  --category "CT > TT" \
  --muda "Inventario (WIP)" \
  --cm "Acotar lectura con offset y limit" \
  --who "agent-ops" \
  --pdca 3
```

### 4. Analizar un `transcript.jsonl` fuera de banda (FTY, CT, CBR, PCE)
```bash
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py analyze-transcript \
  --transcript /ruta/al/transcript.jsonl \
  --format markdown
```

### 5. Crear una Jugada VSM (Estado Presente -> Estado Futuro)
```bash
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py create-jugada \
  --project-dir /ruta/al/proyecto \
  --id "J-01" \
  --flujo "Despliegue de configuración de infraestructura" \
  --ct-presente "8.4 min (patrón sobre techo acordado en 4 corridas)" \
  --fty-presente "78%" \
  --muda-presente "Lecturas completas de archivos y búsquedas secuenciales" \
  --problema "Falta mapa de módulos y chequeo local offline" \
  --poka-yoke "Índice en CLAUDE.md + validador automático sin red"
```

### 6. Preparar el paquete Goldfish e importar su respuesta
```bash
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py prepare-goldfish \
  --project-dir /ruta/al/proyecto
python3 <ruta-al-plugin>/skills/goldfish-observer/scripts/observer_cli.py import-goldfish \
  --project-dir /ruta/al/proyecto \
  --artefacto /ruta/al/proyecto/.tas/goldfish-board.json
```
`import-goldfish` valida cada fila como `add-quality-issue` y `add-delivery-issue`, agrega sin duplicar e informa entradas y rechazos. Sale con 2 si el JSON no tiene esa forma.
