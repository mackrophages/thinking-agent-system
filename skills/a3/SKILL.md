---
name: a3
description: >-
  Usa este skill para pensar en una página un problema no trivial de arquitectura, diagnóstico
  operativo, automatización o diseño técnico antes de codificar o delegar. Incluye plantilla,
  un ejemplo lleno y el validador validar-a3.py.
---

# A3 de una página: pensar antes de construir

El A3 no es un formulario: es la prueba escrita de que se entendió el problema antes de elegir la
solución. Lo que se exige es el pensamiento; los títulos de sección se conservan solo para que el
validador y el dibujante los encuentren.

## Antes de abrir un A3

- **Cuándo no hace falta.** Si la causa es evidente y el cambio es reversible y barato, se hace y se
  registra (commit, tablero Kaizen o nota de entrega). El A3 es para una brecha medida con más de una
  hipótesis viva o una decisión que cuesta revertir.
- **Pregunta cero.** ¿Se puede disolver o eliminar el problema? "No construir" es siempre la opción
  cero. Va escrita en la sección 1, también cuando se descarta.

## Dos papeles

- **Propietario:** responde por el problema. Va al Gemba, mide, escribe y decide.
- **Coach / Revisor:** pregunta; no escribe las respuestas. Puede ser otro agente o el dueño del
  proyecto. Sus preguntas están en `references/preguntas-del-coach.md`. "pendiente" solo vale en la
  etapa comprender; "sin coach" es un aviso, salvo que el plan proponga una acción irreversible o fuera
  del encargo: ahí hace falta un coach distinto del propietario y la autorización con quién y cuándo.

## Etapas: el A3 se llena por partes

| Etapa | Secciones completas | Lo demás |
| :--- | :--- | :--- |
| comprender | 1 y 2 | vacío |
| analizar | 1 a 4 | vacío |
| proponer | 1 a 5 | vacío |
| planear | 1 a 6 | vacío |
| cerrar | 1 a 7 | nada vacío |

Las casillas vacías son parte del método: muestran qué falta saber y dónde mirar. Llenarlas antes de
tiempo es inventar la causa o la solución. Hasta cerrar, el documento termina con `## Siguientes pasos`
(qué, quién, cuándo) y cada etapa se revisa con el coach antes de pasar a la siguiente.

## Qué pensamiento se exige

1. **Contexto (1):** por qué importa ahora, qué desperdicio se ve y la pregunta cero.
2. **Gemba (2):** solo hechos, cada uno con su fuente, y la línea `- **Brecha:** <indicador>: de <actual> (medido) a <meta> (meta) para <cuándo>`. En el contrato 3 el indicador es obligatorio y, apenas la Brecha está escrita, el título tiene que nombrar su indicador y su meta (`# A3: <indicador>: de <actual> a <meta>`); mientras la Brecha sea la muestra de la plantilla, el título es libre.
3. **Meta (3):** resultado medible y el criterio que confirma que quedó resuelto a la primera.
4. **Causa raíz (4):** tabla Verificado / Supuesto; Ishikawa de seis ramas (Método, Máquina,
   Material, Medición, Medio, Relevo) cuando hay dos o más hipótesis, o la línea "Ishikawa: no aplica";
   porqués por causa, tantos como hagan falta, cerrados con su `Por lo tanto:`. Nunca se culpa a una
   persona ni a un agente.
5. **Contramedidas (5):** dos opciones reales como mínimo (o `Única opción: <motivo>`), cada una con
   su causa, nivel, cuadrante PICK y predicción medible. Toda causa tiene al menos una opción y nada que
   caiga en `Eliminar` se elige.
6. **Plan (6):** pasos con responsable y verificación, ventana de despliegue y autorización.
7. **Verificación (7):** predicho contra real, qué puede salir mal y cómo lo veremos, próxima revisión
   (el compromiso de `KAIZEN.md` si existe) y dónde quedó estandarizado.

En el contrato `3` los mapas de estado presente (sección 2, desde `comprender`) y futuro (sección 5, desde `proponer`) son obligatorios, uno por sección y nunca fuera de esas dos secciones; su forma de cinco columnas
(`Paso | Quién | Tiempo | Problema | Fuente`) está en la plantilla y en el ejemplo. En el mapa presente, el paso donde ocurre una causa marca su **estallido kaizen** empezando `Problema` con la letra de su causa en `4b` (por ejemplo `[A] timeout corta el volcado`): desde `analizar`, un `[X]` sin causa en `4b` para la línea y una causa de `4b` sin estallido en el mapa presente da aviso. En el mapa futuro los estallidos ya están resueltos (un `[X]` ahí da aviso) y `Problema` dice solo lo que queda sin resolver (`ninguno` si queda limpio); lo que cambia se escribe en el nombre del paso.

## Flujo de trabajo

1. Copia [plantilla-a3-interno.md](./resources/plantilla-a3-interno.md) (por ejemplo a
   `docs/a3-<tema>.md`). [ejemplo-a3.md](./resources/ejemplo-a3.md) muestra un A3 cerrado.
2. Llena la etapa en curso tras ir al Gemba (`gemba`) y hacer los porqués (`5-porques`).
3. Valida:
   ```bash
   python3 <ruta-al-plugin>/skills/a3/scripts/validar-a3.py [--etapa ETAPA] <ruta-a-tu-a3.md>
   ```
   Sin `--etapa` se lee la etapa de la cabecera; `--raiz` fija la carpeta raíz del proyecto cuando no se
   busca `.git`. Con `- **Contrato:** 3` (por defecto en la plantilla; sin línea `Contrato` se aplica el
   contrato 1 y con `2` solo se revisan las secciones 2 y 4), cada fuente de la sección 2 y cada fila
   `**Verificado**` de la sección 4 debe usar una de las cuatro formas (o varias separadas por `;`):
   `ruta:N` o rango `ruta:N-M`, `` `comando` -> ruta ``, `https://...` o `evidencia: ruta`; la columna
   `Fuente` del mapa presente exige las cuatro formas o `[SIN MEDIR]` (este último solo hasta `analizar`),
   la del mapa futuro exige las cuatro formas o una `(base: de dónde sale)` sola en la celda, y cada
   predicción de la sección 5 lleva al menos una `(base: texto)` en texto plano. El contrato 3 exige la
   forma exacta de la plantilla (línea Contrato, títulos y encabezado de los mapas, filas con `|` al
   principio y al final, la base): lo que se le parezca sin coincidir para la línea y el mensaje muestra
   la forma correcta. `[PARAR LÍNEA]` rechaza (salida 1); `[AVISO]` no rechaza; la salida 2 es un
   error de uso. En contrato 3 también avisa, sin parar la línea, cuando se superan los topes de palabras
   de `contrato-a3.json` (`30` por celda, `40` por viñeta y `1500` en total, sin contar bloques de código).
   Se conserva el límite de 160 líneas no vacías y la detección del formato v1.1.1.
4. Para verlo dibujado (etapa, mapas, Ishikawa y matriz PICK en una página HTML de un solo archivo,
   sin red, que se abre en el teléfono o el navegador):
   ```bash
   python3 <ruta-al-plugin>/skills/a3/scripts/dibujar-a3.py <ruta-a-tu-a3.md> -o <ruta-a-tu-a3.html>
   ```
   El Markdown sigue siendo la fuente: se razona y se valida ahí, y el dibujo se vuelve a generar.
   En la Brecha, las cifras se leen con punto decimal y coma de miles en grupos de tres dígitos (`1,250.5`, `4.125`); otro formato cae a texto destacado.
5. En cambios críticos, pásalo por `ojos-frescos` antes de ejecutar el plan.
