#!/usr/bin/env python3
"""Dibujante determinista de reportes A3 en HTML autocontenido sin red (TAS).

Convierte un documento A3 en Markdown que sigue el contrato de formato en una
pagina HTML de un solo archivo con diagramas SVG en linea.
"""

from __future__ import annotations

import html
import itertools
import json
import math
import re
import sys
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

SECTION_SPECS: tuple[tuple[int, str, str, str], ...] = (
    (1, r"^##\s+1\.\s+Contexto\b.*$", "1. Contexto y Desperdicio (Muda) Observado", "comprender"),
    (2, r"^##\s+2\.\s+Estado Actual\b.*$", "2. Estado Actual en el Gemba", "comprender"),
    (3, r"^##\s+3\.\s+Meta\b.*$", "3. Meta y Criterio de Aceptación", "analizar"),
    (4, r"^##\s+4\.\s+An[aá]lisis de Causa Ra[ií]z\b.*$", "4. Análisis de Causa Raíz", "analizar"),
    (5, r"^##\s+5\.\s+Contramedidas\b.*$", "5. Contramedidas y Poka-Yoke", "proponer"),
    (6, r"^##\s+6\.\s+Plan\b.*$", "6. Plan de Ejecución PDCA y Ventana de Despliegue", "planear"),
    (7, r"^##\s+7\.\s+Verificaci[oó]n\b.*$", "7. Verificación en Gemba y Estandarización", "cerrar"),
)

_CLAVES_CONTRATO = (
    "etapas",
    "ultima_seccion",
    "ramas",
    "subramas",
    "estados_rama",
    "niveles",
    "cuadrantes",
    "pick",
    "decisiones",
    "ventanas",
    "columnas_opciones",
    "rotulos_7",
    "reglas",
)
_CLAVES_REGLAS = ("fuentes", "fila_supuesto", "a3_provisional", "amef")


def _fallar_contrato_json(ruta: Path, motivo: str) -> None:
    print(f"Error: no se pudo leer contrato-a3.json ({ruta}): {motivo}", file=sys.stderr)
    raise SystemExit(2)


def _validar_entrada_contrato(ruta: Path, ver: str, c: object) -> None:
    if not isinstance(c, dict):
        _fallar_contrato_json(ruta, f"el contrato '{ver}' no es un objeto")
    for clave in _CLAVES_CONTRATO:
        if clave not in c:
            _fallar_contrato_json(ruta, f"falta la clave '{clave}' en el contrato '{ver}'")
    for clave_lista in (
        "etapas",
        "ramas",
        "estados_rama",
        "niveles",
        "cuadrantes",
        "decisiones",
        "ventanas",
        "columnas_opciones",
        "rotulos_7",
    ):
        val = c[clave_lista]
        if not isinstance(val, list) or not val or not all(isinstance(x, str) and x for x in val):
            _fallar_contrato_json(ruta, f"'{clave_lista}' debe ser una lista no vacía de textos")
    if not isinstance(c["subramas"], dict):
        _fallar_contrato_json(ruta, "'subramas' debe ser un objeto")
    ultima = c["ultima_seccion"]
    if not isinstance(ultima, dict) or any(e not in ultima or not isinstance(ultima[e], int) for e in c["etapas"]):
        _fallar_contrato_json(ruta, "'ultima_seccion' debe mapear cada etapa a un entero")
    pick = c["pick"]
    if not isinstance(pick, list) or not pick:
        _fallar_contrato_json(ruta, "'pick' debe ser una lista no vacía")
    for item in pick:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(k), str) and item.get(k) for k in ("impacto", "esfuerzo", "cuadrante")
        ):
            _fallar_contrato_json(ruta, "cada entrada de 'pick' requiere impacto, esfuerzo y cuadrante")
    reglas = c["reglas"]
    if not isinstance(reglas, dict) or any(k not in reglas for k in _CLAVES_REGLAS):
        _fallar_contrato_json(ruta, "faltan claves obligatorias en 'reglas'")


def cargar_contrato(numero: int | None = None) -> dict:
    """Lee skills/a3/references/contrato-a3.json y devuelve el diccionario del contrato pedido."""
    ruta = Path(__file__).resolve().parent.parent / "references" / "contrato-a3.json"
    try:
        crudo = ruta.read_text(encoding="utf-8")
    except OSError as exc:
        _fallar_contrato_json(ruta, exc.strerror or str(exc))
    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError as exc:
        _fallar_contrato_json(ruta, f"JSON inválido ({exc.msg})")
    if not isinstance(datos, dict):
        _fallar_contrato_json(ruta, "la raíz debe ser un objeto JSON")
    for clave_raiz in ("vigente", "versiones"):
        if clave_raiz not in datos:
            _fallar_contrato_json(ruta, f"falta la clave '{clave_raiz}'")
    vigente = datos["vigente"]
    versiones = datos["versiones"]
    if not isinstance(vigente, int) or isinstance(vigente, bool):
        _fallar_contrato_json(ruta, "'vigente' debe ser un entero")
    if not isinstance(versiones, dict) or not versiones:
        _fallar_contrato_json(ruta, "'versiones' debe ser un objeto no vacío")
    if str(vigente) not in versiones:
        _fallar_contrato_json(ruta, f"la versión vigente '{vigente}' no existe en 'versiones'")
    for ver, entrada in versiones.items():
        _validar_entrada_contrato(ruta, str(ver), entrada)
    clave = str(vigente) if numero is None else str(numero)
    return dict(versiones[clave])


def _construir_orden_etapas(contrato: dict) -> tuple[tuple[str, str, tuple[int, ...]], ...]:
    ultima = contrato["ultima_seccion"]
    return tuple(
        (etapa, etapa.capitalize(), tuple(range(1, int(ultima[etapa]) + 1)))
        for etapa in contrato["etapas"]
    )


def _sin_acentos(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )

PLACEHOLDER_PATTERNS_CI: tuple[str, ...] = (
    r"\[RELLENAR\]",
    r"\[T[ií]tulo claro",
    r"<t[ií]tulo que nombra",
    r"<quien responde",
)

PLACEHOLDER_PATTERNS_CS: tuple[str, ...] = (
    r"\[TODO\]",
    r"\bTODO:",
    r"\bTBD\b",
    r"\bFIXME\b",
)


def find_placeholder(text: str) -> str | None:
    """Detecta marcadores de plantilla sin confundir la palabra espanola 'todo'."""
    for ph in PLACEHOLDER_PATTERNS_CI:
        m = re.search(ph, text, flags=re.IGNORECASE)
        if m:
            return m.group(0)
    for ph in PLACEHOLDER_PATTERNS_CS:
        m = re.search(ph, text)
        if m:
            return m.group(0)
    return None


class ContractError(Exception):
    """Error cuando el archivo Markdown no cumple el contrato del A3."""


@dataclass
class MarkdownTable:
    headers: list[str]
    rows: list[list[str]]


@dataclass
class IshikawaBranch:
    name: str
    hypothesis: str
    evidence: str
    state: str


@dataclass
class PickOption:
    code: str
    full_option: str
    cause: str
    level: str
    impact: str
    effort: str
    quadrant: str
    decision: str
    prediction: str


@dataclass
class StateMapStep:
    step: str
    who: str
    duration: str
    problem: str
    has_problem: bool


@dataclass
class A3Section:
    number: int
    title: str
    required_from_stage: str
    raw_lines: list[str] = field(default_factory=list)
    present: bool = False


