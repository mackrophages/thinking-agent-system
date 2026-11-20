# `tas` (Thinking Agent System): Mejora Continua, Gemba, Jugadas VSM y Lean AgentOps

**TAS (Thinking Agent System)** es un plugin portable para **Claude Code**, **Antigravity (`agy`)** y **OpenCode** que instrumenta la filosofía operativa Lean (Sistema de Producción Toyota / TPS, leído como *Thinking People System*: agentes que piensan el proceso antes de disparar herramientas) y el marco **Lean AgentOps (Patrón Elephant-Goldfish)** para todos tus proyectos: código, documentos, infraestructura y proyectos personales. Su repositorio público es `thinking-agent-system` (`https://github.com/mackrophages/thinking-agent-system`).

## Brújula: los 5 principios Lean

Lean no es una caja de herramientas sueltas: primero el sistema, después la herramienta. Antes de escoger un skill, contesta la pregunta del principio que toca; la respuesta dice qué skill usar (en Claude Code se invoca como `/tas:<skill>` y en Antigravity y OpenCode como `tas-<skill>`).

| Principio | Pregunta | Skill que la contesta |
| :--- | :--- | :--- |
| **Valor** | ¿Quién recibe este trabajo y cómo sabrá que está bien? | `a3` (meta y criterio de aceptación) |
| **Cadena de valor** | ¿Por dónde pasa el trabajo, desde el pedido hasta quien lo usa, y dónde se atasca? | `gemba` para verlo en el lugar real; `goldfish-observer` para la Jugada VSM |
| **Flujo** | ¿Avanza en piezas pequeñas verificadas, o algo espera o falla tres veces? | `agent-ops` (estándar del ejecutor y Andon); `5-porques` si un defecto lo paró |
| **Pull** | ¿Hay una señal de quien recibe que pida esto, o lo estoy haciendo por si acaso? | `agent-ops` (encargo y devolución en `references/encargo-de-delegacion.md`) |
| **Perfección** | ¿Qué aprendí, qué cambia en el estándar y lo revisó alguien sin mi sesgo? | `kaizen`; `ojos-frescos` |

## Los 14 principios de Toyota en las reglas siempre activas

`rules/AGENTS.md` traduce los 14 principios del Toyota Way a una línea de conducta cada uno, en sus cuatro bloques: filosofía de largo plazo; el proceso correcto da el resultado correcto; desarrollar a las personas y a los socios; resolver la causa raíz y aprender. Debajo van las reglas operativas: Andon al tercer fallo, Gemba antes de afirmar, se culpa al proceso (y no culpar no es excusar), A3 para lo no trivial y ojos frescos.

Qué significa cada principio para un agente, en qué pieza vive, cuánto lo cubre hoy el plugin y las fuentes con su página: [`skills/agent-ops/references/principios.md`](./skills/agent-ops/references/principios.md).

## Cómo trabaja un agente con TAS

- **Largo plazo y nada oculto (Anti-Goodhart):** La calidad en la fuente y la seguridad del trabajo pesan más que el ahorro de tokens de hoy. **Las métricas auditan el proceso y el entorno, NUNCA castigan al agente.** El trabajo necesario de calidad y seguridad (`NNVA`) jamás se recorta.
- **Patrón Elephant-Goldfish (Observador Silencioso en el Círculo de Ohno):** El agente principal (**Elefante**) ejecuta con memoria larga, aplica 5S de contexto al iniciar, explora con índices y lecturas acotadas y tira de la cuerda de **Andon** al 3er fallo consecutivo (*"la tercera es la vencida"*), llegando con hechos y opciones. El **Observador Silencioso (Goldfish)** mide el flujo fuera de banda (`0 tokens` en línea) y alimenta el **Pre-Production Readiness Board** (`Builds 1 a 12`).
- **Jidoka sin curitas:** Ante un defecto se para la línea y se busca la causa raíz en el diseño o el proceso. Prohibida la curita que tapa el síntoma; el cambio pequeño y el ensayo corto que prueba una hipótesis son bienvenidos.
- **Genchi Genbutsu (Ir al Gemba):** *"Firmar no es inspeccionar"*. Ningún estado se reporta sin medirlo en el lugar real donde ocurre el trabajo (el código, el documento o la máquina: procesos en `/proc`, consultas SQLite, páginas de manual PDF renderizadas a 200/400 dpi, y pruebas reales de HTML en navegador sin red).
- **Se culpa al proceso o componente, nunca a la persona ni al agente (`Who` = Componente):** No culpar no es excusar: toda desviación se investiga, y si falla algo delegado se revisa primero el encargo. Toda contramedida instala un **Poka-Yoke** en un artefacto técnico (`CLAUDE.md`, `KI System`, `MCP Config`, `Linter Hook`, `Skill Rule`).
- **Autoridad que se gana con hechos:** Para una acción irreversible o fuera del encargo, ni "¿procedo?" a secas ni actuar por cuenta propia: una propuesta corta con hechos, opciones, recomendación y riesgos.
- **Jugadas VSM (Estado Presente → Estado Futuro) y Kaizen con Ventanas IA (`5h / 20h / 1 semana`):** Cada jugada mapea el estado presente y el estado futuro de un flujo junto con el tablero interactivo HTML, y los compromisos se revisan en cortes de **5 horas, 20 horas y 1 semana** con honestidad total en el Gemba.

