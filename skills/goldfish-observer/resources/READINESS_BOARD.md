# 📋 PRE-PRODUCTION READINESS BOARD (Observador Silencioso)

* **Proyecto / Flujo:** `{{PROYECTO}}`
* **Best Score:** `{{BEST_SCORE}}`
* **Meta calibrada:** `0 defectos | CT <= {{STANDARD_MIN}} min (techo acordado: {{TAKT_MIN}} min)`

## 1. Secuencia de Madurez (Readiness Builds 1 - 12)
| Build | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
| :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **Estado** | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| **Issues (Q)** | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |
| **CT (min)** | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` | `-` |

> **Leyenda:** `⬜ Pendiente` | `🔄 Activa` | `✅ Cerrada` | `🏆 Best Score`

---

## 2. Columna Izquierda: QUALITY (Goal = 0 Defectos)
| Build # | Issue | Familia (`Wrong` / `Missing Parts`) | CM (Contramedida) | Who (Componente) | PDCA |
| :---: | :--- | :--- | :--- | :--- | :---: |

* `Wrong Parts - Supplied` (contexto o KI obsoleto) | `Wrong Parts - Built` (defecto al construir)
* `Wrong Parts - Designed` (MCP o CLI ambiguo) | `Missing Parts` (falta índice o estándar)

---

## 3. Columna Derecha: DELIVERY (CT sin detener reloj)
* **Calibración:** `5` y `7` min son valores de arranque sin respaldo; calibrar referencia (`{{STANDARD_MIN}}` min) y **techo acordado** (`{{TAKT_MIN}}` min, o compás si sale de demanda) con la distribución medida (`Builds 1-12`) en `observer_cli.py init`.
* **Lectura:** Una corrida sobre la referencia no es por sí sola un problema; actuar ante **causa especial** (salto fuera de variación normal) o **patrón** repetido.

### Causas Especiales y Patrones de Flujo
| Build # | Hallazgo | Muda | CM (Contramedida de Flujo) | Who (Componente) | PDCA |
| :---: | :--- | :--- | :--- | :--- | :---: |
