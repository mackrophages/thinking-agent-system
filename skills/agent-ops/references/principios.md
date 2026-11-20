# Los principios de TAS

Este archivo se carga a pedido. Las reglas siempre activas (`rules/AGENTS.md`) llevan una línea por
principio; aquí va qué significa cada uno para un agente, en qué pieza del plugin vive, cuánto lo
cubre hoy y de dónde sale.

**Estado** corresponde a la v1.2.0: `cubierto` (hay una pieza que lo hace cumplir o lo deja
visible), `a medias` (está enunciado y alguna pieza lo apoya, pero falta un mecanismo) o `falta` (solo
está enunciado).

## 1. Los 14 principios de Toyota en cuatro bloques

La columna "Principio" resume la idea con palabras propias; no reproduce el enunciado original.

### A. Filosofía de largo plazo

| # | Principio | Qué significa para un agente | Pieza de TAS donde vive | Estado |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Decidir pensando en el largo plazo aunque hoy cueste | No cambiar verificación, mantenibilidad ni la confianza de quien recibe por ahorrar tokens o terminar antes | `rules/AGENTS.md` principio 1; sección 1 de `agent-ops` | cubierto |

### B. El proceso correcto da el resultado correcto

| # | Principio | Qué significa para un agente | Pieza de TAS donde vive | Estado |
| :--- | :--- | :--- | :--- | :--- |
| 2 | Hacer fluir el trabajo para que los problemas salgan a la luz | Un cambio y su verificación antes del siguiente; nada de veinte ediciones sin probar | `rules/AGENTS.md` principio 2; paso 4 del estándar en `agent-ops`. Falta un límite de trabajo en curso | a medias |
| 3 | Tirar del trabajo en lugar de empujarlo, para no producir de más | Nada empieza sin la señal de quien recibe: el encargo con su criterio de aceptación. Lo no pedido es sobreproducción | `rules/AGENTS.md` principio 3; `encargo-de-delegacion.md` (el encargo es la señal). Falta una señal entre agentes con tope de trabajo abierto | a medias |
| 4 | Nivelar la carga | Encargos de tamaño parejo, holgura de contexto y revisiones que el dueño pueda absorber | `rules/AGENTS.md` principio 4. Ninguna pieza mide ni nivela; la sobrecarga se anota como causa dentro de una rama del Ishikawa de `a3` | falta |
| 5 | Crear la costumbre de parar para arreglar y hacerlo bien a la primera | Andon al tercer fallo; si el mismo defecto vuelve 2 rondas seguidas, cambiar de enfoque y anotar el callejón; causa raíz antes del arreglo, sin curitas; el ensayo pequeño sí vale | `rules/AGENTS.md` principio 5 y operativa 1; `agent-ops` (oscilación); `5-porques`; el sensor del observador cuenta los fallos | cubierto |
| 6 | El trabajo estándar es la base de la mejora y de la autonomía | Reglas, skills y scripts son la mejor forma conocida hoy; la mejora se escribe ahí y el agente puede proponer cambiarlos | `rules/AGENTS.md` principio 6; estándar del ejecutor en `agent-ops`; regla de presupuesto en el README | cubierto |
| 7 | Control visual para que ningún problema quede escondido | Estado y fallas a la vista; no se maquillan métricas; el reporte nombra lo que falló y lo que quedó fuera | `rules/AGENTS.md` principio 7; tablero de `goldfish-observer`; `KAIZEN.md`; `dibujar-a3.py` de `a3` | cubierto |
| 8 | Usar solo tecnología confiable, probada y al servicio del trabajo | No adoptar una herramienta, dependencia o servidor MCP sin probarlo; quitar el desperdicio antes de automatizar | `rules/AGENTS.md` principio 8; alerta 5S en `agent-ops`. Falta una prueba de entrada para herramientas nuevas | a medias |

### C. Desarrollar a las personas y a los socios

| # | Principio | Qué significa para un agente | Pieza de TAS donde vive | Estado |
| :--- | :--- | :--- | :--- | :--- |
| 9 | Formar líderes que entienden el trabajo y lo enseñan | Quien orquesta entiende lo que delega y su encargo enseña el qué y el porqué, con la decisión del dueño textual y sin su propio diseño | `rules/AGENTS.md` principio 9; `encargo-de-delegacion.md` (la devolución muestra si se entendió). Falta comprobar el encargo con un lector en frío | a medias |
| 10 | Desarrollar personas y equipos que siguen la misma filosofía | Todos los agentes cargan las mismas reglas; lo aprendido queda en un artefacto que los demás leen | `rules/AGENTS.md` principio 10, que se inyecta en cada sesión de cada agente. Falta un paso que lleve las lecciones de un proyecto a los otros | a medias |
| 11 | Respetar a socios y proveedores exigiéndoles y ayudándoles a mejorar | Herramientas, librerías y otros agentes son proveedores: su defecto vuelve a la fuente con evidencia y propuesta. Si falla lo delegado, primero se revisa el encargo | `rules/AGENTS.md` principio 11 y operativa 3; `encargo-de-delegacion.md`. Falta un formato para devolver el defecto a una herramienta externa | a medias |

### D. Resolver la causa raíz y aprender

