# A3: <título que nombra el problema, no la solución>

- **Propietario:** <quien responde por el problema>
- **Coach / Revisor:** <quien pregunta; "pendiente" solo vale en comprender>
- **Versión:** 1 (<fecha AAAA-MM-DD>)
- **Etapa:** comprender | analizar | proponer | planear | cerrar
- **Contrato:** 3
- **Objetivo que apoya:** <meta mayor o A3 padre; opcional>

## 1. Contexto y Desperdicio (Muda) Observado
- **Por qué importa ahora:** <qué flujo o usuario se ve afectado y qué cuesta esperar>
- **Desperdicio observado:** <defecto, retrabajo, espera, inventario, movimiento o sobreproceso>
- **Pregunta cero:** <¿se puede disolver o eliminar el problema? "no construir" es la opción cero>

## 2. Estado Actual en el Gemba
| Hecho medido | Fuente |
| :--- | :--- |
| <dato medido, con su cifra> | <fuente: ruta:línea, comando -> ruta, https://... o evidencia: ruta> |

- **Brecha:** de <X medido> (medido) a <Y meta> (meta) para <cuándo se espera>

### Mapa del estado presente

| Paso | Quién | Tiempo | Problema | Fuente |
| :--- | :--- | :--- | :--- | :--- |
| 1. <paso actual> | <componente o agente> | <duración medida> | <problema o ninguno> | <fuente o [SIN MEDIR] hasta analizar> |

## 3. Meta y Criterio de Aceptación
- **Meta:** <resultado medible que cierra la brecha>
- **Criterio de aceptación:** <qué resultado exacto confirma que quedó resuelto a la primera>

## 4. Análisis de Causa Raíz
| Estado | Observación | Evidencia en Gemba o prueba pendiente |
| :--- | :--- | :--- |
| **Verificado** | <hecho comprobado> | <fuente: ruta:línea, comando -> ruta, https://... o evidencia: ruta> |
| **Supuesto** | <hipótesis aún sin medir> | <prueba corta que la confirma o la descarta> |

### 4a. Ishikawa

<con una sola hipótesis, cambia la tabla por: Ishikawa: no aplica, una sola hipótesis (cuál)>

| Rama | Hipótesis u observación | Evidencia en Gemba | Estado |
| :--- | :--- | :--- | :--- |
| Método | <procedimiento, estándar u orden de pasos> | <qué se vio> | <FOCO o DESCARTADA> |
| Máquina | <código, herramientas o infraestructura> | <qué se vio> | <FOCO o DESCARTADA> |
| Material | <datos y contexto de entrada> | <qué se vio> | <FOCO o DESCARTADA> |
| Medición | <sensores, pruebas o métricas> | <qué se vio> | <FOCO o DESCARTADA> |
| Medio | <sistema operativo, red, cuotas, reloj o permisos> | <qué se vio> | <FOCO o DESCARTADA> |
| Relevo | <el encargo y la entrega, nunca la persona> | <qué se vio> | <FOCO o DESCARTADA> |

### 4b. Porqués por causa

- **Causa A (<rama en FOCO>):** <enunciado de la causa, sin culpar a una persona ni a un agente>
  - 1. ¿Por qué <síntoma verificado>? -> <respuesta comprobada>
  - 2. ¿Por qué <respuesta anterior>? -> <respuesta comprobada>
  - Por lo tanto: <la misma cadena leída de abajo hacia arriba, unida con -> >

## 5. Contramedidas y Poka-Yoke
<con una sola opción real, cambia la tabla por: Única opción: motivo>

| Opción | Causa | Nivel | Impacto | Esfuerzo | Cuadrante | Decisión | Predicción |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| O-1 <nombre corto> | <letra o síntoma> | <curita, raíz o poka-yoke> | <alto o bajo> | <bajo o alto> (<5 h, 20 h, 1 semana o más de 1 semana>) | <Implementar, Desafío, Posible o Eliminar> | <elegida, después o descartada> | <qué medida cambia y cuánto> (base: <medición o supuesto>) |
| O-2 <nombre corto> | <letra o síntoma> | <curita, raíz o poka-yoke> | <alto o bajo> | <bajo o alto> (<5 h, 20 h, 1 semana o más de 1 semana>) | <Implementar, Desafío, Posible o Eliminar> | <elegida, después o descartada> | <qué medida cambia y cuánto> (base: <medición o supuesto>) |

### Mapa del estado futuro

| Paso | Quién | Tiempo | Problema | Fuente |
| :--- | :--- | :--- | :--- | :--- |
| 1. <paso futuro> | <componente o agente> | <duración esperada> | <problema restante o ninguno> | <fuente o (base: de dónde sale)> |

## 6. Plan de Ejecución PDCA y Ventana de Despliegue
| Paso | Acción | Responsable | Verificación |
| :--- | :--- | :--- | :--- |
| 1 | <acción concreta> | <componente o agente> | <comando o salida esperada> |

- **Ventana de despliegue:** <cuándo se aplica sin romper lo que está en uso>
- **Autorización:** <"no hace falta" si todo es reversible y está dentro del encargo; si no, quién y cuándo>

## 7. Verificación en Gemba y Estandarización
- **Predicho contra real:** <lo que predijo cada opción elegida y lo que se midió>
- **Qué puede salir mal y cómo lo veremos:** <riesgo y la señal que lo delata>
- **Próxima revisión:** <id del compromiso en KAIZEN.md; sin tablero, ventana de 5 h, 20 h o 1 semana y quién>
- **Estandarización:** <archivo que se carga o se ejecuta solo y donde quedó el cambio>

## Siguientes pasos
- <qué falta para cerrar esta etapa>: <quién lo hace>, <para cuándo>
