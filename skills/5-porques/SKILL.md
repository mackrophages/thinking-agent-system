---
name: 5-porques
description: >-
  Usa este skill antes de proponer o codificar el arreglo de cualquier error en producción,
  fallo de sistema o máquina, regresión de tests o incidente operativo. Obliga a parar la línea
  (Jidoka), separar hechos verificados en el Gemba de supuestos, preguntar por qué hasta nivel
  de diseño o proceso (sin culpar a la persona ni al agente) y definir una contramedida de raíz
  con Poka-Yoke en lugar de una curita.
---

# Jidoka y 5 Porqués: Causa Raíz sin Curitas

## Principio Base

> *"En Lean siempre pensamos en parar y resolver un problema de raíz, no una curita... No tiene sentido optimizar sobre errores: primero arreglar, después optimizar."*

Cuando aparece un fallo en código, en infraestructura, en un documento o en una máquina:
1. **Prohibida la curita, no el cambio pequeño.** Lo prohibido es el parche que tapa el síntoma y deja vivo el mecanismo que lo genera. Un cambio pequeño que ataca la causa, o un ensayo corto que prueba una hipótesis, no es una curita: es la forma más rápida de aprender.
2. **El cuidado de un sistema activo NO se logra achicando el arreglo**, sino eligiendo la **ventana de despliegue adecuada** (cuando las rutas, tareas o jornadas ya cerraron) y garantizando **compatibilidad con sesiones abiertas y colas activas**.
3. **Se culpa al proceso o componente, nunca a la persona ni al agente.** Si tu análisis termina en *"el operador no vio el desgaste"* o *"el agente olvidó pasar el parámetro"*, te detuviste antes de llegar a la raíz.

---

## Procedimiento Obligatorio en 4 Pasos

Antes de tocar una línea de código o recomendar un cambio físico o documental, redacta este bloque diagnóstico (en tu respuesta, en el encargo al subagente o dentro del A3):

### Paso 1: Parar la Línea, Separar Evidencia y Estratificar
Nunca empieces los porqués sobre una teoría no comprobada. Una lectura directa de 2 minutos en el Gemba (lecturas reales de sensores, la tabla en SQLite, `/proc/<pid>/environ`) suele descartar hipótesis enteras antes de tocar nada.

| Tipo | Qué sabemos / Qué observamos | Fuente en el Gemba (comando, log, sensor, pantalla) |
| :--- | :--- | :--- |
| **VERIFICADO** | Hechos medidos directamente sin interpretación | Ej. consulta SQL, lectura de sensores, línea exacta del código |
| **SUPUESTO (Hipótesis)** | Lo que creemos que pasa pero aún no medimos | Qué prueba rápida de 2 minutos falta para confirmarlo o descartarlo |

**Estratifica antes de preguntar:** si el síntoma tiene varias formas (por tipo, módulo, máquina u hora), cuenta cuál pesa más y empieza por esa. Con dos o más hipótesis vivas, ordénalas en el Ishikawa de seis ramas del A3 (`a3`, sección 4a) y abre una cadena por cada rama en FOCO.

### Paso 2: Cadena de Porqués (Hasta Diseño o Proceso)
Encadena las preguntas partiendo del síntoma **verificado**:

```markdown
- **Síntoma verificado:** [Qué falló exactamente y cómo se midió]
  - 1. ¿Por qué ocurrió el síntoma? -> [Causa física o técnica inmediata]
  - 2. ¿Por qué ocurrió (1)? -> [Mecanismo o condición que disparó la falla]
  - 3. ¿Por qué no se detectó o bloqueó a tiempo (2)? -> [Falta de control o alerta]
  - 4. ¿Por qué el diseño o proceso permitía trabajar así (3)? -> [Hueco en el estándar, esquema o checklist]
  - Por lo tanto: [la misma cadena leída de abajo hacia arriba, unida con ->]
```

- **No siempre son cinco.** Para cuando llegas a un diseño o proceso que se puede cambiar; a veces son tres, a veces siete.
- **Si se bifurca, ábrela en árbol.** Cuando una respuesta tiene dos causas, numera `2a` y `2b` y sigue cada rama hasta su raíz.
- **Prueba del "por lo tanto".** Lee la cadena de abajo hacia arriba uniendo cada paso con "por lo tanto". Si un salto no se sostiene, falta un porqué o sobra una suposición.

### Paso 3: Matriz de Contramedida (Descartar la Curita + Instalar Poka-Yoke)
Contrasta explícitamente el parche tentador contra la solución real:

| Nivel | Descripción | Por qué se descarta o se aprueba |
| :--- | :--- | :--- |
| **Curita (PROHIBIDA)** | El arreglo que solo calla la alarma o parcha el dato puntual | *Descartada:* deja vivo el mecanismo generador del fallo |
| **Contramedida de Raíz** | El cambio en código, esquema o procedimiento que elimina el último porqué | *Aprobada:* ataca el proceso o diseño |
| **Poka-Yoke (A prueba de error)** | Mecanismo automático que **impide** que el error vuelva a ocurrir | Ej. registro de lote que bloquea doble procesamiento, test que falla, criterio numérico obligatorio |

Los niveles de poka-yoke, de avisar a impedir, están en `references/poka-yoke-niveles.md`.

### Paso 4: Ventana de Despliegue y Criterio de Verificación
- **Compatibilidad en transición**: ¿Hay colas offline en teléfonos, sesiones de agentes abiertas o lotes a mitad de jornada?
- **Ventana de aplicación**: ¿Se puede aplicar ya o debe programarse para el cierre de la jornada?
- **Prueba en Gemba post-arreglo**: Comando o medición exacta que demuestra que el síntoma desapareció y el Poka-Yoke bloquea la recaída.

---

## Lista de Verificación antes de Codificar o Intervenir
- [ ] ¿Separé honestamente lo **Verificado** en el Gemba de lo **Supuesto**, y estratifiqué antes de preguntar?
- [ ] ¿Llegué a una causa de **diseño o proceso** sin culpar a una persona ni al agente, y la cadena pasa la prueba del "por lo tanto"?
- [ ] ¿Identifiqué la *curita* tentadora y expliqué por qué no basta?
- [ ] ¿Incluí un **Poka-Yoke** concreto que bloquee la repetición desde el sistema?
- [ ] ¿Aseguré que no estoy mezclando optimizaciones cosméticas mientras el error sigue abierto?

Para ver ejemplos reales en proyectos variados (código e IA, infraestructura Linux, documentos y checklists, mantenimiento de un vehículo), consulta [casos-reales.md](./references/casos-reales.md).
