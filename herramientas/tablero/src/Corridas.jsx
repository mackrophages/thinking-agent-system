import { useMemo } from "react";
import { barY, defineChart, ruleY, text } from "@tanstack/charts";
import { scaleBand } from "@tanstack/charts/scales/band";
import { scaleLinear } from "@tanstack/charts/scales/linear";
import { Chart } from "@tanstack/react-charts";
import { formatearNumero, minutosSeguros, textoSeguro } from "./utilidadesDatos.mjs";

export const TEMA_GRAFICAS = {
  foreground: "#e6e6e6",
  muted: "#cccccc",
  grid: "#2a2a2a",
  background: "transparent",
  palette: ["#faff69", "#22c55e", "#f59e0b", "#ef4444", "#3b82f6"],
};

const ETIQUETA_ESTADO = {
  performed: "Hecha",
  active: "Activa",
  ready: "Lista",
};

function claseInsigniaEstado(estado) {
  if (estado === "performed") return "insignia insignia-exito insignia-tabla";
  if (estado === "active") return "insignia insignia-aviso insignia-tabla";
  return "insignia insignia-neutra insignia-tabla";
}

function numeroFinito(valor) {
  if (valor === null || valor === undefined || valor === "") {
    return null;
  }
  const n = Number(valor);
  return Number.isFinite(n) ? n : null;
}

function colorBarraCt(ct, estado, estandar, techo) {
  if (techo !== null && ct > techo) return "#ef4444";
  if (estandar !== null && ct > estandar) return "#f59e0b";
  if (estado === "active") return "#faff69";
  return "#22c55e";
}

function calcularTicksEnteros(tope) {
  const paso = tope <= 6 ? 1 : Math.ceil(tope / 5);
  const valores = [];
  for (let v = 0; v <= tope; v += paso) {
    valores.push(v);
  }
  if (valores[valores.length - 1] !== tope) {
    valores.push(tope);
  }
  return valores;
}

