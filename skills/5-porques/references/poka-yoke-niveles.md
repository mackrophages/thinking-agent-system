# Escalera de niveles de Poka-Yoke y catálogo de error a dispositivo

## Por qué "agregar una regla" no basta

Un poka-yoke verdadero inspecciona el 100 % de los casos de forma automática, no depende de la memoria ni de la atención de quien ejecuta, y actúa cuando aparece una anomalía. "Agregar una regla" en un archivo de texto sigue exigiendo que el agente o el operador recuerde leerla y cumplirla bajo presión: es un recordatorio, no un dispositivo a prueba de error.

Para pedir una contramedida más firme, evalúa en qué peldaño de la escalera está tu propuesta y sube al nivel más alto viable:

## Escalera de menor a mayor fuerza

1. **Aviso (alerta automática sin detener):** Detecta la anomalía en el momento y emite una señal visible, pero deja continuar el paso.
   - *Ejemplo de agente (mantenimiento de equipos):* Un script de captura de telemetría que imprime `[AVISO]` en consola cuando la presión leída de un sensor se acerca al borde de tolerancia, sin abortar el registro del lote.
2. **Valor por defecto (encauzamiento o *nudge*):** Configura la herramienta o plantilla para que el camino más cómodo sea el correcto si nadie cambia nada.
   - *Ejemplo de agente (documentos y contexto):* Una herramienta de lectura de archivos que trae por defecto un límite de 200 líneas y una plantilla de encargo que ya incluye rellenos los campos de brecha y criterio de aceptación.
3. **Control (compuerta que detiene el paso ante el fallo):** Verifica el resultado o la condición operativa antes de pasar a la siguiente etapa y devuelve error (`exit code != 0`) si falta una pieza o falla una invariante.
   - *Ejemplo de agente (código):* Un hook de pre-commit o validador determinista que frena la entrega si el archivo A3 tiene una causa raíz sin contramedida en la sección 5 o si una prueba de regresión falla.
4. **Bloqueo (imposible por diseño en la fuente):** La interfaz, el esquema o la topología física/lógica impide construir o enviar el estado defectuoso desde el origen.
   - *Ejemplo de agente (infraestructura y base de datos):* Una llave única compuesta en la tabla de lotes y una credencial de solo lectura para los subagentes revisores: ni un reintento duplica el registro ni un revisor puede editar el repositorio.

## Tres mecanismos clásicos traducidos a agentes

- **Contacto (forma o tipo):** Comprueba la estructura de cada entrada (esquema JSON estricto, tipos estáticos, escapado automático de caracteres HTML).
- **Valor fijo (conteo o presencia):** Hace evidente si falta una pieza obligatoria (verificar que las 6 ramas de Ishikawa o las 4 líneas de la sección 7 estén presentes).
- **Paso de movimiento (secuencia):** Impide ejecutar un paso si no ocurrió antes el requisito (exigir que exista `.tas/` inicializado antes de registrar trazas, o abrir la fuente cruda antes de dictaminar).

*Nota sobre variación:* Cuando un control o bloqueo se dispara, no pierdas la señal: registra por qué se intentó la acción errónea (ciclo largo de mejora) para corregir la fricción de fondo.

## Tabla de error típico a dispositivo

| Error típico | Dispositivo Poka-Yoke recomendado | Nivel |
| :--- | :--- | :--- |
| **Material o entrada defectuosa** (JSON truncado, archivo corrupto, dato fuera de rango) | Validador de esquema en la entrada del script antes de tocar estado en disco. | Control / Bloqueo |
| **Información faltante o ambigua** (encargo sin criterio de aceptación o sin rutas exactas) | Plantilla con campos obligatorios por defecto y compuerta que rechaza placeholders vacíos. | Valor por defecto + Control |
| **Desajuste de configuración** (correr pruebas apuntando a una ruta fija o entorno equivocado) | Cálculo automático de ruta relativa desde `__file__` con variable de entorno opcional. | Valor por defecto |
| **Omisión de paso** (cerrar un compromiso sin verificar si se sostuvo o entregar sin correr pruebas) | Subcomando de cierre que exige `--hansei` y `--sostenido si\|no` como argumentos requeridos. | Bloqueo |
| **Selección equivocada** (inicializar trazas en el directorio personal o borrar la rama activa) | Lista de directorios protegidos rechazada en el código antes de crear carpetas. | Bloqueo |

## Fuentes

- John Bicheno y Matthias Holweg, *The Lean Toolbox* (4.a edición, PICSIE Books, 2009): jerarquía de inspección en la fuente, modos de aviso y control, tipos de dispositivo (contacto, valor fijo y paso de movimiento), cinco categorías de error de Hinckley y ciclo corto/largo en páginas PDF 196 y 197; encauzamiento mediante valores por defecto (*Nudging for Lean*) en páginas PDF 223 y 224.