@dataclass
class A3Document:
    title: str
    owner: str
    coach: str
    version: str
    stage: str
    objective: str | None
    extra_meta: list[tuple[str, str]]
    brecha: str
    sections: dict[int, A3Section]
    next_steps_lines: list[str] | None
    ishikawa_branches: list[IshikawaBranch] | None = None
    ishikawa_no_aplica: bool = False
    pick_options: list[PickOption] | None = None
    pick_unica_opcion: bool = False
    present_map: list[StateMapStep] | None = None
    future_map: list[StateMapStep] | None = None
    stages_order: tuple[tuple[str, str, tuple[int, ...]], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Lienzo:
    """Variante de un dibujo: ancho del lienzo y tamanos de letra, en unidades del lienzo."""

    variante: str
    ancho: int
    titulo: float
    cuerpo: float
    etiqueta: float

    @property
    def ancha(self) -> bool:
        return self.variante == "ancha"


# Cada dibujo va dos veces en la pagina y el CSS deja a la vista una sola segun el ancho que el
# dibujo tiene (no el de la ventana): unos 340 px en un telefono de 412 px y unos 496 px en cada
# columna del escritorio. La angosta se dibuja a 340 con letra de 12 o mas, que sigue por encima
# de 10 px en pantalla en un telefono de 360 px. La ancha se dibuja a 480 y solo aparece cuando
# el contenedor mide 480 px o mas, asi que nunca se ve encogida.
ANGOSTO = Lienzo("angosta", 340, 14, 12.5, 12)
ANCHO = Lienzo("ancha", 480, 13.5, 12, 11)
# El indicador de etapas vive en la cabecera, que dispone de otro ancho.
ETAPAS_ANGOSTO = 320
ETAPAS_ANCHO = 660


CSS_STYLES = """
:root {
  --color-primary: #faff69;
  --color-primary-active: #e6eb52;
  --color-primary-disabled: #3a3a1f;
  --color-ink: #ffffff;
  --color-body: #cccccc;
  --color-body-strong: #e6e6e6;
  --color-muted: #888888;
  --color-muted-soft: #5a5a5a;
  --color-hairline: #2a2a2a;
  --color-hairline-strong: #3a3a3a;
  --color-canvas: #0a0a0a;
  --color-surface-soft: #121212;
  --color-surface-card: #1a1a1a;
  --color-surface-elevated: #242424;
  --color-surface-yellow-band: #faff69;
  --color-on-primary: #0a0a0a;
  --color-on-dark: #ffffff;
  --color-on-yellow: #0a0a0a;
  --color-accent-emerald: #22c55e;
  --color-accent-rose: #ef4444;
  --color-accent-blue: #3b82f6;
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --font-primary: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'DejaVu Sans', sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  --type-display-sm-size: 32px;
  --type-display-sm-lh: 1.2;
  --type-display-sm-ls: -1px;
  --type-title-lg-size: 24px;
  --type-title-lg-lh: 1.3;
  --type-title-lg-ls: -0.3px;
  --type-title-md-size: 18px;
  --type-title-md-lh: 1.4;
  --type-title-sm-size: 16px;
  --type-title-sm-lh: 1.4;
  --type-body-md-size: 16px;
  --type-body-md-lh: 1.55;
  --type-body-sm-size: 14px;
  --type-body-sm-lh: 1.55;
  --type-caption-size: 13px;
  --type-caption-lh: 1.4;
  --type-caption-up-size: 12px;
  --type-caption-up-lh: 1.4;
  --type-caption-up-ls: 1.5px;
  --type-code-size: 14px;
  --type-code-lh: 1.55;
  --spacing-xxs: 4px;
  --spacing-xs: 8px;
  --spacing-sm: 12px;
  --spacing-md: 16px;
  --spacing-lg: 24px;
  --spacing-xl: 32px;
  --spacing-xxl: 48px;
  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-pill: 9999px;
  --layout-max-width: 1200px;
}
*, *::before, *::after {
  box-sizing: border-box;
}
html, body {
  margin: 0;
  padding: 0;
  background-color: var(--color-canvas);
  color: var(--color-body);
  font-family: var(--font-primary);
  font-size: var(--type-body-sm-size);
  line-height: var(--type-body-sm-lh);
  -webkit-text-size-adjust: 100%;
}
.a3-page {
  max-width: var(--layout-max-width);
  margin: 0 auto;
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}
.a3-header {
  background-color: var(--color-surface-card);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}
.a3-header-top {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-xs);
}
.kicker {
  font-size: var(--type-caption-up-size);
  line-height: var(--type-caption-up-lh);
  letter-spacing: var(--type-caption-up-ls);
  text-transform: uppercase;
  color: var(--color-primary);
  font-weight: 700;
}
.badge-pill {
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius-pill);
  padding: var(--spacing-xxs) var(--spacing-sm);
  font-size: var(--type-caption-up-size);
  line-height: var(--type-caption-up-lh);
  letter-spacing: var(--type-caption-up-ls);
  text-transform: uppercase;
  font-weight: 700;
}
.badge-yellow {
  background-color: var(--color-primary);
  color: var(--color-on-primary);
}
.badge-dark {
  background-color: var(--color-surface-elevated);
  color: var(--color-body-strong);
  border: 1px solid var(--color-hairline-strong);
  letter-spacing: 0.4px;
  text-transform: none;
  font-size: var(--type-caption-size);
  font-weight: 500;
}
.badge-success {
  background-color: var(--color-surface-soft);
  color: var(--color-success);
  border: 1px solid var(--color-success);
}
.badge-warning {
  background-color: var(--color-surface-soft);
  color: var(--color-warning);
  border: 1px solid var(--color-warning);
}
.badge-muted {
  background-color: var(--color-surface-soft);
  color: var(--color-muted);
  border: 1px solid var(--color-hairline-strong);
}
.a3-title {
  margin: 0;
  color: var(--color-ink);
  font-size: var(--type-title-lg-size);
  line-height: var(--type-title-lg-lh);
  letter-spacing: var(--type-title-lg-ls);
  font-weight: 700;
  overflow-wrap: anywhere;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: var(--spacing-xs);
}
.meta-item {
  background-color: var(--color-surface-soft);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  padding: var(--spacing-xs) var(--spacing-sm);
  min-width: 0;
}
.meta-label {
  display: block;
  font-size: var(--type-caption-up-size);
  line-height: var(--type-caption-up-lh);
  letter-spacing: var(--type-caption-up-ls);
  text-transform: uppercase;
  color: var(--color-muted);
  margin-bottom: 2px;
}
.meta-value {
  color: var(--color-ink);
  font-size: var(--type-body-sm-size);
  font-weight: 600;
  overflow-wrap: anywhere;
}
.objective-banner {
  background-color: var(--color-surface-soft);
  border-left: 3px solid var(--color-primary);
  border-radius: var(--radius-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-body-strong);
  overflow-wrap: anywhere;
}
.stage-bar-wrap {
  background-color: var(--color-surface-soft);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-md);
  padding: var(--spacing-xs) var(--spacing-sm);
}
.a3-columns {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--spacing-md);
  align-items: start;
}
.a3-col {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  min-width: 0;
}
@media (min-width: 960px) {
  .a3-page {
    padding: var(--spacing-lg);
    gap: var(--spacing-lg);
  }
  .a3-title {
    font-size: var(--type-display-sm-size);
    line-height: var(--type-display-sm-lh);
    letter-spacing: var(--type-display-sm-ls);
  }
  .a3-columns {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: var(--spacing-lg);
  }
}
.section-card {
  background-color: var(--color-surface-card);
  border: 1px solid var(--color-hairline);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  min-width: 0;
}
.section-card-pending {
  background-color: var(--color-surface-soft);
  border-style: dashed;
  border-color: var(--color-hairline-strong);
}
.section-card-next {
  border-color: var(--color-primary-disabled);
  background-color: var(--color-surface-card);
}
.section-title {
  margin: 0;
  color: var(--color-ink);
  font-size: var(--type-title-md-size);
  line-height: var(--type-title-md-lh);
  font-weight: 700;
  padding-bottom: var(--spacing-xs);
  border-bottom: 1px solid var(--color-hairline);
}
.subsection-title {
  margin: var(--spacing-xs) 0 0 0;
  color: var(--color-body-strong);
  font-size: var(--type-title-sm-size);
  line-height: var(--type-title-sm-lh);
  font-weight: 600;
}
.brecha-callout {
  background-color: var(--color-surface-soft);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--color-ink);
}
.brecha-label {
  display: block;
  font-size: var(--type-caption-up-size);
  letter-spacing: var(--type-caption-up-ls);
  text-transform: uppercase;
  color: var(--color-primary);
  font-weight: 700;
  margin-bottom: var(--spacing-xxs);
}
.brecha-text {
  font-size: var(--type-body-md-size);
  line-height: var(--type-body-md-lh);
  font-weight: 600;
  overflow-wrap: anywhere;
}
.pending-notice {
  margin: 0;
  color: var(--color-muted);
  font-size: var(--type-body-sm-size);
  font-style: italic;
}
.diagram-box {
  background-color: var(--color-surface-soft);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-md);
  padding: var(--spacing-xs);
  width: 100%;
  overflow: hidden;
}
svg {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
}
p {
  margin: 0;
  color: var(--color-body);
  overflow-wrap: anywhere;
}
ul, ol {
  margin: 0;
  padding-left: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxs);
}
li {
  color: var(--color-body);
  overflow-wrap: anywhere;
}
li > ul, li > ol {
  margin-top: var(--spacing-xxs);
}
strong {
  color: var(--color-ink);
  font-weight: 600;
}
code {
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.45;
  background-color: var(--color-surface-elevated);
  color: var(--color-primary);
  padding: 1px 5px;
  border-radius: var(--radius-xs);
  overflow-wrap: break-word;
  word-break: normal;
}
.por-lo-tanto {
  color: var(--color-primary);
  font-weight: 600;
}
.no-apply-note {
  background-color: var(--color-surface-soft);
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-md);
  padding: var(--spacing-xs) var(--spacing-sm);
  color: var(--color-body-strong);
}
.table-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid var(--color-hairline-strong);
  border-radius: var(--radius-md);
  background-color: var(--color-surface-soft);
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--type-caption-size);
  line-height: var(--type-caption-lh);
}
th, td {
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
  border-bottom: 1px solid var(--color-hairline);
  overflow-wrap: break-word;
}
td code, th code {
  overflow-wrap: anywhere;
}
th {
  background-color: var(--color-surface-elevated);
  color: var(--color-ink);
  font-size: 11px;
  line-height: 1.3;
  letter-spacing: 0.7px;
  text-transform: uppercase;
  font-weight: 700;
  white-space: normal;
}
tr:last-child td {
  border-bottom: none;
}
.table-pick {
  overflow-x: visible;
}
.table-pick table, .table-pick tbody {
  display: block;
  width: 100%;
}
.table-pick thead {
  display: none;
}
.table-pick tr {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
  padding: var(--spacing-sm) var(--spacing-md);
  border-bottom: 1px solid var(--color-hairline-strong);
}
.table-pick tr:last-child {
  border-bottom: none;
}
.table-pick td {
  display: block;
  padding: 0;
  border-bottom: none;
  min-width: 0;
}
.table-pick td:first-child,
.table-pick td:last-child {
  grid-column: 1 / -1;
}
.table-pick td:first-child {
  color: var(--color-ink);
  font-weight: 600;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--color-hairline);
}
.table-pick td:last-child {
  padding-top: 6px;
  border-top: 1px dashed var(--color-hairline);
}
.table-pick td::before {
  content: attr(data-label);
  display: block;
  font-size: 10px;
  line-height: 1.3;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: var(--color-muted);
  font-weight: 700;
  margin-bottom: 2px;
}
@media (max-width: 680px) {
  .a3-page {
    padding: var(--spacing-sm);
    gap: var(--spacing-sm);
  }
  .a3-header, .section-card {
    padding: var(--spacing-md);
  }
  .diagram-box {
    padding: 6px;
  }
  .table-wrap {
    overflow-x: visible;
  }
  .table-wrap table, .table-wrap tbody {
    display: block;
    width: 100%;
  }
  .table-wrap thead {
    display: none;
  }
  .table-wrap:not(.table-pick) tr {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--color-hairline-strong);
  }
  .table-wrap:not(.table-pick) tr:last-child {
    border-bottom: none;
  }
  .table-wrap:not(.table-pick) td {
    display: block;
    padding: 0;
    border-bottom: none;
    min-width: 0;
  }
  .table-wrap:not(.table-pick) td:first-child {
    color: var(--color-ink);
    font-weight: 600;
  }
  .table-wrap:not(.table-pick) td::before {
    content: attr(data-label);
    display: block;
    font-size: 10px;
    line-height: 1.3;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: var(--color-muted);
    font-weight: 700;
    margin-bottom: 2px;
  }
}
""".strip()

CSS_DIBUJOS = f"""
.dibujo {{
  container-type: inline-size;
}}
.dibujo > svg {{
  margin: 0 auto;
}}
.dibujo > [data-variante="angosta"] {{
  max-width: 380px;
}}
.dibujo > [data-variante="ancha"] {{
  display: none;
  max-width: 600px;
}}
.dibujo-etapas > [data-variante="ancha"] {{
  max-width: 760px;
}}
@container (min-width: {ANCHO.ancho}px) {{
  .dibujo:not(.dibujo-etapas) > [data-variante="angosta"] {{
    display: none;
  }}
  .dibujo:not(.dibujo-etapas) > [data-variante="ancha"] {{
    display: block;
  }}
}}
@container (min-width: {ETAPAS_ANCHO}px) {{
  .dibujo-etapas > [data-variante="angosta"] {{
    display: none;
  }}
  .dibujo-etapas > [data-variante="ancha"] {{
    display: block;
  }}
}}
""".strip()


def esc(text: str) -> str:
    """Escapa texto plano para insercion segura en HTML y atributos SVG."""
    return html.escape(text, quote=True)


def strip_md_inline(text: str) -> str:
    """Limpia marcas simples de Markdown conservando el texto literal sin escapar."""
    cleaned = text.strip()
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*(.+?)\*\*", r"\1", cleaned)
    return cleaned.strip()


def format_inline_md(text: str) -> str:
    """Convierte codigo en linea y negritas escapando todo contenido de origen."""
    parts = re.split(r"(`[^`]+`)", text)
    rendered: list[str] = []
    for part in parts:
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            rendered.append(f"<code>{esc(part[1:-1])}</code>")
        else:
            escaped = esc(part)
            escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
            rendered.append(escaped)
    return "".join(rendered)


# Avance de cada caracter ASCII (del 32 al 126) en centesimas de em, medido en un navegador con
# una de las fuentes de sistema mas anchas, en peso normal y en negrita. Con una fuente mas
# angosta el texto ocupa menos de lo estimado: el corte de renglones queda del lado seguro.
_AVANCE_NORMAL: tuple[int, ...] = tuple(
    int(n)
    for n in (
        "32 40 46 84 64 95 78 27 39 39 50 84 32 36 32 34 64 64 64 64 64 64 64 64 64 64 34 34 84 84 84 53 "
        "100 71 69 70 77 63 58 77 75 29 29 66 56 86 75 79 60 79 69 63 60 73 68 99 69 61 69 39 34 39 84 50 "
        "50 61 63 55 63 62 35 63 63 28 28 58 28 97 63 61 63 63 40 52 39 63 59 82 59 59 52 64 34 64 84"
    ).split()
)
_AVANCE_NEGRITA: tuple[int, ...] = tuple(
    int(n)
    for n in (
        "35 46 52 84 70 100 87 31 46 46 52 84 38 42 38 37 70 70 70 70 70 70 70 70 70 70 40 40 84 84 84 58 "
        "100 77 76 73 83 68 68 82 84 37 37 77 64 100 84 85 73 85 77 68 70 81 77 110 77 72 73 46 37 46 84 50 "
        "50 67 72 59 72 68 44 72 71 34 34 67 34 104 71 69 72 72 49 60 48 71 65 92 65 65 58 71 37 71 84"
    ).split()
)
# Signos fuera del ASCII que usan los dibujos o el español: (normal, negrita). El resto de los
# caracteres se mide por su letra base sin acento y, si no la tiene, como 1 em.
_AVANCE_OTROS: dict[str, tuple[int, int]] = {
    "·": (32, 38),
    "¿": (53, 58),
    "¡": (40, 46),
    "°": (50, 50),
    "✓": (84, 84),
}


def char_advances(text: str, *, bold: bool = False) -> list[int]:
    """Avance de cada caracter del texto, en centesimas de em."""
    tabla = _AVANCE_NEGRITA if bold else _AVANCE_NORMAL
    columna = 1 if bold else 0
    avances: list[int] = []
    for ch in text:
        base = ch if ch <= "~" else unicodedata.normalize("NFD", ch)[0]
        if " " <= base <= "~":
            avances.append(tabla[ord(base) - 32])
        else:
            avances.append(_AVANCE_OTROS.get(ch, (100, 100))[columna])
    return avances


def text_width(text: str, size: float, *, bold: bool = False, spacing: float = 0.0) -> float:
    """Estima el ancho de un renglon letra por letra, en unidades del lienzo."""
    return sum(char_advances(text, bold=bold)) * size / 100.0 + spacing * len(text)


def split_long_word(word: str, limit: float, size: float, *, bold: bool = False) -> list[str]:
    """Corta con guion una palabra que no cabe en limit; el ultimo trozo va sin guion.

    Los avances se acumulan una sola vez y cada corte se busca con un barrido sobre esa suma:
    el costo es lineal en el largo de la palabra. Medir cada candidato entero lo hacia cubico.
    """
    acumulado = [0, *itertools.accumulate(char_advances(word, bold=bold))]
    guion = char_advances("-", bold=bold)[0]

    def fits(avance: int) -> bool:
        return avance * size / 100.0 <= limit  # la misma cuenta que text_width

    pieces: list[str] = []
    start = 0
    end = len(word)
    while end - start > 1 and not fits(acumulado[end] - acumulado[start]):
        cut = start + 1  # al menos una letra por trozo, aunque no quepa
        while cut + 1 < end and fits(acumulado[cut + 1] - acumulado[start] + guion):
            cut += 1
        pieces.append(word[start:cut] + "-")
        start = cut
    pieces.append(word[start:])
    return pieces


def wrap_text(text: str, max_w: float, size: float, *, bold: bool = False) -> list[str]:
    """Parte un texto en renglones que caben en max_w segun el ancho de sus letras."""
    clean = re.sub(r"\s+", " ", strip_md_inline(text)).strip()
    if not clean:
        return ["-"]
    limit = max_w * 0.97

    def fits(candidate: str) -> bool:
        return text_width(candidate, size, bold=bold) <= limit

    lines: list[str] = []
    current = ""
    for word in clean.split(" "):
        joined = f"{current} {word}" if current else word
        if fits(joined):
            current = joined
            continue
        if current:
            lines.append(current)
        # Una palabra que sola no cabe se corta con guion.
        *enteros, current = split_long_word(word, limit, size, bold=bold)
        lines.extend(enteros)
    lines.append(current)
    return lines


def fmt(value: float) -> str:
    """Escribe un numero de atributo SVG sin ceros de sobra."""
    return f"{value:.1f}".rstrip("0").rstrip(".")


def svg_open(css_class: str, width: int, height: float, variante: str, label: str, extra: str = "") -> str:
    return (
        f'<svg class="{css_class}"{extra} viewBox="0 0 {width} {math.ceil(height)}" '
        f'data-variante="{variante}" role="img" aria-label="{esc(label)}">'
    )


def svg_text(
    x: float,
    y: float,
    content: str,
    size: float,
    fill: str,
    *,
    weight: int = 400,
    anchor: str = "start",
    spacing: float = 0.0,
    rotated: bool = False,
) -> str:
    """Un renglon de texto SVG con su contenido escapado."""
    attrs = f'x="{fmt(x)}" y="{fmt(y)}"'
    if anchor != "start":
        attrs += f' text-anchor="{anchor}"'
    if rotated:
        attrs += f' transform="rotate(-90 {fmt(x)} {fmt(y)})"'
    attrs += f' fill="{fill}" font-size="{fmt(size)}"'
    if weight != 400:
        attrs += f' font-weight="{weight}"'
    if spacing:
        attrs += f' letter-spacing="{fmt(spacing)}"'
    return f"<text {attrs}>{esc(content)}</text>"


def svg_text_lines(
    x: float, y: float, lines: list[str], size: float, line_h: float, fill: str, *, weight: int = 400
) -> str:
    """Varios renglones de texto SVG alineados a la izquierda, uno por <tspan>."""
    tspans = "".join(
        f'<tspan x="{fmt(x)}" dy="{fmt(line_h if idx else 0)}">{esc(ln)}</tspan>'
        for idx, ln in enumerate(lines)
    )
    weight_attr = f' font-weight="{weight}"' if weight != 400 else ""
    return (
        f'<text x="{fmt(x)}" y="{fmt(y)}" fill="{fill}" font-size="{fmt(size)}"{weight_attr}>'
        f"{tspans}</text>"
    )


def draw_variants(wrapper_class: str, draw: Callable[[Lienzo], str]) -> str:
    """Envuelve las dos variantes de un dibujo: el CSS deja a la vista una segun el ancho."""
    return f'<div class="{wrapper_class} dibujo">{draw(ANGOSTO)}{draw(ANCHO)}</div>'


def parse_table_row(line: str) -> list[str]:
    stripped = line.strip()
    parts = re.split(r"(?<!\\)\|", stripped)
    if stripped.startswith("|") and parts:
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [cell.replace(r"\|", "|").strip() for cell in parts]


def is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if "|" not in stripped:
        return False
    cells = parse_table_row(stripped)
    if not cells:
        return False
    return all(bool(re.match(r"^:?-{2,}:?$", c.strip())) for c in cells)


def has_meaningful_content(lines: list[str]) -> bool:
    for line in lines:
        s = line.strip()
        if not s:
            continue
        low = strip_md_inline(s).lower()
        if low in {"-", "pendiente", "vacio", "vacío", "n/a", "(pendiente)"}:
            continue
        return True
    return False


def extract_tables_from_lines(lines: list[str]) -> list[tuple[str | None, MarkdownTable]]:
    """Extrae todas las tablas Markdown de una seccion junto con el ultimo H3 previo."""
    found: list[tuple[str | None, MarkdownTable]] = []
    current_h3: str | None = None
    i = 0
    n = len(lines)
    while i < n:
        stripped = lines[i].strip()
        m_h3 = re.match(r"^###\s+(.+)$", stripped)
        if m_h3:
            current_h3 = strip_md_inline(m_h3.group(1))
            i += 1
            continue
        if "|" in stripped and i + 1 < n and is_table_separator(lines[i + 1]):
            headers = parse_table_row(stripped)
            i += 2
            rows: list[list[str]] = []
            while i < n and "|" in lines[i].strip() and lines[i].strip():
                if not is_table_separator(lines[i]):
                    rows.append(parse_table_row(lines[i]))
                i += 1
            found.append((current_h3, MarkdownTable(headers=headers, rows=rows)))
            continue
        i += 1
    return found


def is_ishikawa_table(table: MarkdownTable) -> bool:
    if len(table.headers) < 4:
        return False
    first_col = strip_md_inline(table.headers[0]).lower()
    return first_col == "rama"


def parse_ishikawa_section(
    sec_lines: list[str], *, required: bool, contrato: dict | None = None
) -> tuple[list[IshikawaBranch] | None, bool]:
    contrato_act = contrato or cargar_contrato(1)
    ishikawa_branches = tuple(contrato_act["ramas"])
    _ = contrato_act.get("subramas", {})
    estados_validos = {str(s).upper() for s in contrato_act["estados_rama"]}
    sec_plain = "\n".join(strip_md_inline(ln) for ln in sec_lines)
    if re.search(r"\bIshikawa:\s*no\s+aplica\b", sec_plain, flags=re.IGNORECASE):
        return None, True

    tables = extract_tables_from_lines(sec_lines)
    ishi_table: MarkdownTable | None = None
    for _, tbl in tables:
        if is_ishikawa_table(tbl):
            ishi_table = tbl
            break

    if ishi_table is None:
        if required:
            raise ContractError(
                "En la sección 4 ('Análisis de Causa Raíz') falta la tabla de Ishikawa "
                "o la línea 'Ishikawa: no aplica, una sola hipótesis (<cuál>)'."
            )
        return None, False

    if len(ishi_table.rows) != len(ishikawa_branches):
        expected_str = ", ".join(ishikawa_branches)
        raise ContractError(
            f"La tabla de Ishikawa debe tener exactamente las 6 ramas del contrato "
            f"({expected_str}); se encontraron {len(ishi_table.rows)} filas."
        )

    branches: list[IshikawaBranch] = []
    for idx, expected_name in enumerate(ishikawa_branches):
        row = ishi_table.rows[idx]
        if len(row) < 4:
            raise ContractError(
                f"La fila {idx + 1} de la tabla de Ishikawa tiene menos de 4 columnas."
            )
        rama_name = strip_md_inline(row[0])
        if rama_name != expected_name:
            raise ContractError(
                f"Rama de Ishikawa fuera de contrato en la fila {idx + 1}: "
                f"se esperaba '{expected_name}' y se encontró '{rama_name}'."
            )
        hypothesis = row[1].strip()
        evidence = row[2].strip()
        state = strip_md_inline(row[3]).upper()
        if state not in estados_validos:
            raise ContractError(
                f"Estado inválido '{row[3]}' en la rama '{expected_name}' del Ishikawa. "
                "Solo se admite 'FOCO' o 'DESCARTADA'."
            )
        if not hypothesis or not evidence:
            raise ContractError(
                f"La rama '{expected_name}' del Ishikawa debe incluir hipótesis y evidencia."
            )
        branches.append(
            IshikawaBranch(
                name=rama_name,
                hypothesis=hypothesis,
                evidence=evidence,
                state=state,
            )
        )

    return branches, False


def is_pick_table(table: MarkdownTable) -> bool:
    if len(table.headers) < 8:
        return False
    first_col = strip_md_inline(table.headers[0]).lower()
    return first_col in {"opción", "opcion"}


def extract_option_code(option_text: str, index: int) -> str:
    clean = strip_md_inline(option_text)
    m_code = re.match(r"^([A-Za-z]{1,4}-?\d+)\b", clean)
    if m_code:
        return m_code.group(1)
    first_token = clean.split(" ")[0] if clean else ""
    if 1 <= len(first_token) <= 8:
        return first_token
    return f"O-{index + 1}"


def parse_pick_section(
    sec_lines: list[str], *, required: bool, contrato: dict | None = None
) -> tuple[list[PickOption] | None, bool]:
    contrato_act = contrato or cargar_contrato(1)
    sec_plain = "\n".join(strip_md_inline(ln) for ln in sec_lines)
    if re.search(r"\b[ÚU]nica\s+opci[oó]n:\s*\S+", sec_plain, flags=re.IGNORECASE):
        return None, True

    tables = extract_tables_from_lines(sec_lines)
    pick_table: MarkdownTable | None = None
    for _, tbl in tables:
        if is_pick_table(tbl):
            pick_table = tbl
            break

    if pick_table is None:
        if required:
            raise ContractError(
                "En la sección 5 ('Contramedidas y Poka-Yoke') falta la tabla de opciones PICK "
                "o la línea 'Única opción: <motivo>'."
            )
        return None, False

    if len(pick_table.rows) < 2:
        raise ContractError(
            "La tabla PICK de la sección 5 exige al menos dos opciones reales "
            "(o la línea 'Única opción: <motivo>')."
        )

    expected_quadrant_map = {
        (str(entrada["impacto"]), str(entrada["esfuerzo"])): str(entrada["cuadrante"])
        for entrada in contrato_act["pick"]
    }
    quad_canon_map: dict[str, str] = {}
    for cuad in contrato_act["cuadrantes"]:
        quad_canon_map[cuad.lower()] = cuad
        quad_canon_map[_sin_acentos(cuad.lower())] = cuad
    decision_canon_map: dict[str, str] = {}
    for dec in contrato_act["decisiones"]:
        decision_canon_map[dec.lower()] = dec
        decision_canon_map[_sin_acentos(dec.lower())] = dec
    niveles_validos: set[str] = set()
    for niv in contrato_act["niveles"]:
        niv_low = niv.lower()
        niveles_validos.add(niv_low)
        niveles_validos.add(_sin_acentos(niv_low))
        niveles_validos.add(niv_low.replace("-", " "))

    options: list[PickOption] = []
    for idx, row in enumerate(pick_table.rows):
        if len(row) < 8:
            raise ContractError(
                f"La fila {idx + 1} de la tabla PICK tiene menos de 8 columnas."
            )
        full_opt = row[0].strip()
        cause = strip_md_inline(row[1])
        level = strip_md_inline(row[2]).lower()
        impact_raw = strip_md_inline(row[3]).lower()
        effort_raw = strip_md_inline(row[4]).lower()
        quad_raw = strip_md_inline(row[5]).lower()
        dec_raw = strip_md_inline(row[6]).lower()
        prediction = row[7].strip()

        if not full_opt or not cause or not prediction:
            raise ContractError(
                f"La opción en la fila {idx + 1} de la tabla PICK tiene celdas obligatorias vacías."
            )

        if level not in niveles_validos:
            raise ContractError(
                f"Nivel inválido '{row[2]}' en la fila {idx + 1} de la tabla PICK. "
                f"Valores admitidos: {', '.join(contrato_act['niveles'])}."
            )

        m_imp = re.match(r"^(alto|bajo)\b", impact_raw)
        if not m_imp:
            raise ContractError(
                f"Impacto inválido '{row[3]}' en la fila {idx + 1} de la tabla PICK. "
                "Debe ser 'alto' o 'bajo'."
            )
        impact_key = m_imp.group(1)

        m_eff = re.match(r"^(bajo|alto)\b", effort_raw)
        if not m_eff:
            raise ContractError(
                f"Esfuerzo inválido '{row[4]}' en la fila {idx + 1} de la tabla PICK. "
                "Debe iniciar con 'bajo' o 'alto'."
            )
        effort_key = m_eff.group(1)

        quad_canon = quad_canon_map.get(quad_raw)
        expected_quad = expected_quadrant_map[(impact_key, effort_key)]
        if quad_canon != expected_quad:
            raise ContractError(
                f"Cuadrante PICK incoherente en la fila {idx + 1} ('{row[0]}'): "
                f"para impacto '{impact_key}' y esfuerzo '{effort_key}' corresponde "
                f"'{expected_quad}', no '{row[5]}'."
            )

        dec_canon = decision_canon_map.get(dec_raw)
        if dec_canon is None:
            raise ContractError(
                f"Decisión inválida '{row[6]}' en la fila {idx + 1} de la tabla PICK. "
                "Valores admitidos: elegida, después, descartada."
            )

        if quad_canon == "Eliminar" and dec_canon == "elegida":
            raise ContractError(
                f"Violación de contrato en '{row[0]}': una opción en el cuadrante 'Eliminar' "
                "no puede estar marcada como 'elegida'."
            )

        options.append(
            PickOption(
                code=extract_option_code(full_opt, idx),
                full_option=full_opt,
                cause=cause,
                level="raíz" if level == "raiz" else level,
                impact=impact_key,
                effort=strip_md_inline(row[4]),
                quadrant=quad_canon,
                decision=dec_canon,
                prediction=prediction,
            )
        )

    return options, False


NO_PROBLEM_VALUES: frozenset[str] = frozenset(
    {
        "",
        "-",
        "\u2014",  # raya, escrita como secuencia de escape: el archivo no lleva el caracter
        "\u2013",  # semirraya
        "n/a",
        "na",
        "ninguno",
        "ninguna",
        "ningún",
        "ningun",
        "ningún problema",
        "ningun problema",
        "no",
        "ok",
        "sin problema",
        "sin problemas",
    }
)


def is_no_problem(cell: str) -> bool:
    """Dice si una celda Problema declara que no hay problema ("Ninguno.", "ninguno (limpio)").

    Compara sin la puntuacion final y sin lo que va entre parentesis. Si toda la celda va entre
    parentesis se compara lo de adentro: "(se corta la tubería)" sigue siendo un problema.
    """
    texto = strip_md_inline(cell).lower()
    fuera = re.sub(r"\([^()]*\)", " ", texto)
    if not fuera.strip(" .,;:!"):
        fuera = texto.replace("(", " ").replace(")", " ")
    return " ".join(fuera.split()).rstrip(" .,;:!") in NO_PROBLEM_VALUES


def state_map_kind_from_h3(h3_title: str | None) -> str | None:
    if not h3_title:
        return None
    m_map = re.match(
        r"^Mapa\s+del\s+estado\s+(presente|futuro)\b",
        strip_md_inline(h3_title),
        flags=re.IGNORECASE,
    )
    if not m_map:
        return None
    return m_map.group(1).lower()


def is_state_map_table(table: MarkdownTable, h3_title: str | None) -> bool:
    if state_map_kind_from_h3(h3_title) is None:
        return False
    if len(table.headers) < 4:
        return False
    first_col = strip_md_inline(table.headers[0]).lower()
    fourth_col = strip_md_inline(table.headers[3]).lower()
    return first_col == "paso" and fourth_col.startswith("problema")


def parse_state_map_table(table: MarkdownTable, kind: str) -> list[StateMapStep]:
    if len(table.headers) < 4:
        raise ContractError(
            f"La tabla 'Mapa del estado {kind}' debe tener las 4 columnas del contrato: "
            "Paso | Quién | Tiempo | Problema."
        )
    if not table.rows:
        raise ContractError(f"La tabla 'Mapa del estado {kind}' no tiene pasos.")

    steps: list[StateMapStep] = []
    for idx, row in enumerate(table.rows):
        if len(row) < 4:
            raise ContractError(
                f"La fila {idx + 1} de 'Mapa del estado {kind}' tiene menos de 4 columnas."
            )
        step_txt = row[0].strip()
        who_txt = row[1].strip()
        time_txt = row[2].strip()
        prob_txt = row[3].strip()
        if not step_txt:
            raise ContractError(
                f"El nombre del paso en la fila {idx + 1} de 'Mapa del estado {kind}' está vacío."
            )
        has_prob = not is_no_problem(prob_txt)
        steps.append(
            StateMapStep(
                step=step_txt,
                who=who_txt or "-",
                duration=time_txt or "-",
                problem=prob_txt,
                has_problem=has_prob,
            )
        )
    return steps


def parse_a3_markdown(md_text: str) -> A3Document:
    if not md_text.strip():
        raise ContractError("El documento A3 está vacío.")

    lines = md_text.splitlines()

    # 1. Buscar titulo H1 del contrato (# A3: ...)
    title: str | None = None
    h1_idx = -1
    for idx, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        m_h1 = re.match(r"^#\s+A3:\s*(.+)$", s, flags=re.IGNORECASE)
        if m_h1:
            title = strip_md_inline(m_h1.group(1))
            h1_idx = idx
        break

    if title is None or not title:
        raise ContractError(
            "Cabecera fuera de contrato: la primera línea con contenido debe ser '# A3: <título>'."
        )

    if find_placeholder(title) is not None:
        raise ContractError(f"El título del A3 contiene un marcador sin completar: '{title}'.")

    # 2. Separar cabecera y secciones H2 (ignorando bloques de codigo cercados)
    h2_indices: list[tuple[int, str]] = []
    in_fence = False
    for idx in range(h1_idx + 1, len(lines)):
        if lines[idx].strip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and re.match(r"^##\s+\S+", lines[idx]):
            h2_indices.append((idx, lines[idx].strip()))

    header_end = h2_indices[0][0] if h2_indices else len(lines)
    header_lines = lines[h1_idx + 1 : header_end]

    meta_map: dict[str, str] = {}
    extra_meta: list[tuple[str, str]] = []
    for raw in header_lines:
        s = raw.strip()
        if not s:
            continue
        m_meta = re.match(r"^[-*]\s*\*\*([^*:]+?):?\*\*:?\s*(.*)$", s)
        if not m_meta:
            continue
        key_raw = m_meta.group(1).strip()
        val_raw = m_meta.group(2).strip()
        key_norm = key_raw.lower()
        if key_norm == "propietario":
            meta_map["propietario"] = strip_md_inline(val_raw)
        elif re.match(r"^coach\s*/\s*revisor$", key_norm):
            meta_map["coach"] = strip_md_inline(val_raw)
        elif key_norm in {"versión", "version"}:
            meta_map["version"] = strip_md_inline(val_raw)
        elif key_norm == "etapa":
            meta_map["etapa"] = strip_md_inline(val_raw).lower()
        elif key_norm == "contrato":
            if "contrato" not in meta_map:
                meta_map["contrato"] = val_raw
        elif key_norm == "objetivo que apoya":
            if val_raw:
                meta_map["objetivo"] = strip_md_inline(val_raw)
        else:
            extra_meta.append((key_raw, val_raw))

    missing_header: list[str] = []
    for req_key, label in (
        ("propietario", "Propietario"),
        ("coach", "Coach / Revisor"),
        ("version", "Versión"),
        ("etapa", "Etapa"),
    ):
        if not meta_map.get(req_key):
            missing_header.append(label)

    if missing_header:
        raise ContractError(
            "Faltan campos obligatorios en la cabecera del contrato A3: "
            + ", ".join(missing_header)
            + "."
        )

    if "contrato" not in meta_map:
        contrato_act = cargar_contrato(1)
    else:
        val_contrato = meta_map["contrato"]
        if re.fullmatch(r"[0-9]+", val_contrato) and str(int(val_contrato)) == val_contrato:
            try:
                contrato_act = cargar_contrato(int(val_contrato))
            except KeyError:
                raise ContractError(
                    f"Cabecera: el Contrato '{val_contrato}' no existe; los válidos son 1 y 2"
                ) from None
        else:
            raise ContractError(
                f"Cabecera: el Contrato '{val_contrato}' no existe; los válidos son 1 y 2"
            )
    stages_order = _construir_orden_etapas(contrato_act)
    stage_index = {key: idx for idx, (key, _, _) in enumerate(stages_order)}

    stage = meta_map["etapa"]
    if stage not in stage_index:
        valid_list = ", ".join(k for k, _, _ in stages_order)
        raise ContractError(
            f"Etapa inválida '{meta_map['etapa']}' en la cabecera. "
            f"Valores admitidos por el contrato: {valid_list}."
        )

    # 3. Mapear secciones 1..7 y Siguientes pasos
    sections: dict[int, A3Section] = {
        num: A3Section(number=num, title=canon_title, required_from_stage=req_stage)
        for num, _, canon_title, req_stage in SECTION_SPECS
    }
    next_steps_lines: list[str] | None = None

    for pos, (start_line, heading_text) in enumerate(h2_indices):
        end_line = h2_indices[pos + 1][0] if pos + 1 < len(h2_indices) else len(lines)
        body = lines[start_line + 1 : end_line]

        matched_num: int | None = None
        for num, pattern, _, _ in SECTION_SPECS:
            if re.match(pattern, heading_text, flags=re.IGNORECASE):
                matched_num = num
                break

        if matched_num is not None:
            sec = sections[matched_num]
            sec.present = True
            sec.raw_lines = body
        elif re.match(r"^##\s+Siguientes\s+pasos\b", heading_text, flags=re.IGNORECASE):
            next_steps_lines = body
        else:
            raise ContractError(f"Sección desconocida fuera del contrato A3: '{heading_text}'.")

    # 4. Verificar secciones obligatorias segun la etapa
    _, _, required_nums = stages_order[stage_index[stage]]
    for req_num in required_nums:
        sec = sections[req_num]
        if not sec.present or not has_meaningful_content(sec.raw_lines):
            raise ContractError(
                f"La etapa '{stage}' exige completar la sección '{sec.title}', "
                "pero está ausente o vacía."
            )
        joined = "\n".join(sec.raw_lines)
        found_ph = find_placeholder(joined)
        if found_ph is not None:
            raise ContractError(
                f"La sección '{sec.title}' contiene un marcador sin completar: '{found_ph}'."
            )

    # 5. Extraer Brecha obligatoria en seccion 2
    brecha: str | None = None
    for raw in sections[2].raw_lines:
        m_br = re.match(
            r"^\s*(?:[-*]\s*)?\*\*Brecha:?\*\*:?\s*(.+)$", raw.strip(), flags=re.IGNORECASE
        )
        if m_br:
            candidate = strip_md_inline(m_br.group(1))
            if candidate:
                brecha = candidate
                break

    if not brecha:
        raise ContractError(
            "La sección 2 ('Estado Actual en el Gemba') debe incluir la línea obligatoria "
            "'- **Brecha:** de X (medido) a Y (meta) para <cuándo>'."
        )

    # 6. Analizar Ishikawa en seccion 4
    sec4_required = stage_index[stage] >= stage_index["analizar"]
    ishi_branches, ishi_no_aplica = (None, False)
    if sections[4].present and has_meaningful_content(sections[4].raw_lines):
        ishi_branches, ishi_no_aplica = parse_ishikawa_section(
            sections[4].raw_lines, required=sec4_required, contrato=contrato_act
        )
    elif sec4_required:
        parse_ishikawa_section([], required=True, contrato=contrato_act)

    # 7. Analizar matriz PICK en seccion 5
    sec5_required = stage_index[stage] >= stage_index["proponer"]
    pick_opts, pick_unica = (None, False)
    if sections[5].present and has_meaningful_content(sections[5].raw_lines):
        pick_opts, pick_unica = parse_pick_section(
            sections[5].raw_lines, required=sec5_required, contrato=contrato_act
        )
    elif sec5_required:
        parse_pick_section([], required=True, contrato=contrato_act)

    # 8. Extraer mapas de estado presente y futuro (opcionales)
    present_map: list[StateMapStep] | None = None
    future_map: list[StateMapStep] | None = None
    for sec in sections.values():
        if not sec.present:
            continue
        for h3_title, tbl in extract_tables_from_lines(sec.raw_lines):
            kind = state_map_kind_from_h3(h3_title)
            if kind == "presente":
                present_map = parse_state_map_table(tbl, "presente")
            elif kind == "futuro":
                future_map = parse_state_map_table(tbl, "futuro")

    return A3Document(
        title=title,
        owner=meta_map["propietario"],
        coach=meta_map["coach"],
        version=meta_map["version"],
        stage=stage,
        objective=meta_map.get("objetivo"),
        extra_meta=extra_meta,
        brecha=brecha,
        sections=sections,
        next_steps_lines=next_steps_lines,
        ishikawa_branches=ishi_branches,
        ishikawa_no_aplica=ishi_no_aplica,
        pick_options=pick_opts,
        pick_unica_opcion=pick_unica,
        present_map=present_map,
        future_map=future_map,
        stages_order=stages_order,
    )


STAGES_SECTIONS: tuple[str, ...] = ("Secc. 1-2", "Secc. 3-4", "Secc. 5", "Secc. 6", "Secc. 7")


def _stage_visual_state(idx: int, current_idx: int, stage_label: str) -> tuple[str, str, str]:
    """Devuelve (estado, titulo_prefijado, subtitulo) de una etapa segun el avance."""
    if idx < current_idx:
        return ("completada", f"✓ {stage_label}", STAGES_SECTIONS[idx])
    if idx == current_idx:
        return ("actual", f"{idx + 1}. {stage_label}", f"Activa · {STAGES_SECTIONS[idx]}")
    return ("pendiente", f"{idx + 1}. {stage_label}", "Pendiente")


def _draw_stages_narrow(
    current_stage: str,
    stages_order: tuple[tuple[str, str, tuple[int, ...]], ...] | None = None,
) -> str:
    if not stages_order:
        stages_order = _construir_orden_etapas(cargar_contrato(1))
    stage_index = {key: idx for idx, (key, _, _) in enumerate(stages_order)}
    current_idx = stage_index[current_stage]
    row_h = 34
    gap = 4
    pad_y = 6
    view_h = pad_y * 2 + len(stages_order) * row_h + (len(stages_order) - 1) * gap
    parts: list[str] = [
        svg_open(
            "svg-etapas",
            ETAPAS_ANGOSTO,
            view_h,
            "angosta",
            f"Indicador de etapa del A3: {current_stage}",
        )
    ]

    for idx in range(len(stages_order) - 1):
        cy1 = pad_y + idx * (row_h + gap) + row_h / 2
        cy2 = cy1 + row_h + gap
        line_color = "#22c55e" if idx < current_idx else "#3a3a3a"
        parts.append(
            f'<line x1="22" y1="{fmt(cy1)}" x2="22" y2="{fmt(cy2)}" '
            f'stroke="{line_color}" stroke-width="2"/>'
        )

    for idx, (stage_key, stage_label, _) in enumerate(stages_order):
        ry = pad_y + idx * (row_h + gap)
        cy = ry + row_h / 2
        ty = ry + 21.5
        estado, title_txt, sub_txt = _stage_visual_state(idx, current_idx, stage_label)
        parts.append(f'<g data-etapa="{esc(stage_key)}" data-etapa-estado="{estado}">')
        if estado == "actual":
            parts.append(
                f'<rect x="6" y="{fmt(ry)}" width="308" height="{row_h}" rx="8" '
                f'fill="#faff69" stroke="#faff69" stroke-width="1.5"/>'
                f'<circle cx="22" cy="{fmt(cy)}" r="5" fill="#0a0a0a"/>'
                + svg_text(36, ty, title_txt, 13, "#0a0a0a", weight=700)
                + svg_text(302, ty, sub_txt, 12, "#0a0a0a", weight=600, anchor="end")
            )
        elif estado == "completada":
            parts.append(
                f'<circle cx="22" cy="{fmt(cy)}" r="5.5" fill="#121212" '
                f'stroke="#22c55e" stroke-width="2"/>'
                f'<circle cx="22" cy="{fmt(cy)}" r="2.2" fill="#22c55e"/>'
                + svg_text(36, ty, title_txt, 13, "#22c55e", weight=700)
                + svg_text(302, ty, sub_txt, 12, "#cccccc", weight=500, anchor="end")
            )
        else:
            parts.append(
                f'<circle cx="22" cy="{fmt(cy)}" r="5" fill="#121212" '
                f'stroke="#5a5a5a" stroke-width="1.5"/>'
                + svg_text(36, ty, title_txt, 13, "#888888", weight=600)
                + svg_text(302, ty, sub_txt, 12, "#6e6e6e", weight=500, anchor="end")
            )
        parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)


