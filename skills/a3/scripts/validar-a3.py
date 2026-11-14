#!/usr/bin/env python3
"""Validador determinista del A3 de TAS (formato de la v1.2.0).

Separa dos clases de hallazgo:

- Errores de pensamiento: rechazan el A3. Hechos sin fuente, falta la brecha, una causa sin
  contramedida o sin su "Por lo tanto", una causa que culpa a una persona o a un agente, un
  cuadrante PICK que no coincide con su impacto y esfuerzo, valores fuera de los permitidos.
- Avisos de forma: no rechazan. Orden o nombre de un rótulo, recomendaciones.

Solo se exige lo que pide la etapa (comprender, analizar, proponer, planear, cerrar). Un A3
escrito con la plantilla de la v1.1.1 se reconoce como formato anterior: se valida con las
reglas de entonces y se dice qué le falta para el formato nuevo.

Uso: validar-a3.py [--etapa ETAPA] <archivo-a3.md>
Códigos de salida: 0 aprobado, 1 rechazado, 2 error de uso.
Solo biblioteca estándar; Python 3.12 o posterior; sin red.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

NOMBRES = {
    1: "Contexto y Desperdicio (Muda) Observado",
    2: "Estado Actual en el Gemba",
    3: "Meta y Criterio de Aceptación",
    4: "Análisis de Causa Raíz",
    5: "Contramedidas y Poka-Yoke",
    6: "Plan de Ejecución PDCA y Ventana de Despliegue",
    7: "Verificación en Gemba y Estandarización",
}
MAX_LINEAS = 160
MIN_LINEAS_V111 = 20

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

# Marcadores de plantilla: "<texto con espacios>" fuera de código (ni tipos como Map<String, int>),
# TODO como nota pendiente (no como la palabra española "todo"), TBD/FIXME y los corchetes v1.1.1.
# ANGULAR solo encuentra el par de ángulos; si es marcador lo decide es_marcador_angular() en
# Python. Así no hay retroceso cuadrático con un '<' sin cerrar seguido de muchas palabras.
ANGULAR = re.compile(r"(?<!\w)<((?:[^<>\n]|(?<=-)>)+)>")
MARCADOR_PALABRA = re.compile(r"\b(?:TBD|FIXME)\b")
PALABRA_TODO = re.compile(r"\bTODO\b")
TODO_ESPANOL_SIGUE = re.compile(
    r"\s+(?:el|la|lo|un|una|su|mi|este|esta|ese|esa|es|est[aá]|queda)\b",
    re.IGNORECASE,
)
MARCADOR_CORCHETE = re.compile(
    r"\[(?:RELLENAR|Título claro|Qué flujo|Qué proceso|Hecho comprobado|Nombre del|Acción concreta)[^\]\n]*\]?"
)
CAMPO = re.compile(r"^\s*[-*]\s*\*\*(.*?):\*\*\s*(.*)$")
BRECHA = re.compile(r"^\s*[-*]\s*\*\*Brecha:\*\*")
CAUSA = re.compile(r"^\s*[-*]\s*\*\*\s*Causa\b([^*]*?):\*\*\s*(.*)$", re.IGNORECASE)
PORQUE = re.compile(r"^\s*[-*]\s*\d+[a-z]?[.)]\s*\S")
POR_LO_TANTO = re.compile(r"^\s*[-*]\s*(?:\*\*)?\s*por lo tanto\s*:?\s*(?:\*\*)?\s*(.*)$", re.IGNORECASE)
FECHA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
BARRA_SIN_ESCAPAR = re.compile(r"(?<!\\)\|")
# Culpa (heurística): en la misma oración hay alguien (un papel, "quien", "alguien" o "humano") y una
# falta, sin una negación que alcance a la falta. Un sujeto que no es persona ni agente (la contraseña,
# el caché, el límite) no es culpa. Un nombre propio ("Ana se saltó el paso") no se detecta. Falta a
# propósito un papel: la compuerta de las rondas 2 y 3 prohíbe su raíz en todo el repo (ver bitácora).
PERSONA = re.compile(
    r"\b(?:operador(?:a|es|as)?|t[eé]cnicos?|usuari[oa]s?|agentes?|equipos?|guardias?"
    r"|propietari[oa]s?|human[oa]s?|personas?|personal|revisor(?:a|es|as)?|desarrollador(?:a|es|as)?"
    r"|administrador(?:a|es|as)?|responsables?|encargad[oa]s?|dueñ[oa]s?|autor(?:a|es|as)?|analistas?"
    r"|integrador(?:a|es|as)?|emplead[oa]s?|quien(?:es)?|alguien)\b",
    re.IGNORECASE,
)
FALTA = re.compile(
    r"\bolvid\w*|\bdescuid\w*|\bequivoc\w*|\bignor\w*|\bno\s+(?:se\s+)?(?:le[eíy]\w*|revis\w*)"
    r"|\bfall(?:ó|aron|ar|ado|aba|aban|an|amos)\b|\berror(?:es)?\s+human[oa]s?\b|\bnegligen\w*"
    r"|\bmal(?:a|as)\s+decisi(?:ó|o)n(?:es)?\b|\bculpa\b(?=\s+del?\b)|\bresponsabilidad\b(?=\s+del?\b)"
    r"|\bconfund\w*|\bdespist\w*|\bdistraj\w*|\bdistra[ií]\w*"
    r"|\bfalta\s+de\s+(?:cuidado|atenci[oó]n)\b|\bno\s+prest\w*\s+atenci[oó]n",
    re.IGNORECASE,
)
# Tras la falta, "de / del / por" y quizá un artículo antes de la persona: "culpa del revisor".
ENLACE_PERSONA = re.compile(r"\s*(?:de|del|por)\s+(?:(?:la|el|los|las|un|una|su|sus)\s+)?", re.IGNORECASE)
FIN_DE_ORACION = re.compile(r"[;!?¿¡]|[.:](?=\s|$)|->|\bsino\b", re.IGNORECASE)
FIN_DE_CLAUSULA = re.compile(r",|\bpero\b|\baunque\b", re.IGNORECASE)
AVISO_HEURISTICA_CULPA = (
    "es una heurística (alguien y una falta en la misma oración, sin negación): si no culpa a nadie,"
    " escribe la causa con el proceso o el diseño como sujeto"
)
# Sección 6: la regla se apoya en lo que declara la línea Autorización. Estas frases del plan la
# contradicen si dice "no hace falta"; los verbos destructivos solo piden confirmar que es reversible.
IRREVERSIBLE = re.compile(
    r"\birreversibles?\b|\bno se pueden? deshacer\b|\bfuera del encargo\b",
    re.IGNORECASE,
)
DESTRUCTIVO = re.compile(
    r"\b(?:borr(?:ar|a|an|ará|arán|aremos|ado|ada|ados|adas|amos|e|en)"
    r"|elimin(?:ar|a|an|ará|arán|aremos|ado|ada|ados|adas|amos|e|en)"
    r"|sobre?scrib\w*|format(?:ear|ea|eará|eado|eada|eo)"
    r"|vac(?:iar|ía|ían|iará|iado|iada|iamos|ió)|trunc(?:ar|a|ará|ado|ada|amos))\b",
    re.IGNORECASE,
)
REVERSIBLE = re.compile(r"\breversibles?\b", re.IGNORECASE)
NO_HACE_FALTA = ("no hace falta", "no aplica", "no se necesita", "no requiere", "no es necesaria")
# Marcas que solo trae el formato nuevo: con una basta para validarlo como v1.2.0 aunque la cabecera
# esté incompleta. Solo el documento que no trae ninguna sigue el camino de la v1.1.1.
MARCAS_FORMATO_NUEVO = (
    ("la línea '- **Brecha:**'", re.compile(r"^\s*[-*]\s*\*\*Brecha:\*\*", re.MULTILINE)),
    ("una causa '- **Causa A (Rama):**'", re.compile(r"^\s*[-*]\s*\*\*\s*Causa\s+[A-Za-z]\s*\([^)\n]*\)\s*:\*\*", re.MULTILINE)),
    ("la tabla de opciones", re.compile(r"^\s*\|\s*Opci[oó]n\s*\|", re.MULTILINE)),
    ("una línea 'Por lo tanto:'", re.compile(r"^\s*[-*]\s*(?:\*\*)?\s*por lo tanto\s*:", re.MULTILINE | re.IGNORECASE)),
    ("la tabla de ramas del Ishikawa", re.compile(r"^\s*\|\s*Rama\s*\|", re.MULTILINE)),
    ("la línea 'Ishikawa: no aplica'", re.compile(r"ishikawa\s*:\s*no aplica", re.IGNORECASE)),
)
NEGACIONES = {"no", "ni", "sin", "nunca", "nada", "nadie", "ningun", "ninguno", "ninguna", "ningunos", "ningunas", "tampoco", "jamas"}
RELLENO_FUENTE = {"", "-", "--", "n/a", "na", "pendiente", "por definir", "?", "sin fuente", "ninguna"}
# Una fuente que empieza así no dice de dónde sale el dato ("pendiente de medir", "no sé", "ninguna.").
PREFIJOS_RELLENO_FUENTE = (
    "pendiente", "por definir", "por medir", "por confirmar", "sin fuente", "no se", "no hay", "no tengo",
    "ninguna", "ninguno", "nada", "desconocid", "n/a", "tbd", "falta", "?",
)
# "Fuente: X" dentro de una viñeta o una línea con rótulo (- **Fuente verificable:** X).
FUENTE_EN_LINEA = re.compile(r"\bfuente\b[^:\n]{0,20}?:\**\s*(.*)$", re.IGNORECASE)


@dataclass
class Informe:
    """Resultado de validar un A3: etapa usada, errores de pensamiento y avisos de forma."""

    etapa: str | None
    origen_etapa: str
    formato: str = "nuevo"
    errores: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    @property
    def aprobado(self) -> bool:
        return not self.errores

    def error(self, mensaje: str) -> None:
        if mensaje not in self.errores:
            self.errores.append(mensaje)

    def aviso(self, mensaje: str) -> None:
        if mensaje not in self.avisos:
            self.avisos.append(mensaje)


@dataclass
class Seccion:
    numero: int | None
    titulo: str
    linea: int
    cuerpo: list[str]

    def tiene_contenido(self) -> bool:
        return any(linea.strip() for linea in self.cuerpo)


@dataclass
class Documento:
    lineas: list[str]
    cabecera: list[str]
    secciones: dict[int, Seccion]
    extras: list[Seccion]


@dataclass
class Tabla:
    encabezado: list[str]
    filas: list[list[str]]


@dataclass
class Causa:
    letra: str
    rama: str | None
    enunciado: str
    porques: list[str]
    por_lo_tanto: str | None


@dataclass
class Opcion:
    """Una fila de la tabla de opciones ya leída; None donde el valor no se pudo leer."""

    nombre: str
    causa: str
    nivel: str | None
    impacto: str | None
    esfuerzo: str | None
    cuadrante: str | None
    decision: str | None
    prediccion: str | None


# ---------------------------------------------------------------- utilidades de texto


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos, sin negritas ni comillas de código y con espacios simples."""
    sin_marcas = texto.replace("**", "").replace("`", "")
    descompuesto = unicodedata.normalize("NFKD", sin_marcas)
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return re.sub(r"[\s_-]+", " ", sin_acentos).strip().lower()


