import { useMemo } from "react";
import { barX, defineChart, text } from "@tanstack/charts";
import { scaleBand } from "@tanstack/charts/scales/band";
import { scaleLinear } from "@tanstack/charts/scales/linear";
import { Chart } from "@tanstack/react-charts";
import { TEMA_GRAFICAS } from "./Corridas.jsx";
import { etiquetaCategoriaEnPantalla } from "./utilidadesDatos.mjs";

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

function recortarRotuloEje(valor) {
  const cadena = String(valor ?? "");
  return cadena.length > 28 ? `${cadena.slice(0, 26)}...` : cadena;
}

export function Pareto({ datos }) {
  const objeto = datos && typeof datos === "object" ? datos : {};

  const resumen = useMemo(() => {
    const calidad = Array.isArray(objeto.qualityLog) ? objeto.qualityLog : [];
    const entrega = Array.isArray(objeto.deliveryLog) ? objeto.deliveryLog : [];
    const combinados = [...calidad, ...entrega];
    if (combinados.length === 0) {
      return { total: 0, filas: [] };
    }

    const conteos = new Map();
    for (const reg of combinados) {
      const etiqueta = etiquetaCategoriaEnPantalla(reg?.category);
      conteos.set(etiqueta, (conteos.get(etiqueta) || 0) + 1);
    }

    const ordenadas = [...conteos.entries()]
      .map(([etiqueta, cuenta]) => ({ etiqueta, cuenta }))
      .sort((a, b) => b.cuenta - a.cuenta || a.etiqueta.localeCompare(b.etiqueta, "es"));

    const maxCuenta = ordenadas[0]?.cuenta || 1;
    let acumulado = 0;
    const filas = ordenadas.map((item, idx) => {
      acumulado += item.cuenta;
      const pct = Math.round((item.cuenta / combinados.length) * 100);
      const pctAcumulado = Math.round((acumulado / combinados.length) * 100);
      return {
        ...item,
        orden: idx + 1,
        pct,
        pctAcumulado,
        colorBarra: item.cuenta === maxCuenta ? "#faff69" : "#f59e0b",
      };
    });

    return { total: combinados.length, filas };
  }, [objeto.qualityLog, objeto.deliveryLog]);

  const definicionPareto = useMemo(() => {
    if (resumen.filas.length === 0) return null;
    const dominioY = resumen.filas.map((f) => f.etiqueta);
    const maxCuenta = resumen.filas[0].cuenta;
    const topeX = Math.max(2, Math.ceil(maxCuenta * 1.25) + 1);
    const ticksX = calcularTicksEnteros(topeX);

    return defineChart({
      marks: [
        barX(resumen.filas, {
          id: "barras-pareto",
          x: "cuenta",
          y: "etiqueta",
          key: "etiqueta",
          fill: (d) => d.colorBarra,
          inset: 3,
          maxThickness: 30,
        }),
        text(resumen.filas, {
          id: "cuentas-pareto",
          x: "cuenta",
          y: "etiqueta",
          key: "etiqueta",
          text: (d) => String(d.cuenta),
          anchor: "start",
          dx: 8,
          fontSize: 11,
          fontWeight: 700,
          fill: "#ffffff",
        }),
      ],
      scales: {
        x: {
          scale: scaleLinear().domain([0, topeX]),
          grid: { stroke: "#2a2a2a", strokeDasharray: "2 3" },
          axis: {
            label: {
              text: "Cuenta de problemas",
              fontSize: 12,
              fontWeight: 600,
              fill: "#cccccc",
            },
            ticks: {
              values: ticksX,
              size: 0,
              padding: 6,
              format: (v) => `${Math.round(Number(v))}`,
            },
            tickLabels: { fontSize: 11 },
          },
        },
        y: {
          scale: scaleBand().domain(dominioY).padding(0.24),
          axis: {
            ticks: { size: 0, padding: 8, format: recortarRotuloEje },
            tickLabels: { fontSize: 11, thin: false },
          },
        },
      },
      margin: { top: 12, right: 26 },
      theme: TEMA_GRAFICAS,
    });
  }, [resumen.filas]);

  if (resumen.filas.length === 0) {
    return (
      <section id="pareto" className="panel-seccion" aria-labelledby="titulo-pareto">
        <div className="encabezado-seccion">
          <h2 id="titulo-pareto" className="titulo-seccion">
            Pareto de problemas por categoría
          </h2>
          <p className="subtitulo-seccion">Calidad y entrega agrupadas de mayor a menor</p>
        </div>
        <p className="estado-vacio">sin datos</p>
      </section>
    );
  }

  const alturaGrafica = Math.max(190, resumen.filas.length * 44 + 68);

  return (
    <section id="pareto" className="panel-seccion" aria-labelledby="titulo-pareto">
      <div className="encabezado-seccion">
        <h2 id="titulo-pareto" className="titulo-seccion">
          Pareto de problemas por categoría
        </h2>
        <p className="subtitulo-seccion">
          Calidad y entrega juntas ({resumen.total}{" "}
          {resumen.total === 1 ? "problema" : "problemas"} en {resumen.filas.length}{" "}
          {resumen.filas.length === 1 ? "categoría" : "categorías"})
        </p>
      </div>

      <div className="rejilla-pareto">
        <div className="caja-grafica" data-grafica="pareto-categorias">
          <div className="cabecera-grafica">
            <h3 className="titulo-subtabla">Frecuencia por categoría</h3>
            <span className="insignia insignia-oscura mono">
              Total: {resumen.total}
            </span>
          </div>

          <div className="lienzo-grafica">
            <Chart
              definition={definicionPareto}
              height={alturaGrafica}
              initialWidth={340}
              ariaLabel="Gráfica de Pareto de problemas por categoría ordenados de mayor a menor"
            />
          </div>
        </div>

        <div className="caja-grafica">
          <h3 className="titulo-subtabla">Desglose ordenado</h3>
          <ol className="lista-pareto">
            {resumen.filas.map((f) => (
              <li
                key={f.etiqueta}
                className="fila-pareto"
                data-pareto-categoria={f.etiqueta}
                data-pareto-cuenta={String(f.cuenta)}
              >
                <div className="fila-pareto-nombre">
                  <span className="pareto-orden mono">#{f.orden}</span>
                  <span className="pareto-etiqueta">{f.etiqueta}</span>
                </div>
                <div className="fila-pareto-cifras mono">
                  <span className="insignia insignia-oscura">
                    {f.cuenta} {f.cuenta === 1 ? "problema" : "problemas"}
                  </span>
                  <span className="pareto-acumulado">
                    {f.pct}% · acum. {f.pctAcumulado}%
                  </span>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
