const ETIQUETAS_CATEGORIA_ENTREGA = {
  "CT > TT": "CT sobre el techo acordado",
  "CT > Standard": "CT sobre el estándar",
};

export function textoSeguro(valor) {
  if (valor === null || valor === undefined) {
    return "sin datos";
  }
  const limpio = String(valor).trim();
  return limpio.length > 0 ? limpio : "sin datos";
}

export function formatearNumero(valor) {
  const num = Number(valor);
  if (!Number.isFinite(num)) {
    return "sin datos";
  }
  if (Number.isInteger(num)) {
    return num.toFixed(1);
  }
  return String(Math.round(num * 100) / 100);
}

export function minutosSeguros(valor) {
  if (valor === null || valor === undefined || valor === "") {
    return "sin datos";
  }
  const num = Number(valor);
  if (!Number.isFinite(num)) {
    return "sin datos";
  }
  return `${formatearNumero(num)} min`;
}

export function etiquetaCategoriaEnPantalla(categoria) {
  const base = textoSeguro(categoria);
  return ETIQUETAS_CATEGORIA_ENTREGA[base] || base;
}

export function calcularIndicadores(datos) {
  const objeto = datos && typeof datos === "object" ? datos : {};
  const corridas = Array.isArray(objeto.builds) ? objeto.builds : null;
  const tieneCalidad = Array.isArray(objeto.qualityLog);
  const tieneEntrega = Array.isArray(objeto.deliveryLog);

  let corridasHechas = "sin datos";
  let detalleCorridas = "sin datos";
  let ctMediano = "sin datos";
  let valorCtMediano = null;
  let corridasLimpias = "sin datos";
  let detalleLimpias = "sin datos";

  if (corridas && corridas.length > 0) {
    const hechas = corridas.filter((b) => b && b.status === "performed");
    const activas = corridas.filter((b) => b && b.status === "active");
    const listas = corridas.filter((b) => b && b.status === "ready");
    corridasHechas = `${hechas.length} / 12`;
    detalleCorridas = `${activas.length} activa · ${listas.length} listas`;

    const cts = hechas
      .map((b) => b.ctMinutes)
      .filter((v) => v !== null && v !== undefined && v !== "" && Number.isFinite(Number(v)))
      .map((v) => Number(v))
      .sort((a, b) => a - b);

    if (cts.length > 0) {
      const mitad = Math.floor(cts.length / 2);
      const mediana = cts.length % 2 === 1 ? cts[mitad] : (cts[mitad - 1] + cts[mitad]) / 2;
      valorCtMediano = mediana;
      ctMediano = `${formatearNumero(mediana)} min`;
    }

    const limpias = hechas.filter(
      (b) =>
        b.qualityIssues !== null &&
        b.qualityIssues !== undefined &&
        b.qualityIssues !== "" &&
        Number(b.qualityIssues) === 0,
    ).length;
    corridasLimpias = String(limpias);
    detalleLimpias =
      hechas.length > 0 ? `de ${hechas.length} corridas hechas` : "sin corridas cerradas";
  }

  let problemasAbiertos = "sin datos";
  let numeroAbiertos = null;
  if (tieneCalidad || tieneEntrega) {
    const registros = [
      ...(tieneCalidad ? objeto.qualityLog : []),
      ...(tieneEntrega ? objeto.deliveryLog : []),
    ];
    const abiertos = registros.filter((item) => item && (Number(item.pdca) || 0) < 4).length;
    numeroAbiertos = abiertos;
    problemasAbiertos = String(abiertos);
  }

  const estandar = Number(objeto.standardMinutes);
  const techo = Number(objeto.taktTimeMinutes);
  let estadoCt = "neutro";
  let detalleCt = "sin corridas cerradas";
  if (valorCtMediano !== null) {
    if (Number.isFinite(techo) && valorCtMediano > techo) {
      estadoCt = "error";
      detalleCt = "sobre el techo acordado";
    } else if (Number.isFinite(estandar) && valorCtMediano > estandar) {
      estadoCt = "aviso";
      detalleCt = "sobre el estándar";
    } else {
      estadoCt = "exito";
      detalleCt = "dentro del estándar";
    }
  }

  return {
    corridasHechas,
    detalleCorridas,
    ctMediano,
    estadoCt,
    detalleCt,
    corridasLimpias,
    detalleLimpias,
    problemasAbiertos,
    numeroAbiertos,
  };
}
