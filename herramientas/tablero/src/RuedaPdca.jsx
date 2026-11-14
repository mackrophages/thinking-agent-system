const NOMBRES_ETAPA = {
  1: "1/4 Plan",
  2: "2/4 Hacer",
  3: "3/4 Verificar",
  4: "4/4 Actuar",
};

const CUARTOS_SVG = [
  "M 12 12 L 12 2 A 10 10 0 0 1 22 12 Z",
  "M 12 12 L 22 12 A 10 10 0 0 1 12 22 Z",
  "M 12 12 L 12 22 A 10 10 0 0 1 2 12 Z",
  "M 12 12 L 2 12 A 10 10 0 0 1 12 2 Z",
];

export function normalizarNivelPdca(valor) {
  if (valor === null || valor === undefined || valor === "") {
    return 0;
  }
  const num = Number(valor);
  if (Number.isInteger(num) && num >= 1 && num <= 4) {
    return num;
  }
  return 0;
}

export function RuedaPdca({ valor }) {
  const nivel = normalizarNivelPdca(valor);
  const textoEtiqueta = NOMBRES_ETAPA[nivel] || "sin datos";
  const colorActivo = nivel === 4 ? "var(--color-success)" : "var(--color-primary)";

  return (
    <span className="celda-pdca">
      <svg
        className="svg-rueda-pdca"
        viewBox="0 0 24 24"
        role="img"
        aria-label={`Estado PDCA: ${textoEtiqueta}`}
      >
        {CUARTOS_SVG.map((trazo, indice) => {
          const cuartoActivo = nivel >= indice + 1;
          return (
            <path
              key={indice}
              d={trazo}
              fill={cuartoActivo ? colorActivo : "var(--color-surface-elevated)"}
              stroke="var(--color-hairline-strong)"
              strokeWidth="1.4"
            />
          );
        })}
      </svg>
      <span className="etiqueta-pdca">{textoEtiqueta}</span>
    </span>
  );
}