def _draw_stages_wide(
    current_stage: str,
    stages_order: tuple[tuple[str, str, tuple[int, ...]], ...] | None = None,
) -> str:
    if not stages_order:
        stages_order = _construir_orden_etapas(cargar_contrato(1))
    stage_index = {key: idx for idx, (key, _, _) in enumerate(stages_order)}
    current_idx = stage_index[current_stage]
    view_h = 68
    step_w = 124
    step_h = 52
    gap = 7
    start_x = 6
    y = 8

    parts: list[str] = [
        svg_open(
            "svg-etapas",
            ETAPAS_ANCHO,
            view_h,
            "ancha",
            f"Indicador de etapa del A3: {current_stage}",
        )
    ]

    for idx in range(len(stages_order) - 1):
        x1 = start_x + idx * (step_w + gap) + step_w
        x2 = x1 + gap
        cy = y + step_h // 2
        line_color = "#22c55e" if idx < current_idx else "#3a3a3a"
        parts.append(
            f'<line x1="{x1}" y1="{cy}" x2="{x2}" y2="{cy}" '
            f'stroke="{line_color}" stroke-width="2"/>'
        )

    for idx, (stage_key, stage_label, _) in enumerate(stages_order):
        x = start_x + idx * (step_w + gap)
        cx = x + step_w / 2
        estado, title_txt, sub_txt = _stage_visual_state(idx, current_idx, stage_label)
        if estado == "completada":
            bg, border, border_w = "#121212", "#22c55e", "1.5"
            title_fill, sub_fill = "#22c55e", "#cccccc"
        elif estado == "actual":
            bg, border, border_w = "#faff69", "#faff69", "2"
            title_fill, sub_fill = "#0a0a0a", "#0a0a0a"
        else:
            bg, border, border_w = "#121212", "#2a2a2a", "1"
            title_fill, sub_fill = "#888888", "#6e6e6e"

        parts.append(
            f'<g data-etapa="{esc(stage_key)}" data-etapa-estado="{estado}">'
            f'<rect x="{x}" y="{y}" width="{step_w}" height="{step_h}" rx="8" '
            f'fill="{bg}" stroke="{border}" stroke-width="{border_w}"/>'
            + svg_text(cx, y + 21, title_txt, 12, title_fill, weight=700, anchor="middle")
            + svg_text(cx, y + 40, sub_txt, 11, sub_fill, weight=500, anchor="middle")
            + "</g>"
        )

    parts.append("</svg>")
    return "".join(parts)


