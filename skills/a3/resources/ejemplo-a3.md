# A3: respaldos sin restaurar: de 3 de 10 a 0 de 10

- **Propietario:** agente de infraestructura
- **Coach / Revisor:** responsable de operaciones
- **Versión:** 4 (2026-11-03)
- **Etapa:** cerrar
- **Contrato:** 3
- **Objetivo que apoya:** recuperar el servicio en menos de 1 hora ante cualquier pérdida de datos

## 1. Contexto y Desperdicio (Muda) Observado
- **Por qué importa ahora:** un respaldo que no restaura se descubre el día que hace falta; hoy 3 de cada 10 noches no hay copia válida.
- **Desperdicio observado:** defecto oculto; cada respaldo inservible se copia, se guarda y se paga sin servir.
- **Pregunta cero:** el problema no se puede eliminar: sin respaldo el servicio no cumple su objetivo de recuperación, así que "no construir" queda descartado.

## 2. Estado Actual en el Gemba
| Hecho medido | Fuente |
| :--- | :--- |
| 3 de 10 respaldos de octubre no se restauran: el archivo termina a mitad de una tabla | ejemplo-respaldo.log:1 |
| Los 3 fallidos son los volcados que pasaron de 30 min | evidencia: ejemplo-respaldo.log |
| El trabajo de respaldo terminó con salida 0 las 10 noches | `journalctl -u respaldo` -> ejemplo-respaldo.log |
| La base pasó de 6 GB a 11 GB desde junio | `du -sh /var/lib/datos` -> ejemplo-respaldo.log |

- **Brecha:** respaldos sin restaurar: de 3 de 10 (medido) a 0 de 10 (meta) para el 2026-11-30

### Mapa del estado presente

| Paso | Quién | Tiempo | Problema | Fuente |
| :--- | :--- | :--- | :--- | :--- |
| 1. Volcar la base | `respaldo.sh` desde el programador | 25 a 35 min | [A] `timeout 30m` corta los volcados largos | ejemplo-respaldo.log:2 |
| 2. Comprimir | gzip en la misma tubería | lo que dure el volcado | termina bien aunque la entrada llegue cortada | ejemplo-respaldo.log:5 |
| 3. Copiar al almacén | `rclone` | 4 min | [B] copia el archivo cortado como si fuera bueno | ejemplo-respaldo.log:6 |
| 4. Revisar | ningún componente | no ocurre | el fallo solo se ve al restaurar | ejemplo-respaldo.log:7 |

## 3. Meta y Criterio de Aceptación
- **Meta:** 10 de 10 respaldos se restauran en la prueba diaria durante 2 semanas seguidas.
- **Criterio de aceptación:** la restauración de prueba termina con salida 0 y el conteo de filas de las 5 tablas mayores coincide con el origen.

## 4. Análisis de Causa Raíz
| Estado | Observación | Evidencia en Gemba o prueba pendiente |
| :--- | :--- | :--- |
| **Verificado** | Un volcado cortado por `timeout` deja la tubería con salida 0 | `timeout 1 sh -c 'sleep 2 \| gzip' >/dev/null` -> ejemplo-respaldo.log |
| **Supuesto** | La base seguirá creciendo cerca de 1 GB por mes | pendiente: medir de nuevo en diciembre |

### 4a. Ishikawa

| Rama | Hipótesis u observación | Evidencia en Gemba | Estado |
| :--- | :--- | :--- | :--- |
| Método | El procedimiento de respaldo no se sigue todas las noches | el programador corre el mismo script las 10 noches | DESCARTADA |
| Máquina | El script acepta un volcado cortado: tubería sin `pipefail` y límite fijo de 30 min | `respaldo.sh`, líneas 12 a 15 | FOCO |
| Material | La base llega dañada al volcado | las 10 bases de origen pasan la verificación de integridad | DESCARTADA |
| Medición | Nada comprueba que un respaldo se pueda restaurar | no existe prueba de restauración programada | FOCO |
| Medio | Disco o red llenos durante el respaldo | 40 % de disco libre y sin cortes de red las 10 noches | DESCARTADA |
| Relevo | El traspaso del servicio dejó fuera el respaldo | el respaldo figura en la lista de traspaso firmada | DESCARTADA |

### 4b. Porqués por causa

- **Causa A (Máquina):** el script da por bueno un volcado cortado.
  - 1. ¿Por qué 3 respaldos no se restauran? -> el archivo termina a mitad de una tabla.
  - 2. ¿Por qué termina a mitad? -> `timeout 30m` corta el volcado cuando la base tarda más de 30 min.
  - 3. ¿Por qué el corte no se reporta? -> sin `pipefail` la tubería devuelve la salida de gzip, que es 0.
  - Por lo tanto: la tubería sin `pipefail` oculta el corte -> el límite fijo corta los volcados largos -> 3 de 10 archivos quedan inservibles.
