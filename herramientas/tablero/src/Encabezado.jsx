import { minutosSeguros, textoSeguro } from "./utilidadesDatos.mjs";

const SECCIONES_NAVEGACION = [
  { href: "#encabezado", texto: "Encabezado" },
  { href: "#indicadores", texto: "Indicadores" },
  { href: "#corridas", texto: "Corridas" },
  { href: "#calidad-entrega", texto: "Calidad y Entrega" },
  { href: "#pareto", texto: "Pareto" },
  { href: "#herramientas-lean", texto: "Herramientas Lean" },
];

export function Encabezado({ datos }) {
  const objeto = datos && typeof datos === "object" ? datos : {};
  const titulo = textoSeguro(objeto.projectTitle);
  const modo = textoSeguro(objeto.observerMode);
  const mejorMarca =
    objeto.bestScore && typeof objeto.bestScore === "object"
      ? textoSeguro(objeto.bestScore.label)
      : "sin datos";
  const meta = textoSeguro(objeto.bestScoreGoal);
  const estandar = minutosSeguros(objeto.standardMinutes);
  const techoAcordado = minutosSeguros(objeto.taktTimeMinutes);

  return (
    <section id="encabezado" className="panel-seccion" aria-labelledby="titulo-proyecto">
      <div className="encabezado-superior">
        <span className="kicker">Tablero de Preparación · Círculo de Ohno</span>
        <span className="insignia insignia-oscura">{modo}</span>
      </div>

      <h1 id="titulo-proyecto" className="titulo-proyecto">
        {titulo}
      </h1>

      <div className="rejilla-meta">
        <div className="caja-meta caja-meta-destacada">
          <span className="etiqueta-meta">Mejor corrida</span>
          <span className="valor-meta valor-meta-acento">{mejorMarca}</span>
        </div>
        <div className="caja-meta">
          <span className="etiqueta-meta">Meta de flujo</span>
          <span className="valor-meta">{meta}</span>
        </div>
        <div className="caja-meta">
          <span className="etiqueta-meta">Estándar</span>
          <span className="valor-meta mono">{estandar}</span>
        </div>
        <div className="caja-meta">
          <span className="etiqueta-meta">Techo acordado</span>
          <span className="valor-meta mono">{techoAcordado}</span>
        </div>
      </div>

      <nav className="barra-anclas" aria-label="Secciones del tablero">
        {SECCIONES_NAVEGACION.map((item) => (
          <a key={item.href} href={item.href} className="enlace-ancla">
            {item.texto}
          </a>
        ))}
      </nav>
    </section>
  );
}