def render_stages_svg(
    current_stage: str,
    stages_order: tuple[tuple[str, str, tuple[int, ...]], ...] | None = None,
) -> str:
    """Dibuja el indicador visual de las cinco etapas en variante angosta y ancha."""
    return (
        f"{_draw_stages_narrow(current_stage, stages_order)}"
        f"{_draw_stages_wide(current_stage, stages_order)}"
    )


def _prepare_ishikawa_branch(
    branch: IshikawaBranch, card_w: int, pill_h: int, hyp_size: float, hyp_lh: float
) -> tuple[list[str], int, int]:
    """Calcula renglones envueltos, alto de tarjeta de hipotesis y alto total del bloque."""
    wrapped = wrap_text(branch.hypothesis, card_w - 20, hyp_size, bold=False)
    card_h = max(34, math.ceil(18.0 + (len(wrapped) - 1) * hyp_lh + 11.0))
    total_h = pill_h + 5 + card_h
    return wrapped, card_h, total_h


def _draw_ishikawa_branch_group(
    branch: IshikawaBranch,
    bx: float,
    by: float,
    card_w: int,
    pill_h: int,
    card_h: int,
    wrapped: list[str],
    spine_x: float,
    join_y_offset: float,
    lienzo: Lienzo,
    hyp_lh: float,
) -> tuple[str, float]:
    """Dibuja una rama del Ishikawa con su pastilla, tarjeta de hipotesis y espina diagonal."""
    is_foco = branch.state == "FOCO"
    group_opacity = "1" if is_foco else "0.75"
    bone_stroke = "#faff69" if is_foco else "#5a5a5a"
    bone_width = "2.5" if is_foco else "1.5"
    bone_dash = "" if is_foco else ' stroke-dasharray="4 3"'

    pill_bg = "#faff69" if is_foco else "#121212"
    pill_border = "#faff69" if is_foco else "#3a3a3a"
    pill_text = "#0a0a0a" if is_foco else "#cccccc"
    pill_sub = "#0a0a0a" if is_foco else "#888888"

    card_bg = "#1a1a1a" if is_foco else "#121212"
    card_border = "#faff69" if is_foco else "#2a2a2a"
    card_border_op = "0.75" if is_foco else "1"
    hyp_fill = "#ffffff" if is_foco else "#a8a8a8"

    name_size = 12.5 if lienzo.ancha else 13.0
    state_size = lienzo.etiqueta
    hyp_size = lienzo.cuerpo

    card_y = by + pill_h + 5
    edge_x = bx + card_w if bx < spine_x else bx
    y1 = by + pill_h / 2.0
    y_twig = card_y + card_h / 2.0
    y2 = y_twig + 9.0 + join_y_offset
    t_ratio = (y_twig - y1) / (y2 - y1)
    join_x = edge_x + t_ratio * (spine_x - edge_x)

    pill_ty = by + (17.5 if lienzo.ancha else 19.0)
    hyp_ty = card_y + (17.0 if lienzo.ancha else 18.0)

    svg = (
        f'<g data-rama="{esc(branch.name)}" data-estado="{esc(branch.state)}" '
        f'opacity="{group_opacity}">'
        f'<line x1="{fmt(edge_x)}" y1="{fmt(y1)}" x2="{fmt(spine_x)}" y2="{fmt(y2)}" '
        f'stroke="{bone_stroke}" stroke-width="{bone_width}"{bone_dash}/>'
        f'<line x1="{fmt(edge_x)}" y1="{fmt(y_twig)}" x2="{fmt(join_x)}" y2="{fmt(y_twig)}" '
        f'stroke="{bone_stroke}" stroke-width="1.5"/>'
        f'<circle cx="{fmt(spine_x)}" cy="{fmt(y2)}" r="3.5" fill="{bone_stroke}"/>'
        f'<g><rect x="{fmt(bx)}" y="{fmt(by)}" width="{card_w}" height="{pill_h}" rx="6" '
        f'fill="{pill_bg}" stroke="{pill_border}" stroke-width="1.5"/>'
        + svg_text(bx + 10, pill_ty, branch.name, name_size, pill_text, weight=700)
        + svg_text(
            bx + card_w - 10,
            pill_ty,
            branch.state,
            state_size,
            pill_sub,
            weight=700,
            anchor="end",
            spacing=0.5,
        )
        + "</g>"
        f'<g><rect x="{fmt(bx)}" y="{fmt(card_y)}" width="{card_w}" height="{card_h}" rx="6" '
        f'fill="{card_bg}" stroke="{card_border}" stroke-opacity="{card_border_op}" '
        f'stroke-width="1.2"/>'
        + svg_text_lines(bx + 10, hyp_ty, wrapped, hyp_size, hyp_lh, hyp_fill)
        + "</g></g>"
    )
    return svg, y2


