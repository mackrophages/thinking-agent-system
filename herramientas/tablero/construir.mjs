import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  realpathSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, extname, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { DATOS_EJEMPLO } from "./src/datosEjemplo.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SALIDA_POR_DEFECTO = resolve(
  __dirname,
  "../../skills/goldfish-observer/resources/index.html",
);
const TOPE_BYTES = 600 * 1024;

function parsearArgumentos(argv) {
  let salida = SALIDA_POR_DEFECTO;
  let comprobar = false;

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--comprobar") {
      comprobar = true;
    } else if (arg === "--salida") {
      const siguiente = argv[i + 1];
      if (!siguiente || siguiente.startsWith("--")) {
        throw new Error("La bandera --salida requiere una ruta de destino.");
      }
      salida = resolve(process.cwd(), siguiente);
      i += 1;
    } else {
      throw new Error(`Argumento no reconocido: ${arg}`);
    }
  }

  return { salida, comprobar };
}

function serializarJsonSeguroParaScript(datos) {
  return JSON.stringify(datos, null, 2)
    .replaceAll("&", "\\u0026")
    .replaceAll("<", "\\u003c")
    .replaceAll(">", "\\u003e")
    .replaceAll("'", "\\u0027");
}

function encontrarDirectorioPaquete(rutaArchivo) {
  let actual = dirname(rutaArchivo);
  const raiz = parseRoot(actual);
  while (actual && actual !== raiz) {
    const candidato = resolve(actual, "package.json");
    if (existsSync(candidato)) {
      return actual;
    }
    const padre = dirname(actual);
    if (padre === actual) break;
    actual = padre;
  }
  return null;
}

function parseRoot(ruta) {
  const coincidencia = ruta.match(/^([A-Za-z]:\\|\/)/);
  return coincidencia ? coincidencia[1] : "/";
}

function buscarArchivoLicencia(dirPaquete) {
  const entradas = readdirSync(dirPaquete).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const patron = /^licen[cs]e(?:\.(?:md|txt))?$/i;
  const encontrado = entradas.find((nombre) => patron.test(nombre));
  return encontrado ? resolve(dirPaquete, encontrado) : null;
}

function recolectarAvisosDeLicencia(metafile) {
  const dirSrc = resolve(__dirname, "src");
  const directoriosPaquete = new Set();

  const rutasEntrada = Object.keys(metafile.inputs).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  for (const rutaRelativa of rutasEntrada) {
    const rutaAbsoluta = resolve(__dirname, rutaRelativa);
    const relASrc = relative(dirSrc, rutaAbsoluta);
    if (!relASrc.startsWith("..") && !relASrc.startsWith("/")) {
      continue;
    }
    if (!rutaRelativa.includes("node_modules")) {
      continue;
    }
    const dirPkg = encontrarDirectorioPaquete(rutaAbsoluta);
    if (dirPkg && dirPkg !== __dirname) {
      directoriosPaquete.add(dirPkg);
    }
  }

  const paquetes = [];
  for (const dirPkg of directoriosPaquete) {
    const pkgJsonRuta = resolve(dirPkg, "package.json");
    const pkg = JSON.parse(readFileSync(pkgJsonRuta, "utf-8"));
    const idPaquete = `${pkg.name}@${pkg.version}`;
    const rutaLicencia = buscarArchivoLicencia(dirPkg);
    if (!rutaLicencia) {
      throw new Error(
        `Falta el archivo de licencia del paquete de terceros empaquetado: ${idPaquete}`,
      );
    }
    const textoLicencia = readFileSync(rutaLicencia, "utf-8")
      .replaceAll("\r\n", "\n")
      .replaceAll("*/", "* /")
      .trim();
    if (!textoLicencia) {
      throw new Error(`El archivo de licencia está vacío en el paquete: ${idPaquete}`);
    }
    paquetes.push({
      id: idPaquete,
      tipo: pkg.license || "Licencia incluida",
      texto: textoLicencia,
    });
  }

  paquetes.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));

  const gruposPorTexto = new Map();
  for (const p of paquetes) {
    const existente = gruposPorTexto.get(p.texto);
    if (existente) {
      existente.ids.push(p.id);
      if (!existente.tipos.includes(p.tipo)) {
        existente.tipos.push(p.tipo);
      }
    } else {
      gruposPorTexto.set(p.texto, {
        ids: [p.id],
        tipos: [p.tipo],
        texto: p.texto,
      });
    }
  }

  const bloques = [...gruposPorTexto.values()].map((grupo) => {
    const encabezado = `Paquetes: ${grupo.ids.join(", ")} (${grupo.tipos.join(", ")})`;
    return `${encabezado}\n${grupo.texto}`;
  });

  if (bloques.length === 0) {
    throw new Error("No se detectaron paquetes de terceros con licencia en el empaquetado.");
  }

  return `/*\nAvisos de licencia de terceros\n\n${bloques.join("\n\n---\n\n")}\n*/`;
}

