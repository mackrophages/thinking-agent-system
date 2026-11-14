import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { crearColumnas } from "./columnasTabla.jsx";
import { etiquetaCategoriaEnPantalla, textoSeguro } from "./utilidadesDatos.mjs";

const OPCIONES_PDCA = [
  { valor: "", texto: "Todos los estados" },
  { valor: "abiertos", texto: "Abiertos (PDCA < 4)" },
  { valor: "1", texto: "1 - Plan" },
  { valor: "2", texto: "2 - Hacer" },
  { valor: "3", texto: "3 - Verificar" },
  { valor: "4", texto: "4 - Actuar" },
];

function SubtablaLean({ claveTabla, titulo, registros, tieneFuente, esEntrega }) {
  const [sorting, setSorting] = useState([]);
  const [columnFilters, setColumnFilters] = useState([]);

  const filas = useMemo(() => (Array.isArray(registros) ? registros : []), [registros]);
  const columnas = useMemo(() => crearColumnas(esEntrega), [esEntrega]);

  const categoriasDisponibles = useMemo(() => {
    const conjunto = new Set();
    for (const r of filas) {
      const cat = textoSeguro(r?.category);
      if (cat !== "sin datos") {
        conjunto.add(cat);
      }
    }
    return [...conjunto].sort((a, b) => a.localeCompare(b, "es"));
  }, [filas]);

  const tabla = useReactTable({
    data: filas,
    columns: columnas,
    state: { sorting, columnFilters },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  const filtroCatActual = String(tabla.getColumn("category")?.getFilterValue() ?? "");
  const filtroPdcaActual = String(tabla.getColumn("pdca")?.getFilterValue() ?? "");
  const hayFiltroActivo = Boolean(filtroCatActual || filtroPdcaActual);
  const idSelectCat = `filtro-cat-${claveTabla}`;
  const idSelectPdca = `filtro-pdca-${claveTabla}`;
  const filasVisibles = tabla.getRowModel().rows;

  return (
    <div className="bloque-tabla" data-tabla={claveTabla}>
      <div className="cabecera-subtabla">
        <h3 className="titulo-subtabla">{titulo}</h3>
        <span className="insignia insignia-oscura mono">
          {tieneFuente ? `${filasVisibles.length} / ${filas.length} registros` : "sin datos"}
        </span>
      </div>

      <div className="barra-filtros">
        <div className="campo-filtro">
          <label className="etiqueta-filtro" htmlFor={idSelectCat}>
            Categoría
          </label>
          <select
            id={idSelectCat}
            data-filtro="categoria"
            className="control-select"
            value={filtroCatActual}
            onChange={(e) => tabla.getColumn("category")?.setFilterValue(e.target.value || undefined)}
          >
            <option value="">Todas las categorías</option>
            {categoriasDisponibles.map((cat) => (
              <option key={cat} value={cat}>
                {esEntrega ? etiquetaCategoriaEnPantalla(cat) : cat}
              </option>
            ))}
          </select>
        </div>

        <div className="campo-filtro">
          <label className="etiqueta-filtro" htmlFor={idSelectPdca}>
            Estado PDCA
          </label>
          <select
            id={idSelectPdca}
            data-filtro="pdca"
            className="control-select"
            value={filtroPdcaActual}
            onChange={(e) => tabla.getColumn("pdca")?.setFilterValue(e.target.value || undefined)}
          >
            {OPCIONES_PDCA.map((op) => (
              <option key={op.valor} value={op.valor}>
                {op.texto}
              </option>
            ))}
          </select>
        </div>

        {hayFiltroActivo && (
          <button
            type="button"
            className="boton-control"
            onClick={() => setColumnFilters([])}
          >
            Limpiar filtros
          </button>
        )}
      </div>

      <div className="tabla-caja">
        <table className="tabla-datos">
          <thead>
            {tabla.getHeaderGroups().map((grupo) => (
              <tr key={grupo.id}>
                {grupo.headers.map((cabecera) => {
                  const direccion = cabecera.column.getIsSorted();
                  const ariaSort =
                    direccion === "asc"
                      ? "ascending"
                      : direccion === "desc"
                        ? "descending"
                        : "none";
                  const simboloOrden =
                    direccion === "asc" ? "▲" : direccion === "desc" ? "▼" : "↕";
                  return (
                    <th key={cabecera.id} scope="col" aria-sort={ariaSort}>
                      <button
                        type="button"
                        className={
                          direccion ? "boton-orden boton-orden-activo" : "boton-orden"
                        }
                        onClick={cabecera.column.getToggleSortingHandler()}
                      >
                        <span>
                          {flexRender(cabecera.column.columnDef.header, cabecera.getContext())}
                        </span>
                        <span aria-hidden="true">{simboloOrden}</span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {filasVisibles.length > 0 ? (
              filasVisibles.map((fila) => (
                <tr key={fila.id}>
                  {fila.getVisibleCells().map((celda) => (
                    <td
                      key={celda.id}
                      data-etiqueta={celda.column.columnDef.meta?.etiqueta || ""}
                    >
                      {flexRender(celda.column.columnDef.cell, celda.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columnas.length} className="estado-vacio">
                  {tieneFuente
                    ? "Sin registros para los filtros seleccionados."
                    : "sin datos"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function CalidadEntrega({ datos }) {
  const objeto = datos && typeof datos === "object" ? datos : {};
  const tieneCalidad = Array.isArray(objeto.qualityLog);
  const tieneEntrega = Array.isArray(objeto.deliveryLog);

  return (
    <section
      id="calidad-entrega"
      className="panel-seccion"
      aria-labelledby="titulo-calidad-entrega"
    >
      <div className="encabezado-seccion">
        <h2 id="titulo-calidad-entrega" className="titulo-seccion">
          Calidad y Entrega
        </h2>
        <p className="subtitulo-seccion">
          Contramedidas por componente técnico y seguimiento PDCA
        </p>
      </div>

      <SubtablaLean
        claveTabla="calidad"
        titulo="Registro de Calidad"
        registros={objeto.qualityLog}
        tieneFuente={tieneCalidad}
        esEntrega={false}
      />

      <SubtablaLean
        claveTabla="entrega"
        titulo="Registro de Entrega y Flujo"
        registros={objeto.deliveryLog}
        tieneFuente={tieneEntrega}
        esEntrega={true}
      />
    </section>
  );
}