- **Causa B (Medición):** ninguna prueba restaura los respaldos.
  - 1. ¿Por qué el fallo pasó semanas sin verse? -> la única señal era la salida del trabajo, siempre 0.
  - 2. ¿Por qué solo se miraba la salida? -> el estándar de respaldo termina al copiar y no incluye restaurar.
  - Por lo tanto: el estándar no incluye restaurar -> solo se mira la salida -> un respaldo inservible pasa semanas sin verse.

## 5. Contramedidas y Poka-Yoke
| Opción | Causa | Nivel | Impacto | Esfuerzo | Cuadrante | Decisión | Predicción |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| O-1 `pipefail` y volcado por directorio en 4 hilos | A | raíz | alto | bajo (5 h) | Implementar | elegida | respaldos sin restaurar: de 3 de 10 a 0 de 10 (base: ejemplo-respaldo.log:1-2 con 4 hilos); duración: de 35 a 12 min |
| O-2 Restauración de prueba diaria que avisa si falla | B | poka-yoke | alto | bajo (20 h) | Implementar | elegida | días con un respaldo inservible sin aviso: de 21 a 0 (base: prueba diaria tras el volcado nocturno) |
| O-3 Respaldo continuo con réplica | A | raíz | alto | alto (más de 1 semana) | Desafío | después | duración del respaldo: de 35 min a menos de 5 min (base: corte instantáneo desde réplica sincronizada) |
| O-4 Subir el límite a 60 min | síntoma | curita | bajo | bajo (5 h) | Posible | descartada | aplaza el corte hasta que la base vuelva a crecer (base: ejemplo-respaldo.log:4 con crecimiento de 1 GB por mes) |
| O-5 Copiar cada respaldo a dos almacenes | síntoma | curita | bajo | alto (1 semana) | Eliminar | descartada | duplica los archivos cortados (base: ejemplo-respaldo.log:5-6 porque rclone copia la salida 0 sin verificar) |

### Mapa del estado futuro

| Paso | Quién | Tiempo | Problema | Fuente |
| :--- | :--- | :--- | :--- | :--- |
| 1. Volcar la base en 4 hilos; un corte se reporta como fallo | `respaldo.sh` con `pipefail` | 12 min | ninguno | (base: volcado de 25 a 35 min repartido en 4 hilos (ejemplo-respaldo.log:2)) |
| 2. Copiar al almacén | `rclone` | 4 min | ninguno | ejemplo-respaldo.log:6 |
| 3. Restaurar en una base de prueba; si falla, avisa a la guardia | `restaurar-prueba.sh` | 15 min | ninguno | (base: restauración del volcado de 11 GB en base de prueba (ejemplo-respaldo.log:4)) |

## 6. Plan de Ejecución PDCA y Ventana de Despliegue
| Paso | Acción | Responsable | Verificación |
| :--- | :--- | :--- | :--- |
| 1 | Escribir la prueba que restaura el último respaldo | `restaurar-prueba.sh` | falla con el respaldo cortado del 2026-10-12 |
| 2 | Activar `pipefail` y el volcado en 4 hilos | `respaldo.sh` | la prueba del paso 1 pasa 3 noches seguidas |
| 3 | Programar la restauración diaria con aviso | programador de tareas | un respaldo cortado a propósito dispara el aviso |

- **Ventana de despliegue:** fuera de la franja de 01:00 a 03:00; los respaldos anteriores se conservan 30 días.
- **Autorización:** no hace falta, todo es reversible y está dentro del encargo.

## 7. Verificación en Gemba y Estandarización
- **Predicho contra real:** O-1 predijo 0 de 10 sin restaurar y 12 min; se midieron 0 de 14 y 13 min. O-2 predijo 0 días sin aviso; el aviso saltó una vez, con el respaldo cortado a propósito.
- **Qué puede salir mal y cómo lo veremos:** la base crece y el volcado vuelve a acercarse al límite; la prueba diaria registra la duración y avisa si pasa de 45 min.
- **Próxima revisión:** compromiso C-07 de `KAIZEN.md`, ventana de 1 semana.
- **Estandarización:** `respaldo.sh` lleva `set -o pipefail`, `restaurar-prueba.sh` corre cada día desde el programador y `docs/alta-de-servicio.md` exige ambos.