def _draw_ishikawa(branches: list[IshikawaBranch], brecha: str, lienzo: Lienzo) -> str:
    pill_h = 26 if lienzo.ancha else 28
    hyp_lh = 15.5 if lienzo.ancha else 16.5
    branch_groups: list[str] = []
    last_rib_y = 20.0

    if lienzo.ancha:
        spine_x = 240.0
        card_w = 208
        bx_left = 8.0
        bx_right = 264.0
        cur_y = 8.0
        row_vgap = 14.0
        for r_idx in range(3):
            b_left = branches[2 * r_idx]
            b_right = branches[2 * r_idx + 1]
            w_l, ch_l, th_l = _prepare_ishikawa_branch(b_left, card_w, pill_h, lienzo.cuerpo, hyp_lh)
            w_r, ch_r, th_r = _prepare_ishikawa_branch(
                b_right, card_w, pill_h, lienzo.cuerpo, hyp_lh
            )
            g_l, y2_l = _draw_ishikawa_branch_group(
                b_left, bx_left, cur_y, card_w, pill_h, ch_l, w_l, spine_x, 0.0, lienzo, hyp_lh
            )
            g_r, y2_r = _draw_ishikawa_branch_group(
                b_right, bx_right, cur_y, card_w, pill_h, ch_r, w_r, spine_x, 7.0, lienzo, hyp_lh
            )
            branch_groups.extend((g_l, g_r))
            last_rib_y = max(last_rib_y, y2_l, y2_r)
            cur_y += max(th_l, th_r) + row_vgap
        branches_bottom = cur_y - row_vgap
        brecha_y = max(branches_bottom, last_rib_y) + 22.0
        head_x = 16
        head_w = 448
        spine_svg = (
            f'<line x1="{fmt(spine_x)}" y1="14" x2="{fmt(spine_x)}" y2="{fmt(brecha_y - 6)}" '
            f'stroke="#e6e6e6" stroke-width="3"/>'
            f'<polygon points="{fmt(spine_x)},{fmt(brecha_y)} '
            f'{fmt(spine_x - 7)},{fmt(brecha_y - 10)} {fmt(spine_x + 7)},{fmt(brecha_y - 10)}" '
            f'fill="#faff69"/>'
        )
    else:
        spine_x = 324.0
        card_w = 292
        bx = 8.0
        cur_y = 8.0
        branch_vgap = 12.0
        for branch in branches:
            wrapped, card_h, total_h = _prepare_ishikawa_branch(
                branch, card_w, pill_h, lienzo.cuerpo, hyp_lh
            )
            g_svg, y2 = _draw_ishikawa_branch_group(
                branch, bx, cur_y, card_w, pill_h, card_h, wrapped, spine_x, 0.0, lienzo, hyp_lh
            )
            branch_groups.append(g_svg)
            last_rib_y = max(last_rib_y, y2)
            cur_y += total_h + branch_vgap
        branches_bottom = cur_y - branch_vgap
        turn_y = max(branches_bottom, last_rib_y) + 12.0
        brecha_y = turn_y + 18.0
        head_x = 8
        head_w = 324
        center_x = lienzo.ancho / 2.0
        spine_svg = (
            f'<polyline points="{fmt(spine_x)},14 {fmt(spine_x)},{fmt(turn_y)} '
            f'{fmt(center_x)},{fmt(turn_y)} {fmt(center_x)},{fmt(brecha_y - 6)}" '
            f'fill="none" stroke="#e6e6e6" stroke-width="3" stroke-linejoin="round"/>'
            f'<polygon points="{fmt(center_x)},{fmt(brecha_y)} '
            f'{fmt(center_x - 7)},{fmt(brecha_y - 10)} {fmt(center_x + 7)},{fmt(brecha_y - 10)}" '
            f'fill="#faff69"/>'
        )

    pad_bx = 12
    brecha_lbl_size = max(11.5, lienzo.etiqueta)
    brecha_body_size = lienzo.cuerpo
    brecha_lh = 16.0 if lienzo.ancha else 16.5
    brecha_lns = wrap_text(brecha, head_w - 2 * pad_bx, brecha_body_size, bold=True)
    body_off = 45.0
    brecha_h = math.ceil(body_off + (len(brecha_lns) - 1) * brecha_lh + 13.0)

    brecha_svg = (
        f'<g data-elemento="brecha">'
        f'<rect x="{head_x}" y="{fmt(brecha_y)}" width="{head_w}" height="{brecha_h}" rx="8" '
        f'fill="#1a1a1a" stroke="#faff69" stroke-width="2"/>'
        + svg_text(
            head_x + head_w / 2.0,
            brecha_y + 20.0,
            "PROBLEMA · BRECHA",
            brecha_lbl_size,
            "#faff69",
            weight=700,
            anchor="middle",
            spacing=0.6,
        )
        + f'<line x1="{head_x + 10}" y1="{fmt(brecha_y + 28)}" '
        f'x2="{head_x + head_w - 10}" y2="{fmt(brecha_y + 28)}" '
        f'stroke="#3a3a3a" stroke-width="1"/>'
        + svg_text_lines(
            head_x + pad_bx,
            brecha_y + body_off,
            brecha_lns,
            brecha_body_size,
            brecha_lh,
            "#ffffff",
            weight=600,
        )
        + "</g>"
    )

    view_h = brecha_y + brecha_h + 8.0
    return (
        svg_open(
            "svg-ishikawa",
            lienzo.ancho,
            view_h,
            lienzo.variante,
            "Diagrama de Ishikawa de seis ramas",
        )
        + spine_svg
        + "".join(branch_groups)
        + brecha_svg
        + "</svg>"
    )


