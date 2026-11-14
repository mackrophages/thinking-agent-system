const CATALOGO =
  typeof __CATALOGO_LEAN__ !== "undefined"
    ? __CATALOGO_LEAN__
    : {
        bloquesPrincipios: [],
        ramas: [],
        cuadrantes: [],
        etapas: [],
        reglasPick: {},
      };

const CINCO_PRINCIPIOS_LEAN = [
  {
    nombre: "Valor",
    significado:
      "Lo define quien recibe el trabajo y su criterio de aceptación, nunca la herramienta usada.",
    pregunta: "¿Quién recibe este entregable y cómo comprobará que está bien?",
  },
  {
    nombre: "Cadena de valor",
    significado:
      "Todos los pasos desde el encargo hasta la entrega útil, incluidos los relevos entre sesiones.",
    pregunta: "¿Por dónde pasa el trabajo y en qué eslabón aparece espera o retrabajo?",
  },
  {
    nombre: "Flujo",
    significado:
      "Avanzar pieza a pieza, verificando cada cambio antes del siguiente sin acumular lotes sin probar.",
    pregunta: "¿Avanza en cortes pequeños verificados o se estanca en fallos repetidos?",
  },
  {
    nombre: "Pull",
    significado:
      "Ejecutar únicamente ante la señal explícita del encargo recibido; agregar lo no pedido es sobreproducción.",
    pregunta: "¿Existe un encargo concreto que pida este paso ahora mismo?",
  },
  {
    nombre: "Perfección",
    significado:
      "Dirección continua hacia cero desperdicio estandarizando cada aprendizaje y revisando sin sesgo propio.",
    pregunta: "¿Qué cambia en el estándar y quién lo revisó con ojos frescos?",
  },
];

const SIGNIFICADO_RAMAS_AGENTE = {
  Método:
    "Procedimiento operativo, orden de pasos, reglas activas o falta de verificación temprana.",
  Máquina:
    "Código fuente, scripts de construcción, herramientas de línea de comandos o servidores MCP.",
  Material:
    "Datos de entrada, archivos leídos, esquemas o índices de contexto incompletos o desactualizados.",
  Medición:
    "Sensores de traza, suites de pruebas, validadores o criterios de inspección que no detectan el fallo.",
  Medio:
    "Sistema operativo, red, límites de cuota, reloj del entorno, variables o permisos de directorios.",
  Relevo:
    "Claridad del encargo, alcance, criterio de aceptación y devolución entre etapas; se audita el proceso.",
};

const DECISION_POR_CUADRANTE = {
  Implementar: {
    reglaPorDefecto: { impacto: "alto", esfuerzo: "bajo" },
    accion: "Prioridad inmediata: ejecutar y estandarizar en la ventana corta.",
    claseInsignia: "insignia insignia-exito insignia-tabla",
  },
  Desafío: {
    reglaPorDefecto: { impacto: "alto", esfuerzo: "alto" },
    accion: "Alto retorno con costo elevado: partir en entregas delgadas o estructurar en un A3.",
    claseInsignia: "insignia insignia-aviso insignia-tabla",
  },
  Posible: {
    reglaPorDefecto: { impacto: "bajo", esfuerzo: "bajo" },
    accion: "Mejora menor: abordar solo cuando haya holgura sin desplazar lo prioritario.",
    claseInsignia: "insignia insignia-oscura insignia-tabla",
  },
  Eliminar: {
    reglaPorDefecto: { impacto: "bajo", esfuerzo: "alto" },
    accion: "Descartar de plano: en un A3 válido jamás se elige una opción de este cuadrante.",
    claseInsignia: "insignia insignia-error insignia-tabla",
  },
};

const DETALLE_ETAPAS_A3 = {
  comprender: {
    secciones: "Secciones 1 a 2",
    resumen: "Contexto, desperdicio observado, pregunta cero, hechos medidos en Gemba y brecha.",
  },
  analizar: {
    secciones: "Secciones 1 a 4",
    resumen: "Meta medible, tabla Verificado vs. Supuesto, Ishikawa y cadena de porqués hasta diseño.",
  },
  proponer: {
    secciones: "Secciones 1 a 5",
    resumen: "Opciones de contramedida con nivel poka-yoke, evaluación PICK y predicción cuantificable.",
  },
  planear: {
    secciones: "Secciones 1 a 6",
    resumen: "Plan PDCA por componente responsable, comando de verificación, ventana y autorización.",
  },
  cerrar: {
    secciones: "Secciones 1 a 7",
    resumen: "Comparación predicho contra real, señales de riesgo, revisión futura y estandarización.",
  },
};