export function Corridas({ datos }) {
  const objeto = datos && typeof datos === "object" ? datos : {};
  const listaCruda = Array.isArray(objeto.builds) ? objeto.builds : null;
  const estandarNum = numeroFinito(objeto.standardMinutes);
  const techoNum = numeroFinito(objeto.taktTimeMinutes);
  const maxEscalaCt = numeroFinito(objeto.maxChartMinutes);
  const maxEscalaCalidad = numeroFinito(objeto.maxQualityScale);

  const filas = useMemo(() => {
    if (!listaCruda || listaCruda.length === 0) return [];
    return listaCruda.map((item, idx) => {
      const b = item && typeof item === "object" ? item : {};
      const idCrudo = b.id !== null && b.id !== undefined && b.id !== "" ? b.id : idx + 1;
      const etiquetaX = String(idCrudo);
      const estado =
        b.status === "performed" || b.status === "active" || b.status === "ready"
          ? b.status
          : "ready";
      const ctCrudo = numeroFinito(b.ctMinutes);
      const ct = ctCrudo !== null ? Math.max(0, ctCrudo) : null;
      const calidadCruda = numeroFinito(b.qualityIssues);
      const calidad = calidadCruda !== null ? Math.max(0, Math.round(calidadCruda)) : null;

      return {
        clave: `${etiquetaX}-${idx}`,
        numero: idCrudo,
        etiquetaX,
        estado,
        ct,
        tieneCt: ct !== null,
        colorCt: ct !== null ? colorBarraCt(ct, estado, estandarNum, techoNum) : "#5a5a5a",
        calidad,
        tieneCalidad: calidad !== null,
        colorCalidad: calidad !== null && calidad > 0 ? "#ef4444" : "#22c55e",
        esMejor: Boolean(b.isBest),
        nota: textoSeguro(b.note),
      };
    });
  }, [listaCruda, estandarNum, techoNum]);

  const definicionCt = useMemo(() => {
    if (filas.length === 0) return null;
    const dominioX = filas.map((f) => f.etiquetaX);
    const conCt = filas.filter((f) => f.tieneCt);
    const maxObservado = Math.max(
      1,
      ...conCt.map((f) => f.ct),
      estandarNum ?? 0,
      techoNum ?? 0,
      maxEscalaCt ?? 0,
    );
    const topeY = Math.max(2, Math.ceil(maxObservado * 1.18));

    const marcas = [
      barY(conCt, {
        id: "barras-ct",
        x: "etiquetaX",
        y: "ct",
        key: "clave",
        fill: (d) => d.colorCt,
        inset: 2,
        maxThickness: 42,
      }),
    ];

    if (estandarNum !== null) {
      marcas.push(
        ruleY([estandarNum], {
          id: "linea-estandar",
          stroke: "#22c55e",
          strokeWidth: 2,
          strokeDasharray: "6 4",
        }),
      );
    }

    if (techoNum !== null) {
      marcas.push(
        ruleY([techoNum], {
          id: "linea-techo-acordado",
          stroke: "#ef4444",
          strokeWidth: 2,
          strokeDasharray: "4 3",
        }),
      );
    }

    if (conCt.length > 0) {
      marcas.push(
        text(conCt, {
          id: "etiquetas-ct",
          x: "etiquetaX",
          y: "ct",
          key: "clave",
          text: (d) => formatearNumero(d.ct),
          dy: -7,
          fontSize: 11,
          fontWeight: 600,
          fill: "#e6e6e6",
        }),
      );
    }

    return defineChart({
      marks: marcas,
      scales: {
        x: {
          scale: scaleBand().domain(dominioX).padding(0.2),
          axis: {
            label: { text: "Corrida (#)", fontSize: 12, fontWeight: 600, fill: "#cccccc" },
            ticks: { size: 0, padding: 6 },
            tickLabels: { fontSize: 11, thin: false },
          },
        },
        y: {
          scale: scaleLinear().domain([0, topeY]),
          grid: { stroke: "#2a2a2a", strokeDasharray: "2 3" },
          axis: {
            label: { text: "CT (min)", fontSize: 12, fontWeight: 600, fill: "#cccccc" },
            ticks: { count: 5, size: 0, padding: 6, format: (v) => `${Number(v)}` },
            tickLabels: { fontSize: 11 },
          },
        },
      },
      margin: { top: 20, right: 14 },
      theme: TEMA_GRAFICAS,
    });
  }, [filas, estandarNum, techoNum, maxEscalaCt]);

  const definicionCalidad = useMemo(() => {
    if (filas.length === 0) return null;
    const dominioX = filas.map((f) => f.etiquetaX);
    const conCalidad = filas.filter((f) => f.tieneCalidad);
    const maxCalidad = Math.max(
      2,
      ...conCalidad.map((f) => f.calidad),
      maxEscalaCalidad ?? 0,
    );
    const topeY = Math.ceil(maxCalidad + 1);
    const ticksY = calcularTicksEnteros(topeY);

    return defineChart({
      marks: [
        barY(conCalidad, {
          id: "barras-calidad",
          x: "etiquetaX",
          y: "calidad",
          key: "clave",
          fill: (d) => d.colorCalidad,
          inset: 2,
          maxThickness: 42,
        }),
        text(conCalidad, {
          id: "etiquetas-calidad",
          x: "etiquetaX",
          y: "calidad",
          key: "clave",
          text: (d) => String(d.calidad),
          dy: -7,
          fontSize: 11,
          fontWeight: 600,
          fill: "#e6e6e6",
        }),
      ],
      scales: {
        x: {
          scale: scaleBand().domain(dominioX).padding(0.2),
          axis: {
            label: { text: "Corrida (#)", fontSize: 12, fontWeight: 600, fill: "#cccccc" },
            ticks: { size: 0, padding: 6 },
            tickLabels: { fontSize: 11, thin: false },
          },
        },
        y: {
          scale: scaleLinear().domain([0, topeY]),
          grid: { stroke: "#2a2a2a", strokeDasharray: "2 3" },
          axis: {
            label: { text: "Problemas", fontSize: 12, fontWeight: 600, fill: "#cccccc" },
            ticks: { values: ticksY, size: 0, padding: 6, format: (v) => `${Math.round(Number(v))}` },
            tickLabels: { fontSize: 11 },
          },
        },
      },
      margin: { top: 20, right: 14 },
      theme: TEMA_GRAFICAS,
    });
  }, [filas, maxEscalaCalidad]);

  if (filas.length === 0) {
    return (
      <section id="corridas" className="panel-seccion" aria-labelledby="titulo-corridas">
        <div className="encabezado-seccion">
          <h2 id="titulo-corridas" className="titulo-seccion">
            Corridas
          </h2>
          <p className="subtitulo-seccion">Tiempo de ciclo, calidad y estado por corrida</p>
        </div>
        <p className="estado-vacio">sin datos</p>
      </section>
    );
  }

  return (
    <section id="corridas" className="panel-seccion" aria-labelledby="titulo-corridas">
      <div className="encabezado-seccion">
        <h2 id="titulo-corridas" className="titulo-seccion">
          Corridas
        </h2>
        <p className="subtitulo-seccion">
          Tiempo de ciclo (CT), problemas de calidad y estado de las {filas.length} corridas
        </p>
      </div>

      <div className="rejilla-graficas-corridas">
        <div className="caja-grafica" data-grafica="ct-corridas">
          <div className="cabecera-grafica">
            <h3 className="titulo-subtabla">Tiempo de ciclo (CT) por corrida</h3>
            <div className="leyenda-referencias" aria-label="Referencias de tiempo de ciclo">
              <span className="item-leyenda">
                <span className="trazo-leyenda trazo-estandar" aria-hidden="true" />
                <span>Estándar:</span>
                <strong className="mono">{minutosSeguros(objeto.standardMinutes)}</strong>
              </span>
              <span className="item-leyenda">
                <span className="trazo-leyenda trazo-techo" aria-hidden="true" />
                <span>Techo acordado:</span>
                <strong className="mono">{minutosSeguros(objeto.taktTimeMinutes)}</strong>
              </span>
            </div>
          </div>

          <div className="lienzo-grafica">
            <Chart
              definition={definicionCt}
              height={260}
              initialWidth={340}
              ariaLabel="Gráfica de tiempo de ciclo por corrida con líneas de estándar y techo acordado"
            />
          </div>
        </div>

        <div className="caja-grafica" data-grafica="calidad-corridas">
          <div className="cabecera-grafica">
            <h3 className="titulo-subtabla">Problemas de calidad por corrida</h3>
            <span className="insignia insignia-oscura mono">Meta: 0 problemas</span>
          </div>

          <div className="lienzo-grafica">
            <Chart
              definition={definicionCalidad}
              height={210}
              initialWidth={340}
              ariaLabel="Gráfica de problemas de calidad detectados por corrida"
            />
          </div>
        </div>
      </div>

      <div className="bloque-estados-corridas">
        <h3 className="titulo-subtabla">Estado de cada corrida</h3>
        <div className="rejilla-estados-corridas">
          {filas.map((f) => (
            <article
              key={f.clave}
              className={
                f.esMejor
                  ? "tarjeta-corrida tarjeta-corrida-mejor"
                  : f.estado === "active"
                    ? "tarjeta-corrida tarjeta-corrida-activa"
                    : "tarjeta-corrida"
              }
              data-corrida-id={String(f.numero)}
              data-estado={f.estado}
              data-mejor={f.esMejor ? "true" : "false"}
            >
              <div className="corrida-cabecera">
                <span className="corrida-numero mono">#{f.numero}</span>
                <div className="corrida-insignias">
                  {f.esMejor && (
                    <span className="insignia insignia-amarilla">Mejor corrida</span>
                  )}
                  <span className={claseInsigniaEstado(f.estado)}>
                    {ETIQUETA_ESTADO[f.estado] || f.estado}
                  </span>
                </div>
              </div>

              <div className="corrida-metricas mono">
                <span>
                  CT: <strong>{f.tieneCt ? `${formatearNumero(f.ct)} min` : "sin datos"}</strong>
                </span>
                <span>
                  Calidad:{" "}
                  <strong>
                    {f.tieneCalidad
                      ? `${f.calidad} ${f.calidad === 1 ? "problema" : "problemas"}`
                      : "sin datos"}
                  </strong>
                </span>
              </div>

              <p className="corrida-nota">{f.nota}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
