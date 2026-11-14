# Casos Reales (Referencia de 5 Porqués, Gemba y Poka-Yoke en Proyectos Variados)

Estos cinco casos reales muestran la diferencia entre una *curita* y una **contramedida de raíz con Poka-Yoke** en distintos dominios (proyecto personal automotriz, código e IA, infraestructura Linux y estándares documentales):

---

## Caso 1: Proyecto Personal Automotriz (Navara D40, Diagrama `FSU-5` y Calculadora Web)
- **Síntoma A (Documental):** En la tabla de pares de apriete de la suspensión delantera (`FSU-5`), los tornillos de leva del brazo inferior aparecían con `274-364 N·m` y etiqueta de "confianza alta", cuando ese valor es ~3 veces lo seguro para ese perno.
  - **1° Por qué:** Porque el extractor tomó el rango `274-364 N·m` del texto extraído de la página.
  - **2° Por qué:** Porque en la página `FSU-5` ese valor corresponde a la tuerca de maza, no al tornillo de leva.
  - **3° Por qué:** Porque se usó `pdftotext` sobre un diagrama explotado donde las cajas de torque se conectan a las piezas mediante líneas guía gráficas, no por proximidad de texto.
  - **4° Por qué:** Porque no había una compuerta que alertara cuando dos piezas distintas en la misma tabla terminan con exactamente el mismo rango numérico.
  - **5° Por qué (Causa Raíz de Proceso):** El flujo de extracción carecía de verificación visual en el Gemba (`pdftoppm` a alta resolución siguiendo la línea guía hasta la leyenda) y de una heurística determinista contra valores duplicados.
  - **Curita descartada:** Corregir solo ese número a mano confiando en el resto de la tabla.
  - **Contramedida de raíz + Poka-Yoke:** Regla obligatoria de renderizar vistas explotadas a 200/400 dpi, marcar `[SIN CONFIRMAR]` cualquier línea dudosa y ejecutar la heurística anti-misatribución (`chequeo-gemba.sh`) que detecta rangos con unidades duplicados en tablas.
- **Síntoma B (Código UI):** El script `build.py` generaba el HTML interactivo sin errores, pero la calculadora por kilometraje estaba muerta y las notas no aparecían en el resumen.
  - **Causa Raíz:** `render()` se invocaba antes de inicializar `var PESO` (*hoisting* de `undefined` en JS) y las notas se guardaban en `<clave>:n` pero se leían en `<clave>`. Se asumió que "el generador compiló" equivalía a "la interfaz funciona".
  - **Contramedida de raíz + Poka-Yoke:** Verificación obligatoria del HTML en navegador real (Playwright sin red) comprobando cero errores de consola y probando la interacción de extremo a extremo.

---

## Caso 2: Código e IA Local (Mega-merge Recursivo en un Curador de Memoria)
- **Síntoma:** Las corridas en seco (`dry-run`) devolvían entre 1 y 4 grupos y ahorros de tokens erráticos (0 a 32,489 tokens) sobre las mismas ~40 notas, y al aplicar los cambios unía temas sin relación en un solo "mega-grupo".
- **1° Por qué:** Porque el modelo agrupaba pares distintos en cada corrida y la clausura transitiva encadenaba un falso positivo con todo el grafo.
- **2° Por qué:** Porque la llamada a Ollama no fijaba `temperature` ni `seed`, y además el curador volvía a leer sus propios reportes y consolidaciones previas como candidatos.
- **3° Por qué:** Porque cualquier par de notas se enviaba al LLM sin un filtro matemático previo de cercanía temática.
- **4° Por qué:** Porque se asumió que el texto del prompt bastaba para que un modelo pequeño hiciera deduplicación estricta sin acotar numéricamente los candidatos.
- **5° Por qué (Causa Raíz de Diseño):** Faltaba separar la **pre-selección matemática determinista** de la **redacción del LLM**, y faltaba aislamiento estructural de los tipos generados por el propio proceso.
- **Curita descartada:** Endurecer el prompt pidiéndole al LLM "por favor sé más estricto".
- **Contramedida de raíz + Poka-Yoke:**
  1. `temperature: 0` y `seed: 42` en el cliente del curador.
  2. Exclusión estructural por tipo (`excludeTypes: ["gerente-curator", "consolidation"]`).
  3. Filtro vectorial determinista con `sqlite-vec` (`all-minilm`) calibrado con datos reales (distancia coseno `<= 0.6`) antes de invocar al LLM.