def sin_codigo(linea: str) -> str:
    return re.sub(r"`[^`\n]*`", "", linea)


def es_marcador_angular(interior: str) -> bool:
    """'<texto con espacios>': sin espacio al abrir ni al cerrar y con al menos un espacio dentro."""
    return not interior[0].isspace() and not interior[-1].isspace() and any(c.isspace() for c in interior)


def marcadores_angulares(texto: str) -> list[str]:
    return [m.group(0) for m in ANGULAR.finditer(texto) if es_marcador_angular(m.group(1))]


def quitar_marcadores_angulares(texto: str) -> str:
    return ANGULAR.sub(lambda m: "" if es_marcador_angular(m.group(1)) else m.group(0), texto)


def es_marcador_todo(texto: str, inicio: int, fin: int) -> bool:
    """'TODO' (con o sin negrita) es marcador al abrir campo, celda o nota o con ':', no como 'todo' español."""
    despues = texto[fin:].lstrip("*_")
    if despues.lstrip().startswith(":"):
        return True
    antes = texto[:inicio].rstrip(" *_")
    if antes and (antes[-1].isalnum() or antes[-1] == "_"):
        return False
    return TODO_ESPANOL_SIGUE.match(despues) is None


def marcadores(lineas: list[str]) -> list[str]:
    """Marcadores de plantilla sin completar, fuera de código en línea o cercado."""
    hallados: list[str] = []
    en_codigo = False
    for linea in lineas:
        if linea.strip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if en_codigo:
            continue
        limpia = sin_codigo(linea)
        encontrados = marcadores_angulares(limpia)
        encontrados += [
            m.group(0) for m in PALABRA_TODO.finditer(limpia) if es_marcador_todo(limpia, m.start(), m.end())
        ]
        for patron in (MARCADOR_PALABRA, MARCADOR_CORCHETE):
            encontrados += [m.group(0) for m in patron.finditer(limpia)]
        for marcador in encontrados:
            if marcador not in hallados:
                hallados.append(marcador)
    return hallados


def tiene_texto_real(valor: str) -> bool:
    """True si al quitar los marcadores angulares queda algo con letras o cifras."""
    return bool(re.search(r"\w", quitar_marcadores_angulares(valor)))


def fuente_real(valor: str) -> bool:
    """True si la fuente dice de dónde sale el dato: no es relleno y tiene al menos una palabra."""
    if not tiene_texto_real(valor) or marcadores([valor]):
        return False
    clave = normalizar(valor).strip(" .,;:!¡¿?()[]")
    if clave in RELLENO_FUENTE or any(clave == p or clave.startswith(p + " ") for p in PREFIJOS_RELLENO_FUENTE):
        return False
    return bool(re.search(r"[^\W\d_]{2,}", valor))


def _quitar_comillas_exteriores(texto: str) -> str:
    s = texto.strip()
    if len(s) >= 2 and s.startswith("`") and s.endswith("`") and "`" not in s[1:-1]:
        return s[1:-1].strip()
    return s


def _partir_fuentes(celda_texto: str) -> list[str] | None:
    partes: list[str] = []
    actual: list[str] = []
    en_comillas = False
    for ch in celda_texto:
        if ch == "`":
            en_comillas = not en_comillas
            actual.append(ch)
        elif ch == ";" and not en_comillas:
            parte = "".join(actual).strip()
            if not parte:
                return None
            partes.append(parte)
            actual = []
        else:
            actual.append(ch)
    ultima = "".join(actual).strip()
    if not ultima:
        return None
    partes.append(ultima)
    return partes


def resolver_bases_fuentes(ruta_a3: Path, raiz: Path | None = None) -> tuple[Path, ...]:
    base_a3 = ruta_a3.resolve().parent
    if raiz is not None:
        base_raiz: Path | None = raiz.resolve()
    else:
        base_raiz = None
        for directorio in (base_a3, *base_a3.parents):
            try:
                if (directorio / ".git").exists():
                    base_raiz = directorio
                    break
            except OSError:
                break
    if base_raiz is None or base_raiz == base_a3:
        return (base_a3,)
    return (base_a3, base_raiz)


def _candidatos_en_bases(ruta_str: str, bases: Sequence[Path]) -> list[Path]:
    if (
        not ruta_str
        or "\x00" in ruta_str
        or "`" in ruta_str
        or Path(ruta_str).is_absolute()
        or re.match(r"^[a-zA-Z]:", ruta_str)
        or ruta_str.startswith("\\\\")
    ):
        return []
    candidatos: list[Path] = []
    for base in bases:
        try:
            candidato = (base / ruta_str).resolve()
            if not candidato.is_relative_to(base):
                continue
            if candidato.is_file():
                candidatos.append(candidato)
        except (OSError, ValueError):
            continue
    return candidatos


def _pesa_mas_de_cero(ruta_archivo: Path) -> bool:
    try:
        return ruta_archivo.stat().st_size > 0
    except OSError:
        return False


def _tiene_al_menos_lineas(ruta_archivo: Path, minimo: int) -> bool:
    try:
        crudo = ruta_archivo.read_bytes()
    except OSError:
        return False
    try:
        total = len(crudo.decode("utf-8").splitlines())
    except UnicodeDecodeError:
        total = len(crudo.splitlines())
    return total >= minimo


def _fuente_parte_valida(parte_cruda: str, bases: Sequence[Path]) -> bool:
    parte = parte_cruda.strip()
    m_cmd = re.match(r"^`([^`\n]+)`\s*->\s*(.+)$", parte)
    if m_cmd:
        if not m_cmd.group(1).strip():
            return False
        ruta_str = _quitar_comillas_exteriores(m_cmd.group(2))
        return any(_pesa_mas_de_cero(c) for c in _candidatos_en_bases(ruta_str, bases))

    sin_comillas = _quitar_comillas_exteriores(parte)
    m_ev = re.match(r"^evidencia:(.*)$", sin_comillas, re.IGNORECASE)
    if m_ev:
        ruta_str = _quitar_comillas_exteriores(m_ev.group(1))
        return any(_pesa_mas_de_cero(c) for c in _candidatos_en_bases(ruta_str, bases))

    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", sin_comillas):
        return bool(re.fullmatch(r"https://\S+", sin_comillas))

    m_linea = re.match(r"^(.+):(\d+)(?:-(\d+))?$", sin_comillas)
    if m_linea:
        ruta_str = _quitar_comillas_exteriores(m_linea.group(1))
        inicio = int(m_linea.group(2))
        fin = int(m_linea.group(3)) if m_linea.group(3) is not None else inicio
        if inicio < 1 or inicio > fin:
            return False
        return any(_tiene_al_menos_lineas(c, fin) for c in _candidatos_en_bases(ruta_str, bases))

    return False


def fuente_cuatro_formas_valida(valor: str, bases: Sequence[Path]) -> bool:
    if not valor.strip() or not tiene_texto_real(valor) or marcadores([valor]):
        return False
    clave = normalizar(valor).strip(" .,;:!¡¿?()[]")
    if clave in RELLENO_FUENTE or any(clave == p or clave.startswith(p + " ") for p in PREFIJOS_RELLENO_FUENTE):
        return False
    partes = _partir_fuentes(valor)
    if not partes:
        return False
    return all(_fuente_parte_valida(parte, bases) for parte in partes)


def mensaje_fuente_invalida(seccion: int, celda_fuente: str, hecho: str) -> str:
    return (
        f"sección {seccion}: la fuente '{celda_fuente}' del hecho '{hecho}' "
        "no tiene una forma válida o no existe. "
        "Formas válidas: ruta:línea; `comando` -> ruta; https://...; evidencia: ruta."
    )


def _hecho_de_vineta_fuente(linea: str, inicio_fuente: int) -> str:
    prefijo = re.sub(r"^\s*[-*]\s*", "", linea[:inicio_fuente])
    limpio = prefijo.rstrip(" *_.,;:-(").strip()
    return limpio or "(sin texto)"


