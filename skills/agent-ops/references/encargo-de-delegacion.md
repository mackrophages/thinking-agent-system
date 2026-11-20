# Encargo de delegación: un solo estándar de relevo con dos caras

Se usa cada vez que un agente pasa trabajo a otro (subagente, otro modelo, otra sesión) o a una
persona. El encargo es la señal de quien recibe: sin él no hay pull. En un encargo de una línea basta
con meta, criterio de aceptación y salida; la plantilla entera es para lo que no cabe en una línea.

```markdown
## Encargo (lo escribe quien delega)
- **Pedido original:** las palabras del dueño (o de quien pidió) que originan el trabajo, citadas textuales; en varias rondas, también las que siguieron.
- **Contexto:** por qué existe este trabajo y qué objetivo mayor apoya.
- **Meta:** qué debe quedar logrado, en una frase.
- **Brecha:** de X (medido) a Y (meta) para <cuándo>.
- **Criterio de aceptación:** cómo se comprueba que está bien (un comando, una prueba, una revisión concreta).
- **Pendientes abiertos:** solo en trabajo de varias rondas: lo que las anteriores dejaron sin resolver o sin verificar, uno por línea, tal como se anotó y con la ronda que lo abrió.
- **Salida esperada:** qué se entrega y en qué ruta.
- **Qué no tocar:** archivos, sistemas y decisiones fuera del alcance.
- **Si falta algo:** se para y se pregunta; no se explora a ciegas.

## Devolución (la escribe quien recibe, antes de ejecutar)
- **Qué entendí:** la meta y el criterio de aceptación con mis palabras.
- **Cómo lo voy a hacer:** los pasos principales.
- **Cuánto cuesta:** ventana (5 h, 20 h o 1 semana) y contexto que hay que cargar.
- **Qué no es viable:** lo que no se puede con lo dado y qué haría falta.
```

## Reglas

1. **El encargo fija el qué, no el cómo.** Lleva la decisión del dueño textual, los hechos observados,
   la meta, el criterio y los límites. No lleva el diseño propio de quien delega ni requisitos que nadie
   pidió: quien recibe está más cerca del trabajo y propone el cómo, salvo que el cómo sea parte de un
   estándar escrito. Resumir la decisión del dueño también es diseño propio: se cita.
2. **La devolución va antes de ejecutar.** Si no coincide con lo que se quería, quien delega corrige el
   encargo, no la devolución. Lo que no es viable se sube con hechos y opciones, no se calla.
3. **Cuando falla lo delegado, se revisa primero el encargo.** Recorre las brechas en orden: lo que se
   quería contra lo que se entendió, lo entendido contra lo escrito, lo escrito contra lo entregado, y
   lo entregado contra lo reportado (abre la salida: Gemba). Si el hueco estaba en el encargo, la
   contramedida va en el encargo o en esta plantilla; en el Ishikawa del A3 es la rama Relevo.
4. **La entrega empieza por lo que se decide.** ¿Se cumplió el criterio de aceptación? Sí o no, con su
   evidencia; después, qué quedó fuera y qué decisión se necesita. El detalle va al final.
5. **El silencio no es resolución.** Quien delega es el único que ve todas las rondas, así que lleva
   los pendientes abiertos de una a la siguiente. Agrega todo lo que una entrega deja sin resolver o sin
   verificar, y cierra un pendiente solo con evidencia (la salida de una prueba que lo muestra resuelto),
   nunca porque la ronda siguiente dejó de mencionarlo. Se copia la observación, no un remedio.
6. **Latido.** En un trabajo de más de unos minutos, quien recibe anota en `progreso.md` la hora y el
   paso al terminar cada paso, y en un comando largo al menos cada 5 minutos. Quien delega sabe así si
   sigue vivo sin interrumpirlo, y si el trabajo se corta, el siguiente sabe desde dónde seguir.