---

## Caso 3: Infraestructura Linux (Colector de Procesos Ciego a Wrappers con `exec`)
- **Síntoma:** Un monitor de sistema reportaba a 5 procesos de agentes como caídos en 217 de 219 capturas, aunque todos estaban corriendo activamente.
- **1° Por qué:** Porque el colector buscaba el nombre del script wrapper en la salida de `ps`.
- **2° Por qué:** Porque los scripts wrapper hacen `exec` al binario principal, por lo que el nombre del wrapper desaparece de `cmdline`.
- **3° Por qué (Causa Raíz de Medición):** La identidad de cada instancia vive en las variables de entorno (`HOME=...`, `CLAUDE_CONFIG_DIR=...`) dentro de `/proc/<pid>/environ`, no en los argumentos de línea de comando.
- **Curita descartada:** Reiniciar los procesos o cambiar el intervalo del cron.
- **Contramedida de raíz + Poka-Yoke:** El colector lee directamente `/proc/<pid>/{cmdline,environ}` acompañado de pruebas automatizadas sobre fixtures de `/proc`.

---

## Caso 4: Documentos y Checklists Operativos ("Firmar no es Inspeccionar")
- **Síntoma:** Un equipo rotativo sufrió una falla severa en suspensión y transmisión a pesar de tener todas sus hojas de revisión de 500 horas firmadas al día.
- **1° Por qué:** Porque operó con elementos de amortiguación degradados sin intervenir a tiempo.
- **2° Por qué:** Porque en las rutinas previas se marcó como realizada la revisión sin detectar la anomalía.
- **3° Por qué:** Porque quien ejecutó la rutina solo miró por encima y firmó la casilla. *(¡OJO! Detenerse aquí sería culpar a la persona; hay que seguir).*
- **4° Por qué:** Porque la hoja decía únicamente *"Revisar visualmente los amortiguadores"*, sin indicar qué limpiar primero, qué buscar ni qué diferencia un estado normal de uno anormal.
- **5° Por qué (Causa Raíz de Proceso):** El estándar documental confundía **firmar** con **inspeccionar**, careciendo de criterios de aceptación observables.
- **Curita descartada:** Llamar la atención al operador o agregar una nota de "revisar con más cuidado".
- **Contramedida de raíz + Poka-Yoke:** Estándar donde cada punto de inspección exige los 5 eslabones obligatorios: `1. Limpio/Preparo -> 2. Busco -> 3. Normal vs. Anormal -> 4. Si lo encuentro -> 5. Para que no vuelva`.

---

## Caso 5: Sistemas Transaccionales (Bloqueo de Doble Procesamiento por Lote)
- **Síntoma / Riesgo:** Al habilitar una vista de cierre y liquidación con filtros libres por fecha o ruta, un mismo documento podía incluirse por error en dos cortes distintos.
- **Causa Raíz de Diseño:** Permitir filtros libres sin una entidad de cierre transaccional deja la integridad de los datos en manos de la memoria visual del usuario.
- **Curita descartada:** Mostrar un cartel de advertencia *"Verifique que el registro no haya sido procesado antes"*.
- **Contramedida de raíz + Poka-Yoke:** Registro de lote en la base de datos que marca cada ítem procesado y **bloquea por diseño** que un ítem ya cerrado vuelva a entrar en un lote nuevo.