const GUIA_SKILLS_LEAN = [
  {
    nombre: "agent-ops",
    cuando: "Al abrir sesión, ordenar contexto con 5S, delegar un encargo o parar en Andon al tercer fallo.",
    pieza: "Estándar TWI del ejecutor, encargo/devolución y fórmulas FTY, CT, CBR y PCE.",
  },
  {
    nombre: "gemba",
    cuando: "Antes de diagnosticar una falla, confiar en un resumen previo o dar un entregable por cerrado.",
    pieza: "Inspección directa en código, datos, navegador sin red y chequeo-gemba.sh.",
  },
  {
    nombre: "5-porques",
    cuando: "Ante cualquier defecto, regresión de pruebas o incidente operativo antes de tocar código.",
    pieza: "Separación Verificado vs. Supuesto, cadena causal sin culpa y contramedida poka-yoke.",
  },
  {
    nombre: "a3",
    cuando: "Para problemas no triviales con varias hipótesis vivas o cambios costosos de revertir.",
    pieza: "Plantilla por etapas, validador determinista validar-a3.py y vista dibujar-a3.py.",
  },
  {
    nombre: "ojos-frescos",
    cuando: "Antes de aprobar un A3, una tabla crítica de datos, una Jugada VSM o un cambio estructural.",
    pieza: "Auditoría en frío sin historial previo para cortar el sesgo de confirmación.",
  },
  {
    nombre: "goldfish-observer",
    cuando: "Para medir corridas 1 a 12 fuera de banda, actualizar este tablero o trazar Jugadas VSM.",
    pieza: "observer_cli.py, bitácoras de calidad/entrega y tablero HTML autónomo.",
  },
  {
    nombre: "kaizen",
    cuando: "Al priorizar mejoras pendientes con PICK y cerrar compromisos con reflexión honesta.",
    pieza: "KAIZEN.md y kaizen-cli.py con cortes de 5 h, 20 h y 1 semana.",
  },
];