def negado(texto: str, inicio: int, ventana: int = 3) -> bool:
    """True si una negación de la misma cláusula está entre las `ventana` palabras previas a `inicio`."""
    clausula = FIN_DE_CLAUSULA.split(texto[:inicio])[-1]
    previas = re.findall(r"\w+", normalizar(clausula))[-ventana:]
    return any(p in NEGACIONES or p.startswith("descart") for p in previas)


def culpa_en(texto: str) -> str | None:
    """Pista de culpa ('persona' + 'falta') si una oración culpa a alguien; None si no (heurística)."""
    for oracion in FIN_DE_ORACION.split(texto):
        for falta in FALTA.finditer(oracion):
            if negado(oracion, falta.start(), ventana=6):
                continue
            if PERSONA.search(falta.group(0)):
                return falta.group(0)
            antes = list(PERSONA.finditer(oracion, 0, falta.start()))
            if antes:
                return f"{antes[-1].group(0)} ... {falta.group(0)}"
            enlace = ENLACE_PERSONA.match(oracion, falta.end())
            despues = PERSONA.match(oracion, enlace.end()) if enlace else None
            if despues:
                return f"{falta.group(0)} {oracion[falta.end() : despues.end()].strip()}"
    return None


def respuesta(linea: str) -> str:
    """Lo que responde un porqué: el texto tras '->' o, si no hay flecha, tras la pregunta."""
    if "->" in linea:
        return linea.split("->", 1)[1]
    if "?" in linea:
        return linea.rsplit("?", 1)[1]
    return re.sub(r"^\s*[-*]\s*\d+[a-z]?[.)]\s*", "", linea)


def coincidir(valor: str, permitidos: Sequence[str]) -> tuple[str | None, bool]:
    """Devuelve (valor canónico, escrito exactamente igual) o (None, False)."""
    limpio = valor.strip().strip("`").strip()
    for canonico in permitidos:
        if limpio == canonico:
            return canonico, True
    clave = normalizar(limpio)
    for canonico in permitidos:
        if clave == normalizar(canonico):
            return canonico, False
    return None, False


def coincidir_rama(valor: str, contrato: dict | None = None) -> tuple[str | None, bool]:
    ramas = tuple((contrato or cargar_contrato(1))["ramas"])
    canonica, exacta = coincidir(valor, ramas)
    if canonica:
        return canonica, exacta
    clave = normalizar(valor)
    for rama in ramas:
        base = normalizar(rama)
        if clave.startswith(base + " ") or clave.startswith(base + "("):
            return rama, False
    return None, False


def lista(valores: Sequence[str]) -> str:
    return ", ".join(valores)


def valor_de_campo(linea: str) -> str:
    return linea.split(":**", 1)[1].strip() if ":**" in linea else ""


# ---------------------------------------------------------------- lectura del documento


def celdas(linea: str) -> list[str]:
    """Parte una fila de tabla. Una barra escrita '\\|' es parte de la celda y se entrega sin la contrabarra."""
    s = linea.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    return [c.strip().replace("\\|", "|") for c in BARRA_SIN_ESCAPAR.split(s)]


def avisar_celdas_desparejas(tabla: Tabla, donde: str, informe: Informe) -> None:
    """Una fila con más o menos celdas que el encabezado suele ser una barra sin escapar."""
    for fila in tabla.filas:
        if len(fila) != len(tabla.encabezado):
            informe.aviso(
                f"{donde}: la fila '{fila[0]}' tiene {len(fila)} celdas y el encabezado {len(tabla.encabezado)};"
                " si una celda lleva una barra, escríbela '\\|'"
            )


