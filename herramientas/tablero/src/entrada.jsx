import { createRoot } from "react-dom/client";
import { Tablero } from "./Tablero.jsx";

const contenedor = document.getElementById("raiz-tablero");
if (contenedor) {
  const datos = typeof window !== "undefined" ? window.BOARD_DATA : undefined;
  createRoot(contenedor).render(<Tablero datos={datos} />);
}