def render_ishikawa_svg(branches: list[IshikawaBranch], brecha: str) -> str:
    """Dibuja el diagrama de Ishikawa de 6 ramas en variante angosta y ancha."""
    return draw_variants("diagram-box", lambda lienzo: _draw_ishikawa(branches, brecha, lienzo))


def _draw_pick_option(opt: PickOption, px: float, py: float, code_size: float, tx_off: float) -> str:
    """Dibuja el marcador y codigo de una opcion dentro de la matriz PICK."""
    header = (
        f'<g data-codigo="{esc(opt.code)}" data-cuadrante="{esc(opt.quadrant)}" '
        f'data-decision="{esc(opt.decision)}">'
    )
    if opt.decision == "elegida":
        body = (
            f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="11.5" fill="none" '
            f'stroke="#faff69" stroke-opacity="0.45" stroke-width="1.5"/>'
            f'<circle data-punto="pick" cx="{fmt(px)}" cy="{fmt(py)}" r="7.5" '
            f'fill="#faff69" stroke="#0a0a0a" stroke-width="1.5"/>'
            + svg_text(px + tx_off, py + 4.5, opt.code, code_size, "#faff69", weight=700)
        )
    elif opt.decision == "después":
        body = (
            f'<circle data-punto="pick" cx="{fmt(px)}" cy="{fmt(py)}" r="7.5" '
            f'fill="#1a1a1a" stroke="#f59e0b" stroke-width="2.4"/>'
            f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="2.5" fill="#f59e0b"/>'
            + svg_text(px + tx_off, py + 4.5, opt.code, code_size, "#e6e6e6", weight=600)
        )
    else:
        body = (
            f'<circle data-punto="pick" cx="{fmt(px)}" cy="{fmt(py)}" r="7" '
            f'fill="#121212" stroke="#5a5a5a" stroke-width="1.5" stroke-dasharray="2 2"/>'
            f'<line x1="{fmt(px - 3.2)}" y1="{fmt(py - 3.2)}" '
            f'x2="{fmt(px + 3.2)}" y2="{fmt(py + 3.2)}" stroke="#888888" stroke-width="1.5"/>'
            f'<line x1="{fmt(px - 3.2)}" y1="{fmt(py + 3.2)}" '
            f'x2="{fmt(px + 3.2)}" y2="{fmt(py - 3.2)}" stroke="#888888" stroke-width="1.5"/>'
            + svg_text(px + tx_off, py + 4.5, opt.code, code_size, "#9a9a9a", weight=500)
        )
    return header + body + "</g>"