function renderizarTextoConCodigo(texto) {
  const cadena = String(texto ?? "");
  const partes = cadena.split(/(`[^`]+`)/g);
  return partes.map((trozo, idx) => {
    if (trozo.startsWith("`") && trozo.endsWith("`") && trozo.length >= 2) {
      return (
        <code key={idx} className="codigo-en-linea">
          {trozo.slice(1, -1)}
        </code>
      );
    }
    return trozo;
  });
}

export function HerramientasLean() {
  const bloques = CATALOGO.bloquesPrincipios || [];
  const ramas = CATALOGO.ramas || [];
  const cuadrantes = CATALOGO.cuadrantes || [];
  const etapas = CATALOGO.etapas || [];
  const reglasPick = CATALOGO.reglasPick || {};

  return (
    <section
      id="herramientas-lean"
      className="panel-seccion"
      aria-labelledby="titulo-herramientas-lean"
    >
      <div className="encabezado-seccion">
        <h2 id="titulo-herramientas-lean" className="titulo-seccion">
          Herramientas Lean
        </h2>
        <p className="subtitulo-seccion">
          Referencia operativa sincronizada con rules/AGENTS.md y contrato-a3.json
        </p>
      </div>

      <div className="subpanel-herramienta">
        <div className="cabecera-grafica">
          <h3 className="titulo-subtabla">Los 14 principios en cuatro bloques</h3>
          <span className="insignia insignia-oscura mono">Fuente: rules/AGENTS.md</span>
        </div>

        <div className="rejilla-bloques-principios">
          {bloques.map((bloque) => (
            <article
              key={bloque.encabezado}
              className="tarjeta-herramienta"
              data-bloque-principios={bloque.encabezado}
            >
              <h4 className="titulo-bloque-lean">{bloque.encabezado}</h4>
              <ol className="lista-principios">
                {bloque.principios.map((p) => (
                  <li
                    key={p.numero}
                    className="item-principio"
                    data-principio-numero={String(p.numero)}
                    data-principio-nombre={p.nombre}
                  >
                    <span className="principio-cabecera">
                      <span className="principio-indice mono">{p.numero}.</span>{" "}
                      <strong className="principio-nombre">{p.nombre}:</strong>
                    </span>{" "}
                    <span className="principio-texto">
                      {renderizarTextoConCodigo(p.descripcion)}
                    </span>
                  </li>
                ))}
              </ol>
            </article>
          ))}
        </div>
      </div>

      <div className="subpanel-herramienta">
        <div className="cabecera-grafica">
          <h3 className="titulo-subtabla">Los 5 principios Lean: la brújula</h3>
          <span className="insignia insignia-oscura mono">Diseño de flujo</span>
        </div>

        <div className="rejilla-cinco-lean">
          {CINCO_PRINCIPIOS_LEAN.map((p, idx) => (
            <article key={p.nombre} className="tarjeta-herramienta" data-principio-lean={p.nombre}>
              <div className="cabecera-item-lean">
                <span className="insignia insignia-amarilla mono">#{idx + 1}</span>
                <h4 className="nombre-item-lean">{p.nombre}</h4>
              </div>
              <p className="texto-herramienta">{p.significado}</p>
              <p className="pregunta-brujula">{p.pregunta}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="rejilla-dos-herramientas">
        <div className="subpanel-herramienta">
          <div className="cabecera-grafica">
            <h3 className="titulo-subtabla">Ishikawa de seis ramas</h3>
            <span className="insignia insignia-oscura mono">RAMAS · contrato-a3.json</span>
          </div>

          <div className="rejilla-ramas">
            {ramas.map((rama) => (
              <article
                key={rama}
                className="tarjeta-herramienta"
                data-ishikawa-rama={rama}
              >
                <h4 className="nombre-item-lean">{rama}</h4>
                <p className="texto-herramienta">
                  {SIGNIFICADO_RAMAS_AGENTE[rama] ||
                    "Rama causal verificable en el proceso técnico y documental."}
                </p>
              </article>
            ))}
          </div>
        </div>

        <div className="subpanel-herramienta">
          <div className="cabecera-grafica">
            <h3 className="titulo-subtabla">Matriz PICK: impacto y esfuerzo</h3>
            <span className="insignia insignia-oscura mono">CUADRANTES · contrato-a3.json</span>
          </div>

          <div className="rejilla-pick">
            {cuadrantes.map((cuadrante) => {
              const info = DECISION_POR_CUADRANTE[cuadrante] || {
                reglaPorDefecto: { impacto: "variable", esfuerzo: "variable" },
                accion: "Evaluar retorno medible frente al esfuerzo requerido.",
                claseInsignia: "insignia insignia-oscura insignia-tabla",
              };
              const par = reglasPick[cuadrante] || info.reglaPorDefecto;
              return (
                <article
                  key={cuadrante}
                  className="tarjeta-herramienta"
                  data-pick-cuadrante={cuadrante}
                >
                  <div className="cabecera-item-lean">
                    <span className={info.claseInsignia}>{cuadrante}</span>
                    <span className="regla-pick mono">
                      Impacto {par.impacto} · Esfuerzo {par.esfuerzo}
                    </span>
                  </div>
                  <p className="texto-herramienta">{info.accion}</p>
                </article>
              );
            })}
          </div>
        </div>
      </div>

      <div className="subpanel-herramienta">
        <div className="cabecera-grafica">
          <h3 className="titulo-subtabla">Las cinco etapas del A3</h3>
          <span className="insignia insignia-oscura mono">ETAPAS · contrato-a3.json</span>
        </div>

        <ol className="rejilla-etapas-a3">
          {etapas.map((etapa, idx) => {
            const det = DETALLE_ETAPAS_A3[etapa] || {
              secciones: "Validación progresiva",
              resumen: "Completar las evidencias requeridas antes de avanzar.",
            };
            return (
              <li
                key={etapa}
                className="tarjeta-herramienta item-etapa-a3"
                data-a3-etapa={etapa}
              >
                <div className="cabecera-item-lean">
                  <span className="pareto-orden mono">Etapa {idx + 1}</span>
                  <code className="chip-componente">{etapa}</code>
                </div>
                <span className="etiqueta-secciones-a3 mono">{det.secciones}</span>
                <p className="texto-herramienta">{det.resumen}</p>
              </li>
            );
          })}
        </ol>
      </div>

      <div className="subpanel-herramienta">
        <div className="cabecera-grafica">
          <h3 className="titulo-subtabla">Qué skill usar en cada caso</h3>
          <span className="insignia insignia-oscura mono">7 skills · TAS</span>
        </div>

        <div className="rejilla-skills">
          {GUIA_SKILLS_LEAN.map((s) => (
            <article
              key={s.nombre}
              className="tarjeta-herramienta"
              data-lean-skill={s.nombre}
            >
              <div className="cabecera-item-lean">
                <code className="chip-componente">{s.nombre}</code>
              </div>
              <p className="texto-herramienta">{s.cuando}</p>
              <p className="pieza-skill">{s.pieza}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
