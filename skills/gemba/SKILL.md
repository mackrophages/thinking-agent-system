---
name: gemba
description: >-
  Usa este skill antes de diagnosticar un fallo, antes de confiar en una bitácora o resumen
  de otro agente, y antes de reportar cualquier entregable como terminado. Formaliza Genchi
  Genbutsu ("ir al lugar real") y "firmar no es inspeccionar" para código, servidores, bases
  de datos, entregables HTML interactivos, manuales PDF y checklists operativos.
---

# Genchi Genbutsu: Verificación en el Gemba ("Firmar no es inspeccionar")

## Por qué existe este skill

Aprendimos por experiencia directa en proyectos de código, infraestructura, documentos y mecánica que **la confianza declarada por un agente o el éxito de un script de compilación no sustituyen ir al Gemba**:

1. **Caso Navara D40 (Bugs silenciosos de UI):** `build.py` generaba el HTML sin un solo error, pero al abrir el documento real en navegador con Playwright aparecieron 2 fallos que rompían funciones centrales: `render()` se llamaba antes de asignar `var PESO` (*hoisting*), dejando muerta la calculadora por kilometraje, y las notas se guardaban bajo `<clave>:n` pero el reporte las leía en `<clave>`.
2. **Caso Navara D40 (`FSU-5`, Torque falso con "confianza alta"):** Un agente asignó `274-364 N·m` a los tornillos de leva del brazo inferior diciendo que estaba "confirmado por texto". Era el torque de la tuerca de maza (~3× lo seguro para el brazo). Se descubrió porque en la tabla quedaron **dos componentes distintos con el mismo valor numérico** y porque al renderizar `FSU-5` a alta resolución la línea guía iba a otra pieza.
3. **Caso Checklists Operativos ("Firmar no es inspeccionar"):** Las hojas de mantenimiento de 500 h tenían la firma en *"Revisar visualmente amortiguadores"*, pero el equipo falló porque **firmar sin criterio de aceptación no es inspeccionar**.
4. **Caso Procesos en Linux (`/proc` vs `ps`):** Confiar en `ps` hacía creer que 5 procesos estaban caídos cuando en realidad sus scripts wrapper hacían `exec` y su identidad real estaba en `/proc/<pid>/environ`.

---

## Los 4 Protocolos de Gemba

### 1. Gemba de Código, Infraestructura y Base de Datos
Antes de afirmar *"el servicio está corriendo"*, *"la base está actualizada"* o *"ya quedó desplegado"*:
- **Procesos:** Verifica el PID vivo y su entorno real (`/proc/<pid>/cmdline`, `/proc/<pid>/environ`, `systemctl status`, sesiones activas), no solo si existe un archivo `.pid` o una nota previa.
- **Datos:** Corre la consulta real contra SQLite/Postgres (`SELECT count(*), max(created_at) ...`) y muestra el número exacto.
- **Estado de repositorio:** Corre `git status -s` y `git log -n 2` para confirmar que no quedaron archivos sueltos ni tests rotos.

### 2. Gemba de Entregables HTML e Interfaces Interactivas
Que el generador Python/TS termine con código `0` **NO** prueba que el entregable funcione:
- Abre el archivo real en **Playwright (navegador completo, no headless shell que deja páginas en blanco)** o `Bun.WebView`, sin red (`offline`), a ancho de teléfono (`412 px`) y de escritorio.
- Comprueba que **no haya errores de consola JS** (`pageerror`, `console.error`) al cargar ni al interactuar con ruedas PDCA, pestañas, filtros o calculadoras.
- Verifica que la primera línea sea `<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">` y que `document.characterSet` sea `UTF-8` (cero *mojibake*).
- Si el documento se abrirá desde `/sdcard/Download/` en el teléfono (`content://`), confirma que todo el CSS esté en `<style>` y las imágenes en `data:` URI, sin depender de CDN ni rutas relativas externas.

### 3. Gemba Documental y de Manuales (PDF / Catálogos)
Nunca extraigas torques, presiones, códigos PNC/P/N ni bornes de vistas explotadas usando únicamente `pdftotext`:
1. Usa `pdftotext -layout` solo para **ubicar la sección y página** (cuidado con falsos positivos por referencias cruzadas tipo `Refer to BR-8`; busca la etiqueta de página sola en su línea).
2. **Renderiza la página como imagen** con `pdftoppm -r 200` (o `-r 400` para seguir líneas guía densas) y mírala directamente.
3. **Nunca recortes solo el dibujo:** recorta siempre el diagrama junto con la **leyenda numerada del pie de figura**.
4. **Regla de Oro de Seguridad Física:** Si una línea guía se cruza o no se puede seguir con 100% de certeza hasta el componente, **no adivines**. Márcalo explícitamente como `[SIN CONFIRMAR]`. Si un dato proviene del oficio y no del manual, etiquétalo como `[PRÁCTICA ESTÁNDAR]`.
5. **Chequeo de valores repetidos:** Si en una misma tabla dos piezas distintas terminan con el mismo valor numérico (ej. `274-364 N·m`), para la línea y verifica en la imagen que no sea una misatribución.

### 4. Gemba de Checklists y Estándares ("Firmar no es inspeccionar")
Al redactar o auditar cualquier lista de chequeo (mantenimiento, QA o pre-despliegue), prohíbe ítems mudos como *"Revisar X"*. Cada punto debe especificar los 5 eslabones:
- **1. Qué limpio / preparo** (o qué comando corro)
- **2. Qué busco**
- **3. Criterio Normal vs. Anormal** (rango numérico en bar/kPa/°C/N·m/ms o condición visual inequívoca)
- **4. Qué hago si lo encuentro anormal** (contramedida inmediata)
- **5. Para que no vuelva** (ajuste de proceso o Poka-Yoke)

---

## Compuerta Determinista: `chequeo-gemba.sh`

Antes de cerrar tu tarea o entregar un directorio, ejecuta el script de inspección rápida:

```bash
bash <ruta-al-plugin>/skills/gemba/scripts/chequeo-gemba.sh [directorio-o-archivo]
```

El script inspecciona en el Gemba:
1. Estado real de Git (cambios sin commitear, rama actual, último commit).
2. Validación sintáctica de todos los archivos `.json` presentes en el objetivo.
3. Detección automática de secuencias de *mojibake* y validación UTF-8 en archivos `.html`, `.md`, `.py`, `.ts`, `.js`, `.json`.
4. Presencia de marcadores `[SIN CONFIRMAR]` y `[PRÁCTICA ESTÁNDAR]`.
5. Detección de valores numéricos con unidades repetidos en tablas Markdown/HTML (heurística anti-misatribución `FSU-5`).