def _draw_pick(options: list[PickOption], lienzo: Lienzo) -> str:
    by_quad: dict[str, list[PickOption]] = {
        "Implementar": [],
        "Desafío": [],
        "Posible": [],
        "Eliminar": [],
    }
    for opt in options:
        by_quad[opt.quadrant].append(opt)

    if lienzo.ancha:
        grid_x = 52
        quad_w = 212
        axis_vx = 43
        rot_sub_x = 33
        rot_title_x = 15
        col_step = 98
        pad_px = 22
        tx_off = 15.0
        max_2col_w = 68.0
        leg_x = (64, 166, 276)
    else:
        grid_x = 44
        quad_w = 146
        axis_vx = 37
        rot_sub_x = 28
        rot_title_x = 13
        col_step = 65
        pad_px = 20
        tx_off = 14.0
        max_2col_w = 37.0
        leg_x = (52, 136, 226)

    grid_y = 40
    row_step = 36
    qtitle_size = 13.5
    qsub_size = lienzo.etiqueta
    qsub_lh = 15.0
    code_size = lienzo.cuerpo

    quad_specs = (
        (0, 0, "Implementar", "Impacto alto · Esfuerzo bajo", "#faff69", "#1d1e14"),
        (1, 0, "Desafío", "Impacto alto · Esfuerzo alto", "#f59e0b", "#181818"),
        (0, 1, "Posible", "Impacto bajo · Esfuerzo bajo", "#cccccc", "#121212"),
        (1, 1, "Eliminar", "Impacto bajo · Esfuerzo alto", "#888888", "#121212"),
    )

    quad_cols: dict[str, int] = {}
    quad_subs: dict[str, list[str]] = {}
    quad_first_off: dict[str, float] = {}
    quad_h = 128
    for _, _, qname, qsub, _, _ in quad_specs:
        sub_lns = wrap_text(qsub, quad_w - 20, qsub_size, bold=False)
        quad_subs[qname] = sub_lns
        header_end = 37.0 + (len(sub_lns) - 1) * qsub_lh
        first_off = header_end + 24.0
        quad_first_off[qname] = first_off

        opts_q = by_quad[qname]
        widest = max((text_width(o.code, code_size, bold=True) for o in opts_q), default=0.0)
        cols_q = 2 if len(opts_q) >= 2 and widest <= max_2col_w else 1
        quad_cols[qname] = cols_q
        rows_q = max(1, (len(opts_q) + cols_q - 1) // cols_q)
        needed_qh = math.ceil(first_off + (rows_q - 1) * row_step + 20.0)
        if needed_qh > quad_h:
            quad_h = needed_qh

    grid_w = quad_w * 2
    grid_h = quad_h * 2
    axis_hy = grid_y + grid_h + 14
    view_h = axis_hy + 46

    parts: list[str] = [
        svg_open("svg-pick", lienzo.ancho, view_h, lienzo.variante, "Matriz PICK de opciones")
    ]

    lx1, lx2, lx3 = leg_x
    parts.append(
        '<g data-elemento="leyenda-pick">'
        f'<circle cx="{lx1}" cy="18" r="8.5" fill="none" stroke="#faff69" stroke-opacity="0.45" stroke-width="1.5"/>'
        f'<circle cx="{lx1}" cy="18" r="5.5" fill="#faff69"/>'
        + svg_text(lx1 + 13, 22.5, "Elegida", 12, "#e6e6e6", weight=600)
        + f'<circle cx="{lx2}" cy="18" r="6" fill="#1a1a1a" stroke="#f59e0b" stroke-width="2.2"/>'
        f'<circle cx="{lx2}" cy="18" r="2" fill="#f59e0b"/>'
        + svg_text(lx2 + 12, 22.5, "Después", 12, "#e6e6e6", weight=600)
        + f'<circle cx="{lx3}" cy="18" r="5.5" fill="#121212" stroke="#5a5a5a" stroke-width="1.5" stroke-dasharray="2 2"/>'
        f'<line x1="{lx3 - 2.8}" y1="15.2" x2="{lx3 + 2.8}" y2="20.8" stroke="#888888" stroke-width="1.5"/>'
        f'<line x1="{lx3 - 2.8}" y1="20.8" x2="{lx3 + 2.8}" y2="15.2" stroke="#888888" stroke-width="1.5"/>'
        + svg_text(lx3 + 12, 22.5, "Descartada", 12, "#888888", weight=600)
        + "</g>"
    )

    opt_coords: dict[int, tuple[float, float]] = {}
    for qcol, qrow, qname, _, qtitle_color, qfill in quad_specs:
        qx = grid_x + qcol * quad_w
        qy = grid_y + qrow * quad_h
        sub_lns = quad_subs[qname]
        parts.append(
            f'<g data-cuadrante-caja="{esc(qname)}">'
            f'<rect x="{qx}" y="{qy}" width="{quad_w}" height="{quad_h}" '
            f'fill="{qfill}" stroke="#3a3a3a" stroke-width="1.5"/>'
            + svg_text(qx + 10, qy + 21, qname, qtitle_size, qtitle_color, weight=700)
            + svg_text_lines(qx + 10, qy + 37, sub_lns, qsub_size, qsub_lh, "#9a9a9a")
            + "</g>"
        )
        cols_q = quad_cols[qname]
        first_off = quad_first_off[qname]
        for idx_in_q, opt in enumerate(by_quad[qname]):
            c_idx = idx_in_q % cols_q
            r_idx = idx_in_q // cols_q
            px = qx + pad_px + c_idx * col_step
            py = qy + first_off + r_idx * row_step
            opt_coords[id(opt)] = (px, py)

    for opt in options:
        px, py = opt_coords[id(opt)]
        parts.append(_draw_pick_option(opt, px, py, code_size, tx_off))

    ax_sub_size = lienzo.etiqueta
    parts.append(
        f'<line x1="{axis_vx}" y1="{grid_y + grid_h}" x2="{axis_vx}" y2="{grid_y + 6}" '
        f'stroke="#888888" stroke-width="1.5"/>'
        f'<polygon points="{axis_vx},{grid_y} {axis_vx - 4},{grid_y + 9} {axis_vx + 4},{grid_y + 9}" '
        f'fill="#888888"/>'
        + svg_text(
            rot_sub_x,
            grid_y + quad_h / 2,
            "ALTO",
            ax_sub_size,
            "#cccccc",
            weight=700,
            anchor="middle",
            spacing=1.0,
            rotated=True,
        )
        + svg_text(
            rot_sub_x,
            grid_y + quad_h + quad_h / 2,
            "BAJO",
            ax_sub_size,
            "#888888",
            weight=700,
            anchor="middle",
            spacing=1.0,
            rotated=True,
        )
        + svg_text(
            rot_title_x,
            grid_y + grid_h / 2,
            "IMPACTO",
            12,
            "#ffffff",
            weight=700,
            anchor="middle",
            spacing=1.5,
            rotated=True,
        )
    )

    parts.append(
        f'<line x1="{grid_x}" y1="{axis_hy}" x2="{grid_x + grid_w - 6}" y2="{axis_hy}" '
        f'stroke="#888888" stroke-width="1.5"/>'
        f'<polygon points="{grid_x + grid_w},{axis_hy} {grid_x + grid_w - 9},{axis_hy - 4} '
        f'{grid_x + grid_w - 9},{axis_hy + 4}" fill="#888888"/>'
        + svg_text(
            grid_x + quad_w / 2,
            axis_hy + 17,
            "BAJO",
            ax_sub_size,
            "#cccccc",
            weight=700,
            anchor="middle",
            spacing=1.0,
        )
        + svg_text(
            grid_x + quad_w + quad_w / 2,
            axis_hy + 17,
            "ALTO",
            ax_sub_size,
            "#888888",
            weight=700,
            anchor="middle",
            spacing=1.0,
        )
        + svg_text(
            grid_x + grid_w / 2,
            axis_hy + 36,
            "ESFUERZO",
            12,
            "#ffffff",
            weight=700,
            anchor="middle",
            spacing=1.5,
        )
    )

    parts.append("</svg>")
    return "".join(parts)


def render_pick_svg(options: list[PickOption]) -> str:
    """Dibuja la matriz PICK 2x2 en variante angosta y ancha."""
    return draw_variants("diagram-box", lambda lienzo: _draw_pick(options, lienzo))


def _draw_state_map(steps: list[StateMapStep], kind: str, lienzo: Lienzo) -> str:
    total = len(steps)
    cols = min(2, max(1, total)) if lienzo.ancha else 1
    margin_x = 8
    arrow_gap = 24
    usable_w = lienzo.ancho - 2 * margin_x
    box_w = (usable_w - (cols - 1) * arrow_gap) // cols
    pad_x = 12
    text_max_w = box_w - 2 * pad_x

    tag_size = lienzo.etiqueta
    step_size = 13.0 if lienzo.ancha else 13.5
    step_lh = 17.0 if lienzo.ancha else 18.0
    meta_size = lienzo.cuerpo
    meta_lh = 15.5 if lienzo.ancha else 16.5
    prob_size = max(11.5, lienzo.etiqueta)
    prob_lh = 15.0 if lienzo.ancha else 16.0

    rows_data: list[
        tuple[int, list[tuple[StateMapStep, list[str], list[str], list[str], float, float, float]]]
    ] = []
    for start in range(0, total, cols):
        chunk = steps[start : start + cols]
        prepared_chunk: list[
            tuple[StateMapStep, list[str], list[str], list[str], float, float, float]
        ] = []
        row_h = 88
        for st in chunk:
            step_lns = wrap_text(st.step, text_max_w, step_size, bold=True)
            meta_lns = wrap_text(f"{st.who} · {st.duration}", text_max_w, meta_size, bold=False)
            prob_lns = (
                wrap_text(st.problem, text_max_w, prob_size, bold=True) if st.has_problem else []
            )
            step_off = 45.0
            step_end = step_off + (len(step_lns) - 1) * step_lh
            meta_off = step_end + step_lh + 3.0
            meta_end = meta_off + (len(meta_lns) - 1) * meta_lh
            if st.has_problem and prob_lns:
                sep_off = meta_end + 9.0
                prob_off = sep_off + 16.0
                prob_end = prob_off + (len(prob_lns) - 1) * prob_lh
                needed_h = math.ceil(prob_end + 12.0)
            else:
                sep_off = 0.0
                needed_h = math.ceil(meta_end + 12.0)
            if needed_h > row_h:
                row_h = needed_h
            prepared_chunk.append((st, step_lns, meta_lns, prob_lns, step_off, meta_off, sep_off))
        rows_data.append((row_h, prepared_chunk))

    row_vgap = 24 if cols == 1 else 28
    total_h = 16 + sum(rh for rh, _ in rows_data) + max(0, len(rows_data) - 1) * row_vgap

    parts: list[str] = [
        svg_open(
            "svg-mapa-estado",
            lienzo.ancho,
            total_h,
            lienzo.variante,
            f"Mapa del estado {kind}",
            extra=f' data-mapa="{esc(kind)}"',
        )
    ]

    cur_y = 8
    for r_idx, (row_h, chunk) in enumerate(rows_data):
        for c_idx, (st, step_lns, meta_lns, prob_lns, step_off, meta_off, sep_off) in enumerate(
            chunk
        ):
            global_idx = r_idx * cols + c_idx
            bx = margin_x + c_idx * (box_w + arrow_gap)
            by = cur_y
            prob_flag = "si" if st.has_problem else "no"

            if st.has_problem:
                border_col, border_w, border_op = "#ef4444", "2", "1"
            elif kind == "futuro":
                border_col, border_w, border_op = "#22c55e", "1.5", "0.75"
            else:
                border_col, border_w, border_op = "#3a3a3a", "1.5", "1"

            parts.append(
                f'<g data-paso="{global_idx + 1}" data-problema="{prob_flag}">'
                f'<rect x="{bx}" y="{by}" width="{box_w}" height="{row_h}" rx="8" '
                f'fill="#1a1a1a" stroke="{border_col}" stroke-opacity="{border_op}" '
                f'stroke-width="{border_w}"/>'
            )

            if st.has_problem:
                pill_w = 90 if lienzo.ancha else 96
                pill_h = 19 if lienzo.ancha else 20
                pill_ty = by + 21.5 if lienzo.ancha else by + 22
                parts.append(
                    f'<g><rect x="{bx + 10}" y="{by + 8}" width="{pill_w}" height="{pill_h}" '
                    f'rx="{fmt(pill_h / 2)}" fill="#ef4444"/>'
                    + svg_text(
                        bx + 10 + pill_w / 2,
                        pill_ty,
                        "PROBLEMA",
                        tag_size,
                        "#ffffff",
                        weight=700,
                        anchor="middle",
                        spacing=0.5,
                    )
                    + "</g>"
                )
            else:
                tag_txt = "META OK" if kind == "futuro" else "SIN FALLO"
                tag_col = "#22c55e" if kind == "futuro" else "#888888"
                parts.append(
                    svg_text(bx + pad_x, by + 22, tag_txt, tag_size, tag_col, weight=700, spacing=0.5)
                )

            parts.append(
                svg_text_lines(
                    bx + pad_x, by + step_off, step_lns, step_size, step_lh, "#ffffff", weight=700
                )
                + svg_text_lines(
                    bx + pad_x, by + meta_off, meta_lns, meta_size, meta_lh, "#cccccc"
                )
            )

            if st.has_problem and prob_lns:
                parts.append(
                    f'<line x1="{bx + 10}" y1="{fmt(by + sep_off)}" '
                    f'x2="{bx + box_w - 10}" y2="{fmt(by + sep_off)}" '
                    f'stroke="#ef4444" stroke-opacity="0.6" stroke-width="1" stroke-dasharray="3 2"/>'
                    + svg_text_lines(
                        bx + pad_x,
                        by + sep_off + 16.0,
                        prob_lns,
                        prob_size,
                        prob_lh,
                        "#ef4444",
                        weight=600,
                    )
                )

            parts.append("</g>")

            if global_idx + 1 < total:
                if c_idx + 1 < len(chunk):
                    ax1 = bx + box_w + 2
                    ax2 = bx + box_w + arrow_gap - 2
                    ay = by + row_h // 2
                    parts.append(
                        f'<g data-flecha="paso">'
                        f'<line x1="{ax1}" y1="{ay}" x2="{ax2 - 6}" y2="{ay}" '
                        f'stroke="#faff69" stroke-width="2"/>'
                        f'<polygon points="{ax2},{ay} {ax2 - 8},{ay - 4.5} {ax2 - 8},{ay + 4.5}" '
                        f'fill="#faff69"/>'
                        f"</g>"
                    )
                elif cols == 1:
                    cx = lienzo.ancho // 2
                    ay1 = by + row_h + 3
                    ay2 = by + row_h + row_vgap - 2
                    parts.append(
                        f'<g data-flecha="paso">'
                        f'<line x1="{cx}" y1="{ay1}" x2="{cx}" y2="{ay2 - 6}" '
                        f'stroke="#faff69" stroke-width="2"/>'
                        f'<polygon points="{cx},{ay2} {cx - 5},{ay2 - 8} {cx + 5},{ay2 - 8}" '
                        f'fill="#faff69"/>'
                        f"</g>"
                    )
                else:
                    mid_gap_y = by + row_h + row_vgap // 2
                    next_top_y = by + row_h + row_vgap
                    start_cx = bx + box_w // 2
                    dest_cx = margin_x + box_w // 2
                    parts.append(
                        f'<g data-flecha="paso">'
                        f'<polyline points="{start_cx},{by + row_h + 2} {start_cx},{mid_gap_y} '
                        f'{dest_cx},{mid_gap_y} {dest_cx},{next_top_y - 7}" '
                        f'fill="none" stroke="#faff69" stroke-width="2"/>'
                        f'<polygon points="{dest_cx},{next_top_y - 1} {dest_cx - 4.5},{next_top_y - 9} '
                        f'{dest_cx + 4.5},{next_top_y - 9}" fill="#faff69"/>'
                        f"</g>"
                    )

        cur_y += row_h + row_vgap

    parts.append("</svg>")
    return "".join(parts)


def render_state_map_svg(steps: list[StateMapStep], kind: str) -> str:
    """Dibuja el mapa de estado presente o futuro en variante angosta y ancha."""
    return draw_variants("diagram-box", lambda lienzo: _draw_state_map(steps, kind, lienzo))


def render_table_html(table: MarkdownTable) -> str:
    head_cells = "".join(f"<th>{format_inline_md(h)}</th>" for h in table.headers)
    plain_headers = [strip_md_inline(h) for h in table.headers]
    is_ishi = is_ishikawa_table(table)
    is_pick = is_pick_table(table)
    wrap_cls = "table-wrap table-pick" if is_pick else "table-wrap"
    body_rows: list[str] = []
    for row in table.rows:
        padded = row + [""] * max(0, len(table.headers) - len(row))
        rendered_cells: list[str] = []
        for col_i, c in enumerate(padded[: len(table.headers)]):
            lbl_attr = f' data-label="{esc(plain_headers[col_i])}"'
            if is_ishi and col_i == 3:
                st = strip_md_inline(c).upper()
                cls = "badge-yellow" if st == "FOCO" else "badge-muted"
                rendered_cells.append(
                    f'<td{lbl_attr}><span class="badge-pill {cls}">{esc(st)}</span></td>'
                )
            elif is_pick and col_i == 6:
                dec = strip_md_inline(c).lower()
                if dec == "elegida":
                    cls = "badge-yellow"
                elif dec in {"después", "despues"}:
                    cls = "badge-warning"
                else:
                    cls = "badge-muted"
                rendered_cells.append(
                    f'<td{lbl_attr}><span class="badge-pill {cls}">{esc(dec)}</span></td>'
                )
            else:
                rendered_cells.append(f"<td{lbl_attr}>{format_inline_md(c)}</td>")
        body_rows.append(f'<tr>{"".join(rendered_cells)}</tr>')
    return (
        f'<div class="{wrap_cls}"><table><thead><tr>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
    )


def render_list_block(list_lines: list[tuple[int, str]]) -> str:
    """Renderiza listas con hasta dos niveles de sangria."""
    if not list_lines:
        return ""
    base_indent = min(ind for ind, _ in list_lines)
    items_html: list[str] = []
    idx = 0
    while idx < len(list_lines):
        ind, content = list_lines[idx]
        sub_items: list[str] = []
        idx += 1
        while idx < len(list_lines) and list_lines[idx][0] > base_indent:
            sub_items.append(list_lines[idx][1])
            idx += 1

        formatted = format_inline_md(content)
        if re.match(r"^Por\s+lo\s+tanto:", strip_md_inline(content), flags=re.IGNORECASE):
            formatted = f'<span class="por-lo-tanto">{formatted}</span>'

        if sub_items:
            sub_rendered: list[str] = []
            for sub in sub_items:
                sub_fmt = format_inline_md(sub)
                if re.match(r"^Por\s+lo\s+tanto:", strip_md_inline(sub), flags=re.IGNORECASE):
                    sub_fmt = f'<span class="por-lo-tanto">{sub_fmt}</span>'
                sub_rendered.append(f"<li>{sub_fmt}</li>")
            items_html.append(f"<li>{formatted}<ul>{''.join(sub_rendered)}</ul></li>")
        else:
            items_html.append(f"<li>{formatted}</li>")

    return f"<ul>{''.join(items_html)}</ul>"


def render_markdown_blocks(
    lines: list[str],
    *,
    doc: A3Document | None = None,
    skip_brecha_line: bool = False,
) -> str:
    """Convierte lineas de una seccion Markdown a bloques HTML seguros."""
    out: list[str] = []
    i = 0
    n = len(lines)
    ishikawa_drawn = False
    pick_drawn = False
    current_h3: str | None = None

    while i < n:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            i += 1
            continue

        if skip_brecha_line and re.match(
            r"^\s*(?:[-*]\s*)?\*\*Brecha:?\*\*:?\s*(.+)$", stripped, flags=re.IGNORECASE
        ):
            i += 1
            continue

        # Subtitulo H3
        m_h3 = re.match(r"^###\s+(.+)$", stripped)
        if m_h3:
            current_h3 = strip_md_inline(m_h3.group(1))
            out.append(f'<h3 class="subsection-title">{format_inline_md(m_h3.group(1))}</h3>')
            i += 1
            continue

        # Tabla Markdown
        if "|" in stripped and i + 1 < n and is_table_separator(lines[i + 1]):
            headers = parse_table_row(stripped)
            i += 2
            rows: list[list[str]] = []
            while i < n and "|" in lines[i].strip() and lines[i].strip():
                if not is_table_separator(lines[i]):
                    rows.append(parse_table_row(lines[i]))
                i += 1
            tbl = MarkdownTable(headers=headers, rows=rows)
            map_kind = state_map_kind_from_h3(current_h3)
            if (
                not ishikawa_drawn
                and doc is not None
                and doc.ishikawa_branches is not None
                and not doc.ishikawa_no_aplica
                and is_ishikawa_table(tbl)
            ):
                out.append(render_ishikawa_svg(doc.ishikawa_branches, doc.brecha))
                ishikawa_drawn = True
            elif (
                not pick_drawn
                and doc is not None
                and doc.pick_options is not None
                and not doc.pick_unica_opcion
                and is_pick_table(tbl)
            ):
                out.append(render_pick_svg(doc.pick_options))
                pick_drawn = True
            elif doc is not None and map_kind == "presente" and doc.present_map is not None:
                out.append(render_state_map_svg(doc.present_map, "presente"))
            elif doc is not None and map_kind == "futuro" and doc.future_map is not None:
                out.append(render_state_map_svg(doc.future_map, "futuro"))
            out.append(render_table_html(tbl))
            continue

        # Lista con vinetas o numerada
        m_li = re.match(r"^(\s*)(?:[-*]|\d+\.)\s+(.+)$", raw)
        if m_li:
            list_items: list[tuple[int, str]] = []
            while i < n:
                m_cur = re.match(r"^(\s*)(?:[-*]|\d+\.)\s+(.+)$", lines[i])
                if not m_cur:
                    break
                if skip_brecha_line and re.match(
                    r"^\s*[-*]\s*\*\*Brecha:?\*\*:?\s*(.+)$",
                    lines[i].strip(),
                    flags=re.IGNORECASE,
                ):
                    i += 1
                    continue
                list_items.append((len(m_cur.group(1)), m_cur.group(2).strip()))
                i += 1
            if list_items:
                out.append(render_list_block(list_items))
            continue

        # Parrafo normal (con resaltado suave si es declaracion de no aplica o unica opcion)
        para_lines: list[str] = [stripped]
        i += 1
        while i < n:
            nxt = lines[i].strip()
            if (
                not nxt
                or nxt.startswith("###")
                or re.match(r"^(\s*)(?:[-*]|\d+\.)\s+", lines[i])
                or ("|" in nxt and i + 1 < n and is_table_separator(lines[i + 1]))
            ):
                break
            para_lines.append(nxt)
            i += 1
        joined_para = " ".join(para_lines)
        plain_para = strip_md_inline(joined_para)
        if re.match(
            r"^(?:Ishikawa:\s*no\s+aplica|[ÚU]nica\s+opci[oó]n:)\b",
            plain_para,
            flags=re.IGNORECASE,
        ):
            out.append(f'<div class="no-apply-note">{format_inline_md(joined_para)}</div>')
        else:
            out.append(f"<p>{format_inline_md(joined_para)}</p>")

    return "\n".join(out)


def render_section_card(doc: A3Document, sec_num: int) -> str:
    sec = doc.sections[sec_num]
    orden = doc.stages_order or _construir_orden_etapas(cargar_contrato(1))
    stage_index = {key: idx for idx, (key, _, _) in enumerate(orden)}
    current_idx = stage_index[doc.stage]
    req_idx = stage_index[sec.required_from_stage]

    if req_idx > current_idx and (not sec.present or not has_meaningful_content(sec.raw_lines)):
        return (
            f'<section class="section-card section-card-pending" data-seccion="{sec_num}">'
            f'<h2 class="section-title">{esc(sec.title)}</h2>'
            f'<p class="pending-notice">Pendiente de la etapa {esc(sec.required_from_stage)}.</p>'
            f"</section>"
        )

    inner_parts: list[str] = [f'<h2 class="section-title">{esc(sec.title)}</h2>']
    if sec_num == 2:
        inner_parts.append(
            f'<div class="brecha-callout">'
            f'<span class="brecha-label">Brecha en el Gemba</span>'
            f'<div class="brecha-text">{format_inline_md(doc.brecha)}</div>'
            f"</div>"
        )

    rendered_body = render_markdown_blocks(
        sec.raw_lines, doc=doc, skip_brecha_line=(sec_num == 2)
    )
    if rendered_body:
        inner_parts.append(rendered_body)

    return f'<section class="section-card" data-seccion="{sec_num}">' + "\n".join(inner_parts) + "</section>"


def render_html(doc: A3Document) -> str:
    meta_cards: list[tuple[str, str]] = [
        ("Propietario", esc(doc.owner)),
        ("Coach / Revisor", esc(doc.coach)),
        ("Versión", esc(doc.version)),
        ("Etapa", esc(doc.stage)),
    ]
    for k, v in doc.extra_meta:
        meta_cards.append((esc(k), format_inline_md(v)))

    meta_html = "".join(
        f'<div class="meta-item"><span class="meta-label">{lbl}</span>'
        f'<span class="meta-value">{val}</span></div>'
        for lbl, val in meta_cards
    )

    obj_html = ""
    if doc.objective:
        obj_html = (
            f'<div class="objective-banner"><strong>Objetivo que apoya:</strong> '
            f"{format_inline_md(doc.objective)}</div>"
        )

    left_col = "\n".join(render_section_card(doc, n) for n in (1, 2, 3, 4))
    right_parts = [render_section_card(doc, n) for n in (5, 6, 7)]
    if doc.next_steps_lines is not None and has_meaningful_content(doc.next_steps_lines):
        right_parts.append(
            '<section class="section-card section-card-next" data-seccion="siguientes-pasos">'
            '<h2 class="section-title">Siguientes pasos</h2>'
            f"{render_markdown_blocks(doc.next_steps_lines)}"
            "</section>"
        )
    right_col = "\n".join(right_parts)

    first_line = '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
    rest_lines = [
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>A3: {esc(doc.title)}</title>",
        f"<style>{CSS_STYLES}\n{CSS_DIBUJOS}</style>",
        "</head>",
        "<body>",
        '<main class="a3-page">',
        '<header class="a3-header">',
        '<div class="a3-header-top">',
        '<span class="kicker">Reporte A3 · Pensamiento Lean</span>',
        f'<span class="badge-pill badge-yellow">Etapa: {esc(doc.stage)}</span>',
        "</div>",
        f'<h1 class="a3-title">A3: {esc(doc.title)}</h1>',
        f'<div class="meta-grid">{meta_html}</div>',
        obj_html,
        f'<div class="stage-bar-wrap dibujo dibujo-etapas">{render_stages_svg(doc.stage, doc.stages_order)}</div>',
        "</header>",
        '<div class="a3-columns">',
        f'<div class="a3-col">{left_col}</div>',
        f'<div class="a3-col">{right_col}</div>',
        "</div>",
        "</main>",
        "</body></html>",
    ]
    return first_line + "\n" + "\n".join(line for line in rest_lines if line) + "\n"


USAGE = "Uso: dibujar-a3.py <a3.md> -o <a3.html>"
HELP = f"""{USAGE}

Convierte un reporte A3 en Markdown a una página HTML visual sin red.

Argumentos:
  <a3.md>                 Ruta al archivo A3 en Markdown.
  -o, --output <a3.html>  Ruta del archivo HTML de salida (termina en .html o .htm).
                          Su carpeta ya debe existir y no puede ser la entrada.
  -h, --help              Muestra esta ayuda y termina.
"""


class UsageError(Exception):
    """Uso invalido de la linea de comandos: codigo de salida 2."""


def parse_args(argv: list[str]) -> tuple[str, str] | None:
    """Devuelve (entrada, salida), o None si se pidio la ayuda.

    Se lee a mano y no con argparse para que el uso, la ayuda y los errores salgan en español.
    """
    entradas: list[str] = []
    salida: str | None = None
    solo_entradas = False
    pendientes = iter(argv)
    for arg in pendientes:
        if solo_entradas or arg == "-" or not arg.startswith("-"):
            entradas.append(arg)
        elif arg == "--":
            solo_entradas = True
        elif arg in ("-h", "--help"):
            return None
        elif arg in ("-o", "--output"):
            salida = next(pendientes, None)
            if salida is None:
                raise UsageError(f"a {arg} le falta la ruta del archivo HTML de salida")
        elif arg.startswith("--output="):
            salida = arg.removeprefix("--output=")
        elif arg.startswith("-o") and not arg.startswith("--"):
            salida = arg.removeprefix("-o")
        else:
            raise UsageError(f"opción desconocida: {arg}")
    if not entradas:
        raise UsageError("falta el archivo A3 de entrada (<a3.md>)")
    if len(entradas) > 1:
        raise UsageError(f"sobra un argumento, solo se dibuja un A3 por vez: {' '.join(entradas[1:])}")
    if salida is None:
        raise UsageError("falta la salida (-o <a3.html>)")
    return entradas[0], salida


def output_problem(in_path: Path, out_path: Path) -> str | None:
    """Motivo por el que no se debe escribir en out_path, o None si se puede."""
    try:
        misma = out_path.resolve() == in_path.resolve() or (out_path.exists() and out_path.samefile(in_path))
    except (OSError, RuntimeError):  # ruta que no se puede resolver: lo dira el error de escritura
        misma = False
    if misma:
        return f"la salida es el mismo archivo que la entrada, se borraría el A3: {out_path}"
    if not out_path.name.lower().endswith((".html", ".htm")):
        return f"la salida debe terminar en .html o .htm: {out_path}"
    carpeta = out_path.parent
    if not carpeta.is_dir():
        # No se crea: una ruta mal escrita dejaria carpetas basura (misma regla que kaizen-cli.py).
        motivo = "no es una carpeta" if carpeta.exists() else "no existe"
        return f"la carpeta de la salida {motivo}: {carpeta}"
    return None


def main(argv: list[str] | None = None) -> int:
    try:
        rutas = parse_args(sys.argv[1:] if argv is None else argv)
    except UsageError as exc:
        print(f"{USAGE}\nError: {exc}", file=sys.stderr)
        return 2
    if rutas is None:
        print(HELP, end="")
        return 0

    in_path = Path(rutas[0])
    out_path = Path(rutas[1])

    if not in_path.exists() or not in_path.is_file():
        print(f"Error: el archivo de entrada no existe: {in_path}", file=sys.stderr)
        return 1

    problema = output_problem(in_path, out_path)
    if problema:
        print(f"Error: {problema}", file=sys.stderr)
        return 2

    try:
        raw_md = in_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(
            f"Error: el archivo '{in_path}' no está codificado en UTF-8 válido.",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"Error al leer '{in_path}': {exc}", file=sys.stderr)
        return 1

    try:
        doc = parse_a3_markdown(raw_md)
        html_out = render_html(doc)
    except ContractError as exc:
        print(f"Error de contrato A3: {exc}", file=sys.stderr)
        return 1
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2

    try:
        out_path.write_text(html_out, encoding="utf-8")
    except OSError as exc:
        print(f"Error al escribir '{out_path}': {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
