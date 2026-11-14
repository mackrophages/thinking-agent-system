import { normalizarNivelPdca, RuedaPdca } from "./RuedaPdca.jsx";
import { etiquetaCategoriaEnPantalla, textoSeguro } from "./utilidadesDatos.mjs";

function filtroExactoCategoria(fila, idColumna, valorFiltro) {
  if (!valorFiltro) return true;
  return String(fila.getValue(idColumna) ?? "") === valorFiltro;
}

function filtroEstadoPdca(fila, idColumna, valorFiltro) {
  if (!valorFiltro) return true;
  const nivel = Number(fila.getValue(idColumna)) || 0;
  if (valorFiltro === "abiertos") {
    return nivel < 4;
  }
  return nivel === Number(valorFiltro);
}

function insigniaCategoria(categoriaCruda, esEntrega) {
  const textoVisible = esEntrega
    ? etiquetaCategoriaEnPantalla(categoriaCruda)
    : textoSeguro(categoriaCruda);
  if (textoVisible === "sin datos") {
    return <span className="insignia insignia-tabla insignia-neutra">sin datos</span>;
  }
  if (categoriaCruda === "CT > TT") {
    return <span className="insignia insignia-tabla insignia-error">{textoVisible}</span>;
  }
  if (categoriaCruda === "CT > Standard") {
    return <span className="insignia insignia-tabla insignia-aviso">{textoVisible}</span>;
  }
  return <span className="insignia insignia-tabla insignia-oscura">{textoVisible}</span>;
}

export function crearColumnas(esEntrega) {
  const base = [
    {
      id: "build",
      header: "Corrida",
      meta: { etiqueta: "Corrida" },
      accessorFn: (fila) => {
        const n = Number(fila?.build);
        return fila?.build !== null &&
          fila?.build !== undefined &&
          fila?.build !== "" &&
          Number.isFinite(n)
          ? n
          : -1;
      },
      cell: (info) => {
        const val = info.getValue();
        return <span className="mono">{val >= 0 ? `#${val}` : "sin datos"}</span>;
      },
    },
    {
      id: "issue",
      header: "Problema",
      meta: { etiqueta: "Problema" },
      accessorFn: (fila) => textoSeguro(fila?.issue),
      cell: (info) => info.getValue(),
    },
    {
      id: "category",
      header: "Categoría",
      meta: { etiqueta: "Categoría" },
      accessorFn: (fila) => textoSeguro(fila?.category),
      filterFn: filtroExactoCategoria,
      sortingFn: (filaA, filaB, idCol) => {
        const a = esEntrega
          ? etiquetaCategoriaEnPantalla(filaA.getValue(idCol))
          : filaA.getValue(idCol);
        const b = esEntrega
          ? etiquetaCategoriaEnPantalla(filaB.getValue(idCol))
          : filaB.getValue(idCol);
        return String(a).localeCompare(String(b), "es");
      },
      cell: (info) => insigniaCategoria(info.getValue(), esEntrega),
    },
  ];

  if (esEntrega) {
    base.push({
      id: "muda",
      header: "Muda",
      meta: { etiqueta: "Muda" },
      accessorFn: (fila) => textoSeguro(fila?.muda),
      cell: (info) => info.getValue(),
    });
  }

  base.push(
    {
      id: "cm",
      header: "Contramedida",
      meta: { etiqueta: "Contramedida" },
      accessorFn: (fila) => textoSeguro(fila?.cm),
      cell: (info) => info.getValue(),
    },
    {
      id: "who",
      header: "Componente",
      meta: { etiqueta: "Componente" },
      accessorFn: (fila) => textoSeguro(fila?.who),
      cell: (info) => <code className="chip-componente">{info.getValue()}</code>,
    },
    {
      id: "pdca",
      header: "PDCA",
      meta: { etiqueta: "PDCA" },
      accessorFn: (fila) => normalizarNivelPdca(fila?.pdca),
      filterFn: filtroEstadoPdca,
      cell: (info) => <RuedaPdca valor={info.row.original?.pdca} />,
    },
  );

  return base;
}
