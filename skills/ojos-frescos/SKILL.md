---
name: ojos-frescos
description: >-
  Usa este skill cuando hayas redactado un A3, un diagnóstico de causa raíz, una Jugada VSM,
  un plan de implementación o una tabla técnica y necesites auditarlo sin sesgo de confirmación.
  Invoca subagentes aislados (Ojos Frescos) que revisan en frío sin el historial previo.
---

# Revisión con Ojos Frescos (Autor con Contexto vs. Revisor Aislado)

## Roles bajo el modelo Elephant-Goldfish

1. **Autor (Elefante):** Tiene la historia del caso, fue al Gemba y tiene las herramientas de edición.
2. **Revisor de Ojos Frescos (Goldfish):** Arranca en frío y en **solo lectura** con la ruta del entregable y las fuentes crudas. Abre al menos una fuente cruda antes de opinar: cuando falta evidencia o hay un dato sin respaldo dictamina **`[PARAR LÍNEA]`**; en lo que es juicio devuelve **preguntas por etapa con la evidencia que falta**, y **el autor decide el arreglo**.

## Los 4 Revisores y Cuántos Invocar según Criticidad

| Subagente (`agents/`) | Lente de auditoría | Cuándo invocarlo |
| :--- | :--- | :--- |
| **`auditor-gemba`** | Contrasta cifras, códigos, consultas o afirmaciones contra la fuente cruda y frena datos sin respaldo. | Tablas técnicas, manuales PDF, reportes con métricas o diagnósticos. |
| **`critico-causa-raiz`** | Audita brecha, meta no disfrazada, lectura inversa con "por lo tanto", opciones reales, cobertura por causa y nivel de poka-yoke. | Incidentes, reportes A3, arreglos de producción o arquitectura. |
| **`lector-primera-visita`** | Verifica en frío que el A3, jugada o guía se entienda sin contexto implícito y que las pruebas rápidas vayan primero. | Jugadas VSM, A3, guías operativas o encargos para otros agentes. |
| **`observador-goldfish`** | Analiza `.tas/gemba_trace.jsonl` y el transcript para clasificar desviaciones por componente técnico (`Who`). | Al cerrar corridas en proyectos con `.tas/` activo. |

La inspección sucesiva solo reduce fallos si los revisores son independientes (sin tu razonamiento previo y con lentes distintas):

| Criticidad de la entrega | Revisores independientes recomendados | Combinación típica |
| :--- | :--- | :--- |
| **Cotidiano** (cambio local y reversible) | **0 o 1** revisor | Autocontrol en el Gemba; `lector-primera-visita` si hay relevo. |
| **Importante** (A3, guía operativa, fix con causa raíz) | **1** revisor con la lente del caso | `critico-causa-raiz`, `auditor-gemba` o `lector-primera-visita`. |
| **Crítico** (producción, datos, corte irreversible) | **2 o más** revisores con lentes distintas | `critico-causa-raiz` + `lector-primera-visita` (o `auditor-gemba`). |

## Protocolo de Ejecución

### Paso 1: Empaqueta sin contaminar al revisor
Guarda el artefacto en disco. **Prohibido** pasar tu razonamiento o pedir *"solo míralo por encima"*. Tu prompt incluye **únicamente**: (1) ruta absoluta del entregable, (2) rutas absolutas de las fuentes crudas y (3) instrucción de seguir `agents/<revisor>.md` (y `skills/a3/references/preguntas-del-coach.md` si revisa un A3).

### Paso 2: Invoca al subagente
En Antigravity usa `invoke_subagent`; en Claude Code invoca el subagente del plugin (`omitClaudeMd: true`, `[Read, Grep, Glob]`).

### Paso 3: Triaje y respuesta del autor
1. **`[PARAR LÍNEA]`**: Obligatorio corregir antes de entregar; el revisor frena la línea cuando falta evidencia o hay un dato sin respaldo.
2. **Preguntas del coach (`[DESPERDICIO / MUDA]`, `[MEJORA KAIZEN]`)**: El revisor señala qué evidencia falta y pregunta; **el autor investiga en el Gemba y decide el arreglo** (o registra compromisos futuros con `kaizen`).
3. **Cierre honesto**: Documenta al final de la entrega qué señaló la revisión de Ojos Frescos y cómo lo resolviste.
