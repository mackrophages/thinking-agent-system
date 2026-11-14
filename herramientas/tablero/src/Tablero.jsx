import { CalidadEntrega } from "./CalidadEntrega.jsx";
import { Corridas } from "./Corridas.jsx";
import { Encabezado } from "./Encabezado.jsx";
import { HerramientasLean } from "./HerramientasLean.jsx";
import { Indicadores } from "./Indicadores.jsx";
import { Pareto } from "./Pareto.jsx";

export function Tablero({ datos }) {
  return (
    <main className="tablero-pagina">
      <Encabezado datos={datos} />
      <Indicadores datos={datos} />
      <Corridas datos={datos} />
      <CalidadEntrega datos={datos} />
      <Pareto datos={datos} />
      <HerramientasLean />
    </main>
  );
}