def es_separador(linea: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?(\s*:?-+:?\s*\|)*\s*:?-+:?\s*\|?\s*", linea))


def tablas(lineas: list[str]) -> list[Tabla]:
    resultado: list[Tabla] = []
    i = 0
    while i < len(lineas):
        if lineas[i].strip().startswith("|"):
            bloque: list[str] = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                bloque.append(lineas[i])
                i += 1
            filas = [celdas(f) for f in bloque[1:] if not es_separador(f)]
            resultado.append(Tabla(celdas(bloque[0]), [f for f in filas if any(f)]))
        else:
            i += 1
    return resultado


def columna(tabla: Tabla, nombre: str) -> int | None:
    clave = normalizar(nombre)
    for i, titulo in enumerate(tabla.encabezado):
        if normalizar(titulo) == clave:
            return i
    for i, titulo in enumerate(tabla.encabezado):
        if normalizar(titulo).startswith(clave):
            return i
    return None


def celda(fila: list[str], indice: int | None) -> str:
    if indice is None or indice >= len(fila):
        return ""
    return fila[indice]


def leer_documento(texto: str) -> tuple[Documento, list[str]]:
    """Separa cabecera y secciones; devuelve también los avisos sobre títulos de sección."""
    lineas = texto.split("\n")
    avisos: list[str] = []
    encabezados: list[tuple[int, str]] = []
    en_codigo = False
    for i, linea in enumerate(lineas):
        if linea.strip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if not en_codigo and re.match(r"##(?!#)(\s|$)", linea):
            encabezados.append((i, linea[2:].strip()))
    fin_cabecera = encabezados[0][0] if encabezados else len(lineas)
    secciones: dict[int, Seccion] = {}
    extras: list[Seccion] = []
    orden: list[int] = []
    for posicion, (inicio, titulo) in enumerate(encabezados):
        fin = encabezados[posicion + 1][0] if posicion + 1 < len(encabezados) else len(lineas)
        numero = numero_de_seccion(titulo, avisos)
        seccion = Seccion(numero, titulo, inicio, lineas[inicio + 1 : fin])
        if numero is None:
            extras.append(seccion)
        elif numero in secciones:
            avisos.append(f"sección {numero}: el título aparece más de una vez; se lee la primera")
        else:
            secciones[numero] = seccion
            orden.append(numero)
    if orden != sorted(orden):
        avisos.append("las secciones numeradas van en otro orden; el orden del A3 es de 1 a 7")
    return Documento(lineas, lineas[:fin_cabecera], secciones, extras), avisos


def numero_de_seccion(titulo: str, avisos: list[str]) -> int | None:
    m = re.match(r"(\d+)\.\s*(.*)$", titulo)
    if m and 1 <= int(m.group(1)) <= 7:
        numero = int(m.group(1))
        nombre = m.group(2).strip()
        canonico = NOMBRES[numero]
        if nombre != canonico and not nombre.startswith(canonico + " ("):
            avisos.append(f"sección {numero}: el título debería ser '{numero}. {canonico}' (dice '{titulo}')")
        return numero
    clave = normalizar(titulo)
    for numero, nombre in NOMBRES.items():
        base = normalizar(nombre)
        if clave == base or clave.startswith(base + " ("):
            avisos.append(f"el título '## {titulo}' no lleva número; escribe '## {numero}. {nombre}'")
            return numero
    return None


def leer_campos(lineas: list[str]) -> dict[str, tuple[str, str]]:
    campos: dict[str, tuple[str, str]] = {}
    for linea in lineas:
        m = CAMPO.match(linea)
        if m:
            clave = normalizar(m.group(1))
            if clave and clave not in campos:
                campos[clave] = (m.group(1).strip(), m.group(2).strip())
    return campos


def tiene_estructura_a3(doc: Documento) -> bool:
    """True si el documento trae un título '# A3:' o al menos una sección del A3."""
    if doc.secciones:
        return True
    en_codigo = False
    for linea in doc.cabecera:
        if linea.strip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if not en_codigo and re.match(r"^\s*#(?!#)\s*A3\s*:", linea, re.IGNORECASE):
            return True
    return False


# ---------------------------------------------------------------- formato nuevo


def validar_a3(
    texto: str,
    etapa: str | None = None,
    *,
    ruta_a3: Path | None = None,
    raiz: Path | None = None,
) -> Informe:
    """Valida el texto de un A3. `etapa` manda sobre la cabecera; con None se lee de la cabecera."""
    if raiz is not None:
        raiz_path = Path(raiz)
        if not raiz_path.is_dir():
            raise ValueError(f"raiz no existe o no es una carpeta: {raiz}")
    else:
        raiz_path = None
    ruta_a3_path = Path(ruta_a3) if ruta_a3 is not None else None

    texto = unicodedata.normalize("NFC", texto.removeprefix("\ufeff")).replace("\r\n", "\n").replace("\r", "\n")
    doc, avisos_titulos = leer_documento(texto)
    campos = leer_campos(doc.cabecera)
    contrato_base = cargar_contrato(1)
    if etapa is not None and etapa not in contrato_base["etapas"]:
        raise ValueError(f"etapa desconocida: {etapa!r}")
    marcas_nuevas = marcas_del_formato_nuevo(texto)
    if not texto.strip() or (
        not tiene_estructura_a3(doc) and "etapa" not in campos and "propietario" not in campos and not marcas_nuevas
    ):
        informe = Informe(etapa=None, origen_etapa="sin estructura", formato="sin_estructura")
        informe.error("el archivo está vacío o no tiene estructura de A3")
        return informe
    sin_cabecera_nueva = etapa is None and "etapa" not in campos and "propietario" not in campos
    marcas = marcas_nuevas if sin_cabecera_nueva else []
    if sin_cabecera_nueva and not marcas:
        return validar_formato_anterior(texto, doc, contrato_base)

    campo_contrato = campos.get("contrato")
    contrato: dict | None = None
    error_contrato: str | None = None
    if campo_contrato is None:
        contrato = contrato_base
    else:
        val_contrato = campo_contrato[1].strip()
        if re.fullmatch(r"[0-9]+", val_contrato) and str(int(val_contrato)) == val_contrato:
            try:
                contrato = cargar_contrato(int(val_contrato))
            except KeyError:
                error_contrato = f"Cabecera: el Contrato '{val_contrato}' no existe; los válidos son 1 y 2"
        else:
            error_contrato = f"Cabecera: el Contrato '{val_contrato}' no existe; los válidos son 1 y 2"

    if contrato is not None and etapa is not None and etapa not in contrato["etapas"]:
        raise ValueError(f"etapa desconocida: {etapa!r}")
    if contrato is not None and contrato["reglas"]["fuentes"] == "cuatro_formas" and ruta_a3_path is None:
        raise ValueError("contrato 2 requiere ruta_a3")

    informe = Informe(etapa=None, origen_etapa="pedida con --etapa" if etapa else "leída de la cabecera")
    if marcas:
        informe.aviso(
            f"se valida como formato nuevo (v1.2.0) porque trae {', '.join(marcas)}; la cabecera necesita"
            " las líneas Propietario y Etapa"
        )
    if error_contrato is not None:
        informe.error(error_contrato)
        for aviso in avisos_titulos:
            informe.aviso(aviso)
        validar_cabecera(doc, campos, informe)
        no_vacias = sum(1 for linea in doc.lineas if linea.strip())
        if no_vacias > MAX_LINEAS:
            informe.error(f"el A3 tiene {no_vacias} líneas no vacías y el máximo es {MAX_LINEAS} (una página); sintetiza")
        return informe

    assert contrato is not None
    bases_fuentes = (
        resolver_bases_fuentes(ruta_a3_path, raiz_path)
        if contrato["reglas"]["fuentes"] == "cuatro_formas" and ruta_a3_path is not None
        else ()
    )

    etapa_cabecera = leer_etapa(campos, etapa, informe, contrato)
    efectiva = etapa or etapa_cabecera
    informe.etapa = efectiva
    for aviso in avisos_titulos:
        informe.aviso(aviso)

    validar_cabecera(doc, campos, informe)
    no_vacias = sum(1 for linea in doc.lineas if linea.strip())
    if no_vacias > MAX_LINEAS:
        informe.error(f"el A3 tiene {no_vacias} líneas no vacías y el máximo es {MAX_LINEAS} (una página); sintetiza")
    if efectiva is None:
        return informe

    ultima = contrato["ultima_seccion"][efectiva]
    completas: dict[int, Seccion] = {}
    for numero in range(1, ultima + 1):
        seccion = doc.secciones.get(numero)
        if seccion is None:
            informe.error(f"sección {numero}: falta '## {numero}. {NOMBRES[numero]}'; la etapa {efectiva} la exige")
        elif not seccion.tiene_contenido():
            informe.error(f"sección {numero}: está vacía; la etapa {efectiva} la exige completa")
        else:
            completas[numero] = seccion
            for marcador in marcadores(seccion.cuerpo):
                informe.error(f"sección {numero}: Contiene placeholder sin completar: '{marcador}'")
            for tabla in tablas(seccion.cuerpo):
                avisar_celdas_desparejas(tabla, f"sección {numero}", informe)
    futuras = [n for n, s in sorted(doc.secciones.items()) if n > ultima and s.tiene_contenido()]
    if futuras:
        informe.aviso(
            f"las secciones {', '.join(map(str, futuras))} tienen contenido y no se validan en la etapa {efectiva}"
        )

    if 2 in completas:
        validar_seccion_2(completas[2], doc, informe, contrato, bases_fuentes)
    causas = validar_seccion_4(completas[4], informe, contrato, bases_fuentes) if 4 in completas else []
    if 5 in completas:
        validar_seccion_5(completas[5], causas, informe, contrato)
    irreversible = validar_seccion_6(completas[6], informe) if 6 in completas else False
    if 7 in completas:
        validar_seccion_7(completas[7], informe, contrato)
    validar_coach(campos, efectiva, irreversible, informe)
    # El bloque Siguientes pasos depende de la etapa del documento (su cabecera), no de la pedida.
    validar_siguientes_pasos(doc, etapa_cabecera or efectiva, informe)
    return informe


def marcas_del_formato_nuevo(texto: str) -> list[str]:
    """Nombres de las marcas del formato nuevo que aparecen en el texto."""
    return [nombre for nombre, patron in MARCAS_FORMATO_NUEVO if patron.search(texto)]


def leer_etapa(
    campos: dict[str, tuple[str, str]], pedida: str | None, informe: Informe, contrato: dict | None = None
) -> str | None:
    etapas = tuple((contrato or cargar_contrato(1))["etapas"])
    campo = campos.get("etapa")
    etapa_cabecera: str | None = None
    if campo is not None:
        valor = campo[1]
        clave = normalizar(valor)
        if clave in etapas:
            etapa_cabecera = clave
        elif not clave:
            informe.error(f"Cabecera: la línea Etapa está vacía; usa una de: {lista(etapas)}")
        else:
            informe.error(f"Cabecera: la Etapa '{valor}' no es una etapa válida; usa una de: {lista(etapas)}")
    if pedida:
        if campo is None:
            informe.aviso(f"Cabecera: falta la línea '- **Etapa:**'; se valida como '{pedida}' por la opción --etapa")
        elif etapa_cabecera and etapa_cabecera != pedida:
            informe.aviso(f"la opción --etapa ({pedida}) manda sobre la Etapa de la cabecera ({etapa_cabecera})")
    elif campo is None:
        informe.error(f"Cabecera: falta la línea '- **Etapa:**' ({lista(etapas)}); escríbela o pasa la opción --etapa")
    return etapa_cabecera


def validar_cabecera(doc: Documento, campos: dict[str, tuple[str, str]], informe: Informe) -> None:
    titulo = next((linea for linea in doc.cabecera if re.match(r"#(?!#)", linea)), None)
    if titulo is None:
        informe.error("Cabecera: falta el título '# A3: ...' que nombra el problema")
    else:
        texto = re.sub(r"^#\s*", "", titulo).strip()
        if not re.match(r"A3\s*:", texto):
            informe.aviso("Cabecera: el título debería empezar con '# A3:'")
        hallados = marcadores([titulo])
        for marcador in hallados:
            informe.error(f"Cabecera: Contiene placeholder sin completar: '{marcador}'")
        if not hallados and not re.sub(r"^A3\s*:\s*", "", texto).strip():
            informe.error("Cabecera: el título está vacío; nombra el problema, no la solución")
    for rotulo, valor in campos.values():
        for marcador in marcadores([valor]):
            informe.error(f"Cabecera ({rotulo}): Contiene placeholder sin completar: '{marcador}'")
    propietario = campos.get("propietario")
    if propietario is None:
        informe.error("Cabecera: falta la línea '- **Propietario:**' (quien responde por el problema)")
    elif not tiene_texto_real(propietario[1]) and not marcadores([propietario[1]]):
        informe.error("Cabecera: Propietario está vacío; di quién responde por el problema")
    version = campos.get("version")
    if version is None:
        informe.aviso("Cabecera: falta la línea '- **Versión:**' (número entero y fecha AAAA-MM-DD)")
    elif not re.fullmatch(r"\d+\s*\(\d{4}-\d{2}-\d{2}\)", version[1]):
        informe.aviso(f"Cabecera: la Versión '{version[1]}' debería ser un número entero y la fecha: '3 (2026-10-02)'")


def validar_seccion_2(
    seccion: Seccion,
    doc: Documento,
    informe: Informe,
    contrato: dict | None = None,
    bases_fuentes: Sequence[Path] = (),
) -> None:
    contrato_act = contrato or cargar_contrato(1)
    cuatro_formas = contrato_act["reglas"]["fuentes"] == "cuatro_formas"
    cuerpo = seccion.cuerpo
    brechas = [linea for linea in cuerpo if BRECHA.match(linea)]
    parecidas = [linea for linea in cuerpo if re.match(r"\s*[-*]\s*\*\*Brecha\b[^*]*:\*\*", linea)]
    linea_brecha: str | None = None
    if brechas:
        linea_brecha = brechas[0]
    elif parecidas:
        linea_brecha = parecidas[0]
        informe.aviso("sección 2: el rótulo de la brecha debe ser exactamente '- **Brecha:**'")
    else:
        fuera = [linea for linea in doc.lineas if BRECHA.match(linea)]
        if fuera:
            linea_brecha = fuera[0]
            informe.aviso("la línea '- **Brecha:**' está fuera de la sección 2; va en la sección 2")
    otras = [linea for linea in cuerpo if linea not in brechas and linea not in parecidas]

    tabla_hechos = next((t for t in tablas(cuerpo) if columna(t, "Fuente") is not None), None)
    coincidencias_fuente = [(linea, m) for linea in otras if (m := FUENTE_EN_LINEA.search(linea))]
    if tabla_hechos is not None:
        i_fuente = columna(tabla_hechos, "Fuente")
        if not tabla_hechos.filas:
            informe.error("sección 2: la tabla de hechos no tiene filas; ningún hecho tiene fuente")
        for fila in tabla_hechos.filas:
            hecho = celda(fila, 0) or "(sin texto)"
            valor_fuente = celda(fila, i_fuente)
            if cuatro_formas:
                if not fuente_cuatro_formas_valida(valor_fuente, bases_fuentes):
                    informe.error(mensaje_fuente_invalida(2, valor_fuente, hecho))
            elif not fuente_real(valor_fuente):
                informe.error(f"sección 2: el hecho '{hecho}' está sin fuente (ruta, comando, registro o medición)")
    elif cuatro_formas:
        if coincidencias_fuente:
            al_menos_una_valida = False
            for linea, m in coincidencias_fuente:
                valor_fuente = m.group(1)
                hecho = _hecho_de_vineta_fuente(linea, m.start())
                if fuente_cuatro_formas_valida(valor_fuente, bases_fuentes):
                    al_menos_una_valida = True
                else:
                    informe.error(mensaje_fuente_invalida(2, valor_fuente, hecho))
            if al_menos_una_valida:
                informe.aviso("sección 2: los hechos se leen mejor en la tabla '| Hecho medido | Fuente |'")
        else:
            informe.error("sección 2: ningún hecho tiene fuente; cada dato medido dice de dónde sale")
    elif any(fuente_real(m.group(1)) for _, m in coincidencias_fuente):
        informe.aviso("sección 2: los hechos se leen mejor en la tabla '| Hecho medido | Fuente |'")
    elif coincidencias_fuente:
        informe.error("sección 2: los hechos están sin fuente; la línea 'Fuente:' no dice de dónde sale el dato")
    else:
        informe.error("sección 2: ningún hecho tiene fuente; cada dato medido dice de dónde sale")

    if linea_brecha is None:
        informe.error("sección 2: falta la línea '- **Brecha:** de X (medido) a Y (meta) para <cuándo>'")
        return
    valor = valor_de_campo(linea_brecha)
    if not valor or marcadores([valor]) or not tiene_texto_real(valor):
        informe.error("sección 2: la línea Brecha está vacía o sin completar; di de cuánto a cuánto y para cuándo")
        return
    if not re.match(r"de\s+.+?\(medido\)\s+a\s+.+?\(meta\)\s+para\s+\S", valor, re.IGNORECASE):
        informe.aviso("sección 2: la Brecha debería tener la forma 'de X (medido) a Y (meta) para <cuándo>'")
    if not re.search(r"\d", valor):
        informe.aviso("sección 2: la Brecha no tiene ninguna cifra; sin número no se sabe si se cerró")


def validar_seccion_4(
    seccion: Seccion,
    informe: Informe,
    contrato: dict | None = None,
    bases_fuentes: Sequence[Path] = (),
) -> list[Causa]:
    contrato_act = contrato or cargar_contrato(1)
    cuerpo = seccion.cuerpo
    tablas_s4 = tablas(cuerpo)
    filas_vs = [normalizar(celda(f, 0)) for t in tablas_s4 for f in t.filas]
    for rotulo in ("Verificado", "Supuesto"):
        if normalizar(rotulo) not in filas_vs:
            informe.error(f"sección 4: falta la fila '{rotulo}' de la tabla Verificado / Supuesto")

    if contrato_act["reglas"]["fuentes"] == "cuatro_formas":
        tabla_obs = next((t for t in tablas_s4 if normalizar(celda(t.encabezado, 0)) == "estado"), None)
        if tabla_obs is not None:
            for fila in tabla_obs.filas:
                if normalizar(celda(fila, 0).strip("*_ ")) == "verificado":
                    hecho = celda(fila, 1) or "(sin texto)"
                    valor_fuente = celda(fila, 2)
                    if not fuente_cuatro_formas_valida(valor_fuente, bases_fuentes):
                        informe.error(mensaje_fuente_invalida(4, valor_fuente, hecho))

    causas = leer_causas(cuerpo, informe, contrato_act)
    if not causas:
        informe.error("sección 4: no hay ninguna causa; escribe '- **Causa A (Rama):**' con sus porqués")
    elif not any(re.match(r"\s*###\s*4b\.\s*Porqu[eé]s por causa", linea) for linea in cuerpo):
        informe.aviso("sección 4: falta el subtítulo '### 4b. Porqués por causa' sobre las causas")

    ishikawa = next((t for t in tablas(cuerpo) if normalizar(celda(t.encabezado, 0)) == "rama"), None)
    no_aplica = any(normalizar(linea).lstrip("* ").startswith("ishikawa: no aplica") for linea in cuerpo)
    if ishikawa is None:
        if not no_aplica:
            informe.error("sección 4: falta la tabla de Ishikawa o la línea 'Ishikawa: no aplica, una sola hipótesis (...)'")
        elif len(causas) >= 2:
            informe.error(
                f"sección 4: Ishikawa dice 'no aplica' pero hay {len(causas)} causas; con dos o más"
                " hipótesis va la tabla de seis ramas"
            )
    else:
        if not any(re.match(r"\s*###\s*4a\.\s*Ishikawa", linea) for linea in cuerpo):
            informe.aviso("sección 4: falta el subtítulo '### 4a. Ishikawa' sobre la tabla")
        validar_ishikawa(ishikawa, causas, informe, contrato_act)

    vistas: set[str] = set()
    for causa in causas:
        if causa.letra and causa.letra in vistas:
            informe.error(f"sección 4: la letra de Causa {causa.letra} está repetida; cada causa lleva la suya")
        vistas.add(causa.letra)
    return causas


def leer_causas(cuerpo: list[str], informe: Informe, contrato: dict | None = None) -> list[Causa]:
    contrato_act = contrato or cargar_contrato(1)
    ramas = tuple(contrato_act["ramas"])
    causas: list[Causa] = []
    i = 0
    while i < len(cuerpo):
        m = CAUSA.match(cuerpo[i])
        if not m:
            i += 1
            continue
        dentro, enunciado = m.group(1).strip(), m.group(2).strip()
        partes = re.fullmatch(r"([A-Za-z]?)\s*(?:\((.*)\))?", dentro)
        letra, rama_texto = (partes.group(1), partes.group(2)) if partes else ("", None)
        nombre = f"Causa {letra.upper()}" if letra else "una causa sin letra"
        if partes is None:
            informe.error(f"sección 4: la causa '{dentro}' no sigue la forma '- **Causa A (Rama):**'")
        elif not letra:
            informe.error("sección 4: una causa no lleva letra; usa '- **Causa A (Rama):**'")
        elif letra != letra.upper():
            informe.aviso(f"sección 4: la letra de la causa va en mayúscula: 'Causa {letra.upper()}'")
        letra = letra.upper()
        rama: str | None = None
        if partes is not None:
            if not rama_texto or not rama_texto.strip():
                informe.error(f"sección 4: {nombre} no dice entre paréntesis de qué rama sale")
            else:
                rama, exacta = coincidir_rama(rama_texto, contrato_act)
                if rama is None:
                    informe.error(
                        f"sección 4: {nombre}: la rama '{rama_texto.strip()}' no es un valor permitido ({lista(ramas)})"
                    )
                elif not exacta:
                    informe.aviso(f"sección 4: {nombre}: la rama se escribe '{rama}'")
        bloque: list[str] = []
        i += 1
        while i < len(cuerpo):
            linea = cuerpo[i]
            if not linea.strip():
                i += 1
                continue
            if CAUSA.match(linea) or not linea[0].isspace():
                break
            bloque.append(linea)
            i += 1
        porques = [linea for linea in bloque if PORQUE.match(linea)]
        por_lo_tanto: str | None = None
        for linea in bloque:
            mp = POR_LO_TANTO.match(linea)
            if mp:
                por_lo_tanto = mp.group(1).strip()
        causas.append(Causa(letra, rama, enunciado, porques, por_lo_tanto))
        if not tiene_texto_real(enunciado) and not marcadores([enunciado]):
            informe.error(f"sección 4: {nombre} no tiene enunciado")
        if not porques:
            informe.error(f"sección 4: {nombre} no tiene ningún porqué ('  - 1. ¿Por qué ...? -> ...')")
        elif any(not tiene_texto_real(respuesta(p)) and not marcadores([respuesta(p)]) for p in porques):
            informe.error(f"sección 4: {nombre} tiene un porqué sin respuesta")
        if por_lo_tanto is None:
            informe.error(f"sección 4: {nombre} no cierra con su línea 'Por lo tanto:'")
        elif not tiene_texto_real(por_lo_tanto):
            informe.error(f"sección 4: {nombre}: la línea 'Por lo tanto:' está vacía; léela de abajo hacia arriba")
        # La culpa se mira solo en las líneas de causa: el enunciado y el último porqué de la cadena.
        palabra = culpa_en(enunciado) or (culpa_en(respuesta(porques[-1])) if porques else None)
        if palabra:
            informe.error(
                f"sección 4: {nombre} culpa a una persona o a un agente ('{palabra}'); sigue preguntando"
                f" por qué hasta llegar al proceso o al diseño; {AVISO_HEURISTICA_CULPA}"
            )
    return causas


def validar_ishikawa(tabla: Tabla, causas: list[Causa], informe: Informe, contrato: dict | None = None) -> None:
    contrato_act = contrato or cargar_contrato(1)
    ramas = tuple(contrato_act["ramas"])
    estados_rama = tuple(contrato_act["estados_rama"])
    i_estado = columna(tabla, "Estado")
    i_evidencia = columna(tabla, "Evidencia")
    i_estado = 3 if i_estado is None else i_estado
    i_evidencia = 2 if i_evidencia is None else i_evidencia
    estados: dict[str, str] = {}
    vistas: list[str] = []
    for fila in tabla.filas:
        texto_rama = celda(fila, 0)
        rama, exacta = coincidir_rama(texto_rama, contrato_act)
        if rama is None:
            informe.error(
                f"sección 4: la rama '{texto_rama}' no es una de las seis ({lista(ramas)}); lo que toca a las"
                " personas va en 'Relevo': el encargo y la entrega, nunca la persona"
            )
            continue
        if not exacta:
            informe.aviso(f"sección 4: la rama '{texto_rama}' se escribe '{rama}'")
        vistas.append(rama)
        texto_estado = celda(fila, i_estado)
        estado, exacto = coincidir(texto_estado, estados_rama)
        if estado is None:
            informe.error(
                f"sección 4: rama {rama}: el estado '{texto_estado}' no es un valor permitido ({' o '.join(estados_rama)})"
            )
            continue
        if not exacto:
            informe.aviso(f"sección 4: rama {rama}: el estado se escribe '{estado}'")
        estados.setdefault(rama, estado)
        if estado == "DESCARTADA" and not tiene_texto_real(celda(fila, i_evidencia)):
            informe.error(f"sección 4: la rama {rama} está DESCARTADA sin evidencia; una línea breve basta")
    for rama in ramas:
        if rama not in vistas:
            informe.error(f"sección 4: falta la rama '{rama}' en el Ishikawa (van las seis: {lista(ramas)})")
    if vistas != [r for r in ramas if r in vistas] and len(set(vistas)) == len(vistas):
        informe.aviso(f"sección 4: las ramas del Ishikawa van en otro orden; el orden es {lista(ramas)}")
    if estados and "FOCO" not in estados.values():
        informe.error("sección 4: ninguna rama está en FOCO; al menos una hipótesis sigue viva")
    ramas_de_causas = {c.rama for c in causas if c.rama}
    for causa in causas:
        if causa.rama and estados.get(causa.rama) == "DESCARTADA":
            informe.error(f"sección 4: Causa {causa.letra or '?'} sale de la rama {causa.rama}, que está DESCARTADA")
    for rama, estado in estados.items():
        if estado == "FOCO" and rama not in ramas_de_causas:
            informe.error(f"sección 4: la rama {rama} está en FOCO y ninguna causa sale de ella")


def leer_unica_opcion(cuerpo: list[str]) -> str | None:
    """Motivo de la línea 'Única opción:' (con o sin viñeta y negrita); None si no está."""
    for linea in cuerpo:
        limpia = re.sub(r"^\s*(?:[-*]\s+)?", "", linea).replace("**", "")
        if normalizar(limpia).startswith("unica opcion"):
            return limpia.split(":", 1)[1].strip() if ":" in limpia else ""
    return None


def validar_seccion_5(
    seccion: Seccion, causas: list[Causa], informe: Informe, contrato: dict | None = None
) -> None:
    contrato_act = contrato or cargar_contrato(1)
    columnas_opciones = tuple(contrato_act["columnas_opciones"])
    cuerpo = seccion.cuerpo
    tabla = next((t for t in tablas(cuerpo) if normalizar(celda(t.encabezado, 0)) == "opcion"), None)
    unica = leer_unica_opcion(cuerpo)
    if unica is not None and (not unica or marcadores([unica]) or not tiene_texto_real(unica)):
        informe.error("sección 5: la línea 'Única opción:' no dice el motivo por el que no hay otra")
    if tabla is None:
        if unica is None:
            informe.error("sección 5: falta la tabla de opciones (mínimo dos) o la línea 'Única opción: <motivo>'")
        return
    if len(tabla.filas) < 2 and unica is None:
        informe.error(
            f"sección 5: la tabla tiene {len(tabla.filas)} opción; hacen falta dos opciones reales"
            " o la línea 'Única opción: <motivo>'"
        )

    indices: dict[str, int | None] = {}
    for nombre in columnas_opciones:
        indices[nombre] = columna(tabla, nombre)
        if indices[nombre] is None:
            informe.error(f"sección 5: a la tabla de opciones le falta la columna '{nombre}'")
    presentes = [i for i in indices.values() if i is not None]
    if presentes != sorted(presentes):
        informe.aviso(
            f"sección 5: las columnas de la tabla de opciones van en otro orden: {' | '.join(columnas_opciones)}"
        )

    letras = {c.letra for c in causas if c.letra}
    por_causa: dict[str, list[str]] = {}
    niveles: list[str] = []
    for fila in tabla.filas:
        opcion = leer_fila_opcion(fila, indices, letras, informe, contrato_act)
        comprobar_opcion(opcion, informe, contrato_act)
        if opcion.causa:
            por_causa.setdefault(opcion.causa, [])
            if opcion.decision:
                por_causa[opcion.causa].append(opcion.decision)
        if opcion.nivel:
            niveles.append(opcion.nivel)

    for causa in causas:
        if not causa.letra:
            continue
        if causa.letra not in por_causa:
            informe.error(f"sección 5: Causa {causa.letra} sin contramedida; ninguna opción la ataca")
        elif por_causa[causa.letra] and all(d == "descartada" for d in por_causa[causa.letra]):
            informe.aviso(f"sección 5: Causa {causa.letra} tiene todas sus opciones descartadas")
    if len([n for n in niveles if n != "curita"]) >= 2 and "poka-yoke" not in niveles:
        informe.aviso("sección 5: ninguna opción es de nivel poka-yoke; considera una que impida repetir el fallo")


def leer_fila_opcion(
    fila: list[str],
    indices: dict[str, int | None],
    letras: set[str],
    informe: Informe,
    contrato: dict | None = None,
) -> Opcion:
    """Lee una fila de la tabla de opciones; avisa o da error por cada valor que no se puede leer."""
    contrato_act = contrato or cargar_contrato(1)
    ventanas = tuple(contrato_act["ventanas"])
    niveles = tuple(contrato_act["niveles"])
    cuadrantes = tuple(contrato_act["cuadrantes"])
    decisiones = tuple(contrato_act["decisiones"])
    texto_opcion = celda(fila, indices["Opción"])
    m_id = re.match(r"O-\d+", texto_opcion)
    nombre = m_id.group(0) if m_id else f"'{texto_opcion}'"
    if not m_id:
        informe.aviso(f"sección 5: la opción '{texto_opcion}' no lleva identificador 'O-n'")
    causa = ""
    if indices["Causa"] is not None:
        texto_causa = celda(fila, indices["Causa"]).strip()
        sintoma, exacto = coincidir(texto_causa, ("síntoma",))
        if sintoma:
            causa = "síntoma"
            if not exacto:
                informe.aviso(f"sección 5: {nombre}: la causa se escribe 'síntoma'")
        elif re.fullmatch(r"[A-Z]", texto_causa) and (not letras or texto_causa in letras):
            causa = texto_causa
        else:
            informe.error(
                f"sección 5: {nombre}: la causa '{texto_causa}' no es un valor permitido"
                " (una letra de la sección 4b o 'síntoma')"
            )
    esfuerzo = alto_o_bajo(fila, indices["Esfuerzo"], nombre, "el esfuerzo", informe, contrato_act)
    if esfuerzo:
        m_ventana = re.search(r"\((.*)\)", celda(fila, indices["Esfuerzo"]))
        ventana = m_ventana.group(1).strip() if m_ventana else ""
        if coincidir(ventana, ventanas)[0] is None:
            informe.aviso(
                f"sección 5: {nombre}: la ventana de esfuerzo '{ventana}' no es una de"
                f" {', '.join(ventanas[:-1])} o {ventanas[-1]}"
            )
    return Opcion(
        nombre=nombre,
        causa=causa,
        nivel=valor_cerrado(fila, indices["Nivel"], niveles, nombre, "el nivel", informe),
        impacto=alto_o_bajo(fila, indices["Impacto"], nombre, "el impacto", informe, contrato_act),
        esfuerzo=esfuerzo,
        cuadrante=valor_cerrado(fila, indices["Cuadrante"], cuadrantes, nombre, "el cuadrante", informe),
        decision=valor_cerrado(fila, indices["Decisión"], decisiones, nombre, "la decisión", informe),
        prediccion=None if indices["Predicción"] is None else celda(fila, indices["Predicción"]),
    )


def comprobar_opcion(opcion: Opcion, informe: Informe, contrato: dict | None = None) -> None:
    """Reglas de pensamiento de una opción: cuadrante PICK, Eliminar elegida y predicción."""
    contrato_act = contrato or cargar_contrato(1)
    mapa_pick = {
        (entrada["impacto"], entrada["esfuerzo"]): entrada["cuadrante"]
        for entrada in contrato_act["pick"]
    }
    nombre = opcion.nombre
    calculado = mapa_pick.get((opcion.impacto, opcion.esfuerzo)) if opcion.impacto and opcion.esfuerzo else None
    if opcion.cuadrante and calculado and opcion.cuadrante != calculado:
        informe.error(
            f"sección 5: {nombre}: el cuadrante declarado es '{opcion.cuadrante}' y con impacto {opcion.impacto}"
            f" y esfuerzo {opcion.esfuerzo} corresponde '{calculado}'"
        )
    if opcion.decision != "elegida":
        return
    if (calculado or opcion.cuadrante) == "Eliminar":
        informe.error(f"sección 5: {nombre} está elegida y cae en 'Eliminar' (impacto bajo, esfuerzo alto)")
    if opcion.prediccion is None:
        return
    if not tiene_texto_real(opcion.prediccion):
        informe.error(f"sección 5: {nombre} está elegida y no tiene Predicción (qué medida cambia y cuánto)")
    elif not re.search(r"\d", opcion.prediccion):
        informe.aviso(f"sección 5: {nombre}: la Predicción no tiene cifra; di qué medida cambia y cuánto")


def valor_cerrado(
    fila: list[str], indice: int | None, permitidos: Sequence[str], opcion: str, que: str, informe: Informe
) -> str | None:
    if indice is None:
        return None
    texto = celda(fila, indice)
    canonico, exacto = coincidir(texto, permitidos)
    if canonico is None:
        informe.error(f"sección 5: {opcion}: {que} '{texto}' no es un valor permitido ({lista(permitidos)})")
        return None
    if not exacto:
        informe.aviso(f"sección 5: {opcion}: {que} se escribe '{canonico}'")
    return canonico


def alto_o_bajo(
    fila: list[str],
    indice: int | None,
    opcion: str,
    que: str,
    informe: Informe,
    contrato: dict | None = None,
) -> str | None:
    """Impacto y esfuerzo: 'alto' o 'bajo', con una aclaración opcional entre paréntesis."""
    if indice is None:
        return None
    contrato_act = contrato or cargar_contrato(1)
    permitidos_ab = tuple(
        dict.fromkeys(
            valor
            for entrada in contrato_act["pick"]
            for valor in (entrada["impacto"], entrada["esfuerzo"])
        )
    )
    texto = celda(fila, indice)
    primera = texto.split("(", 1)[0].strip()
    canonico, exacto = coincidir(primera, permitidos_ab)
    if canonico is None:
        informe.error(f"sección 5: {opcion}: {que} '{primera or texto}' no es un valor permitido (alto o bajo)")
        return None
    if not exacto:
        informe.aviso(f"sección 5: {opcion}: {que} se escribe '{canonico}'")
    return canonico


def sin_negar(patron: re.Pattern[str], lineas: list[str]) -> str | None:
    """Primera coincidencia de `patron` que ninguna negación previa alcanza."""
    for linea in lineas:
        for m in patron.finditer(linea):
            if not negado(linea, m.start()):
                return m.group(0)
    return None


def accion_destructiva(lineas: list[str]) -> str | None:
    """Primer verbo destructivo sin negar en una línea que no dice ya que es reversible."""
    for linea in lineas:
        if sin_negar(REVERSIBLE, [linea]) is None and (verbo := sin_negar(DESTRUCTIVO, [linea])):
            return verbo
    return None


def validar_seccion_6(seccion: Seccion, informe: Informe) -> bool:
    """Revisa la autorización; devuelve True si el plan registra o necesita una (entonces pide coach)."""
    autorizacion: str | None = None
    otras: list[str] = []
    for linea in seccion.cuerpo:
        m = CAMPO.match(linea)
        if m and normalizar(m.group(1)) == "autorizacion" and autorizacion is None:
            autorizacion = m.group(2).strip()
        else:
            otras.append(linea)
    declarada = sin_negar(IRREVERSIBLE, otras)
    destructiva = accion_destructiva(otras)
    if autorizacion is None or not tiene_texto_real(autorizacion):
        if declarada:
            informe.error(
                f"sección 6: el plan dice '{declarada}' y falta registrar la autorización"
                " ('- **Autorización:**' con quién y cuándo)"
            )
            return True
        informe.aviso(
            "sección 6: falta la línea '- **Autorización:**' (escribe 'no hace falta' si todo es"
            " reversible y está dentro del encargo)"
        )
        if destructiva:
            informe.aviso(f"sección 6: el plan nombra '{destructiva}'; confirma en el plan que es reversible")
        return False
    if normalizar(autorizacion).startswith(NO_HACE_FALTA):
        if declarada:
            informe.error(
                f"sección 6: la línea Autorización dice que no hace falta, pero el plan dice '{declarada}';"
                " registra quién autoriza y cuándo (AAAA-MM-DD)"
            )
            return True
        if destructiva:
            informe.aviso(
                f"sección 6: el plan nombra '{destructiva}' y la Autorización dice que no hace falta; confirma"
                " en el plan que es reversible (copia, papelera, borrado lógico) o registra quién autoriza y cuándo"
            )
        return False
    primera = normalizar(autorizacion.split(",", 1)[0])
    if not FECHA.search(autorizacion) or primera.startswith(("pendiente", "se pedira", "por pedir")):
        informe.error(
            "sección 6: la línea Autorización registra una autorización y no dice quién la dio y cuándo"
            " (AAAA-MM-DD); la autorización se registra antes de ejecutar"
        )
    return True


def validar_seccion_7(seccion: Seccion, informe: Informe, contrato: dict | None = None) -> None:
    contrato_act = contrato or cargar_contrato(1)
    rotulos_7 = tuple(contrato_act["rotulos_7"])
    rotulos: list[tuple[str, str]] = []
    for linea in seccion.cuerpo:
        m = CAMPO.match(linea)
        if m:
            rotulos.append((m.group(1).strip(), m.group(2).strip()))
    posiciones: list[int] = []
    valores: dict[str, str] = {}
    for canonico in rotulos_7:
        indice = next((i for i, (r, _) in enumerate(rotulos) if r == canonico), None)
        if indice is None:
            primera = normalizar(canonico).split(" ")[0]
            indice = next((i for i, (r, _) in enumerate(rotulos) if normalizar(r).split(" ")[0] == primera), None)
            if indice is None:
                informe.error(f"sección 7: falta la línea '- **{canonico}:**'")
                continue
            informe.aviso(f"sección 7: el rótulo '- **{rotulos[indice][0]}:**' debe ser '- **{canonico}:**'")
        posiciones.append(indice)
        valores[canonico] = rotulos[indice][1]
        if not tiene_texto_real(rotulos[indice][1]):
            informe.error(f"sección 7: la línea '{canonico}' está vacía")
    if posiciones != sorted(posiciones):
        informe.aviso(f"sección 7: las cuatro líneas van en otro orden: {', '.join(rotulos_7)}")
    revision = valores.get("Próxima revisión", "")
    if revision and "kaizen.md" not in revision.lower():
        ventana = re.search(r"\b(?:5|20)\s*h\b|\b1\s+semana\b", revision)
        if FECHA.search(revision) or not ventana:
            informe.aviso(
                "sección 7: Próxima revisión debería apuntar al compromiso de KAIZEN.md (su id y su ventana)"
                " o, sin tablero, a una ventana de 5 h, 20 h o 1 semana y quién; no a una fecha a mano"
            )
    estandar = valores.get("Estandarización", "")
    if estandar and not (
        "`" in estandar or re.search(r"[\w-]+\.(?:py|md|sh|json|toml|ya?ml|txt|js|ts|cfg|ini|html)\b", estandar)
    ):
        informe.aviso(
            "sección 7: Estandarización no nombra un artefacto que se cargue o se ejecute solo"
            " (prueba, regla, script, plantilla)"
        )


def validar_coach(campos: dict[str, tuple[str, str]], etapa: str, irreversible: bool, informe: Informe) -> None:
    campo = campos.get("coach / revisor")
    valor = campo[1] if campo else ""
    clave = normalizar(valor)
    propietario = normalizar(campos.get("propietario", ("", ""))[1])
    if campo is None or clave in {"", "sin coach", "ninguno"}:
        problema = "sin coach"
    elif clave == "pendiente":
        problema = "pendiente"
    elif propietario and clave == propietario:
        problema = "propietario"
    else:
        return
    if irreversible:
        informe.error(
            f"Cabecera: Coach / Revisor es '{valor or 'sin coach'}' y la sección 6 registra o necesita una"
            " autorización (acción irreversible o fuera del encargo); hace falta un coach distinto del"
            " propietario que la revise"
        )
    elif campo is None:
        informe.aviso("Cabecera: falta la línea '- **Coach / Revisor:**'; se toma como 'sin coach'")
    elif problema == "pendiente":
        if etapa != "comprender":
            informe.aviso(f"Cabecera: Coach / Revisor sigue 'pendiente' en la etapa {etapa}; solo vale en comprender")
    elif problema == "sin coach":
        informe.aviso("Cabecera: Coach / Revisor dice 'sin coach'; nadie más revisa el razonamiento")
    else:
        informe.aviso("Cabecera: Coach / Revisor es el mismo que el Propietario; nadie más revisa el razonamiento")


def validar_siguientes_pasos(doc: Documento, etapa_documento: str, informe: Informe) -> None:
    if etapa_documento == "cerrar":
        return
    bloque = next((s for s in doc.extras if normalizar(s.titulo) == "siguientes pasos"), None)
    if bloque is None:
        informe.error("falta el bloque '## Siguientes pasos' (qué, quién, cuándo); toda etapa anterior a cerrar lo lleva")
        return
    reales = [linea for linea in bloque.cuerpo if tiene_texto_real(linea) and not marcadores([linea])]
    if not reales:
        informe.error("el bloque '## Siguientes pasos' está vacío o sin completar; di qué, quién y cuándo")
    if any(s.linea > bloque.linea for s in doc.secciones.values()):
        informe.aviso("el bloque '## Siguientes pasos' va al final del documento, después de las secciones")


# ---------------------------------------------------------------- formato anterior (v1.1.1)

SECCIONES_V111 = [
    (r"^##\s+1\.\s+Contexto", 1),
    (r"^##\s+2\.\s+Estado Actual", 2),
    (r"^##\s+3\.\s+Meta", 3),
    (r"^##\s+4\.\s+An[aá]lisis de Causa Ra[ií]z", 4),
    (r"^##\s+5\.\s+Contramedidas", 5),
    (r"^##\s+6\.\s+Plan", 6),
    (r"^##\s+7\.\s+Verificaci[oó]n", 7),
]


def validar_formato_anterior(texto: str, doc: Documento, contrato: dict | None = None) -> Informe:
    """Reglas de la v1.1.1 (la culpa se mira solo en la línea de causa raíz) y lo que falta para el nuevo."""
    contrato_act = contrato or cargar_contrato(1)
    rotulos_7 = tuple(contrato_act["rotulos_7"])
    informe = Informe(etapa=None, origen_etapa="formato anterior", formato="anterior")
    lineas = doc.lineas
    no_vacias = sum(1 for linea in lineas if linea.strip())
    if no_vacias > MAX_LINEAS:
        informe.error(f"el A3 tiene {no_vacias} líneas no vacías y el máximo es {MAX_LINEAS} (una página); sintetiza")
    elif no_vacias < MIN_LINEAS_V111:
        informe.error(f"documento demasiado corto ({no_vacias} líneas no vacías); falta desarrollo real")
    for patron, numero in SECCIONES_V111:
        if not re.search(patron, texto, flags=re.IGNORECASE | re.MULTILINE):
            informe.error(f"Falta la sección obligatoria: '{numero}. {NOMBRES[numero]}'")
    for marcador in marcadores(lineas):
        informe.error(f"Contiene placeholder sin completar: '{marcador}'")
    if not re.search(r"\bverificad[oa]s?\b", texto, flags=re.IGNORECASE):
        informe.error("no se declara qué datos están 'Verificados' en el Gemba")
    if not re.search(r"\bsupuest[oa]s?\b|\bhip[oó]tesis\b", texto, flags=re.IGNORECASE):
        informe.error("no se contrasta lo verificado con 'Supuestos' o 'Hipótesis'")
    porques = [linea for linea in lineas if re.search(r"¿\s*por\s+qu[eé]", linea, re.IGNORECASE)]
    if len(porques) < 3:
        informe.error(f"Cadena de Porqués insuficiente: hay {len(porques)} preguntas 'Por qué' (mínimo 3)")
    if not re.search(r"poka[-\s]?yoke", texto, flags=re.IGNORECASE):
        informe.error("falta declarar el mecanismo 'Poka-Yoke' que impide repetir el error")
    if not re.search(r"curita|parche\s+superficial", texto, flags=re.IGNORECASE):
        informe.aviso("recomendación: explicita qué curita o parche superficial se descartó")
    de_raiz = [linea for linea in porques if re.search(r"causa\s+ra[ií]z", linea, re.IGNORECASE)]
    for linea in de_raiz or porques[-1:]:
        palabra = culpa_en(respuesta(linea))
        if palabra:
            informe.error(
                f"la causa raíz culpa a una persona o a un agente ('{palabra}'); sigue preguntando por qué"
                f" hasta llegar al proceso o al diseño; {AVISO_HEURISTICA_CULPA}"
            )

    campos = leer_campos(doc.cabecera)
    faltan = [r for r in ("Propietario", "Coach / Revisor", "Versión", "Etapa") if normalizar(r) not in campos]
    if faltan:
        informe.aviso("formato nuevo: faltan en la cabecera las líneas " + ", ".join(f"'- **{r}:**'" for r in faltan))
    if not re.search(r"^\s*[-*]\s*\*\*Brecha:\*\*", texto, re.MULTILINE):
        informe.aviso("formato nuevo: falta en la sección 2 la línea '- **Brecha:** de X (medido) a Y (meta) para <cuándo>'")
    if not re.search(r"^\s*\|\s*Rama\s*\|", texto, re.MULTILINE) and "Ishikawa: no aplica" not in texto:
        informe.aviso("formato nuevo: falta en la sección 4 el Ishikawa de seis ramas o la línea 'Ishikawa: no aplica'")
    if not re.search(r"por lo tanto\s*:", texto, re.IGNORECASE):
        informe.aviso(
            "formato nuevo: faltan en la sección 4 las causas '- **Causa A (Rama):**' con sus porqués y su línea 'Por lo tanto:'"
        )
    if not re.search(r"^\s*\|\s*Opci[oó]n\s*\|", texto, re.MULTILINE) and not re.search(r"[UÚ]nica opci[oó]n\s*:", texto):
        informe.aviso(
            "formato nuevo: falta en la sección 5 la tabla de opciones con cuadrante PICK y predicción,"
            " o la línea 'Única opción: <motivo>'"
        )
    faltan_7 = [r for r in rotulos_7 if f"**{r}:**" not in texto]
    if faltan_7:
        informe.aviso("formato nuevo: faltan en la sección 7 las líneas " + ", ".join(f"'- **{r}:**'" for r in faltan_7))
    informe.aviso("formato nuevo: con lo que falta y la línea Etapa en la cabecera se valida como A3 de la v1.2.0")
    return informe


# ---------------------------------------------------------------- línea de comandos


def armar_uso(etapas: Sequence[str]) -> str:
    return f"""\
Uso: validar-a3.py [--etapa ETAPA] [--raiz CARPETA] <archivo-a3.md>

Valida un A3 de TAS: los errores de pensamiento lo rechazan y los avisos de forma no.
Lee '- **Contrato:** 1|2' de la cabecera (1 si falta; con 2 exige las cuatro formas de fuente).

Opciones:
  --etapa ETAPA   valida contra lo que exige esa etapa: {lista(etapas)}.
                  Sin la opción, se lee la línea Etapa de la cabecera.
  --raiz CARPETA  carpeta raíz del proyecto para resolver rutas de fuentes (contrato 2);
                  sustituye a la búsqueda de .git hacia arriba.
  -h, --help      muestra esta ayuda.

Códigos de salida: 0 aprobado, 1 rechazado, 2 error de uso.
"""


class ErrorDeUso(Exception):
    """Argumentos o archivo que no permiten validar."""


class PedirAyuda(Exception):
    """Se pidió la ayuda con -h o --help."""


def leer_argumentos(
    argv: list[str], etapas: Sequence[str] | None = None
) -> tuple[str | None, str, Path | None]:
    etapas_validas = tuple(etapas) if etapas is not None else tuple(cargar_contrato()["etapas"])
    etapa: str | None = None
    raiz_valor: str | None = None
    archivos: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help"):
            raise PedirAyuda
        if arg == "--etapa":
            if i + 1 >= len(argv):
                raise ErrorDeUso("a la opción --etapa le falta el valor")
            etapa = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--etapa="):
            etapa = arg.split("=", 1)[1]
        elif arg == "--raiz":
            if i + 1 >= len(argv):
                raise ErrorDeUso("a la opción --raiz le falta el valor")
            raiz_valor = argv[i + 1]
            if not raiz_valor.strip():
                raise ErrorDeUso("a la opción --raiz le falta el valor")
            i += 2
            continue
        elif arg.startswith("--raiz="):
            raiz_valor = arg.split("=", 1)[1]
            if not raiz_valor.strip():
                raise ErrorDeUso("a la opción --raiz le falta el valor")
        elif arg.startswith("-") and arg != "-":
            raise ErrorDeUso(f"opción desconocida: {arg}")
        else:
            archivos.append(arg)
        i += 1
    if etapa is not None:
        etapa = etapa.strip().lower()
        if etapa not in etapas_validas:
            raise ErrorDeUso(f"etapa desconocida '{etapa}'; usa una de: {lista(etapas_validas)}")
    ruta_raiz: Path | None = None
    if raiz_valor is not None:
        ruta_raiz = Path(raiz_valor)
        if not ruta_raiz.is_dir():
            raise ErrorDeUso(f"la carpeta indicada en --raiz no existe o no es una carpeta: {raiz_valor}")
    if not archivos:
        raise ErrorDeUso("falta el archivo A3")
    if len(archivos) > 1:
        raise ErrorDeUso("indica un solo archivo A3")
    return etapa, archivos[0], ruta_raiz


def leer_archivo(ruta: Path) -> str:
    if not ruta.exists():
        raise ErrorDeUso(f"el archivo no existe: {ruta}")
    if not ruta.is_file():
        raise ErrorDeUso(f"no es un archivo A3 sino una carpeta u otro objeto: {ruta}")
    try:
        datos = ruta.read_bytes()
    except OSError as error:
        raise ErrorDeUso(f"no se pudo leer {ruta}: {error.strerror or error}") from None
    try:
        return unicodedata.normalize("NFC", datos.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise ErrorDeUso(f"el archivo no está en UTF-8: {ruta}") from None


def imprimir(informe: Informe, nombre: str) -> None:
    print(f"=== Validación A3: {nombre} ===")
    if informe.formato == "anterior":
        print("Formato anterior (v1.1.1) reconocido: se aplican sus reglas y se dice qué falta para el formato nuevo.")
    elif informe.formato == "sin_estructura":
        pass
    elif informe.etapa:
        print(f"Etapa: {informe.etapa} ({informe.origen_etapa})")
    else:
        print("Etapa: sin determinar; solo se revisan la cabecera y el límite de una página")
    if informe.errores:
        print(f"\nErrores de pensamiento ({len(informe.errores)}), rechazan el A3:")
        for error in informe.errores:
            print(f"[PARAR LÍNEA] {error}")
    if informe.avisos:
        print(f"\nAvisos de forma ({len(informe.avisos)}), no rechazan:")
        for aviso in informe.avisos:
            print(f"[AVISO] {aviso}")
    if informe.aprobado:
        print(f"\nResultado: APROBADO ({len(informe.avisos)} avisos de forma).")
    else:
        print(
            f"\nResultado: RECHAZADO ({len(informe.errores)} errores de pensamiento,"
            f" {len(informe.avisos)} avisos de forma)."
        )


def main(argv: list[str] | None = None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(flujo, "reconfigure", None)
        if reconfigurar is not None:
            reconfigurar(errors="replace")
    argumentos = sys.argv[1:] if argv is None else argv
    try:
        etapas_uso = tuple(cargar_contrato()["etapas"])
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    uso = armar_uso(etapas_uso)
    try:
        etapa, nombre, ruta_raiz = leer_argumentos(argumentos, etapas_uso)
        ruta = Path(nombre)
        texto = leer_archivo(ruta)
        informe = validar_a3(texto, etapa, ruta_a3=ruta, raiz=ruta_raiz)
    except PedirAyuda:
        print(uso, end="")
        return 0
    except ErrorDeUso as error:
        print(f"Error: {error}\n\n{uso}", end="", file=sys.stderr)
        return 2
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    imprimir(informe, ruta.name)
    return 0 if informe.aprobado else 1


if __name__ == "__main__":
    sys.exit(main())
