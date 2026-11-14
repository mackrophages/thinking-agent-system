# Jugada {{ID}}: {{FLUJO}} (Estado Presente → Estado Futuro)

- **Fecha:** {{FECHA}}
- **Proyecto:** {{PROYECTO}}
- **Estándar de Entrega (`Standard`):** `{{STANDARD_MIN}} min` | **Techo acordado:** `{{TAKT_MIN}} min`
- **Tablero Asociado:** [READINESS_BOARD.md](../READINESS_BOARD.md) | [Tablero Interactivo HTML](../dashboard/index.html)

---

## 1. Mapa del Estado Presente (Current State Flow)

> Describe cómo ocurre hoy el flujo en el Gemba antes de intervenir, midiendo sin detener el reloj dónde se consume valor (`VA`), trabajo necesario (`NNVA`) y desperdicio (`Muda`).

| Paso # | Eslabón del Flujo Actual | Clasificación (`VA` / `NNVA` / `Muda`) | Tiempo / Costo Observado | Fricción (`Wrong/Missing Parts` o `CT`) |
| :---: | :--- | :---: | :--- | :--- |
| 1 | {{PASO_PRESENTE_1}} | `NNVA` / `Muda` | `X.X min` | `Missing Parts` / `Inventario` |
| 2 | {{PASO_PRESENTE_2}} | `VA` | `Y.Y min` | `0 defectos` |

### Línea Base del Estado Presente
- **Cycle Time medido (`CT`):** `{{CT_PRESENTE}}`
- **First-Time Yield de herramientas (`FTY`):** `{{FTY_PRESENTE}}`
- **Principal cuello de botella / Muda:** `{{MUDA_PRESENTE}}`

---

## 2. Explosiones Kaizen y Poka-Yokes (Transición)

| Problema / Muda en Estado Presente | Contramedida (`CM`) + Poka-Yoke | Componente (`Who`) | Ventana (5h / 20h / 1sem) |
| :--- | :--- | :--- | :---: |
| {{PROBLEMA_1}} | {{POKA_YOKE_1}} | `CLAUDE.md` / `Script` / `Hook` | `5h` |

---

## 3. Mapa del Estado Futuro (Future State Flow)

> Describe cómo queda el flujo rediseñado (lotes paralelos, índices claros y validación en la fuente), listo para verificarse en las 12 corridas del `Pre-Production Readiness Board`.

| Paso # | Eslabón del Flujo Futuro | Clasificación (`VA` / `NNVA`) | Meta de Tiempo | Poka-Yoke Activo |
| :---: | :--- | :---: | :--- | :--- |
| 1 | {{PASO_FUTURO_1}} | `NNVA` | `<= 1.0 min` | Índice directo / lectura acotada |
| 2 | {{PASO_FUTURO_2}} | `VA` | `<= 3.0 min` | Compuerta automática en la fuente |

### Meta del Estado Futuro (Readiness Goal)
- **Meta de Calidad (`Quality`):** `0 Issues` (`FTY = 100%`)
- **Meta de Entrega (`Delivery`):** `CT <= {{STANDARD_MIN}} min (techo acordado: {{TAKT_MIN}} min)`
- **Criterio de graduación en el Tablero:** Alcanzar `Best Score` sostenido en el bloque de 12 corridas (`Builds 1 a 12`).