| # | Principio | Qué significa para un agente | Pieza de TAS donde vive | Estado |
| :--- | :--- | :--- | :--- | :--- |
| 12 | Ir a ver en persona para entender a fondo | Verificar en el lugar real antes de afirmar; lo que no se pudo trazar se marca sin confirmar | `gemba` y `chequeo-gemba.sh`; agente auditor de Gemba; operativa 2 de `rules/AGENTS.md`. Falta la práctica de ir al Gemba también para aprender a ver (cuasi fallos y desperdicio), no solo para verificar | cubierto |
| 13 | Decidir sin prisa, con consenso y mirando todas las opciones; ejecutar rápido | Lo reversible lo decide el agente y anota por qué; lo irreversible o fuera del encargo va como propuesta corta con hechos, opciones, recomendación y riesgos | `rules/AGENTS.md` principio 13; opciones y matriz PICK en la sección 5 de `a3` y cabecera con revisor | cubierto |
| 14 | Aprender como organización con reflexión honesta y mejora continua | Al cerrar: qué salió distinto de lo previsto, qué cambia en el estándar, y queda escrito | `rules/AGENTS.md` principio 14; "Predicho contra real" en la sección 7 de `a3`; cierre con hansei en `kaizen` | cubierto |

Los 14 caben en las reglas siempre activas con una línea cada uno, sin agrupar y dentro del tope de
6.374 bytes, porque lo que se hace solo a veces pasó a los skills.

## 2. Los 5 principios Lean, la brújula

Son la brújula del README: una pregunta por principio que lleva al skill que la contesta. No se cargan
siempre porque orientan el diseño de un flujo, no la conducta de cada turno.

| Principio | Qué significa para un agente | Pregunta de la brújula |
| :--- | :--- | :--- |
| Valor | Lo define quien recibe el trabajo (el dueño, el usuario del entregable o el siguiente agente), no la herramienta que se usó | ¿Quién recibe esto y cómo sabrá que está bien? |
| Cadena de valor | Todos los pasos por los que pasa el trabajo desde el pedido hasta quien lo usa, incluidos los relevos entre agentes | ¿Por dónde pasa el trabajo y dónde se atasca? |
| Flujo | Avanzar pieza a pieza, cada una verificada, sin colas ni lotes grandes | ¿Avanza en piezas pequeñas verificadas o algo espera? |
| Pull | Producir solo con la señal de quien recibe; lo demás es sobreproducción | ¿Hay una señal de quien recibe que pida esto? |
| Perfección | No es la meta alcanzada sino la dirección: cero desperdicio, lo que se pidió, cuando se pidió | ¿Qué aprendí, qué cambia en el estándar y lo revisó alguien sin mi sesgo? |

## 3. De dónde sale el resto de las reglas siempre activas

| Regla en `rules/AGENTS.md` | Idea de origen | Fuente |
| :--- | :--- | :--- |
| Pull se define por la señal de quien recibe | Pull exige una señal del proceso siguiente; leer por índice no lo es | Bicheno y Holweg, pdf 164 |
| El valor lo define quien recibe | Qué es desperdicio lo decide solo el cliente, que puede ser el proceso siguiente | Bicheno y Holweg, pdf 28 y 34 |
| Prohibida la curita; lo pequeño y el ensayo sí | Soluciones simples y baratas, sin parches que dejen viva la causa; ensayos rápidos para evaluar opciones | Bicheno y Holweg, pdf 19 y 44; Shook, pdf 80, 84 y 87 |
| No culpar no es excusar | Sin culpa no significa aceptar los problemas; si no se sigue un estándar, preguntar por qué no se puede | Shook, pdf 64, 66 y 118; Bicheno y Holweg, pdf 237 |
| Métricas que no castigan | El error es ocasión de mejorar, no algo que se vigila y castiga; el foco va al proceso | Bicheno y Holweg, pdf 25 y 45 |
| Autoridad que se gana con hechos | La autoridad se atrae con el A3: hechos, acuerdo y la iniciativa en quien hace el trabajo | Shook, pdf 14, 93 y 116 a 119 |
| Siempre activo solo lo que se hace siempre | La conducta se construye con lo que se hace siempre; el exceso de información es desperdicio | Bicheno y Holweg, pdf 18 y 40-41 |
| Tope y compensación | En el costeo objetivo el costo tope no se supera: lo que se agrega se paga con una reducción | Bicheno y Holweg, pdf 291 |

"Seguridad psicológica" es un término moderno que el libro no usa; en TAS su respaldo es el de la
fila "Métricas que no castigan".

## 4. Fuentes

- John Bicheno y Matthias Holweg, *The Lean Toolbox*, 4.a edición, PICSIE Books, 2009.
  - Los 14 principios en cuatro bloques: pdf 32. Son de Jeffrey Liker, *The Toyota Way*, McGraw-Hill,
    2004, y el libro los reproduce con permiso de la editorial. TAS no copia los enunciados.
  - Los 5 principios Lean de Womack y Jones (*Lean Thinking*): pdf 28-29. Sobre pull, pdf 164:
    “there needs to be a demand-pull from a downstream process to initiate production”.
  - Sobre el valor, pdf 34: “What is and what is not waste is solely determined by the customer”.
- John Shook, *Dirigir para aprender* (Managing to Learn), Lean Enterprise Institute, 2008, edición en
  español. Autoridad basada en pull: pdf 14 y 116 a 119. Sin culpa y sin excusas: pdf 66 y 118.

Página PDF = página impresa + 16 en Bicheno y Holweg; + 12 en Shook.
