#!/usr/bin/env python3
"""Lectura compartida de la Brecha, el estallido kaizen y las cifras del A3 (TAS).

Tanto el validador como el dibujante cargan este módulo por ruta relativa para
aplicar exactamente las mismas reglas al leer el indicador y los valores de la
Brecha, las marcas de estallido en el mapa de estado y las cifras de cuadros o
barras.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

CUERPO_BRECHA = re.compile(
    r"de\s+.+?\(medido\)\s+a\s+.+?\(meta\)\s+para\s+\S",
    re.IGNORECASE,
)
CUERPO_BRECHA_PARTES = re.compile(
    r"^de\s+(?P<actual>.+?)\s*\(medido\)\s+a\s+(?P<meta>.+?)\s*\(meta\)\s+para\s+(?P<cuando>\S.*?)\s*$",
    re.IGNORECASE,
)
CUERPO_BRECHA_RESPALDO = re.compile(
    r"^de\s+(?P<actual>.+?)(?:\s*\(medido\))?\s+a\s+(?P<meta>.+?)(?:\s*\(meta\))?(?:\s+para\s+(?P<cuando>\S.*?))?\s*$",
    re.IGNORECASE,
)
MARCADOR_ANGULAR_COMPLETO = re.compile(r"(?<!\w)<((?:[^<>\n]|(?<=-)>)+)>")
ESTALLIDO_CANONICO = re.compile(r"^\[([A-Z])\](?!\()\s*(.*)$", re.DOTALL)
MARCA_CORCHETE_INICIO = re.compile(
    r"^(?:[*_~]+)?\[[*_~]*([^\s\]`*_~]{1,3})[*_~]*\](?!\()(?:\s*[*_~]+)*"
)
ESTALLIDO_EN_CELDA = re.compile(r"\[([A-Z])\]")
CUADROS_NDM = re.compile(r"^\s*(\d+)\s+de\s+(\d+)\b", re.IGNORECASE)
MAGNITUD_COMPLETA = re.compile(
    r"^\s*(?P<cifra>[+-]?\d[\d.,]*)(?P<esp>\s*)(?P<unidad>%|°[CFK]?|[^\W\d_]+[²³]?(?:[·/][^\W\d_]+[²³]?)?)\s*$",
    re.UNICODE,
)
PALABRAS_NO_UNIDAD = frozenset({"de", "a", "o", "y", "por", "en", "con", "sin", "para"})


@dataclass(frozen=True)
class BrechaLeida:
    """Resultado de desarmar la línea Brecha de la sección 2."""

    indicador: str
    cuerpo: str
    cuerpo_canonico: bool
    actual: str | None
    meta: str | None
    cuando: str | None


@dataclass(frozen=True)
class EstallidoLeido:
    """Resultado de inspeccionar el inicio de la celda Problema de un paso."""

    estado: str
    letra: str | None
    marca: str | None
    texto_limpio: str


@dataclass(frozen=True)
class CuadrosBrecha:
    """Datos listos para pintar una brecha de proporción 'N de M'."""

    n_actual: int
    n_meta: int
    total: int
    brecha_n: int
    rotulo_actual: str
    rotulo_meta: str


@dataclass(frozen=True)
class BarrasBrecha:
    """Datos listos para pintar una brecha de magnitud con misma unidad."""

    valor_actual: Decimal
    valor_meta: Decimal
    rotulo_actual: str
    rotulo_meta: str
    rotulo_brecha: str


def _es_marcador_angular_espaciado(interior: str) -> bool:
    return bool(
        interior
        and not interior[0].isspace()
        and not interior[-1].isspace()
        and any(c.isspace() for c in interior)
    )


def tiene_texto_util(valor: str) -> bool:
    """True si tras quitar marcadores angulares con espacio queda alguna letra o cifra."""
    limpio = MARCADOR_ANGULAR_COMPLETO.sub(
        lambda m: "" if _es_marcador_angular_espaciado(m.group(1)) else m.group(0),
        valor,
    )
    return bool(re.search(r"\w", limpio))


def extraer_partes_cuerpo_brecha(
    cuerpo: str,
) -> tuple[str, str, str | None, bool] | None:
    """Extrae (actual, meta, cuando, es_canonico) desde 'de <actual> ... a <meta> ...'."""
    m_can = CUERPO_BRECHA_PARTES.match(cuerpo.strip())
    if m_can is not None:
        actual = m_can.group("actual").strip()
        meta = m_can.group("meta").strip()
        cuando = m_can.group("cuando").strip()
        if tiene_texto_util(actual) and tiene_texto_util(meta):
            return (actual, meta, cuando, True)
        return None
    m_res = CUERPO_BRECHA_RESPALDO.match(cuerpo.strip())
    if m_res is None:
        return None
    actual = m_res.group("actual").strip()
    meta = m_res.group("meta").strip()
    cuando_raw = m_res.group("cuando")
    cuando = cuando_raw.strip() if cuando_raw else None
    if not tiene_texto_util(actual) or not tiene_texto_util(meta):
        return None
    return (actual, meta, cuando, False)


def leer_brecha(valor: str) -> BrechaLeida:
    """Lee indicador, cuerpo y valores (actual, meta, cuándo) por el ancla ': ' antes del cuerpo."""
    texto = valor.strip()
    enmascarado = re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), texto)
    pos_medido = enmascarado.lower().find("(medido)")
    limite_ancla = pos_medido if pos_medido != -1 else len(enmascarado)

    # 1. Buscar el ': ' que precede a 'de <actual> (medido) a <meta> (meta) para <cuándo>'
    anclas_espacio = [
        m.start() for m in re.finditer(r":\s+", enmascarado[:limite_ancla])
    ]
    anclas_sin_espacio = [
        m.start() for m in re.finditer(r":(?=de\s)", enmascarado[:limite_ancla], re.IGNORECASE)
    ]
    for idx in reversed(anclas_espacio or anclas_sin_espacio):
        ind = texto[:idx].strip()
        resto = texto[idx + 1 :].strip()
        if CUERPO_BRECHA.match(resto):
            ind_ef = ind if tiene_texto_util(ind) else ""
            partes = extraer_partes_cuerpo_brecha(resto)
            if partes is not None:
                return BrechaLeida(ind_ef, resto, True, partes[0], partes[1], partes[2])
            return BrechaLeida(ind_ef, resto, True, None, None, None)

    # 2. Cuerpo canónico sin indicador delante (contratos 1 y 2, o falta de indicador en contrato 3)
    if CUERPO_BRECHA.match(texto):
        partes = extraer_partes_cuerpo_brecha(texto)
        if partes is not None:
            return BrechaLeida("", texto, True, partes[0], partes[1], partes[2])
        return BrechaLeida("", texto, True, None, None, None)

    # 3. Cuerpo sin '(medido)'/'(meta)' completos pero con ancla ': ' delante de 'de ... a ...'
    for m in reversed(list(re.finditer(r":\s+", enmascarado))):
        idx = m.start()
        ind = texto[:idx].strip()
        resto = texto[idx + 1 :].strip()
        partes_res = extraer_partes_cuerpo_brecha(resto)
        if partes_res is not None:
            ind_ef = ind if tiene_texto_util(ind) else ""
            return BrechaLeida(ind_ef, resto, False, partes_res[0], partes_res[1], partes_res[2])

    m_primero = re.search(r":\s+", enmascarado)
    if m_primero is not None:
        idx = m_primero.start()
        ind = texto[:idx].strip()
        resto = texto[idx + 1 :].strip()
        if tiene_texto_util(ind) and not re.match(r"de\s+\d", ind, re.IGNORECASE):
            return BrechaLeida(ind, resto, False, None, None, None)

    partes_sin = extraer_partes_cuerpo_brecha(texto)
    if partes_sin is not None:
        return BrechaLeida("", texto, False, partes_sin[0], partes_sin[1], partes_sin[2])
    return BrechaLeida("", texto, False, None, None, None)


def leer_estallido(problema: str) -> EstallidoLeido:
    """Lee la marca de estallido al inicio de una celda Problema."""
    limpio = problema.strip()
    m_can = ESTALLIDO_CANONICO.match(limpio)
    if m_can is not None:
        letra = m_can.group(1)
        resto = m_can.group(2).strip()
        return EstallidoLeido(
            estado="canonico",
            letra=letra,
            marca=f"[{letra}]",
            texto_limpio=resto or letra,
        )
    m_inv = MARCA_CORCHETE_INICIO.match(limpio)
    if m_inv is not None:
        return EstallidoLeido(
            estado="invalido",
            letra=None,
            marca=m_inv.group(0).strip(),
            texto_limpio=limpio,
        )
    return EstallidoLeido(
        estado="ninguno",
        letra=None,
        marca=None,
        texto_limpio=limpio,
    )


def estallidos_en_texto(texto_sin_codigo: str) -> list[str]:
    """Devuelve las letras de estallidos canónicos presentes en un texto."""
    return ESTALLIDO_EN_CELDA.findall(texto_sin_codigo)


ATOMO_VALOR_BRECHA = re.compile(
    r"\d+(?:[.,:]\d+)*|[%°/]|[^\W\d_]+",
    re.UNICODE,
)
CIFRA_COMA_MILES = re.compile(r"^[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?$")


def _minusculas_sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).lower()


def normalizar_fragmento_brecha(texto: str) -> str:
    """Convierte a minúsculas sin tildes ni signos, con espacios simples."""
    return re.sub(r"[\W_]+", " ", _minusculas_sin_tildes(texto), flags=re.UNICODE).strip()


INICIO_CIFRA = re.compile(r"^\s*(?:[*_~]+\s*)*[+-]?\d")
SEPARADOR_CLAUSULA_X = re.compile(r":\s+|;\s+|\s+-\s+")


def _empieza_con_cifra(texto: str) -> bool:
    return bool(INICIO_CIFRA.match(texto))


def _contiene_cifra(texto: str) -> bool:
    """True si el texto trae una cifra, aunque lleve un signo o una palabra delante ($1,250, <200 ms)."""
    return bool(re.search(r"\d", texto))


def _es_negativo(texto: str) -> bool:
    return bool(re.match(r"^\s*(?:[*_~`]+\s*)*-(?=\d)", texto))


def _normalizar_atomo_brecha(tok: str) -> str:
    if CIFRA_COMA_MILES.fullmatch(tok):
        return tok.replace(",", "")
    return tok


def _atomos_valor_brecha(texto: str) -> list[str]:
    limpio = re.sub(r"[*_~`]+", "", _minusculas_sin_tildes(texto))
    return [_normalizar_atomo_brecha(m.group(0)) for m in ATOMO_VALOR_BRECHA.finditer(limpio)]


def coincide_valor_texto_brecha(
    en_titulo: str, en_brecha: str, etiqueta: str = ""
) -> bool:
    """Compara un valor del título contra la Brecha por su texto, sin leer barras."""
    limpio = en_titulo.strip()
    if etiqueta:
        limpio = re.sub(rf"\s*\({etiqueta}\)\s*$", "", limpio, flags=re.IGNORECASE)
    if _es_negativo(limpio) != _es_negativo(en_brecha):
        return False
    atomos_br = _atomos_valor_brecha(en_brecha)
    if not atomos_br:
        return False
    return _atomos_valor_brecha(limpio) == atomos_br


def coincide_meta_en_titulo(y_titulo: str, meta_brecha: str) -> bool:
    """True si Y empieza con la meta y termina el título o sigue un separador o palabra."""
    limpio_y = y_titulo.strip()
    if _es_negativo(limpio_y) != _es_negativo(meta_brecha):
        return False
    atomos_meta = _atomos_valor_brecha(meta_brecha)
    if not atomos_meta:
        return False
    limpio_norm = re.sub(r"[*_~`]+", "", _minusculas_sin_tildes(limpio_y))
    hallados = list(ATOMO_VALOR_BRECHA.finditer(limpio_norm))
    if len(hallados) < len(atomos_meta):
        return False
    k = len(atomos_meta)
    prefijo = [_normalizar_atomo_brecha(m.group(0)) for m in hallados[:k]]
    if prefijo != atomos_meta:
        return False
    cola = limpio_norm[hallados[k - 1].end() :]
    cola = re.sub(r"^\s*\(meta\)", "", cola, flags=re.IGNORECASE)
    if not re.sub(r"[\s.!?;:]+$", "", cola):
        return True
    if re.match(r"^\s*(?:[,;:\-\u2013\u2014()\[\]|·]|/\s)", cola):
        return True
    if re.match(r"^\s+[^\W\d_]", cola, flags=re.UNICODE):
        return True
    return False


def _pares_de_x_a_y_en_tramo(tramo: str) -> list[tuple[str, str]]:
    limpio = re.sub(r"[\s.!?;:,]+$", "", tramo.strip())
    if not limpio:
        return []
    pares: list[tuple[str, str]] = []
    for m_de in re.finditer(r"\bde\s+", limpio, flags=re.IGNORECASE):
        if re.search(r"\b\d+\s+$", limpio[: m_de.start()]):
            continue
        resto = limpio[m_de.end() :].strip()
        if not _contiene_cifra(resto):
            continue
        for m_a in re.finditer(r"\s+a\s+", resto, flags=re.IGNORECASE):
            x_txt = resto[: m_a.start()].strip()
            y_txt = resto[m_a.end() :].strip()
            if not x_txt or not y_txt:
                continue
            if SEPARADOR_CLAUSULA_X.search(x_txt):
                break
            if _contiene_cifra(x_txt) and _contiene_cifra(y_txt):
                pares.append((x_txt, y_txt))
    return pares


def extraer_de_x_a_y_titulo(
    titulo_texto: str, indicador_brecha: str
) -> list[tuple[str, str]]:
    """Extrae los candidatos (X, Y) si el título trae 'de <X> a <Y>' fuera del indicador."""
    tokens_tit = [
        (normalizar_fragmento_brecha(m.group(0)), m.start(), m.end())
        for m in re.finditer(r"[^\W_]+", titulo_texto, flags=re.UNICODE)
    ]
    tokens_tit = [t for t in tokens_tit if t[0]]
    tokens_ind = normalizar_fragmento_brecha(indicador_brecha).split()
    if not tokens_tit or not tokens_ind or len(tokens_ind) > len(tokens_tit):
        return _pares_de_x_a_y_en_tramo(titulo_texto)

    n_ind = len(tokens_ind)
    for idx in range(len(tokens_tit) - n_ind + 1):
        if [t[0] for t in tokens_tit[idx : idx + n_ind]] == tokens_ind:
            ini_char = tokens_tit[idx][1]
            fin_char = tokens_tit[idx + n_ind - 1][2]
            despues = titulo_texto[fin_char:]
            pares_desp = _pares_de_x_a_y_en_tramo(despues)
            if pares_desp:
                return pares_desp
            antes = re.sub(
                r"(?:\s+(?:en|para|sobre|por|del|de)|[\s,:;\-])+$",
                "",
                titulo_texto[:ini_char],
                flags=re.IGNORECASE,
            )
            pares_ant = _pares_de_x_a_y_en_tramo(antes)
            if pares_ant:
                return pares_ant
    return []


def leer_cuadros_brecha(actual_txt: str, meta_txt: str) -> CuadrosBrecha | None:
    """Interpreta proporciones 'N de M' compatibles para pintarse como cuadros."""
    m_act = CUADROS_NDM.match(actual_txt)
    m_met = CUADROS_NDM.match(meta_txt)
    if m_act is None or m_met is None:
        return None
    n_act, m_den_act = int(m_act.group(1)), int(m_act.group(2))
    n_met, m_den_met = int(m_met.group(1)), int(m_met.group(2))
    if m_den_act != m_den_met or not (1 <= m_den_act <= 20):
        return None
    if not (0 <= n_act <= m_den_act and 0 <= n_met <= m_den_met):
        return None
    return CuadrosBrecha(
        n_actual=n_act,
        n_meta=n_met,
        total=m_den_act,
        brecha_n=abs(n_met - n_act),
        rotulo_actual=actual_txt.strip(),
        rotulo_meta=meta_txt.strip(),
    )


CIFRA_SALVADOR = re.compile(
    r"^(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)(?:\.\d+)?$"
)


def _analizar_cifra_humana(cifra_cruda: str) -> Decimal | None:
    """Lee una cifra no negativa con punto decimal y coma de miles en grupos de 3."""
    if cifra_cruda.startswith("-"):
        return None
    limpia = cifra_cruda[1:] if cifra_cruda.startswith("+") else cifra_cruda
    if not CIFRA_SALVADOR.fullmatch(limpia):
        return None
    return Decimal(limpia.replace(",", ""))


def _agrupar_miles(entera: str, sep: str) -> str:
    grupos: list[str] = []
    i = len(entera)
    while i > 0:
        grupos.append(entera[max(0, i - 3) : i])
        i -= 3
    return sep.join(reversed(grupos))


def _formatear_diferencia_humana(diff: Decimal) -> str:
    texto_dec = format(diff, "f")
    if "." in texto_dec:
        texto_dec = texto_dec.rstrip("0").rstrip(".")
    entera, _, decimal = texto_dec.partition(".")
    if len(entera) > 3:
        entera = _agrupar_miles(entera, ",")
    if decimal:
        return f"{entera}.{decimal}"
    return entera


def leer_barras_brecha(actual_txt: str, meta_txt: str) -> BarrasBrecha | None:
    """Interpreta dos magnitudes humanas de una sola cifra con la misma unidad."""
    m_act = MAGNITUD_COMPLETA.match(actual_txt)
    m_met = MAGNITUD_COMPLETA.match(meta_txt)
    if m_act is None or m_met is None:
        return None
    u_act = m_act.group("unidad")
    u_met = m_met.group("unidad")
    if u_act.lower() != u_met.lower() or u_act.lower() in PALABRAS_NO_UNIDAD:
        return None
    v_act = _analizar_cifra_humana(m_act.group("cifra"))
    v_met = _analizar_cifra_humana(m_met.group("cifra"))
    if v_act is None or v_met is None:
        return None
    if v_act < 0 or v_met < 0 or max(v_act, v_met) <= 0:
        return None
    diff_txt = _formatear_diferencia_humana(abs(v_act - v_met))
    sep_u = " " if (m_act.group("esp") or m_met.group("esp")) else ""
    unidad_brecha = u_act if u_act == u_met else u_act.lower()
    return BarrasBrecha(
        valor_actual=v_act,
        valor_meta=v_met,
        rotulo_actual=actual_txt.strip(),
        rotulo_meta=meta_txt.strip(),
        rotulo_brecha=f"{diff_txt}{sep_u}{unidad_brecha}",
    )
