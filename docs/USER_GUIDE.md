# Guía de usuario — instalación

Para quien va a *usar* `d-arxiv-1st` (no para quien desarrolla el repo — ver `README.md`/`ARCHITECTURE.md` §03b para esa distinción).

## Qué camino te corresponde

| Dónde vas a pedirle cosas a `d-arxiv-1st` | Camino |
|---|---|
| Claude Code CLI (terminal) | **A** — wizard, nada más |
| Cowork o la app de Claude, y quieres poder traer **contenido nuevo** de archive.org ahí | **B** — wizard una vez, más instalar una extensión `.mcpb` |
| Cowork, sin acceso a terminal en ningún momento | **C** — hoy no puedes traer contenido nuevo; sí puedes trabajar con lo que ya esté descargado |

Los tres caminos comparten el mismo motor y la misma config (`~/.d-arxiv-1st/`) — no son instalaciones independientes, B es A más un paso.

## A. Claude Code CLI

### Instalar

Dos formas, el resultado es el mismo:

**Vía el comando del plugin** — requiere dar de alta el plugin en Claude Code, vía el marketplace que este repo declara en `.claude-plugin/marketplace.json`:

```
/plugin marketplace add TINTA-ARTIFICIAL/d-arxiv-1st
/plugin install d-arxiv-1st@d-arxiv-marketplace
```

Verifica con `/plugin list` (si no aparece, prueba `/reload-plugins`). El comando `/d-arxiv-1st:setup` ejecuta `scripts/bootstrap.py` y te va preguntando en el propio chat.

**Directamente** — sin dar de alta ningún plugin, en cualquier chat con acceso a una terminal (tool Bash):

```bash
python3 scripts/bootstrap.py
```

`bootstrap.py` instala desde la última release publicada en GitHub (ya existe una release real, `v0.1.0`, desde `SETUP-02`). Si lo lanzas desde dentro de un checkout de este repo sin red, cae automáticamente a instalación editable desde ese checkout — el wizard funciona igual en ambos casos.

### Qué preguntas hace el wizard

Dos preguntas — instalar la herramienta y decidir qué vas a indexar son dos momentos distintos, lo segundo se pregunta conversacionalmente la primera vez que hace falta, no aquí:

| # | Pregunta | Valor por defecto si pulsas Enter |
|---|---|---|
| 1 | Ruta del workspace | `~/D-ARXIV-1ST-workspace` |
| 2 | Ámbito de instalación del skill (`user`/`project`) | `user` |

La política de descarga (`always_pdf: false`, `image_default_size: w500`) se escribe con esos valores sin preguntar — si quieres otros, edita `config.yaml` a mano.

### Qué queda configurado al terminar

- `~/.d-arxiv-1st/venv/` — el motor instalado, autocontenido
- `~/.d-arxiv-1st/config.yaml` — workspace y política de descarga. **Esta es la config que lee también el servidor MCP del camino B** — un único fichero, compartido, no hay una config separada para Cowork
- `~/.d-arxiv-1st/install.yaml` — dónde se instaló el skill y desde qué origen se instaló el motor
- El skill `archive-ingest` copiado en `~/.claude/skills/` (`user`) o `./.claude/skills/` (`project`)

**El wizard no toca `publications.yaml`.** No hay ninguna publicación registrada todavía al terminar — eso pasa la primera vez que le pides al skill que traiga o indexe algo.

Con esto ya puedes pedir, en cualquier chat de Claude Code: *"trae el número Summer 1978 de CoEvolution Quarterly"* (identifier `coevolutionquart00unse_15`). La primera vez que trabajes con una publicación no registrada, el skill te pregunta un `key` y un `label` y la registra sobre la marcha — no hace falta decidirlo de antemano.

## B. Cowork o la app de Claude

Necesitas el motor instalado en tu máquina real (**paso 1**, idéntico a A) más una extensión instalada en la app (**paso 2**) — el motor por sí solo no basta: una sesión de Cowork no tiene red real hacia archive.org, así que sin la extensión el skill no puede traer nada nuevo (ver `ARCHITECTURE.md` §01, verificado con pruebas reales).

**Paso 1 — corre el wizard una vez, con cualquier acceso a terminal que tengas** (el tuyo, o un chat de Claude Code con tool Bash — no tiene que ser tu uso habitual, basta con hacerlo una vez): sigue exactamente el camino A de arriba. Esto deja `~/.d-arxiv-1st/venv/` y `~/.d-arxiv-1st/config.yaml` listos.

**Paso 2 — instala la extensión `.mcpb`.** Descárgala de los assets de la última release en GitHub. Instálala con cualquiera de estas tres vías (instalación manual, así es como funciona — no hay forma de automatizar este paso):

1. Doble clic en el fichero `.mcpb`, o
2. arrástralo a la ventana de la app de Claude, o
3. Settings → Extensions → Advanced settings → Install Extension… y selecciónalo

Confirmas permisos en la propia pantalla de instalación. No hace falta repetir esto por sesión — una vez instalada, la extensión queda disponible en cualquier chat nuevo de esa cuenta.

**Paso 3 — conecta la carpeta del workspace a tu sesión de Cowork** (la misma ruta que configuraste en el paso 1). Esto es aparte de la extensión: la extensión trae contenido nuevo escribiéndolo en esa carpeta; conectarla es lo que deja que la propia sesión de Cowork lea/edite lo que ya hay ahí.

Con los tres pasos hechos, en un chat nuevo de Cowork puedes pedir lo mismo que en el camino A — "trae el número X de Y" — y funciona igual, solo que por debajo pasa por las tools de la extensión en vez de por Bash directo.

## C. Cowork sin acceso a terminal, nunca

Con lo que existe hoy, no puedes completar el paso 1 de B (crear `~/.d-arxiv-1st/venv/` necesita correr el wizard, y el wizard necesita una terminal en algún momento, aunque sea prestada) — así que no puedes traer contenido nuevo de archive.org desde Cowork. Es una limitación real, no un paso que falte documentar; está fuera de scope de `MCP-02` (`docs/backlog/ISSUE_MCP-02_mcpb_bundle_distribuible.md`) resolverla, y solo se abordaría si hay demanda confirmada de este perfil concreto.

Sí puedes, sin ninguna instalación adicional: trabajar con contenido que otra persona (o tú mismo, por el camino A o B) ya haya descargado y procesado, conectando la carpeta `processed/` a tu sesión — eso es lectura/escritura de ficheros normal, sin depender de red.

## Relanzar el wizard

`d-arxiv wizard` (una vez el motor ya está instalado, invocando directamente `~/.d-arxiv-1st/venv/bin/d-arxiv wizard`) vuelve a correr el flujo de instalación — útil para reconfigurar el workspace o el ámbito del skill. No hace falta relanzarlo para añadir publicaciones nuevas ni para reinstalar la extensión `.mcpb`; son independientes entre sí.