## Presupuesto de Contexto

Lean también para el plugin: el contexto que se carga en cada sesión lo pagan todos los agentes, todas las veces.

- **Tope:** lo siempre activo es `rules/AGENTS.md`, que se inyecta entero en cada sesión. Su tope es de 6.374 bytes (lo que pesaba en la v1.1.1) y se mide con `wc -c rules/AGENTS.md`.
- **Toda adición se compensa con una reducción:** quien agrega una línea siempre activa quita otra de igual o mayor peso.
- **Siempre activo solo lo que se hace siempre:** lo que sirve a veces vive en un skill o en su carpeta `references/`, que se carga a pedido.
- **Cada regla es una contramedida:** se sabe qué condición atiende y se retira si deja de mover algo.
- **Descripciones de skills cortas:** sirven para elegir el skill; el detalle va en el cuerpo y en `references/`.

---

## Estructura del Plugin

```text
tas/
├── plugin.json                        # Manifiesto nativo para Antigravity (agy)
├── hooks.json                         # Hooks de ciclo de vida para Antigravity (PostToolUse, Stop)
├── CHANGELOG.md                       # Historial de cambios y guía de migración
├── .claude-plugin/
│   ├── plugin.json                    # Manifiesto para Claude Code
│   ├── marketplace.json               # Catálogo local para Claude Code (tas@tas)
│   └── agents/                        # Adaptadores livianos (omitClaudeMd: true, solo lectura)
├── hooks/
│   └── hooks.json                     # Hooks para Claude Code (SessionStart, PostToolUse, PostToolUseFailure, Stop)
├── scripts/
│   ├── goldfish_sensor.py             # Sensor silencioso fuera de banda (opt-in por proyecto con .tas/)
│   └── session_start_rules.py         # Inyección de rules/AGENTS.md en SessionStart para Claude Code
├── rules/
│   └── AGENTS.md                      # Reglas siempre activas: 14 principios y reglas operativas (tope 6.374 bytes)
├── agents/                            # Subagentes canónicos sin contexto previo
│   ├── auditor-gemba.md               # Verifica números, torques, P/N, SQL y rutas contra la fuente cruda
│   ├── critico-causa-raiz.md          # Caza curitas, culpas a la persona/agente y falta de Poka-Yoke
│   ├── lector-primera-visita.md       # Evalúa claridad de relevo y flujo Estado Presente -> Estado Futuro
│   └── observador-goldfish.md         # Observador Silencioso local en el Círculo de Ohno
└── skills/
    ├── agent-ops/                     # Estándar TWI del Elefante (5S, exploración, Andon, valor por quien recibe, KPIs honestos)
    │   └── references/
    │       ├── principios.md          # 14 principios de Toyota y 5 principios Lean: cobertura y fuentes
    │       └── encargo-de-delegacion.md  # Estándar de relevo: encargo y devolución
    ├── goldfish-observer/             # Tablero Readiness 1-12 (MD + HTML offline), Jugadas VSM y observer_cli.py
    │   └── references/
    │       └── compas-y-variacion.md  # Compás, calibración medida y variación: de dónde sale
    ├── 5-porques/                     # Jidoka, Verificado vs Supuesto, porqués y casos reales variados
    │   └── references/
    │       ├── casos-reales.md        # Casos reales de causa raíz
    │       └── poka-yoke-niveles.md   # Escalera de poka-yoke, de aviso a bloqueo
    ├── a3/                            # A3 interno de 1 página por etapas
    │   ├── resources/
    │   │   ├── plantilla-a3-interno.md  # Plantilla del A3 (Contrato 3)
    │   │   ├── ejemplo-a3.md          # Un A3 lleno que pasa el validador
    │   │   └── ejemplo-respaldo.log   # Registro de respaldo citado por el ejemplo
    │   ├── references/
    │   │   ├── contrato-a3.json       # Vocabulario unificado de los contratos del A3
    │   │   └── preguntas-del-coach.md # Preguntas del revisor por etapa
    │   └── scripts/
    │       ├── validar-a3.py          # Validador del A3 (poka-yoke de fuentes verificables)
    │       └── dibujar-a3.py          # Dibujos del A3 a partir de sus tablas, sin red
    ├── gemba/                         # Protocolo Genchi Genbutsu + scripts/chequeo-gemba.sh
    ├── ojos-frescos/                  # Orquestación de auditoría sin sesgo de confirmación
    └── kaizen/                        # Tablero KAIZEN.md con ventanas 5h / 20h / 1 semana + scripts/kaizen-cli.py
```

