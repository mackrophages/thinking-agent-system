import { calcularIndicadores } from "./utilidadesDatos.mjs";

function claseCifraSegunEstado(estado) {
  if (estado === "exito") return "indicador-cifra indicador-cifra-exito";
  if (estado === "aviso") return "indicador-cifra indicador-cifra-aviso";
  if (estado === "error") return "indicador-cifra indicador-cifra-error";
  if (estado === "neutro") return "indicador-cifra indicador-cifra-neutra";
  return "indicador-cifra";
}

export function Indicadores({ datos }) {
  const ind = calcularIndicadores(datos);
  const estadoAbiertos =
    ind.numeroAbiertos === null
      ? "neutro"
      : ind.numeroAbiertos === 0
        ? "exito"
        : "aviso";

  return (
    <section id="indicadores" className="panel-seccion" aria-labelledby="titulo-indicadores">
      <div className="encabezado-seccion">
        <h2 id="titulo-indicadores" className="titulo-seccion">
          Indicadores
        </h2>
        <p className="subtitulo-seccion">Resumen de las 12 corridas de validación</p>
      </div>

      <div className="rejilla-indicadores">
        <article className="tarjeta-indicador" data-indicador="corridas-hechas">
          <span className="etiqueta-meta">Corridas hechas de 12</span>
          <span
            className={
              ind.corridasHechas === "sin datos"
                ? "indicador-cifra indicador-cifra-neutra"
                : "indicador-cifra"
            }
          >
            {ind.corridasHechas}
          </span>
          <p className="indicador-detalle">{ind.detalleCorridas}</p>
        </article>

        <article className="tarjeta-indicador" data-indicador="ct-mediano">
          <span className="etiqueta-meta">CT mediano</span>
          <span className={claseCifraSegunEstado(ind.estadoCt)}>{ind.ctMediano}</span>
          <p className="indicador-detalle">{ind.detalleCt}</p>
        </article>

        <article className="tarjeta-indicador" data-indicador="corridas-limpias">
          <span className="etiqueta-meta">Corridas con 0 problemas de calidad</span>
          <span
            className={
              ind.corridasLimpias === "sin datos"
                ? "indicador-cifra indicador-cifra-neutra"
                : "indicador-cifra indicador-cifra-exito"
            }
          >
            {ind.corridasLimpias}
          </span>
          <p className="indicador-detalle">{ind.detalleLimpias}</p>
        </article>

        <article className="tarjeta-indicador" data-indicador="problemas-abiertos">
          <span className="etiqueta-meta">Problemas abiertos (PDCA menor que 4)</span>
          <span className={claseCifraSegunEstado(estadoAbiertos)}>
            {ind.problemasAbiertos}
          </span>
          <p className="indicador-detalle">
            {ind.numeroAbiertos === null
              ? "sin datos"
              : ind.numeroAbiertos === 0
                ? "todas las contramedidas estandarizadas"
                : "contramedidas en Plan, Hacer o Verificar"}
          </p>
        </article>
      </div>
    </section>
  );
}