function obtenerRutasModulosAdicionales() {
  const rutaReactCharts = resolve(__dirname, "node_modules/@tanstack/react-charts");
  if (!existsSync(rutaReactCharts)) {
    return [];
  }
  const real = realpathSync(rutaReactCharts);
  const contenedor = resolve(real, "../..");
  return existsSync(contenedor) ? [contenedor] : [];
}

function parsearPrincipiosDeAgentsMd(textoMd) {
  const normalizado = textoMd.replaceAll("\r\n", "\n");
  const seccion = normalizado.match(/^## 1\.[^\n]*\n([\s\S]*?)(?=^## |(?![\s\S]))/m);
  const cuerpo = seccion ? seccion[1] : normalizado;

  const bloques = [];
  let bloqueActual = null;
  let totalPrincipios = 0;

  for (const lineaCruda of cuerpo.split("\n")) {
    const linea = lineaCruda.trim();
    if (!linea) continue;

    const mBloque = linea.match(/^###\s+([A-Z]\.\s+.+)$/);
    if (mBloque) {
      bloqueActual = {
        encabezado: mBloque[1].trim(),
        principios: [],
      };
      bloques.push(bloqueActual);
      continue;
    }

    const mPrincipio = linea.match(/^-\s+\*\*(\d+)\.\s+([^*]+?):\*\*\s+(.+)$/);
    if (mPrincipio) {
      if (!bloqueActual) {
        throw new Error(
          "Se encontró un principio antes de su encabezado de bloque ### en rules/AGENTS.md.",
        );
      }
      const numero = Number(mPrincipio[1]);
      bloqueActual.principios.push({
        numero,
        nombre: mPrincipio[2].trim(),
        descripcion: mPrincipio[3].trim(),
      });
      totalPrincipios += 1;
    }
  }

  if (bloques.length !== 4 || totalPrincipios !== 14) {
    throw new Error(
      `Extracción inválida de rules/AGENTS.md: se esperaban 4 bloques y 14 principios, salieron ${bloques.length} bloques y ${totalPrincipios} principios.`,
    );
  }

  return bloques;
}

const CLAVES_CONTRATO_REQUERIDAS = [
  "etapas",
  "ultima_seccion",
  "ramas",
  "subramas",
  "estados_rama",
  "niveles",
  "cuadrantes",
  "decisiones",
  "ventanas",
  "columnas_opciones",
  "rotulos_7",
  "pick",
  "reglas",
];

export function cargarCatalogoLean() {
  const raizRepo = resolve(__dirname, "../..");
  const rutaAgents = resolve(raizRepo, "rules/AGENTS.md");
  const rutaContrato = resolve(raizRepo, "skills/a3/references/contrato-a3.json");

  const datosVacios = {
    bloquesPrincipios: [],
    ramas: [],
    cuadrantes: [],
    etapas: [],
    reglasPick: {},
  };

  if (!existsSync(rutaAgents)) {
    return {
      ok: false,
      error: new Error(`No existe rules/AGENTS.md en ${rutaAgents}`),
      datos: datosVacios,
    };
  }
  if (!existsSync(rutaContrato)) {
    return {
      ok: false,
      error: new Error(`No existe contrato-a3.json en ${rutaContrato}`),
      datos: datosVacios,
    };
  }

  try {
    const textoAgents = readFileSync(rutaAgents, "utf-8");
    const bloquesPrincipios = parsearPrincipiosDeAgentsMd(textoAgents);
    const crudoContrato = JSON.parse(readFileSync(rutaContrato, "utf-8"));

    if (
      !crudoContrato ||
      typeof crudoContrato !== "object" ||
      typeof crudoContrato.vigente !== "number" ||
      !crudoContrato.versiones ||
      typeof crudoContrato.versiones !== "object"
    ) {
      throw new Error(
        "Esquema inválido en contrato-a3.json: faltan 'vigente' o 'versiones'.",
      );
    }

    const claveVigente = String(crudoContrato.vigente);
    const contrato = crudoContrato.versiones[claveVigente];
    if (!contrato || typeof contrato !== "object") {
      throw new Error(
        `No existe el contrato vigente '${claveVigente}' en contrato-a3.json.`,
      );
    }

    for (const clave of CLAVES_CONTRATO_REQUERIDAS) {
      if (!(clave in contrato)) {
        throw new Error(
          `Falta la clave obligatoria '${clave}' en el contrato ${claveVigente} de contrato-a3.json.`,
        );
      }
    }

    if (
      !Array.isArray(contrato.ramas) ||
      !Array.isArray(contrato.cuadrantes) ||
      !Array.isArray(contrato.etapas) ||
      !Array.isArray(contrato.pick) ||
      !contrato.subramas ||
      typeof contrato.subramas !== "object" ||
      Array.isArray(contrato.subramas)
    ) {
      throw new Error(
        `Tipos inválidos en el contrato ${claveVigente} de contrato-a3.json.`,
      );
    }

    const reglasPick = {};
    for (const entrada of contrato.pick) {
      if (
        !entrada ||
        typeof entrada !== "object" ||
        typeof entrada.impacto !== "string" ||
        typeof entrada.esfuerzo !== "string" ||
        typeof entrada.cuadrante !== "string"
      ) {
        throw new Error(
          `Entrada PICK inválida en el contrato ${claveVigente} de contrato-a3.json.`,
        );
      }
      reglasPick[entrada.cuadrante] = {
        impacto: entrada.impacto,
        esfuerzo: entrada.esfuerzo,
      };
    }

    return {
      ok: true,
      error: null,
      datos: {
        bloquesPrincipios,
        ramas: contrato.ramas,
        cuadrantes: contrato.cuadrantes,
        etapas: contrato.etapas,
        reglasPick,
      },
    };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err : new Error(String(err)),
      datos: datosVacios,
    };
  }
}

async function construirHtml() {
  const esbuild = await import("esbuild");
  const rutaCss = resolve(__dirname, "src/estilos.css");
  const cssCrudo = readFileSync(rutaCss, "utf-8");
  if (/@import/i.test(cssCrudo) || /url\(\s*['"]?https?:/i.test(cssCrudo)) {
    throw new Error("El CSS contiene @import o url(http...), prohibidos por el contrato.");
  }

  const cssMinificado = await esbuild.transform(cssCrudo, {
    loader: "css",
    minify: true,
    charset: "utf8",
  });

  const resultadoCatalogo = cargarCatalogoLean();

  const resultadoJs = await esbuild.build({
    absWorkingDir: __dirname,
    entryPoints: ["src/entrada.jsx"],
    bundle: true,
    write: false,
    format: "iife",
    platform: "browser",
    target: ["es2020"],
    jsx: "automatic",
    minify: true,
    charset: "utf8",
    legalComments: "none",
    metafile: true,
    nodePaths: obtenerRutasModulosAdicionales(),
    define: {
      "process.env.NODE_ENV": '"production"',
      __CATALOGO_LEAN__: JSON.stringify(resultadoCatalogo.datos),
    },
  });

  if (resultadoJs.outputFiles.length !== 1) {
    throw new Error(`Se esperaba 1 archivo JS de salida, salieron ${resultadoJs.outputFiles.length}.`);
  }

  // En literales JS, <\/script equivale a </script y evita cerrar la etiqueta HTML <script>.
  const jsLimpio = resultadoJs.outputFiles[0].text
    .replace(/<\/script/gi, "<\\/script")
    .trim();

  if (/<\/script/i.test(jsLimpio)) {
    throw new Error("El JS empaquetado todavía contiene la secuencia prohibida </script.");
  }

  const comentarioLicencias = recolectarAvisosDeLicencia(resultadoJs.metafile);
  if (/<\/script/i.test(comentarioLicencias)) {
    throw new Error("El bloque de licencias contiene la secuencia prohibida </script.");
  }

  if (!resultadoCatalogo.ok) {
    throw resultadoCatalogo.error;
  }

  const datosEjemploJson = serializarJsonSeguroParaScript(DATOS_EJEMPLO);

  const lineas = [
    '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">',
    "<!-- Archivo generado. No editar a mano: regenerar con node herramientas/tablero/construir.mjs -->",
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    "<title>Tablero de Preparación: Observador Goldfish</title>",
    `<style>${cssMinificado.code.trim()}</style>`,
    "</head><body>",
    `<script id="board-data-script">\n      window.BOARD_DATA = ${datosEjemploJson};\n    </script>`,
    '<div id="raiz-tablero"></div>',
    `<script>\n${jsLimpio}\n${comentarioLicencias}\n</script>`,
    "</body></html>",
    "",
  ];

  const html = lineas.join("\n");

  if (html.includes("\u2014") || html.includes("\u2013")) {
    throw new Error("El HTML generado contiene guiones largos o medios prohibidos.");
  }

  const bytes = Buffer.from(html, "utf-8");
  if (bytes.byteLength > TOPE_BYTES) {
    throw new Error(`El HTML generado pesa ${bytes.byteLength} bytes y supera el tope de ${TOPE_BYTES}.`);
  }

  return bytes;
}

function resolverRutaSalida(salida) {
  if (existsSync(salida) && statSync(salida).isDirectory()) {
    return resolve(salida, "index.html");
  }
  if (!extname(salida)) {
    return resolve(salida, "index.html");
  }
  return salida;
}

async function main() {
  const { salida, comprobar } = parsearArgumentos(process.argv.slice(2));
  const destino = resolverRutaSalida(salida);
  const bytesGenerados = await construirHtml();

  if (comprobar) {
    if (!existsSync(destino)) {
      process.stderr.write(`No existe el archivo a comprobar: ${destino}\n`);
      process.exit(1);
    }
    const bytesActuales = readFileSync(destino);
    if (!bytesActuales.equals(bytesGenerados)) {
      process.stderr.write(
        "El archivo index.html no coincide con una construcción limpia. Ejecuta: node herramientas/tablero/construir.mjs\n",
      );
      process.exit(1);
    }
    process.stdout.write("COMPROBADO: la salida coincide byte a byte.\n");
    return;
  }

  mkdirSync(dirname(destino), { recursive: true });
  writeFileSync(destino, bytesGenerados);
  process.stdout.write(`Generado (${bytesGenerados.byteLength} bytes)\n`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((err) => {
    process.stderr.write(`Error al construir el tablero: ${err.message || String(err)}\n`);
    process.exit(1);
  });
}