---

## Los 7 Skills y sus Herramientas Deterministas

| Skill | Cuándo usarlo | Herramienta / Plantilla incluida |
| :--- | :--- | :--- |
| **`agent-ops`** | Al iniciar una sesión, al delegar o al diseñar mejoras de flujo para el Agente Ejecutor (Elefante). | Estándar TWI (Auditoría 5S, exploración quirúrgica en paralelo, Andon al 3er fallo, calidad en la fuente), valor definido por quien recibe, fórmulas honestas (`FTY`, `CT`, `CBR`, `PCE`), `references/principios.md` y `references/encargo-de-delegacion.md`. |
| **`goldfish-observer`** | Para inicializar `.tas/`, medir corridas (`Builds 1-12`), actualizar el tablero interactivo HTML, crear Jugadas VSM o despachar a un revisor remoto. | `scripts/observer_cli.py`, `resources/READINESS_BOARD.md`, `resources/index.html` (100% offline, sin CDN) y `resources/plantilla-jugada-vsm.md`. |
| **`5-porques`** | Antes de codificar el arreglo de un defecto, regresión o fallo operativo. | Matriz *Verificado vs. Supuesto*, porqués hasta diseño/proceso, contraste *Curita vs. Poka-Yoke*, casos reales (`references/casos-reales.md`) y escalera de poka-yoke (`references/poka-yoke-niveles.md`). |
| **`a3`** | Para estructurar un cambio no trivial o alinear un encargo complejo en una sola página Markdown. | `resources/plantilla-a3-interno.md`, `resources/ejemplo-a3.md`, `resources/ejemplo-respaldo.log`, `references/contrato-a3.json`, `references/preguntas-del-coach.md`, validador `scripts/validar-a3.py` y dibujante `scripts/dibujar-a3.py`. |
| **`gemba`** | Antes de diagnosticar, antes de confiar en una bitácora previa y antes de dar una tarea por cerrada. | Protocolos de Gemba (código/procesos, navegador Playwright sin red, manuales PDF a 200/400 dpi, checklists con 5 eslabones) + `scripts/chequeo-gemba.sh`. |
| **`ojos-frescos`** | Antes de aprobar un A3, una extracción de datos, una Jugada VSM o un plan de implementación. | Despacho aislado a `auditor-gemba`, `critico-causa-raiz`, `lector-primera-visita` y `observador-goldfish`. |
| **`kaizen`** | Para registrar desperdicios eliminados, Jugadas (Estado Presente → Estado Futuro) y auditar compromisos en ventanas de **5 horas / 20 horas / 1 semana**. | `resources/plantilla-kaizen.md` y utilidad `scripts/kaizen-cli.py` (`init`, `add-compromiso`, `cerrar`, `add-kaizen`, `add-jugada`, `status`). |

---

## Instalación

El repositorio público es `thinking-agent-system` (`https://github.com/mackrophages/thinking-agent-system`). En Claude Code, con `<ruta-a-tas>` como la carpeta donde lo clonaste:

```bash
claude plugin marketplace add <ruta-a-tas>
claude plugin install tas@tas
```

Antigravity y OpenCode necesitan copias `tas-*` de los skills. Los pasos de las tres plataformas, y cómo comprobar que quedó cargado, están en la [sección 2 del manual](./docs/manual.md#2-instalación-y-comprobación); los cambios de cada versión y cómo migrar, en [`CHANGELOG.md`](./CHANGELOG.md).

---

## Licencia

Distribuido bajo licencia **MIT**. Ver [LICENSE](./LICENSE).
