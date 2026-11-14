---
name: kaizen
description: >-
  Usa este skill para mantener la bitácora operativa de mejora continua del proyecto (KAIZEN.md),
  priorizar compromisos por cuadrante PICK con límite de abiertos, cerrarlos con reflexión (Hansei)
  y ejecutar revisiones en ventanas de 5 horas, 20 horas y 1 semana con kaizen-cli.py.
---

# Kaizen con Ventanas de la Era IA (5 Horas / 20 Horas / 1 Semana)

## Qué resuelve `kaizen`

- **Ventanas de 5 h, 20 h y 1 semana (168 h):** Evaluamos rápido en el Gemba (código, documento, infraestructura o máquina) si un compromiso se cumplió y si la mejora se sostiene sin vigilancia manual.
- **Cuadrante PICK heredado o directo:** Si el compromiso nace de un A3, hereda su cuadrante de la sección 5 (`--a3 <ruta> --opcion <código>`) para no puntuar dos veces lo mismo. Solo cuando no viene de un A3 se pasa `--impacto alto|bajo --esfuerzo bajo|alto`, calculando `Implementar`, `Desafío`, `Posible` o `Eliminar`.
- **Límite de abiertos y orden PICK:** `status` ordena los compromisos abiertos por cuadrante (`Implementar` primero, `Sin puntuar` al final) y avisa cuando superan el límite (5 por defecto, configurable con `--limite`).
- **Reflexión al cerrar (`cerrar`):** Cerrar un compromiso exige documentar si la mejora se sostuvo en la siguiente ventana (`--sostenido si|no`) y la reflexión (`--hansei`: **qué funcionó y por qué, qué no funcionó y por qué**).

---

## Uso de `kaizen-cli.py`

### 1. Inicializar `KAIZEN.md`
```bash
python3 <ruta-al-plugin>/skills/kaizen/scripts/kaizen-cli.py init \
  --file ./KAIZEN.md \
  --project "Nombre del Proyecto" \
  --limite 5
```

### 2. Registrar un Compromiso (heredado de A3 o puntuado directo)
```bash
# Desde un A3 (hereda el cuadrante PICK de la tabla de opciones de la sección 5):
python3 <ruta-al-plugin>/skills/kaizen/scripts/kaizen-cli.py add-compromiso \
  --file ./KAIZEN.md --id "C-01" \
  --compromiso "Validar esquema antes de guardar lote" \
  --dueno "scripts/validador.py" --a3 ./A3-lotes.md --opcion "O-1"

# Sin A3 (calcula el cuadrante PICK a partir de impacto y esfuerzo):
python3 <ruta-al-plugin>/skills/kaizen/scripts/kaizen-cli.py add-compromiso \
  --file ./KAIZEN.md --id "C-02" \
  --compromiso "Acotar lecturas de archivos grandes por defecto" \
  --dueno "CLAUDE.md / Skill Rule" --impacto alto --esfuerzo bajo
```

### 3. Auditar estado, orden PICK y límite de abiertos (`status`)
```bash
python3 <ruta-al-plugin>/skills/kaizen/scripts/kaizen-cli.py status \
  --file ./KAIZEN.md --now "2026-11-10T14:00" --limite 5
```

### 4. Cerrar un Compromiso con reflexión (`cerrar`)
```bash
python3 <ruta-al-plugin>/skills/kaizen/scripts/kaizen-cli.py cerrar \
  --file ./KAIZEN.md --id "C-01" \
  --hansei "Qué funcionó y por qué: el bloqueo en entrada frenó 3 lotes rotos. Qué no y por qué: faltó cubrir la importación manual." \
  --sostenido si
```

### 5. Registrar mejora Kaizen (`add-kaizen`) y Jugada VSM (`add-jugada`)
```bash
python3 <ruta-al-plugin>/skills/kaizen/scripts/kaizen-cli.py add-kaizen \
  --file ./KAIZEN.md --proceso "Base de Datos" \
  --muda "Doble procesamiento por filtro abierto" \
  --poka-yoke "Llave única de lote que bloquea duplicados" --impacto "0 duplicados en estrés"

python3 <ruta-al-plugin>/skills/kaizen/scripts/kaizen-cli.py add-jugada \
  --file ./KAIZEN.md --id "J-01" --flujo "Verificación de interfaz" \
  --presente "CT = 7.8 min, validación manual" --futuro "CT <= 4.0 min, prueba automática sin red"
```

---

## Reglas de Oro
1. **Culpa al proceso o componente, nunca a la persona ni al agente:** En `--proceso` y `--dueno`, nombra siempre el componente técnico o subsistema (`CLAUDE.md`, `MCP Config`, `Esquema SQL`, `Pipeline de Tests`).
2. **Honestidad y aprendizaje en el Gemba:** Si un estándar no se cumplió, investiga qué fricción del proceso lo impidió; al cerrar, registra siempre qué funcionó y por qué, y qué no funcionó y por qué.
